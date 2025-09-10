import React, { useMemo, useState } from 'react'
import { Chat } from './pages/chat'
import { Session } from './pages/session'
import { Admin } from './pages/admin'
import { Settings } from './pages/settings'
import { getApiBase } from './lib/api'

export function App() {
  const [tab, setTab] = useState<'session'|'chat'|'admin'|'settings'>('session')
  const metricsHref = (() => {
    try {
      const sid = window?.localStorage?.getItem('eqi_session_id')
      const base = `${getApiBase()}/api/v1/metrics/dashboard`
      return sid ? `${base}?session_id=${encodeURIComponent(sid)}` : base
    } catch { return `${getApiBase()}/api/v1/metrics/dashboard` }
  })()
  return (
    <div className="container">
      <header>
        <h1>EQiLevel</h1>
        <nav>
          <button className={tab==='session'?'active':''} onClick={()=>setTab('session')}>Session</button>
          <button className={tab==='chat'?'active':''} onClick={()=>setTab('chat')}>Chat</button>
          <button className={tab==='admin'?'active':''} onClick={()=>setTab('admin')}>Admin</button>
          <button className={tab==='settings'?'active':''} onClick={()=>setTab('settings')}>Settings</button>
          <a className="link" href={metricsHref} target="_blank" rel="noopener noreferrer">Metrics</a>
          <a className="link" href={`${getApiBase()}/docs`} target="_blank" rel="noopener noreferrer">API Docs</a>
        </nav>
      </header>
      {tab === 'session' ? <Session /> : tab === 'admin' ? <Admin /> : tab === 'settings' ? <Settings /> : <Chat />}
    </div>
  )
}
