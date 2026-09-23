import type { TrajectoryItem } from '../api'
import { eventTitle } from '../catalog'
import { useI18n, type TKey } from '../i18n'

const statusChip: Record<string, string> = {
  completed: 'ok',
  in_progress: 'info',
  dropped: 'danger',
  overdue: 'danger',
  no_show: 'danger',
  declined: '',
}

export function History({ items }: { items: TrajectoryItem[] }) {
  const { t, lang } = useI18n()
  const locale = lang === 'kk' ? 'kk-KZ' : lang === 'en' ? 'en-GB' : 'ru-RU'
  const sorted = [...items].sort((a, b) => b.date.localeCompare(a.date))

  return (
    <div className="card">
      <h2 className="card-title">
        {t('history')}
        <small>{items.length}</small>
      </h2>
      {sorted.length === 0 ? (
        <div className="state">{t('empty_history')}</div>
      ) : (
        <ul className="timeline">
          {sorted.map((it) => (
            <li key={it.record_id} className="tl-item">
              <span className={`tl-dot ${it.status}`} />
              <div style={{ minWidth: 0 }}>
                <div className="tl-title">{eventTitle(it.event_id)}</div>
                <div className="tl-date">
                  {new Date(it.date).toLocaleDateString(locale, { day: 'numeric', month: 'short', year: 'numeric' })}
                  {it.score != null ? ` · ${it.score}/100` : ''}
                </div>
              </div>
              <div className="tl-right">
                <span className={`chip ${statusChip[it.status] ?? ''}`}>{t(`status_${it.status}` as TKey) ?? it.status}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
