import React, { useCallback, useEffect, useState } from 'react'
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
  const [auto, setAuto] = useLocalStorage('eqi_metrics_auto', '0')
  const [intervalSec, setIntervalSec] = useLocalStorage('eqi_metrics_interval', '10')

  const [snap, setSnap] = useState<MetricsSnapshot | null>(null)
  const [series, setSeries] = useState<MetricsSeries | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string|null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const [s, ser] = await Promise.all([
        getMetrics({ sessionId: sessionId.trim() || undefined, sinceMinutes: Number(since) || undefined }),
        getMetricsSeries({ sessionId: sessionId.trim() || undefined, sinceMinutes: Number(since) || undefined, bucket: (bucket === 'hour' ? 'hour' : 'minute') })
      ])
      setSnap(s); setSeries(ser)
    } catch (e: any) { setError(e?.message || String(e)); setSnap(null); setSeries(null) }
    finally { setLoading(false) }
  }, [sessionId, since, bucket])

  function useCurrentSession() { try { const sid = localStorage.getItem('eqi_session_id'); if (sid) setSessionId(sid) } catch {}
  }

  useEffect(() => { load() }, [load])
  useEffect(() => {
    if (auto !== '1') return
    const ms = Math.max(2, Number(intervalSec) || 10) * 1000
    const id = setInterval(load, ms)
    return () => clearInterval(id)
  }, [auto, intervalSec, load])

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
          <label className="muted" style={{display:'flex', alignItems:'center', gap:6}}>
            <input type="checkbox" checked={auto==='1'} onChange={e=>setAuto(e.target.checked ? '1':'0')} /> auto-refresh
          </label>
          <div className="row" style={{gap:6}}>
            <label className="muted">every</label>
            <input type="number" min={2} style={{width:60}} value={intervalSec} onChange={e=>setIntervalSec(e.target.value)} />
            <label className="muted">sec</label>
          </div>
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

      {/* Series charts */}
      {series && series.points && series.points.length>0 && (
        <div style={{marginTop:12}}>
          <h3 style={{margin:'4px 0'}}>Charts</h3>
          <MiniCharts series={series} />
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

// -------- Simple inline charts (no deps) --------
function MiniCharts({ series }: { series: MetricsSeries }) {
  const W = 640, H = 140, P = 24
  const pts = series.points
  // x index mapping
  const turns = pts.map(p=>p.turns)
  const rewards = pts.map(p=>p.avg_reward)
  const maxTurns = Math.max(1, ...turns)
  const minR = Math.min(...rewards, 0)
  const maxR = Math.max(...rewards, 1)
  const sx = (i:number)=> P + (W-2*P) * (i/(Math.max(1, pts.length-1)))
  // bar scale derived inline below
  const syReward = (v:number)=> H-P - (H-2*P) * ((v - minR) / (maxR - minR || 1))
  const pathR = rewards.map((v,i)=>`${i?'L':'M'}${sx(i)},${syReward(v)}`).join(' ')
  return (
    <div className="grid">
      <div className="card">
        <div className="muted">Avg reward</div>
        <svg width={W} height={H}>
          <rect x={0} y={0} width={W} height={H} fill="#fff" stroke="#eee" />
          <path d={pathR} fill="none" stroke="#3a86ff" strokeWidth={2} />
          {rewards.map((v,i)=> (
            <circle key={i} cx={sx(i)} cy={syReward(v)} r={2.5} fill="#3a86ff" />
          ))}
        </svg>
      </div>
      <div className="card">
        <div className="muted">Turns</div>
        <svg width={W} height={H}>
          <rect x={0} y={0} width={W} height={H} fill="#fff" stroke="#eee" />
          {turns.map((v,i)=>{
            const x = sx(i)
            const bw = (W-2*P)/Math.max(pts.length,1) * 0.8
            const h = (H-2*P) * (v/maxTurns)
            const y = H-P-h
            return <rect key={i} x={x-bw/2} y={y} width={bw} height={h} fill="#94a3b8" />
          })}
        </svg>
      </div>
    </div>
  )
}
