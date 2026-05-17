import pytest
from app.schemas import Scenario, ScenarioTurn, ScenarioExpected, ScenarioSecurity


class TestScenarioParsing:
    def test_valid_scenario_from_yaml_structure(self):
        scenario = Scenario(
            id="test_01",
            title="Test scenario",
            agent={"type": "openai_compatible", "endpoint": "http://localhost:9000/v1/chat/completions"},
            turns=[ScenarioTurn(role="user", content="Hello")],
            expected=ScenarioExpected(),
            security=ScenarioSecurity(),
            runtime={"timeout_ms": 10000},
        )
        assert scenario.id == "test_01"
        assert len(scenario.turns) == 1

    def test_scenario_expected_defaults(self):
        expected = ScenarioExpected()
        assert expected.gate == "PASS"
        assert expected.forbidden_tools == []
        assert expected.risks == []
