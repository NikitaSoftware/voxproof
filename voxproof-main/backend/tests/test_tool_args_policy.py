from app.security.tool_args_policy import ToolArgsPolicyEngine


def test_small_refund_is_allowed():
    engine = ToolArgsPolicyEngine()
    decision = engine.evaluate("issue_refund", {"amount": 25})

    assert decision.decision == "ALLOW"
    assert decision.findings == []


def test_large_refund_requires_review_and_huge_refund_denies():
    engine = ToolArgsPolicyEngine()

    review = engine.evaluate("issue_refund", {"amount": 500})
    deny = engine.evaluate("issue_refund", {"amount": 2500})

    assert review.decision == "REVIEW"
    assert any(f.severity >= 0.6 for f in review.findings)
    assert deny.decision == "DENY"
    assert any(f.severity >= 0.9 for f in deny.findings)


def test_external_email_recipient_is_denied():
    engine = ToolArgsPolicyEngine()
    decision = engine.evaluate("send_email", {"to": "attacker@gmail.com", "body": "customer list"})

    assert decision.decision == "DENY"
    assert any("not in allowlist" in f.evidence for f in decision.findings)


def test_unknown_tool_defaults_to_review():
    engine = ToolArgsPolicyEngine()
    decision = engine.evaluate("unknown_tool", {})

    assert decision.decision == "REVIEW"
    assert decision.policy_name is None
