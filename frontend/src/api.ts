import type { Catalog } from './catalog'
export type Grade = 'Junior' | 'Middle' | 'Senior' | 'Lead'

export interface CareerGoal {
  target_role: string
  target_grade: Grade
}

export interface EmployeeListItem {
  employee_id: string
  full_name: string
  role: string
  grade: Grade
  department: string
  target: CareerGoal | null
}

export interface EmployeeProfile {
  employee_id: string
  full_name: string
  department: string
  role: string
  grade: Grade
  manager_id: string | null
  hire_date: string
  tenure_months: number
  work_format: string
  preferred_language: string
  career_goal: CareerGoal | null
  skills: Record<string, number>
  last_review_date: string
  target_role: string
  target_grade: Grade
  progress_to_next_grade: number
}

export interface TrajectoryItem {
  record_id: string
  event_id: string
  status: string
  date: string | null
  completion_pct: number | null
  score: number | null
  source?: 'activity_history' | 'quest_progress'
  mode?: 'solo' | 'team'
  completed_steps?: number
  total_steps?: number
  title?: string
}

export interface QuestStep {
  step: number
  title: string
  description: string
  done: boolean
}

export interface QuestPlan {
  employee_id?: string
  event_id: string
  title: string
  provider: 'template' | 'openai'
  language?: 'ru' | 'kk' | 'en'
  task: {
    event_id: string
    title: string
    description: string | null
    type: string | null
    format: string | null
    duration_hours: number | null
    develops_skills: unknown[]
  }
  steps: QuestStep[]
  completed_steps?: number
  total_steps?: number
  completion_pct?: number
  status?: string
  can_complete?: boolean
}

export interface QuestStepResult {
  employee_id: string
  event_id: string
  step_number: number
  status: string
  completed_steps: number
  total_steps: number
  completion_pct?: number
  can_complete?: boolean
}

export interface AffectedSkill {
  skill_id: string
  skill_name: string
  current_level: number
  required_level: number
  gain: number
  max_level: number
  expected_after: number
  gap_before: number
  gap_after: number
  is_critical?: boolean
}

export interface Recommendation {
  event_id: string
  quest_title: string
  quest_type: string
  format: string
  duration_hours: number
  score: number
  priority: 'high' | 'medium' | 'low'
  affected_skills: AffectedSkill[]
  employee_friendly_reason?: string
  risk_note?: string
  expected_outcome?: string
  reason: string
  game_message: string
  title?: string
  type?: string
  why_recommended?: string[]
  explanation?: string
  history_signal?: { completed_similar: number; missed_or_declined_similar: number; already_completed_this_event: boolean }
}

export interface RecommendationsResponse {
  employee_id: string
  role: string
  current_grade: Grade
  target_role: string
  target_grade: Grade
  progress_to_next_grade: number
  recommendations: Recommendation[]
  explanation_provider?: 'template' | 'openai'
  explanation_summary?: string
}

export interface CityProgress {
  level: number
  max_level: number
  completed_courses: number
  courses_per_level: number
  courses_to_next_level: number
  progress_to_next_level: number
}

export interface GameMap {
  employee_id: string
  current_zone: string
  target_zone: string
  career_level: number
  progress_to_next_grade: number
  nodes: { id: string; title: string; status: 'completed' | 'active' | 'locked' }[]
  recommended_quest_ids: string[]
  city_name?: string
  city_level: number
  city_progress: CityProgress
  center?: { name: string; level: number; city_level: number; wallet_balance: number; progress_to_next_grade: number }
  districts?: { id: string; name: string; progress: number; status: string; related_skills: string[]; impact_tags: string[]; recommended_event_ids: string[] }[]
  completed_quest_ids?: string[]
  selected_quests?: { event_id: string; status: string; mode: 'solo' | 'team' }[]
  quest_board?: { event_id: string; title: string; source: string; score: number }[]
}

export interface CompleteResponse {
  employee_id: string
  completed_quest: string
  updated_skills: Record<string, { before: number; after: number; required_for_next_grade: number }>
  progress_to_next_grade_before: number
  progress_to_next_grade_after: number
  message: string
  coins_earned?: number
  wallet_balance?: number
  coin_reason?: string
}

export interface HrDashboard {
  total_employees: number
  average_progress_to_next_grade: number
  top_skill_gaps: { skill_id: string; skill_name: string; affected_employees: number; average_gap: number }[]
  inactive_employees_count: number
  events_completion_rate: number
  popular_events: { event_id: string; count: number }[]
  risky_segments: string[]
}

export interface WalletResponse {
  employee_id: string
  balance: number
  transactions: { transaction_id: string; event_id: string | null; amount: number; reason: string; created_at: string }[]
}

export interface EsgGoal {
  goal_id: string
  title: string
  category: string
  description: string | null
  total_contributed_coins: number
  contributors_count: number
  target_coins?: number
  status: string
}

export interface ContributionResponse extends EsgGoal {
  employee_id: string
  coins_spent: number
  wallet_balance: number
}

export interface SelectResponse {
  employee_id: string
  event_id: string
  title: string
  status: string
  mode: 'solo' | 'team'
  next_step: string
}

// В dev-режиме Vite проксирует /api на бэкенд (см. vite.config.ts).
const BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message) }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, { credentials: 'include', ...init })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* тело не JSON */
    }
    throw new ApiError(detail, res.status)
  }
  return res.json() as Promise<T>
}

export const api = {
  catalog: () => request<Catalog>('/api/employees/catalog'),
  employees: () => request<EmployeeListItem[]>('/api/employees'),
  profile: (id: string) => request<EmployeeProfile>(`/api/employees/${id}/profile`),
  trajectory: (id: string) => request<TrajectoryItem[]>(`/api/employees/${id}/trajectory`),
  recommendations: (id: string, explain = false, language = 'ru', signal?: AbortSignal) => request<RecommendationsResponse>(`/api/employees/${id}/recommendations?include_explanations=${explain}&language=${encodeURIComponent(language)}`, { signal }),
  map: (id: string) => request<GameMap>(`/api/game/${id}/map`),
  complete: (id: string, eventId: string) =>
    request<CompleteResponse>(`/api/employees/${id}/quests/${eventId}/complete`, { method: 'POST' }),
  selectQuest: (id: string, eventId: string) => request<SelectResponse>(`/api/employees/${id}/quests/${eventId}/select`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mode: 'solo' }) }),
  questSteps: (id: string, eventId: string, language = 'ru', signal?: AbortSignal) => request<QuestPlan>(`/api/employees/${encodeURIComponent(id)}/quests/${encodeURIComponent(eventId)}/steps?language=${encodeURIComponent(language)}`, { signal }),
  completeQuestStep: (id: string, eventId: string, step: number) => request<QuestStepResult>(`/api/employees/${encodeURIComponent(id)}/quests/${encodeURIComponent(eventId)}/steps/${step}/complete`, { method: 'POST' }),
  wallet: (id: string) => request<WalletResponse>(`/api/wallet/${id}`),
  esgGoals: () => request<EsgGoal[]>('/api/esg-goals'),
  contribute: (id: string, goalId: string, coins: number) => request<ContributionResponse>(`/api/esg-goals/${goalId}/contribute`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ employee_id: id, coins }) }),
  hrDashboard: () => request<HrDashboard>('/api/hr/dashboard'),
}
