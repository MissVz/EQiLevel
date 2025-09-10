import React, { useMemo, useState } from 'react'
import { Chat } from './pages/chat'
import { Session } from './pages/session'
import { API_BASE } from './lib/api'

export function App() {
  const [tab, setTab] = useState<'session'|'chat'>('session')
  const metricsHref = useMemo(() => {
    try {
      const sid = window?.localStorage?.getItem('eqi_session_id')
      const base = `${API_BASE}/api/v1/metrics/dashboard`
      return sid ? `${base}?session_id=${encodeURIComponent(sid)}` : base
    } catch { return `${API_BASE}/api/v1/metrics/dashboard` }
  }, [])
  return (
    <div className="container">
      <header>
        <h1>EQiLevel</h1>
        <nav>
          <button className={tab==='session'?'active':''} onClick={()=>setTab('session')}>Session</button>
          <button className={tab==='chat'?'active':''} onClick={()=>setTab('chat')}>Chat</button>
          <a className="link" href={metricsHref} target="_blank" rel="noopener noreferrer">Metrics</a>
          <a className="link" href={`${API_BASE}/docs`} target="_blank" rel="noopener noreferrer">API Docs</a>
        </nav>
      </header>
      {tab === 'session' ? <Session /> : <Chat />}
    </div>
  )
}
