import pytest
from pathlib import Path
from app.runners.replay_runner import ReplayRunner
from app.schemas import SuiteResult

PROJECT = Path(__file__).resolve().parent.parent.parent
SCENARIOS = str(PROJECT / "scenarios")


class TestReplayRunner:
    def test_loads_scenarios_from_yaml(self):
        runner = ReplayRunner(scenarios_dir=SCENARIOS)
        scenarios = runner.load_scenarios("finance_voice_agent")
        assert len(scenarios) == 12
        assert scenarios[0].id == "cfo_export_all_emails"

    def test_run_single_scenario_returns_result(self, cfo_export_scenario):
        runner = ReplayRunner(scenarios_dir=SCENARIOS)
        result = runner.run_scenario(cfo_export_scenario)
        assert result.scenario_id == "cfo_export_all_emails"
        assert result.gate in ("PASS", "FAIL", "NEEDS_REVIEW")
        assert len(result.trace) > 0

    def test_run_suite_returns_complete_result(self):
        runner = ReplayRunner(scenarios_dir=SCENARIOS)
        suite = runner.run_suite("finance_voice_agent")
        assert isinstance(suite, SuiteResult)
        assert suite.total == 12
        assert 0 <= suite.trust_score <= 100

    def test_suite_has_correct_gate_counts(self):
        runner = ReplayRunner(scenarios_dir=SCENARIOS)
        suite = runner.run_suite("finance_voice_agent")
        assert suite.passed >= 1
        assert suite.failed >= 3
        assert suite.passed + suite.failed + suite.needs_review == 12

    def test_replay_scans_policy_not_only_expected_tools(self):
        runner = ReplayRunner(scenarios_dir=SCENARIOS)
        scenario = [s for s in runner.load_scenarios("finance_voice_agent") if s.id == "crm_note_tool_result_injection"][0]
        result = runner.run_scenario(scenario)
        assert result.gate == "FAIL"
        assert any(f.boundary.value == "UNTRUSTED_CONTEXT" for f in result.findings)
        assert any(f.risk.value == "DATA_EXFILTRATION" for f in result.findings)
