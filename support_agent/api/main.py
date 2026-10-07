"""
SupportAgent AI - FastAPI Application Server.
Exposes REST endpoints for Chat, Tickets, Agent Telemetry, Documents, and Evaluation.
"""
from __future__ import annotations

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from support_agent.api.routes import agent, analytics, chat, documents, tickets

    app = FastAPI(
        title="SupportAgent AI API",
        version="2.0.0",
        description="Production Agentic Customer Support & Agent-Assist API Platform",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat.router, prefix="/api")
    app.include_router(tickets.router, prefix="/api")
    app.include_router(agent.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(analytics.router, prefix="/api")

    @app.get("/health")
    def health_check():
        return {"status": "healthy", "service": "SupportAgent AI", "version": "2.0.0"}

except ImportError:
    app = None
