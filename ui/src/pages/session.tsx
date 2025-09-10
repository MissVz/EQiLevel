import React, { useEffect, useState } from 'react'
import { startSession } from '../lib/api'

export function Session() {
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [starting, setStarting] = useState(false)

  useEffect(() => {
    const saved = localStorage.getItem('eqi_session_id')
    if (saved) setSessionId(Number(saved))
  }, [])

  async function handleStart() {
    setStarting(true)
    try {
      const id = await startSession()
      setSessionId(id)
      localStorage.setItem('eqi_session_id', String(id))
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
      <p>Start a new learner session and store it locally for the Chat page.</p>
      <div className="row">
        <button onClick={handleStart} disabled={starting}>Start Session</button>
        <button onClick={clearSession} disabled={!sessionId}>Clear</button>
      </div>
      <div className="muted" style={{marginTop:8}}>
        Session ID: {sessionId ?? '—'}
      </div>
    </div>
  )
}

