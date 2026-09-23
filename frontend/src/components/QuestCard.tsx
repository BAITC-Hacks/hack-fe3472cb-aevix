import type { Recommendation } from '../api'
import { eventInfo } from '../catalog'
import { useI18n, type TKey } from '../i18n'
import { Icon } from './Icon'

interface Props {
  index: number
  quest: Recommendation
  busy: boolean
  onComplete: () => void
}

const fmtDate = (d: string, lang: string) =>
  new Date(d).toLocaleDateString(lang === 'kk' ? 'kk-KZ' : lang === 'en' ? 'en-GB' : 'ru-RU', { day: 'numeric', month: 'short' })

export function QuestCard({ index, quest, busy, onComplete }: Props) {
  const { t, lang } = useI18n()
  const info = eventInfo(quest.event_id)
  const nextSession = info?.upcoming_sessions?.[0]

  return (
    <article className={`quest ${quest.priority}`}>
      <div className="quest-head">
        <div className="quest-num">{index + 1}</div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <h3>{quest.quest_title}</h3>
          {info?.description && <div className="quest-desc">{info.description}</div>}
        </div>
        <div className="match">
          <div className="match-val">{Math.round(quest.score * 100)}%</div>
          <div className="match-cap">match</div>
        </div>
      </div>

      <div className="meta">
        <span className={`chip ${quest.priority === 'high' ? 'danger' : quest.priority === 'medium' ? 'accent' : 'primary'}`}>
          {t(`priority_${quest.priority}` as TKey)}
        </span>
        <span className="chip">{quest.quest_type}</span>
        <span className="chip">{quest.format}</span>
        <span className="chip">
          <Icon name="clock" size={13} /> {quest.duration_hours} {t('hours')}
        </span>
      </div>

      <div className="gains">
        {quest.affected_skills.map((s) => (
          <div key={s.skill_id} className="gain-row">
            <div className="gain-name">{s.skill_name}</div>
            <div className="gain-val">
              {s.current_level} → <b>{s.expected_after}</b> / {s.required_level}
            </div>
            <div className="pips" aria-hidden="true">
              {[1, 2, 3, 4, 5].map((lvl) => (
                <div
                  key={lvl}
                  className={`pip ${lvl <= s.current_level ? 'have' : lvl <= s.expected_after ? 'gain' : ''} ${
                    lvl <= s.required_level ? 'need' : ''
                  }`}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="why">
        <div className="why-title">
          <Icon name="spark" size={14} /> {t('why')}
        </div>
        {quest.reason}
      </div>

      <div className="quest-foot">
        {nextSession ? (
          <span className="session">
            <Icon name="calendar" size={13} /> {fmtDate(nextSession, lang)}
          </span>
        ) : (
          <span className="session">self-paced</span>
        )}
        <button className="btn btn-foot" disabled={busy} onClick={onComplete}>
          <Icon name="check" size={16} /> {t('mark_done')}
        </button>
      </div>
    </article>
  )
}
