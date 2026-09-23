import { useCallback, useEffect, useState } from 'react'
import { api, type HrDashboard } from '../api'
import { eventTitle, skillName } from '../catalog'
import { Icon } from '../components/Icon'
import { useI18n } from '../i18n'

export function HrPage() {
  const { t } = useI18n()
  const [data, setData] = useState<HrDashboard | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    setError(null)
    api.hrDashboard().then(setData, (e: Error) => setError(e.message))
  }, [])

  useEffect(load, [load])

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
        <div className="skeleton" style={{ minHeight: 100 }} />
        <div className="skeleton" style={{ minHeight: 320 }} />
      </div>
    )

  const maxAffected = Math.max(...data.top_skill_gaps.map((g) => g.affected_employees), 1)
  const maxPopular = Math.max(...data.popular_events.map((e) => e.count), 1)

  return (
    <div>
      <div className="page-head">
        <h1>{t('hr_title')}</h1>
        <p>
          <Icon name="shield" size={14} /> {t('hr_note')}
        </p>
      </div>

      <div className="grid">
        <div className="kpis">
          <div className="card kpi">
            <div className="kpi-label">{t('kpi_employees')}</div>
            <div className="kpi-value">{data.total_employees}</div>
          </div>
          <div className="card kpi">
            <div className="kpi-label">{t('kpi_progress')}</div>
            <div className="kpi-value">
              {Math.round(data.average_progress_to_next_grade)}
              <small>%</small>
            </div>
          </div>
          <div className="card kpi">
            <div className="kpi-label">{t('kpi_completion')}</div>
            <div className="kpi-value">
              {Math.round(data.events_completion_rate * 100)}
              <small>%</small>
            </div>
          </div>
          <div className="card kpi">
            <div className="kpi-label">{t('kpi_inactive')}</div>
            <div className="kpi-value">{data.inactive_employees_count}</div>
          </div>
        </div>

        <div className="grid grid-main">
          <section className="card">
            <h2 className="card-title">{t('top_gaps')}</h2>
            <div className="hbars">
              {data.top_skill_gaps.map((g) => (
                <div key={g.skill_id}>
                  <div className="hbar-head">
                    <b>{skillName(g.skill_id)}</b>
                    <span>
                      {g.affected_employees} {t('affected')} · {t('avg_gap')} {g.average_gap.toFixed(1)}
                    </span>
                  </div>
                  <div className="hbar warm">
                    <div style={{ width: `${(g.affected_employees / maxAffected) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </section>

          <div className="stack">
            <section className="card">
              <h2 className="card-title">{t('popular')}</h2>
              <div className="hbars">
                {data.popular_events.map((e) => (
                  <div key={e.event_id}>
                    <div className="hbar-head">
                      <b>{eventTitle(e.event_id)}</b>
                      <span>{e.count}</span>
                    </div>
                    <div className="hbar">
                      <div style={{ width: `${(e.count / maxPopular) * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="card">
              <h2 className="card-title">{t('risky')}</h2>
              <div className="meta" style={{ marginTop: 0 }}>
                {data.risky_segments.map((s) => (
                  <span key={s} className="chip danger">
                    {s}
                  </span>
                ))}
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  )
}
