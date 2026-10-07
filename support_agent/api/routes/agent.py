"""
Agent and Evaluation API routes.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
try:
    from fastapi import APIRouter
except ImportError:
    APIRouter = None

from support_agent.database.repository import repo
from support_agent.evaluation.runner import evaluator
from support_agent.tools.registry import registry

if APIRouter:
    router = APIRouter(prefix="/agent", tags=["Agent Operations"])

    @router.get("/runs")
    def get_agent_runs(limit: int = 50):
        return repo.get_agent_runs(limit=limit)

    @router.get("/tools")
    def get_registered_tools():
        tools = registry.list_tools()
        return [
            {
                "name": t.name,
                "description": t.description,
                "permission": t.permission.value,
                "parameters": t.parameters_schema,
            }
            for t in tools
        ]

    @router.post("/eval")
    def run_benchmark():
        return evaluator.run_all()
else:
    router = None
