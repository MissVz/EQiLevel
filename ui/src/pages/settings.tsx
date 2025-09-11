import React, { useEffect, useState } from 'react'
import { getApiBase, getAdminKey, getHealthFull, validateAdminKey, getSystemPrompt, setSystemPrompt, type HealthFull } from '../lib/api'

function useLocalStorage(key: string, initial: string = ''): [string, (v: string)=>void] {
  const [v, setV] = useState<string>(() => {
    try { return localStorage.getItem(key) ?? initial } catch { return initial }
  })
  useEffect(() => { try { localStorage.setItem(key, v) } catch {} }, [key, v])
  return [v, setV]
}

type Mic = { deviceId: string; label: string }

export function Settings() {
  const [apiBase, setApiBase] = useLocalStorage('eqi_api_base', getApiBase())
  const [adminKey, setAdminKey] = useLocalStorage('eqi_admin_key', getAdminKey() || '')
  const [mics, setMics] = useState<Mic[]>([])
  const [micId, setMicId] = useLocalStorage('eqi_mic_id', '')
  const [vadAuto, setVadAuto] = useLocalStorage('eqi_vad_autostop', '1')
  const [vadThresh, setVadThresh] = useLocalStorage('eqi_vad_thresh', '0.03')
  const [vadMinMs, setVadMinMs] = useLocalStorage('eqi_vad_min_ms', '1200')
  const [vadSilMs, setVadSilMs] = useLocalStorage('eqi_vad_sil_ms', '1200')
  const [chatHist, setChatHist] = useLocalStorage('eqi_chat_hist_turns', '8')
  const [err, setErr] = useState<string|null>(null)
  const [health, setHealth] = useState<HealthFull | null>(null)
  const [healthBusy, setHealthBusy] = useState(false)
  const [adminBusy, setAdminBusy] = useState(false)
  const [adminValid, setAdminValid] = useState<null | boolean>(null)
  const [showKey, setShowKey] = useState(false)
  const [sysPrompt, setSysPrompt] = useState<string>('')
  const [sysBusy, setSysBusy] = useState(false)
  const examplePrompt = `You are a patient, encouraging K–12 tutor.
Follow these rules every turn:
- Persona: warm, supportive, and precise; avoid jargon.
- Tone: {tone}. Pacing: {pacing}. Difficulty: {difficulty}. Style: {style}.
- Next step to prioritize: {next_step} (one of: explain, example, prompt, quiz, review).
- Use small steps, concrete examples, and growth‑mindset language.
- If the learner seems stuck, offer a minimal hint first; then scaffold.
- Never reveal the full solution immediately; guide them to it.
- Keep replies to 3–5 short sentences.
- End with exactly ONE question (only a single “?” in the whole reply).

Use the "Curriculum objectives" (if provided) to guide strategies, vocabulary, and examples. Respect stated prerequisites; if a gap is detected, briefly remediate.

Output format (JSON object):
- support: string (concise explanation, hints, or encouragement; optional)
- question: string (exactly one question, ends with “?”)
- next_step: one of [explain, example, prompt, quiz, review]
`;

  async function listDevices(requirePermission = false) {
    setErr(null)
    try {
      if (requirePermission) {
        // Request a one-time stream to get labels populated
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        stream.getTracks().forEach(t => t.stop())
      }
      const devs = await navigator.mediaDevices.enumerateDevices()
      const options = devs.filter(d => d.kind === 'audioinput').map(d => ({ deviceId: d.deviceId, label: d.label || '(microphone)' }))
      setMics(options)
    } catch (e: any) {
      setErr(e?.message || String(e))
    }
  }

  useEffect(() => { listDevices(false) }, [])
  useEffect(() => {
    // Load system prompt if we have a key; soft-fail otherwise
    const k = adminKey?.trim()
    if (!k) return
    getSystemPrompt(k).then(setSysPrompt).catch(()=>{})
  }, [adminKey])

  function applyDefaults() {
    setApiBase(location.origin)
  }

  async function checkHealth() {
    setHealthBusy(true); setErr(null)
    try {
      const h = await getHealthFull()
      setHealth(h)
    } catch (e: any) {
      setErr(e?.message || String(e))
      setHealth(null)
    } finally { setHealthBusy(false) }
  }

  async function checkAdminKey() {
    setAdminBusy(true); setErr(null)
    try {
      const ok = await validateAdminKey()
      setAdminValid(ok)
    } catch (e: any) {
      setErr(e?.message || String(e))
      setAdminValid(false)
    } finally { setAdminBusy(false) }
  }

  function clearAll() {
    try { localStorage.removeItem('eqi_api_base') } catch {}
    try { localStorage.removeItem('eqi_admin_key') } catch {}
    try { localStorage.removeItem('eqi_mic_id') } catch {}
    try { localStorage.removeItem('eqi_vad_autostop') } catch {}
    try { localStorage.removeItem('eqi_vad_thresh') } catch {}
    try { localStorage.removeItem('eqi_vad_min_ms') } catch {}
    try { localStorage.removeItem('eqi_vad_sil_ms') } catch {}
    setHealth(null); setAdminValid(null)
  }

  return (
    <div className="card">
      <h2>Settings</h2>
      <div className="row" style={{flexWrap:'wrap', gap:10}}>
        <div style={{display:'flex', flexDirection:'column', gap:4, minWidth:260}}>
          <label style={{fontSize:12, color:'var(--muted)'}}>API Base</label>
          <input value={apiBase} onChange={e=>setApiBase(e.target.value)} placeholder="http://127.0.0.1:8000" />
          <div className="muted" style={{fontSize:12}}>Current default: {getApiBase()}</div>
        </div>
        <div style={{display:'flex', flexDirection:'column', gap:4, minWidth:320}}>
          <label style={{fontSize:12, color:'var(--muted)'}}>Admin Key (X-Admin-Key)</label>
          <div className="row" style={{gap:6}}>
            <input type={showKey ? 'text':'password'} value={adminKey} onChange={e=>setAdminKey(e.target.value)} placeholder="Paste admin key" />
            <button onClick={()=>setShowKey(s=>!s)}>{showKey? 'Hide':'Show'}</button>
            <button onClick={checkAdminKey} disabled={adminBusy || !adminKey.trim()}>{adminBusy? 'Checking…':'Validate'}</button>
          </div>
          <div className="muted" style={{fontSize:12}}>
            Status: {adminValid==null? 'unknown' : adminValid? 'valid ✅' : 'invalid ❌'}
          </div>
        </div>
        <div style={{display:'flex', flexDirection:'column', gap:4, minWidth:260}}>
          <label style={{fontSize:12, color:'var(--muted)'}}>Microphone</label>
          <select value={micId} onChange={e=>setMicId(e.target.value)}>
            <option value="">System default</option>
            {mics.map(m => (
              <option key={m.deviceId} value={m.deviceId}>{m.label || `(id:${m.deviceId.slice(0,6)})`}</option>
            ))}
          </select>
          <div className="row" style={{gap:8}}>
            <button onClick={()=>listDevices(true)}>Grant mic + Refresh</button>
            <button onClick={()=>listDevices(false)}>Refresh</button>
          </div>
        </div>
        <div className="row" style={{gap:8, alignItems:'flex-end'}}>
          <button onClick={applyDefaults}>Use this origin</button>
          <button onClick={checkHealth} disabled={healthBusy}>Check Health</button>
          {health && (
            <span className="muted" style={{display:'inline-flex', alignItems:'center', gap:6}}>
              <span className={`dot ${health.status==='ok'?'ok':(health.status==='degraded'?'warn':'err')}`} />
              {health.status}
            </span>
          )}
        </div>
      </div>
      <div style={{marginTop:16}}>
        <h3 style={{margin:'6px 0'}}>System Prompt (Admin) <span className="muted" title={examplePrompt} style={{cursor:'help'}}>ⓘ</span></h3>
        <div style={{display:'flex', flexDirection:'column', gap:6}}>
          <textarea rows={10} value={sysPrompt} onChange={e=>setSysPrompt(e.target.value)} placeholder="Edit system prompt here (use {tone}, {pacing}, {difficulty}, {style}, {next_step})" />
          <div className="row" style={{gap:8}}>
            <button onClick={()=>{ if (sysPrompt && sysPrompt.trim() && sysPrompt !== examplePrompt) { if (!window.confirm('Replace current prompt with the example?')) return; } setSysPrompt(examplePrompt) }}>Insert example</button>
            <button onClick={async ()=>{ if (!adminKey?.trim()) return; setSysBusy(true); try{ await setSystemPrompt(adminKey, sysPrompt); } finally { setSysBusy(false) } }} disabled={!adminKey?.trim() || sysBusy}>Save</button>
            <button onClick={async ()=>{ if (!adminKey?.trim()) return; setSysBusy(true); try{ await setSystemPrompt(adminKey, ''); setSysPrompt(''); } finally { setSysBusy(false) } }} disabled={!adminKey?.trim() || sysBusy}>Use default</button>
          </div>
          <div className="muted" style={{fontSize:12}}>Saving replaces the live system prompt immediately. “Use default” clears the override and falls back to the code template.</div>
        </div>
      </div>
      <div style={{marginTop:16}}>
        <h3 style={{margin:'6px 0'}}>Conversation</h3>
        <div className="row" style={{flexWrap:'wrap', gap:10}}>
          <div style={{display:'flex', flexDirection:'column', gap:4, minWidth:220}}>
            <label style={{fontSize:12, color:'var(--muted)'}}>Chat history turns (1–20)</label>
            <input type="number" min={1} max={20} value={chatHist} onChange={e=>setChatHist(e.target.value)} />
            <div className="muted" style={{fontSize:12}}>Controls how many prior turns are sent to the tutor.</div>
          </div>
        </div>
      </div>
      <div style={{marginTop:16}}>
        <h3 style={{margin:'6px 0'}}>Voice / VAD</h3>
        <div className="row" style={{flexWrap:'wrap', gap:10}}>
          <label className="muted" style={{display:'flex', alignItems:'center', gap:6}}>
            <input type="checkbox" checked={vadAuto !== '0'} onChange={e=>setVadAuto(e.target.checked ? '1' : '0')} />
            Auto-stop on silence (default)
          </label>
          <div style={{display:'flex', flexDirection:'column', gap:4, minWidth:200}}>
            <label style={{fontSize:12, color:'var(--muted)'}}>Silence threshold (RMS)</label>
            <input type="number" step="0.005" min="0.001" max="0.2" value={vadThresh} onChange={e=>setVadThresh(e.target.value)} />
            <div className="muted" style={{fontSize:12}}>Typical: 0.02–0.05 (raise to stop faster)</div>
          </div>
          <div style={{display:'flex', flexDirection:'column', gap:4, minWidth:200}}>
            <label style={{fontSize:12, color:'var(--muted)'}}>Min speak time (ms)</label>
            <input type="number" min="0" value={vadMinMs} onChange={e=>setVadMinMs(e.target.value)} />
          </div>
          <div style={{display:'flex', flexDirection:'column', gap:4, minWidth:220}}>
            <label style={{fontSize:12, color:'var(--muted)'}}>Silence duration to stop (ms)</label>
            <input type="number" min="200" value={vadSilMs} onChange={e=>setVadSilMs(e.target.value)} />
          </div>
          <div className="row" style={{gap:8, alignItems:'flex-end'}}>
            <button onClick={()=>{ setVadAuto('1'); setVadThresh('0.03'); setVadMinMs('1200'); setVadSilMs('1200') }}>Reset VAD</button>
          </div>
        </div>
        {health?.stream && (
          <div className="muted" style={{marginTop:8, fontSize:12}}>
            Server stream timeouts: max {health.stream.max_seconds ?? '—'}s, stale-partial {health.stream.stale_partial_seconds ?? '—'}s
          </div>
        )}
      </div>
      {err && <div className="error" style={{marginTop:8}}>Error: {err}</div>}
      <div className="row" style={{marginTop:8, gap:8}}>
        <div className="muted">Values are stored in localStorage for this origin.</div>
        <button onClick={clearAll}>Clear all</button>
      </div>
    </div>
  )
}
