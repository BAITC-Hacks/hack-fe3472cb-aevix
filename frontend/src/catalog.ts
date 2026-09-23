// Справочники (названия навыков, требования ролей, мероприятия) берём прямо из датасета кейса.
import skillsData from '../../case_1/career_quest_dataset/skills.json'
import eventsData from '../../case_1/career_quest_dataset/events.json'
import type { Grade } from './api'

export const GRADES: Grade[] = ['Junior', 'Middle', 'Senior', 'Lead']

interface SkillDef {
  skill_id: string
  name: string
  type: 'hard' | 'soft'
  category: string
}

interface RoleProfile {
  role: string
  grade: Grade
  required_skills: Record<string, number>
  critical_skills: string[]
}

export interface EventDef {
  event_id: string
  title: string
  description: string
  type: string
  format: string
  duration_hours: number
  mandatory: boolean
  upcoming_sessions: string[]
}

const skills = skillsData.skills as unknown as SkillDef[]
const roleProfiles = skillsData.role_profiles as unknown as RoleProfile[]
const events = eventsData.events as unknown as EventDef[]

const skillById = new Map(skills.map((s) => [s.skill_id, s]))
const eventById = new Map(events.map((e) => [e.event_id, e]))

export const skillName = (id: string) => skillById.get(id)?.name ?? id.replace(/^SK_/, '').replace(/_/g, ' ')
export const skillType = (id: string) => skillById.get(id)?.type ?? 'hard'
export const eventInfo = (id: string) => eventById.get(id)
export const eventTitle = (id: string) => eventById.get(id)?.title ?? id

export function roleProfile(role: string, grade: string): RoleProfile | undefined {
  return roleProfiles.find((p) => p.role === role && p.grade === grade)
}

export const proficiency = skillsData.proficiency_scale as Record<string, string>
