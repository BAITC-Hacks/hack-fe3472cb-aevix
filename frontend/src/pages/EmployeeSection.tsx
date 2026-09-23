import type { EmployeeProfile, GameMap, RecommendationsResponse, TrajectoryItem } from '../api'
import type { Page } from '../routes'
import { cityCopy } from '../cityCopy'
import { eventTitle } from '../catalog'
import { CityPage } from './CityPage'
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
  const active = history.filter((item) => ['in_progress', 'overdue'].includes(item.status))
  const completed = history.filter((item) => item.status === 'completed')
  const recommendations = recs.recommendations.filter((item) => `${item.quest_title} ${item.reason} ${item.affected_skills.map((s) => s.skill_name).join(' ')}`.toLowerCase().includes(query.trim().toLowerCase()))
  return <div className="section-page">
    <header className="page-head"><span className="eyebrow">CAREER CITY</span><h1>{c[page]}</h1><p>{page === 'city' ? c.cityNote : page === 'learning' ? c.learningNote : page === 'skills' ? c.skillsNote : page === 'recommendations' ? c.recommendationsNote : c.achievementsNote}</p></header>
    {page === 'recommendations' && <div className="quest-page-grid">
      {recommendations.length ? recommendations.map((quest, index) => <QuestCard key={quest.event_id} index={index} quest={quest} busy={busy} onComplete={() => onComplete(quest.event_id)} />) : <div className="card state">{query.trim() ? c.noResults : t('no_recs')}</div>}
    </div>}
    {page === 'skills' && <SkillGap skills={profile.skills} targetRole={recs.target_role} targetGrade={recs.target_grade} />}
    {page === 'learning' && <div className="grid">
      <section className="card"><h2 className="card-title">{t('status_in_progress')}<small>{active.length}</small></h2>
        {active.length ? active.map((item) => <article key={item.record_id} className="learning-row"><div><h3>{eventTitle(item.event_id)}</h3>{item.status === 'overdue' && <span className="chip danger">{t('status_overdue')}</span>}<progress max={100} value={item.completion_pct} aria-label={eventTitle(item.event_id)} /><span>{item.completion_pct}%</span></div><button className="btn" disabled={busy} onClick={() => onComplete(item.event_id)}>{t('mark_done')}</button></article>) : <div className="state"><Icon name="book" size={32} /><p>{c.noActive}</p><button className="btn" onClick={() => navigate('recommendations')}>{c.explore}<Icon name="arrow" /></button></div>}
      </section><History items={history} />
    </div>}
    {page === 'achievements' && <div className="grid"><div className="achievement-summary card"><Icon name="trophy" size={36} /><div><strong>{new Set(completed.map((item) => item.event_id)).size}</strong><p>{c.completed}</p></div><ProgressRing value={profile.progress_to_next_grade} caption={t('progress')} /></div>{completed.length ? <History items={completed} /> : <div className="card state">{c.empty}</div>}</div>}
    {page === 'city' && <CityPage profile={profile} recs={recs} map={map} navigate={navigate} />}
  </div>
}
