import { useState, useRef, useCallback } from 'react'
import { Broadcast, Stop, Warning, CheckCircle, SpeakerHigh, SpeakerSlash } from '@phosphor-icons/react'

function speak(text: string, isAgent: boolean) {
  if (!window.speechSynthesis) return
  window.speechSynthesis.cancel()
  const utter = new SpeechSynthesisUtterance(text)
  const voices = window.speechSynthesis.getVoices()
  if (isAgent) {
    const agentVoice = voices.find(v => v.name.includes('Google UK English Male') || v.name.includes('Male') || v.lang === 'en-GB')
    if (agentVoice) utter.voice = agentVoice
    utter.pitch = 0.9; utter.rate = 0.95
  } else {
    const callerVoice = voices.find(v => v.name.includes('Google US English') || v.name.includes('Female') || v.lang === 'en-US')
    if (callerVoice) utter.voice = callerVoice
    utter.pitch = 1.1; utter.rate = 1.05
  }
  window.speechSynthesis.speak(utter)
}

const BOUNDARY_COLORS: Record<string, string> = {
  USER_INPUT: 'bg-blue-500', AUDIO_LAYER: 'bg-violet-500', AGENT_RESPONSE: 'bg-amber-500',
  TOOL_ARGUMENT: 'bg-orange-500', TOOL_EXECUTION: 'bg-red-500', UNTRUSTED_CONTEXT: 'bg-fuchsia-600',
  EGRESS: 'bg-rose-600', POLICY_GAP: 'bg-zinc-500',
}

interface LiveEvent {
  type: string
  speaker?: string
  text?: string
  findings?: Array<{
    boundary: string; risk: string; severity: number
    lobster_decision?: string; evidence?: string
  }>
  gemini_classification?: { risk_type: string; confidence: number; boundary: string }
  expected_threats?: string[]
}

export default function LiveMonitor() {
  const [events, setEvents] = useState<LiveEvent[]>([])
  const [running, setRunning] = useState(false)
  const [ttsEnabled, setTtsEnabled] = useState(true)
  const wsRef = useRef<WebSocket | null>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const startSession = useCallback(() => {
    setRunning(true)
    setEvents([])
    window.speechSynthesis?.cancel()
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${location.host}/ws/live`)
    wsRef.current = ws

    ws.onopen = () => ws.send(JSON.stringify({ action: 'start_session' }))
    ws.onmessage = (msg) => {
      const event = JSON.parse(msg.data)
      if (event.type === 'transcript') {
        setEvents(prev => [...prev, event])
        if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight
        if (ttsEnabled && event.text) {
          const isAgent = !!(event as any).is_agent
          speak(event.text.replace(/\[whispered\]|\[normal\]/gi, '').trim(), isAgent)
        }
      } else if (event.type === 'session_complete') {
        setRunning(false)
        window.speechSynthesis?.cancel()
      }
    }
    ws.onerror = () => setRunning(false)
    ws.onclose = () => setRunning(false)
  }, [ttsEnabled])

  const stopSession = () => {
    wsRef.current?.close()
    setRunning(false)
    window.speechSynthesis?.cancel()
  }

  const totalFindings = events.filter(e => e.findings && e.findings.length > 0).length
  const totalThreats = events.filter(e => e.expected_threats && e.expected_threats.length > 0).length

  return (
    <div>
      {/* Controls */}
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={startSession}
          disabled={running}
          className="flex items-center gap-2.5 px-6 py-3 bg-zinc-900 text-white rounded-2xl text-sm font-semibold
            hover:bg-zinc-800 active:scale-[0.98] transition-all duration-200 disabled:opacity-40"
        >
          {running ? (
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-400 live-dot" />
              Session active...
            </span>
          ) : (
            <>
              <Broadcast className="w-5 h-5" weight="fill" /> Start Live Session
            </>
          )}
        </button>

        {running && (
          <button onClick={stopSession}
            className="flex items-center gap-2 px-4 py-3 bg-red-50 text-red-600 rounded-2xl text-sm font-semibold hover:bg-red-100 transition-colors">
            <Stop className="w-4 h-4" weight="fill" /> Stop
          </button>
        )}

        <button
          onClick={() => setTtsEnabled(v => !v)}
          title={ttsEnabled ? 'Mute voices' : 'Enable voices'}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold transition-colors ${
            ttsEnabled ? 'bg-indigo-100 text-indigo-700 hover:bg-indigo-200' : 'bg-zinc-100 text-zinc-400 hover:bg-zinc-200'
          }`}
        >
          {ttsEnabled
            ? <><SpeakerHigh className="w-4 h-4" weight="fill" /> Voice ON</>
            : <><SpeakerSlash className="w-4 h-4" weight="fill" /> Voice OFF</>}
        </button>

        {events.length > 0 && (
          <div className="flex items-center gap-4 text-xs font-medium text-zinc-500">
            <span className="font-mono tabular-nums">{events.length} turns</span>
            <span className="w-px h-3 bg-zinc-300" />
            <span className="flex items-center gap-1.5"><Warning className="w-3.5 h-3.5 text-amber-500" weight="fill" />{totalFindings} flagged</span>
            <span className="w-px h-3 bg-zinc-300" />
            <span className="flex items-center gap-1.5"><CheckCircle className="w-3.5 h-3.5 text-red-400" weight="fill" />{totalThreats} threats</span>
          </div>
        )}
      </div>

      {/* Split: transcript + alerts */}
      <div className="grid grid-cols-[1fr_340px] gap-8">
        {/* Transcript */}
        <div className="diffuse-card max-h-[65vh] overflow-y-auto" ref={listRef}>
          <h3 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-4">Live Transcript</h3>
          {events.length === 0 && !running && (
            <div className="flex flex-col items-center py-12 text-center">
              <Broadcast className="w-10 h-10 text-zinc-200 mb-3" weight="duotone" />
              <p className="text-sm font-medium text-zinc-400">Start a session to monitor voice agent calls</p>
              <p className="text-xs text-zinc-300 mt-1 max-w-[28ch]">Pre-recorded attack scenarios stream with realistic timing</p>
            </div>
          )}
          <div className="space-y-3">
            {events.map((e, i) => {
              const isAgent = (e as any).is_agent
              const isClear = !e.findings || e.findings.length === 0
              return (
                <div key={i} className={`p-4 rounded-xl border-l-[3px] transition-all animate-fadeIn ${
                  isAgent
                    ? isClear ? 'bg-emerald-50/40 border-l-emerald-400' : 'bg-amber-50/30 border-l-amber-400'
                    : e.findings && e.findings.length > 0 ? 'bg-red-50/30 border-l-red-400' : 'bg-blue-50/30 border-l-blue-400'
                }`}>
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-zinc-600">{e.speaker}</span>
                      {isAgent && <span className="text-[9px] font-bold bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full uppercase tracking-wide">AI</span>}
                    </div>
                    {e.findings && e.findings.length > 0 && (
                      <span className="text-[10px] font-bold text-red-500">{e.findings.length} finding{e.findings.length > 1 ? 's' : ''}</span>
                    )}
                  </div>
                  <p className="text-sm text-zinc-700 leading-relaxed">{e.text}</p>
                  {e.findings && e.findings.map((f, j) => (
                    <div key={j} className="flex items-center gap-2 mt-2 flex-wrap">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold text-white ${BOUNDARY_COLORS[f.boundary] || 'bg-zinc-500'}`}>
                        {f.boundary.replace(/_/g, ' ')}
                      </span>
                      <span className="text-[11px] font-semibold text-zinc-700">{f.risk.replace(/_/g, ' ')}</span>
                      {f.lobster_decision && (
                        <span className="text-[10px] font-semibold bg-violet-100 text-violet-700 px-1.5 py-0.5 rounded">{f.lobster_decision}</span>
                      )}
                    </div>
                  ))}
                  {e.gemini_classification && e.gemini_classification.risk_type !== 'NONE' && (
                    <p className="mt-2 text-[11px] font-medium text-indigo-600">
                      Gemini: {(e.gemini_classification.confidence * 100).toFixed(0)}% confidence — {e.gemini_classification.risk_type.replace(/_/g, ' ')}
                    </p>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Alerts panel */}
        <div className="diffuse-card">
          <h3 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-4">Security Alerts</h3>
          {events.filter(e => e.findings && e.findings.length > 0).length === 0 ? (
            <div className="flex flex-col items-center py-12 text-center">
              <div className="w-10 h-10 rounded-full bg-emerald-50 flex items-center justify-center mb-3">
                <CheckCircle className="w-5 h-5 text-emerald-400" weight="fill" />
              </div>
              <p className="text-sm text-zinc-400">No threats detected</p>
            </div>
          ) : (
            <div className="space-y-2">
              {events.filter(e => e.findings && e.findings.length > 0).map((e, i) => (
                <div key={i} className="p-3 rounded-xl bg-red-50/50 border border-red-100/50">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[11px] font-semibold text-red-700">{e.speaker}</span>
                    <span className="text-[10px] text-zinc-400">{new Date().toLocaleTimeString()}</span>
                  </div>
                  {e.findings?.map((f, j) => (
                    <div key={j} className="flex items-center gap-1.5 flex-wrap mt-1">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold text-white ${BOUNDARY_COLORS[f.boundary] || 'bg-zinc-500'}`}>
                        {f.boundary.replace('_', ' ')}
                      </span>
                      <span className="text-[11px] font-medium text-zinc-700">{f.risk.replace(/_/g, ' ')}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
