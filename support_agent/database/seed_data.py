"""
SupportAgent AI - Realistic Synthetic Seed Data Generator.
Provides mock enterprise customer support records for orders, payments, refunds,
tickets, customer profiles, and persistent memory.
Clearly labeled as synthetic/demo data.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from support_agent.database.connection import get_connection, init_database
from support_agent.security import hash_password


def seed_database(force: bool = False) -> None:
    """Populate database with synthetic business entities."""
    init_database()
    conn = get_connection()
    cur = conn.cursor()

    # Check if already seeded
    cur.execute("SELECT COUNT(*) as count FROM customers")
    if cur.fetchone()["count"] > 0 and not force:
        conn.close()
        return

    # 1. Base Users (admin, student, and demo customers)
    users = [
        ("admin", hash_password("admin123"), "admin"),
        ("student", hash_password("1234"), "customer"),
        ("agent_jane", hash_password("agent123"), "agent"),
        ("rahul_sharma", hash_password("demo123"), "customer"),
        ("priya_patel", hash_password("demo123"), "customer"),
        ("vikram_m", hash_password("demo123"), "customer"),
    ]
    for u, p, r in users:
        cur.execute(
            """
            INSERT INTO users (username, password_hash, role)
            VALUES (?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash, role=excluded.role
            """,
            (u, p, r),
        )

    # Fetch user ids
    cur.execute("SELECT id, username FROM users")
    user_map = {row["username"]: row["id"] for row in cur.fetchall()}

    # User settings
    for uid in user_map.values():
        cur.execute(
            """
            INSERT INTO user_settings (user_id, preferred_language, voice_enabled)
            VALUES (?, 'auto', 0)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (uid,),
        )

    # 2. Customers
    customers = [
        ("CUST-101", user_map.get("rahul_sharma"), "Rahul Sharma", "rahul@example.com", "+91-9876543210", "Gold"),
        ("CUST-102", user_map.get("priya_patel"), "Priya Patel", "priya@example.com", "+91-9876543211", "Standard"),
        ("CUST-103", user_map.get("vikram_m"), "Vikram Malhotra", "vikram@example.com", "+91-9876543212", "VIP"),
        ("CUST-104", user_map.get("student"), "Student Demo", "student@example.com", "+1-555-019-2831", "Standard"),
        ("CUST-105", None, "Amit Roy", "amit.roy@example.com", "+91-9876543214", "Standard"),
    ]
    for cid, uid, name, email, phone, tier in customers:
        cur.execute(
            """
            INSERT INTO customers (id, user_id, name, email, phone, tier)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET name=excluded.name, email=excluded.email, tier=excluded.tier
            """,
            (cid, uid, name, email, phone, tier),
        )

    now = datetime.now()
    d1 = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    d5 = (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
    d10 = (now - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
    d45 = (now - timedelta(days=45)).strftime("%Y-%m-%d %H:%M:%S")

    # 3. Orders
    orders = [
        ("ORD-1001", "CUST-101", "Wireless Noise-Cancelling Headphones", 2999.00, "INR", "shipped", "42 MG Road, Bengaluru, 560001", "TRK-IN-982103", d5, None),
        ("ORD-1002", "CUST-102", "Mechanical Ergonomic Keyboard", 4500.00, "INR", "delivered", "15 Ring Road, Pune, 411001", "TRK-IN-883190", d5, d1),
        ("ORD-1005", "CUST-104", "Smart Fitness Tracker Watch", 199.00, "USD", "pending", "742 Evergreen Terrace, Springfield, OR", "TRK-US-102931", d1, None),
        ("ORD-1024", "CUST-103", "Ultra HD 4K Gaming Monitor", 24999.00, "INR", "delivered", "88 Marine Drive, Mumbai, 400020", "TRK-IN-773829", d10, d5),
        ("ORD-1025", "CUST-105", "Thunderbolt 4 Docking Station", 3200.00, "INR", "delivered", "12 Park Street, Kolkata, 700016", "TRK-IN-662910", d45, d45),
    ]
    for oid, cid, item, amt, curr, stat, addr, trk, odate, ddate in orders:
        cur.execute(
            """
            INSERT INTO orders (order_id, customer_id, item_name, amount, currency, status, delivery_address, tracking_number, order_date, delivered_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(order_id) DO UPDATE SET status=excluded.status
            """,
            (oid, cid, item, amt, curr, stat, addr, trk, odate, ddate),
        )

    # 4. Payments
    payments = [
        ("PAY-5001", "ORD-1001", "CUST-101", 2999.00, "INR", "upi", "captured", d5),
        ("PAY-5002", "ORD-1002", "CUST-102", 4500.00, "INR", "credit_card", "captured", d5),
        ("PAY-5003", "ORD-1024", "CUST-103", 24999.00, "INR", "credit_card", "captured", d10),
        ("PAY-5004", "ORD-1024", "CUST-103", 24999.00, "INR", "credit_card", "duplicate_flagged", d10), # Duplicate charge!
        ("PAY-5005", "ORD-1005", "CUST-104", 199.00, "USD", "credit_card", "captured", d1),
        ("PAY-5006", "ORD-1025", "CUST-105", 3200.00, "INR", "net_banking", "captured", d45),
    ]
    for pid, oid, cid, amt, curr, mthd, stat, tdate in payments:
        cur.execute(
            """
            INSERT INTO payments (payment_id, order_id, customer_id, amount, currency, method, status, transaction_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(payment_id) DO UPDATE SET status=excluded.status
            """,
            (pid, oid, cid, amt, curr, mthd, stat, tdate),
        )

    # 5. Refunds
    refunds = [
        ("REF-2001", "ORD-1025", "CUST-105", 3200.00, "Past return window", "rejected", d10),
    ]
    for rid, oid, cid, amt, rsn, stat, cdate in refunds:
        cur.execute(
            """
            INSERT INTO refunds (refund_id, order_id, customer_id, amount, reason, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(refund_id) DO UPDATE SET status=excluded.status
            """,
            (rid, oid, cid, amt, rsn, stat, cdate),
        )

    # 6. Customer Memory (Persistent Long-Term Memory)
    memories = [
        ("CUST-101", "language_preference", "preferred_language", "Hindi responses", 0.95),
        ("CUST-103", "preference", "communication_style", "Concise executive summary, high priority VIP handling", 0.98),
        ("CUST-102", "known_issue", "hardware_compatibility", "Uses macOS Sonoma with external mechanical keyboards", 0.85),
    ]
    for cid, mtype, mkey, mval, conf in memories:
        cur.execute(
            """
            INSERT INTO customer_memory (customer_id, memory_type, memory_key, memory_value, confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(customer_id, memory_type, memory_key) DO UPDATE SET memory_value=excluded.memory_value
            """,
            (cid, mtype, mkey, mval, conf),
        )

    # 7. Initial Tickets & Events
    tickets = [
        ("TICK-8001", user_map.get("student"), "CUST-104", "Order tracking inquiry for ORD-1005", "Order Tracking", "Low", "Resolved", 0, None, "Customer verified shipping carrier update.", "agent_jane", d5),
        ("TICK-8002", user_map.get("vikram_m"), "CUST-103", "Duplicate deduction on monitor order ORD-1024", "Billing & Refund", "High", "Open", 1, "Duplicate payment confirmed on PAY-5004", "Payment investigation required for second charge refund.", "agent_jane", d1),
    ]
    for tid, uid, cid, top, intent, prio, stat, esc, esc_rsn, handoff, assn, cdate in tickets:
        cur.execute(
            """
            INSERT INTO tickets (id, user_id, customer_id, topic, intent, priority, status, escalated, escalation_reason, handoff_summary, assigned_to, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET status=excluded.status
            """,
            (tid, uid, cid, top, intent, prio, stat, esc, esc_rsn, handoff, assn, cdate, cdate),
        )
        cur.execute(
            """
            INSERT INTO ticket_events (ticket_id, event_type, details, timestamp)
            VALUES (?, 'created', 'Initial ticket created by SupportAgent AI', ?)
            """,
            (tid, cdate),
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    seed_database(force=True)
    print("Database successfully initialized and seeded with synthetic business entities.")
