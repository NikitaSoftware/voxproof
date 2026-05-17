import { useState, useCallback } from 'react'
import { Play, Shield, Scroll, Broadcast, CaretRight, Gear, Check, X, Flask, ChatCenteredText, SignOut, FileText, CheckCircle, Warning, XCircle, ShieldWarning } from '@phosphor-icons/react'
import type { ScenarioResult, SuiteResult } from './types'
import LiveMonitor from './components/LiveMonitor'
import CustomTest from './components/CustomTest'
import Playground from './components/Playground'
import Login from './components/Login'
import PolicyCompiler from './components/PolicyCompiler'
import RagDemo from './components/RagDemo'

type Tab = 'suite' | 'live' | 'playground' | 'rag' | 'custom' | 'report' | 'policy'

function getToken() { return localStorage.getItem('voxproof_token') }
function getUser() { return localStorage.getItem('voxproof_user') }

const BOUNDARY_COLORS: Record<string, string> = {
  USER_INPUT: 'bg-blue-500', AUDIO_LAYER: 'bg-violet-500', AGENT_RESPONSE: 'bg-amber-500',
  TOOL_ARGUMENT: 'bg-orange-500', TOOL_EXECUTION: 'bg-red-500', UNTRUSTED_CONTEXT: 'bg-fuchsia-600',
  EGRESS: 'bg-rose-600', POLICY_GAP: 'bg-zinc-500',
}
const GATE_COLORS: Record<string, string> = { PASS: 'text-emerald-600', FAIL: 'text-red-600', NEEDS_REVIEW: 'text-amber-600' }
const GATE_BG: Record<string, string> = {
  PASS: 'bg-emerald-50 border-emerald-200',
  FAIL: 'bg-red-50 border-red-200',
  NEEDS_REVIEW: 'bg-amber-50 border-amber-200',
}

function TrustGauge({ score }: { score: number }) {
  const r = 38
  const circumference = 2 * Math.PI * r
  const dashOffset = circumference * (1 - score / 100)
  const color = score >= 80 ? '#22c55e' : score >= 40 ? '#f59e0b' : '#ef4444'
  const trackColor = score >= 80 ? '#dcfce7' : score >= 40 ? '#fef3c7' : '#fee2e2'

  return (
    <div className="relative flex flex-col items-center">
      <svg width="96" height="96" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={r} fill="none" stroke={trackColor} strokeWidth="8" />
        <circle cx="50" cy="50" r={r} fill="none" stroke={color} strokeWidth="8"
          strokeLinecap="round" strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          transform="rotate(-90 50 50)"
          style={{ transition: 'stroke-dashoffset 1.2s cubic-bezier(0.4,0,0.2,1)' }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold tabular-nums leading-none" style={{ color }}>{score}</span>
        <span className="text-[9px] font-semibold text-zinc-400 uppercase tracking-widest mt-0.5">Trust</span>
      </div>
    </div>
  )
}

export default function App() {
  const [token, setToken] = useState(getToken())
  const [user, setUser] = useState(getUser())
  const [tab, setTab] = useState<Tab>('suite')
  const [results, setResults] = useState<ScenarioResult[]>([])
  const [trustScore, setTrustScore] = useState<number | null>(null)
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [running, setRunning] = useState(false)
  const [lastRunId, setLastRunId] = useState<number | null>(null)
  const [passed, setPassed] = useState(0)
  const [failed, setFailed] = useState(0)
  const [needsReview, setNeedsReview] = useState(0)
  const [showSettings, setShowSettings] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [keyStatus, setKeyStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')

  const handleLogout = () => {
    localStorage.removeItem('voxproof_token')
    localStorage.removeItem('voxproof_user')
    setToken(null); setUser(null)
  }

  const handleLogin = (t: string, email: string) => {
    localStorage.setItem('voxproof_token', t)
    localStorage.setItem('voxproof_user', email)
    setToken(t); setUser(email)
  }

  if (!token) return <Login onLogin={handleLogin} />

  const handleRun = useCallback(async () => {
    setRunning(true)
    try {
      const r = await fetch('/api/run/finance_voice_agent', { method: 'POST' })
      const data = await r.json() as SuiteResult & { run_id: number }
      setResults(data.results)
      setTrustScore(data.trust_score)
      setPassed(data.passed)
      setFailed(data.failed)
      setNeedsReview(data.needs_review)
      setLastRunId(data.run_id)
      setSelectedIdx(0)
    } catch (e) { console.error(e) }
    setRunning(false)
  }, [])

  const saveKey = async () => {
    setKeyStatus('saving')
    try {
      const r = await fetch('/api/config/key', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({api_key: apiKey}) })
      const d = await r.json()
      setKeyStatus(d.status === 'ok' ? 'saved' : 'error')
      setTimeout(() => setKeyStatus('idle'), 2000)
    } catch { setKeyStatus('error') }
  }

  const selected = results[selectedIdx]

  const TABS = [
    ['suite', Play, 'Attack Suite'],
    ['live', Broadcast, 'Live Monitor'],
    ['playground', ChatCenteredText, 'Playground'],
    ['rag', ShieldWarning, 'RAG · Egress'],
    ['policy', FileText, 'Policy Compiler'],
    ['custom', Flask, 'Custom Test'],
    ['report', Scroll, 'Evidence Pack'],
  ] as const

  return (
    <div className="min-h-[100dvh] bg-zinc-50">
      {/* Nav */}
      <header className="sticky top-0 z-40 border-b border-zinc-200/60 bg-white/90 backdrop-blur-xl">
        <div className="max-w-[1440px] mx-auto px-6 h-14 flex items-center gap-4">
          {/* Brand */}
          <div className="flex items-center gap-2.5 mr-2">
            <div className="w-8 h-8 rounded-xl bg-emerald-500 flex items-center justify-center shadow shadow-emerald-500/25">
              <Shield className="w-4.5 h-4.5 text-white" weight="fill" />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight text-zinc-900 leading-none">VoxProof</h1>
              <p className="text-[10px] text-zinc-400 leading-none mt-0.5">{user}</p>
            </div>
          </div>

          {/* Hackathon badges */}
          <div className="hidden md:flex items-center gap-1 mr-4">
            <span className="text-[9px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 px-1.5 py-0.5 rounded-full uppercase tracking-wider">Track 1 · Lobster Trap</span>
            <span className="text-[9px] font-bold bg-amber-50 text-amber-700 border border-amber-200 px-1.5 py-0.5 rounded-full uppercase tracking-wider">Track 2 · Gemini</span>
          </div>

          {/* Tabs */}
          <nav className="flex gap-0.5 bg-zinc-100 rounded-xl p-1 flex-1 max-w-2xl">
            {TABS.map(([id, Icon, label]) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-[9px] text-xs font-medium transition-all duration-150 flex-1 justify-center ${
                  tab === id
                    ? 'bg-white text-zinc-900 shadow-sm shadow-zinc-200/50'
                    : 'text-zinc-500 hover:text-zinc-700 hover:bg-white/50'
                }`}
              >
                <Icon className="w-3.5 h-3.5" weight={tab === id ? 'fill' : 'regular'} />
                <span className="hidden lg:inline">{label}</span>
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-1 ml-auto">
            <button onClick={() => setShowSettings(true)} className="w-8 h-8 flex items-center justify-center rounded-xl bg-zinc-100 hover:bg-zinc-200 transition-colors">
              <Gear className="w-4 h-4 text-zinc-500" />
            </button>
            <button onClick={handleLogout} className="w-8 h-8 flex items-center justify-center rounded-xl bg-zinc-100 hover:bg-red-50 transition-colors" title="Logout">
              <SignOut className="w-4 h-4 text-zinc-400" />
            </button>
          </div>
        </div>

        {/* Pipeline strip */}
        <div className="border-t border-zinc-100 bg-zinc-50/80">
          <div className="max-w-[1440px] mx-auto px-6 py-1.5 flex items-center justify-center gap-1.5 text-[10px] font-medium">
            {[
              { label: 'Audio Heuristics', color: 'text-violet-600 bg-violet-50 border-violet-200' },
              { label: 'Lobster Trap DPI', color: 'text-indigo-600 bg-indigo-50 border-indigo-200' },
              { label: 'RAG Sanitizer', color: 'text-fuchsia-600 bg-fuchsia-50 border-fuchsia-200' },
              { label: 'Tool Policy', color: 'text-orange-600 bg-orange-50 border-orange-200' },
              { label: 'Egress Guard', color: 'text-red-600 bg-red-50 border-red-200' },
              { label: 'Gemini Evidence', color: 'text-emerald-600 bg-emerald-50 border-emerald-200' },
            ].map((s, i, arr) => (
              <span key={i} className="flex items-center gap-1.5">
                <span className={`px-2 py-0.5 rounded-md border ${s.color}`}>{s.label}</span>
                {i < arr.length - 1 && <span className="text-zinc-300">→</span>}
              </span>
            ))}
          </div>
        </div>
      </header>

      {/* Settings modal */}
      {showSettings && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={() => setShowSettings(false)}>
          <div className="bg-white rounded-2.5xl shadow-diffuse-lg p-8 w-full max-w-md border border-zinc-200/60" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-base font-bold text-zinc-800">Settings</h2>
              <button onClick={() => setShowSettings(false)} className="w-8 h-8 flex items-center justify-center rounded-xl hover:bg-zinc-100">
                <X className="w-4 h-4 text-zinc-400" />
              </button>
            </div>
            <div>
              <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Gemini API Key</label>
              <div className="flex gap-2 mt-1.5">
                <input type="password" value={apiKey} onChange={e => setApiKey(e.target.value)}
                  placeholder="AIza..." className="flex-1 px-4 py-2.5 rounded-xl border border-zinc-200 text-sm font-mono focus:outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100" />
                <button onClick={saveKey} disabled={keyStatus === 'saving'}
                  className="px-4 py-2.5 rounded-xl bg-zinc-900 text-white text-sm font-semibold hover:bg-zinc-800 active:scale-[0.98] transition-all disabled:opacity-40">
                  {keyStatus === 'saving' ? '...' : keyStatus === 'saved' ? <Check className="w-4 h-4" weight="bold" /> : 'Save'}
                </button>
              </div>
              {keyStatus === 'saved' && <p className="text-xs text-emerald-600 mt-1.5">Key saved successfully.</p>}
              {keyStatus === 'error' && <p className="text-xs text-red-500 mt-1.5">Failed to save key.</p>}
              <p className="text-[10px] text-zinc-400 mt-2">Without a key, mock classifiers are used. Get one at <a href="https://aistudio.google.com" className="text-emerald-600 underline" target="_blank">aistudio.google.com</a></p>
            </div>
          </div>
        </div>
      )}

      {/* Main content */}
      <main className="max-w-[1440px] mx-auto px-6 py-6 pb-20">
        {tab === 'suite' ? (
          <div>
            {/* Controls + stats */}
            <div className="flex items-center gap-6 mb-6">
              <button onClick={handleRun} disabled={running}
                className="flex items-center gap-2 px-5 py-2.5 bg-zinc-900 text-white rounded-xl text-sm font-semibold
                  hover:bg-zinc-800 active:scale-[0.98] transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm">
                {running ? (
                  <span className="flex items-center gap-2">
                    <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Running 12 scenarios...
                  </span>
                ) : (
                  <><CaretRight className="w-4 h-4" weight="fill" />Run Attack Suite (12 vectors)</>
                )}
              </button>

              {trustScore !== null && (
                <div className="flex items-center gap-5">
                  <TrustGauge score={trustScore} />
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2 text-xs">
                      <CheckCircle className="w-4 h-4 text-emerald-500" weight="fill" />
                      <span className="font-semibold text-zinc-700">{passed} scenarios passed</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <XCircle className="w-4 h-4 text-red-500" weight="fill" />
                      <span className="font-semibold text-zinc-700">{failed} threats detected</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <Warning className="w-4 h-4 text-amber-500" weight="fill" />
                      <span className="font-semibold text-zinc-700">{needsReview} need review</span>
                    </div>
                  </div>
                </div>
              )}

              {lastRunId && (
                <button onClick={() => setTab('report')}
                  className="ml-auto flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-700 font-medium transition-colors">
                  <Scroll className="w-3.5 h-3.5" />View Report
                </button>
              )}
            </div>

            {/* Two column layout */}
            <div className="grid grid-cols-[1fr_1.3fr] gap-6">
              {/* Scenario list */}
              <div className="space-y-1.5">
                {results.length > 0 ? results.map((r, i) => (
                  <button key={i} onClick={() => setSelectedIdx(i)}
                    className={`w-full text-left p-4 rounded-xl border transition-all duration-150 ${
                      i === selectedIdx
                        ? `bg-white border-zinc-300 shadow-diffuse`
                        : 'bg-transparent border-transparent hover:bg-white/70 hover:border-zinc-200'
                    }`}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1.5">
                          <span className={`w-1.5 h-5 rounded-full flex-shrink-0 ${
                            r.gate === 'FAIL' ? 'bg-red-400' : r.gate === 'NEEDS_REVIEW' ? 'bg-amber-400' : 'bg-emerald-400'
                          }`} />
                          <p className="text-xs font-semibold text-zinc-800 leading-snug truncate">{r.title}</p>
                        </div>
                        <div className="flex gap-1 flex-wrap ml-3.5">
                          {r.findings.slice(0, 3).map((f, j) => (
                            <span key={j} className={`px-1.5 py-0.5 rounded text-[9px] font-bold text-white ${BOUNDARY_COLORS[f.boundary] || 'bg-zinc-500'}`}>
                              {f.boundary.replace(/_/g, ' ')}
                            </span>
                          ))}
                          {r.findings.length > 3 && (
                            <span className="text-[9px] text-zinc-400 font-medium">+{r.findings.length - 3}</span>
                          )}
                        </div>
                      </div>
                      <span className={`text-[10px] font-bold whitespace-nowrap mt-0.5 ${GATE_COLORS[r.gate]}`}>{r.gate}</span>
                    </div>
                  </button>
                )) : (
                  <div className="diffuse-card flex flex-col items-center justify-center py-16 text-center">
                    <div className="w-12 h-12 rounded-2xl bg-zinc-100 flex items-center justify-center mb-4">
                      <Shield className="w-6 h-6 text-zinc-300" weight="duotone" />
                    </div>
                    <p className="text-sm font-semibold text-zinc-500 mb-1">Ready to test</p>
                    <p className="text-xs text-zinc-400 max-w-[22ch]">Run the attack suite to test 12 voice agent threat scenarios</p>
                  </div>
                )}
              </div>

              {/* Detail panel */}
              <div className="diffuse-card min-h-[480px] !p-6">
                {selected ? (
                  <div>
                    <div className="flex items-center justify-between mb-4 pb-3 border-b border-zinc-100">
                      <div>
                        <h3 className="text-sm font-bold text-zinc-900">{selected.title}</h3>
                        <span className={`inline-block mt-1 text-[10px] font-bold px-2 py-0.5 rounded-full border ${GATE_BG[selected.gate] || 'bg-zinc-100 border-zinc-200'} ${GATE_COLORS[selected.gate]}`}>
                          {selected.gate}
                        </span>
                      </div>
                      <div className="text-right">
                        <p className="text-[10px] text-zinc-400">Findings</p>
                        <p className={`text-2xl font-bold tabular-nums ${selected.findings.length > 0 ? 'text-red-500' : 'text-emerald-500'}`}>
                          {selected.findings.length}
                        </p>
                      </div>
                    </div>

                    {/* Trace */}
                    <div className="space-y-1 mb-5">
                      {selected.trace.map((e, i) => (
                        <div key={i} className={`flex items-start gap-2.5 px-3 py-2 rounded-lg text-xs ${
                          e.event_type === 'user_message' ? 'bg-blue-50/60' :
                          e.event_type.includes('tool') ? 'bg-amber-50/60' : 'bg-zinc-50'
                        }`}>
                          <span className="text-[9px] font-bold uppercase text-zinc-400 mt-0.5 w-20 shrink-0 tracking-wider">
                            {e.event_type.replace(/_/g, ' ')}
                          </span>
                          <span className="text-zinc-600 leading-relaxed">{(e.content || e.tool_name || '').slice(0, 130)}</span>
                        </div>
                      ))}
                    </div>

                    {/* Findings */}
                    <h4 className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 mb-2.5">
                      Security Findings ({selected.findings.length})
                    </h4>
                    <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1">
                      {selected.findings.map((f, i) => (
                        <div key={i} className="p-3 rounded-xl bg-red-50/60 border border-red-100/80">
                          <div className="flex items-center gap-1.5 flex-wrap mb-1.5">
                            <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold text-white ${BOUNDARY_COLORS[f.boundary] || 'bg-zinc-500'}`}>
                              {f.boundary.replace(/_/g, ' ')}
                            </span>
                            <span className="text-xs font-semibold text-zinc-700">{f.risk.replace(/_/g, ' ')}</span>
                            <span className="text-[9px] text-zinc-400 font-mono ml-auto">sev {f.severity.toFixed(2)}</span>
                            {f.lobster_decision && f.lobster_decision !== 'ALLOW' && (
                              <span className="text-[9px] font-bold bg-violet-100 text-violet-700 px-1.5 py-0.5 rounded">{f.lobster_decision}</span>
                            )}
                          </div>
                          <p className="text-[11px] text-zinc-500 leading-relaxed">{f.evidence.slice(0, 200)}</p>
                          {f.gemini_explanation && (
                            <div className="mt-2 p-2.5 rounded-lg bg-white border border-emerald-100">
                              <p className="text-[9px] font-bold uppercase tracking-wider text-emerald-600 mb-1">Gemini Analysis</p>
                              <p className="text-[11px] text-zinc-600 leading-relaxed">{f.gemini_explanation.slice(0, 280)}</p>
                            </div>
                          )}
                        </div>
                      ))}
                      {selected.findings.length === 0 && (
                        <div className="flex items-center gap-2 text-xs text-emerald-600">
                          <CheckCircle className="w-4 h-4" weight="fill" />
                          No security findings — scenario passed all checks
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center">
                    <Shield className="w-10 h-10 text-zinc-200 mb-3" weight="duotone" />
                    <p className="text-sm text-zinc-400 font-medium">Select a scenario</p>
                    <p className="text-xs text-zinc-300 mt-1">to view trace and security findings</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : tab === 'live' ? (
          <LiveMonitor />
        ) : tab === 'playground' ? (
          <Playground />
        ) : tab === 'rag' ? (
          <RagDemo />
        ) : tab === 'policy' ? (
          <div className="diffuse-card"><PolicyCompiler /></div>
        ) : tab === 'custom' ? (
          <CustomTest />
        ) : (
          <div className="diffuse-card">
            <h2 className="text-lg font-bold text-zinc-800 mb-1">Voice Agent Security Readiness Report</h2>
            <p className="text-sm text-zinc-400 mb-6">Automated security assessment with boundary-based scoring and AI-generated remediation guidance</p>
            {lastRunId ? (
              <iframe src={`/api/runs/${lastRunId}/report`} className="w-full h-[80vh] rounded-2xl border border-zinc-200" />
            ) : (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Scroll className="w-12 h-12 text-zinc-200 mb-3" weight="duotone" />
                <p className="text-sm text-zinc-400">Run the attack suite to generate a readiness report</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
