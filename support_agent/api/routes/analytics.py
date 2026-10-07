"""
Analytics and Telemetry API route.
"""
from __future__ import annotations

try:
    from fastapi import APIRouter
except ImportError:
    APIRouter = None

from support_agent.observability.logger import observability_manager

if APIRouter:
    router = APIRouter(prefix="/analytics", tags=["Analytics"])

    @router.get("")
    def get_analytics():
        return observability_manager.get_system_telemetry()
else:
    router = None
