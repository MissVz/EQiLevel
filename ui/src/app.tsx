import React, { useMemo, useState } from 'react'
import { Chat } from './pages/chat'
import { Session } from './pages/session'
import { Admin } from './pages/admin'
import { Settings } from './pages/settings'
import { Metrics } from './pages/metrics'
import { getApiBase } from './lib/api'

export function App() {
  const [tab, setTab] = useState<'session'|'chat'|'admin'|'metrics'|'settings'>('session')
  return (
    <div className="container">
      <header>
        <h1>EQiLevel</h1>
        <nav>
          <button className={tab==='session'?'active':''} onClick={()=>setTab('session')}>Session</button>
          <button className={tab==='chat'?'active':''} onClick={()=>setTab('chat')}>Chat</button>
          <button className={tab==='admin'?'active':''} onClick={()=>setTab('admin')}>Admin</button>
          <button className={tab==='metrics'?'active':''} onClick={()=>setTab('metrics')}>Metrics</button>
          <button className={tab==='settings'?'active':''} onClick={()=>setTab('settings')}>Settings</button>
          <a className="link" href={`${getApiBase()}/docs`} target="_blank" rel="noopener noreferrer">API Docs</a>
        </nav>
      </header>
      {tab === 'session' ? <Session /> : tab === 'admin' ? <Admin /> : tab === 'metrics' ? <Metrics /> : tab === 'settings' ? <Settings /> : <Chat />}
    </div>
  )
}
