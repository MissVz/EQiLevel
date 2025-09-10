import React, { useEffect, useMemo, useState } from 'react'
import { postAudioTurn, postTextTurn } from '../lib/api'
import { Recorder } from '../components/recorder'

type Turn = {
  role: 'user'|'tutor'
  text: string
  raw?: any
}

export function Chat() {
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [text, setText] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [busy, setBusy] = useState(false)
  const hasSession = sessionId != null

  useEffect(() => {
    const saved = localStorage.getItem('eqi_session_id')
    if (saved) setSessionId(Number(saved))
  }, [])

  async function sendText() {
    if (!hasSession || !text.trim()) return
    setBusy(true)
    try {
      const u: Turn = { role: 'user', text }
      setTurns(t => [...t, u])
      const resp = await postTextTurn(sessionId!, text)
      const replyText = String(resp?.text ?? '').trim() || '[Tutor] …'
      setTurns(t => [...t, { role: 'tutor', text: replyText, raw: resp }])
      setText('')
    } catch (e: any) {
      setTurns(t => [...t, { role: 'tutor', text: `Error: ${e?.message || e}` }])
    } finally {
      setBusy(false)
    }
  }

  async function sendAudio(file: File) {
    if (!hasSession) return
    setBusy(true)
    try {
      setTurns(t => [...t, { role: 'user', text: `[voice upload] ${file.name}` }])
      const resp = await postAudioTurn(sessionId!, file, text || undefined)
      const replyText = String(resp?.text ?? '').trim() || '[Tutor] …'
      setTurns(t => [...t, { role: 'tutor', text: replyText, raw: resp }])
      setText('')
    } catch (e: any) {
      setTurns(t => [...t, { role: 'tutor', text: `Error: ${e?.message || e}` }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid">
      <div className="card">
        <h2>Chat</h2>
        <div className="muted">Session ID: {sessionId ?? '—'} (set on Session tab)</div>
        <div className="row" style={{marginTop:8}}>
          <input value={text} onChange={e=>setText(e.target.value)} placeholder="Type a message" />
          <button onClick={sendText} disabled={!hasSession || !text.trim() || busy}>Send</button>
        </div>
        <div style={{marginTop:8}}>
          <Recorder onStop={sendAudio} />
        </div>
      </div>
      <div className="card">
        <h2>Transcript</h2>
        <div className="chat">
          {turns.map((t,i) => (
            <div key={i} className={t.role==='user'? 'u':'t'}>
              <div className="who">{t.role}</div>
              <div className="bubble">{t.text}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

