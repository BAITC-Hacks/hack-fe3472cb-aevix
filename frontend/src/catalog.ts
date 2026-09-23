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

export interface Catalog {
  skills: SkillDef[]
  role_profiles: RoleProfile[]
  events: EventDef[]
}
let roleProfiles: RoleProfile[] = []
const skillById = new Map<string, SkillDef>()
const eventById = new Map<string, EventDef>()

export function setCatalog(data: Catalog) {
  roleProfiles = data.role_profiles
  skillById.clear()
  eventById.clear()
  data.skills.forEach((s) => skillById.set(s.skill_id, s))
  data.events.forEach((e) => eventById.set(e.event_id, e))
}

export const skillName = (id: string) => skillById.get(id)?.name ?? id.replace(/^SK_/, '').replace(/_/g, ' ')
export const skillType = (id: string) => skillById.get(id)?.type ?? 'hard'
export const eventInfo = (id: string) => eventById.get(id)
export const eventTitle = (id: string) => eventById.get(id)?.title ?? id

export function roleProfile(role: string, grade: string): RoleProfile | undefined {
  return roleProfiles.find((p) => p.role === role && p.grade === grade)
}


const eventLabels = {
  ru: { course: 'Курс', workshop: 'Практикум', certification: 'Сертификация', compliance: 'Обязательное обучение', meetup: 'Встреча', mentoring: 'Менторство', onboarding: 'Адаптация', online: 'Онлайн', offline: 'Очно', self_paced: 'В своём темпе' },
  kk: { course: 'Курс', workshop: 'Практикум', certification: 'Сертификаттау', compliance: 'Міндетті оқу', meetup: 'Кездесу', mentoring: 'Тәлімгерлік', onboarding: 'Бейімделу', online: 'Онлайн', offline: 'Офлайн', self_paced: 'Өз қарқынымен' },
  en: { course: 'Course', workshop: 'Workshop', certification: 'Certification', compliance: 'Required learning', meetup: 'Meetup', mentoring: 'Mentoring', onboarding: 'Onboarding', online: 'Online', offline: 'In person', self_paced: 'Self-paced' },
}
export function eventLabel(value: string, lang: keyof typeof eventLabels) {
  return eventLabels[lang][value as keyof typeof eventLabels.ru] ?? value
}
