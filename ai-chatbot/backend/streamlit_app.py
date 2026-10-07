"""
SupportAgent AI - Enterprise Agentic Customer Support & Agent-Assist Platform.
Features:
- Multi-step autonomous agent workflow with tool calling & state tracking
- RAG with verified citations
- Short-term conversation memory & rolling summarization
- Long-term persistent customer memory
- Human handoff briefings & escalation lifecycle
- AI Engineering & Failure Taxonomy debugging
- Benchmark evaluation studio
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import streamlit as st

from support_agent.agent.escalation import escalation_engine
from support_agent.agent.orchestrator import orchestrator
from support_agent.config import MAX_AGENT_STEPS, AGENT_PROMPT_VERSION, LLM_PROVIDER
from support_agent.database.connection import init_database
from support_agent.database.repository import repo
from support_agent.database.seed_data import seed_database
from support_agent.evaluation.runner import evaluator
from support_agent.memory.long_term import customer_memory
from support_agent.models.schemas import PermissionLevel
from support_agent.observability.logger import observability_manager
from support_agent.rag.retriever import retriever
from support_agent.rag.store import doc_store
from support_agent.security import hash_password, verify_password
from support_agent.tools.registry import registry

# Page configuration
st.set_page_config(
    page_title="SupportAgent AI — Agentic Support & Assist Desk",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


def local_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

        :root {
            --bg-top: #0a0f1d;
            --bg-bottom: #121c33;
            --card-bg: rgba(255, 255, 255, 0.05);
            --card-border: rgba(255, 255, 255, 0.12);
            --brand-primary: #38bdf8;
            --brand-accent: #818cf8;
            --brand-gold: #fbbf24;
            --success: #34d399;
            --danger: #f87171;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
        }

        * {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }

        code, pre, .mono {
            font-family: 'JetBrains Mono', monospace !important;
        }

        .stApp {
            background:
                radial-gradient(1200px 600px at 0% -10%, rgba(56, 189, 248, 0.15), transparent 60%),
                radial-gradient(1000px 600px at 100% 0%, rgba(129, 140, 248, 0.16), transparent 55%),
                linear-gradient(180deg, var(--bg-top), var(--bg-bottom));
            color: var(--text-main);
        }

        .top-shell {
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.12), rgba(129, 140, 248, 0.10));
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 18px 22px;
            margin-bottom: 14px;
            backdrop-filter: blur(12px);
        }

        .hero-title {
            font-size: 1.45rem;
            font-weight: 800;
            background: linear-gradient(90deg, #38bdf8, #818cf8, #fbbf24);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .hero-sub {
            color: var(--text-muted);
            font-size: 0.92rem;
            margin-top: 4px;
        }

        .badge-pill {
            display: inline-block;
            border-radius: 9999px;
            padding: 4px 12px;
            font-size: 0.78rem;
            font-weight: 600;
            border: 1px solid rgba(255, 255, 255, 0.18);
            background: rgba(255, 255, 255, 0.08);
            margin-right: 6px;
            margin-top: 6px;
        }

        .badge-active {
            background: rgba(56, 189, 248, 0.2);
            border-color: rgba(56, 189, 248, 0.5);
            color: #38bdf8;
        }

        .badge-tool {
            background: rgba(129, 140, 248, 0.2);
            border-color: rgba(129, 140, 248, 0.5);
            color: #a5b4fc;
        }

        .badge-escalate {
            background: rgba(248, 113, 113, 0.2);
            border-color: rgba(248, 113, 113, 0.5);
            color: #f87171;
        }

        .handoff-card {
            background: rgba(248, 113, 113, 0.08);
            border: 1px solid rgba(248, 113, 113, 0.35);
            border-radius: 14px;
            padding: 16px;
            margin-top: 10px;
            margin-bottom: 10px;
        }

        .handoff-header {
            font-weight: 700;
            color: #f87171;
            font-size: 0.95rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .stat-box {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 14px;
            padding: 16px;
            text-align: center;
            backdrop-filter: blur(8px);
        }

        .stat-num {
            font-size: 1.8rem;
            font-weight: 800;
            color: var(--brand-primary);
        }

        .stat-title {
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-top: 2px;
        }

        .stChatMessage {
            border: 1px solid var(--card-border);
            background: rgba(15, 23, 42, 0.7) !important;
            border-radius: 14px !important;
            padding: 14px !important;
        }

        .stButton > button {
            border-radius: 10px;
            font-weight: 600;
            border: 1px solid rgba(255, 255, 255, 0.15);
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(129, 140, 248, 0.25));
            color: #f1f5f9 !important;
            transition: all 0.2s ease;
        }

        .stButton > button:hover {
            border-color: var(--brand-primary);
            box-shadow: 0 0 14px rgba(56, 189, 248, 0.3);
            transform: translateY(-1px);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


local_css()

# Initialization
init_database()
seed_database(force=False)

# Session state initialization
if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_page" not in st.session_state:
    st.session_state.current_page = "desk"
if "session_start" not in st.session_state:
    st.session_state.session_start = time.time()
if "last_state" not in st.session_state:
    st.session_state.last_state = None


def normalize_user() -> None:
    u = st.session_state.user
    if isinstance(u, str):
        db_user = repo.get_user_by_username(u)
        st.session_state.user = db_user if db_user else None


normalize_user()


def top_shell(user: dict) -> None:
    c1, c2 = st.columns([10, 2])
    with c1:
        st.markdown(
            f"""
            <div class='top-shell'>
                <div class='hero-title'>SupportAgent AI — Command & Agent-Assist Desk</div>
                <div class='hero-sub'>
                    Active Operator: <b>{user['username']}</b> (Role: <i>{user.get('role', 'customer').title()}</i>) |
                    Autonomous Multi-Step Workflows | Grounded RAG Citations | Persistent Memory
                </div>
                <div>
                    <span class='badge-pill badge-active'>Model: {LLM_PROVIDER.upper()}</span>
                    <span class='badge-pill badge-tool'>Tools: {len(registry.list_tools())} Active</span>
                    <span class='badge-pill'>Knowledge Chunks: {len(doc_store.chunks)}</span>
                    <span class='badge-pill'>Version: {AGENT_PROMPT_VERSION}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        with st.popover("⚙️ Quick Menu", use_container_width=True):
            st.markdown("<b>Session Actions</b>", unsafe_allow_html=True)
            if st.button("🧹 Clear Conversation", use_container_width=True):
                st.session_state.messages = []
                st.session_state.last_state = None
                st.rerun()
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.user = None
                st.session_state.messages = []
                st.session_state.last_state = None
                st.rerun()


def render_nav() -> None:
    nav_items = [
        ("desk", "🎧 Support Desk"),
        ("tickets", "🎫 Ticket Center"),
        ("knowledge", "📚 Knowledge Hub (RAG)"),
        ("ops", "📊 Operations Dashboard"),
        ("debugging", "🔬 AI Engineering & Debug"),
        ("evaluation", "🧪 Evaluation Studio"),
        ("account", "👤 Account & Settings"),
    ]
    cols = st.columns(len(nav_items))
    for idx, (key, label) in enumerate(nav_items):
        is_active = st.session_state.current_page == key
        if cols[idx].button(label, use_container_width=True, type="primary" if is_active else "secondary"):
            st.session_state.current_page = key
            st.rerun()
    st.divider()


# ================= PAGE 1: Support Desk =================
def render_support_desk(user: dict) -> None:
    st.markdown("### 💬 Interactive Support Agent Desk")
    st.caption("Ask questions, run order workflows, verify refunds, or test human escalation.")

    # Interview Demo Scenarios Quick Actions
    st.markdown("**🎯 Quick Test Scenarios (Master Prompt Demos):**")
    p1, p2, p3, p4 = st.columns(4)
    if p1.button("📦 Order Tracking (ORD-1001)", use_container_width=True):
        handle_prompt(user, "Where is my order ORD-1001?")
        st.rerun()
    if p2.button("💳 Duplicate Charge (ORD-1024)", use_container_width=True):
        handle_prompt(user, "I was charged twice for ORD-1024 and I want a refund.")
        st.rerun()
    if p3.button("👤 Human Escalation", use_container_width=True):
        handle_prompt(user, "I've been trying for three days and nobody is helping me. Connect me to a human.")
        st.rerun()
    if p4.button("📜 Refund Policy (RAG)", use_container_width=True):
        handle_prompt(user, "What is your refund policy?")
        st.rerun()

    st.write("")

    # Chat message list
    for idx, m in enumerate(st.session_state.messages):
        avatar = "🧑" if m["role"] == "user" else "🤖"
        with st.chat_message(m["role"], avatar=avatar):
            st.markdown(m["content"])

            if m["role"] == "assistant":
                # Workflow pills
                pills = []
                if m.get("intent"):
                    pills.append(f"<span class='badge-pill badge-active'>Intent: {m['intent']}</span>")
                if m.get("priority"):
                    pills.append(f"<span class='badge-pill'>Priority: {m['priority']}</span>")
                if m.get("tools"):
                    for t in m["tools"]:
                        pills.append(f"<span class='badge-pill badge-tool'>Tool: {t}</span>")
                if m.get("escalated"):
                    pills.append("<span class='badge-pill badge-escalate'>Escalated to Human</span>")

                if pills:
                    st.markdown("".join(pills), unsafe_allow_html=True)

                # Citations Expander
                if m.get("citations"):
                    with st.expander("📚 Verified Knowledge Sources (RAG Citations)"):
                        for c in m["citations"]:
                            st.markdown(f"**Source:** `{c['source']}` — *{c.get('section', 'General')}* (Relevance: {c.get('score', 0.9)})")
                            st.caption(f"> \"{c.get('snippet', '')}\"")

                # Suggested Actions
                if m.get("suggested_actions"):
                    st.markdown("**Suggested Follow-Up Actions:**")
                    for act in m["suggested_actions"]:
                        st.markdown(f"- {act}")

                # CSAT feedback
                fc1, fc2, fc3, _ = st.columns([1, 1, 1, 5])
                if fc1.button("⭐ Helpful (5)", key=f"csat_5_{idx}"):
                    repo.add_feedback(conversation_id=m.get("conv_id", "demo"), csat_score=5)
                    st.toast("Thank you for your rating! Recorded CSAT: 5/5")
                if fc2.button("😐 Partial (3)", key=f"csat_3_{idx}"):
                    repo.add_feedback(conversation_id=m.get("conv_id", "demo"), csat_score=3)
                    st.toast("Recorded CSAT: 3/5")
                if fc3.button("👎 Poor (1)", key=f"csat_1_{idx}"):
                    repo.add_feedback(conversation_id=m.get("conv_id", "demo"), csat_score=1)
                    st.toast("Recorded CSAT: 1/5")

    if prompt := st.chat_input("Ask a question, enter an order ID, or describe your issue..."):
        handle_prompt(user, prompt)
        st.rerun()


def handle_prompt(user: dict, prompt: str) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Prepare history for context
    history = [
        {"role": m["role"], "text": m["content"]}
        for m in st.session_state.messages[-10:]
    ]

    cust = repo.get_customer_by_user_id(user["id"])
    customer_id = cust["id"] if cust else "CUST-104"

    # Execute orchestrator
    state = orchestrator.run(
        user_message=prompt,
        customer_id=customer_id,
        user_id=user["id"],
        history=history,
    )
    st.session_state.last_state = state

    tools_used = [tc.tool_name for tc in state.tool_calls]

    st.session_state.messages.append({
        "role": "assistant",
        "content": state.final_response or "Your request has been processed.",
        "intent": state.intent,
        "emotion": state.emotion,
        "priority": state.priority,
        "tools": tools_used,
        "escalated": state.escalation_required,
        "citations": state.citations,
        "suggested_actions": state.suggested_actions,
        "conv_id": state.conversation_id,
    })


# ================= PAGE 2: Ticket Center =================
def render_tickets(user: dict) -> None:
    st.markdown("### 🎫 Ticket Center & Human Handoff Dashboard")
    st.caption("Inspect support tickets, status timelines, and human-assist handoff briefings.")

    tickets = repo.list_tickets()
    if not tickets:
        st.info("No tickets currently logged.")
        return

    for t in tickets:
        is_esc = bool(t.get("escalated"))
        icon = "🚨" if is_esc else "🎫"
        title = f"{icon} {t['id']} — {t['topic']} [{t['priority']} Priority | Status: {t['status']}]"

        with st.expander(title, expanded=is_esc and t["status"] == "Open"):
            c1, c2 = st.columns([8, 4])
            with c1:
                st.markdown(f"**Intent Category:** {t['intent']}")
                st.markdown(f"**Created At:** {t['created_at']}")
                st.markdown(f"**Customer ID:** `{t.get('customer_id') or 'N/A'}`")
                if t.get("escalation_reason"):
                    st.error(f"**Escalation Trigger:** {t['escalation_reason']}")

                # Human Handoff Summary
                if t.get("handoff_summary"):
                    st.markdown(
                        f"""
                        <div class='handoff-card'>
                            <div class='handoff-header'>📋 Human Agent Handoff Briefing</div>
                            <pre style='white-space: pre-wrap; font-size: 0.85rem; margin-top: 8px;'>{t['handoff_summary']}</pre>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            with c2:
                current_stat = t["status"]
                stat_options = ["Open", "In Progress", "Waiting", "Resolved", "Closed"]
                stat_idx = stat_options.index(current_stat) if current_stat in stat_options else 0
                new_status = st.selectbox("Update Status", stat_options, index=stat_idx, key=f"sel_{t['id']}")
                notes = st.text_input("Resolution / Agent Notes", key=f"note_{t['id']}")
                if st.button("💾 Save Status Update", key=f"btn_{t['id']}", use_container_width=True):
                    repo.update_ticket_status(t["id"], new_status, notes)
                    st.success(f"Ticket {t['id']} updated to {new_status}")
                    st.rerun()

            # Event timeline
            events = repo.get_ticket_events(t["id"])
            if events:
                st.markdown("**Lifecycle Events Timeline:**")
                for e in events:
                    st.caption(f"⏱️ `{e['timestamp']}` — **{e['event_type']}**: {e.get('details', '')}")


# ================= PAGE 3: Knowledge Hub =================
def render_knowledge(user: dict) -> None:
    st.markdown("### 📚 Knowledge Hub & Verified RAG Store")
    st.caption("Upload policy documents (PDF, TXT, MD, CSV, JSON) and test semantic knowledge retrieval.")

    col1, col2 = st.columns([6, 6])
    with col1:
        st.markdown("#### Upload Company Knowledge")
        uploaded = st.file_uploader("Upload policy documentation", type=["pdf", "md", "txt", "csv", "json"])
        if uploaded and st.button("📥 Index into RAG Store", use_container_width=True):
            with st.spinner("Parsing and chunking with metadata..."):
                chunk_count = doc_store.add_document_content(uploaded.name, uploaded.getvalue())
            st.success(f"Indexed {chunk_count} verified chunks from '{uploaded.name}'!")
            st.rerun()

        st.info(f"**Total Verified Knowledge Chunks in Store:** {len(doc_store.chunks)}")

    with col2:
        st.markdown("#### Live RAG Retrieval Tester")
        query = st.text_input("Test search query:", value="What is the refund window?")
        if query:
            hits = retriever.search(query, top_k=4)
            st.markdown(f"**Retrieved Chunks ({len(hits)} hits):**")
            for h in hits:
                st.markdown(f"- **{h.source}** (Section: *{h.section}*) — Score: `{h.score}`")
                st.caption(f"> \"{h.chunk[:240]}...\"")


# ================= PAGE 4: Operations Dashboard =================
def render_operations(user: dict) -> None:
    st.markdown("### 📊 Enterprise Support Operations Dashboard")
    st.caption("Real-time operational KPIs, tool execution metrics, and ticket queue analytics.")

    telemetry = observability_manager.get_system_telemetry()
    tickets = repo.list_tickets()
    open_tickets = sum(1 for t in tickets if t["status"] == "Open")
    critical_tickets = sum(1 for t in tickets if t["priority"] in ("High", "Critical"))

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='stat-box'><div class='stat-num'>{telemetry['resolution_rate']}%</div><div class='stat-title'>AI Resolution Rate</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='stat-box'><div class='stat-num'>{open_tickets}</div><div class='stat-title'>Open Tickets</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='stat-box'><div class='stat-num'>{critical_tickets}</div><div class='stat-title'>High / Critical Cases</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='stat-box'><div class='stat-num'>{telemetry['tool_success_rate']}%</div><div class='stat-title'>Tool Execution Success</div></div>", unsafe_allow_html=True)

    st.write("")
    c5, c6, c7, c8 = st.columns(4)
    c5.markdown(f"<div class='stat-box'><div class='stat-num'>{telemetry['total_runs']}</div><div class='stat-title'>Total Agent Runs</div></div>", unsafe_allow_html=True)
    c6.markdown(f"<div class='stat-box'><div class='stat-num'>{telemetry['escalation_count']}</div><div class='stat-title'>Escalations Handed Off</div></div>", unsafe_allow_html=True)
    c7.markdown(f"<div class='stat-box'><div class='stat-num'>{telemetry['avg_tool_latency_ms']} ms</div><div class='stat-title'>Avg Tool Latency</div></div>", unsafe_allow_html=True)
    c8.markdown(f"<div class='stat-box'><div class='stat-num'>{telemetry['avg_csat']} / 5.0</div><div class='stat-title'>Average CSAT Rating</div></div>", unsafe_allow_html=True)

    st.write("")
    st.markdown("#### Recent Live Agent Executions")
    runs = repo.get_agent_runs(limit=10)
    if runs:
        for r in runs:
            esc_badge = "🚨 Escalated" if r.get("escalated") else "✅ Solved"
            st.markdown(
                f"**{r['start_time']}** | `{r['id']}` | **Intent:** {r['intent']} | **Priority:** {r['priority']} | "
                f"**Steps:** {r['steps_count']} | **Tools:** {r['tools_called_count']} | **Latency:** {r['latency_ms']} ms | **Status:** {esc_badge}"
            )
            st.caption(f"Customer query: \"{r['user_message']}\"")


# ================= PAGE 5: AI Engineering & Debugging =================
def render_debugging(user: dict) -> None:
    st.markdown("### 🔬 AI Engineering & Failure Taxonomy Debugger")
    st.caption("Inspect agent steps, failure classifications, tool inputs/outputs, and customer memory state.")

    tab1, tab2, tab3, tab4 = st.tabs(["Failure Taxonomy Breakdown", "Tool Call Payloads", "Customer Memory State", "Prompt Engine"])

    with tab1:
        st.markdown("#### AI Failure Taxonomy Classification")
        telemetry = observability_manager.get_system_telemetry()
        breakdown = telemetry.get("failure_breakdown", {})
        if not breakdown:
            st.success("Zero unhandled system failures recorded! All agent runs converged or gracefully escalated.")
        else:
            for cat, count in breakdown.items():
                st.warning(f"**{cat}**: {count} occurrences")

        st.markdown("#### Failure Taxonomy Categories:")
        st.markdown("""
        - `MODEL_FAILURE`: Non-convergent generation or ungrounded responses.
        - `PROMPT_FAILURE`: Ambiguous instruction compliance.
        - `CONTEXT_FAILURE`: Token budget overflow or dropped state.
        - `RETRIEVAL_FAILURE`: RAG returned zero verified chunks (< 0.20 threshold).
        - `TOOL_FAILURE`: Tool execution exception, foreign key or database error.
        - `PARSING_FAILURE`: Invalid JSON structure in model decision.
        - `APPLICATION_FAILURE`: Maximum agent iterations reached without resolution.
        """)

    with tab2:
        st.markdown("#### Tool Call Audit Log & Latency Telemetry")
        tool_calls = repo.get_tool_calls(limit=15)
        if tool_calls:
            for tc in tool_calls:
                with st.expander(f"Tool `{tc['tool_name']}` — Latency: {tc['latency_ms']} ms (Success: {bool(tc['success'])})"):
                    st.write(f"**Timestamp:** {tc['timestamp']}")
                    st.write("**Input Payload:**")
                    st.code(tc["input_json"], language="json")
                    st.write("**Output Payload:**")
                    st.code(tc["output_json"] or "{}", language="json")
                    if tc.get("error_message"):
                        st.error(f"Error: {tc['error_message']}")

    with tab3:
        st.markdown("#### Persistent Long-Term Customer Memory Store")
        cust_id = st.text_input("Inspect Customer ID:", value="CUST-101")
        if cust_id:
            mems = customer_memory.get_memories(cust_id)
            if mems:
                for m in mems:
                    st.markdown(f"- **{m.memory_type}** (`{m.key}`): *{m.value}* (Confidence: {m.confidence})")
            else:
                st.info(f"No persistent memories stored for {cust_id} yet.")

    with tab4:
        st.markdown("#### Versioned Prompt Templates")
        st.markdown(f"**Current Prompt Version:** `{AGENT_PROMPT_VERSION}`")
        prompt_choice = st.selectbox(
            "Select Prompt to Inspect:",
            ["system_agent.txt", "tool_selection.txt", "memory_extraction.txt", "summarization.txt", "rag_answer.txt", "escalation.txt"]
        )
        from support_agent.config import PACKAGE_ROOT
        prompt_file = PACKAGE_ROOT / "prompts" / prompt_choice
        if prompt_file.exists():
            st.code(prompt_file.read_text(encoding="utf-8"), language="text")


# ================= PAGE 6: Evaluation Studio =================
def render_evaluation(user: dict) -> None:
    st.markdown("### 🧪 Evaluation Studio — 25 Support Scenarios Benchmark")
    st.caption("Run automated benchmark evaluations across intent, tool selection, retrieval relevance, and escalation.")

    latest = repo.get_latest_evaluation()

    if st.button("🚀 Run Full Benchmark Suite (25 Cases)", type="primary", use_container_width=True):
        with st.spinner("Running 25 benchmark scenarios against SupportAgent AI..."):
            metrics = evaluator.run_all()
        st.success("Benchmark evaluation completed!")
        latest = repo.get_latest_evaluation()

    if latest:
        m = latest.get("metrics", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='stat-box'><div class='stat-num'>{m.get('overall_accuracy_percent', 0)}%</div><div class='stat-title'>Overall Accuracy</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='stat-box'><div class='stat-num'>{m.get('intent_accuracy_percent', 0)}%</div><div class='stat-title'>Intent Accuracy</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='stat-box'><div class='stat-num'>{m.get('tool_accuracy_percent', 0)}%</div><div class='stat-title'>Tool Selection Accuracy</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='stat-box'><div class='stat-num'>{m.get('escalation_accuracy_percent', 0)}%</div><div class='stat-title'>Escalation Accuracy</div></div>", unsafe_allow_html=True)

        st.write("")
        st.markdown(f"**Last Run Timestamp:** `{latest['timestamp']}` | **Passed Cases:** {latest['passed_cases']} / {latest['total_cases']}")

        with st.expander("Detailed Breakdown by Test Case", expanded=True):
            cases = m.get("case_results", [])
            for c in cases:
                badge = "✅ PASS" if c["passed"] else "❌ FAIL"
                st.markdown(
                    f"**{c['id']}**: {c['name']} — {badge} | Intent: {c['intent_match']} | Tool: {c['tool_match']} | "
                    f"Escalation: {c['escalation_match']} | RAG: {c['retrieval_match']}"
                )
                if not c["passed"]:
                    st.caption(f"Detected Intent: {c['detected_intent']} | Tools: {c['tools_executed']}")


# ================= PAGE 7: Account & Settings =================
def render_account(user: dict) -> None:
    st.markdown("### 👤 Account Profile & System Preferences")
    st.caption("Manage operator settings, preferred response language, and model configuration.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### User Information")
        st.markdown(f"- **Username:** `{user['username']}`")
        st.markdown(f"- **User Role:** `{user.get('role', 'customer')}`")
        st.markdown(f"- **User ID:** `{user['id']}`")
        cust = repo.get_customer_by_user_id(user["id"])
        if cust:
            st.markdown(f"- **Customer ID:** `{cust['id']}`")
            st.markdown(f"- **Customer Tier:** `{cust['tier']}`")

        settings = repo.get_user_settings(user["id"])
        lang_opts = ["auto", "en", "hi", "bn"]
        cur_lang = settings.get("preferred_language", "auto")
        lang_idx = lang_opts.index(cur_lang) if cur_lang in lang_opts else 0
        new_lang = st.selectbox("Preferred Communication Language", lang_opts, index=lang_idx)
        voice = st.toggle("Voice-optimized output format", bool(settings.get("voice_enabled", 0)))
        if st.button("Save User Settings", use_container_width=True):
            repo.update_user_settings(user["id"], new_lang, 1 if voice else 0)
            st.success("Settings saved successfully!")

    with c2:
        st.markdown("#### AI Agent Engine Settings")
        st.info(f"**Current LLM Provider:** `{LLM_PROVIDER}`")
        st.markdown(f"- **Max Agent Loop Iterations:** `{MAX_AGENT_STEPS}`")
        st.markdown(f"- **Prompt Template Version:** `{AGENT_PROMPT_VERSION}`")
        st.markdown(f"- **Grounding Confidence Threshold:** `0.60`")
        st.markdown(f"- **RAG Document Chunks:** `{len(doc_store.chunks)}`")


# ================= Authentication Page =================
def render_login_page() -> None:
    st.markdown(
        """
        <div style='text-align:center; padding: 30px 0 10px 0;'>
            <div style='font-size: 64px;'>🤖</div>
            <h1 style='margin-bottom: 4px; font-weight: 800;'>SupportAgent AI</h1>
            <p style='color: #94a3b8; font-size: 1.05rem;'>Production-Grade Agentic Customer Support & Agent-Assist Platform</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([1, 1.4, 1])
    with c2:
        tab_login, tab_reg = st.tabs(["Operator Login", "Register New User"])

        with tab_login:
            username = st.text_input("Username", key="l_user")
            password = st.text_input("Password", type="password", key="l_pass")
            if st.button("Sign In to SupportAgent", use_container_width=True):
                db_user = repo.get_user_by_username(username.strip())
                if db_user and verify_password(password, db_user["password_hash"]):
                    st.session_state.user = db_user
                    st.session_state.session_start = time.time()
                    st.rerun()
                st.error("Invalid username or password.")

        with tab_reg:
            new_u = st.text_input("New Username", key="r_user")
            new_p = st.text_input("New Password", type="password", key="r_pass")
            if st.button("Create Account", use_container_width=True):
                if new_u and new_p:
                    uid = repo.create_user(new_u.strip(), hash_password(new_p))
                    if uid:
                        st.session_state.user = repo.get_user_by_id(uid)
                        st.rerun()
                    st.error("Username already exists.")

        st.info("Demo Operator Accounts: `admin / admin123` or `student / 1234`")


# ================= Application Router =================
if st.session_state.user is None:
    render_login_page()
else:
    user = st.session_state.user
    top_shell(user)
    render_nav()

    page = st.session_state.current_page
    if page == "desk":
        render_support_desk(user)
    elif page == "tickets":
        render_tickets(user)
    elif page == "knowledge":
        render_knowledge(user)
    elif page == "ops":
        render_operations(user)
    elif page == "debugging":
        render_debugging(user)
    elif page == "evaluation":
        render_evaluation(user)
    elif page == "account":
        render_account(user)
