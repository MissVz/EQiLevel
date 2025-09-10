export const API_BASE: string = (import.meta as any).env?.VITE_API_BASE || 'http://127.0.0.1:8000'
export const ADMIN_KEY: string | undefined = (import.meta as any).env?.VITE_ADMIN_KEY

export async function startSession(): Promise<number> {
  const r = await fetch(`${API_BASE}/session/start`, { method: 'POST' })
  if (!r.ok) throw new Error(await r.text())
  const j = await r.json()
  return j.session_id
}

export async function postTextTurn(sessionId: number, userText: string) {
  const r = await fetch(`${API_BASE}/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, user_text: userText })
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function postAudioTurn(sessionId: number, file: File, userText?: string) {
  const fd = new FormData()
  fd.append('session_id', String(sessionId))
  fd.append('file', file, file.name)
  if (userText) fd.append('user_text', userText)
  const r = await fetch(`${API_BASE}/session`, { method: 'POST', body: fd })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

