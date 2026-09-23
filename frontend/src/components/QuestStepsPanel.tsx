import { useEffect, useId, useRef, useState } from 'react'
import { api, ApiError, type QuestPlan, type TrajectoryItem } from '../api'
import { eventInfo, eventLabel, eventTitle } from '../catalog'
import { useI18n } from '../i18n'
import { Icon } from './Icon'
import './questSteps.css'

const copy = {
  ru: {
    open: 'Открыть шаги', close: 'Свернуть', task: 'Что предстоит сделать', plan: 'План выполнения', loading: 'Готовим план обучения…',
    saved: 'Шаг сохранён.', mark: 'Шаг выполнен', done: 'Выполнено', saving: 'Сохраняем…', refresh: 'Обновить шаги', retry: 'Повторить',
    loadError: 'Не удалось загрузить план. Попробуйте ещё раз.', saveError: 'Не удалось сохранить шаг. Обновите план и повторите попытку.',
    conflict: 'Состояние задания изменилось. Обновите шаги перед продолжением.', missing: 'Задание не найдено. Обновите страницу обучения.',
    ready: 'Все шаги выполнены. Подтвердите завершение, чтобы обновить навыки и получить награду за добровольное обучение.',
    pending: 'Выполните и отметьте каждый шаг. Затем станет доступно завершение квеста.', finish: 'Завершить квест',
    team: 'Командный квест', teamReady: 'Ваши шаги готовы. Когда все участники закончат, завершите общий квест в команде.', teamPending: 'Отмечайте свой прогресс. Общий квест завершается в пространстве команды.', openTeam: 'Открыть команду',
    completed: 'шагов выполнено', overdue: 'Просрочено', fallbackDescription: 'Изучите материалы занятия, выполните практическую часть и зафиксируйте результат по шагам ниже.',
    explicit: 'Отметки сохраняются автоматически. Завершение квеста подтверждается отдельно.',
  },
  kk: {
    open: 'Қадамдарды ашу', close: 'Жинау', task: 'Не істеу керек', plan: 'Орындау жоспары', loading: 'Оқу жоспары дайындалуда…',
    saved: 'Қадам сақталды.', mark: 'Қадам орындалды', done: 'Орындалды', saving: 'Сақталуда…', refresh: 'Қадамдарды жаңарту', retry: 'Қайталау',
    loadError: 'Жоспар жүктелмеді. Қайта көріңіз.', saveError: 'Қадам сақталмады. Жоспарды жаңартып, қайталаңыз.',
    conflict: 'Тапсырма күйі өзгерді. Жалғастырмас бұрын қадамдарды жаңартыңыз.', missing: 'Тапсырма табылмады. Оқу бетін жаңартыңыз.',
    ready: 'Барлық қадам орындалды. Дағдыларды жаңарту және ерікті оқу үшін марапат алу үшін квестті аяқтауды растаңыз.',
    pending: 'Әр қадамды орындап, белгілеңіз. Содан кейін квестті аяқтауға болады.', finish: 'Квестті аяқтау',
    team: 'Командалық квест', teamReady: 'Сіздің қадамдарыңыз дайын. Барлық қатысушы бітіргенде, ортақ квестті командада аяқтаңыз.', teamPending: 'Жеке ілгерілеуіңізді белгілеңіз. Ортақ квест команда кеңістігінде аяқталады.', openTeam: 'Команданы ашу',
    completed: 'қадам орындалды', overdue: 'Мерзімі өткен', fallbackDescription: 'Сабақ материалдарын оқып, практикалық бөлігін орындаңыз және төмендегі қадамдармен нәтижені тіркеңіз.',
    explicit: 'Белгілер автоматты түрде сақталады. Квестті аяқтау бөлек расталады.',
  },
  en: {
    open: 'Open steps', close: 'Collapse', task: 'What you will do', plan: 'Learning plan', loading: 'Preparing your learning plan…',
    saved: 'Step saved.', mark: 'Mark step complete', done: 'Completed', saving: 'Saving…', refresh: 'Refresh steps', retry: 'Retry',
    loadError: 'Could not load the plan. Please try again.', saveError: 'Could not save the step. Refresh the plan and try again.',
    conflict: 'The activity status has changed. Refresh the steps before continuing.', missing: 'Activity not found. Refresh your learning page.',
    ready: 'All steps are done. Confirm completion to update your skills and receive a reward for voluntary learning.',
    pending: 'Complete and mark each step. You can then finish the quest.', finish: 'Complete quest',
    team: 'Team quest', teamReady: 'Your steps are ready. Once every member finishes, complete the shared quest in your team space.', teamPending: 'Record your own progress. The shared quest is completed in your team space.', openTeam: 'Open team',
    completed: 'steps completed', overdue: 'Overdue', fallbackDescription: 'Review the activity materials, complete the practical work and record your result using the steps below.',
    explicit: 'Step marks save automatically. Quest completion is confirmed separately.',
  },
}

type Props = {
  employeeId: string
  item: TrajectoryItem
  teamMode: boolean
  busy: boolean
  saving: boolean
  onRefresh: () => void | Promise<void>
  onComplete: () => void | Promise<void>
  onOpenTeam: () => void
}
type ErrorKey = 'loadError' | 'saveError' | 'conflict' | 'missing'

export function QuestStepsPanel(props: Props) {
  return <QuestStepsContent key={`${props.employeeId}:${props.item.event_id}`} {...props} />
}

function QuestStepsContent({ employeeId, item, teamMode, busy, saving, onRefresh, onComplete, onOpenTeam }: Props) {
  const { lang, t } = useI18n()
  const c = copy[lang]
  const id = useId()
  const [open, setOpen] = useState(false)
  const [plan, setPlan] = useState<QuestPlan | null>(null)
  const [loading, setLoading] = useState(false)
  const [stepBusy, setStepBusy] = useState<number | 'finish' | null>(null)
  const [error, setError] = useState<ErrorKey | null>(null)
  const [saved, setSaved] = useState(false)
  const mounted = useRef(false)
  const lock = useRef(false)
  const controller = useRef<AbortController | null>(null)
  const generation = useRef(0)
  const info = eventInfo(item.event_id)
  const done = plan?.steps.filter((step) => step.done).length ?? item.completed_steps ?? 0
  const total = plan?.steps.length ?? item.total_steps ?? 0
  const allDone = !!plan && total > 0 && done === total
  const progress = plan && total ? Math.round(done / total * 100) : Math.round(Math.max(0, Math.min(100, item.completion_pct ?? 0)))
  const disabled = busy || loading || stepBusy !== null

  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false; generation.current += 1; controller.current?.abort() }
  }, [])

  async function load() {
    if (lock.current || busy) return
    const current = ++generation.current
    controller.current?.abort()
    const request = new AbortController()
    controller.current = request
    setLoading(true)
    setError(null)
    setSaved(false)
    try {
      const result = await api.questSteps(employeeId, item.event_id, lang, request.signal)
      if (mounted.current && current === generation.current) setPlan(result)
    } catch (failure) {
      if (mounted.current && current === generation.current && !request.signal.aborted) setError(failure instanceof ApiError && failure.status === 404 ? 'missing' : 'loadError')
    } finally {
      if (mounted.current && current === generation.current) setLoading(false)
    }
  }

  async function completeStep(step: number) {
    if (lock.current || disabled || !plan) return
    lock.current = true
    setStepBusy(step)
    setError(null)
    setSaved(false)
    try {
      const result = await api.completeQuestStep(employeeId, item.event_id, step)
      if (!mounted.current) return
      setPlan((previous) => previous ? {
        ...previous, steps: previous.steps.map((item) => item.step === result.step_number ? { ...item, done: true } : item),
        completed_steps: result.completed_steps, total_steps: result.total_steps,
        completion_pct: result.completion_pct, can_complete: result.can_complete,
      } : previous)
      setSaved(true)
      await onRefresh()
    } catch (failure) {
      if (mounted.current) setError(failure instanceof ApiError && failure.status === 409 ? 'conflict' : failure instanceof ApiError && failure.status === 404 ? 'missing' : 'saveError')
    } finally {
      lock.current = false
      if (mounted.current) setStepBusy(null)
    }
  }

  async function finish() {
    if (lock.current || disabled || !allDone) return
    if (teamMode) { onOpenTeam(); return }
    lock.current = true
    setStepBusy('finish')
    setError(null)
    try { await onComplete() } catch { if (mounted.current) setError('conflict') }
    finally { lock.current = false; if (mounted.current) setStepBusy(null) }
  }

  return <article className="quest-step-panel">
    <button type="button" className="quest-step-toggle" aria-expanded={open} aria-controls={`${id}-body`} onClick={() => { setOpen(!open); if (!open && !plan && !loading) void load() }}>
      <span className="quest-step-summary"><h3>{plan?.title || item.title || eventTitle(item.event_id)}</h3><span className="quest-step-summary-meta">{teamMode && <span className="chip primary">{c.team}</span>}{item.status === 'overdue' && <span className="chip danger">{c.overdue}</span>}<span>{total ? `${done} / ${total} ${c.completed}` : `${progress}%`}</span>{info?.duration_hours != null && <span>{info.duration_hours} {t('hours')}</span>}</span><progress max={100} value={progress} aria-label={`${eventTitle(item.event_id)}: ${progress}%`} /></span>
      <span className="quest-step-open">{open ? c.close : c.open}<Icon name="chevron" size={16} /></span>
    </button>
    {open && <div className="quest-step-body" id={`${id}-body`}>
      {loading && <p className="quest-step-loading" role="status">{c.loading}</p>}
      {error && <div className="quest-step-task"><p className="quest-step-feedback" role="alert">{c[error]}</p><button className="btn ghost quest-step-action" disabled={disabled} onClick={() => void load()}>{c.retry}</button></div>}
      {saved && !error && <p className="quest-step-feedback success" role="status">{c.saved}</p>}
      {plan && <>
        <div className="quest-step-task"><h4>{c.task}</h4><p className="quest-step-description">{plan.task.description || info?.description || c.fallbackDescription}</p><div className="meta">{plan.task.type && <span className="chip">{eventLabel(plan.task.type, lang)}</span>}{plan.task.format && <span className="chip">{eventLabel(plan.task.format, lang)}</span>}{plan.task.duration_hours != null && <span className="chip"><Icon name="clock" size={13} />{plan.task.duration_hours} {t('hours')}</span>}</div></div>
        <div className="quest-step-tools"><h4>{c.plan}</h4><button className="text-button" disabled={disabled} onClick={() => void load()}>{c.refresh}</button></div>
        <ol className="quest-step-list">{plan.steps.map((step) => <li className={`quest-step-item${step.done ? ' is-done' : ''}`} key={step.step}><span className="quest-step-number" aria-hidden="true">{step.done ? <Icon name="check" size={15} /> : step.step}</span><div className="quest-step-content"><h4>{step.title}</h4><p>{step.description}</p>{step.done ? <span className="quest-step-done"><Icon name="check" size={13} />{c.done}</span> : <button className="btn ghost quest-step-action" disabled={disabled} aria-busy={stepBusy === step.step} onClick={() => void completeStep(step.step)}>{stepBusy === step.step ? c.saving : c.mark}<Icon name="check" size={14} /></button>}</div></li>)}</ol>
        <p className="quest-step-note">{c.explicit}</p>
        <div className="quest-step-footer"><p className="quest-step-note">{teamMode ? allDone ? c.teamReady : c.teamPending : allDone ? c.ready : c.pending}</p><button className="btn" disabled={disabled || !allDone} aria-busy={saving || stepBusy === 'finish'} onClick={() => void finish()}>{saving || stepBusy === 'finish' ? c.saving : teamMode ? c.openTeam : c.finish}<Icon name={teamMode ? 'people' : 'check'} size={15} /></button></div>
      </>}
    </div>}
  </article>
}
