import React, { useEffect, useMemo, useState } from 'react'
import { AdminTurn, getAdminKey, getAdminTurns } from '../lib/api'

function useLocalStorage(key: string, initial: string = ''): [string, (v: string)=>void] {
  const [v, setV] = useState<string>(() => {
    try { return localStorage.getItem(key) ?? initial } catch { return initial }
  })
  useEffect(() => { try { localStorage.setItem(key, v) } catch {} }, [key, v])
  return [v, setV]
}

export function Admin() {
  const [adminKey, setAdminKey] = useLocalStorage('eqi_admin_key', getAdminKey() || '')
  const [sessionId, setSessionId] = useLocalStorage('eqi_admin_session', '')
  const [since, setSince] = useLocalStorage('eqi_admin_since', '240')
  const [limit, setLimit] = useLocalStorage('eqi_admin_limit', '50')
  const [order, setOrder] = useLocalStorage('eqi_admin_order', 'desc')
  const [rows, setRows] = useState<AdminTurn[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true); setError(null)
    try {
      const data = await getAdminTurns({
        sessionId: sessionId.trim() || undefined,
        sinceMinutes: Number(since) || undefined,
        limit: Number(limit) || undefined,
        order: (order === 'asc' ? 'asc' : 'desc')
      })
      setRows(data)
    } catch (e: any) {
      setError(e?.message || String(e))
      setRows([])
    } finally { setLoading(false) }
  }

  function useCurrentSession() {
    try {
      const sid = localStorage.getItem('eqi_session_id')
      if (sid) setSessionId(sid)
    } catch {}
  }

  useEffect(() => { load() }, [])

  return (
    <div className="card">
      <h2>Admin</h2>
      <div className="muted" style={{marginBottom:8}}>Requires X-Admin-Key (set below or via VITE_ADMIN_KEY)</div>
      <div className="row" style={{flexWrap:'wrap', gap:10}}>
        <div style={{display:'flex', flexDirection:'column', gap:4}}>
          <label style={{fontSize:12, color:'var(--muted)'}}>Admin Key</label>
          <input value={adminKey} onChange={e=>setAdminKey(e.target.value)} placeholder="X-Admin-Key" />
        </div>
        <div style={{display:'flex', flexDirection:'column', gap:4}}>
          <label style={{fontSize:12, color:'var(--muted)'}}>Session ID</label>
          <input value={sessionId} onChange={e=>setSessionId(e.target.value)} placeholder="e.g., 3" />
        </div>
        <div style={{display:'flex', flexDirection:'column', gap:4}}>
          <label style={{fontSize:12, color:'var(--muted)'}}>Since (minutes)</label>
          <input type="number" min={1} value={since} onChange={e=>setSince(e.target.value)} />
        </div>
        <div style={{display:'flex', flexDirection:'column', gap:4}}>
          <label style={{fontSize:12, color:'var(--muted)'}}>Limit</label>
          <input type="number" min={1} max={200} value={limit} onChange={e=>setLimit(e.target.value)} />
        </div>
        <div style={{display:'flex', flexDirection:'column', gap:4}}>
          <label style={{fontSize:12, color:'var(--muted)'}}>Order</label>
          <select value={order} onChange={e=>setOrder(e.target.value)}>
            <option value="desc">desc</option>
            <option value="asc">asc</option>
          </select>
        </div>
        <div className="row" style={{gap:8, alignItems:'flex-end'}}>
          <button onClick={load} disabled={loading}>{loading? 'Loading…':'Refresh'}</button>
          <button onClick={useCurrentSession} title="Use Session ID from localStorage">Use current session</button>
        </div>
      </div>

      {error && <div className="error" style={{marginTop:8}}>Error: {error}</div>}
      <div className="muted" style={{marginTop:8}}>
        {rows.length} result(s)
      </div>
      <div style={{overflowX:'auto', marginTop:8}}>
        <table style={{borderCollapse:'collapse', width:'100%'}}>
          <thead>
            <tr>
              <th style={th}>id</th>
              <th style={th}>session</th>
              <th style={th}>created_at</th>
              <th style={th}>user_text</th>
              <th style={th}>reply_text</th>
              <th style={th}>reward</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.id}>
                <td style={td}>{r.id}</td>
                <td style={td}>{r.session_id}</td>
                <td style={td}>{new Date(r.created_at).toLocaleString()}</td>
                <td style={td} title={r.user_text}>{truncate(r.user_text, 120)}</td>
                <td style={td} title={r.reply_text}>{truncate(r.reply_text, 120)}</td>
                <td style={td}>{Number(r.reward).toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const th: React.CSSProperties = { textAlign:'left', padding:'6px 8px', borderBottom:'1px solid #eee', fontSize:12, color:'var(--muted)' }
const td: React.CSSProperties = { padding:'6px 8px', borderBottom:'1px solid #f0f0f0', verticalAlign:'top' }

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n-1) + '…' : s
}

