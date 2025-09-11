import React, { useEffect, useRef, useState, forwardRef, useImperativeHandle, useCallback } from 'react'
import type { TutorReply } from '../lib/api'
import { getApiBase } from '../lib/api'

export type StreamerHandle = {
  start: () => Promise<void>
  stop: () => void
  isRecording: () => boolean
}

type Props = {
  sessionId: number | null
  deviceId?: string
  objectiveCode?: string
  onReply?: (reply: TutorReply) => void
  onFinalTranscript?: (text: string) => void
  onPartial?: (text: string) => void
}

export const Streamer = forwardRef<StreamerHandle, Props>(function Streamer({ sessionId, deviceId, objectiveCode, onReply, onFinalTranscript, onPartial }, ref) {
  const [rec, setRec] = useState<MediaRecorder|null>(null)
  const [ws, setWs] = useState<WebSocket|null>(null)
  const [recording, setRecording] = useState(false)
  const [partial, setPartial] = useState('')
  const [error, setError] = useState<string|null>(null)
  const [status, setStatus] = useState<'idle'|'connecting'|'ready'|'recording'>('idle')
  // chunks were unused; streaming sends directly as buffers
  const audioCtx = useRef<AudioContext|null>(null)
  const analyser = useRef<AnalyserNode|null>(null)
  const rafId = useRef<number|undefined>(undefined)
  const startedAt = useRef<number>(0)
  const lastVoiceAt = useRef<number>(0)
  const lastPartialAt = useRef<number>(0)
  const lastPartialRef = useRef<string>("")
  const AUTO_STOP_LS_KEY = 'eqi_vad_autostop'
  const VAD_THRESH_KEY = 'eqi_vad_thresh'
  const VAD_MIN_MS_KEY = 'eqi_vad_min_ms'
  const VAD_SIL_MS_KEY = 'eqi_vad_sil_ms'
  const [autoStop, setAutoStop] = useState<boolean>(() => {
    try { return localStorage.getItem(AUTO_STOP_LS_KEY) !== '0' } catch { return true }
  })

  const wsUrl = useCallback((): string => {
    const base = getApiBase().replace(/^http/, 'ws')
    let params: string[] = []
    if (sessionId != null) params.push(`session_id=${encodeURIComponent(String(sessionId))}`)
    try {
      const v = parseInt(localStorage.getItem('eqi_chat_hist_turns') || '8', 10)
      const vv = Number.isNaN(v) ? 8 : Math.max(1, Math.min(20, v))
      params.push(`hist=${vv}`)
    } catch {}
    if (objectiveCode) params.push(`objective_code=${encodeURIComponent(objectiveCode)}`)
    const q = params.length ? `?${params.join('&')}` : ''
    return `${base}/ws/voice${q}`
  }, [sessionId, objectiveCode])

  function chooseMime(): string {
    const isSup = (t: string) => {
      try { return (window as any).MediaRecorder && (window as any).MediaRecorder.isTypeSupported && (window as any).MediaRecorder.isTypeSupported(t) } catch { return false }
    }
    if (isSup('audio/webm;codecs=opus')) return 'audio/webm;codecs=opus'
    if (isSup('audio/webm')) return 'audio/webm'
    if (isSup('audio/mp4')) return 'audio/mp4'
    return '' // let browser pick
  }

  // Define stop() before setupVAD/start to avoid TDZ when referenced as a dependency
  const stop = useCallback(() => {
    try { ws?.send(JSON.stringify({ event: 'stop' })) } catch {}
    try { rec?.requestData() } catch {}
    try { rec?.stop() } catch {}
    setRecording(false)
    setRec(null)
    cleanupAudio()
  }, [ws, rec])

  // Define setupVAD before start() to avoid TDZ issues in dependency arrays
  const setupVAD = useCallback((stream: MediaStream) => {
    if (!autoStop) return
    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
      audioCtx.current = ctx
      const src = ctx.createMediaStreamSource(stream)
      const an = ctx.createAnalyser()
      an.fftSize = 2048
      src.connect(an)
      analyser.current = an
      startedAt.current = performance.now()
      lastVoiceAt.current = startedAt.current
      const data = new Float32Array(an.fftSize)

      // Load thresholds from Settings (localStorage)
      let THRESH = 0.02
      let MIN_MS = 1200
      let SIL_MS = 1200
      try {
        const t = parseFloat(localStorage.getItem(VAD_THRESH_KEY) || '0.02')
        if (!Number.isNaN(t)) THRESH = Math.min(0.2, Math.max(0.001, t))
        const minms = parseInt(localStorage.getItem(VAD_MIN_MS_KEY) || '1200', 10)
        if (!Number.isNaN(minms) && minms >= 0) MIN_MS = minms
        const silms = parseInt(localStorage.getItem(VAD_SIL_MS_KEY) || '1200', 10)
        if (!Number.isNaN(silms) && silms >= 200) SIL_MS = silms
      } catch {}

      const tick = () => {
        if (!analyser.current) return
        try {
          if ((analyser.current as any).getFloatTimeDomainData) {
            ;(analyser.current as any).getFloatTimeDomainData(data)
          } else {
            const bytes = new Uint8Array(analyser.current!.fftSize)
            analyser.current!.getByteTimeDomainData(bytes)
            for (let i=0;i<data.length;i++){ data[i] = (bytes[i]-128)/128 }
          }
          const level = rms(data)
          const now = performance.now()
          if (level > THRESH) {
            lastVoiceAt.current = now
          }
          if (autoStop && (now - startedAt.current) > MIN_MS && (now - lastVoiceAt.current) > SIL_MS) {
            stop()
            return
          }
        } catch {}
        rafId.current = requestAnimationFrame(tick)
      }
      rafId.current = requestAnimationFrame(tick)
    } catch (e) {
      // VAD not available; ignore
    }
  }, [autoStop, stop])

  const start = useCallback(async () => {
    if (recording) return
    setError(null)
    setStatus('connecting')
    try {
      const socket = new WebSocket(wsUrl())
      socket.onopen = () => { /* wait for server 'ready' */ }
      socket.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data)
          if (msg.type === 'ready') {
            setStatus('ready')
            // Start mic when server is ready
            const constraints: MediaStreamConstraints = { audio: deviceId ? { deviceId: { exact: deviceId } as any } : true }
            navigator.mediaDevices.getUserMedia(constraints).then(stream => {
              const mime = chooseMime()
              const mr = new MediaRecorder(stream, mime ? { mimeType: mime } as any : undefined)
              mr.ondataavailable = (e) => {
                if (e.data && e.data.size > 0) {
                  // Send as ArrayBuffer
                  e.data.arrayBuffer().then(buf => socket.send(buf))
                }
              }
              mr.onstop = () => {
                stream.getTracks().forEach(t => t.stop())
                setTimeout(() => { try { socket.send(JSON.stringify({ event: 'stop' })) } catch {} }, 50)
                cleanupAudio()
              }
              mr.start(300) // 300ms chunks
              setRec(mr)
              setRecording(true)
              setStatus('recording')
              setupVAD(stream)
            })
            return
          }
          if (msg.type === 'final') {
            if (msg.transcript && onFinalTranscript) onFinalTranscript(String(msg.transcript))
            if (msg.reply && onReply) onReply(msg.reply as TutorReply)
            setPartial('')
            try { socket.close() } catch {}
            setStatus('idle')
          } else if (msg.type === 'partial') {
            let t = String(msg.text || '')
            t = sanitizePartial(t)
            if (t && shouldEmitPartial(t, lastPartialRef.current)) {
              lastPartialRef.current = t
              lastPartialAt.current = performance.now()
              setPartial(t)
              if (onPartial) onPartial(t)
            }
          } else if (msg.type === 'error') {
            setError(String(msg.message || 'Streaming error'))
            setStatus('idle')
          }
        } catch {
          // ignore non-JSON
        }
      }
      socket.onerror = () => setError('WebSocket error')
      socket.onclose = () => { setWs(null); setRecording(false); setRec(null); setStatus('idle') }
      setWs(socket)
    } catch (e: any) {
      setError(e?.message || String(e))
      setStatus('idle')
    }
  }, [recording, deviceId, onFinalTranscript, onPartial, onReply, wsUrl, setupVAD])

  const supported = !!(navigator.mediaDevices && (window as any).MediaRecorder)

  useImperativeHandle(ref, () => ({
    start,
    stop,
    isRecording: () => recording,
  }), [start, stop, recording])


  function cleanupAudio() {
    try { if (rafId.current) cancelAnimationFrame(rafId.current) } catch {}
    rafId.current = undefined
    try { analyser.current && analyser.current.disconnect() } catch {}
    analyser.current = null
    try { audioCtx.current && audioCtx.current.close() } catch {}
    audioCtx.current = null
  }

  // Failsafe monitor: stop if too long or stale
  useEffect(() => {
    if (!recording) return
    const id = window.setInterval(() => {
      const now = performance.now()
      const MAX_MS = 25_000
      if (startedAt.current && (now - startedAt.current) > MAX_MS) { stop(); return }
      const STALE_MS = 10_000
      if (autoStop && lastPartialAt.current && (now - lastPartialAt.current) > STALE_MS) { stop(); return }
    }, 1000)
    return () => window.clearInterval(id)
  }, [recording, autoStop, stop])

  function sanitizePartial(s: string): string {
    // Collapse repeated 'thank you' phrases and trim
    try {
      let t = s.replace(/\s+/g, ' ')
      t = t.replace(/(?:\bthank you\b[.!?,;:]?\s*){3,}/gi, 'Thank you. ')
      if (t.length > 220) t = t.slice(-220)
      return t
    } catch { return s }
  }

  function shouldEmitPartial(curr: string, prev: string): boolean {
    if (!curr) return false
    if (!prev) return true
    if (curr === prev) return false
    if (curr.startsWith(prev) && (curr.length - prev.length) < 8) return false
    return true
  }

  return (
    <div>
      {!supported && <div className="warn">Streaming not supported in this browser.</div>}
      <div className="row" style={{marginTop:8}}>
        <button onClick={start} disabled={!supported || recording || !sessionId || !(objectiveCode && objectiveCode.trim())}>Start Stream</button>
        <button onClick={stop} disabled={!recording}>Stop</button>
        <label className="muted" style={{display:'flex', alignItems:'center', gap:6}}>
          <input type="checkbox" checked={autoStop} onChange={e=>{ setAutoStop(e.target.checked); try{ localStorage.setItem(AUTO_STOP_LS_KEY, e.target.checked ? '1':'0') } catch {} }} />
          auto-stop on silence
        </label>
      </div>
      <div className="muted" style={{marginTop:4}}>status: {status}{!supported ? ' (MediaRecorder not supported)' : ''}</div>
      {error && <div className="error">{error}</div>}
      {partial && <div className="muted" style={{marginTop:4}}>{partial}</div>}
    </div>
  )
})

// Expose imperative API to parent (start/stop/isRecording)
// useImperativeHandle to expose API to parent

function rms(buf: Float32Array): number {
  let sum = 0
  for (let i = 0; i < buf.length; i++) { const v = buf[i]; sum += v*v }
  return Math.sqrt(sum / buf.length)
}

// (helpers above in component)
