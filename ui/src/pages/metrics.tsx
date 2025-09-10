import React, { useEffect, useMemo, useState } from 'react'
import { getMetrics, getMetricsSeries, MetricsSeries, MetricsSnapshot } from '../lib/api'

function useLocalStorage(key: string, initial: string = ''): [string, (v: string)=>void] {
  const [v, setV] = useState<string>(() => {
    try { return localStorage.getItem(key) ?? initial } catch { return initial }
  })
  useEffect(() => { try { localStorage.setItem(key, v) } catch {} }, [key, v])
  return [v, setV]
}

export function Metrics() {
  const [sessionId, setSessionId] = useLocalStorage('eqi_metrics_session', '')
  const [since, setSince] = useLocalStorage('eqi_metrics_since', '240')
  const [bucket, setBucket] = useLocalStorage('eqi_metrics_bucket', 'minute')

  const [snap, setSnap] = useState<MetricsSnapshot | null>(null)
  const [series, setSeries] = useState<MetricsSeries | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string|null>(null)

  async function load() {
    setLoading(true); setError(null)
    try {
      const [s, ser] = await Promise.all([
        getMetrics({ sessionId: sessionId.trim() || undefined, sinceMinutes: Number(since) || undefined }),
        getMetricsSeries({ sessionId: sessionId.trim() || undefined, sinceMinutes: Number(since) || undefined, bucket: (bucket === 'hour' ? 'hour' : 'minute') })
      ])
      setSnap(s); setSeries(ser)
    } catch (e: any) { setError(e?.message || String(e)); setSnap(null); setSeries(null) }
    finally { setLoading(false) }
  }

  function useCurrentSession() { try { const sid = localStorage.getItem('eqi_session_id'); if (sid) setSessionId(sid) } catch {}
  }

  useEffect(() => { load() }, [])

  return (
    <div className="card">
      <h2>Metrics</h2>
      <div className="row" style={{flexWrap:'wrap', gap:10}}>
        <div style={{display:'flex', flexDirection:'column', gap:4}}>
          <label style={{fontSize:12, color:'var(--muted)'}}>Session ID</label>
          <input value={sessionId} onChange={e=>setSessionId(e.target.value)} placeholder="e.g., 3" />
        </div>
        <div style={{display:'flex', flexDirection:'column', gap:4}}>
          <label style={{fontSize:12, color:'var(--muted)'}}>Since (minutes)</label>
          <input type="number" min={1} value={since} onChange={e=>setSince(e.target.value)} />
        </div>
        <div style={{display:'flex', flexDirection:'column', gap:4}}>
          <label style={{fontSize:12, color:'var(--muted)'}}>Bucket</label>
          <select value={bucket} onChange={e=>setBucket(e.target.value)}>
            <option value="minute">minute</option>
            <option value="hour">hour</option>
          </select>
        </div>
        <div className="row" style={{gap:8, alignItems:'flex-end'}}>
          <button onClick={load} disabled={loading}>{loading? 'Loading…':'Refresh'}</button>
          <button onClick={useCurrentSession}>Use current session</button>
        </div>
      </div>
      {error && <div className="error" style={{marginTop:8}}>Error: {error}</div>}

      {/* KPIs */}
      {snap && (
        <div className="row" style={{gap:16, marginTop:12, flexWrap:'wrap'}}>
          <Kpi title="Turns" value={String(snap.turns_total)} />
          <Kpi title="Avg Reward" value={snap.avg_reward.toFixed(3)} />
          <Kpi title="Frustration Adapt" value={fmtPct(snap.frustration_adaptation_rate)} />
          <Kpi title="Tone Alignment" value={fmtPct(snap.tone_alignment_rate)} />
          <Kpi title="Last 10 Avg" value={snap.last_10_reward_avg.toFixed(3)} />
        </div>
      )}

      {/* Breakdowns */}
      {snap && (
        <div className="grid" style={{marginTop:12}}>
          <div>
            <h3 style={{margin:'4px 0'}}>Emotion breakdown</h3>
            <table style={{borderCollapse:'collapse'}}>
              <tbody>
              {Object.entries(snap.by_emotion || {}).map(([k,v]) => (
                <tr key={k}><Td>{k}</Td><Td>{String(v)}</Td></tr>
              ))}
              </tbody>
            </table>
          </div>
          <div>
            <h3 style={{margin:'4px 0'}}>Action distribution</h3>
            <table style={{borderCollapse:'collapse'}}>
              <tbody>
                {flattenActions(snap).map(([k,v]) => (
                  <tr key={k}><Td>{k}</Td><Td>{String(v)}</Td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Series table (compact) */}
      {series && (
        <div style={{marginTop:12}}>
          <h3 style={{margin:'4px 0'}}>Series ({series.bucket})</h3>
          <div className="muted" style={{fontSize:12, marginBottom:6}}>Last {series.points.length} points</div>
          <div style={{overflowX:'auto'}}>
            <table style={{borderCollapse:'collapse', width:'100%'}}>
              <thead>
                <tr>
                  <Th>ts</Th>
                  <Th>turns</Th>
                  <Th>avg_reward</Th>
                  <Th>frustrated</Th>
                </tr>
              </thead>
              <tbody>
                {series.points.map((p, i) => (
                  <tr key={i}>
                    <Td>{new Date(p.ts).toLocaleString()}</Td>
                    <Td>{String(p.turns)}</Td>
                    <Td>{p.avg_reward.toFixed(3)}</Td>
                    <Td>{String(p.frustrated)}</Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function flattenActions(s: MetricsSnapshot): Array<[string, number]> {
  const ad = s.action_distribution || {} as any
  return [
    ...Object.entries(ad.tone || {}).map(([k,v]) => [`tone.${k}`, Number(v) as number]),
    ...Object.entries(ad.pacing || {}).map(([k,v]) => [`pacing.${k}`, Number(v) as number]),
    ...Object.entries(ad.difficulty || {}).map(([k,v]) => [`difficulty.${k}`, Number(v) as number]),
    ...Object.entries(ad.next_step || {}).map(([k,v]) => [`next_step.${k}`, Number(v) as number]),
  ] as Array<[string, number]>
}

function fmtPct(v: number) { return (v*100).toFixed(1) + '%' }

function Kpi({ title, value }: { title: string, value: string }) {
  return (
    <div className="card" style={{minWidth:180}}>
      <div style={{color:'var(--muted)'}}>{title}</div>
      <div style={{fontSize:26, fontWeight:700, marginTop:6}}>{value}</div>
    </div>
  )
}

function Th({ children }: { children: React.ReactNode }) {
  return <th style={{ textAlign:'left', padding:'6px 8px', borderBottom:'1px solid #eee', fontSize:12, color:'var(--muted)' }}>{children}</th>
}

function Td({ children }: { children: React.ReactNode }) {
  return <td style={{ padding:'6px 8px', borderBottom:'1px solid #f0f0f0', verticalAlign:'top' }}>{children}</td>
}

