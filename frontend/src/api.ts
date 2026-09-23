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
  date: string
  completion_pct: number
  score: number | null
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

// В dev-режиме Vite проксирует /api на бэкенд (см. vite.config.ts).
const BASE = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message) }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, init)
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
  recommendations: (id: string) => request<RecommendationsResponse>(`/api/employees/${id}/recommendations`),
  map: (id: string) => request<GameMap>(`/api/game/${id}/map`),
  complete: (id: string, eventId: string) =>
    request<CompleteResponse>(`/api/employees/${id}/quests/${eventId}/complete`, { method: 'POST' }),
  hrDashboard: () => request<HrDashboard>('/api/hr/dashboard'),
}
