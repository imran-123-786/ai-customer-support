"""
SupportAgent AI - Multi-Step Autonomous Agent Orchestrator.
Coordinates triage, persistent memory, tool execution loop, RAG retrieval,
grounding verification, human handoff, and observability telemetry.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional

from support_agent.agent.escalation import escalation_engine
from support_agent.agent.triage import triage_engine
from support_agent.config import MAX_AGENT_STEPS
from support_agent.context.builder import context_builder
from support_agent.database.repository import repo
from support_agent.llm.provider import get_llm_provider
from support_agent.memory.extractor import memory_extractor
from support_agent.memory.long_term import customer_memory
from support_agent.models.schemas import (
    AgentActionType,
    AgentDecision,
    AgentState,
    FailureCategory,
    RetrievedDocument,
    ToolCallRecord,
    ToolResultRecord,
)
from support_agent.rag.retriever import retriever
from support_agent.tools.registry import registry


class SupportAgentOrchestrator:
    def __init__(self, max_steps: int = MAX_AGENT_STEPS):
        self.max_steps = max_steps
        self.llm = get_llm_provider()

    def run(
        self,
        user_message: str,
        conversation_id: Optional[str] = None,
        customer_id: str = "CUST-104",
        user_id: Optional[int] = None,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> AgentState:
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        conv_id = conversation_id or f"conv-{uuid.uuid4().hex[:8]}"
        start_time_iso = time.strftime("%Y-%m-%d %H:%M:%S")
        start_time = time.time()

        # 1. Triage analysis
        triage_res = triage_engine.triage(user_message)

        # 2. Fetch existing long-term memories
        memories = customer_memory.get_memories(customer_id)
        memory_dicts = [{"memory_type": m.memory_type, "memory_key": m.key, "memory_value": m.value} for m in memories]

        # 3. Initialize AgentState
        state = AgentState(
            run_id=run_id,
            conversation_id=conv_id,
            customer_id=customer_id,
            user_id=user_id,
            current_message=user_message,
            intent=triage_res.intent,
            emotion=triage_res.emotion,
            priority=triage_res.priority,
            short_term_memory=history or [],
            long_term_memory=memory_dicts,
            max_steps=self.max_steps,
            suggested_actions=triage_res.suggested_actions,
        )

        # Check customer language preference from long-term memory
        lang_pref = "en"
        for m in memories:
            if m.memory_type == "language_preference":
                if "hindi" in m.value.lower():
                    lang_pref = "hi"
                elif "bengali" in m.value.lower():
                    lang_pref = "bn"

        # 4. Immediate Escalation Check
        escalation_eval = escalation_engine.evaluate_escalation(state)
        if escalation_eval.escalate:
            tool_res = registry.execute(
                tool_name="escalate_to_human",
                args={"reason": escalation_eval.reason or "Human escalation requested", "priority": escalation_eval.priority},
                run_id=run_id,
                user_role="customer",
            )
            state.tool_calls.append(
                ToolCallRecord(
                    call_id=tool_res.call_id,
                    run_id=run_id,
                    tool_name="escalate_to_human",
                    tool_args={"reason": escalation_eval.reason, "priority": escalation_eval.priority},
                    success=tool_res.success,
                )
            )
            state.tool_results.append(tool_res)
            ticket_id = tool_res.result.get("ticket_id") if tool_res.result else "TICK-ESC"
            state.escalation_required = True
            state.escalation_reason = escalation_eval.reason
            state.final_response = (
                f"I understand your request requires personal assistance. "
                f"I have escalated your case to our priority human support desk under Ticket **{ticket_id}** ({escalation_eval.priority} priority).\n\n"
                f"A support specialist has been briefed with your issue context and will take over shortly."
            )
            state.finished = True

        # 5. Multi-Step Controlled Agent Loop
        available_tools = [t.name for t in registry.list_tools()]

        while not state.finished and state.current_step < state.max_steps:
            state.current_step += 1

            # Agent decision
            decision: AgentDecision = self.llm.select_action(
                state_dict=state.model_dump(),
                available_tools=available_tools,
            )

            if decision.action == AgentActionType.TOOL:
                if not decision.tool_name:
                    state.failure_category = FailureCategory.TOOL_FAILURE
                    break

                # Execute tool
                tool_res: ToolResultRecord = registry.execute(
                    tool_name=decision.tool_name,
                    args=decision.tool_args,
                    run_id=run_id,
                    user_role="customer",
                )
                state.tool_calls.append(
                    ToolCallRecord(
                        call_id=tool_res.call_id,
                        run_id=run_id,
                        tool_name=decision.tool_name,
                        tool_args=decision.tool_args,
                        success=tool_res.success,
                    )
                )
                state.tool_results.append(tool_res)

                # Check if tool execution had an error
                if not tool_res.success:
                    state.failure_category = FailureCategory.TOOL_FAILURE
                    # Escalate if a critical tool failed
                    ticket_id = escalation_engine.trigger_escalation(state, f"Tool error in {decision.tool_name}: {tool_res.error_message}")
                    state.final_response = (
                        f"We encountered a temporary processing issue while looking up your records. "
                        f"I have opened Ticket **{ticket_id}** and escalated this to an agent to verify manually."
                    )
                    state.finished = True
                    break

            elif decision.action == AgentActionType.RETRIEVE:
                # Retrieve from RAG
                docs = retriever.search(user_message, top_k=3)
                state.retrieved_documents = docs
                state.citations = retriever.format_citations(docs)

            elif decision.action == AgentActionType.ASK_CLARIFICATION:
                state.final_response = (
                    "To help you with this right away, could you please provide your **Order ID** "
                    "(e.g., ORD-1001 or ORD-1024) or the email address associated with your purchase?"
                )
                state.finished = True
                break

            elif decision.action == AgentActionType.ESCALATE:
                ticket_id = escalation_engine.trigger_escalation(state, decision.reason, "High")
                state.final_response = (
                    f"I have escalated your request to our senior support team under Ticket **{ticket_id}**. "
                    f"A human representative is reviewing your case."
                )
                state.finished = True
                break

            elif decision.action == AgentActionType.ANSWER:
                state.final_response = self._synthesize_grounded_answer(state, lang_pref)
                state.finished = True
                break

        # Loop timeout guard: If step limit exceeded
        if not state.finished and state.current_step >= state.max_steps:
            state.failure_category = FailureCategory.APPLICATION_FAILURE
            ticket_id = escalation_engine.trigger_escalation(
                state, f"Agent exceeded {state.max_steps} iterations without resolution.", "High"
            )
            state.final_response = (
                f"Your request involves multi-tiered validation that exceeded our automated step limit. "
                f"I have logged Ticket **{ticket_id}** and transferred your request directly to our human operations desk."
            )
            state.finished = True

        # 6. Memory Extraction (Learn from conversation)
        memory_extractor.extract_from_message(customer_id, user_message)

        # 7. Grounding and Citations
        if state.retrieved_documents and not state.citations:
            state.citations = retriever.format_citations(state.retrieved_documents)

        # 8. Record Agent Run Telemetry in Database
        latency_ms = round((time.time() - start_time) * 1000, 2)
        end_time_iso = time.strftime("%Y-%m-%d %H:%M:%S")

        repo.log_agent_run(
            run_id=run_id,
            conversation_id=conv_id,
            customer_id=customer_id,
            user_message=user_message,
            intent=state.intent,
            emotion=state.emotion,
            priority=state.priority,
            steps_count=state.current_step,
            tools_called_count=len(state.tool_calls),
            retrieval_count=len(state.retrieved_documents),
            start_time=start_time_iso,
            end_time=end_time_iso,
            latency_ms=latency_ms,
            final_action="escalate" if state.escalation_required else "answer",
            escalated=state.escalation_required,
            escalation_reason=state.escalation_reason,
            failure_category=state.failure_category.value if state.failure_category else None,
            success=state.failure_category is None,
            error_message=state.escalation_reason if state.escalation_required else None,
        )

        # Persist conversation and message to SQLite
        repo.save_conversation(conv_id, user_id, customer_id, title=user_message[:50])
        repo.add_message(
            conv_id=conv_id,
            role="user",
            content=user_message,
            intent=state.intent,
            emotion=state.emotion,
            confidence=0.92,
        )
        repo.add_message(
            conv_id=conv_id,
            role="assistant",
            content=state.final_response or "",
            intent=state.intent,
            emotion=state.emotion,
            confidence=0.92,
            sources_json=json.dumps(state.citations) if state.citations else None,
            tool_calls_json=json.dumps([tc.model_dump() for tc in state.tool_calls]) if state.tool_calls else None,
        )

        # Also store to legacy chats table for backwards compatibility
        if user_id:
            repo.save_legacy_chat(user_id, user_message, state.final_response or "")

        return state

    def _synthesize_grounded_answer(self, state: AgentState, lang: str = "en") -> str:
        """
        Formulate a clear, grounded, professional response using verified tool results or RAG sources.
        """
        # 1. Multi-tool Duplicate Refund Workflow
        has_duplicate = any("duplicate" in tc.tool_name or (isinstance(tr.result, dict) and tr.result.get("duplicate_charge_flag")) for tc, tr in zip(state.tool_calls, state.tool_results))
        refund_call = next((tr for tr in state.tool_results if tr.tool_name == "create_refund_request"), None)
        ticket_call = next((tr for tr in state.tool_results if tr.tool_name == "create_support_ticket"), None)

        if refund_call and refund_call.success:
            ref_data = refund_call.result
            t_id = ticket_call.result.get("ticket_id") if ticket_call and ticket_call.success else "TICK-REF"
            if lang == "hi":
                return (
                    f"हमने आपके ऑर्डर **{ref_data['order_id']}** के लिए डुप्लीकेट कटौती की पुष्टि कर ली है। "
                    f"रिफंड अनुरोध **{ref_data['refund_id']}** राशि **₹{ref_data['amount']}** के लिए सफलतापूर्वक दर्ज कर दिया गया है। "
                    f"ट्रैकिंग टिकट **{t_id}** जनरेट किया गया है। राशि 3-5 कार्य दिवसों में आपके मूल भुगतान खाते में जमा कर दी जाएगी।"
                )
            return (
                f"We have verified your order **{ref_data['order_id']}** and confirmed the duplicate gateway charge. "
                f"Refund request **{ref_data['refund_id']}** has been created for **{ref_data.get('currency', 'INR')} {ref_data['amount']}**.\n\n"
                f"Support tracking Ticket **{t_id}** is active. Funds will credit back to your original payment method within **3 to 5 business days**."
            )

        # 2. Refund eligibility checked
        elig_call = next((tr for tr in state.tool_results if tr.tool_name == "check_refund_eligibility"), None)
        if elig_call and elig_call.success:
            el_data = elig_call.result
            if el_data.get("eligible"):
                return (
                    f"Good news! Your order **{el_data['order_id']}** is eligible for a full refund. "
                    f"Policy verification: {el_data['reason']}\n\n"
                    f"Would you like me to submit the refund request now?"
                )
            else:
                return (
                    f"Regarding order **{el_data['order_id']}**: {el_data['reason']}\n\n"
                    f"If you believe there are extenuating circumstances, I can escalate this to a supervisor."
                )

        # 3. Order details / Tracking lookup
        order_call = next((tr for tr in state.tool_results if tr.tool_name == "get_order_details"), None)
        if order_call:
            if not order_call.success or "error" in (order_call.result or {}):
                return f"I searched our order records, but could not locate the specified order. Please double-check the Order ID (e.g., ORD-1001)."
            ord_data = order_call.result
            trk = ord_data.get("tracking_number") or "Pending carrier dispatch"
            return (
                f"Here are the verified details for order **{ord_data['order_id']}**:\n\n"
                f"- **Item:** {ord_data['item_name']}\n"
                f"- **Status:** {ord_data['status'].title()}\n"
                f"- **Total Amount:** {ord_data['currency']} {ord_data['amount']}\n"
                f"- **Tracking ID:** `{trk}`\n"
                f"- **Delivery Address:** {ord_data['delivery_address']}"
            )

        # 4. RAG Knowledge Response
        if state.retrieved_documents:
            top_doc = state.retrieved_documents[0]
            if top_doc.score >= 0.20:
                answer = (
                    f"Based on our verified company policy:\n\n"
                    f"{top_doc.chunk}\n\n"
                    f"*Source: {top_doc.source} ({top_doc.section or 'Section 1'})*"
                )
                return answer
            else:
                return (
                    "I could not find enough verified information in our support knowledge base to answer this with certainty. "
                    "I can escalate this inquiry to our specialist support desk if you'd like."
                )

        # 5. Default polite response
        if lang == "hi":
            return "नमस्ते! मैं सपोर्ट एजेंट AI हूँ। मैं आपके ऑर्डर, रिफंड, या अन्य सहायता में कैसे मदद कर सकता हूँ?"
        return "Hello! I am SupportAgent AI. How can I assist you today with orders, returns, payments, or account questions?"


orchestrator = SupportAgentOrchestrator()
