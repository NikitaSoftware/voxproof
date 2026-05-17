from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import Optional
import uuid


class Boundary(str, Enum):
    USER_INPUT = "USER_INPUT"
    AUDIO_LAYER = "AUDIO_LAYER"
    AGENT_RESPONSE = "AGENT_RESPONSE"
    TOOL_ARGUMENT = "TOOL_ARGUMENT"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    UNTRUSTED_CONTEXT = "UNTRUSTED_CONTEXT"
    EGRESS = "EGRESS"
    POLICY_GAP = "POLICY_GAP"


class RiskType(str, Enum):
    DATA_EXFILTRATION = "DATA_EXFILTRATION"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    AUTH_BYPASS = "AUTH_BYPASS"
    SYSTEM_PROMPT_EXTRACTION = "SYSTEM_PROMPT_EXTRACTION"
    SOCIAL_ENGINEERING = "SOCIAL_ENGINEERING"
    AUDIO_LAYER_ATTACK = "AUDIO_LAYER_ATTACK"
    SPECTRAL_ANOMALY = "SPECTRAL_ANOMALY"
    ADVERSARIAL_AUDIO = "ADVERSARIAL_AUDIO"
    VOICE_CLONE = "VOICE_CLONE"
    HIGH_RISK_ACTION = "HIGH_RISK_ACTION"
    UNSAFE_TOOL_CALL = "UNSAFE_TOOL_CALL"
    NONE = "NONE"


class GateResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class Finding(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    boundary: Boundary
    risk: RiskType
    severity: float = Field(ge=0.0, le=1.0)
    evidence: str = ""
    lobster_decision: Optional[str] = None
    gemini_confidence: Optional[float] = None
    gemini_explanation: Optional[str] = None
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())


class TraceEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    event_type: str
    content: str = ""
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None
    tool_result: Optional[str] = None
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())


class ScenarioTurn(BaseModel):
    role: str
    content: str


class ScenarioExpected(BaseModel):
    final_outcome: Optional[str] = None
    forbidden_tools: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    must_mention: list[str] = Field(default_factory=list)
    gate: GateResult = GateResult.PASS
    risks: list[RiskType] = Field(default_factory=list)
    boundaries: list[Boundary] = Field(default_factory=list)


class ScenarioSecurity(BaseModel):
    lobster_policy: str = ""
    expected_lobster_actions: list[str] = Field(default_factory=list)


class Scenario(BaseModel):
    id: str
    title: str
    agent: dict = Field(default_factory=dict)
    turns: list[ScenarioTurn] = Field(default_factory=list)
    expected: ScenarioExpected = Field(default_factory=ScenarioExpected)
    security: ScenarioSecurity = Field(default_factory=ScenarioSecurity)
    runtime: dict = Field(default_factory=dict)


class ScenarioResult(BaseModel):
    scenario_id: str
    title: str
    gate: GateResult
    score: float = Field(ge=0.0, le=100.0)
    findings: list[Finding] = Field(default_factory=list)
    trace: list[TraceEvent] = Field(default_factory=list)
    duration_ms: float = 0.0


class SuiteResult(BaseModel):
    suite_name: str = ""
    total: int = 0
    passed: int = 0
    failed: int = 0
    needs_review: int = 0
    trust_score: float = Field(ge=0.0, le=100.0)
    results: list[ScenarioResult] = Field(default_factory=list)
    generated_at: str = ""
