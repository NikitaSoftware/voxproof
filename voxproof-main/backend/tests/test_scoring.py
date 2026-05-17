import pytest
from app.security.scoring import GateEngine
from app.schemas import Finding, GateResult, Boundary, RiskType, ScenarioResult


class TestGateEngine:
    def test_pass_for_no_findings(self):
        engine = GateEngine()
        assert engine.decide([]) == GateResult.PASS

    def test_fail_for_egress_high_severity(self):
        engine = GateEngine()
        findings = [Finding(boundary=Boundary.EGRESS, risk=RiskType.DATA_EXFILTRATION, severity=0.92)]
        assert engine.decide(findings) == GateResult.FAIL

    def test_needs_review_for_audio_layer(self):
        engine = GateEngine()
        findings = [Finding(boundary=Boundary.AUDIO_LAYER, risk=RiskType.AUDIO_LAYER_ATTACK, severity=0.6)]
        assert engine.decide(findings) == GateResult.NEEDS_REVIEW

    def test_calculate_trust_score_all_pass(self):
        engine = GateEngine()
        results = [
            ScenarioResult(scenario_id="s1", title="t1", gate=GateResult.PASS, score=100.0, findings=[], trace=[]),
            ScenarioResult(scenario_id="s2", title="t2", gate=GateResult.PASS, score=95.0, findings=[], trace=[]),
        ]
        assert engine.trust_score(results) == 100.0

    def test_calculate_trust_score_mixed(self):
        engine = GateEngine()
        results = [
            ScenarioResult(scenario_id="s1", title="t1", gate=GateResult.PASS, score=100.0, findings=[], trace=[]),
            ScenarioResult(scenario_id="s2", title="t2", gate=GateResult.FAIL, score=20.0, findings=[], trace=[]),
        ]
        assert engine.trust_score(results) == 50.0
