import React, { useEffect, useState } from 'react'
import type { MCP, TutorReply, Objective, SimpleUser, ObjectiveProgressItem } from '../lib/api'
import { postAudioTurn, postTextTurn, getObjectives, getUserBySession, getObjectiveProgress } from '../lib/api'
import { Recorder, type RecorderHandle } from '../components/recorder'
import { Streamer, type StreamerHandle } from '../components/streamer'
import { speak, cancelSpeak } from '../lib/tts'

type Turn = {
  role: 'user'|'tutor'
  text: string
  raw?: TutorReply
  diffs?: string[]
}

export function Chat() {
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [text, setText] = useState('')
  const [objectiveCode, setObjectiveCode] = useState<string>('')
  const [objInput, setObjInput] = useState<string>('')
  const [objectives, setObjectives] = useState<Objective[]>([])
  const [selectedObj, setSelectedObj] = useState<Objective | null>(null)
  const [userName, setUserName] = useState<string>('')
  const [mastery, setMastery] = useState<ObjectiveProgressItem | null>(null)
  const getChatHistTurns = () => {
    try {
      const v = parseInt(localStorage.getItem('eqi_chat_hist_turns') || '8', 10)
      if (Number.isNaN(v)) return 8
      return Math.max(1, Math.min(20, v))
    } catch { return 8 }
  }
  const [turns, setTurns] = useState<Turn[]>([])
  const [busy, setBusy] = useState(false)
  const [micId, setMicId] = useState<string | null>(null)
  const [mcp, setMcp] = useState<MCP | null>(null)
  const [autoSend, setAutoSend] = useState<boolean>(() => {
    try { return localStorage.getItem('eqi_auto_send_chips') === '1' } catch { return false }
  })
  const [live, setLive] = useState<string>('')
  const recRef = React.useRef<RecorderHandle>(null)
  const streamRef = React.useRef<StreamerHandle>(null)
  const awaitingUser = React.useMemo(() => {
    if (turns.length === 0) return false
    const last = turns[turns.length-1]
    return last.role === 'tutor' && /\?/m.test(last.text || '')
  }, [turns])

  function stopAllOrSend() {
    // Try to stop stream first (force stop even if UI state is stale)
    const sRec = streamRef.current
    if (sRec) { try { sRec.stop() } catch {} return }
    const rRec = recRef.current
    if (rRec) { try { rRec.stop() } catch {} return }
    if (!busy && hasSession && text.trim()) { void sendText(); return }
  }
  const hasSession = sessionId != null

  useEffect(() => {
    const saved = localStorage.getItem('eqi_session_id')
    if (saved) setSessionId(Number(saved))
    try { const mid = localStorage.getItem('eqi_mic_id'); if (mid) setMicId(mid) } catch {}
  }, [])

  useEffect(() => {
    // preload full list (small CSV); could add search later
    getObjectives().then(setObjectives).catch(() => {})
  }, [])

  useEffect(() => {
    // Fetch username for current session
    if (sessionId != null) {
      getUserBySession(sessionId).then(u => {
        if (u && u.name) setUserName(u.name)
        else {
          try { const ls = localStorage.getItem('eqi_user_name'); if (ls) setUserName(ls) } catch {}
        }
      }).catch(() => {
        try { const ls = localStorage.getItem('eqi_user_name'); if (ls) setUserName(ls) } catch {}
      })
    }
  }, [sessionId])

  function onObjChange(v: string){
    setObjInput(v)
    const match = objectives.find(o => o.description === v)
    if (match){
      setObjectiveCode(match.objective_code)
      setSelectedObj(match)
    } else {
      setSelectedObj(null)
    }
  }

  // Load mastery for selected objective
  useEffect(() => {
    const sid = sessionId
    const oc = objectiveCode?.trim()
    if (!sid || !oc) { setMastery(null); return }
    getObjectiveProgress({ sessionId: sid }).then(items => {
      const it = items.find(x => x.objective_code === oc)
      setMastery(it || null)
    }).catch(()=>{})
  }, [sessionId, objectiveCode, turns.length])

  function diffMcp(prev: MCP | null, curr: MCP | null): string[] {
    if (!curr) return []
    const fields: Array<keyof MCP> = ['tone','pacing','difficulty','style','next_step']
    const out: string[] = []
    for (const f of fields) {
      const a = prev ? (prev as any)[f] : undefined
      const b = (curr as any)[f]
      if (a === undefined) continue
      if (a !== b) out.push(`${String(f)}: ${a} → ${b}`)
    }
    if (prev && prev.emotion && curr.emotion) {
      if (prev.emotion.label !== curr.emotion.label) {
        out.push(`emotion: ${prev.emotion.label} → ${curr.emotion.label}`)
      }
      const ds = (curr.emotion.sentiment ?? 0) - (prev.emotion.sentiment ?? 0)
      if (Math.abs(ds) >= 0.15) {
        out.push(`sentiment: ${(prev.emotion.sentiment ?? 0).toFixed(2)} → ${(curr.emotion.sentiment ?? 0).toFixed(2)}`)
      }
    }
    return out
  }

  const stepPhrases: Record<MCP['next_step'], string> = {
    example: 'Please show me another example.',
    explain: 'Please explain step by step.',
    quiz: 'Give me a short quiz to practice.',
    prompt: 'Can I have a hint to try?',
    review: 'Let’s review the key points so far.'
  }

  function insertStep(step: MCP['next_step']){
    const phrase = stepPhrases[step]
    if (autoSend) {
      void sendImmediate(phrase)
    } else {
      setText(phrase)
    }
    try { localStorage.setItem('eqi_auto_send_chips', autoSend ? '1' : '0') } catch {}
  }

  async function sendImmediate(phrase: string) {
    if (!hasSession || !phrase.trim()) return
    setBusy(true)
    try {
      const u: Turn = { role: 'user', text: phrase }
      setTurns(t => [...t, u])
      const resp: TutorReply = await postTextTurn(sessionId!, phrase, objectiveCode || undefined, getChatHistTurns())
      const replyText = String(resp?.text ?? '').trim() || '[Tutor] …'
      const changes = diffMcp(mcp, resp?.mcp || null)
      const withReward = typeof resp?.reward === 'number' ? [...changes, `reward: ${resp.reward.toFixed(3)}`] : changes
      setTurns(t => [...t, { role: 'tutor', text: replyText, raw: resp, diffs: withReward }])
      try { speak(replyText) } catch {}
      if (resp?.mcp) setMcp(resp.mcp)
    } catch (e: any) {
      setTurns(t => [...t, { role: 'tutor', text: `Error: ${e?.message || e}` }])
    } finally { setBusy(false) }
  }

  async function sendText() {
    if (!hasSession || !text.trim()) return
    setBusy(true)
    try {
      const u: Turn = { role: 'user', text }
      setTurns(t => [...t, u])
      const resp: TutorReply = await postTextTurn(sessionId!, text, objectiveCode || undefined, getChatHistTurns())
      const replyText = String(resp?.text ?? '').trim() || '[Tutor] …'
      const changes = diffMcp(mcp, resp?.mcp || null)
      setTurns(t => [...t, { role: 'tutor', text: replyText, raw: resp, diffs: changes }])
      try { speak(replyText) } catch {}
      if (resp?.mcp) setMcp(resp.mcp)
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
      const resp: TutorReply = await postAudioTurn(sessionId!, file, text || undefined, objectiveCode || undefined, getChatHistTurns())
      const utext = String(resp?.transcript || '').trim() || `[voice upload] ${file.name}`
      setTurns(t => [...t, { role: 'user', text: utext }])
      const replyText = String(resp?.text ?? '').trim() || '[Tutor] …'
      const changes = diffMcp(mcp, resp?.mcp || null)
      setTurns(t => [...t, { role: 'tutor', text: replyText, raw: resp, diffs: changes }])
      try { speak(replyText) } catch {}
      if (resp?.mcp) setMcp(resp.mcp)
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
        <div className="muted">Session ID: {sessionId ?? '—'} • Student: {userName || '—'}</div>
        <div className="row" style={{marginTop:6, gap:8, alignItems:'center'}}>
          <input list="obj-list" value={objInput} onChange={e=>onObjChange(e.target.value)} placeholder="Objective (type to search titles) – optional" style={{width:'60%'}} />
          <datalist id="obj-list">
            {objectives.map(o => (
              <option key={o.objective_code} value={o.description} />
            ))}
          </datalist>
          <input value={objectiveCode} onChange={e=>setObjectiveCode(e.target.value)} placeholder="Code" style={{width:80}} />
        </div>
        {selectedObj && (
          <div className="muted" style={{fontSize:12, marginTop:4, lineHeight:1.3}}>
            <div><b>{selectedObj.objective_code}</b>: {selectedObj.description}</div>
            {selectedObj.strands && <div>strands: {selectedObj.strands}</div>}
            {selectedObj.prereqs && <div>prereqs: {selectedObj.prereqs}</div>}
            {selectedObj.examples && <div>examples: {selectedObj.examples}</div>}
            {(selectedObj.mastery_threshold || selectedObj.assessment_types) && (
              <div>
                {selectedObj.mastery_threshold && <>mastery: {selectedObj.mastery_threshold} </>}
                {selectedObj.assessment_types && <>assessments: {selectedObj.assessment_types}</>}
              </div>
            )}
            {mastery && (
              <div>
                progress: {mastery.correct}/{mastery.attempts} correct ({Math.round((mastery.accuracy||0)*100)}%) • {mastery.mastered ? 'Mastered ✅' : 'Not yet'}
              </div>
            )}
          </div>
        )}
        <div className="row" style={{marginTop:8}}>
          <input value={text} onChange={e=>setText(e.target.value)} placeholder="Type a message" onKeyDown={e=>{ if (e.key==='Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); sendText() } }} />
          <button onClick={sendText} disabled={!hasSession || !text.trim() || busy} title="Ctrl/Cmd+Enter">Send</button>
        </div>
        {/* Guided next steps */}
        <div className="chips">
          {(['example','explain','quiz','prompt','review'] as MCP['next_step'][]).map(s => (
            <button key={s} className={`chip${mcp?.next_step===s?' active':''}`} onClick={()=>insertStep(s)} disabled={awaitingUser && (s==='quiz' || s==='prompt' || s==='review')}>{s}</button>
          ))}
          <label className="muted" style={{display:'flex', alignItems:'center', gap:6}}>
            <input type="checkbox" checked={autoSend} onChange={e=>{ setAutoSend(e.target.checked); try{localStorage.setItem('eqi_auto_send_chips', e.target.checked ? '1':'0')}catch{}}} />
            auto-send
          </label>
        </div>
        <div style={{marginTop:8}}>
          <Recorder ref={recRef} deviceId={micId || undefined} canRecord={!!objectiveCode.trim()} onStop={sendAudio} />
        </div>
        <div style={{marginTop:8}}>
          <Streamer ref={streamRef} sessionId={sessionId} deviceId={micId || undefined} objectiveCode={objectiveCode || undefined}
            onPartial={(t)=>setLive(t)}
            onFinalTranscript={(t)=>{ setLive(''); setTurns(ts=>[...ts,{role:'user', text:t}]) }}
            onReply={(reply)=>{
            const changes = diffMcp(mcp, reply?.mcp || null)
            setTurns(t => [...t, { role: 'tutor', text: reply.text, raw: reply, diffs: changes }])
            try { speak(reply.text) } catch {}
            if (reply?.mcp) setMcp(reply.mcp as any)
          }} />
        </div>
        <div className="row" style={{marginTop:8}}>
          <button onClick={stopAllOrSend} disabled={busy || (!hasSession)} title="Stop recording/streaming or send text (requires objective)">End / Send</button>
          <button onClick={()=>{ try{ cancelSpeak() }catch{} }} title="Stop voice">Stop voice</button>
          {awaitingUser && <span className="muted">Waiting for your answer…</span>}
        </div>
      </div>
      <div className="card">
        <h2>Transcript</h2>
        <div className="chat">
          {turns.map((t,i) => (
            <div key={i} className={t.role==='user'? 'u':'t'}>
              <div className="who">{t.role}</div>
              <div className="bubble">{t.text}</div>
              {t.role==='tutor' && t.diffs && t.diffs.length>0 && (
                <div className="badges">
                  {t.diffs.map((d, j) => (
                    <span key={j} className="badge">{d}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
          {live && (
            <div className={'u'}>
              <div className="who">user (live)</div>
              <div className="bubble live">{live}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
