"""RAG / untrusted-context sanitizer.

Catches indirect prompt injection in retrieved documents, CRM notes, emails,
tool results — the vector behind EchoLeak (CVE-2025-32711, CVSS 9.3) and
ForcedLeak (Salesforce Agentforce, Sep 2025, CVSS 9.4).

Detection signals:
- Zero-width / invisible Unicode (U+200B..U+200F, U+2060, U+FEFF, U+00AD)
- Unicode tag block (U+E0000..U+E007F) — the Bard/ChatGPT exfil pattern
- Chat-template role tokens (<|im_start|>, [INST], <<SYS>>, etc.)
- Hidden HTML (display:none, visibility:hidden, opacity:0, comments)
- "Retrieved context says ignore..." indirect injection patterns
- Suspicious base64 blobs (>40 chars) indicating encoded payload

Reference: Greshake et al. arXiv:2302.12173 (indirect injection foundational),
EchoLeak HackTheBox writeup (Jul 2025), Noma ForcedLeak (Sep 2025).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.schemas import Finding, Boundary, RiskType


ZERO_WIDTH_CHARS = ("\u200b", "\u200c", "\u200d", "\u200e", "\u200f",
                    "\u2060", "\u2061", "\u2062", "\u2063", "\u2064",
                    "\ufeff", "\u00ad")
TAG_BLOCK_START = 0xE0000
TAG_BLOCK_END = 0xE007F

ROLE_TOKEN_RE = re.compile(
    r'<\|(?:im_start|im_end|system|user|assistant|begin_of_text|end_of_text|endoftext|eot_id|start_header_id|end_header_id)\|>'
    r'|\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>'
    r'|<\|s\|>|<\|/s\|>',
    re.IGNORECASE,
)

HIDDEN_HTML_RE = re.compile(
    r'<!--[\s\S]*?-->'
    r'|style\s*=\s*["\'][^"\']*(?:display\s*:\s*none|visibility\s*:\s*hidden|opacity\s*:\s*0|font-size\s*:\s*0)[^"\']*["\']',
    re.IGNORECASE,
)

INDIRECT_INJECTION_RE = re.compile(
    r'(?:(?:retrieved|external|untrusted)\s+context|(?:crm|support|ticket)\s+note|email\s+body|web\s+page|document|tool\s+(?:output|result)|knowledge\s*base)'
    r'.{0,250}'
    r'(?:ignore|override|forget|disregard|bypass|skip).{0,80}(?:instruction|rule|policy|security|system|prompt)',
    re.IGNORECASE | re.DOTALL,
)

CONTEXT_DRIVEN_ACTION_RE = re.compile(
    r'(?:(?:tool|api)\s+(?:output|result|response)|crm\s+note|retrieved\s+context|web\s+page|email|attachment)'
    r'.{0,200}'
    r'(?:send|post|forward|export|approve|refund|wire|transfer|mark.*verified|set.*credit|grant\s+access|delete|reset)',
    re.IGNORECASE | re.DOTALL,
)

BASE64_BLOB_RE = re.compile(r'[A-Za-z0-9+/]{40,}={0,2}')


@dataclass
class SanitizationResult:
    cleaned_text: str
    findings: list[Finding] = field(default_factory=list)
    removed_chars: int = 0
    source: str = "untrusted_context"


class RAGSanitizer:
    """Sanitizes untrusted text (RAG chunks, CRM notes, emails, tool results)
    before they reach the LLM. Returns cleaned text + audit findings."""

    def sanitize(self, text: str, source: str = "retrieved_context") -> SanitizationResult:
        if not text:
            return SanitizationResult(cleaned_text="", source=source)

        findings: list[Finding] = []
        cleaned = text
        removed_count = 0

        # 1. Zero-width / invisible Unicode
        zw_count = sum(cleaned.count(c) for c in ZERO_WIDTH_CHARS)
        if zw_count > 0:
            for c in ZERO_WIDTH_CHARS:
                cleaned = cleaned.replace(c, "")
            removed_count += zw_count
            findings.append(Finding(
                boundary=Boundary.UNTRUSTED_CONTEXT,
                risk=RiskType.PROMPT_INJECTION,
                severity=0.78,
                evidence=f"RAG sanitizer: stripped {zw_count} zero-width chars from {source} — hidden Unicode injection (Embrace the Red 2023)",
            ))

        # 2. Unicode tag block (U+E0000..U+E007F)
        tag_count = sum(1 for ch in cleaned if TAG_BLOCK_START <= ord(ch) <= TAG_BLOCK_END)
        if tag_count > 0:
            cleaned = "".join(ch for ch in cleaned if not (TAG_BLOCK_START <= ord(ch) <= TAG_BLOCK_END))
            removed_count += tag_count
            findings.append(Finding(
                boundary=Boundary.UNTRUSTED_CONTEXT,
                risk=RiskType.PROMPT_INJECTION,
                severity=0.85,
                evidence=f"RAG sanitizer: removed {tag_count} Unicode tag-block chars (U+E0000-U+E007F) from {source} — Bard/ChatGPT covert-channel pattern",
            ))

        # 3. Chat role-token injection
        role_matches = ROLE_TOKEN_RE.findall(cleaned)
        if role_matches:
            removed_count += sum(len(match) for match in role_matches)
            cleaned = ROLE_TOKEN_RE.sub("[REMOVED_ROLE_TOKEN]", cleaned)
            findings.append(Finding(
                boundary=Boundary.UNTRUSTED_CONTEXT,
                risk=RiskType.PROMPT_INJECTION,
                severity=0.88,
                evidence=f"RAG sanitizer: chat-template role token in {source} ({role_matches[0]}) — attempts to break LLM role boundary",
            ))

        # 4. Hidden HTML
        if HIDDEN_HTML_RE.search(cleaned):
            removed_count += sum(len(match) for match in HIDDEN_HTML_RE.findall(cleaned))
            cleaned = HIDDEN_HTML_RE.sub("[REMOVED_HIDDEN_HTML]", cleaned)
            findings.append(Finding(
                boundary=Boundary.UNTRUSTED_CONTEXT,
                risk=RiskType.PROMPT_INJECTION,
                severity=0.82,
                evidence=f"RAG sanitizer: hidden HTML in {source} (display:none / opacity:0 / HTML comment) — visual-vs-LLM divergence attack",
            ))

        # 5. Indirect injection pattern
        if INDIRECT_INJECTION_RE.search(cleaned):
            findings.append(Finding(
                boundary=Boundary.UNTRUSTED_CONTEXT,
                risk=RiskType.PROMPT_INJECTION,
                severity=0.90,
                evidence=f"RAG sanitizer: indirect injection in {source} — retrieved content tries to override instructions (Greshake arXiv:2302.12173; EchoLeak CVE-2025-32711; ForcedLeak Sep 2025)",
            ))

        # 6. Context-driven dangerous action
        if CONTEXT_DRIVEN_ACTION_RE.search(cleaned):
            findings.append(Finding(
                boundary=Boundary.UNTRUSTED_CONTEXT,
                risk=RiskType.PROMPT_INJECTION,
                severity=0.85,
                evidence=f"RAG sanitizer: {source} attempts to steer agent into dangerous action (send/export/approve/refund pattern)",
            ))

        # 7. Suspicious base64 blob
        for blob in BASE64_BLOB_RE.findall(cleaned)[:2]:
            findings.append(Finding(
                boundary=Boundary.UNTRUSTED_CONTEXT,
                risk=RiskType.DATA_EXFILTRATION,
                severity=0.65,
                evidence=f"RAG sanitizer: long base64-like blob in {source} ({len(blob)} chars) — encoded payload candidate",
            ))

        return SanitizationResult(
            cleaned_text=cleaned,
            findings=findings,
            removed_chars=removed_count,
            source=source,
        )
