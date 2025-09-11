import React, { useEffect, useState } from 'react'
import { NavLink, Routes, Route, Navigate } from 'react-router-dom'
import { Chat } from './pages/chat'
import { Session } from './pages/session'
import { Admin } from './pages/admin'
import { Settings } from './pages/settings'
import { Metrics } from './pages/metrics'
import { getApiBase, getHealthFull, type HealthFull } from './lib/api'
import { ErrorBoundary } from './components/ErrorBoundary'

export function App() {
  const [health, setHealth] = useState<HealthFull | null>(null)
  const [healthErr, setHealthErr] = useState<string | null>(null)
  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const h = await getHealthFull()
        if (alive) { setHealth(h); setHealthErr(null) }
      } catch (e: any) {
        if (alive) { setHealth(null); setHealthErr(e?.message || String(e)) }
      }
    }
    load()
    const id = setInterval(load, 30000)
    return () => { alive = false; clearInterval(id) }
  }, [])
  const dotClass = health ? (health.status === 'ok' ? 'dot ok' : 'dot warn') : 'dot err'
  const dotTitle = health ? `OpenAI: ${health.components.openai_key}; DB: ${health.components.database}` : (healthErr || 'Health unknown')
  return (
    <div className="container">
      <header>
        <h1>EQiLevel</h1>
        <nav>
          <NavLink className={({isActive})=> isActive? 'active':''} to="/session"><button>Session</button></NavLink>
          <NavLink className={({isActive})=> isActive? 'active':''} to="/chat"><button>Chat</button></NavLink>
          <NavLink className={({isActive})=> isActive? 'active':''} to="/admin"><button>Admin</button></NavLink>
          <NavLink className={({isActive})=> isActive? 'active':''} to="/metrics"><button>Metrics</button></NavLink>
          <NavLink className={({isActive})=> isActive? 'active':''} to="/settings"><button>Settings</button></NavLink>
          <a className="link" href={`${getApiBase()}/docs`} target="_blank" rel="noopener noreferrer">API Docs</a>
          <span className="muted" title={dotTitle} style={{display:'inline-flex', alignItems:'center', gap:6}}>
            <span className={dotClass} />
            {health ? (health.status === 'ok' ? 'healthy' : 'degraded') : 'unknown'}
          </span>
        </nav>
      </header>
      <ErrorBoundary>
        <Routes>
          <Route path="/" element={<Navigate to="/session" replace />} />
          <Route path="/session" element={<Session />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="/metrics" element={<Metrics />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/session" replace />} />
        </Routes>
      </ErrorBoundary>
    </div>
  )
}
