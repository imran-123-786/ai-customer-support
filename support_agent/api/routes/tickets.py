"""
Tickets API route.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel
try:
    from fastapi import APIRouter, HTTPException
except ImportError:
    APIRouter = None

from support_agent.database.repository import repo


class CreateTicketRequest(BaseModel):
    topic: str
    intent: str = "General Inquiry"
    priority: str = "Medium"
    issue_details: str = ""
    user_id: Optional[int] = None
    customer_id: Optional[str] = "CUST-104"


class UpdateTicketStatusRequest(BaseModel):
    status: str
    notes: Optional[str] = None


if APIRouter:
    router = APIRouter(prefix="/tickets", tags=["Tickets"])

    @router.get("")
    def get_tickets(user_id: Optional[int] = None, status: Optional[str] = None):
        return repo.list_tickets(user_id=user_id, status=status)

    @router.get("/{ticket_id}")
    def get_ticket(ticket_id: str):
        ticket = repo.get_ticket(ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
        events = repo.get_ticket_events(ticket_id)
        return {"ticket": ticket, "events": events}

    @router.patch("/{ticket_id}")
    def update_ticket(ticket_id: str, req: UpdateTicketStatusRequest):
        success = repo.update_ticket_status(ticket_id, req.status, req.notes)
        if not success:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} update failed")
        return {"success": True, "ticket_id": ticket_id, "status": req.status}
else:
    router = None
