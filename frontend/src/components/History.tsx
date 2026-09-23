import type { TrajectoryItem } from '../api'
import { eventTitle } from '../catalog'
import { useI18n, type TKey } from '../i18n'
import { Icon } from './Icon'

const statusChip: Record<string, string> = {
  completed: 'ok',
  in_progress: 'info',
  dropped: 'danger',
  overdue: 'danger',
  no_show: 'danger',
  declined: '',
}

function timestamp(date: string | null | undefined) {
  if (!date) return -Infinity
  const value = new Date(date).getTime()
  return Number.isFinite(value) ? value : -Infinity
}

export function History({ items }: { items: TrajectoryItem[] }) {
  const { t, lang } = useI18n()
  const locale = lang === 'kk' ? 'kk-KZ' : lang === 'en' ? 'en-GB' : 'ru-RU'
  const copy = {
    ru: { noDate: 'Дата не указана', score: 'Результат', progress: 'Пройдено' },
    kk: { noDate: 'Күні көрсетілмеген', score: 'Нәтиже', progress: 'Орындалған' },
    en: { noDate: 'No date recorded', score: 'Score', progress: 'Completed' },
  }[lang]
  const sorted = [...items].sort((a, b) => timestamp(b.date) - timestamp(a.date))

  return (
    <div className="card history-card">
      <h2 className="card-title">
        {t('history')}
        <small>{items.length}</small>
      </h2>
      {sorted.length === 0 ? (
        <div className="state"><Icon name="book" size={26} />{t('empty_history')}</div>
      ) : (
        <ul className="timeline">
          {sorted.map((item) => {
            const date = timestamp(item.date)
            const progress = Math.round(Math.max(0, Math.min(100, item.completion_pct || 0)))
            const status = Object.prototype.hasOwnProperty.call(statusChip, item.status) ? t(`status_${item.status}` as TKey) : item.status
            return (
              <li key={item.record_id} className="tl-item">
                <span className={`tl-dot ${item.status}`} aria-hidden="true" />
                <div className="tl-content">
                  <div className="tl-title">{eventTitle(item.event_id)}</div>
                  <div className="tl-meta">
                    <span className="tl-date">
                      {Number.isFinite(date) ? <time dateTime={item.date ?? undefined}>{new Date(date).toLocaleDateString(locale, { day: 'numeric', month: 'short', year: 'numeric' })}</time> : copy.noDate}
                    </span>
                    {item.score != null && Number.isFinite(item.score) && <span className="tl-score">{copy.score}: {item.score}/100</span>}
                    {item.status === 'in_progress' && <span className="tl-score">{copy.progress}: {progress}%</span>}
                  </div>
                </div>
                <div className="tl-right">
                  <span className={`chip ${statusChip[item.status] ?? ''}`}>{status}</span>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
