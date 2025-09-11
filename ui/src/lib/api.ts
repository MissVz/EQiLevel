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

export type EmotionSignals = {
  label: 'frustrated'|'engaged'|'bored'|'calm'
  sentiment: number
}
export type PerformanceSignals = {
  correct?: boolean | null
  attempts?: number | null
  time_to_solve_sec?: number | null
  accuracy_pct?: number | null
}
export type LearningStyle = {
  visual: number
  auditory: number
  reading_writing: number
  kinesthetic: number
}
export type MCP = {
  emotion: EmotionSignals
  performance: PerformanceSignals
  learning_style: LearningStyle
  tone: 'warm'|'encouraging'|'neutral'|'concise'
  pacing: 'slow'|'medium'|'fast'
  difficulty: 'down'|'hold'|'up'
  style: 'visual'|'auditory'|'reading_writing'|'kinesthetic'|'mixed'
  next_step: 'explain'|'example'|'prompt'|'quiz'|'review'
}
export type TutorReply = { text: string; mcp: MCP; reward?: number; transcript?: string }

// ---- Objectives ----
export type Objective = {
  unit: string
  objective_code: string
  description: string
  strands?: string
  examples?: string
  prereqs?: string
  mastery_threshold?: string
  assessment_types?: string
}

export async function getObjectives(params: { unit?: string; q?: string } = {}): Promise<Objective[]> {
  const s = new URLSearchParams()
  if (params.unit) s.set('unit', params.unit)
  if (params.q) s.set('q', params.q)
  const r = await fetch(`${getApiBase()}/api/v1/objectives?${s.toString()}`)
  if (!r.ok) throw new Error(await r.text())
  const j = await r.json()
  return j.items || []
}

export type ObjectiveProgressItem = {
  objective_code: string
  description?: string
  attempts: number
  correct: number
  accuracy: number
  avg_reward: number
  mastery_threshold?: number
  mastered: boolean
  last_turn_utc?: string
}

export async function getObjectiveProgress(params: { sessionId?: number; userId?: number; sinceMinutes?: number } = {}): Promise<ObjectiveProgressItem[]> {
  const s = new URLSearchParams()
  if (params.sessionId != null) s.set('session_id', String(params.sessionId))
  if (params.userId != null) s.set('user_id', String(params.userId))
  if (params.sinceMinutes != null) s.set('since_minutes', String(params.sinceMinutes))
  const r = await fetch(`${getApiBase()}/api/v1/objectives/progress?${s.toString()}`)
  if (!r.ok) throw new Error(await r.text())
  const j = await r.json()
  return j.items || []
}

export async function startSession(userName?: string, userId?: number): Promise<number> {
  const body: any = {}
  if (userName) body.user_name = userName
  if (userId != null) body.user_id = userId
  const r = await fetch(`${getApiBase()}/session/start`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!r.ok) throw new Error(await r.text())
  const j = await r.json()
  return j.session_id
}

export type SimpleUser = { id: number; name: string }
export async function getUsers(q?: string): Promise<SimpleUser[]> {
  const s = new URLSearchParams()
  if (q) s.set('q', q)
  const r = await fetch(`${getApiBase()}/api/v1/users?${s.toString()}`)
  if (!r.ok) throw new Error(await r.text())
  const j = await r.json()
  return j.items || []
}

export async function getUserBySession(sessionId: number): Promise<SimpleUser | null> {
  const r = await fetch(`${getApiBase()}/api/v1/users/by_session?session_id=${encodeURIComponent(String(sessionId))}`)
  if (!r.ok) throw new Error(await r.text())
  const j = await r.json()
  if (j.found && j.user) return j.user as SimpleUser
  return null
}

export async function postTextTurn(sessionId: number, userText: string, objectiveCode?: string, chatHistoryTurns?: number): Promise<TutorReply> {
  const r = await fetch(`${getApiBase()}/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, user_text: userText, objective_code: objectiveCode, chat_history_turns: chatHistoryTurns })
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function postAudioTurn(sessionId: number, file: File, userText?: string, objectiveCode?: string, chatHistoryTurns?: number): Promise<TutorReply> {
  const fd = new FormData()
  fd.append('session_id', String(sessionId))
  fd.append('file', file, file.name)
  if (userText) fd.append('user_text', userText)
  if (objectiveCode) fd.append('objective_code', objectiveCode)
  if (chatHistoryTurns != null) fd.append('chat_history_turns', String(chatHistoryTurns))
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

export type AdminSummary = {
  sessions: Array<{
    session_id: number
    turns_total: number
    last_turn_utc?: string | null
    last_emotion?: string | null
    last_reward?: number | null
    last_difficulty?: string | null
    last_tone?: string | null
    turns_in_window?: number | null
    avg_reward_window?: number | null
  }>
  filters: Record<string, any>
}

export async function getAdminSummary(params: { sinceMinutes?: number, sinceHours?: number } = {}): Promise<AdminSummary> {
  const s = new URLSearchParams()
  if (params.sinceMinutes != null) s.set('since_minutes', String(params.sinceMinutes))
  if (params.sinceHours != null) s.set('since_hours', String(params.sinceHours))
  const r = await fetch(`${getApiBase()}/api/v1/admin/summary?${s.toString()}`)
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

// ---- Health / Admin utils ----
export type HealthFull = {
  status: 'ok' | 'degraded'
  components: { openai_key: 'present'|'missing'; database: 'up'|'down'; ffmpeg?: 'present'|'missing' }
  stream?: { max_seconds?: number; stale_partial_seconds?: number }
  errors?: Record<string, string>
}

export async function getHealthFull(): Promise<HealthFull> {
  const r = await fetch(`${getApiBase()}/api/v1/health/full`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function validateAdminKey(): Promise<boolean> {
  // Try a very small request to a protected endpoint
  const headers: Record<string,string> = {}
  const key = getAdminKey()
  if (key) headers['X-Admin-Key'] = key
  const r = await fetch(`${getApiBase()}/api/v1/admin/turns?limit=1`, { headers })
  if (r.status === 200) return true
  if (r.status === 401 || r.status === 403) return false
  // For other statuses, treat as unknown/failure
  return false
}

// ---- System prompt settings (admin) ----
export async function getSystemPrompt(adminKey: string): Promise<string> {
  const r = await fetch(`${getApiBase()}/api/v1/settings/system_prompt`, { headers: { 'X-Admin-Key': adminKey } })
  if (!r.ok) throw new Error(await r.text())
  const j = await r.json()
  return j.system_prompt || ''
}

export async function setSystemPrompt(adminKey: string, value: string): Promise<void> {
  const r = await fetch(`${getApiBase()}/api/v1/settings/system_prompt`, {
    method: 'POST', headers: { 'X-Admin-Key': adminKey, 'Content-Type': 'application/json' }, body: JSON.stringify({ value })
  })
  if (!r.ok) throw new Error(await r.text())
}
