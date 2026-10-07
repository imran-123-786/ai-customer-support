"""
Typed database repository for SupportAgent AI.
Encapsulates CRUD operations for users, customers, orders, payments, refunds,
tickets, memories, conversations, agent runs, tool calls, and feedback.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from support_agent.database.connection import get_connection


class DatabaseRepository:
    def __init__(self):
        pass

    # ================= User Operations =================
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username.strip().lower(),))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def create_user(self, username: str, password_hash: str, role: str = "customer") -> Optional[int]:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username.strip().lower(), password_hash, role),
            )
            user_id = cur.lastrowid
            cur.execute(
                "INSERT INTO user_settings (user_id, preferred_language, voice_enabled) VALUES (?, 'auto', 0)",
                (user_id,),
            )
            # Create matching customer entry
            cust_id = f"CUST-{1000 + user_id}"
            cur.execute(
                "INSERT INTO customers (id, user_id, name, email) VALUES (?, ?, ?, ?)",
                (cust_id, user_id, username.title(), f"{username.lower()}@example.com"),
            )
            conn.commit()
            return user_id
        except Exception:
            conn.rollback()
            return None
        finally:
            conn.close()

    def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT preferred_language, voice_enabled FROM user_settings WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return {"preferred_language": "auto", "voice_enabled": 0}
        return dict(row)

    def update_user_settings(self, user_id: int, preferred_language: str, voice_enabled: int) -> None:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO user_settings (user_id, preferred_language, voice_enabled)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                preferred_language = excluded.preferred_language,
                voice_enabled = excluded.voice_enabled
            """,
            (user_id, preferred_language, voice_enabled),
        )
        conn.commit()
        conn.close()

    # ================= Customer & Profile =================
    def get_customer_by_id(self, customer_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_customer_by_user_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM customers WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_customer_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM customers WHERE LOWER(email) = ?", (email.strip().lower(),))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    # ================= Order Operations =================
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders WHERE UPPER(order_id) = ?", (order_id.strip().upper(),))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_orders_by_customer(self, customer_id: str) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY order_date DESC", (customer_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_order_status(self, order_id: str, new_status: str) -> bool:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE orders SET status = ? WHERE UPPER(order_id) = ?", (new_status, order_id.strip().upper()))
        updated = cur.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    # ================= Payment Operations =================
    def get_payments_for_order(self, order_id: str) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM payments WHERE UPPER(order_id) = ? ORDER BY transaction_date DESC", (order_id.strip().upper(),))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ================= Refund Operations =================
    def get_refunds_for_order(self, order_id: str) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM refunds WHERE UPPER(order_id) = ? ORDER BY created_at DESC", (order_id.strip().upper(),))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def create_refund_request(self, refund_id: str, order_id: str, customer_id: str, amount: float, reason: str, status: str = "requested") -> Dict[str, Any]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO refunds (refund_id, order_id, customer_id, amount, reason, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (refund_id, order_id.upper(), customer_id, amount, reason, status),
        )
        conn.commit()
        conn.close()
        return {
            "refund_id": refund_id,
            "order_id": order_id.upper(),
            "amount": amount,
            "reason": reason,
            "status": status,
        }

    # ================= Ticket Operations =================
    def create_ticket(
        self,
        ticket_id: str,
        user_id: Optional[int],
        customer_id: Optional[str],
        topic: str,
        intent: str,
        priority: str,
        status: str = "Open",
        escalated: int = 0,
        escalation_reason: Optional[str] = None,
        handoff_summary: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        conn = get_connection()
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            """
            INSERT INTO tickets (id, user_id, customer_id, topic, intent, priority, status, escalated, escalation_reason, handoff_summary, assigned_to, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                priority = excluded.priority,
                status = excluded.status,
                escalated = excluded.escalated,
                escalation_reason = excluded.escalation_reason,
                handoff_summary = excluded.handoff_summary,
                updated_at = excluded.updated_at
            """,
            (ticket_id, user_id, customer_id, topic, intent, priority, status, escalated, escalation_reason, handoff_summary, assigned_to, now, now),
        )
        cur.execute(
            """
            INSERT INTO ticket_events (ticket_id, event_type, details, timestamp)
            VALUES (?, 'created', ?, ?)
            """,
            (ticket_id, f"Ticket created with priority {priority}", now),
        )
        conn.commit()
        conn.close()
        return {
            "id": ticket_id,
            "user_id": user_id,
            "customer_id": customer_id,
            "topic": topic,
            "intent": intent,
            "priority": priority,
            "status": status,
            "escalated": bool(escalated),
            "escalation_reason": escalation_reason,
            "handoff_summary": handoff_summary,
            "created_at": now,
        }

    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id.strip(),))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def list_tickets(self, user_id: Optional[int] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        query = "SELECT * FROM tickets WHERE 1=1"
        params: list = []
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY datetime(created_at) DESC"
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_ticket_status(self, ticket_id: str, new_status: str, notes: Optional[str] = None) -> bool:
        conn = get_connection()
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("UPDATE tickets SET status = ?, updated_at = ? WHERE id = ?", (new_status, now, ticket_id))
        updated = cur.rowcount > 0
        if updated:
            cur.execute(
                "INSERT INTO ticket_events (ticket_id, event_type, details, timestamp) VALUES (?, 'status_changed', ?, ?)",
                (ticket_id, f"Status changed to {new_status}. {notes or ''}", now),
            )
            conn.commit()
        conn.close()
        return updated

    def get_ticket_events(self, ticket_id: str) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM ticket_events WHERE ticket_id = ? ORDER BY id ASC", (ticket_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ================= Long-Term Customer Memory =================
    def get_customer_memories(self, customer_id: str) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT memory_type, memory_key, memory_value, confidence, updated_at FROM customer_memory WHERE customer_id = ? ORDER BY id ASC",
            (customer_id,),
        )
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def save_customer_memory(self, customer_id: str, memory_type: str, key: str, value: str, confidence: float = 1.0) -> bool:
        conn = get_connection()
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            """
            INSERT INTO customer_memory (customer_id, memory_type, memory_key, memory_value, confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(customer_id, memory_type, memory_key) DO UPDATE SET
                memory_value = excluded.memory_value,
                confidence = excluded.confidence,
                updated_at = excluded.updated_at
            """,
            (customer_id, memory_type, key, value, confidence, now, now),
        )
        conn.commit()
        conn.close()
        return True

    # ================= Conversations & Messages =================
    def save_conversation(self, conv_id: str, user_id: Optional[int], customer_id: Optional[str], title: str, summary: str = "") -> None:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO conversations (id, user_id, customer_id, title, summary)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET summary = excluded.summary, updated_at = CURRENT_TIMESTAMP
            """,
            (conv_id, user_id, customer_id, title, summary),
        )
        conn.commit()
        conn.close()

    def update_conversation_summary(self, conv_id: str, summary: str) -> None:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE conversations SET summary = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (summary, conv_id))
        conn.commit()
        conn.close()

    def get_conversation(self, conv_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def add_message(
        self,
        conv_id: str,
        role: str,
        content: str,
        intent: Optional[str] = None,
        emotion: Optional[str] = None,
        confidence: Optional[float] = None,
        sources_json: Optional[str] = None,
        tool_calls_json: Optional[str] = None,
    ) -> int:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO messages (conversation_id, role, content, intent, emotion, confidence, sources_json, tool_calls_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (conv_id, role, content, intent, emotion, confidence, sources_json, tool_calls_json),
        )
        msg_id = cur.lastrowid
        conn.commit()
        conn.close()
        return msg_id

    def get_messages(self, conv_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC LIMIT ?",
            (conv_id, limit),
        )
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # Legacy table bridge for existing chats
    def save_legacy_chat(self, user_id: int, user_message: str, bot_reply: str) -> None:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO chats (user_id, user_message, bot_reply) VALUES (?, ?, ?)", (user_id, user_message, bot_reply))
        conn.commit()
        conn.close()

    def get_legacy_chats(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM chats WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ================= Observability & Telemetry =================
    def log_tool_call(
        self,
        call_id: str,
        run_id: Optional[str],
        tool_name: str,
        input_data: Any,
        output_data: Any,
        latency_ms: float,
        success: bool,
        error_message: Optional[str] = None,
    ) -> None:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO tool_calls (id, run_id, tool_name, input_json, output_json, latency_ms, success, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                call_id,
                run_id,
                tool_name,
                json.dumps(input_data) if not isinstance(input_data, str) else input_data,
                json.dumps(output_data) if not isinstance(output_data, str) else output_data,
                latency_ms,
                1 if success else 0,
                error_message,
            ),
        )
        conn.commit()
        conn.close()

    def log_agent_run(
        self,
        run_id: str,
        conversation_id: str,
        customer_id: str,
        user_message: str,
        intent: str,
        emotion: str,
        priority: str,
        steps_count: int,
        tools_called_count: int,
        retrieval_count: int,
        start_time: str,
        end_time: str,
        latency_ms: float,
        final_action: str,
        escalated: bool,
        escalation_reason: Optional[str],
        failure_category: Optional[str],
        success: bool,
        error_message: Optional[str],
    ) -> None:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO agent_runs (
                id, conversation_id, customer_id, user_message, intent, emotion, priority,
                steps_count, tools_called_count, retrieval_count, start_time, end_time,
                latency_ms, final_action, escalated, escalation_reason, failure_category,
                success, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                final_action = excluded.final_action,
                end_time = excluded.end_time,
                latency_ms = excluded.latency_ms,
                success = excluded.success,
                failure_category = excluded.failure_category
            """,
            (
                run_id,
                conversation_id,
                customer_id,
                user_message,
                intent,
                emotion,
                priority,
                steps_count,
                tools_called_count,
                retrieval_count,
                start_time,
                end_time,
                latency_ms,
                final_action,
                1 if escalated else 0,
                escalation_reason,
                failure_category,
                1 if success else 0,
                error_message,
            ),
        )
        conn.commit()
        conn.close()

    def get_agent_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM agent_runs ORDER BY start_time DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_tool_calls(self, run_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        if run_id:
            cur.execute("SELECT * FROM tool_calls WHERE run_id = ? ORDER BY timestamp DESC LIMIT ?", (run_id, limit))
        else:
            cur.execute("SELECT * FROM tool_calls ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ================= Evaluation Operations =================
    def save_evaluation_run(self, eval_id: str, eval_name: str, total_cases: int, passed_cases: int, accuracy: float, metrics: Dict[str, Any]) -> None:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO evaluations (id, eval_name, total_cases, passed_cases, accuracy_score, metrics_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (eval_id, eval_name, total_cases, passed_cases, accuracy, json.dumps(metrics)),
        )
        conn.commit()
        conn.close()

    def get_latest_evaluation(self) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM evaluations ORDER BY timestamp DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        res = dict(row)
        res["metrics"] = json.loads(res["metrics_json"])
        return res

    # ================= Feedback Operations =================
    def add_feedback(self, conversation_id: str, csat_score: int, feedback_text: Optional[str] = None) -> None:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO feedback (conversation_id, csat_score, feedback_text) VALUES (?, ?, ?)",
            (conversation_id, csat_score, feedback_text),
        )
        conn.commit()
        conn.close()

    def get_feedback_metrics(self) -> Dict[str, Any]:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT AVG(csat_score) as avg_csat, COUNT(*) as total_reviews FROM feedback")
        row = cur.fetchone()
        conn.close()
        return {
            "avg_csat": round(row["avg_csat"], 2) if row and row["avg_csat"] else 0.0,
            "total_reviews": row["total_reviews"] if row else 0,
        }


repo = DatabaseRepository()
