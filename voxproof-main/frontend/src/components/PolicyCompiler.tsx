import { useState } from 'react'
import { FileText, Lightning, CheckCircle, Warning, X, Copy, Check } from '@phosphor-icons/react'

interface CompiledPolicy {
  summary: string
  lobster_yaml: string
  scenarios: Array<{
    id: string
    title: string
    transcript: string
    expected_risk: string
    expected_gate: string
  }>
  rules_count: number
  attack_vectors: string[]
  error?: string
}

const EXAMPLE_POLICY = `Refund Policy:
- Refunds under $50 can be processed by support agents automatically
- Refunds $50-$500 require supervisor approval before processing
- Refunds above $500 require manager sign-off and identity re-verification

Identity Verification:
- All callers must verify with account number + last 4 digits of SSN
- Identity cannot be bypassed for any reason, regardless of caller authority
- If verification fails 3 times, transfer to fraud department

Data Access:
- Support agents can view individual customer records
- Bulk data exports require written request + compliance approval
- Customer PII must never be shared verbally over phone

Escalation:
- High-value transactions ($500+) must be escalated to manager
- Any request to bypass security protocols triggers fraud alert
- Calls with suspicious patterns should be flagged for review`

export default function PolicyCompiler() {
  const [policyText, setPolicyText] = useState('')
  const [result, setResult] = useState<CompiledPolicy | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [activeTab, setActiveTab] = useState<'yaml' | 'scenarios'>('yaml')

  const compile = async () => {
    if (!policyText.trim()) return
    setLoading(true)
    setResult(null)
    try {
      const r = await fetch('/api/policy/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ policy_text: policyText }),
      })
      const data = await r.json()
      setResult(data)
    } catch {
      setResult({ error: 'Network error — is the backend running?', summary: '', lobster_yaml: '', scenarios: [], rules_count: 0, attack_vectors: [] })
    }
    setLoading(false)
  }

  const copyYaml = () => {
    if (result?.lobster_yaml) {
      navigator.clipboard.writeText(result.lobster_yaml)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const gateColor = (gate: string) => {
    if (gate === 'FAIL') return 'text-red-600 bg-red-50'
    if (gate === 'NEEDS_REVIEW') return 'text-amber-600 bg-amber-50'
    return 'text-emerald-600 bg-emerald-50'
  }

  const riskColor = (risk: string) => {
    const colors: Record<string, string> = {
      DATA_EXFILTRATION: 'bg-rose-100 text-rose-700',
      PROMPT_INJECTION: 'bg-orange-100 text-orange-700',
      AUTH_BYPASS: 'bg-red-100 text-red-700',
      HIGH_RISK_ACTION: 'bg-amber-100 text-amber-700',
      SOCIAL_ENGINEERING: 'bg-violet-100 text-violet-700',
      SYSTEM_PROMPT_EXTRACTION: 'bg-pink-100 text-pink-700',
    }
    return colors[risk] || 'bg-zinc-100 text-zinc-700'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center flex-shrink-0">
          <FileText className="w-5 h-5 text-indigo-600" weight="duotone" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-zinc-900">Policy-to-Attack Compiler</h2>
          <p className="text-sm text-zinc-500 mt-0.5">
            Paste your enterprise policy document — Gemini compiles it into Lobster Trap rules + adversarial voice attack scenarios.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-[1fr_1fr] gap-6">
        {/* Input */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Policy Document</label>
            <button
              onClick={() => setPolicyText(EXAMPLE_POLICY)}
              className="text-xs text-indigo-600 hover:text-indigo-700 font-medium"
            >
              Load example
            </button>
          </div>
          <textarea
            value={policyText}
            onChange={e => setPolicyText(e.target.value)}
            placeholder="Paste your refund policy, identity verification rules, data access policy..."
            className="w-full h-80 px-4 py-3 rounded-2xl border border-zinc-200 bg-white text-sm text-zinc-800
              placeholder:text-zinc-400 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500/30
              focus:border-indigo-300 font-mono leading-relaxed"
          />
          <button
            onClick={compile}
            disabled={loading || !policyText.trim()}
            className="w-full flex items-center justify-center gap-2.5 px-6 py-3 bg-indigo-600 text-white
              rounded-2xl text-sm font-semibold hover:bg-indigo-700 active:scale-[0.98] transition-all
              duration-200 disabled:opacity-40"
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Gemini is compiling...
              </>
            ) : (
              <>
                <Lightning className="w-4 h-4" weight="fill" />
                Compile Policy
              </>
            )}
          </button>
        </div>

        {/* Output */}
        <div className="space-y-3">
          {!result && !loading && (
            <div className="h-full rounded-2xl border border-dashed border-zinc-200 flex flex-col items-center justify-center py-16 text-center gap-3">
              <Lightning className="w-10 h-10 text-zinc-200" weight="duotone" />
              <p className="text-sm text-zinc-400 max-w-xs">
                Paste a policy document and click Compile — Gemini generates Lobster Trap YAML rules and voice attack test scenarios.
              </p>
            </div>
          )}

          {result?.error && (
            <div className="rounded-2xl bg-red-50 border border-red-200 p-4 flex items-start gap-3">
              <X className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" weight="bold" />
              <p className="text-sm text-red-700">{result.error}</p>
            </div>
          )}

          {result && !result.error && (
            <div className="space-y-4">
              {/* Summary */}
              <div className="rounded-2xl bg-indigo-50 border border-indigo-100 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle className="w-4 h-4 text-indigo-600" weight="fill" />
                  <span className="text-xs font-semibold text-indigo-700 uppercase tracking-wide">
                    Compiled — {result.rules_count} rules · {result.scenarios?.length ?? 0} scenarios
                  </span>
                </div>
                <p className="text-sm text-indigo-800 leading-relaxed">{result.summary}</p>
                {result.attack_vectors?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {result.attack_vectors.map(v => (
                      <span key={v} className="px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded-full text-xs font-medium">
                        {v}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Tabs */}
              <div className="flex gap-1 p-1 bg-zinc-100 rounded-xl">
                <button
                  onClick={() => setActiveTab('yaml')}
                  className={`flex-1 py-1.5 rounded-lg text-xs font-semibold transition-colors ${activeTab === 'yaml' ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-500'}`}
                >
                  Lobster YAML
                </button>
                <button
                  onClick={() => setActiveTab('scenarios')}
                  className={`flex-1 py-1.5 rounded-lg text-xs font-semibold transition-colors ${activeTab === 'scenarios' ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-500'}`}
                >
                  Attack Scenarios ({result.scenarios?.length ?? 0})
                </button>
              </div>

              {/* YAML tab */}
              {activeTab === 'yaml' && result.lobster_yaml && (
                <div className="relative">
                  <button
                    onClick={copyYaml}
                    className="absolute top-3 right-3 p-1.5 bg-white/90 rounded-lg hover:bg-white transition-colors z-10"
                    title="Copy YAML"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" weight="bold" /> : <Copy className="w-3.5 h-3.5 text-zinc-500" />}
                  </button>
                  <pre className="h-52 overflow-auto rounded-2xl bg-zinc-900 text-zinc-100 text-xs p-4 leading-relaxed font-mono">
                    {result.lobster_yaml}
                  </pre>
                </div>
              )}

              {/* Scenarios tab */}
              {activeTab === 'scenarios' && (
                <div className="space-y-2 max-h-52 overflow-y-auto">
                  {(result.scenarios ?? []).map((s, i) => (
                    <div key={i} className="rounded-xl border border-zinc-200 bg-white p-3 space-y-1.5">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-semibold text-zinc-800 leading-tight">{s.title}</span>
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${riskColor(s.expected_risk)}`}>
                            {s.expected_risk}
                          </span>
                          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${gateColor(s.expected_gate)}`}>
                            {s.expected_gate}
                          </span>
                        </div>
                      </div>
                      <p className="text-xs text-zinc-500 italic">"{s.transcript}"</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Research badge */}
      <div className="flex items-start gap-3 rounded-xl bg-zinc-50 border border-zinc-200 p-3">
        <Warning className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" weight="fill" />
        <div className="text-xs text-zinc-600 leading-relaxed space-y-1">
          <p><strong>Academic validation:</strong> AudioHijack (IEEE S&P 2026, arXiv 2604.14604) reported 79–96% attack success against large audio-language models and calls for dedicated defenses. Agentic red-teaming research (May 2026, arXiv 2605.04019) shows why automated adversarial testing matters for agentic systems.</p>
          <p className="text-zinc-500">Runtime Governance (Mar 2026, arXiv 2603.16586): "prospective policy enforcement that intercepts actions before execution" — exactly what VoxProof does. AI Agent Code of Conduct (arXiv 2509.23994): converts enterprise policies into runtime guardrails — our Policy Compiler.</p>
        </div>
      </div>
    </div>
  )
}
