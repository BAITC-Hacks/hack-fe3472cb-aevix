import { useCallback, useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { api, ApiError, type EsgGoal, type WalletResponse } from '../api'
import { useI18n } from '../i18n'
import { Icon } from './Icon'
import './wallet.css'

const copy = {
  ru: {
    title: 'Ваш вклад начинается с роста', subtitle: 'Учитесь, получайте Growth Coins и поддерживайте общие инициативы.',
    balance: 'Доступный баланс', earned: 'Награды за развитие', earnHint: 'Growth Coins начисляются за новые завершённые добровольные квесты. Обязательное обучение не приносит монеты.',
    history: 'Последние операции', noHistory: 'Завершите добровольный квест — здесь появится первая награда.', reward: 'Награда за квест', contribution: 'Поддержка инициативы',
    goals: 'Инициативы ESG', goalHint: 'Выберите, во что превратить свой прогресс.', noGoals: 'Пока нет доступных инициатив.',
    pending: 'На проверке HR', active: 'Активна', approved: 'Одобрена HR', completed: 'Завершена', unknown: 'Статус уточняется',
    total: 'Собрано', people: 'Участников', amount: 'Ваш вклад, Growth Coins', support: 'Поддержать', submitting: 'Отправляем…',
    spendHint: 'Взнос списывается с вашего баланса.', needCoins: 'Завершите добровольный квест, чтобы заработать монеты.',
    invalidAmount: 'Введите целое число от 1 до доступного баланса.', success: 'Вклад принят. Списано Growth Coins:',
    walletError: 'Не удалось загрузить кошелёк.', goalsError: 'Не удалось загрузить инициативы.', sendError: 'Не удалось отправить вклад. Попробуйте ещё раз.', insufficient: 'Недостаточно монет. Обновите баланс и уменьшите сумму.',
    social: 'Общество', environment: 'Экология', governance: 'Ответственное управление',
    mentoring: 'Цифровая грамотность', green: 'Зелёный офис', ai: 'Ответственный ИИ',
  },
  kk: {
    title: 'Сіздің үлесіңіз дамудан басталады', subtitle: 'Оқыңыз, Growth Coins жинаңыз және ортақ бастамаларды қолдаңыз.',
    balance: 'Қолжетімді баланс', earned: 'Даму үшін марапат', earnHint: 'Growth Coins жаңадан аяқталған ерікті квесттер үшін беріледі. Міндетті оқу үшін монеталар берілмейді.',
    history: 'Соңғы операциялар', noHistory: 'Ерікті квестті аяқтаңыз — алғашқы марапат осында көрсетіледі.', reward: 'Квест үшін марапат', contribution: 'Бастаманы қолдау',
    goals: 'ESG бастамалары', goalHint: 'Дамуыңыздың қай іске үлес қосатынын таңдаңыз.', noGoals: 'Әзірге қолжетімді бастамалар жоқ.',
    pending: 'HR тексеруінде', active: 'Белсенді', approved: 'HR мақұлдаған', completed: 'Аяқталды', unknown: 'Мәртебесі нақтылануда',
    total: 'Жиналды', people: 'Қатысушылар', amount: 'Сіздің үлесіңіз, Growth Coins', support: 'Қолдау', submitting: 'Жіберілуде…',
    spendHint: 'Үлес сіздің балансыңыздан шегеріледі.', needCoins: 'Монеталар алу үшін ерікті квестті аяқтаңыз.',
    invalidAmount: '1-ден қолжетімді балансқа дейінгі бүтін санды енгізіңіз.', success: 'Үлес қабылданды. Шегерілген Growth Coins:',
    walletError: 'Әмиянды жүктеу мүмкін болмады.', goalsError: 'Бастамаларды жүктеу мүмкін болмады.', sendError: 'Үлесті жіберу мүмкін болмады. Қайта көріңіз.', insufficient: 'Монеталар жеткіліксіз. Балансты жаңартып, соманы азайтыңыз.',
    social: 'Қоғам', environment: 'Экология', governance: 'Жауапты басқару',
    mentoring: 'Цифрлық сауаттылық', green: 'Жасыл кеңсе', ai: 'Жауапты ЖИ',
  },
  en: {
    title: 'Turn your growth into impact', subtitle: 'Learn, earn Growth Coins and support shared initiatives.',
    balance: 'Available balance', earned: 'Rewards for growth', earnHint: 'Earn Growth Coins for newly completed voluntary quests. Mandatory training does not earn coins.',
    history: 'Recent transactions', noHistory: 'Complete a voluntary quest to see your first reward here.', reward: 'Quest reward', contribution: 'Initiative contribution',
    goals: 'ESG initiatives', goalHint: 'Choose where your progress makes a difference.', noGoals: 'No initiatives are available yet.',
    pending: 'Pending HR review', active: 'Active', approved: 'Approved by HR', completed: 'Completed', unknown: 'Status to be confirmed',
    total: 'Contributed', people: 'Contributors', amount: 'Your contribution, Growth Coins', support: 'Contribute', submitting: 'Sending…',
    spendHint: 'Your contribution is deducted from your balance.', needCoins: 'Complete a voluntary quest to earn coins.',
    invalidAmount: 'Enter a whole number from 1 to your available balance.', success: 'Contribution received. Growth Coins spent:',
    walletError: 'Unable to load your wallet.', goalsError: 'Unable to load initiatives.', sendError: 'Unable to send your contribution. Please try again.', insufficient: 'Not enough coins. Refresh your balance and reduce the amount.',
    social: 'Social', environment: 'Environment', governance: 'Governance',
    mentoring: 'Digital literacy mentoring', green: 'Green office initiative', ai: 'Responsible AI learning',
  },
}

type Props = { employeeId: string; onBalanceChange: () => void }

// Each employee gets isolated form and request state, including pending responses.
export function WalletPanel(props: Props) {
  return <WalletContent key={props.employeeId} {...props} />
}

function WalletContent({ employeeId, onBalanceChange }: Props) {
  const { lang, t } = useI18n()
  const c = copy[lang]
  const id = useId()
  const [wallet, setWallet] = useState<WalletResponse | null>(null)
  const [goals, setGoals] = useState<EsgGoal[]>([])
  const [loading, setLoading] = useState(true)
  const [walletError, setWalletError] = useState(false)
  const [goalsError, setGoalsError] = useState(false)
  const [amounts, setAmounts] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState<string | null>(null)
  const [message, setMessage] = useState<{ error?: 'invalidAmount' | 'sendError' | 'insufficient'; spent?: number } | null>(null)
  const mounted = useRef(false)
  const locked = useRef(false)
  const generation = useRef(0)
  const number = (value: number) => value.toLocaleString(lang)

  const refresh = useCallback(async () => {
    const request = ++generation.current
    setLoading(true)
    const [walletResult, goalsResult] = await Promise.allSettled([api.wallet(employeeId), api.esgGoals()])
    if (!mounted.current || request !== generation.current) return
    setWalletError(walletResult.status === 'rejected')
    setGoalsError(goalsResult.status === 'rejected')
    if (walletResult.status === 'fulfilled') setWallet(walletResult.value)
    if (goalsResult.status === 'fulfilled') setGoals(goalsResult.value)
    setLoading(false)
  }, [employeeId])

  useEffect(() => {
    mounted.current = true
    void refresh()
    return () => { mounted.current = false; generation.current += 1 }
  }, [refresh])

  async function contribute(event: FormEvent<HTMLFormElement>, goal: EsgGoal) {
    event.preventDefault()
    if (locked.current || loading || walletError || !wallet) return
    const coins = Number(amounts[goal.goal_id] ?? '')
    if (!Number.isSafeInteger(coins) || coins <= 0 || coins > wallet.balance) {
      setMessage({ error: 'invalidAmount' })
      return
    }
    locked.current = true
    setBusy(goal.goal_id)
    setMessage(null)
    try {
      const result = await api.contribute(employeeId, goal.goal_id, coins)
      if (!mounted.current) return
      setWallet((previous) => previous ? { ...previous, balance: result.wallet_balance } : previous)
      setGoals((previous) => previous.map((item) => item.goal_id === goal.goal_id ? { ...item, ...result } : item))
      setAmounts((previous) => ({ ...previous, [goal.goal_id]: '' }))
      setMessage({ spent: result.coins_spent })
      onBalanceChange()
      await refresh()
    } catch (error) {
      if (mounted.current) setMessage({ error: error instanceof ApiError && error.status === 409 ? 'insufficient' : 'sendError' })
    } finally {
      locked.current = false
      if (mounted.current) setBusy(null)
    }
  }

  const titles: Record<string, string> = { ESG_SOCIAL_MENTORING: c.mentoring, ESG_GREEN_OFFICE: c.green, ESG_GOVERNANCE: c.ai }
  const categories: Record<string, string> = { Social: c.social, Environment: c.environment, Governance: c.governance }
  const statuses: Record<string, string> = { pending_hr_review: c.pending, active: c.active, approved: c.approved, completed: c.completed }

  return <section className="growth-wallet" aria-labelledby={`${id}-heading`}>
    <div className="growth-wallet-heading"><div><h2 id={`${id}-heading`}>{c.title}</h2><p>{c.subtitle}</p></div><span className="growth-wallet-label"><Icon name="leaf" size={16} />Growth Coins</span></div>
    <div className="growth-wallet-layout">
      <aside className="card growth-wallet-account" aria-label={c.balance}>
        <span className="growth-wallet-eyebrow">{c.earned}</span>
        <div className="growth-wallet-balance" aria-live="polite"><strong>{wallet ? number(wallet.balance) : '—'}</strong><span>Growth Coins</span></div>
        <p className="growth-wallet-balance-label">{c.balance}</p>
        <p className="growth-wallet-hint">{c.earnHint}</p>
        {loading && <p role="status" className="growth-wallet-hint">{t('loading')}</p>}
        {walletError && <div className="growth-wallet-error" role="alert"><p>{c.walletError}</p><button className="text-button" disabled={loading || !!busy} onClick={() => void refresh()}>{t('retry')}</button></div>}
        <details className="growth-wallet-history">
          <summary>{c.history}<Icon name="chevron" size={16} /></summary>
          {wallet?.transactions.length ? <ul>{wallet.transactions.slice(0, 5).map((transaction) => <li key={transaction.transaction_id}>
            <div><span>{transaction.amount < 0 ? c.contribution : c.reward}</span><time dateTime={transaction.created_at}>{new Date(`${transaction.created_at.slice(0, 10)}T12:00:00`).toLocaleDateString(lang, { day: 'numeric', month: 'short' })}</time></div>
            <strong className={transaction.amount < 0 ? '' : 'growth-wallet-credit'}>{transaction.amount > 0 ? '+' : ''}{number(transaction.amount)}</strong>
          </li>)}</ul> : <p className="growth-wallet-hint">{wallet ? c.noHistory : walletError ? c.walletError : t('loading')}</p>}
        </details>
      </aside>
      <div className="growth-wallet-initiatives">
        <div className="growth-wallet-goal-heading"><span className="growth-wallet-icon"><Icon name="people" size={20} /></span><div><h3>{c.goals}</h3><p>{c.goalHint}</p></div></div>
        <p className="growth-wallet-spend-note" id={`${id}-spend-note`}>{c.spendHint}</p>
        {message && <p className={`growth-wallet-feedback ${message.error ? 'growth-wallet-error' : ''}`} role={message.error ? 'alert' : 'status'}>{message.error ? c[message.error] : `${c.success} ${number(message.spent ?? 0)}`}</p>}
        {goalsError && <div className="growth-wallet-error" role="alert"><p>{c.goalsError}</p><button className="text-button" disabled={loading || !!busy} onClick={() => void refresh()}>{t('retry')}</button></div>}
        {!goals.length && <p className="growth-wallet-hint">{loading ? t('loading') : goalsError ? '' : c.noGoals}</p>}
        <div className="growth-wallet-goals">{goals.map((goal) => {
          const amount = Number(amounts[goal.goal_id] ?? '')
          const valid = Number.isSafeInteger(amount) && amount > 0 && amount <= (wallet?.balance ?? 0)
          const pending = goal.status === 'pending_hr_review'
          return <details className="growth-wallet-goal" key={goal.goal_id}>
            <summary><span><small>{categories[goal.category] ?? goal.category}</small><strong>{titles[goal.goal_id] ?? goal.title}</strong><span className={`growth-wallet-status ${pending ? 'pending' : ''}`}>{pending && <Icon name="clock" size={12} />}{statuses[goal.status] ?? c.unknown}</span></span><Icon name="chevron" size={17} /></summary>
            <div className="growth-wallet-goal-body">
              {goal.description && <p className="growth-wallet-hint">{goal.description}</p>}
              <div className="growth-wallet-goal-stats"><span>{c.total}<strong>{number(goal.total_contributed_coins)} GC</strong></span><span>{c.people}<strong>{number(goal.contributors_count)}</strong></span></div>
              {goal.target_coins != null && goal.target_coins > 0 && <progress aria-label={`${c.total}: ${number(goal.total_contributed_coins)} / ${number(goal.target_coins)} GC`} value={Math.min(goal.total_contributed_coins, goal.target_coins)} max={goal.target_coins} />}
              <form className="growth-wallet-form" onSubmit={(event) => void contribute(event, goal)}>
                <label htmlFor={`${id}-${goal.goal_id}`}>{c.amount}</label>
                <div><input id={`${id}-${goal.goal_id}`} type="number" inputMode="numeric" min="1" max={wallet?.balance ?? 0} step="1" required placeholder="10" value={amounts[goal.goal_id] ?? ''} disabled={!!busy || loading || walletError || !wallet?.balance} onChange={(event) => setAmounts((previous) => ({ ...previous, [goal.goal_id]: event.target.value }))} aria-describedby={`${id}-spend-note`} /><button className="btn" type="submit" disabled={!!busy || loading || walletError || !valid}>{busy === goal.goal_id ? c.submitting : c.support}<Icon name="arrow" size={15} /></button></div>
              </form>
              {wallet?.balance === 0 && <p className="growth-wallet-hint">{c.needCoins}</p>}
            </div>
          </details>
        })}</div>
      </div>
    </div>
  </section>
}
