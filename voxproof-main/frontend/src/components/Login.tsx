import { useState } from 'react'
import { Shield, Envelope, Lock, UserPlus, SignIn, Spinner, Microphone, Robot, FileText, ChartBar } from '@phosphor-icons/react'

const FEATURES = [
  { icon: Microphone, label: 'Audio-layer threat detection before transcription' },
  { icon: Shield, label: 'Lobster Trap deep policy inspection (MIT)' },
  { icon: Robot, label: 'Gemini Function Calling interception at tool boundary' },
  { icon: FileText, label: 'Automated compliance evidence & audit report' },
  { icon: ChartBar, label: 'Trust score with attack scenario suite (12 vectors)' },
]

const PAPERS = [
  'AudioHijack 79–96% success rate (IEEE S&P 2026)',
  'Agentic Red Teaming: 85% in 3h (May 2026)',
  'ToolSafe: step-level guardrails (Jan 2026)',
]

export default function Login({ onLogin }: { onLogin: (token: string, email: string) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
    if (!email || !password) return
    setError(''); setLoading(true)
    try {
      const endpoint = mode === 'login' ? '/api/auth/login' : '/api/auth/register'
      const r = await fetch(endpoint, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const data = await r.json()
      if (data.error) { setError(data.error); setLoading(false); return }
      onLogin(data.token, data.user.email)
    } catch { setError('Connection failed'); setLoading(false) }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50">
        <div className="text-center">
          <Spinner className="w-8 h-8 text-emerald-500 animate-spin mx-auto mb-3" />
          <p className="text-sm text-zinc-500">{mode === 'login' ? 'Signing in...' : 'Creating account...'}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex">
      {/* Left: dark hero panel */}
      <div className="hidden lg:flex flex-col justify-between w-[460px] bg-zinc-950 p-10 relative overflow-hidden flex-shrink-0">
        {/* Radial glow */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_30%_40%,rgba(16,185,129,0.10),transparent_65%)] pointer-events-none" />
        <div className="absolute bottom-0 right-0 w-64 h-64 bg-[radial-gradient(circle,rgba(99,102,241,0.06),transparent_70%)] pointer-events-none" />

        {/* Logo */}
        <div className="flex items-center gap-3 relative z-10">
          <div className="w-9 h-9 rounded-xl bg-emerald-500 flex items-center justify-center shadow-lg shadow-emerald-500/30">
            <Shield className="w-5 h-5 text-white" weight="fill" />
          </div>
          <div>
            <span className="text-lg font-bold text-white tracking-tight">VoxProof</span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="text-[9px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded-full uppercase tracking-wider">Track 1</span>
              <span className="text-[9px] font-semibold bg-indigo-500/20 text-indigo-400 border border-indigo-500/20 px-1.5 py-0.5 rounded-full uppercase tracking-wider">Lobster Trap</span>
              <span className="text-[9px] font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/20 px-1.5 py-0.5 rounded-full uppercase tracking-wider">Gemini</span>
            </div>
          </div>
        </div>

        {/* Headline + features */}
        <div className="space-y-6 relative z-10">
          <div>
            <h2 className="text-2xl font-bold text-white leading-tight mb-2">
              Protect voice AI agents<br />before they betray you.
            </h2>
            <p className="text-sm text-zinc-400 leading-relaxed">
              Layered runtime security gate: audio heuristics → Lobster Trap DPI → Gemini judge → RAG sanitizer → tool policy → egress guard.
            </p>
          </div>
          <div className="space-y-3">
            {FEATURES.map(f => (
              <div key={f.label} className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-lg bg-zinc-800 border border-zinc-700/50 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <f.icon className="w-3 h-3 text-emerald-400" weight="duotone" />
                </div>
                <span className="text-xs text-zinc-400 leading-relaxed">{f.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Academic refs */}
        <div className="relative z-10 space-y-2">
          <p className="text-[9px] text-zinc-600 uppercase tracking-widest font-semibold">Academic foundation</p>
          {PAPERS.map(p => (
            <p key={p} className="text-[11px] text-zinc-500 font-mono">{p}</p>
          ))}
        </div>
      </div>

      {/* Right: form */}
      <div className="flex-1 flex items-center justify-center bg-zinc-50 p-8">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="lg:hidden text-center mb-8">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500 flex items-center justify-center mx-auto mb-3 shadow-lg shadow-emerald-500/30">
              <Shield className="w-7 h-7 text-white" weight="fill" />
            </div>
            <h1 className="text-xl font-bold text-zinc-900">VoxProof</h1>
            <p className="text-sm text-zinc-500 mt-1">Voice Agent Security Gateway</p>
          </div>

          <div className="mb-6">
            <h2 className="text-2xl font-bold text-zinc-900">
              {mode === 'login' ? 'Welcome back' : 'Create account'}
            </h2>
            <p className="text-sm text-zinc-500 mt-1">
              {mode === 'login' ? 'Sign in to your security dashboard' : 'Start protecting your voice agents'}
            </p>
          </div>

          <div className="bg-white rounded-2.5xl border border-zinc-200/60 shadow-diffuse p-6">
            {/* Mode toggle */}
            <div className="flex mb-6 bg-zinc-100 rounded-xl p-1">
              <button onClick={() => setMode('login')}
                className={`flex-1 py-2 rounded-[10px] text-sm font-semibold transition-all ${mode === 'login' ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-500 hover:text-zinc-700'}`}>
                <SignIn className="w-4 h-4 inline mr-1.5" weight={mode === 'login' ? 'fill' : 'regular'} />Sign In
              </button>
              <button onClick={() => setMode('register')}
                className={`flex-1 py-2 rounded-[10px] text-sm font-semibold transition-all ${mode === 'register' ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-500 hover:text-zinc-700'}`}>
                <UserPlus className="w-4 h-4 inline mr-1.5" weight={mode === 'register' ? 'fill' : 'regular'} />Register
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1.5 block">Email</label>
                <div className="relative">
                  <Envelope className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400" />
                  <input value={email} onChange={e => setEmail(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                    className="w-full pl-10 pr-4 py-3 rounded-xl border border-zinc-200 text-sm focus:outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 transition-all"
                    placeholder="you@company.com" autoFocus />
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1.5 block">Password</label>
                <div className="relative">
                  <Lock className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400" />
                  <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                    className="w-full pl-10 pr-4 py-3 rounded-xl border border-zinc-200 text-sm focus:outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 transition-all"
                    placeholder="Min 6 characters" />
                </div>
              </div>

              {error && (
                <div className="flex items-center gap-2 text-xs text-red-600 bg-red-50 border border-red-100 px-3 py-2.5 rounded-xl">
                  <Shield className="w-3.5 h-3.5 flex-shrink-0" weight="fill" />
                  {error}
                </div>
              )}

              <button onClick={handleSubmit} disabled={loading || !email || !password}
                className="w-full py-3 bg-zinc-900 text-white rounded-xl text-sm font-semibold hover:bg-zinc-800 active:scale-[0.98] transition-all disabled:opacity-40 mt-2">
                {mode === 'login' ? 'Sign In →' : 'Create Account →'}
              </button>
            </div>
          </div>

          <p className="text-center text-[11px] text-zinc-400 mt-4">
            No credit card required · MIT-licensed · Open source
          </p>
        </div>
      </div>
    </div>
  )
}
