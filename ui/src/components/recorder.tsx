import React, { useEffect, useRef, useState } from 'react'

type Props = {
  onStop: (file: File) => void
}

export function Recorder({ onStop }: Props) {
  const [rec, setRec] = useState<MediaRecorder|null>(null)
  const [recording, setRecording] = useState(false)
  const chunks = useRef<BlobPart[]>([])
  const [error, setError] = useState<string|null>(null)

  async function start() {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
      mr.ondataavailable = (e) => { if (e.data && e.data.size > 0) chunks.current.push(e.data) }
      mr.onstop = () => {
        const blob = new Blob(chunks.current, { type: 'audio/webm' })
        chunks.current = []
        const file = new File([blob], `recording-${Date.now()}.webm`, { type: 'audio/webm' })
        onStop(file)
        stream.getTracks().forEach(t => t.stop())
      }
      mr.start()
      setRec(mr)
      setRecording(true)
    } catch (e: any) {
      setError(e?.message || String(e))
    }
  }

  function stop() {
    rec?.stop()
    setRecording(false)
    setRec(null)
  }

  const supported = !!(navigator.mediaDevices && window.MediaRecorder)

  return (
    <div>
      {!supported && <div className="warn">MediaRecorder not supported in this browser.</div>}
      <div className="row">
        <button onClick={start} disabled={!supported || recording}>Record</button>
        <button onClick={stop} disabled={!recording}>Stop</button>
      </div>
      {error && <div className="error">{error}</div>}
    </div>
  )
}

