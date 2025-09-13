import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { startSession, getUsers, type SimpleUser } from '../lib/api'

export function Session() {
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [starting, setStarting] = useState(false)
  const navigate = useNavigate()
  const [userName, setUserName] = useState<string>(() => { try { return localStorage.getItem('eqi_user_name') || '' } catch { return '' } })
  const [users, setUsers] = useState<SimpleUser[]>([])

  useEffect(() => {
    const saved = localStorage.getItem('eqi_session_id')
    if (saved) setSessionId(Number(saved))
    // preload users for autocomplete (lightweight)
    getUsers().then(setUsers).catch(()=>{})
  }, [])

  async function handleStart() {
    setStarting(true)
    try {
      const id = await startSession(userName || undefined)
      setSessionId(id)
      localStorage.setItem('eqi_session_id', String(id))
      if (userName) try { localStorage.setItem('eqi_user_name', userName) } catch {}
      // Navigate user directly to Chat after creating a session
      try { navigate('/chat') } catch {}
    } finally {
      setStarting(false)
    }
  }

  function clearSession() {
    setSessionId(null)
    localStorage.removeItem('eqi_session_id')
  }

  return (
    <div className="card">
      <h2>Session</h2>
      <p>Ready to learn? Enter your name to start your personalized session.</p>
      <div className="row">
        <input list="user-list" value={userName} onChange={e=>setUserName(e.target.value)} placeholder="Student name (optional)" style={{minWidth:260}} />
        <datalist id="user-list">
          {users.map(u => (<option key={u.id} value={u.name} />))}
        </datalist>
        <button onClick={handleStart} disabled={starting || !userName.trim()}>Start Session</button>
        <button onClick={clearSession} disabled={!sessionId}>Clear</button>
      </div>
      <div className="muted" style={{marginTop:8}}>
        Session ID: {sessionId ?? '—'}
      </div>
    </div>
  )
}
