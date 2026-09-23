import { useCallback, useEffect, useState } from 'react'
import { api, type EmployeeProfile, type RecommendationsResponse, type TrajectoryItem } from '../api'
import { CareerMap } from '../components/CareerMap'
import { cityCopy } from '../cityCopy'
import { eventTitle } from '../catalog'
import { History } from '../components/History'
import { Icon } from '../components/Icon'
import { ProgressRing } from '../components/ProgressRing'
import { QuestCard } from '../components/QuestCard'
import { SkillGap } from '../components/SkillGap'
import { useI18n } from '../i18n'

interface Data {
  profile: EmployeeProfile
  recs: RecommendationsResponse
  history: TrajectoryItem[]
}

export function EmployeePage({ employeeId, onToast, query }: { employeeId: string; onToast: (msg: string) => void; query: string }) {
  const { t, lang } = useI18n()
  const c = cityCopy[lang]
  const jump = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  const [data, setData] = useState<Data | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      const [profile, recs, history] = await Promise.all([
        api.profile(employeeId),
        api.recommendations(employeeId),
        api.trajectory(employeeId),
      ])
      setData({ profile, recs, history })
    } catch (e) {
      setError((e as Error).message)
    }
  }, [employeeId])

  useEffect(() => {
    setData(null)
    load()
  }, [load])

  const complete = async (eventId: string) => {
    setBusy(eventId)
    try {
      const res = await api.complete(employeeId, eventId)
      await load()
      onToast(
        `${t('toast_done')}: ${res.completed_quest} · ${Math.round(res.progress_to_next_grade_before)}% → ${Math.round(
          res.progress_to_next_grade_after,
        )}%`,
      )
    } catch (e) {
      onToast(`⚠ ${(e as Error).message}`)
    } finally {
      setBusy(null)
    }
  }

  if (error)
    return (
      <div className="card state error">
        <p>{t('error_backend')}</p>
        <p style={{ fontSize: 13, color: 'var(--text-3)' }}>{error}</p>
        <button className="btn ghost" onClick={load}>
          {t('retry')}
        </button>
      </div>
    )

  if (!data)
    return (
      <div className="grid">
        <div className="skeleton" />
        <div className="grid grid-main">
          <div className="skeleton" style={{ minHeight: 360 }} />
          <div className="skeleton" style={{ minHeight: 360 }} />
        </div>
      </div>
    )

  const { profile: p, recs, history } = data
  const progress = recs.progress_to_next_grade ?? p.progress_to_next_grade

  const completed = history.filter((item) => item.status === 'completed')
  const recent = [...completed].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 3)
  const first = recs.recommendations[0]
  const filtered = recs.recommendations.filter((q) => `${q.quest_title} ${q.reason} ${q.affected_skills.map((s) => s.skill_name).join(' ')}`.toLowerCase().includes(query.toLowerCase().trim()))

  return (
    <div className="city-dashboard" id="home">
      <section className="city-hero" aria-labelledby="city-title">
        <div className="hero-copy">
          <span className="eyebrow">{c.eyebrow}</span>
          <h1 id="city-title">CAREER <span>CITY</span></h1>
          <p className="hero-headline">{c.headline}<br />{c.subline}</p>
          <div className="city-stats">
            <div><Icon name="city" size={29} /><span><b>{Object.keys(p.skills).length}</b><small>{c.buildings}</small></span></div>
            <div><Icon name="trophy" size={29} /><span><b>{completed.length}</b><small>{c.completed}</small></span></div>
            <div><Icon name="leaf" size={29} /><span><b>{recs.recommendations.length}</b><small>{c.available}</small></span></div>
          </div>
          <button className="btn hero-cta" onClick={() => jump('learning')}>{c.continue}<Icon name="arrow" /></button>
          <button className="text-button how-link" onClick={() => jump('city')}><span className="play-circle"><Icon name="play" size={14} /></span>{c.how}</button>
        </div>
        <div className="hero-progress card">
          <h2>{c.progress}<Icon name="leaf" /></h2>
          <div className="progress-content"><ProgressRing value={progress} caption={t('progress')} /><div><small>{c.target}</small><strong>{recs.target_grade}</strong><span>{recs.target_role}</span></div></div>
        </div>
        <div className="city-level"><Icon name="flag" size={20} /><span>{c.level}<strong>{p.grade}</strong></span></div>
        <button className="city-pin pin-skills" onClick={() => jump('skills')}><Icon name="shield" />{c.skills}<Icon name="arrow" size={13} /></button>
        <button className="city-pin pin-career" onClick={() => jump('city')}><Icon name="city" />{c.how}<Icon name="arrow" size={13} /></button>
      </section>

      <div className="overview-grid">
        <section className="card next-card">
          <h2 className="card-title">{c.current}<button className="text-button" onClick={() => jump('learning')}><Icon name="arrow" /></button></h2>
          {first ? <div className="next-course"><div className="course-art"><Icon name="book" size={40} /><span>CAREER<br />ACADEMY</span></div><div><span className="course-kicker">{first.quest_type}</span><h3>{first.quest_title}</h3><span className="chip primary">{first.format}</span><p className="course-duration"><Icon name="clock" size={15} />{first.duration_hours} {t('hours')}</p><button className="text-button" onClick={() => jump(`quest-${first.event_id}`)}>{c.details}<Icon name="arrow" size={15} /></button></div></div> : <p className="hero-sub">{t('no_recs')}</p>}
        </section>
        <section className="card ai-card">
          <h2 className="card-title">{c.ai}<button className="text-button" onClick={() => jump('recommendations')}>{c.all}<Icon name="arrow" size={14} /></button></h2>
          {recs.recommendations.slice(0, 3).map((q, i) => <button className="recommendation-row" key={q.event_id} onClick={() => jump(`quest-${q.event_id}`)}><span className={`rec-icon tone-${i}`}><Icon name={i === 0 ? 'code' : i === 1 ? 'people' : 'leaf'} size={25} /></span><span><strong>{q.quest_title}</strong><small>{q.affected_skills.map((s) => s.skill_name).join(' · ')}</small></span><span className="round-arrow"><Icon name="arrow" size={16} /></span></button>)}
          {!recs.recommendations.length && <p className="hero-sub">{t('no_recs')}</p>}
        </section>
        <section className="card achievements-card">
          <h2 className="card-title">{c.recent}<button className="text-button" onClick={() => jump('achievements')}><Icon name="arrow" /></button></h2>
          {recent.map((item, i) => <div className="achievement-row" key={item.record_id}><span className={`medal medal-${i}`}><Icon name={i === 0 ? 'shield' : 'trophy'} size={24} /></span><div><small>{t('status_completed')}</small><strong>{eventTitle(item.event_id)}</strong></div><time>{new Date(item.date).toLocaleDateString(lang === 'kk' ? 'kk-KZ' : lang === 'en' ? 'en-GB' : 'ru-RU', { day: 'numeric', month: 'short' })}</time></div>)}
          {!recent.length && <p className="hero-sub">{c.empty}</p>}
        </section>
      </div>
      <section className="growth-banner"><Icon name="trophy" size={35} /><p>{c.banner}<span>{c.support}</span></p><button className="btn" onClick={() => jump('recommendations')}>{c.explore}<Icon name="arrow" /></button><span className="banner-brand">✦ Halyk</span></section>
      <section id="city" className="city-map-section"><CareerMap role={p.role} grade={p.grade} targetRole={recs.target_role} targetGrade={recs.target_grade} progress={progress} /></section>
      <div className="grid grid-main" id="learning">
        <section className="card" id="recommendations">
          <h2 className="card-title">{t('next_quests')}<small>{filtered.length}</small></h2>
          {filtered.length === 0 ? <div className="state">{query.trim() ? c.noResults : t('no_recs')}</div> : filtered.map((q, i) => <div id={`quest-${q.event_id}`} className="quest-anchor" key={q.event_id}><QuestCard index={i} quest={q} busy={busy !== null} onComplete={() => complete(q.event_id)} /></div>)}
        </section>
        <div className="stack"><div id="skills"><SkillGap skills={p.skills} targetRole={recs.target_role} targetGrade={recs.target_grade} /></div><div id="achievements"><History items={history} /></div></div>
      </div>
    </div>
  )
}
