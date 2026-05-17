export type GateResult = 'PASS' | 'FAIL' | 'NEEDS_REVIEW';
export type Boundary =
  | 'USER_INPUT' | 'AUDIO_LAYER' | 'AGENT_RESPONSE'
  | 'TOOL_ARGUMENT' | 'TOOL_EXECUTION' | 'UNTRUSTED_CONTEXT'
  | 'EGRESS' | 'POLICY_GAP';
export type RiskType =
  | 'DATA_EXFILTRATION' | 'PROMPT_INJECTION' | 'AUTH_BYPASS'
  | 'SYSTEM_PROMPT_EXTRACTION' | 'SOCIAL_ENGINEERING'
  | 'AUDIO_LAYER_ATTACK' | 'ADVERSARIAL_AUDIO' | 'VOICE_CLONE'
  | 'SPECTRAL_ANOMALY' | 'HIGH_RISK_ACTION' | 'UNSAFE_TOOL_CALL' | 'NONE';

export interface Finding {
  id: string;
  boundary: Boundary;
  risk: RiskType;
  severity: number;
  evidence: string;
  lobster_decision?: string;
  gemini_confidence?: number;
  gemini_explanation?: string;
}

export interface TraceEvent {
  id: string;
  event_type: string;
  content?: string;
  tool_name?: string;
  tool_args?: Record<string, unknown>;
}

export interface ScenarioResult {
  scenario_id: string;
  title: string;
  gate: GateResult;
  score: number;
  findings: Finding[];
  trace: TraceEvent[];
  duration_ms: number;
}

export interface SuiteResult {
  suite_name?: string;
  total: number;
  passed: number;
  failed: number;
  needs_review: number;
  trust_score: number;
  results: ScenarioResult[];
}
