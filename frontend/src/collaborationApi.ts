import { ApiError, type CompleteResponse } from './api'

export interface LearningTeam {
  team_id: string
  name: string
  creator_id: string
  max_members: number
  status: 'active' | 'in_progress' | 'paused' | 'waiting_for_member'
  completed_team_quests: number
  member_ids: string[]
  current_quest: { event_id: string; status: string; started_at: string | null } | null
}

export type PairFormat = 'online_together' | 'in_person' | 'self_paced_discussion'

export interface PairInvitation {
  invitation_id: string
  event_id: string
  activity_title: string
  activity_type: string | null
  activity_format: PairFormat
  start_date: string | null
  end_date: string | null
  display_name: string
  display_mode: 'name' | 'alias'
  status: string
}

export interface PairPreview {
  invitation_id: string
  event_id: string
  activity_title: string
  eligible: boolean
  can_respond: boolean
  explanation: string
  employee_friendly_reason: string
}

export interface LearningPair {
  pair_id: string
  event_id: string
  activity_title: string
  members: string[]
  status: string
  next_step: string
  messages: unknown[]
}

interface PairResponse {
  invitation_id: string
  status: 'accepted' | 'declined' | 'not_a_match'
  eligible: boolean
  pair_id?: string
}

const BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')
const id = encodeURIComponent

async function request<T>(path: string, body?: unknown, method = body === undefined ? 'GET' : 'POST'): Promise<T> {
  const response = await fetch(BASE + path, {
    credentials: 'include',
    method,
    ...(body === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const value = await response.json()
      if (typeof value.detail === 'string') detail = value.detail
    } catch { /* A failed request may have a non-JSON response. */ }
    throw new ApiError(detail, response.status)
  }
  return response.json() as Promise<T>
}

export const collaborationApi = {
  team: (teamId: string) => request<LearningTeam>(`/api/teams/${id(teamId)}`),
  createTeam: (creator_id: string, name: string, max_members: number) => request<LearningTeam>('/api/teams', { creator_id, name, max_members }),
  joinTeam: (teamId: string, employee_id: string) => request<LearningTeam>(`/api/teams/${id(teamId)}/join`, { employee_id }),
  teamStatus: (teamId: string, action: 'pause' | 'resume') => request<LearningTeam>(`/api/teams/${id(teamId)}/${action}`, undefined, 'POST'),
  startTeamQuest: (teamId: string, eventId: string) => request<LearningTeam>(`/api/teams/${id(teamId)}/quests/${id(eventId)}/start`, undefined, 'POST'),
  completeTeamQuest: (teamId: string, eventId: string) => request<LearningTeam & { member_results: CompleteResponse[] }>(`/api/teams/${id(teamId)}/quests/${id(eventId)}/complete`, undefined, 'POST'),
  invitations: (employeeId?: string) => request<PairInvitation[]>(`/api/pairs/invitations${employeeId ? `?employee_id=${id(employeeId)}` : ''}`),
  invite: (payload: { inviter_id: string; event_id: string; format: PairFormat; display_mode: 'name' | 'alias'; display_name?: string; start_date?: string; end_date?: string }) => request<PairInvitation>('/api/pairs/invitations', payload),
  preview: (invitationId: string, employeeId: string) => request<PairPreview>(`/api/pairs/invitations/${id(invitationId)}/preview?employee_id=${id(employeeId)}`),
  respond: (invitationId: string, employee_id: string, decision: 'accept' | 'decline') => request<PairResponse>(`/api/pairs/invitations/${id(invitationId)}/respond`, { employee_id, decision }),
  pair: (pairId: string) => request<LearningPair>(`/api/pairs/${id(pairId)}`),
}
