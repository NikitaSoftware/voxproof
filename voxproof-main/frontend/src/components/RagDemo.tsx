import { useState } from 'react'
import { ShieldWarning, LockSimple, PlayCircle, Scissors, Eye, EyeSlash, ArrowRight } from '@phosphor-icons/react'

type Finding = {
  boundary: string
  risk: string
  severity: number
  evidence: string
  lobster_decision?: string
}

type RagResult = {
  user_message: string
  rag_document_raw: string
  rag_document_sanitized: string
  rag_findings: Finding[]
  agent_response_risky: string
  agent_response_safe: string
  egress_findings: Finding[]
  egress_blocked: string[]
  summary: {
    rag_chars_removed: number
    egress_allowed: boolean
    total_findings: number
  }
  cve_refs: string[]
}

const SEVERITY_COLOR = (s: number) =>
  s >= 0.85 ? 'bg-red-100 text-red-700 border-red-200'
  : s >= 0.7 ? 'bg-orange-100 text-orange-700 border-orange-200'
  : 'bg-amber-50 text-amber-700 border-amber-200'

function FindingRow({ f }: { f: Finding }) {
  return (
    <div className="flex items-start gap-2.5 px-3 py-2 rounded-lg bg-white border border-zinc-200/60">
      <div className={`px-1.5 py-0.5 rounded text-[9px] font-bold border ${SEVERITY_COLOR(f.severity)} shrink-0 mt-0.5`}>
        sev {f.severity.toFixed(2)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 flex-wrap mb-0.5">
          <span className="text-[10px] font-bold text-white bg-fuchsia-600 px-1.5 py-0.5 rounded">{f.boundary.replace(/_/g, ' ')}</span>
          <span className="text-[11px] font-semibold text-zinc-700">{f.risk.replace(/_/g, ' ')}</span>
        </div>
        <p className="text-[11px] text-zinc-500 leading-relaxed">{f.evidence}</p>
      </div>
    </div>
  )
}

export default function RagDemo() {
  const [result, setResult] = useState<RagResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [revealSanitized, setRevealSanitized] = useState(true)
  const [customDoc, setCustomDoc] = useState('')

  const runDemo = async () => {
    setLoading(true)
    setResult(null)
    try {
      const r = await fetch('/api/playground/rag_demo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(customDoc ? { rag_document: customDoc } : {}),
      })
      const data = await r.json()
      setResult(data)
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      {/* Header */}
      <div className="diffuse-card !p-6">
        <div className="flex items-start gap-4">
          <div className="w-11 h-11 rounded-xl bg-fuchsia-100 flex items-center justify-center flex-shrink-0">
            <ShieldWarning className="w-5 h-5 text-fuchsia-600" weight="duotone" />
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="text-base font-bold text-zinc-900 mb-0.5">Indirect Injection · Egress Demo</h2>
            <p className="text-xs text-zinc-500 leading-relaxed">
              A poisoned RAG document tries to steer the voice agent into bulk PII exfiltration via a Markdown-image side channel.
              VoxProof sanitizes untrusted context and blocks the egress URL before the agent can read it back to the caller.
            </p>
            <div className="flex flex-wrap gap-1.5 mt-2.5">
              <span className="text-[10px] font-bold bg-red-50 text-red-700 border border-red-200 px-1.5 py-0.5 rounded">CVE-2025-32711 · EchoLeak · M365 Copilot · CVSS 9.3</span>
              <span className="text-[10px] font-bold bg-red-50 text-red-700 border border-red-200 px-1.5 py-0.5 rounded">ForcedLeak · Salesforce Agentforce · Sep 2025 · CVSS 9.4</span>
              <span className="text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200 px-1.5 py-0.5 rounded">Greshake arXiv:2302.12173</span>
            </div>
          </div>
        </div>

        <div className="mt-5 flex flex-col gap-3">
          <textarea
            value={customDoc}
            onChange={e => setCustomDoc(e.target.value)}
            placeholder="(optional) Paste your own poisoned document — or leave empty to use the built-in EchoLeak-style payload..."
            className="w-full h-20 px-4 py-2.5 rounded-xl border border-zinc-200 text-xs font-mono resize-none focus:outline-none focus:border-fuchsia-400 focus:ring-2 focus:ring-fuchsia-100"
          />
          <button
            onClick={runDemo}
            disabled={loading}
            className="flex items-center justify-center gap-2 px-5 py-2.5 bg-zinc-900 text-white rounded-xl text-sm font-semibold hover:bg-zinc-800 active:scale-[0.98] transition-all disabled:opacity-40 self-start"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Sanitizing & inspecting egress...
              </span>
            ) : (
              <><PlayCircle className="w-4 h-4" weight="fill" />Run RAG poisoning attack</>
            )}
          </button>
        </div>
      </div>

      {result && (
        <>
          {/* Summary strip */}
          <div className="flex items-center gap-4 p-3 rounded-xl bg-red-50/70 border border-red-200">
            <LockSimple className="w-5 h-5 text-red-500 flex-shrink-0" weight="fill" />
            <span className="text-xs font-semibold text-red-900">
              VoxProof blocked the attack: removed {result.summary.rag_chars_removed} hidden chars from RAG,
              flagged {result.rag_findings.length} injection signal{result.rag_findings.length !== 1 ? 's' : ''},
              blocked {result.egress_blocked.length} egress URL{result.egress_blocked.length !== 1 ? 's' : ''}.
            </span>
            <span className="ml-auto text-[10px] font-bold uppercase tracking-wider text-red-700 bg-white/60 border border-red-200 px-2 py-0.5 rounded-full">
              gate: FAIL
            </span>
          </div>

          {/* Step 1: Document side-by-side */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-bold text-zinc-500 uppercase tracking-widest">Step 1 · RAG sanitization</h3>
              <button
                onClick={() => setRevealSanitized(v => !v)}
                className="flex items-center gap-1 text-[10px] text-zinc-500 hover:text-zinc-700 transition-colors"
              >
                {revealSanitized ? <EyeSlash className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                {revealSanitized ? 'Hide cleaned text' : 'Show cleaned text'}
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-3 items-stretch">
              {/* Poisoned */}
              <div className="rounded-xl border-2 border-red-200 bg-red-50/30 overflow-hidden flex flex-col">
                <div className="flex items-center gap-2 px-3 py-2 bg-red-500 text-white">
                  <span className="text-[10px] font-bold uppercase tracking-wider">Poisoned RAG document</span>
                  <span className="ml-auto text-[10px] font-mono bg-white/20 px-1.5 py-0.5 rounded">{result.rag_document_raw.length} chars</span>
                </div>
                <pre className="text-[11px] font-mono text-zinc-700 p-3 whitespace-pre-wrap break-words leading-relaxed flex-1 overflow-auto max-h-72">
                  {result.rag_document_raw}
                </pre>
              </div>

              {/* Arrow */}
              <div className="hidden md:flex items-center justify-center px-2">
                <div className="flex flex-col items-center gap-2 text-fuchsia-500">
                  <Scissors className="w-5 h-5" weight="fill" />
                  <ArrowRight className="w-5 h-5" weight="bold" />
                  <span className="text-[9px] font-bold uppercase tracking-widest">sanitize</span>
                </div>
              </div>

              {/* Sanitized */}
              <div className="rounded-xl border-2 border-emerald-200 bg-emerald-50/20 overflow-hidden flex flex-col">
                <div className="flex items-center gap-2 px-3 py-2 bg-emerald-500 text-white">
                  <span className="text-[10px] font-bold uppercase tracking-wider">Sanitized for the LLM</span>
                  <span className="ml-auto text-[10px] font-mono bg-white/20 px-1.5 py-0.5 rounded">{result.rag_document_sanitized.length} chars</span>
                </div>
                <pre className="text-[11px] font-mono text-zinc-700 p-3 whitespace-pre-wrap break-words leading-relaxed flex-1 overflow-auto max-h-72">
                  {revealSanitized ? result.rag_document_sanitized : '[hidden — click "Show cleaned text"]'}
                </pre>
              </div>
            </div>

            {/* RAG findings */}
            <div className="mt-3 space-y-1.5">
              {result.rag_findings.map((f, i) => <FindingRow key={i} f={f} />)}
            </div>
          </div>

          {/* Step 2: Egress side-by-side */}
          <div>
            <h3 className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-2">Step 2 · Agent response · egress check</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {/* Risky */}
              <div className="rounded-xl border-2 border-red-200 bg-red-50/30 overflow-hidden">
                <div className="flex items-center gap-2 px-3 py-2 bg-red-500 text-white">
                  <span className="text-[10px] font-bold uppercase tracking-wider">What would have leaked</span>
                </div>
                <p className="text-xs text-zinc-700 p-3 font-mono leading-relaxed break-words">
                  {result.agent_response_risky}
                </p>
              </div>

              {/* Safe */}
              <div className="rounded-xl border-2 border-emerald-200 bg-emerald-50/20 overflow-hidden">
                <div className="flex items-center gap-2 px-3 py-2 bg-emerald-500 text-white">
                  <span className="text-[10px] font-bold uppercase tracking-wider">VoxProof-protected response</span>
                </div>
                <p className="text-xs text-zinc-700 p-3 font-mono leading-relaxed break-words">
                  {result.agent_response_safe}
                </p>
              </div>
            </div>

            {/* Egress findings */}
            <div className="mt-3 space-y-1.5">
              {result.egress_findings.map((f, i) => <FindingRow key={i} f={f} />)}
            </div>

            {/* Blocked URLs */}
            {result.egress_blocked.length > 0 && (
              <div className="mt-3 p-3 rounded-xl bg-zinc-950 border border-zinc-800">
                <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-1.5">Blocked egress URLs</p>
                {result.egress_blocked.map((url, i) => (
                  <p key={i} className="text-[11px] font-mono text-red-300 break-all">
                    <span className="text-zinc-600">→ </span>{url}
                  </p>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
