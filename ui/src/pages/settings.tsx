import React, { useEffect, useState } from 'react'
import { getApiBase, getAdminKey } from '../lib/api'

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
  const [err, setErr] = useState<string|null>(null)

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

  function applyDefaults() {
    setApiBase(location.origin)
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
        <div style={{display:'flex', flexDirection:'column', gap:4, minWidth:260}}>
          <label style={{fontSize:12, color:'var(--muted)'}}>Admin Key (X-Admin-Key)</label>
          <input value={adminKey} onChange={e=>setAdminKey(e.target.value)} placeholder="Paste admin key" />
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
        </div>
      </div>
      {err && <div className="error" style={{marginTop:8}}>Error: {err}</div>}
      <div className="muted" style={{marginTop:8}}>Values are stored in localStorage for this origin.</div>
    </div>
  )
}

