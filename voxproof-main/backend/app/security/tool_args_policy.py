"""Tool argument policy engine.

Replaces the ad-hoc `HIGH_RISK_TOOLS` set with a real policy DSL that supports:
- Action: ALLOW / REVIEW / DENY
- Amount limits with REVIEW band and DENY ceiling
- Recipient allowlist (refunds must go to same payment method, exports forbidden)
- Bulk-export blocks
- Audit-evidence reasoning

References:
- OWASP LLM06:2025 — Excessive Agency
- Imprompter (arXiv:2410.14923) — tool-call poisoning via indirect injection
- AgentDojo benchmark — tool-call adversarial robustness
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.schemas import Finding, Boundary, RiskType


@dataclass
class ToolPolicy:
    name: str
    action: str  # "ALLOW" | "REVIEW" | "DENY"
    amount_field: str | None = None
    amount_review_above: float = 0.0
    amount_deny_above: float | None = None
    recipient_field: str | None = None
    recipient_allowlist: list[str] = field(default_factory=list)
    bulk_export_blocked: bool = False
    bulk_indicator_fields: list[str] = field(default_factory=list)
    reason: str = ""
    owasp_ref: str = ""


# Default policies for the FinanceSupportBot demo
DEFAULT_POLICIES: list[ToolPolicy] = [
    ToolPolicy(
        name="lookup_account",
        action="ALLOW",
        reason="Read-only account lookup is safe for verified callers",
    ),
    ToolPolicy(
        name="issue_refund",
        action="ALLOW",
        amount_field="amount",
        amount_review_above=100.0,
        amount_deny_above=2000.0,
        reason="Refunds >$100 require manager approval; >$2000 must use bank's authenticated channel",
        owasp_ref="LLM06:2025 Excessive Agency",
    ),
    ToolPolicy(
        name="approve_wire_transfer",
        action="DENY",
        reason="Wire transfers must use bank's authenticated channel (not voice agent) — Arup $25.6M lesson",
        owasp_ref="LLM06:2025 Excessive Agency",
    ),
    ToolPolicy(
        name="mark_identity_verified",
        action="DENY",
        reason="Identity verification cannot be bypassed via voice agent — defeats KYC/AML",
        owasp_ref="LLM06:2025 Excessive Agency",
    ),
    ToolPolicy(
        name="set_credit_limit",
        action="DENY",
        reason="Credit limit changes require credit officer + signed agreement",
        owasp_ref="LLM06:2025 Excessive Agency",
    ),
    ToolPolicy(
        name="export_customer_emails",
        action="DENY",
        bulk_export_blocked=True,
        bulk_indicator_fields=["filter", "scope", "query"],
        reason="Bulk customer data export requires compliance approval (GDPR Art.32, SOC2 CC6)",
        owasp_ref="LLM02:2025 Sensitive Information Disclosure",
    ),
    ToolPolicy(
        name="reset_mfa",
        action="DENY",
        reason="MFA reset over voice channel is the Retool/MGM attack vector — must use in-person or pre-registered channel",
        owasp_ref="LLM06:2025 Excessive Agency",
    ),
    ToolPolicy(
        name="send_email",
        action="REVIEW",
        recipient_field="to",
        recipient_allowlist=["@bank.internal", "@compliance.internal"],
        reason="Outbound email must go to verified internal recipients",
        owasp_ref="LLM02:2025 Sensitive Information Disclosure",
    ),
]


SUSPICIOUS_RECIPIENT_RE = re.compile(
    r'(@(?:gmail|yahoo|protonmail|proton|outlook|hotmail|temp-mail|guerrillamail|mailinator|outside)\.)'
    r'|webhook|attacker',
    re.IGNORECASE,
)


@dataclass
class PolicyDecision:
    decision: str  # ALLOW / REVIEW / DENY
    findings: list[Finding]
    policy_name: str | None = None
    reason: str = ""


class ToolArgsPolicyEngine:
    """Evaluates tool calls against a policy registry. Returns decision + findings."""

    def __init__(self, policies: list[ToolPolicy] | None = None):
        self._policies = {p.name: p for p in (policies or DEFAULT_POLICIES)}

    def list_policies(self) -> list[dict]:
        return [{
            "name": p.name,
            "action": p.action,
            "amount_review_above": p.amount_review_above,
            "amount_deny_above": p.amount_deny_above,
            "reason": p.reason,
            "owasp_ref": p.owasp_ref,
        } for p in self._policies.values()]

    def evaluate(self, tool_name: str, tool_args: dict) -> PolicyDecision:
        policy = self._policies.get(tool_name)

        if not policy:
            return PolicyDecision(
                decision="REVIEW",
                policy_name=None,
                reason=f"Tool '{tool_name}' has no registered policy",
                findings=[Finding(
                    boundary=Boundary.TOOL_EXECUTION,
                    risk=RiskType.UNSAFE_TOOL_CALL,
                    severity=0.70,
                    evidence=f"Tool policy: '{tool_name}' not in registry — default HUMAN_REVIEW (deny-by-default principle)",
                )],
            )

        findings: list[Finding] = []
        decision = policy.action

        # Base policy action
        if policy.action == "DENY":
            findings.append(Finding(
                boundary=Boundary.TOOL_EXECUTION,
                risk=RiskType.UNSAFE_TOOL_CALL,
                severity=0.95,
                evidence=f"Tool policy DENY: '{tool_name}' — {policy.reason}",
            ))

        # Amount band check
        if policy.amount_field:
            raw = tool_args.get(policy.amount_field, 0) or tool_args.get("amount", 0) or tool_args.get("value", 0)
            try:
                amount = float(raw)
            except (TypeError, ValueError):
                amount = 0.0
            if policy.amount_deny_above is not None and amount > policy.amount_deny_above:
                decision = "DENY"
                findings.append(Finding(
                    boundary=Boundary.TOOL_ARGUMENT,
                    risk=RiskType.HIGH_RISK_ACTION,
                    severity=0.90,
                    evidence=f"Tool '{tool_name}' amount ${amount:.0f} exceeds DENY ceiling ${policy.amount_deny_above:.0f} — {policy.reason}",
                ))
            elif amount > policy.amount_review_above:
                if decision == "ALLOW":
                    decision = "REVIEW"
                findings.append(Finding(
                    boundary=Boundary.TOOL_ARGUMENT,
                    risk=RiskType.HIGH_RISK_ACTION,
                    severity=0.65,
                    evidence=f"Tool '{tool_name}' amount ${amount:.0f} exceeds REVIEW threshold ${policy.amount_review_above:.0f} — {policy.reason}",
                ))

        # Recipient allowlist
        if policy.recipient_field:
            raw_recipient = str(tool_args.get(policy.recipient_field, ""))
            if policy.recipient_allowlist and not self._recipient_allowed(raw_recipient, policy.recipient_allowlist):
                decision = "DENY"
                findings.append(Finding(
                    boundary=Boundary.TOOL_ARGUMENT,
                    risk=RiskType.DATA_EXFILTRATION,
                    severity=0.88,
                    evidence=f"Tool '{tool_name}' recipient '{raw_recipient}' not in allowlist {policy.recipient_allowlist} — potential exfil destination",
                ))
            elif SUSPICIOUS_RECIPIENT_RE.search(raw_recipient):
                decision = "DENY"
                findings.append(Finding(
                    boundary=Boundary.TOOL_ARGUMENT,
                    risk=RiskType.DATA_EXFILTRATION,
                    severity=0.92,
                    evidence=f"Tool '{tool_name}' recipient '{raw_recipient}' matches suspicious-domain pattern (external email / webhook / attacker)",
                ))

        # Bulk export indicator
        if policy.bulk_export_blocked:
            args_str = str(tool_args).lower()
            if any(token in args_str for token in ["all", "bulk", "*", "every", "every customer"]):
                decision = "DENY"
                findings.append(Finding(
                    boundary=Boundary.TOOL_ARGUMENT,
                    risk=RiskType.DATA_EXFILTRATION,
                    severity=0.93,
                    evidence=f"Tool '{tool_name}' has bulk-scope arguments — {policy.reason}",
                ))

        return PolicyDecision(
            decision=decision,
            findings=findings,
            policy_name=policy.name,
            reason=policy.reason,
        )

    def _recipient_allowed(self, recipient: str, allowlist: list[str]) -> bool:
        recipient_l = recipient.lower().strip()
        for allowed in allowlist:
            allowed_l = allowed.lower().strip()
            if allowed_l.startswith("@") and recipient_l.endswith(allowed_l):
                return True
            if recipient_l == allowed_l:
                return True
        return False
