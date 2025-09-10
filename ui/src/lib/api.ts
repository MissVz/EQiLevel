const API_BASE_ENV: string = (import.meta as any).env?.VITE_API_BASE || 'http://127.0.0.1:8000'
const ADMIN_KEY_ENV: string | undefined = (import.meta as any).env?.VITE_ADMIN_KEY

export function getApiBase(): string {
  try {
    return localStorage.getItem('eqi_api_base') || API_BASE_ENV
  } catch {
    return API_BASE_ENV
  }
}

export function getAdminKey(): string | undefined {
  try {
    return localStorage.getItem('eqi_admin_key') || ADMIN_KEY_ENV
  } catch {
    return ADMIN_KEY_ENV
  }
}

export async function startSession(): Promise<number> {
  const r = await fetch(`${getApiBase()}/session/start`, { method: 'POST' })
  if (!r.ok) throw new Error(await r.text())
  const j = await r.json()
  return j.session_id
}

export async function postTextTurn(sessionId: number, userText: string) {
  const r = await fetch(`${getApiBase()}/session`, {
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
  const r = await fetch(`${getApiBase()}/session`, { method: 'POST', body: fd })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export type AdminTurn = {
  id: number
  session_id: number
  user_text: string
  reply_text: string
  emotion: Record<string, any>
  performance: Record<string, any>
  mcp: Record<string, any>
  reward: number
  created_at: string
}

export async function getAdminTurns(params: {
  sessionId?: number | string
  sinceMinutes?: number
  limit?: number
  offset?: number
  order?: 'asc'|'desc'
} = {}): Promise<AdminTurn[]> {
  const s = new URLSearchParams()
  if (params.sessionId != null && String(params.sessionId).trim() !== '') s.set('session_id', String(params.sessionId))
  if (params.sinceMinutes != null) s.set('since_minutes', String(params.sinceMinutes))
  if (params.limit != null) s.set('limit', String(params.limit))
  if (params.offset != null) s.set('offset', String(params.offset))
  if (params.order) s.set('order', params.order)

  const headers: Record<string,string> = {}
  const key = getAdminKey()
  if (key) headers['X-Admin-Key'] = key

  const r = await fetch(`${getApiBase()}/api/v1/admin/turns?${s.toString()}`, { headers })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export type MetricsSnapshot = {
  turns_total: number
  avg_reward: number
  frustration_adaptation_rate: number
  tone_alignment_rate: number
  last_10_reward_avg: number
  by_emotion: Record<string, number>
  action_distribution: {
    tone: Record<string, number>
    pacing: Record<string, number>
    difficulty: Record<string, number>
    next_step: Record<string, number>
  }
  filters: Record<string, any>
}

export async function getMetrics(params: {
  sessionId?: number | string
  sinceMinutes?: number
  sinceHours?: number
} = {}): Promise<MetricsSnapshot> {
  const s = new URLSearchParams()
  if (params.sessionId != null && String(params.sessionId).trim() !== '') s.set('session_id', String(params.sessionId))
  if (params.sinceMinutes != null) s.set('since_minutes', String(params.sinceMinutes))
  if (params.sinceHours != null) s.set('since_hours', String(params.sinceHours))
  const r = await fetch(`${getApiBase()}/api/v1/metrics?${s.toString()}`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export type MetricsSeries = {
  bucket: 'minute'|'hour'
  since_minutes: number
  window_start_utc?: string | null
  session_id?: number | string | null
  points: Array<{ ts: string; turns: number; avg_reward: number; frustrated: number }>
}

export async function getMetricsSeries(params: {
  sessionId?: number | string
  bucket?: 'minute'|'hour'
  sinceMinutes?: number
} = {}): Promise<MetricsSeries> {
  const s = new URLSearchParams()
  if (params.sessionId != null && String(params.sessionId).trim() !== '') s.set('session_id', String(params.sessionId))
  s.set('bucket', params.bucket || 'minute')
  if (params.sinceMinutes != null) s.set('since_minutes', String(params.sinceMinutes))
  const r = await fetch(`${getApiBase()}/api/v1/metrics/series?${s.toString()}`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}
