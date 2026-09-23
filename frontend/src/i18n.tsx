import { createContext, useContext, useState, type ReactNode } from 'react'

export type Lang = 'ru' | 'kk' | 'en'

const dict = {
  ru: {
    brand: 'Career Quest',
    tagline: 'AI-навигатор развития',
    nav_me: 'Мой путь',
    nav_hr: 'HR-аналитика',
    pick_employee: 'Сотрудник',
    search: 'Поиск по имени, роли, ID…',
    goal: 'Цель',
    no_goal: 'Цель не задана — берём следующий грейд',
    progress: 'Готовность к цели',
    tenure: 'Стаж',
    months: 'мес.',
    format: 'Формат',
    review: 'Последняя оценка',
    career_map: 'Карьерная карта',
    you_are_here: 'Вы здесь',
    target: 'Цель',
    next_quests: 'Следующие квесты',
    why: 'Почему этот квест',
    hours: 'ч',
    mark_done: 'Отметить выполненным',
    done: 'Выполнено',
    skills_gap: 'Навыки: сейчас vs требуется',
    critical: 'Критичный',
    only_gaps: 'Только разрывы',
    all_skills: 'Все навыки',
    history: 'История обучения',
    empty_history: 'Пока нет записей',
    no_recs: 'Все навыки для цели закрыты — отличная работа!',
    priority_high: 'Высокий приоритет',
    priority_medium: 'Средний приоритет',
    priority_low: 'Низкий приоритет',
    after: 'после',
    loading: 'Загрузка…',
    error_backend: 'Не удалось связаться с бэкендом. Запущен ли uvicorn на :8000?',
    retry: 'Повторить',
    hr_title: 'Аналитика по компании',
    hr_note: 'Только агрегированные данные — без персональных рейтингов.',
    kpi_employees: 'Сотрудников',
    kpi_progress: 'Средняя готовность',
    kpi_completion: 'Завершаемость',
    kpi_inactive: 'Неактивных',
    top_gaps: 'Главные разрывы в навыках',
    affected: 'сотр.',
    avg_gap: 'ср. разрыв',
    popular: 'Популярные мероприятия',
    risky: 'Сегменты риска',
    toast_done: 'Квест выполнен',
    status_completed: 'Завершено',
    status_in_progress: 'В процессе',
    status_dropped: 'Брошено',
    status_no_show: 'Не пришёл',
    status_declined: 'Отказ',
    status_overdue: 'Просрочено',
  },
  kk: {
    brand: 'Career Quest',
    tagline: 'Дамудың AI-навигаторы',
    nav_me: 'Менің жолым',
    nav_hr: 'HR-талдау',
    pick_employee: 'Қызметкер',
    search: 'Аты, рөлі, ID бойынша іздеу…',
    goal: 'Мақсат',
    no_goal: 'Мақсат қойылмаған — келесі грейд алынады',
    progress: 'Мақсатқа дайындық',
    tenure: 'Өтілі',
    months: 'ай',
    format: 'Формат',
    review: 'Соңғы бағалау',
    career_map: 'Мансап картасы',
    you_are_here: 'Сіз осындасыз',
    target: 'Мақсат',
    next_quests: 'Келесі квесттер',
    why: 'Неге бұл квест',
    hours: 'сағ',
    mark_done: 'Орындалды деп белгілеу',
    done: 'Орындалды',
    skills_gap: 'Дағдылар: қазір vs талап',
    critical: 'Маңызды',
    only_gaps: 'Тек олқылықтар',
    all_skills: 'Барлық дағдылар',
    history: 'Оқу тарихы',
    empty_history: 'Әзірге жазба жоқ',
    no_recs: 'Мақсатқа қажетті барлық дағдылар жабылды!',
    priority_high: 'Жоғары басымдық',
    priority_medium: 'Орташа басымдық',
    priority_low: 'Төмен басымдық',
    after: 'кейін',
    loading: 'Жүктелуде…',
    error_backend: 'Бэкендке қосылу мүмкін болмады. uvicorn :8000 портында іске қосылған ба?',
    retry: 'Қайталау',
    hr_title: 'Компания бойынша талдау',
    hr_note: 'Тек жиынтық деректер — жеке рейтингсіз.',
    kpi_employees: 'Қызметкерлер',
    kpi_progress: 'Орташа дайындық',
    kpi_completion: 'Аяқтау үлесі',
    kpi_inactive: 'Белсенді емес',
    top_gaps: 'Негізгі дағды олқылықтары',
    affected: 'адам',
    avg_gap: 'орт. олқылық',
    popular: 'Танымал іс-шаралар',
    risky: 'Тәуекел сегменттері',
    toast_done: 'Квест орындалды',
    status_completed: 'Аяқталды',
    status_in_progress: 'Орындалуда',
    status_dropped: 'Тасталды',
    status_no_show: 'Келмеді',
    status_declined: 'Бас тартты',
    status_overdue: 'Мерзімі өтті',
  },
  en: {
    brand: 'Career Quest',
    tagline: 'AI growth navigator',
    nav_me: 'My path',
    nav_hr: 'HR analytics',
    pick_employee: 'Employee',
    search: 'Search by name, role, ID…',
    goal: 'Goal',
    no_goal: 'No goal set — using the next grade',
    progress: 'Readiness for goal',
    tenure: 'Tenure',
    months: 'mo',
    format: 'Format',
    review: 'Last review',
    career_map: 'Career map',
    you_are_here: 'You are here',
    target: 'Target',
    next_quests: 'Next quests',
    why: 'Why this quest',
    hours: 'h',
    mark_done: 'Mark as completed',
    done: 'Completed',
    skills_gap: 'Skills: current vs required',
    critical: 'Critical',
    only_gaps: 'Gaps only',
    all_skills: 'All skills',
    history: 'Learning history',
    empty_history: 'No records yet',
    no_recs: 'All skills for the goal are covered — great job!',
    priority_high: 'High priority',
    priority_medium: 'Medium priority',
    priority_low: 'Low priority',
    after: 'after',
    loading: 'Loading…',
    error_backend: 'Cannot reach the backend. Is uvicorn running on :8000?',
    retry: 'Retry',
    hr_title: 'Company analytics',
    hr_note: 'Aggregated data only — no personal rankings.',
    kpi_employees: 'Employees',
    kpi_progress: 'Avg readiness',
    kpi_completion: 'Completion rate',
    kpi_inactive: 'Inactive',
    top_gaps: 'Top skill gaps',
    affected: 'empl.',
    avg_gap: 'avg gap',
    popular: 'Popular events',
    risky: 'Risk segments',
    toast_done: 'Quest completed',
    status_completed: 'Completed',
    status_in_progress: 'In progress',
    status_dropped: 'Dropped',
    status_no_show: 'No-show',
    status_declined: 'Declined',
    status_overdue: 'Overdue',
  },
} as const

export type TKey = keyof (typeof dict)['ru']

interface Ctx {
  lang: Lang
  setLang: (l: Lang) => void
  t: (k: TKey) => string
}

const I18nContext = createContext<Ctx | null>(null)

function initialLang(): Lang {
  try {
    const saved = localStorage.getItem('cq_lang')
    if (saved === 'ru' || saved === 'kk' || saved === 'en') return saved
  } catch {
    /* storage недоступен */
  }
  return 'ru'
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang)
  const setLang = (l: Lang) => {
    setLangState(l)
    try {
      localStorage.setItem('cq_lang', l)
    } catch {
      /* ignore */
    }
  }
  const t = (k: TKey) => dict[lang][k] ?? dict.ru[k]
  return <I18nContext.Provider value={{ lang, setLang, t }}>{children}</I18nContext.Provider>
}

export function useI18n() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n outside provider')
  return ctx
}
