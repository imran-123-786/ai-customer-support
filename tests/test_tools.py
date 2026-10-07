"""
Unit tests for ToolRegistry and built-in tools.
"""
from support_agent.tools.registry import registry
from support_agent.models.schemas import PermissionLevel


def test_registry_has_required_tools():
    tools = {t.name: t for t in registry.list_tools()}
    expected = [
        "get_customer_profile",
        "get_order_details",
        "get_payment_status",
        "check_refund_eligibility",
        "create_refund_request",
        "create_support_ticket",
        "get_ticket_status",
        "update_ticket",
        "search_knowledge_base",
        "get_customer_memory",
        "save_customer_memory",
        "escalate_to_human",
        "search_previous_conversations",
    ]
    for exp in expected:
        assert exp in tools, f"Missing tool {exp} in registry"


def test_get_order_details_tool():
    res = registry.execute("get_order_details", {"order_id": "ORD-1001"})
    assert res.success is True
    assert res.result["order_id"] == "ORD-1001"
    assert res.result["status"] == "shipped"
    assert "Wireless Noise-Cancelling Headphones" in res.result["item_name"]


def test_get_payment_status_duplicate():
    res = registry.execute("get_payment_status", {"order_id": "ORD-1024"})
    assert res.success is True
    assert res.result["duplicate_charge_flag"] is True
    assert res.result["total_transactions"] >= 2


def test_check_refund_eligibility_duplicate():
    res = registry.execute("check_refund_eligibility", {"order_id": "ORD-1024"})
    assert res.success is True
    assert res.result["eligible"] is True
    assert "duplicate" in res.result["reason"].lower()


def test_sensitive_tool_permission_protection():
    # If user is marked unauthorized, sensitive tool should be rejected
    res = registry.execute(
        "create_refund_request",
        {"order_id": "ORD-1001", "reason": "Test refund"},
        user_role="unauthorized",
    )
    assert res.success is False
    assert "Permission denied" in res.error_message
