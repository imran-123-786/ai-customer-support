"""
Chat API route.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel
try:
    from fastapi import APIRouter, HTTPException
except ImportError:
    APIRouter = None

from support_agent.agent.orchestrator import orchestrator


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    customer_id: str = "CUST-104"
    user_id: Optional[int] = None
    history: Optional[List[Dict[str, Any]]] = None


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    intent: str
    emotion: str
    priority: str
    escalated: bool
    tools_called: List[str]
    citations: List[Dict[str, Any]]
    suggested_actions: List[str]


if APIRouter:
    router = APIRouter(prefix="/chat", tags=["Chat"])

    @router.post("", response_model=ChatResponse)
    def post_chat(req: ChatRequest):
        state = orchestrator.run(
            user_message=req.message,
            conversation_id=req.conversation_id,
            customer_id=req.customer_id,
            user_id=req.user_id,
            history=req.history,
        )
        return ChatResponse(
            conversation_id=state.conversation_id,
            reply=state.final_response or "",
            intent=state.intent,
            emotion=state.emotion,
            priority=state.priority,
            escalated=state.escalation_required,
            tools_called=[tc.tool_name for tc in state.tool_calls],
            citations=state.citations,
            suggested_actions=state.suggested_actions,
        )
else:
    router = None
