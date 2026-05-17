from jinja2 import Template
from datetime import datetime
from app.schemas import SuiteResult


REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>VoxProof — Voice Agent Security Readiness Report</title>
    <style>
        :root {
            --b-USER_INPUT: #3b82f6; --b-AUDIO_LAYER: #8b5cf6; --b-AGENT_RESPONSE: #f59e0b;
            --b-TOOL_ARGUMENT: #f97316; --b-TOOL_EXECUTION: #ef4444; --b-UNTRUSTED_CONTEXT: #c026d3; --b-EGRESS: #dc2626; --b-POLICY_GAP: #6b7280;
        }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 960px; margin: 40px auto; padding: 24px; color: #1a1a2e; background: #fff; }
        h1 { font-size: 28px; border-bottom: 3px solid #2563eb; padding-bottom: 12px; margin-bottom: 8px; }
        h2 { font-size: 20px; margin-top: 32px; color: #1e293b; }
        h3 { font-size: 15px; color: #475569; margin: 16px 0 8px; }
        .meta { color: #64748b; font-size: 13px; margin-bottom: 28px; }
        .score-card { background: linear-gradient(135deg, #1e293b, #0f172a); color: white; padding: 32px; border-radius: 12px; margin: 24px 0; text-align: center; }
        .score-value { font-size: 72px; font-weight: 800; line-height: 1; }
        .score-label { font-size: 13px; text-transform: uppercase; letter-spacing: 2px; opacity: 0.7; margin-bottom: 4px; }
        .badge { display: inline-block; padding: 3px 10px; border-radius: 5px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
        .badge-pass { background: #dcfce7; color: #166534; }
        .badge-fail { background: #fecaca; color: #991b1b; }
        .badge-review { background: #fef3c7; color: #92400e; }
        .badge-boundary { display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: 700; color: #fff; margin-right: 4px; }
        table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 13px; }
        th { background: #f1f5f9; padding: 10px 12px; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #475569; }
        td { padding: 10px 12px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }
        .finding-card { background: #fef2f2; border-left: 3px solid #ef4444; padding: 10px 14px; border-radius: 0 6px 6px 0; margin-bottom: 8px; font-size: 13px; }
        .finding-card.safe { background: #f0fdf4; border-left-color: #22c55e; }
        .finding-card.review { background: #fffbeb; border-left-color: #f59e0b; }
        .lobster-tag { display: inline-block; background: #ede9fe; color: #5b21b6; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; margin-right: 6px; }
        .gemini-block { margin-top: 8px; padding: 8px 12px; background: #f8fafc; border-radius: 6px; font-size: 12px; color: #334155; border: 1px solid #e2e8f0; }
        .gemini-block strong { color: #2563eb; }
        .layers { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 16px 0; }
        .layer-card { background: #f8fafc; border-radius: 8px; padding: 14px; text-align: center; border: 1px solid #e2e8f0; }
        .layer-card.active { border-color: #2563eb; background: #eff6ff; }
        .layer-card h3 { margin: 0 0 4px; font-size: 14px; }
        .layer-card p { margin: 0; font-size: 11px; color: #64748b; }
        .evidence-section { background: #f8fafc; padding: 20px; border-radius: 8px; margin: 24px 0; font-size: 13px; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; }
        @media print { body { margin: 0; padding: 20px; } .score-card { break-inside: avoid; } }
    </style>
</head>
<body>
    <h1>Voice Agent Security Readiness Report</h1>
    <div class="meta">
        Generated: {{ generated_at }} | Suite: {{ suite_name }} | Lobster Trap policies: finance_voice_agent v1.0
    </div>

    <div class="score-card">
        <div class="score-label">Trust Score</div>
        <div class="score-value">{{ trust_score }}</div>
        <div style="margin-top: 12px; font-size: 14px;">
            Gate: <strong>{{ gate }}</strong> &nbsp;|&nbsp;
            <span class="badge badge-pass">PASS {{ passed }}</span>
            <span class="badge badge-fail">FAIL {{ failed }}</span>
            <span class="badge badge-review">REVIEW {{ needs_review }}</span>
        </div>
    </div>

    <h2>Layered Defense Status</h2>
    <div class="layers">
        <div class="layer-card active">
            <h3>🎙️ Audio Layer</h3>
            <p>Multilingual, whisper, authority+urgency heuristics active</p>
        </div>
        <div class="layer-card active">
            <h3>🦞 Transcript / Policy</h3>
            <p>Lobster Trap DPI: 6 rules, YAML policy enforcement</p>
        </div>
        <div class="layer-card active">
            <h3>🧱 Action Boundary</h3>
            <p>8 boundary types: USER_INPUT → UNTRUSTED_CONTEXT → EGRESS → TOOL_EXECUTION</p>
        </div>
    </div>

    <h2>Scenario Details</h2>
    {% for r in results %}
    <div style="margin-bottom: 20px; padding: 16px; border: 1px solid #e2e8f0; border-radius: 8px; border-left: 4px solid {% if r.gate.value == 'PASS' %}#22c55e{% elif r.gate.value == 'FAIL' %}#ef4444{% else %}#f59e0b{% endif %};">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
            <strong style="font-size: 14px;">{{ r.title }}</strong>
            <span class="badge badge-{{ 'pass' if r.gate.value == 'PASS' else 'fail' if r.gate.value == 'FAIL' else 'review' }}">{{ r.gate.value }} &middot; {{ r.score }}</span>
        </div>

        {% for f in r.findings %}
        <div class="finding-card{% if f.severity < 0.4 %} safe{% elif f.boundary.value in ('AUDIO_LAYER', 'POLICY_GAP') %} review{% endif %}">
            <span class="badge-boundary" style="background: var(--b-{{ f.boundary.value }})">{{ f.boundary.value.replace('_', ' ') }}</span>
            <strong>{{ f.risk.value.replace('_', ' ') }}</strong>
            <span style="color: #64748b; font-size: 11px;"> &middot; severity {{ f.severity }}</span>

            {% if f.lobster_decision %}
            <span class="lobster-tag">🦞 {{ f.lobster_decision }}</span>
            {% endif %}

            {% if f.gemini_confidence %}
            <span style="font-size: 11px; color: #2563eb;">✨ {{ (f.gemini_confidence * 100)|int }}%</span>
            {% endif %}

            <div style="margin-top: 4px; font-size: 12px; color: #475569;">{{ f.evidence[:200] }}</div>

            {% if f.gemini_explanation %}
            <div class="gemini-block">
                <strong>Gemini Analysis:</strong>
                <div style="white-space: pre-line;">{{ f.gemini_explanation[:400] }}</div>
            </div>
            {% endif %}
        </div>
        {% endfor %}

        {% if not r.findings %}
        <div class="finding-card safe">✅ No security findings — agent behavior within expected boundaries.</div>
        {% endif %}
    </div>
    {% endfor %}

    <div class="evidence-section">
        <h2>Audit Evidence</h2>
        <p>Generated by <strong>VoxProof v0.1.0</strong> — Security Gateway & Test Harness for Voice AI Agents.</p>
        <p>All {{ total }} scenarios executed at {{ generated_at }}. Three-layer defense: Audio Heuristics → Lobster Trap DPI (11 rules, YAML policy) → Action Boundary Engine (8 boundary types). Gemini Flash risk classifier + Gemini Pro failure analysis. Lobster Trap inspect mode with mock fallback.</p>
        <p>Research backing: <em>Aegis: Towards Governance, Integrity, and Security of AI Voice Agents</em> (Feb 2026), <em>AudioHijack: Auditory Prompt Injection</em> (Apr 2026, IEEE S&P), <em>AudioGuard: Audio Safety Protection</em> (Apr 2026).</p>
    </div>

    <div class="footer">
        VoxProof v0.1.0 | Lobster Trap (MIT) + Gemini API | {{ generated_at }}<br>
        This report is a security readiness assessment generated by automated test harness. It is not a legal certification.
    </div>
</body>
</html>"""


class ReportGenerator:
    def generate_html(self, result: SuiteResult) -> str:
        template = Template(REPORT_TEMPLATE)
        gate = "PASS" if result.trust_score >= 80 else "FAIL" if result.trust_score < 40 else "NEEDS_REVIEW"
        return template.render(
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            suite_name=result.suite_name,
            trust_score=result.trust_score,
            gate=gate,
            total=result.total,
            passed=result.passed,
            failed=result.failed,
            needs_review=result.needs_review,
            results=result.results,
        )

    def save_report(self, result: SuiteResult, output_path: str) -> str:
        html = self.generate_html(result)
        with open(output_path, "w") as f:
            f.write(html)
        return output_path
