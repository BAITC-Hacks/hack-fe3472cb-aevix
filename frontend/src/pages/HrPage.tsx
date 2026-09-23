import { useCallback, useEffect, useState } from 'react'
import { api, ApiError, type HrDashboard } from '../api'
import { eventTitle, skillName } from '../catalog'
import { Icon } from '../components/Icon'
import { useI18n } from '../i18n'

export function HrPage({ onUnauthorized }: { onUnauthorized: () => void }) {
  const { t, lang } = useI18n()
  const copy = {
    ru: {
      employees: 'Все сотрудники в системе', progress: 'По требованиям к целевой роли и грейду',
      completion: 'Доля завершённых записей за всю историю', inactive: 'Нет активного или завершённого обучения',
      gaps: 'Навыки, которых не хватает для карьерных целей сотрудников.',
      popular: 'По числу записей в истории, включая незавершённые мероприятия.',
      risks: 'Грейды, в которых есть неактивные сотрудники.',
      noGaps: 'Разрывы в навыках не найдены', noEvents: 'История обучения пока пуста', noRisks: 'Сегменты риска не обнаружены',
    },
    kk: {
      employees: 'Жүйедегі барлық қызметкерлер', progress: 'Мақсатты рөл мен грейд талаптары бойынша',
      completion: 'Барлық тарихтағы аяқталған жазбалардың үлесі', inactive: 'Белсенді немесе аяқталған оқу жоқ',
      gaps: 'Қызметкерлердің мансаптық мақсаттарына жету үшін жетіспейтін дағдылар.',
      popular: 'Аяқталмаған іс-шараларды қоса, тарихтағы жазбалар саны бойынша.',
      risks: 'Белсенді емес қызметкерлер бар грейдтер.',
      noGaps: 'Дағды олқылықтары табылмады', noEvents: 'Оқу тарихы әзірге бос', noRisks: 'Тәуекел сегменттері анықталмады',
    },
    en: {
      employees: 'All employees in the system', progress: 'Based on target role and grade requirements',
      completion: 'Completed records across all learning history', inactive: 'No active or completed learning',
      gaps: 'Skills employees need to develop to reach their career goals.',
      popular: 'By number of history records, including unfinished activities.',
      risks: 'Grades with inactive employees.',
      noGaps: 'No skill gaps found', noEvents: 'No learning history yet', noRisks: 'No risk segments found',
    },
  }[lang]
  const [data, setData] = useState<HrDashboard | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    setError(null)
    api.hrDashboard().then(setData, (e: Error) => {
      if (e instanceof ApiError && (e.status === 401 || e.status === 403)) onUnauthorized()
      else setError(e.message)
    })
  }, [onUnauthorized])

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
            <p className="panel-hint">{copy.employees}</p>
          </div>
          <div className="card kpi">
            <div className="kpi-label">{t('kpi_progress')}</div>
            <div className="kpi-value">
              {Math.round(data.average_progress_to_next_grade)}
              <small>%</small>
            </div>
            <p className="panel-hint">{copy.progress}</p>
          </div>
          <div className="card kpi">
            <div className="kpi-label">{t('kpi_completion')}</div>
            <div className="kpi-value">
              {Math.round(data.events_completion_rate * 100)}
              <small>%</small>
            </div>
            <p className="panel-hint">{copy.completion}</p>
          </div>
          <div className="card kpi">
            <div className="kpi-label">{t('kpi_inactive')}</div>
            <div className="kpi-value">{data.inactive_employees_count}</div>
            <p className="panel-hint">{copy.inactive}</p>
          </div>
        </div>

        <div className="grid grid-main">
          <section className="card">
            <h2 className="card-title">{t('top_gaps')}</h2>
            <p className="panel-hint">{copy.gaps}</p>
            {data.top_skill_gaps.length === 0 ? <p className="state">{copy.noGaps}</p> : <div className="hbars">
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
            </div>}
          </section>

          <div className="stack">
            <section className="card">
              <h2 className="card-title">{t('popular')}</h2>
              <p className="panel-hint">{copy.popular}</p>
              {data.popular_events.length === 0 ? <p className="state">{copy.noEvents}</p> : <div className="hbars">
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
              </div>}
            </section>

            <section className="card">
              <h2 className="card-title">{t('risky')}</h2>
              <p className="panel-hint">{copy.risks}</p>
              {data.risky_segments.length === 0 ? <p className="state">{copy.noRisks}</p> : <div className="meta" style={{ marginTop: 0 }}>
                {data.risky_segments.map((s) => (
                  <span key={s} className="chip danger">
                    {s}
                  </span>
                ))}
              </div>}
            </section>
          </div>
        </div>
      </div>
    </div>
  )
}
