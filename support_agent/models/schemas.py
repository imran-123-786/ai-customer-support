"""
Pydantic schemas for AgentState, structured decisions, tool models, and telemetry.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentActionType(str, Enum):
    ANSWER = "answer"
    TOOL = "tool"
    RETRIEVE = "retrieve"
    ASK_CLARIFICATION = "ask_clarification"
    ESCALATE = "escalate"
    CREATE_TICKET = "create_ticket"
    FINISH = "finish"


class PermissionLevel(str, Enum):
    READ_ONLY = "READ_ONLY"
    WRITE = "WRITE"
    SENSITIVE = "SENSITIVE"


class FailureCategory(str, Enum):
    MODEL_FAILURE = "MODEL_FAILURE"
    PROMPT_FAILURE = "PROMPT_FAILURE"
    CONTEXT_FAILURE = "CONTEXT_FAILURE"
    RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"
    TOOL_FAILURE = "TOOL_FAILURE"
    MEMORY_FAILURE = "MEMORY_FAILURE"
    APPLICATION_FAILURE = "APPLICATION_FAILURE"
    PARSING_FAILURE = "PARSING_FAILURE"


class AgentDecision(BaseModel):
    action: AgentActionType = Field(description="Selected action type")
    tool_name: Optional[str] = Field(default=None, description="Name of tool to execute if action is tool")
    tool_args: Dict[str, Any] = Field(default_factory=dict, description="Arguments for tool call")
    reason: str = Field(description="Explicit reasoning for this decision")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")


class ToolCallRecord(BaseModel):
    call_id: str
    run_id: Optional[str] = None
    tool_name: str
    tool_args: Dict[str, Any]
    latency_ms: float = 0.0
    success: bool = True
    error_message: Optional[str] = None


class ToolResultRecord(BaseModel):
    call_id: str
    tool_name: str
    result: Any
    success: bool = True
    error_message: Optional[str] = None


class RetrievedDocument(BaseModel):
    source: str
    section: Optional[str] = None
    chunk: str
    score: float


class GroundingCheckResult(BaseModel):
    is_grounded: bool = True
    unsupported_claims: List[str] = Field(default_factory=list)
    confidence: float = 1.0


class MemoryItem(BaseModel):
    memory_type: str = Field(description="Type: preference, language_preference, style_preference, known_issue")
    key: str = Field(description="Identifier or category")
    value: str = Field(description="Actual remembered preference or fact")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class MemoryExtractionCandidate(BaseModel):
    should_remember: bool = False
    memories: List[MemoryItem] = Field(default_factory=list)


class EscalationDecision(BaseModel):
    escalate: bool = False
    reason: Optional[str] = None
    priority: str = "Medium"


class HandoffSummary(BaseModel):
    issue: str
    priority: str
    customer_sentiment: str
    actions_attempted: List[str] = Field(default_factory=list)
    recommended_action: str


class TriageResult(BaseModel):
    intent: str
    emotion: str
    priority: str
    confidence: float = 0.85
    suggested_actions: List[str] = Field(default_factory=list)


class AgentState(BaseModel):
    run_id: str
    conversation_id: str
    customer_id: str = "CUST-104"
    user_id: Optional[int] = None
    current_message: str
    intent: str = "General Inquiry"
    emotion: str = "neutral"
    priority: str = "Low"
    retrieved_documents: List[RetrievedDocument] = Field(default_factory=list)
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    tool_results: List[ToolResultRecord] = Field(default_factory=list)
    short_term_memory: List[Dict[str, Any]] = Field(default_factory=list)
    long_term_memory: List[Dict[str, Any]] = Field(default_factory=list)
    conversation_summary: str = ""
    current_step: int = 0
    max_steps: int = 6
    escalation_required: bool = False
    escalation_reason: Optional[str] = None
    handoff_summary: Optional[str] = None
    failure_category: Optional[FailureCategory] = None
    final_response: Optional[str] = None
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    suggested_actions: List[str] = Field(default_factory=list)
    finished: bool = False
