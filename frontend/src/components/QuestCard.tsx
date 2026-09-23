import type { Recommendation } from '../api'
import { eventInfo, eventLabel } from '../catalog'
import { useI18n, type TKey } from '../i18n'
import { Icon } from './Icon'
import { useReadOnlyPreview } from '../PreviewContext'

interface Props {
  index: number
  quest: Recommendation
  busy: boolean
  saving: boolean
  selected: boolean
  onSelect: () => void
  onContinue: () => void
}

export function QuestCard({ index, quest, busy, saving, selected, onSelect, onContinue }: Props) {
  const { t, lang } = useI18n()
  const readOnly = useReadOnlyPreview()
  const info = eventInfo(quest.event_id)
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const nextSession = info?.upcoming_sessions?.filter((value) => new Date(value).getTime() >= today.getTime()).sort((a, b) => new Date(a).getTime() - new Date(b).getTime())[0]
  const locale = lang === 'kk' ? 'kk-KZ' : lang === 'en' ? 'en-GB' : 'ru-RU'
  const copy = {
    ru: { relevance: 'Релевантность', details: 'Почему подходит и что даст', skills: 'Навыки после обучения', target: 'цель', selfPaced: 'В своём темпе', completed: 'Уже завершено', similar: 'Похожих занятий завершено', missed: 'Пропуски и отказы учтены', completing: 'Добавляем…', add: 'Добавить в обучение', learning: 'К моему обучению', selected: 'Уже в обучении', schedule: 'Дата уточняется' },
    kk: { relevance: 'Сәйкестік', details: 'Неге ұсынылады және нәтижесі', skills: 'Оқудан кейінгі дағдылар', target: 'мақсат', selfPaced: 'Өз қарқыныңызбен', completed: 'Аяқталған', similar: 'Аяқталған ұқсас сабақтар', missed: 'Қатыспау мен бас тарту ескерілген', completing: 'Қосылуда…', add: 'Оқуыма қосу', learning: 'Оқуыма өту', selected: 'Оқуға қосылған', schedule: 'Күні нақтыланады' },
    en: { relevance: 'Relevance', details: 'Why it fits and what you’ll learn', skills: 'Skills after learning', target: 'target', selfPaced: 'At your own pace', completed: 'Already completed', similar: 'Similar activities completed', missed: 'Missed or declined activities considered', completing: 'Adding…', add: 'Add to my learning', learning: 'Go to my learning', selected: 'In your learning', schedule: 'Date to be confirmed' },
  }[lang]
  const score = Number.isFinite(quest.score) ? Math.round(Math.min(1, Math.max(0, quest.score)) * 100) : 0
  const skill = quest.affected_skills[0]
  const explanation = skill ? ({
    ru: `Обучение поможет развить ${skill.skill_name} с уровня ${skill.current_level} до ${skill.expected_after}. Для вашей цели требуется уровень ${skill.required_level}.`,
    kk: `Оқу ${skill.skill_name} дағдысын ${skill.current_level} деңгейінен ${skill.expected_after} деңгейіне дейін дамытуға көмектеседі. Мақсатыңыз үшін ${skill.required_level} деңгейі қажет.`,
    en: `Build ${skill.skill_name} from level ${skill.current_level} to ${skill.expected_after}. Your target requires level ${skill.required_level}.`,
  }[lang]) : quest.explanation || quest.reason
  const reasons = [...new Set(quest.why_recommended ?? [])]
  const history = quest.history_signal
  const sessionDate = nextSession ? new Date(nextSession) : null
  const validSession = sessionDate && Number.isFinite(sessionDate.getTime()) ? sessionDate : null

  return (
    <article className={`quest ${quest.priority}`}>
      <div className="quest-head">
        <div className="quest-num" aria-hidden="true">{String(index + 1).padStart(2, '0')}</div>
        <div className="quest-summary-copy">
          <h3>{quest.quest_title}</h3>
        </div>
        <div className="match" title={copy.relevance}>
          <span className="match-val">{score}%</span>
          <span className="match-cap">{copy.relevance}</span>
        </div>
      </div>

      <div className="meta">
        {selected && <span className="chip ok"><Icon name="check" size={13} />{copy.selected}</span>}
        <span className={`chip ${quest.priority === 'high' ? 'danger' : quest.priority === 'medium' ? 'accent' : 'primary'}`}>
          {t(`priority_${quest.priority}` as TKey)}
        </span>
        <span className="chip">{eventLabel(quest.quest_type, lang)}</span>
        <span className="chip">{eventLabel(quest.format, lang)}</span>
        <span className="chip">
          <Icon name="clock" size={13} /> {quest.duration_hours} {t('hours')}
        </span>
      </div>

      <div className="quest-skills">
        {quest.affected_skills.slice(0, 3).map((skill) => (
          <span key={skill.skill_id}>{skill.skill_name}</span>
        ))}
        {quest.affected_skills.length > 3 && <span>+{quest.affected_skills.length - 3}</span>}
      </div>

      {explanation && <p className="quest-benefit"><Icon name="spark" size={16} /><span>{explanation}</span></p>}

      <details className="quest-details">
        <summary>
          <Icon name="spark" size={15} />
          <span>{copy.details}</span>
          <Icon name="chevron" size={16} />
        </summary>
        <div className="details-body">
          {info?.description && <p className="quest-desc">{info.description}</p>}
          {reasons.length > 0 && (
            <ul className="recommendation-reasons">
              {reasons.map((reason) => <li key={reason}>{reason}</li>)}
            </ul>
          )}
          {quest.affected_skills.length > 0 && (
            <div className="gains">
              <h4>{copy.skills}</h4>
              {quest.affected_skills.map((skill) => (
                <div key={skill.skill_id} className="gain-row">
                  <div className="gain-name">
                    {skill.skill_name}
                    {skill.is_critical && <span className="critical-label">{t('critical')}</span>}
                  </div>
                  <div className="gain-val">
                    {skill.current_level} → <b>{skill.expected_after}</b>
                    <span> · {copy.target} {skill.required_level}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
          {history && (history.completed_similar > 0 || history.missed_or_declined_similar > 0) && (
            <div className="history-signal">
              {history.completed_similar > 0 && <span>{copy.similar}: {history.completed_similar}</span>}
              {history.missed_or_declined_similar > 0 && <span>{copy.missed}: {history.missed_or_declined_similar}</span>}
            </div>
          )}
        </div>
      </details>

      <div className="quest-foot">
        {validSession ? (
          <span className="session">
            <Icon name="calendar" size={14} />
            <time dateTime={nextSession}>{validSession.toLocaleDateString(locale, { day: 'numeric', month: 'short' })}</time>
          </span>
        ) : (
          <span className="session"><Icon name="clock" size={14} /> {quest.format === 'self_paced' ? copy.selfPaced : copy.schedule}</span>
        )}
        <button type="button" className="btn btn-foot" disabled={busy || (readOnly && !selected)} onClick={selected ? onContinue : onSelect} aria-busy={saving}>
          <Icon name={selected ? 'arrow' : 'book'} size={16} /> {saving ? copy.completing : selected ? copy.learning : copy.add}
        </button>
      </div>
    </article>
  )
}
