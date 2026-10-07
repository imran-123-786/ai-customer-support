"""
Built-in enterprise customer support tools.
Implements real business logic, DB queries, validation, and structured responses.
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from support_agent.database.repository import repo
from support_agent.models.schemas import PermissionLevel
from support_agent.tools.registry import registry


# ================= Models =================
class GetCustomerProfileInput(BaseModel):
    customer_id: Optional[str] = Field(default=None, description="Customer ID, e.g. CUST-101")
    email: Optional[str] = Field(default=None, description="Customer email address")


class GetOrderDetailsInput(BaseModel):
    order_id: str = Field(description="Order ID, e.g. ORD-1001, ORD-1024")


class GetPaymentStatusInput(BaseModel):
    order_id: str = Field(description="Order ID to look up payment transactions for")


class CheckRefundEligibilityInput(BaseModel):
    order_id: str = Field(description="Order ID to evaluate refund policy against")


class CreateRefundRequestInput(BaseModel):
    order_id: str = Field(description="Order ID for refund request")
    reason: str = Field(description="Reason for refund, e.g. duplicate payment or damaged item")
    amount: Optional[float] = Field(default=None, description="Optional custom amount, defaults to order total")


class CreateSupportTicketInput(BaseModel):
    topic: str = Field(description="Short title of the support issue")
    priority: str = Field(default="Medium", description="Low, Medium, High, or Critical")
    intent: str = Field(default="General Inquiry", description="Classified intent")
    issue_details: str = Field(description="Detailed description of the customer issue")


class GetTicketStatusInput(BaseModel):
    ticket_id: str = Field(description="Support ticket ID, e.g. TICK-8001 or SS-1024")


class UpdateTicketInput(BaseModel):
    ticket_id: str = Field(description="Ticket ID to update")
    status: str = Field(description="New status: Open, In Progress, Waiting, Resolved, Closed")
    notes: Optional[str] = Field(default=None, description="Resolution or status change notes")


class SearchKnowledgeBaseInput(BaseModel):
    query: str = Field(description="Search question or topic in support documentation")
    top_k: int = Field(default=3, description="Number of document chunks to retrieve")


class GetCustomerMemoryInput(BaseModel):
    customer_id: str = Field(description="Customer ID to retrieve long-term memory for")


class SaveCustomerMemoryInput(BaseModel):
    customer_id: str = Field(description="Customer ID to store preference or fact for")
    memory_type: str = Field(description="Type: preference, language_preference, style_preference, known_issue")
    key: str = Field(description="Key descriptor")
    value: str = Field(description="Content to remember")


class EscalateToHumanInput(BaseModel):
    ticket_id: Optional[str] = Field(default=None, description="Existing ticket ID if already created")
    reason: str = Field(description="Reason why human agent escalation is required")
    priority: str = Field(default="High", description="Escalation priority")


class SearchPreviousConversationsInput(BaseModel):
    customer_id: str = Field(description="Customer ID to search past interaction history for")
    query: str = Field(description="Keywords to filter past conversations")


# ================= Tool Implementations =================

@registry.register(
    name="get_customer_profile",
    description="Look up customer details, tier, email, and phone by customer ID or email.",
    permission=PermissionLevel.READ_ONLY,
    input_model=GetCustomerProfileInput,
)
def get_customer_profile(customer_id: Optional[str] = None, email: Optional[str] = None) -> Dict[str, Any]:
    cust = None
    if customer_id:
        cust = repo.get_customer_by_id(customer_id)
    elif email:
        cust = repo.get_customer_by_email(email)

    if not cust:
        return {"success": False, "error": f"Customer profile not found for ID: {customer_id} / email: {email}"}

    memories = repo.get_customer_memories(cust["id"])
    return {
        "success": True,
        "customer_id": cust["id"],
        "name": cust["name"],
        "email": cust["email"],
        "phone": cust.get("phone"),
        "tier": cust["tier"],
        "known_preferences": [f"{m['memory_type']}: {m['memory_value']}" for m in memories],
    }


@registry.register(
    name="get_order_details",
    description="Retrieve order status, items, amounts, currency, and delivery tracking details.",
    permission=PermissionLevel.READ_ONLY,
    input_model=GetOrderDetailsInput,
)
def get_order_details(order_id: str) -> Dict[str, Any]:
    order = repo.get_order(order_id)
    if not order:
        return {"success": False, "error": f"Order {order_id} not found in system records."}

    payments = repo.get_payments_for_order(order_id)
    return {
        "success": True,
        "order_id": order["order_id"],
        "customer_id": order["customer_id"],
        "item_name": order["item_name"],
        "amount": order["amount"],
        "currency": order["currency"],
        "status": order["status"],
        "delivery_address": order["delivery_address"],
        "tracking_number": order["tracking_number"],
        "order_date": order["order_date"],
        "delivered_date": order["delivered_date"],
        "payment_count": len(payments),
    }


@registry.register(
    name="get_payment_status",
    description="Check payment status, method, and transaction history for an order.",
    permission=PermissionLevel.READ_ONLY,
    input_model=GetPaymentStatusInput,
)
def get_payment_status(order_id: str) -> Dict[str, Any]:
    payments = repo.get_payments_for_order(order_id)
    if not payments:
        return {"success": False, "error": f"No payment records found for order {order_id}."}

    duplicate_detected = any(p["status"] == "duplicate_flagged" for p in payments) or len(payments) > 1
    total_charged = sum(p["amount"] for p in payments if p["status"] in ("captured", "duplicate_flagged"))

    return {
        "success": True,
        "order_id": order_id.upper(),
        "total_transactions": len(payments),
        "duplicate_charge_flag": duplicate_detected,
        "total_charged": total_charged,
        "transactions": [
            {
                "payment_id": p["payment_id"],
                "amount": p["amount"],
                "currency": p["currency"],
                "method": p["method"],
                "status": p["status"],
                "date": p["transaction_date"],
            }
            for p in payments
        ],
    }


@registry.register(
    name="check_refund_eligibility",
    description="Evaluate whether an order is eligible for refund based on delivery date, status, and duplicate payments.",
    permission=PermissionLevel.READ_ONLY,
    input_model=CheckRefundEligibilityInput,
)
def check_refund_eligibility(order_id: str) -> Dict[str, Any]:
    order = repo.get_order(order_id)
    if not order:
        return {"success": False, "eligible": False, "reason": f"Order {order_id} not found."}

    payments = repo.get_payments_for_order(order_id)
    has_duplicate = any(p["status"] == "duplicate_flagged" for p in payments)

    # If duplicate payment occurred, immediate eligibility for the second charge
    if has_duplicate:
        return {
            "success": True,
            "eligible": True,
            "reason": "Duplicate transaction detected on payment gateway. Customer is eligible for immediate refund of duplicate amount.",
            "order_id": order["order_id"],
            "refundable_amount": order["amount"],
            "currency": order["currency"],
        }

    # Policy rule: delivered within 30 days is eligible, cancelled/pending is eligible
    if order["status"] == "pending":
        return {
            "success": True,
            "eligible": True,
            "reason": "Order has not yet shipped. Full cancellation and immediate refund is permitted.",
            "order_id": order["order_id"],
            "refundable_amount": order["amount"],
            "currency": order["currency"],
        }

    if order["status"] == "delivered":
        if order["delivered_date"]:
            try:
                del_dt = datetime.strptime(order["delivered_date"][:10], "%Y-%m-%d")
                if datetime.now() - del_dt > timedelta(days=30):
                    return {
                        "success": True,
                        "eligible": False,
                        "reason": "Delivered more than 30 days ago. Standard refund window has expired under support policy.",
                        "order_id": order["order_id"],
                    }
            except Exception:
                pass
        return {
            "success": True,
            "eligible": True,
            "reason": "Order delivered within the 30-day return window. Item in eligible condition for return/refund.",
            "order_id": order["order_id"],
            "refundable_amount": order["amount"],
            "currency": order["currency"],
        }

    return {
        "success": True,
        "eligible": False,
        "reason": f"Order status is {order['status']}. Return request requires manual review.",
        "order_id": order["order_id"],
    }


@registry.register(
    name="create_refund_request",
    description="Initiate a refund for an order. SENSITIVE OPERATION that logs a transaction record.",
    permission=PermissionLevel.SENSITIVE,
    input_model=CreateRefundRequestInput,
)
def create_refund_request(order_id: str, reason: str, amount: Optional[float] = None) -> Dict[str, Any]:
    order = repo.get_order(order_id)
    if not order:
        return {"success": False, "error": f"Cannot create refund. Order {order_id} does not exist."}

    refund_amt = amount if amount is not None else order["amount"]
    refund_id = f"REF-{random.randint(1000, 9999)}"

    record = repo.create_refund_request(
        refund_id=refund_id,
        order_id=order["order_id"],
        customer_id=order["customer_id"],
        amount=refund_amt,
        reason=reason,
        status="requested",
    )
    return {
        "success": True,
        "refund_id": refund_id,
        "order_id": order["order_id"],
        "amount": refund_amt,
        "currency": order["currency"],
        "status": "requested",
        "message": f"Refund request {refund_id} successfully registered for {order['currency']} {refund_amt}. Estimated processing: 3-5 business days.",
    }


@registry.register(
    name="create_support_ticket",
    description="Create a persistent support ticket with priority and intent triage.",
    permission=PermissionLevel.WRITE,
    input_model=CreateSupportTicketInput,
)
def create_support_ticket(topic: str, priority: str = "Medium", intent: str = "General Inquiry", issue_details: str = "") -> Dict[str, Any]:
    ticket_id = f"TICK-{random.randint(8000, 9999)}"
    ticket = repo.create_ticket(
        ticket_id=ticket_id,
        user_id=None,
        customer_id="CUST-104",
        topic=topic[:80],
        intent=intent,
        priority=priority,
        status="Open",
        escalated=1 if priority in ("High", "Critical") else 0,
        escalation_reason=issue_details[:120] if priority in ("High", "Critical") else None,
        handoff_summary=issue_details,
    )
    return {
        "success": True,
        "ticket_id": ticket_id,
        "priority": priority,
        "status": "Open",
        "message": f"Support ticket {ticket_id} created successfully with {priority} priority.",
    }


@registry.register(
    name="get_ticket_status",
    description="Look up the current status and events of an existing support ticket.",
    permission=PermissionLevel.READ_ONLY,
    input_model=GetTicketStatusInput,
)
def get_ticket_status(ticket_id: str) -> Dict[str, Any]:
    ticket = repo.get_ticket(ticket_id)
    if not ticket:
        return {"success": False, "error": f"Ticket {ticket_id} not found."}

    events = repo.get_ticket_events(ticket_id)
    return {
        "success": True,
        "ticket_id": ticket["id"],
        "topic": ticket["topic"],
        "priority": ticket["priority"],
        "status": ticket["status"],
        "created_at": ticket["created_at"],
        "updated_at": ticket["updated_at"],
        "history": [f"{e['event_type']} at {e['timestamp']}: {e['details']}" for e in events],
    }


@registry.register(
    name="update_ticket",
    description="Update an existing support ticket status or append resolution notes.",
    permission=PermissionLevel.WRITE,
    input_model=UpdateTicketInput,
)
def update_ticket(ticket_id: str, status: str, notes: Optional[str] = None) -> Dict[str, Any]:
    success = repo.update_ticket_status(ticket_id, status, notes)
    if not success:
        return {"success": False, "error": f"Ticket {ticket_id} could not be updated."}

    return {"success": True, "ticket_id": ticket_id, "status": status, "notes": notes}


@registry.register(
    name="search_knowledge_base",
    description="Search verified company documentation and policies using semantic / lexical RAG.",
    permission=PermissionLevel.READ_ONLY,
    input_model=SearchKnowledgeBaseInput,
)
def search_knowledge_base(query: str, top_k: int = 3) -> Dict[str, Any]:
    from support_agent.rag.retriever import retriever
    hits = retriever.search(query, top_k=top_k)
    return {
        "success": True,
        "count": len(hits),
        "results": [
            {
                "source": h.source,
                "section": h.section or "General",
                "snippet": h.chunk[:300],
                "score": round(h.score, 3),
            }
            for h in hits
        ],
    }


@registry.register(
    name="get_customer_memory",
    description="Retrieve persistent customer preferences, language, and known issues from long-term memory.",
    permission=PermissionLevel.READ_ONLY,
    input_model=GetCustomerMemoryInput,
)
def get_customer_memory(customer_id: str) -> Dict[str, Any]:
    memories = repo.get_customer_memories(customer_id)
    return {
        "success": True,
        "customer_id": customer_id,
        "memories": [
            {"type": m["memory_type"], "key": m["memory_key"], "value": m["memory_value"]}
            for m in memories
        ],
    }


@registry.register(
    name="save_customer_memory",
    description="Persist durable customer preference or communication style to long-term memory.",
    permission=PermissionLevel.WRITE,
    input_model=SaveCustomerMemoryInput,
)
def save_customer_memory(customer_id: str, memory_type: str, key: str, value: str) -> Dict[str, Any]:
    repo.save_customer_memory(customer_id, memory_type, key, value)
    return {
        "success": True,
        "customer_id": customer_id,
        "message": f"Saved {memory_type} preference: '{key}' = '{value}' to persistent customer memory.",
    }


@registry.register(
    name="escalate_to_human",
    description="Escalate a complex, high-priority, or failed case to a human support agent.",
    permission=PermissionLevel.WRITE,
    input_model=EscalateToHumanInput,
)
def escalate_to_human(ticket_id: Optional[str] = None, reason: str = "", priority: str = "High") -> Dict[str, Any]:
    final_ticket_id = ticket_id or f"TICK-{uuid.uuid4().hex[:6].upper()}"
    if not ticket_id:
        repo.create_ticket(
            ticket_id=final_ticket_id,
            user_id=None,
            customer_id="CUST-104",
            topic=f"Escalation: {reason[:60]}",
            intent="Human Handoff",
            priority=priority,
            status="Open",
            escalated=1,
            escalation_reason=reason,
            handoff_summary=f"Automated escalation triggered: {reason}",
        )
    else:
        repo.update_ticket_status(final_ticket_id, "Open", notes=f"Escalated to human tier. Reason: {reason}")

    return {
        "success": True,
        "escalated": True,
        "ticket_id": final_ticket_id,
        "priority": priority,
        "reason": reason,
        "message": f"Successfully escalated to Human Support tier under ticket {final_ticket_id}. Queue SLA: 10 minutes.",
    }


@registry.register(
    name="search_previous_conversations",
    description="Search past customer conversations and tickets for historical context.",
    permission=PermissionLevel.READ_ONLY,
    input_model=SearchPreviousConversationsInput,
)
def search_previous_conversations(customer_id: str, query: str) -> Dict[str, Any]:
    # Search tickets & legacy chats
    tickets = repo.list_tickets()
    matching_tickets = [
        {"id": t["id"], "topic": t["topic"], "status": t["status"]}
        for t in tickets
        if query.lower() in t["topic"].lower() or query.lower() in t["intent"].lower()
    ]
    return {
        "success": True,
        "customer_id": customer_id,
        "query": query,
        "matching_records": matching_tickets[:3],
    }
