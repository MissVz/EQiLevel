import React, { useRef, useState, forwardRef, useImperativeHandle, useCallback } from 'react'

export type RecorderHandle = {
  start: () => Promise<void>
  stop: () => void
  isRecording: () => boolean
}

type Props = {
  onStop: (file: File) => void
  deviceId?: string
  canRecord?: boolean
}

export const Recorder = forwardRef<RecorderHandle, Props>(function Recorder({ onStop, deviceId, canRecord = true }, ref) {
  const [rec, setRec] = useState<MediaRecorder|null>(null)
  const [recording, setRecording] = useState(false)
  const chunks = useRef<any[]>([])
  const [error, setError] = useState<string|null>(null)

  function chooseMime(): { mime: string, ext: string } {
    const isSup = (t: string) => {
      try { return (window as any).MediaRecorder && (window as any).MediaRecorder.isTypeSupported && (window as any).MediaRecorder.isTypeSupported(t) } catch { return false }
    }
    if (isSup('audio/webm;codecs=opus')) return { mime: 'audio/webm;codecs=opus', ext: 'webm' }
    if (isSup('audio/webm')) return { mime: 'audio/webm', ext: 'webm' }
    if (isSup('audio/mp4')) return { mime: 'audio/mp4', ext: 'm4a' }
    // Fallback: let browser choose
    return { mime: 'audio/webm', ext: 'webm' }
  }

  const start = useCallback(async () => {
    setError(null)
    try {
      const constraints: MediaStreamConstraints = {
        audio: deviceId ? { deviceId: { exact: deviceId } as any } : true
      }
      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      const { mime, ext } = chooseMime()
      const mr = new MediaRecorder(stream, { mimeType: mime } as any)
      mr.ondataavailable = (e) => { if (e.data && e.data.size > 0) chunks.current.push(e.data) }
      mr.onstop = () => {
        const blob = new Blob(chunks.current, { type: 'audio/webm' })
        chunks.current = []
        const file = new File([blob], `recording-${Date.now()}.${ext}`, { type: mime })
        onStop(file)
        stream.getTracks().forEach(t => t.stop())
      }
      mr.start()
      setRec(mr)
      setRecording(true)
    } catch (e: any) {
      setError(e?.message || String(e))
    }
  }, [deviceId, onStop])

  const stop = useCallback(() => {
    rec?.stop()
    setRecording(false)
    setRec(null)
  }, [rec])

  useImperativeHandle(ref, () => ({
    start,
    stop,
    isRecording: () => recording,
  }), [recording, start, stop])

  const supported = !!(navigator.mediaDevices && window.MediaRecorder)

  return (
    <div>
      {!supported && <div className="warn">MediaRecorder not supported in this browser.</div>}
      <div className="row">
        <button onClick={start} disabled={!supported || recording || !canRecord}>Record</button>
        <button onClick={stop} disabled={!recording}>Stop</button>
      </div>
      {error && <div className="error">{error}</div>}
    </div>
  )
})
