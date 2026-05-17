from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_get_api_auth_me_is_not_swallowed_by_spa_fallback():
    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()[0]["error"] == "Not authenticated"


def test_rag_demo_returns_findings_and_blocks_egress():
    response = client.post("/api/playground/rag_demo", json={})
    data = response.json()

    assert data["summary"]["total_findings"] >= 2
    assert data["summary"]["egress_allowed"] is False
    assert data["egress_blocked"]


def test_chat_tools_uses_tool_policy_for_refund_review():
    response = client.post("/api/playground/chat_tools", json={"message": "Issue a refund of $500"})
    data = response.json()

    tool = data["intercepted_tools"][0]
    assert tool["name"] == "issue_refund"
    assert tool["policy_decision"] == "REVIEW"
    assert tool["gate"] in {"NEEDS_REVIEW", "FAIL"}
