import { useEffect, useRef, useState } from 'react'
import { api, type RecommendationsResponse } from '../api'
import { useI18n } from '../i18n'
import { Icon } from './Icon'
import './assistant.css'

export function CareerAssistant({ recs }: { recs: RecommendationsResponse }) {
  const { lang } = useI18n()
  const copy = {
    ru: { title: 'Ваш план развития', note: 'Навыки, карьерная цель и опыт — основа вашей подборки.', explain: 'Объяснить мой план', loading: 'Помощник готовит пояснение…', generated: 'Пояснение AI-помощника', baseline: 'По данным вашего профиля', fallback: 'AI-пояснение сейчас недоступно. Подборка и ожидаемый рост навыков по-прежнему доступны в карточках ниже.', error: 'Не удалось получить пояснение. Попробуйте ещё раз.', outcome: 'Ожидаемый результат', start: 'Начните с', step: 'Добавьте занятие в обучение. После прохождения отметьте его выполненным — навыки и город обновятся.', retry: 'Повторить', hide: 'Скрыть пояснение', show: 'Показать пояснение' },
    kk: { title: 'Сіздің даму жоспарыңыз', note: 'Ұсыныстар дағдыларыңызға, мансаптық мақсатыңызға және тәжірибеңізге негізделген.', explain: 'Жоспарымды түсіндіру', loading: 'Көмекші түсіндірме дайындауда…', generated: 'AI көмекшісінің түсіндірмесі', baseline: 'Профиль деректеріңіз бойынша', fallback: 'AI түсіндірмесі қазір қолжетімсіз. Ұсыныстар мен дағдылардың күтілетін дамуы төмендегі карточкаларда бар.', error: 'Түсіндірме алынбады. Қайта көріңіз.', outcome: 'Күтілетін нәтиже', start: 'Осыдан бастаңыз', step: 'Сабақты оқуыңызға қосыңыз. Оқып болған соң аяқталды деп белгілеңіз — дағдылар мен қала жаңарады.', retry: 'Қайталау', hide: 'Түсіндірмені жасыру', show: 'Түсіндірмені көрсету' },
    en: { title: 'Your development plan', note: 'Built around your skills, career goal and learning history.', explain: 'Explain my plan', loading: 'Your assistant is preparing an explanation…', generated: 'AI assistant explanation', baseline: 'Based on your profile', fallback: 'The AI explanation is unavailable right now. Your recommendations and expected skill gains are still available in the cards below.', error: 'Could not load the explanation. Please try again.', outcome: 'Expected outcome', start: 'Start with', step: 'Add an activity to your learning. Mark it complete once finished to update your skills and city.', retry: 'Try again', hide: 'Hide explanation', show: 'Show explanation' },
  }[lang]
  const [result, setResult] = useState<RecommendationsResponse | null>(null)
  const [expanded, setExpanded] = useState(true)
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(false)
  const requestRef = useRef<AbortController | null>(null)

  useEffect(() => {
    requestRef.current?.abort()
    setResult(null)
    setLoading(false)
    setFailed(false)
    return () => requestRef.current?.abort()
  }, [recs, lang])

  async function explain() {
    requestRef.current?.abort()
    const controller = new AbortController()
    requestRef.current = controller
    setLoading(true)
    setExpanded(true)
    setFailed(false)
    try {
      const response = await api.recommendations(recs.employee_id, true, lang, controller.signal)
      if (!controller.signal.aborted) setResult(response)
    } catch {
      if (!controller.signal.aborted) setFailed(true)
    } finally {
      if (!controller.signal.aborted) setLoading(false)
    }
  }

  const first = recs.recommendations[0]
  if (!first) return null
  const generated = result?.explanation_provider === 'openai'
  return <section className="assistant-panel" aria-labelledby="assistant-heading">
    <div className="assistant-heading">
      <span className="assistant-icon"><Icon name="spark" size={24} /></span>
      <div><span className="eyebrow">CAREER ASSISTANT</span><h2 id="assistant-heading">{copy.title}</h2></div>
      <span className="chip primary">{recs.target_grade} · {recs.target_role}</span>
    </div>
    <p className="assistant-note">{copy.note}</p>
    <div className="assistant-next"><Icon name="route" size={20} /><div><small>{copy.start}</small><strong>{first.quest_title}</strong><p>{copy.step}</p></div></div>
    <div className="assistant-action">
      <button className="btn ghost" onClick={() => result ? setExpanded(!expanded) : void explain()} disabled={loading} aria-busy={loading} aria-expanded={result ? expanded : undefined} aria-controls={result ? 'assistant-response' : undefined}><Icon name="spark" size={16} />{loading ? copy.loading : result ? expanded ? copy.hide : copy.show : failed ? copy.retry : copy.explain}</button>
      <span className="assistant-source">{generated ? copy.generated : copy.baseline}</span>
    </div>
    {failed && <p className="assistant-error" role="alert">{copy.error}</p>}
    {result && <div id="assistant-response" className="assistant-response" aria-live="polite" hidden={!expanded}>
      {generated ? <><p>{result.explanation_summary}</p><ol>{recs.recommendations.map((quest) => {
        const explanation = result.recommendations.find((item) => item.event_id === quest.event_id)
        return explanation ? <li key={quest.event_id}><strong>{quest.quest_title}</strong><p>{explanation.employee_friendly_reason}</p>{explanation.expected_outcome && <p><b>{copy.outcome}: </b>{explanation.expected_outcome}</p>}</li> : null
      })}</ol></> : <p>{copy.fallback}</p>}
    </div>}
  </section>
}
