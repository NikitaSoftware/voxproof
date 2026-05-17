import json
import re
import subprocess
import shutil
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from app.schemas import Finding, Boundary, RiskType
from app.security.boundary_engine import BoundaryEngine
from app.config import LOBSTER_POLICIES_DIR


_RULE_TO_RISK: dict[str, RiskType] = {
    "block_data_exfiltration": RiskType.DATA_EXFILTRATION,
    "flag_prompt_injection": RiskType.PROMPT_INJECTION,
    "flag_auth_bypass": RiskType.AUTH_BYPASS,
    "flag_system_prompt_extraction": RiskType.SYSTEM_PROMPT_EXTRACTION,
    "flag_high_risk_action": RiskType.HIGH_RISK_ACTION,
    "flag_social_engineering": RiskType.SOCIAL_ENGINEERING,
    "flag_credit_manipulation": RiskType.HIGH_RISK_ACTION,
    "flag_indirect_prompt_injection": RiskType.PROMPT_INJECTION,
    "flag_tool_result_injection": RiskType.PROMPT_INJECTION,
    "flag_external_egress_channel": RiskType.DATA_EXFILTRATION,
    "flag_audio_covert_instruction": RiskType.ADVERSARIAL_AUDIO,
}

_RULE_TO_BOUNDARY: dict[str, Boundary] = {
    "block_data_exfiltration": Boundary.EGRESS,
    "flag_prompt_injection": Boundary.USER_INPUT,
    "flag_auth_bypass": Boundary.USER_INPUT,
    "flag_system_prompt_extraction": Boundary.AGENT_RESPONSE,
    "flag_high_risk_action": Boundary.TOOL_ARGUMENT,
    "flag_social_engineering": Boundary.USER_INPUT,
    "flag_credit_manipulation": Boundary.TOOL_ARGUMENT,
    "flag_indirect_prompt_injection": Boundary.UNTRUSTED_CONTEXT,
    "flag_tool_result_injection": Boundary.UNTRUSTED_CONTEXT,
    "flag_external_egress_channel": Boundary.EGRESS,
    "flag_audio_covert_instruction": Boundary.AUDIO_LAYER,
}

_ACTION_SEVERITY: dict[str, float] = {
    "DENY": 0.92,
    "QUARANTINE": 0.88,
    "HUMAN_REVIEW": 0.62,
    "LOG": 0.35,
    "ALLOW": 0.0,
}

_ACTION_PRIORITY = ["DENY", "QUARANTINE", "HUMAN_REVIEW", "LOG", "ALLOW"]

# Lobster Trap binary boolean flags → Finding mapping
_LOBSTER_FLAG_MAP = {
    "contains_injection_patterns": (RiskType.PROMPT_INJECTION, Boundary.USER_INPUT, 0.88, "DENY"),
    "contains_exfiltration": (RiskType.DATA_EXFILTRATION, Boundary.EGRESS, 0.92, "DENY"),
    "contains_role_impersonation": (RiskType.SOCIAL_ENGINEERING, Boundary.USER_INPUT, 0.75, "HUMAN_REVIEW"),
    "contains_phishing_patterns": (RiskType.SOCIAL_ENGINEERING, Boundary.USER_INPUT, 0.72, "HUMAN_REVIEW"),
    "contains_malware_request": (RiskType.UNSAFE_TOOL_CALL, Boundary.TOOL_EXECUTION, 0.95, "DENY"),
    "contains_system_commands": (RiskType.UNSAFE_TOOL_CALL, Boundary.TOOL_ARGUMENT, 0.80, "DENY"),
    "contains_pii_request": (RiskType.DATA_EXFILTRATION, Boundary.EGRESS, 0.65, "HUMAN_REVIEW"),
}


@dataclass
class LobsterInspectResult:
    raw_output: str = ""
    action: str = ""
    rule: str = ""
    findings: list[Finding] = field(default_factory=list)


class LobsterAdapter:
    def __init__(self, lobster_binary: str = "lobstertrap", boundary_engine: BoundaryEngine = None):
        self.lobster_binary = lobster_binary
        self.boundary_engine = boundary_engine or BoundaryEngine()
        self._available = shutil.which(lobster_binary) is not None
        self._policy_rules = self._load_policy_rules()

    def _load_policy_rules(self) -> list[dict]:
        policy_path = Path(LOBSTER_POLICIES_DIR) / "lobster_finance.yaml"
        if not policy_path.exists():
            return []
        try:
            with open(policy_path) as f:
                data = yaml.safe_load(f)
            rules = data.get("rules", [])
            if not rules:
                for rule in data.get("ingress_rules", []):
                    conditions = rule.get("conditions", [])
                    patterns = [
                        c["value"] for c in conditions
                        if c.get("field") == "prompt_text" and "value" in c
                    ]
                    action = rule.get("action", "LOG")
                    actions = [action] if action == "LOG" else [action, "LOG"]
                    rules.append({
                        "name": rule.get("name", ""),
                        "description": rule.get("description", ""),
                        "patterns": patterns,
                        "actions": actions,
                    })
            return rules
        except Exception:
            return []

    @property
    def available(self) -> bool:
        return self._available

    def inspect_transcript(self, text: str, policy: str = None) -> LobsterInspectResult:
        binary_findings: list[Finding] = []
        binary_action = "ALLOW"
        binary_rule = ""
        binary_raw = ""

        if self._available:
            try:
                policy_path = policy or str(Path(LOBSTER_POLICIES_DIR) / "lobster_finance.yaml")
                args = [self.lobster_binary, "inspect", "--policy", policy_path, text]
                result = subprocess.run(args, capture_output=True, text=True, timeout=10)
                raw = result.stdout.strip()
                # Extract JSON portion from binary output (may contain header text)
                json_start = raw.find('{')
                if json_start >= 0:
                    binary_raw = raw[json_start:]
                    parsed = self._parse_lobster_binary_output(binary_raw)
                    if parsed is not None:
                        binary_findings = parsed.findings
                        binary_action = parsed.action
                        binary_rule = parsed.rule
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        # Always run regex policy inspection — Lobster Trap binary uses its own NLP,
        # we complement with our finance-domain regex rules
        policy_result = self._policy_inspect(text)

        # Merge findings from binary + Python regex
        all_findings = list(binary_findings) + list(policy_result.findings)

        # Take strictest action across both sources
        all_actions = [binary_action, policy_result.action]
        primary_action = next((a for a in _ACTION_PRIORITY if a in all_actions), "ALLOW")

        if not all_findings:
            return LobsterInspectResult(
                raw_output=binary_raw or '{"action":"ALLOW"}',
                action="ALLOW",
                findings=[],
            )

        return LobsterInspectResult(
            raw_output=binary_raw or policy_result.raw_output,
            action=primary_action,
            rule=binary_rule or policy_result.rule,
            findings=all_findings,
        )

    def _parse_lobster_binary_output(self, raw: str) -> LobsterInspectResult | None:
        """Parse Lobster Trap binary JSON output including NLP boolean flags."""
        if not raw:
            return None
        try:
            data = json.loads(raw)
            action = data.get("action", "ALLOW")
            rule = data.get("rule", data.get("matched_rule", ""))
            risk_score = float(data.get("risk_score", 0) or 0)

            findings = []

            # Map binary NLP boolean flags → security findings
            for flag, (risk, boundary, base_sev, decision) in _LOBSTER_FLAG_MAP.items():
                if data.get(flag):
                    severity = max(risk_score, base_sev * 0.9) if risk_score > 0 else base_sev
                    findings.append(Finding(
                        boundary=boundary,
                        risk=risk,
                        severity=severity,
                        evidence=f"Lobster Trap NLP [{decision}]: {flag.replace('_', ' ')} detected",
                        lobster_decision=decision,
                    ))

            # Standard rule-based finding when binary returns non-ALLOW with rule
            if action != "ALLOW" and rule:
                severity = _ACTION_SEVERITY.get(action, risk_score or 0.5)
                risk = _RULE_TO_RISK.get(rule, RiskType.UNSAFE_TOOL_CALL)
                findings.append(Finding(
                    boundary=_RULE_TO_BOUNDARY.get(rule, Boundary.POLICY_GAP),
                    risk=risk,
                    severity=severity,
                    evidence=f"Lobster Trap [{action}]: rule '{rule}' — risk_score={risk_score:.2f}",
                    lobster_decision=action,
                ))

            return LobsterInspectResult(raw_output=raw, action=action, rule=rule, findings=findings)
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def _parse_lobster_output(self, raw: str) -> LobsterInspectResult | None:
        """Legacy parser — kept for compatibility."""
        return self._parse_lobster_binary_output(raw)

    def _policy_inspect(self, text: str) -> LobsterInspectResult:
        matched: list[dict] = []

        for rule in self._policy_rules:
            rule_name = rule.get("name", "")
            description = rule.get("description", "")
            actions = rule.get("actions", ["LOG"])
            matched_pattern = None
            for pattern in rule.get("patterns", []):
                try:
                    if re.search(pattern, text, re.IGNORECASE):
                        matched_pattern = pattern
                        break
                except re.error:
                    continue
            if matched_pattern:
                matched.append({
                    "rule": rule_name,
                    "description": description,
                    "actions": actions,
                    "pattern": matched_pattern,
                })

        if not matched:
            return LobsterInspectResult(
                raw_output='{"action":"ALLOW","rules":[]}',
                action="ALLOW",
                findings=[],
            )

        all_actions = [a for m in matched for a in m["actions"]]
        primary_action = next((a for a in _ACTION_PRIORITY if a in all_actions), "LOG")

        findings = []
        for m in matched:
            rule_name = m["rule"]
            risk = _RULE_TO_RISK.get(rule_name, RiskType.UNSAFE_TOOL_CALL)
            boundary = _RULE_TO_BOUNDARY.get(rule_name, Boundary.POLICY_GAP)
            rule_action = next((a for a in _ACTION_PRIORITY if a in m["actions"]), "LOG")
            severity = _ACTION_SEVERITY.get(rule_action, 0.5)
            findings.append(Finding(
                boundary=boundary,
                risk=risk,
                severity=severity,
                evidence=f"Lobster Trap: rule '{rule_name}' triggered — {m['description']} (matched: \"{m['pattern']}\")",
                lobster_decision=rule_action,
            ))

        return LobsterInspectResult(
            raw_output=json.dumps({
                "action": primary_action,
                "rules": [m["rule"] for m in matched],
                "matched_count": len(matched),
            }),
            action=primary_action,
            rule=matched[0]["rule"],
            findings=findings,
        )

    def normalize_log(self, log_line: str) -> Finding | None:
        try:
            data = json.loads(log_line)
        except json.JSONDecodeError:
            return None

        action = data.get("action", "")
        rule = data.get("rule", "")
        prompt = data.get("prompt", "")
        metadata = data.get("metadata", {})
        boundaries = self.boundary_engine.classify_finding(prompt)

        return Finding(
            boundary=boundaries[0] if boundaries else Boundary.POLICY_GAP,
            risk=_RULE_TO_RISK.get(rule, RiskType.NONE),
            severity=metadata.get("risk_score", 0.7),
            evidence=f"Lobster Trap: rule '{rule}' action={action} | {prompt[:100]}",
            lobster_decision=action,
        )
