import { useCallback, useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { api, ApiError, type EmployeeListItem, type Recommendation } from '../api'
import { collaborationApi as service, type LearningPair, type LearningTeam, type PairFormat, type PairInvitation, type PairPreview } from '../collaborationApi'
import { eventTitle } from '../catalog'
import { Icon } from '../components/Icon'
import { useI18n } from '../i18n'
import '../components/collaboration.css'

const copy = {
  ru: {
    intro: 'Общие цели. Общий прогресс.', subtitle: 'Соберите команду для квестов или найдите партнёра для обучения.',
    teams: 'Команды', partners: 'Партнёры', refresh: 'Обновить', loading: 'Загружаем пространство…', working: 'Сохраняем…',
    createTeam: 'Создать команду', teamName: 'Название команды', capacity: 'Мест в команде', create: 'Создать', joinTitle: 'Есть код команды?', joinHint: 'Вступите по коду от коллеги. Если вы уже участник, команда откроется снова.', teamCode: 'Код команды', join: 'Вступить / открыть',
    noTeams: 'Вместе к следующей цели', noTeamsHint: 'Создайте команду или присоединитесь к коллегам по коду. Здесь появятся ваши общие квесты.',
    members: 'Участники', you: 'вы', completed: 'Квестов завершено', active: 'Готова к квесту', inProgress: 'Квест выполняется', paused: 'На паузе', waiting: 'Нужен новый участник',
    pause: 'Пауза', resume: 'Продолжить', current: 'Общий квест', chooseQuest: 'Следующий общий квест', start: 'Начать вместе', finish: 'Завершить для команды', completeNote: 'Завершение обновит навыки и награды всех участников.',
    waitingHint: 'После трёх квестов пригласите ещё одного коллегу, чтобы продолжить.', teamQuestHint: 'Перед стартом проверим требования к квесту для каждого участника.', noQuests: 'Сейчас нет подходящих рекомендаций. Обновите свою карьерную цель или вернитесь позже.',
    codeHint: 'Передайте этот код коллегам.', copy: 'Копировать', copied: 'Код скопирован.', copyFailed: 'Не удалось скопировать автоматически. Выделите код и скопируйте его.',
    teamCreated: 'Команда создана. Пригласите коллег по коду.', joined: 'Команда открыта.', updated: 'Состояние команды обновлено.', started: 'Общий квест начат.', finished: 'Квест завершён. Прогресс команды обновлён.',
    invitationTitle: 'Пригласить партнёра', invitationHint: 'Выберите обучение из своих рекомендаций и удобный формат.', activity: 'Обучение', format: 'Формат встречи', online: 'Вместе онлайн', inPerson: 'Личная встреча', discussion: 'Самостоятельно + обсуждение',
    display: 'Как вас увидят коллеги', name: 'Моё имя', alias: 'Псевдоним', aliasName: 'Ваш псевдоним', dates: 'Даты (необязательно)', from: 'Начало', to: 'Окончание', publish: 'Опубликовать приглашение', published: 'Приглашение опубликовано и доступно коллегам.',
    invitations: 'Приглашения коллег', noInvitations: 'Пока нет открытых приглашений', noInvitationsHint: 'Создайте первое приглашение. Коллеги увидят его и смогут проверить, подходит ли им обучение.', ownInvitations: 'Ваши открытые приглашения', waitingPartner: 'Ждём отклика коллеги',
    preview: 'Проверить совместимость', suitable: 'Подходит вашему развитию', unsuitable: 'Сейчас не подходит', suitableHint: 'Обучение помогает закрыть пробелы относительно вашей карьерной цели.', unsuitableHint: 'Обучение не соответствует текущим рекомендациям или уже пройдено.', closedHint: 'Приглашение уже недоступно. Обновите список.', details: 'Подробности рекомендации', accept: 'Учиться вместе', decline: 'Отклонить', declineWarning: 'Это закроет приглашение для всех коллег.', confirmDecline: 'Закрыть приглашение', cancel: 'Отмена', declined: 'Приглашение закрыто.', accepted: 'Пара создана. Поделитесь её кодом с партнёром.',
    pairs: 'Ваши пары', pairCode: 'Код пары', openPair: 'Открыть пару', restorePair: 'Открыть по коду', restoreHint: 'Если коллега принял ваше приглашение, попросите у него код пары. Сохранённые пары откроются в этом браузере автоматически.', pairReady: 'Пара создана', pairHint: 'Договоритесь с коллегой о первой встрече. Добавьте обучение в свой план, чтобы отслеживать личный прогресс.', addLearning: 'Добавить в моё обучение', added: 'Добавлено в план обучения.', addedLabel: 'В моём плане', learning: 'Открыть моё обучение', pairOpened: 'Пространство пары открыто.',
    loadError: 'Часть данных не загрузилась. Нажмите «Обновить», чтобы повторить.', error: 'Не удалось выполнить действие. Попробуйте ещё раз.', notFound: 'Команда, пара или приглашение не найдены. Проверьте код и обновите страницу.', invalid: 'Проверьте заполненные поля и выбранные даты.', conflict: 'Состояние уже изменилось. Обновите данные перед повторной попыткой.', full: 'В команде нет свободных мест.', prerequisites: 'Один из участников ещё не соответствует требованиям к этому квесту.', alreadyCompleted: 'Этот квест уже завершён одним из участников. Выберите другой.', notMember: 'Этот код относится к паре другого сотрудника.',
  },
  kk: {
    intro: 'Ортақ мақсат. Ортақ даму.', subtitle: 'Квесттер үшін команда құрыңыз немесе бірге оқитын серіктес табыңыз.',
    teams: 'Командалар', partners: 'Серіктестер', refresh: 'Жаңарту', loading: 'Кеңістік жүктелуде…', working: 'Сақталуда…',
    createTeam: 'Команда құру', teamName: 'Команда атауы', capacity: 'Командадағы орындар', create: 'Құру', joinTitle: 'Команда коды бар ма?', joinHint: 'Әріптес берген кодпен қосылыңыз. Қатысушы болсаңыз, команда қайта ашылады.', teamCode: 'Команда коды', join: 'Қосылу / ашу',
    noTeams: 'Келесі мақсатқа бірге', noTeamsHint: 'Команда құрыңыз немесе кодпен қосылыңыз. Ортақ квесттеріңіз осында көрсетіледі.',
    members: 'Қатысушылар', you: 'сіз', completed: 'Аяқталған квесттер', active: 'Квестке дайын', inProgress: 'Квест орындалуда', paused: 'Кідіртілген', waiting: 'Жаңа қатысушы қажет',
    pause: 'Кідірту', resume: 'Жалғастыру', current: 'Ортақ квест', chooseQuest: 'Келесі ортақ квест', start: 'Бірге бастау', finish: 'Команда үшін аяқтау', completeNote: 'Аяқтау барлық қатысушылардың дағдылары мен марапаттарын жаңартады.',
    waitingHint: 'Үш квесттен кейін жалғастыру үшін тағы бір әріптесті шақырыңыз.', teamQuestHint: 'Бастамас бұрын әр қатысушының квест талаптарына сәйкестігін тексереміз.', noQuests: 'Әзірге сәйкес ұсыныстар жоқ. Мансап мақсатын жаңартыңыз немесе кейін оралыңыз.',
    codeHint: 'Кодты әріптестерге жіберіңіз.', copy: 'Көшіру', copied: 'Код көшірілді.', copyFailed: 'Автоматты көшіру мүмкін болмады. Кодты белгілеп, көшіріңіз.',
    teamCreated: 'Команда құрылды. Әріптестерді кодпен шақырыңыз.', joined: 'Команда ашылды.', updated: 'Команда күйі жаңартылды.', started: 'Ортақ квест басталды.', finished: 'Квест аяқталды. Команданың ілгерілеуі жаңартылды.',
    invitationTitle: 'Серіктес шақыру', invitationHint: 'Ұсыныстардан оқу мен қолайлы форматты таңдаңыз.', activity: 'Оқу', format: 'Кездесу форматы', online: 'Бірге онлайн', inPerson: 'Жеке кездесу', discussion: 'Өздігінен оқу + талқылау',
    display: 'Әріптестер сізді қалай көреді', name: 'Менің атым', alias: 'Бүркеншік ат', aliasName: 'Бүркеншік атыңыз', dates: 'Күндер (міндетті емес)', from: 'Басталуы', to: 'Аяқталуы', publish: 'Шақыру жариялау', published: 'Шақыру жарияланды және әріптестерге қолжетімді.',
    invitations: 'Әріптестердің шақырулары', noInvitations: 'Әзірге ашық шақырулар жоқ', noInvitationsHint: 'Алғашқы шақыруды жариялаңыз. Әріптестер оқудың өздеріне сәйкестігін тексере алады.', ownInvitations: 'Сіздің ашық шақыруларыңыз', waitingPartner: 'Әріптестің жауабын күтеміз',
    preview: 'Сәйкестікті тексеру', suitable: 'Дамуыңызға сәйкес', unsuitable: 'Қазір сәйкес емес', suitableHint: 'Оқу мансап мақсатыңызға қажетті дағдыларды дамытуға көмектеседі.', unsuitableHint: 'Оқу ағымдағы ұсыныстарға сәйкес емес немесе аяқталған.', closedHint: 'Шақыру енді қолжетімсіз. Тізімді жаңартыңыз.', details: 'Ұсыныс туралы', accept: 'Бірге оқу', decline: 'Бас тарту', declineWarning: 'Бұл шақыруды барлық әріптестер үшін жабады.', confirmDecline: 'Шақыруды жабу', cancel: 'Бас тарту', declined: 'Шақыру жабылды.', accepted: 'Жұп құрылды. Кодты серіктесіңізге беріңіз.',
    pairs: 'Сіздің жұптарыңыз', pairCode: 'Жұп коды', openPair: 'Жұпты ашу', restorePair: 'Кодпен ашу', restoreHint: 'Әріптес шақыруыңызды қабылдаса, одан жұп кодын сұраңыз. Сақталған жұптар осы браузерде автоматты түрде ашылады.', pairReady: 'Жұп құрылды', pairHint: 'Алғашқы кездесуді әріптесіңізбен келісіңіз. Жеке ілгерілеуді бақылау үшін оқуды жоспарыңызға қосыңыз.', addLearning: 'Менің оқуыма қосу', added: 'Оқу жоспарына қосылды.', addedLabel: 'Менің жоспарымда', learning: 'Менің оқуымды ашу', pairOpened: 'Жұп кеңістігі ашылды.',
    loadError: 'Деректердің бір бөлігі жүктелмеді. «Жаңарту» түймесін басыңыз.', error: 'Әрекетті орындау мүмкін болмады. Қайта көріңіз.', notFound: 'Команда, жұп немесе шақыру табылмады. Кодты тексеріп, жаңартыңыз.', invalid: 'Толтырылған өрістер мен күндерді тексеріңіз.', conflict: 'Күй өзгерді. Қайталаудан бұрын деректерді жаңартыңыз.', full: 'Командада бос орын жоқ.', prerequisites: 'Қатысушылардың бірі квест талаптарына әлі сәйкес келмейді.', alreadyCompleted: 'Қатысушылардың бірі бұл квестті аяқтаған. Басқасын таңдаңыз.', notMember: 'Бұл код басқа қызметкердің жұбына тиесілі.',
  },
  en: {
    intro: 'Shared goals. Shared progress.', subtitle: 'Build a quest team or find a partner to learn with.',
    teams: 'Teams', partners: 'Partners', refresh: 'Refresh', loading: 'Loading your space…', working: 'Saving…',
    createTeam: 'Create a team', teamName: 'Team name', capacity: 'Team capacity', create: 'Create', joinTitle: 'Have a team code?', joinHint: 'Join using a code from a colleague. Existing members can reopen their team here.', teamCode: 'Team code', join: 'Join / open',
    noTeams: 'Reach your next goal together', noTeamsHint: 'Create a team or join your colleagues with a code. Your shared quests will appear here.',
    members: 'Members', you: 'you', completed: 'Quests completed', active: 'Ready for a quest', inProgress: 'Quest in progress', paused: 'Paused', waiting: 'Needs a new member',
    pause: 'Pause', resume: 'Resume', current: 'Shared quest', chooseQuest: 'Next shared quest', start: 'Start together', finish: 'Complete for the team', completeNote: 'Completing updates skills and rewards for every member.',
    waitingHint: 'After three quests, invite one more colleague to continue.', teamQuestHint: 'Quest prerequisites are checked for every member before starting.', noQuests: 'No suitable recommendations right now. Update your career goal or come back later.',
    codeHint: 'Share this code with your colleagues.', copy: 'Copy', copied: 'Code copied.', copyFailed: 'Could not copy automatically. Select the code and copy it.',
    teamCreated: 'Team created. Invite colleagues with its code.', joined: 'Team opened.', updated: 'Team status updated.', started: 'Shared quest started.', finished: 'Quest completed. Team progress updated.',
    invitationTitle: 'Invite a learning partner', invitationHint: 'Choose a recommended activity and a format that works for you.', activity: 'Learning activity', format: 'Meeting format', online: 'Online together', inPerson: 'In person', discussion: 'Self-paced + discussion',
    display: 'How colleagues see you', name: 'My name', alias: 'Alias', aliasName: 'Your alias', dates: 'Dates (optional)', from: 'Start', to: 'End', publish: 'Publish invitation', published: 'Your invitation is now visible to colleagues.',
    invitations: 'Invitations from colleagues', noInvitations: 'No open invitations yet', noInvitationsHint: 'Publish the first invitation. Colleagues can check whether the learning fits their goals.', ownInvitations: 'Your open invitations', waitingPartner: 'Waiting for a colleague',
    preview: 'Check compatibility', suitable: 'Supports your development', unsuitable: 'Not a match right now', suitableHint: 'This activity helps close skill gaps toward your career goal.', unsuitableHint: 'This learning does not match your current recommendations or is already completed.', closedHint: 'This invitation is no longer available. Refresh the list.', details: 'Recommendation details', accept: 'Learn together', decline: 'Decline', declineWarning: 'This closes the invitation for all colleagues.', confirmDecline: 'Close invitation', cancel: 'Cancel', declined: 'Invitation closed.', accepted: 'Pair created. Share its code with your partner.',
    pairs: 'Your learning pairs', pairCode: 'Pair code', openPair: 'Open pair', restorePair: 'Open with a code', restoreHint: 'If a colleague accepted your invitation, ask them for the pair code. Saved pairs reopen automatically in this browser.', pairReady: 'Pair created', pairHint: 'Agree on your first session with your colleague. Add the activity to your plan to track your own progress.', addLearning: 'Add to my learning', added: 'Added to your learning plan.', addedLabel: 'In my plan', learning: 'Open my learning', pairOpened: 'Pair space opened.',
    loadError: 'Some data could not be loaded. Select Refresh to try again.', error: 'Could not complete this action. Please try again.', notFound: 'Team, pair or invitation not found. Check the code and refresh.', invalid: 'Check the form fields and selected dates.', conflict: 'The current status has changed. Refresh before trying again.', full: 'This team has no available places.', prerequisites: 'One of the members does not meet this quest’s prerequisites yet.', alreadyCompleted: 'One of the members has already completed this quest. Choose another one.', notMember: 'This code belongs to another employee’s pair.',
  },
}

type CopyKey = keyof typeof copy.en
type Saved = { teams: string[]; pairs: string[] }
type Props = { employeeId: string; onRefresh: () => void }
const storageKey = (employeeId: string) => `cq_collaboration_${employeeId}`
function readSaved(employeeId: string): Saved {
  try {
    const value = JSON.parse(localStorage.getItem(storageKey(employeeId)) ?? '{}')
    return { teams: Array.isArray(value.teams) ? value.teams.filter((id: unknown) => typeof id === 'string') : [], pairs: Array.isArray(value.pairs) ? value.pairs.filter((id: unknown) => typeof id === 'string') : [] }
  } catch { return { teams: [], pairs: [] } }
}

export function CollaborationPage(props: Props) {
  return <CollaborationContent key={props.employeeId} {...props} />
}

function CollaborationContent({ employeeId, onRefresh }: Props) {
  const { lang } = useI18n()
  const c = copy[lang]
  const uid = useId()
  const [tab, setTab] = useState<'teams' | 'partners'>('teams')
  const [teams, setTeams] = useState<LearningTeam[]>([])
  const [pairs, setPairs] = useState<LearningPair[]>([])
  const [invitations, setInvitations] = useState<PairInvitation[]>([])
  const [ownInvitations, setOwnInvitations] = useState<PairInvitation[]>([])
  const [previews, setPreviews] = useState<Record<string, PairPreview>>({})
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [employees, setEmployees] = useState<EmployeeListItem[]>([])
  const [selected, setSelected] = useState<Record<string, string>>({})
  const [planned, setPlanned] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<{ key: CopyKey; error?: boolean } | null>(null)
  const [teamName, setTeamName] = useState('')
  const [capacity, setCapacity] = useState('5')
  const [teamCode, setTeamCode] = useState('')
  const [pairCode, setPairCode] = useState('')
  const [inviteEvent, setInviteEvent] = useState('')
  const [format, setFormat] = useState<PairFormat>('online_together')
  const [displayMode, setDisplayMode] = useState<'name' | 'alias'>('name')
  const [alias, setAlias] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [declining, setDeclining] = useState<string | null>(null)
  const saved = useRef(readSaved(employeeId))
  const mounted = useRef(false)
  const locked = useRef(false)
  const generation = useRef(0)
  const disabled = loading || busy !== null

  function remember(kind: keyof Saved, value: string) {
    saved.current = { ...saved.current, [kind]: Array.from(new Set([...saved.current[kind], value])) }
    try { localStorage.setItem(storageKey(employeeId), JSON.stringify(saved.current)) } catch { /* The visible code still allows restoring the space. */ }
  }

  const refresh = useCallback(async () => {
    if (locked.current) return
    const current = ++generation.current
    setLoading(true)
    const results = await Promise.allSettled([
      api.recommendations(employeeId), api.employees(), service.invitations(employeeId), service.invitations(), api.trajectory(employeeId),
      Promise.allSettled(saved.current.teams.map((id) => service.team(id))),
      Promise.allSettled(saved.current.pairs.map((id) => service.pair(id))),
    ] as const)
    if (!mounted.current || current !== generation.current) return
    const [recs, people, invites, allInvites, trajectory, teamResults, pairResults] = results
    let failed = results.some((result) => result.status === 'rejected')
    if (recs.status === 'fulfilled') setRecommendations(recs.value.recommendations)
    if (people.status === 'fulfilled') setEmployees(people.value)
    if (invites.status === 'fulfilled') setInvitations(invites.value)
    if (invites.status === 'fulfilled' && allInvites.status === 'fulfilled') {
      const otherIds = new Set(invites.value.map((invite) => invite.invitation_id))
      setOwnInvitations(allInvites.value.filter((invite) => !otherIds.has(invite.invitation_id)))
    }
    if (trajectory.status === 'fulfilled') setPlanned(trajectory.value.filter((row) => ['in_progress', 'selected', 'completed'].includes(row.status)).map((row) => row.event_id))
    if (teamResults.status === 'fulfilled') {
      failed ||= teamResults.value.some((result) => result.status === 'rejected')
      setTeams(teamResults.value.flatMap((result) => result.status === 'fulfilled' && result.value.member_ids.includes(employeeId) ? [result.value] : []))
    }
    if (pairResults.status === 'fulfilled') {
      failed ||= pairResults.value.some((result) => result.status === 'rejected')
      setPairs(pairResults.value.flatMap((result) => result.status === 'fulfilled' && result.value.members.includes(employeeId) ? [result.value] : []))
    }
    setPreviews({})
    setLoadError(failed)
    setLoading(false)
  }, [employeeId])

  useEffect(() => {
    mounted.current = true
    void refresh()
    return () => { mounted.current = false; generation.current += 1 }
  }, [refresh])

  useEffect(() => {
    const available = new Set(recommendations.map((item) => item.event_id))
    setSelected((previous) => Object.fromEntries(Object.entries(previous).filter(([, eventId]) => available.has(eventId))))
    setInviteEvent((previous) => available.has(previous) ? previous : '')
  }, [recommendations])

  function errorKey(error: unknown): CopyKey {
    if (!(error instanceof ApiError)) return 'error'
    if (error.message.includes('Team is full')) return 'full'
    if (error.message.includes('prerequisites')) return 'prerequisites'
    if (error.message.toLowerCase().includes('already completed')) return 'alreadyCompleted'
    if (error.message === 'not_member') return 'notMember'
    if (error.status === 404) return 'notFound'
    if (error.status === 422) return 'invalid'
    if (error.status === 409) return 'conflict'
    return 'error'
  }

  async function run<T,>(key: string, operation: () => Promise<T>, success: (result: T) => void | Promise<void>) {
    if (locked.current || loading) return
    locked.current = true
    setBusy(key)
    setFeedback(null)
    try {
      const result = await operation()
      if (mounted.current) await success(result)
    } catch (error) {
      if (mounted.current) setFeedback({ key: errorKey(error), error: true })
    } finally {
      locked.current = false
      if (mounted.current) setBusy(null)
    }
  }

  async function updateTeam(team: LearningTeam, key: CopyKey) {
    const completedEvent = key === 'finished' ? teams.find((item) => item.team_id === team.team_id)?.current_quest?.event_id : null
    setTeams((previous) => [team, ...previous.filter((item) => item.team_id !== team.team_id)])
    remember('teams', team.team_id)
    setFeedback({ key })
    onRefresh()
    if (completedEvent) {
      setRecommendations((previous) => previous.filter((item) => item.event_id !== completedEvent))
      const [recs, trajectory] = await Promise.allSettled([api.recommendations(employeeId), api.trajectory(employeeId)])
      if (!mounted.current) return
      if (recs.status === 'fulfilled') setRecommendations(recs.value.recommendations)
      if (trajectory.status === 'fulfilled') setPlanned(trajectory.value.filter((row) => ['in_progress', 'selected', 'completed'].includes(row.status)).map((row) => row.event_id))
      if (recs.status === 'rejected' || trajectory.status === 'rejected') setLoadError(true)
    }
  }

  function addPair(pair: LearningPair, key: CopyKey) {
    setPairs((previous) => [pair, ...previous.filter((item) => item.pair_id !== pair.pair_id)])
    remember('pairs', pair.pair_id)
    setFeedback({ key })
  }

  const nameFor = (id: string) => employees.find((employee) => employee.employee_id === id)?.full_name ?? id
  const activityTitle = (id: string) => recommendations.find((item) => item.event_id === id)?.quest_title ?? eventTitle(id)
  const formats: Record<PairFormat, string> = { online_together: c.online, in_person: c.inPerson, self_paced_discussion: c.discussion }
  const statuses: Record<string, string> = { active: c.active, in_progress: c.inProgress, paused: c.paused, waiting_for_member: c.waiting }
  const date = (value: string) => new Date(`${value}T12:00:00`).toLocaleDateString(lang, { day: 'numeric', month: 'short' })

  function members(ids: string[]) {
    return <ul className="collab-members" aria-label={c.members}>{ids.map((id) => <li key={id}><span className="collab-avatar">{nameFor(id).split(' ').map((part) => part[0]).slice(0, 2).join('')}</span><span>{nameFor(id)}{id === employeeId ? ` · ${c.you}` : ''}</span></li>)}</ul>
  }

  function code(value: string) {
    return <div><div className="collab-code"><code>{value}</code><button className="text-button" type="button" onClick={() => {
      void navigator.clipboard?.writeText(value).then(() => { if (mounted.current) setFeedback({ key: 'copied' }) }, () => { if (mounted.current) setFeedback({ key: 'copyFailed', error: true }) })
      if (!navigator.clipboard) setFeedback({ key: 'copyFailed', error: true })
    }}>{c.copy}</button></div><p className="collab-muted">{c.codeHint}</p></div>
  }

  function eventOptions() {
    return recommendations.map((item) => <option value={item.event_id} key={item.event_id}>{item.quest_title || item.title || item.event_id}</option>)
  }

  function publish(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const eventId = inviteEvent || recommendations[0]?.event_id
    if (!eventId || (startDate && endDate && endDate < startDate)) { setFeedback({ key: 'invalid', error: true }); return }
    void run('publish', () => service.invite({
      inviter_id: employeeId, event_id: eventId, format, display_mode: displayMode,
      ...(displayMode === 'alias' && alias.trim() ? { display_name: alias.trim() } : {}),
      ...(startDate ? { start_date: startDate } : {}), ...(endDate ? { end_date: endDate } : {}),
    }), (invitation) => { setOwnInvitations((previous) => [invitation, ...previous]); setFeedback({ key: 'published' }) })
  }

  async function respond(invitation: PairInvitation, decision: 'accept' | 'decline') {
    await run(`respond-${invitation.invitation_id}`, async () => {
      const result = await service.respond(invitation.invitation_id, employeeId, decision)
      if (result.status === 'accepted' && result.pair_id) {
        remember('pairs', result.pair_id)
        return { result, pair: await service.pair(result.pair_id) }
      }
      return { result, pair: null }
    }, ({ result, pair }) => {
      if (result.status === 'not_a_match') { setFeedback({ key: 'unsuitableHint', error: true }); return }
      setInvitations((previous) => previous.filter((item) => item.invitation_id !== invitation.invitation_id))
      setDeclining(null)
      if (pair) addPair(pair, 'accepted')
      else setFeedback({ key: 'declined' })
    })
  }

  return <div className="collab-page">
    <div className="collab-heading"><div><span className="collab-kicker"><Icon name="people" size={16} />{c.intro}</span><p>{c.subtitle}</p></div><button className="btn ghost" disabled={disabled} onClick={() => { setFeedback(null); void refresh() }}>{loading ? c.loading : c.refresh}</button></div>
    <div className="collab-tabs" role="tablist" aria-label={c.intro}>{(['teams', 'partners'] as const).map((value) => <button key={value} id={`${uid}-${value}-tab`} role="tab" tabIndex={tab === value ? 0 : -1} aria-selected={tab === value} aria-controls={`${uid}-${value}`} onClick={() => { setTab(value); setFeedback(null) }} onKeyDown={(event) => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
      event.preventDefault()
      const next = event.key === 'Home' ? 'teams' : event.key === 'End' ? 'partners' : value === 'teams' ? 'partners' : 'teams'
      setTab(next)
      setFeedback(null)
      document.getElementById(`${uid}-${next}-tab`)?.focus()
    }}><Icon name={value === 'teams' ? 'people' : 'book'} size={16} />{c[value]}</button>)}</div>
    {feedback && <p className={`collab-notice${feedback.error ? ' error' : ''}`} role={feedback.error ? 'alert' : 'status'}>{c[feedback.key]}</p>}
    {loadError && <p className="collab-notice error" role="alert">{c.loadError}</p>}
    {loading && <p className="collab-muted" role="status">{c.loading}</p>}

    {tab === 'teams' ? <div className="collab-layout" id={`${uid}-teams`} role="tabpanel" aria-labelledby={`${uid}-teams-tab`}>
      <div className="collab-list">
        {!loading && !teams.length && <div className="card collab-empty"><span className="collab-empty-icon"><Icon name="people" size={28} /></span><h2>{c.noTeams}</h2><p className="collab-muted">{c.noTeamsHint}</p></div>}
        {teams.map((team) => <article className="card" key={team.team_id}>
          <div className="collab-card-head"><h2>{team.name}</h2><span className={`chip ${team.status === 'in_progress' ? 'primary' : ''}`}>{statuses[team.status] ?? team.status}</span></div>
          {code(team.team_id)}
          <div className="collab-card-head"><span className="collab-muted">{c.members} · {team.member_ids.length}/{team.max_members}</span><span className="collab-muted">{c.completed} · {team.completed_team_quests}</span></div>
          {members(team.member_ids)}
          {team.current_quest && <div className="collab-quest"><small>{c.current}</small><h3>{activityTitle(team.current_quest.event_id)}</h3><p className="collab-muted">{c.completeNote}</p><button className="btn" disabled={disabled || team.status !== 'in_progress'} onClick={() => void run(`complete-${team.team_id}`, () => service.completeTeamQuest(team.team_id, team.current_quest!.event_id), (result) => updateTeam(result, 'finished'))}>{busy === `complete-${team.team_id}` ? c.working : c.finish}<Icon name="check" size={16} /></button></div>}
          {team.status === 'active' && !team.current_quest && <form className="collab-form collab-divider" onSubmit={(event) => { event.preventDefault(); const eventId = selected[team.team_id] || recommendations[0]?.event_id; if (eventId) void run(`start-${team.team_id}`, () => service.startTeamQuest(team.team_id, eventId), (result) => updateTeam(result, 'started')) }}>
            <label className="collab-field">{c.chooseQuest}<select required value={selected[team.team_id] || recommendations[0]?.event_id || ''} disabled={disabled || !recommendations.length} onChange={(event) => setSelected((previous) => ({ ...previous, [team.team_id]: event.target.value }))}>{!recommendations.length && <option value="">—</option>}{eventOptions()}</select></label>
            <p className="collab-muted">{recommendations.length ? c.teamQuestHint : c.noQuests}</p><button className="btn" disabled={disabled || !recommendations.length}>{busy === `start-${team.team_id}` ? c.working : c.start}<Icon name="play" size={14} /></button>
          </form>}
          {team.status === 'waiting_for_member' && <p className="collab-muted">{c.waitingHint}</p>}
          {['active', 'in_progress', 'paused'].includes(team.status) && <div className="collab-actions"><button className="btn ghost" disabled={disabled} onClick={() => void run(`status-${team.team_id}`, () => service.teamStatus(team.team_id, team.status === 'paused' ? 'resume' : 'pause'), (result) => updateTeam(result, 'updated'))}>{busy === `status-${team.team_id}` ? c.working : team.status === 'paused' ? c.resume : c.pause}</button></div>}
        </article>)}
      </div>
      <aside className="collab-sidebar">
        <section className="card"><h2>{c.createTeam}</h2><form className="collab-form" onSubmit={(event) => { event.preventDefault(); void run('create', () => service.createTeam(employeeId, teamName.trim(), Number(capacity)), (result) => { updateTeam(result, 'teamCreated'); setTeamName('') }) }}>
          <label className="collab-field">{c.teamName}<input value={teamName} maxLength={200} required disabled={disabled} onChange={(event) => setTeamName(event.target.value)} /></label>
          <label className="collab-field">{c.capacity}<input type="number" min="1" step="1" max="100" required value={capacity} disabled={disabled} onChange={(event) => setCapacity(event.target.value)} /></label>
          <button className="btn" disabled={disabled || !teamName.trim()}>{busy === 'create' ? c.working : c.create}<Icon name="arrow" size={15} /></button>
        </form></section>
        <section className="card"><h2>{c.joinTitle}</h2><p className="collab-muted">{c.joinHint}</p><form className="collab-form" onSubmit={(event) => { event.preventDefault(); void run('join', () => service.joinTeam(teamCode.trim(), employeeId), (result) => { updateTeam(result, 'joined'); setTeamCode('') }) }}><label className="collab-field">{c.teamCode}<input placeholder="TEAM_…" value={teamCode} required disabled={disabled} onChange={(event) => setTeamCode(event.target.value)} /></label><button className="btn ghost" disabled={disabled || !teamCode.trim()}>{busy === 'join' ? c.working : c.join}</button></form></section>
      </aside>
    </div> : <div className="collab-layout" id={`${uid}-partners`} role="tabpanel" aria-labelledby={`${uid}-partners-tab`}>
      <div className="collab-list">
        {pairs.length > 0 && <h2>{c.pairs}</h2>}
        {pairs.map((pair) => <article className="card" key={pair.pair_id}><div className="collab-card-head"><h2>{pair.activity_title}</h2><span className="chip ok">{c.pairReady}</span></div>{members(pair.members)}{code(pair.pair_id)}<p className="collab-muted">{c.pairHint}</p><div className="collab-actions"><button className="btn" disabled={disabled || planned.includes(pair.event_id)} onClick={() => void run(`plan-${pair.pair_id}`, () => api.selectQuest(employeeId, pair.event_id), () => { setPlanned((previous) => [...previous, pair.event_id]); setFeedback({ key: 'added' }); onRefresh() })}>{planned.includes(pair.event_id) ? c.addedLabel : busy === `plan-${pair.pair_id}` ? c.working : c.addLearning}<Icon name="check" size={15} /></button><a className="text-button" href="#/learning">{c.learning}<Icon name="arrow" size={14} /></a></div></article>)}
        <h2>{c.invitations}</h2>
        {!loading && !invitations.length && <div className="card collab-empty"><span className="collab-empty-icon"><Icon name="book" size={26} /></span><h3>{c.noInvitations}</h3><p className="collab-muted">{c.noInvitationsHint}</p></div>}
        {invitations.map((invitation) => {
          const preview = previews[invitation.invitation_id]
          return <article className="card" key={invitation.invitation_id}><div className="collab-card-head"><h3>{invitation.activity_title}</h3><span className="chip">{invitation.display_name}</span></div><div className="collab-invitation-meta"><span><Icon name="people" size={14} />{formats[invitation.activity_format]}</span>{(invitation.start_date || invitation.end_date) && <span><Icon name="calendar" size={14} />{invitation.start_date ? date(invitation.start_date) : '…'}{invitation.end_date ? ` — ${date(invitation.end_date)}` : ''}</span>}</div>
            {preview && <div className={`collab-match${preview.can_respond ? '' : ' unavailable'}`}><strong>{preview.can_respond ? c.suitable : c.unsuitable}</strong><p className="collab-muted">{preview.can_respond ? c.suitableHint : preview.eligible ? c.closedHint : c.unsuitableHint}</p><details className="collab-details"><summary>{c.details}<Icon name="chevron" size={14} /></summary><p className="collab-muted">{preview.employee_friendly_reason || preview.explanation}</p></details></div>}
            <div className="collab-actions">{!preview ? <button className="btn ghost" disabled={disabled} onClick={() => void run(`preview-${invitation.invitation_id}`, () => service.preview(invitation.invitation_id, employeeId), (result) => setPreviews((previous) => ({ ...previous, [invitation.invitation_id]: result })))}>{busy === `preview-${invitation.invitation_id}` ? c.loading : c.preview}</button> : <><button className="btn" disabled={disabled || !preview.can_respond} onClick={() => void respond(invitation, 'accept')}>{busy === `respond-${invitation.invitation_id}` ? c.working : c.accept}</button><button className="text-button" disabled={disabled} onClick={() => setDeclining(invitation.invitation_id)}>{c.decline}</button></>}</div>
            {declining === invitation.invitation_id && <div className="collab-form collab-divider"><p className="collab-muted">{c.declineWarning}</p><div className="collab-actions"><button className="btn ghost" disabled={disabled} onClick={() => void respond(invitation, 'decline')}>{c.confirmDecline}</button><button className="text-button" disabled={disabled} onClick={() => setDeclining(null)}>{c.cancel}</button></div></div>}
          </article>
        })}
        {ownInvitations.length > 0 && <section className="card"><h2>{c.ownInvitations}</h2>{ownInvitations.map((invitation) => <div key={invitation.invitation_id}><h3>{invitation.activity_title}</h3><p className="collab-muted">{formats[invitation.activity_format]} · {c.waitingPartner}</p></div>)}</section>}
      </div>
      <aside className="collab-sidebar">
        <section className="card"><h2>{c.invitationTitle}</h2><p className="collab-muted">{recommendations.length ? c.invitationHint : c.noQuests}</p><form className="collab-form" onSubmit={publish}>
          <label className="collab-field">{c.activity}<select value={inviteEvent || recommendations[0]?.event_id || ''} disabled={disabled || !recommendations.length} required onChange={(event) => setInviteEvent(event.target.value)}>{!recommendations.length && <option value="">—</option>}{eventOptions()}</select></label>
          <label className="collab-field">{c.format}<select value={format} disabled={disabled} onChange={(event) => setFormat(event.target.value as PairFormat)}>{Object.entries(formats).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <label className="collab-field">{c.display}<select value={displayMode} disabled={disabled} onChange={(event) => setDisplayMode(event.target.value as 'name' | 'alias')}><option value="name">{c.name}</option><option value="alias">{c.alias}</option></select></label>
          {displayMode === 'alias' && <label className="collab-field">{c.aliasName}<input value={alias} disabled={disabled} required maxLength={200} onChange={(event) => setAlias(event.target.value)} /></label>}
          <details className="collab-details"><summary>{c.dates}<Icon name="chevron" size={14} /></summary><div className="collab-fields"><label className="collab-field">{c.from}<input type="date" value={startDate} disabled={disabled} onChange={(event) => setStartDate(event.target.value)} /></label><label className="collab-field">{c.to}<input type="date" value={endDate} min={startDate || undefined} disabled={disabled} onChange={(event) => setEndDate(event.target.value)} /></label></div></details>
          <button className="btn" disabled={disabled || !recommendations.length || (displayMode === 'alias' && !alias.trim())}>{busy === 'publish' ? c.working : c.publish}<Icon name="arrow" size={14} /></button>
        </form></section>
        <section className="card"><h2>{c.restorePair}</h2><p className="collab-muted">{c.restoreHint}</p><form className="collab-form" onSubmit={(event) => { event.preventDefault(); void run('open-pair', async () => { const pair = await service.pair(pairCode.trim()); if (!pair.members.includes(employeeId)) throw new ApiError('not_member', 422); return pair }, (pair) => { addPair(pair, 'pairOpened'); setPairCode('') }) }}><label className="collab-field">{c.pairCode}<input placeholder="PAIR_…" required value={pairCode} disabled={disabled} onChange={(event) => setPairCode(event.target.value)} /></label><button className="btn ghost" disabled={disabled || !pairCode.trim()}>{busy === 'open-pair' ? c.working : c.openPair}</button></form></section>
      </aside>
    </div>}
  </div>
}
