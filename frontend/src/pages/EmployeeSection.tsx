import { useState } from 'react'
import type { EmployeeProfile, GameMap, RecommendationsResponse, TrajectoryItem } from '../api'
import type { Page } from '../routes'
import { cityCopy } from '../cityCopy'
import { eventTitle } from '../catalog'
import { CityPage } from './CityPage'
import { CareerAssistant } from '../components/CareerAssistant'
import { History } from '../components/History'
import { Icon } from '../components/Icon'
import { ProgressRing } from '../components/ProgressRing'
import { QuestCard } from '../components/QuestCard'
import { SkillGap } from '../components/SkillGap'
import { useI18n } from '../i18n'

interface Props {
  page: Exclude<Page, 'home' | 'hr'>
  profile: EmployeeProfile
  recs: RecommendationsResponse
  history: TrajectoryItem[]
  map: GameMap
  query: string
  busy: string | null
  onSelect: (id: string) => void
  onRefresh: () => void
  onComplete: (id: string) => void
  navigate: (page: Page) => void
}

export function EmployeeSection({ page, profile, recs, history, map, query, busy, onComplete, onSelect, onRefresh, navigate }: Props) {
  const { t, lang } = useI18n()
  const c = cityCopy[lang]
  const [filter, setFilter] = useState('all')
  const copy = {
    ru: { all: 'Все', short: 'До 4 часов', critical: 'Ключевые навыки', found: 'Подходит занятий', reset: 'Сбросить фильтры', hint: 'Начните с первого занятия: рекомендации расположены по соответствию вашей цели.', saving: 'Сохраняем…' },
    kk: { all: 'Барлығы', short: '4 сағатқа дейін', critical: 'Негізгі дағдылар', found: 'Сәйкес сабақтар', reset: 'Сүзгілерді тазалау', hint: 'Бірінші сабақтан бастаңыз: ұсыныстар мақсатыңызға сәйкестігі бойынша реттелген.', saving: 'Сақталуда…' },
    en: { all: 'All', short: 'Up to 4 hours', critical: 'Critical skills', found: 'Matching activities', reset: 'Reset filters', hint: 'Start with the first activity: recommendations are ranked by fit for your goal.', saving: 'Saving…' },
  }[lang]
  const active = history.filter((item) => ['in_progress', 'overdue'].includes(item.status))
  const selectedIds = new Set([...active.map((item) => item.event_id), ...(map.selected_quests ?? []).map((item) => item.event_id)])
  const completed = history.filter((item) => item.status === 'completed')
  const recommendations = recs.recommendations.filter((item) => `${item.quest_title} ${item.reason} ${item.affected_skills.map((s) => s.skill_name).join(' ')}`.toLowerCase().includes(query.trim().toLowerCase())).filter((item) => filter === 'short' ? item.duration_hours <= 4 : filter === 'critical' ? item.affected_skills.some((skill) => skill.is_critical) : true)
  return <div className="section-page">
    <header className="page-head"><span className="eyebrow">CAREER CITY</span><h1>{c[page]}</h1><p>{page === 'city' ? c.cityNote : page === 'learning' ? c.learningNote : page === 'skills' ? c.skillsNote : page === 'recommendations' ? c.recommendationsNote : c.achievementsNote}</p></header>
    {page === 'recommendations' && <>
      <CareerAssistant recs={recs} />
      <div className="recommendation-toolbar">
        <div className="filter-pills" role="group" aria-label={c.filters}>{(['all', 'short', 'critical'] as const).map((value) => <button key={value} aria-pressed={filter === value} className={filter === value ? 'selected' : ''} onClick={() => setFilter(value)}>{copy[value]}</button>)}</div>
        <span role="status">{copy.found}: {recommendations.length} / {recs.recommendations.length}</span>
      </div>
      <div className="quest-page-grid">
        {recommendations.length ? recommendations.map((quest) => <QuestCard key={quest.event_id} index={recs.recommendations.indexOf(quest)} quest={quest} busy={busy !== null} saving={busy === quest.event_id} selected={selectedIds.has(quest.event_id)} onSelect={() => onSelect(quest.event_id)} onContinue={() => navigate('learning')} />) : <div className="card state recommendation-empty"><Icon name="search" size={30} /><p>{query.trim() || filter !== 'all' ? c.noResults : t('no_recs')}</p>{filter !== 'all' && <button className="btn ghost" onClick={() => setFilter('all')}>{copy.reset}</button>}</div>}
      </div>
    </>}
    {page === 'skills' && <SkillGap skills={profile.skills} targetRole={recs.target_role} targetGrade={recs.target_grade} />}
    {page === 'learning' && <div className="grid">
      <section className="card"><h2 className="card-title">{t('status_in_progress')}<small>{active.length}</small></h2>
        {active.length ? active.map((item) => <article key={item.record_id} className="learning-row"><div><h3>{eventTitle(item.event_id)}</h3>{item.status === 'overdue' && <span className="chip danger">{t('status_overdue')}</span>}<progress max={100} value={item.completion_pct} aria-label={eventTitle(item.event_id)} /><span>{item.completion_pct}%</span></div><button className="btn" disabled={busy !== null} aria-busy={busy === item.event_id} onClick={() => onComplete(item.event_id)}>{busy === item.event_id ? copy.saving : t('mark_done')}</button></article>) : <div className="state"><Icon name="book" size={32} /><p>{c.noActive}</p><button className="btn" onClick={() => navigate('recommendations')}>{c.explore}<Icon name="arrow" /></button></div>}
      </section><History items={history} />
    </div>}
    {page === 'achievements' && <div className="grid"><div className="achievement-summary card"><Icon name="trophy" size={36} /><div><strong>{new Set(completed.map((item) => item.event_id)).size}</strong><p>{c.completed}</p></div><ProgressRing value={profile.progress_to_next_grade} caption={t('progress')} /></div>{completed.length ? <History items={completed} /> : <div className="card state">{c.empty}</div>}</div>}
    {page === 'city' && <CityPage profile={profile} recs={recs} map={map} navigate={navigate} onRefresh={onRefresh} />}
  </div>
}
