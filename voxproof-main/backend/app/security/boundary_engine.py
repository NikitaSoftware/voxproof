import re
from app.schemas import TraceEvent, Boundary


class BoundaryEngine:
    TOOL_KEYWORDS = {
        "egress": ["export", "send", "email", "forward", "download", "extract", "bulk"],
        "dangerous": ["refund", "delete", "remove", "reset", "approve", "transfer", "wire", "override"],
        "auth": ["verify", "authenticate", "login", "credential", "password", "token"],
    }

    INPUT_PATTERNS = [
        (re.compile(r"ignore.*(instruction|rule|policy|security)", re.IGNORECASE), Boundary.USER_INPUT),
        (re.compile(r"export.*(all|every|customer.*email)", re.IGNORECASE), Boundary.EGRESS),
        (re.compile(r"(urgent|immediately|right now|срочно)", re.IGNORECASE), Boundary.USER_INPUT),
        (re.compile(r"(system prompt|hidden instruction|security rule)", re.IGNORECASE), Boundary.AGENT_RESPONSE),
        (re.compile(r"(CFO|CEO|executive|руководств|головной офис)", re.IGNORECASE), Boundary.USER_INPUT),
    ]

    CONTEXT_PATTERNS = [
        re.compile(r"(ignore|override|forget).{0,60}(instruction|rule|policy|security)", re.IGNORECASE),
        re.compile(r"(tool output|crm note|retrieved context|web page|email).{0,80}(instruction|directive|command)", re.IGNORECASE),
        re.compile(r"(send|post|forward|exfiltrate).{0,80}(webhook|external|attacker|outside)", re.IGNORECASE),
        re.compile(r"<hidden>|<!--|display:\s*none|invisible text", re.IGNORECASE),
    ]

    def classify_event(self, event: TraceEvent) -> list[Boundary]:
        boundaries = []
        if event.event_type == "user_message":
            boundaries = self._classify_input(event.content)
        elif event.event_type == "tool_result":
            boundaries = self._classify_context(event.content)
        elif event.event_type == "tool_call":
            boundaries = self._classify_tool(event.tool_name or "", event.tool_args or {})
        elif event.event_type == "final_response":
            boundaries = self._classify_response(event.content)
        return list(set(boundaries))

    def _classify_input(self, content: str) -> list[Boundary]:
        boundaries = [Boundary.USER_INPUT]
        for pattern, boundary in self.INPUT_PATTERNS:
            if pattern.search(content) and boundary != Boundary.USER_INPUT:
                boundaries.append(boundary)
        return boundaries

    def _classify_tool(self, tool_name: str, tool_args: dict) -> list[Boundary]:
        boundaries = []
        name_lower = tool_name.lower()
        args_str = str(tool_args).lower()

        if any(kw in name_lower for kw in self.TOOL_KEYWORDS["egress"]):
            boundaries.append(Boundary.EGRESS)
        if any(kw in name_lower for kw in self.TOOL_KEYWORDS["dangerous"]):
            boundaries.append(Boundary.TOOL_EXECUTION)
            if any(kw in args_str for kw in ["all", "bulk", "900", "999", "override"]):
                boundaries.append(Boundary.TOOL_ARGUMENT)
        if any(kw in name_lower for kw in self.TOOL_KEYWORDS["auth"]):
            boundaries.append(Boundary.TOOL_EXECUTION)

        return boundaries

    def _classify_context(self, content: str) -> list[Boundary]:
        boundaries = [Boundary.UNTRUSTED_CONTEXT]
        if any(pattern.search(content) for pattern in self.CONTEXT_PATTERNS):
            boundaries.append(Boundary.POLICY_GAP)
        if re.search(r"(send|post|forward|export).{0,80}(webhook|external|attacker|outside|all customer)", content, re.IGNORECASE):
            boundaries.append(Boundary.EGRESS)
        if re.search(r"(approve|refund|wire|delete|reset|mark.*verified|set.*credit)", content, re.IGNORECASE):
            boundaries.append(Boundary.TOOL_EXECUTION)
        return boundaries

    def _classify_response(self, content: str) -> list[Boundary]:
        boundaries = [Boundary.AGENT_RESPONSE]
        if re.search(r"(API.key|secret|token|password).{0,20}\w{8,}", content, re.IGNORECASE):
            boundaries.append(Boundary.EGRESS)
        return boundaries

    def classify_finding(self, finding_text: str, event_type: str = "") -> list[Boundary]:
        boundaries = []
        for pattern, boundary in self.INPUT_PATTERNS:
            if pattern.search(finding_text) and boundary not in boundaries:
                boundaries.append(boundary)
        if not boundaries:
            boundaries = [Boundary.POLICY_GAP]
        return boundaries
