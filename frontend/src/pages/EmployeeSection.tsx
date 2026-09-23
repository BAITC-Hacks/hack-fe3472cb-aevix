import type { EmployeeProfile, GameMap, RecommendationsResponse, TrajectoryItem } from '../api'
import type { Page } from '../routes'
import { cityCopy } from '../cityCopy'
import { eventTitle } from '../catalog'
import { CareerMap } from '../components/CareerMap'
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
  busy: boolean
  onComplete: (id: string) => void
  navigate: (page: Page) => void
}

export function EmployeeSection({ page, profile, recs, history, map, query, busy, onComplete, navigate }: Props) {
  const { t, lang } = useI18n()
  const c = cityCopy[lang]
  const active = history.filter((item) => item.status === 'in_progress')
  const completed = history.filter((item) => item.status === 'completed')
  const recommendations = recs.recommendations.filter((item) => `${item.quest_title} ${item.reason} ${item.affected_skills.map((s) => s.skill_name).join(' ')}`.toLowerCase().includes(query.trim().toLowerCase()))
  return <div className="section-page">
    <header className="page-head"><span className="eyebrow">CAREER CITY</span><h1>{c[page]}</h1><p>{profile.full_name} · {profile.grade} {profile.role} <span aria-hidden="true">→</span> {recs.target_grade} {recs.target_role}</p></header>
    {page === 'recommendations' && <div className="quest-page-grid">
      {recommendations.length ? recommendations.map((quest, index) => <QuestCard key={quest.event_id} index={index} quest={quest} busy={busy} onComplete={() => onComplete(quest.event_id)} />) : <div className="card state">{query.trim() ? c.noResults : t('no_recs')}</div>}
    </div>}
    {page === 'skills' && <SkillGap skills={profile.skills} targetRole={recs.target_role} targetGrade={recs.target_grade} />}
    {page === 'learning' && <div className="grid">
      <section className="card"><h2 className="card-title">{t('status_in_progress')}<small>{active.length}</small></h2>
        {active.length ? active.map((item) => <article key={item.record_id} className="learning-row"><div><h3>{eventTitle(item.event_id)}</h3><progress max={100} value={item.completion_pct} aria-label={eventTitle(item.event_id)} /><span>{item.completion_pct}%</span></div><button className="btn" disabled={busy} onClick={() => onComplete(item.event_id)}>{t('mark_done')}</button></article>) : <div className="state"><p>{t('empty_history')}</p><button className="btn" onClick={() => navigate('recommendations')}>{c.explore}<Icon name="arrow" /></button></div>}
      </section><History items={history} />
    </div>}
    {page === 'achievements' && <div className="grid"><div className="achievement-summary card"><Icon name="trophy" size={36} /><div><strong>{completed.length}</strong><p>{c.completed}</p></div><ProgressRing value={profile.progress_to_next_grade} caption={t('progress')} /></div>{completed.length ? <History items={completed} /> : <div className="card state">{c.empty}</div>}</div>}
    {page === 'city' && <div className="grid"><section className="city-overview card"><div><span className="chip primary">{c.level} {map.career_level}</span><h2>{map.current_zone} → {map.target_zone}</h2><p>{recs.target_role}</p><button className="btn" onClick={() => navigate('recommendations')}>{c.explore}<Icon name="arrow" /></button></div><ProgressRing value={map.progress_to_next_grade} caption={t('progress')} /></section><CareerMap role={profile.role} grade={profile.grade} targetRole={recs.target_role} targetGrade={recs.target_grade} progress={map.progress_to_next_grade} /><div className="city-node-grid">{map.nodes.map((node) => <div className={`card city-node ${node.status}`} key={node.id}><Icon name={node.status === 'completed' ? 'check' : node.status === 'locked' ? 'shield' : 'flag'} size={25} /><h3>{node.id === 'profile' ? t('nav_me') : node.id === 'core_skills' ? c.skills : `${c.target}: ${map.target_zone}`}</h3><span>{node.status === 'completed' ? t('done') : node.status === 'active' ? t('you_are_here') : t('target')}</span></div>)}</div></div>}
  </div>
}
