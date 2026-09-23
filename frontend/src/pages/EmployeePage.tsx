import type { Page } from '../routes'
import { EmployeeSection } from './EmployeeSection'
import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError, type EmployeeProfile, type RecommendationsResponse, type GameMap, type TrajectoryItem } from '../api'
import { cityCopy } from '../cityCopy'
import { eventInfo, eventTitle, eventLabel } from '../catalog'
import { Icon } from '../components/Icon'
import { ProgressRing } from '../components/ProgressRing'
import { useI18n } from '../i18n'

interface Data {
  profile: EmployeeProfile
  recs: RecommendationsResponse
  history: TrajectoryItem[]
  map: GameMap
}

export function EmployeePage({ employeeId, onToast, query, page, navigate }: { employeeId: string; onToast: (msg: string) => void; query: string; page: Exclude<Page, 'hr'>; navigate: (page: Page) => void }) {
  const { t, lang } = useI18n()
  const c = cityCopy[lang]
  const [data, setData] = useState<Data | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])

  const load = useCallback(async () => {
    setError(null)
    try {
      const [profile, recs, history, map] = await Promise.all([
        api.profile(employeeId),
        api.recommendations(employeeId),
        api.trajectory(employeeId),
        api.map(employeeId),
      ])
      setData({ profile, recs, history, map })
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
      if (!mounted.current) return
      onToast(
        `${t('toast_done')}: ${res.completed_quest} · ${Math.round(res.progress_to_next_grade_before)}% → ${Math.round(
          res.progress_to_next_grade_after,
        )}%${res.coins_earned ? ` · +${res.coins_earned} ${c.balance.toLowerCase()}` : ''}`,
      )
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) await load()
      if (!mounted.current) return
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

  const { profile: p, recs, history, map } = data
  const progress = recs.progress_to_next_grade ?? p.progress_to_next_grade

  const completed = history.filter((item) => item.status === 'completed')
  const active = history.filter((item) => ['in_progress', 'overdue'].includes(item.status))
  const current = active[0]
  const first = recs.recommendations[0]
  const currentInfo = current ? eventInfo(current.event_id) : null
  const wallet = map.center?.wallet_balance

  if (page !== 'home') return <EmployeeSection page={page} profile={p} recs={recs} history={history} map={map} query={query} busy={busy !== null} onComplete={complete} navigate={navigate} />

  return (
    <div className="dashboard">
      <header className="page-head home-heading"><div><span className="eyebrow">{c.greeting}</span><h1>{p.full_name.split(' ')[0]}<span className="greeting-dot">.</span></h1><p>{c.overview}</p></div><span className="chip primary">{p.grade} · {p.role}</span></header>
      <section className="dashboard-hero">
        <div className="dashboard-hero-copy"><span className="eyebrow">CAREER CITY</span><h2>{c.headline}<br />{c.subline}</h2><p>{c.homeNote}</p><button className="btn" onClick={() => navigate(current ? 'learning' : 'recommendations')}>{current ? c.continue : c.explore}<Icon name="arrow" /></button></div>
        <span className="hero-caption"><Icon name="city" size={16} />{c.city}</span>
      </section>
      <div className="dashboard-metrics">
        <button className="metric" onClick={() => navigate('learning')}><span className="metric-icon"><Icon name="book" size={21} /></span><span><small>{c.inProgress}</small><strong>{active.length}</strong></span><Icon name="arrow" size={16} /></button>
        <button className="metric" onClick={() => navigate('achievements')}><span className="metric-icon gold"><Icon name="trophy" size={21} /></span><span><small>{c.completed}</small><strong>{new Set(completed.map((item) => item.event_id)).size}</strong></span><Icon name="arrow" size={16} /></button>
        <button className="metric" onClick={() => navigate('city')}><span className="metric-icon"><Icon name="leaf" size={21} /></span><span><small>{wallet !== undefined ? c.balance : c.skills}</small><strong>{wallet !== undefined ? wallet.toLocaleString(lang) : Object.keys(p.skills).length}</strong></span><Icon name="arrow" size={16} /></button>
      </div>
      <div className="dashboard-bottom">
        <section className="card next-step"><div className="card-title"><h2>{current ? c.learning : c.nextStep}</h2><span className="chip">{current ? t(current.status === 'overdue' ? 'status_overdue' : 'status_in_progress') : c.recommendations}</span></div>
          {current || first ? <div className="next-course"><div className="course-art"><Icon name="book" size={34} /></div><div><h3>{current ? eventTitle(current.event_id) : first.quest_title}</h3><p>{current ? `${current.completion_pct}% · ${eventLabel(currentInfo?.format ?? '', lang)}` : `${first.duration_hours} ${t('hours')} · ${eventLabel(first.format, lang)}`}</p>{current && <progress value={current.completion_pct} max={100} aria-label={c.progress} />}<button className="text-button" onClick={() => navigate(current ? 'learning' : 'recommendations')}>{current ? c.continue : c.details}<Icon name="arrow" size={16} /></button></div></div> : <p className="state">{t('no_recs')}</p>}
        </section>
        <section className="card goal-card"><div className="card-title"><h2>{c.progress}</h2><button className="text-button" onClick={() => navigate('skills')}>{c.details}<Icon name="arrow" size={15} /></button></div><div className="goal-content"><ProgressRing value={progress} caption={t('progress')} size={100} /><div><small>{c.target}</small><h3>{recs.target_grade}</h3><p>{recs.target_role}</p></div></div></section>
      </div>
    </div>
  )
}
