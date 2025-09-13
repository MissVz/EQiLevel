// Lightweight browser TTS helpers using the Web Speech API
// Stores preferences in localStorage so Settings and Chat can share state.

export type TTSSettings = {
  enabled: boolean
  voiceName: string | null
  rate: number // 0.1–10 (browser clamps); we use 0.5–1.5 normally
  pitch: number // 0–2
}

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n))
}

export function getTTSSettings(): TTSSettings {
  try {
    const enabled = (localStorage.getItem('eqi_tts_enabled') || '0') === '1'
    const voiceName = localStorage.getItem('eqi_tts_voice') || null
    const rate = clamp(parseFloat(localStorage.getItem('eqi_tts_rate') || '1.0'), 0.1, 4.0)
    const pitch = clamp(parseFloat(localStorage.getItem('eqi_tts_pitch') || '1.0'), 0, 2)
    return { enabled, voiceName, rate, pitch }
  } catch {
    return { enabled: false, voiceName: null, rate: 1.0, pitch: 1.0 }
  }
}

export function setTTSSetting(key: keyof TTSSettings, val: any) {
  try {
    switch (key) {
      case 'enabled':
        localStorage.setItem('eqi_tts_enabled', val ? '1' : '0'); break
      case 'voiceName':
        localStorage.setItem('eqi_tts_voice', val || ''); break
      case 'rate':
        localStorage.setItem('eqi_tts_rate', String(val)); break
      case 'pitch':
        localStorage.setItem('eqi_tts_pitch', String(val)); break
    }
  } catch {}
}

// Returns voices, waiting for the async population if necessary
export function listVoices(): Promise<SpeechSynthesisVoice[]> {
  return new Promise((resolve) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      resolve([]); return
    }
    const synth = window.speechSynthesis
    let vs = synth.getVoices()
    if (vs && vs.length > 0) { resolve(vs); return }
    const onVoices = () => {
      vs = synth.getVoices();
      resolve(vs || [])
      synth.removeEventListener('voiceschanged', onVoices)
    }
    synth.addEventListener('voiceschanged', onVoices)
    // Fallback timeout in case event never fires
    setTimeout(() => {
      vs = synth.getVoices();
      resolve(vs || [])
      synth.removeEventListener('voiceschanged', onVoices)
    }, 1200)
  })
}

export function cancelSpeak() {
  try { if ('speechSynthesis' in window) window.speechSynthesis.cancel() } catch {}
}

export function speak(text: string): boolean {
  if (!text || !text.trim()) return false
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return false
  const cfg = getTTSSettings()
  if (!cfg.enabled) return false
  try {
    const u = new SpeechSynthesisUtterance(text)
    u.rate = clamp(cfg.rate || 1.0, 0.1, 4.0)
    u.pitch = clamp(cfg.pitch || 1.0, 0, 2)
    const synth = window.speechSynthesis
    const voices = synth.getVoices()
    if (cfg.voiceName && voices && voices.length > 0) {
      const match = voices.find(v => v.name === cfg.voiceName)
      if (match) u.voice = match
    }
    synth.cancel() // replace any current speech with latest tutor message
    synth.speak(u)
    return true
  } catch {
    return false
  }
}

