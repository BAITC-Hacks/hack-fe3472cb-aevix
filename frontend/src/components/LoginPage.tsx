import { useId, useRef, useState, type FormEvent } from 'react'
import { ApiError } from '../api'
import { useI18n, type Lang } from '../i18n'
import { BrandLogo } from './BrandLogo'
import { Icon } from './Icon'
import './login.css'

const copy = {
  ru: {
    language: 'Язык интерфейса',
    theme: 'Сменить тему',
    eyebrow: 'РАСТЁМ ВМЕСТЕ',
    title: 'Ваш следующий шаг начинается здесь',
    intro: 'Развивайте навыки, учитесь вместе и открывайте новые возможности в Career City.',
    personal: 'Личный план развития',
    teamwork: 'Обучение вместе с коллегами',
    analytics: 'Аналитика команды для HR',
    welcome: 'Добро пожаловать',
    hint: 'Единый вход для сотрудников и HR.',
    username: 'ID сотрудника или логин HR',
    usernameHint: 'Используйте свою рабочую учётную запись.',
    password: 'Личный пароль',
    showPassword: 'Показать пароль',
    hidePassword: 'Скрыть пароль',
    submit: 'Войти',
    busy: 'Входим…',
    help: 'Нужен доступ или новый пароль? Обратитесь к администратору вашей компании.',
    invalid: 'Неверный ID, логин или пароль. Проверьте данные и попробуйте снова.',
    limit: 'Слишком много попыток входа. Подождите немного и попробуйте снова.',
    network: 'Не удалось войти. Проверьте подключение и попробуйте ещё раз.',
    missingUsername: 'Введите ID сотрудника или логин HR.',
  },
  kk: {
    language: 'Интерфейс тілі',
    theme: 'Тақырыпты өзгерту',
    eyebrow: 'БІРГЕ ДАМИМЫЗ',
    title: 'Келесі қадамыңыз осы жерден басталады',
    intro: 'Career City-де дағдыларыңызды дамытыңыз, бірге оқыңыз және жаңа мүмкіндіктерді ашыңыз.',
    personal: 'Жеке даму жоспары',
    teamwork: 'Әріптестермен бірге оқу',
    analytics: 'HR үшін команда аналитикасы',
    welcome: 'Қош келдіңіз',
    hint: 'Қызметкерлер мен HR үшін бірыңғай кіру.',
    username: 'Қызметкер ID-і немесе HR логині',
    usernameHint: 'Жұмыс тіркелгіңізді пайдаланыңыз.',
    password: 'Жеке құпиясөз',
    showPassword: 'Құпиясөзді көрсету',
    hidePassword: 'Құпиясөзді жасыру',
    submit: 'Кіру',
    busy: 'Кіруде…',
    help: 'Кіруге рұқсат немесе жаңа құпиясөз керек пе? Компанияңыздың әкімшісіне хабарласыңыз.',
    invalid: 'ID, логин немесе құпиясөз қате. Деректерді тексеріп, қайта көріңіз.',
    limit: 'Кіру әрекеттері тым көп. Біраз күтіп, қайта көріңіз.',
    network: 'Кіру мүмкін болмады. Байланысты тексеріп, қайта көріңіз.',
    missingUsername: 'Қызметкер ID-ін немесе HR логинін енгізіңіз.',
  },
  en: {
    language: 'Interface language',
    theme: 'Change theme',
    eyebrow: 'GROW TOGETHER',
    title: 'Your next step starts here',
    intro: 'Build your skills, learn together and discover new opportunities in Career City.',
    personal: 'Your personal development plan',
    teamwork: 'Learning with your colleagues',
    analytics: 'Team insights for HR',
    welcome: 'Welcome back',
    hint: 'One sign-in for employees and HR.',
    username: 'Employee ID or HR username',
    usernameHint: 'Use your own work account.',
    password: 'Personal password',
    showPassword: 'Show password',
    hidePassword: 'Hide password',
    submit: 'Sign in',
    busy: 'Signing in…',
    help: 'Need access or a new password? Contact your company administrator.',
    invalid: 'Incorrect ID, username or password. Check your details and try again.',
    limit: 'Too many sign-in attempts. Please wait a little and try again.',
    network: 'Could not sign in. Check your connection and try again.',
    missingUsername: 'Enter your employee ID or HR username.',
  },
} as const

type LoginError = 'invalid' | 'limit' | 'network' | 'missingUsername'

export interface LoginPageProps {
  onLogin: (username: string, password: string) => Promise<void>
  loading?: boolean
  theme?: 'light' | 'dark'
  onToggleTheme?: () => void
}

export function LoginPage({ onLogin, loading = false, theme = 'light', onToggleTheme }: LoginPageProps) {
  const { lang, setLang } = useI18n()
  const c = copy[lang]
  const id = useId()
  const usernameInput = useRef<HTMLInputElement>(null)
  const submitLock = useRef(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [visible, setVisible] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<LoginError | null>(null)
  const busy = loading || submitting
  const errorId = `${id}-error`
  const usernameHintId = `${id}-username-hint`

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (loading || submitLock.current) return
    if (!username.trim()) {
      setError('missingUsername')
      usernameInput.current?.focus()
      return
    }
    submitLock.current = true
    setSubmitting(true)
    setError(null)
    try {
      await onLogin(username.trim(), password)
      setPassword('')
      setVisible(false)
    } catch (cause) {
      setError(cause instanceof ApiError && cause.status === 401 ? 'invalid'
        : cause instanceof ApiError && cause.status === 429 ? 'limit' : 'network')
    } finally {
      submitLock.current = false
      setSubmitting(false)
    }
  }

  return <div className="login-page" lang={lang}>
    <header className="login-header">
      <div className="login-brand" role="img" aria-label="HalykBank Career City"><BrandLogo /></div>
      <div className="login-tools"><div className="login-languages" role="group" aria-label={c.language}>
        {(['kk', 'ru', 'en'] as Lang[]).map((language) => <button
          type="button" key={language} lang={language}
          aria-label={{ kk: 'Қазақша', ru: 'Русский', en: 'English' }[language]}
          aria-pressed={lang === language} onClick={() => setLang(language)}
        >{language === 'kk' ? 'KZ' : language.toUpperCase()}</button>)}
      </div>
      {onToggleTheme && <button type="button" className="login-theme" aria-label={c.theme} title={c.theme} onClick={onToggleTheme}><Icon name={theme === 'dark' ? 'sun' : 'moon'} size={20} /></button>}
      </div>
    </header>

    <main className="login-main">
      <div className="login-layout">
        <section className="login-intro" aria-labelledby={`${id}-intro`}>
          <span className="login-intro-icon"><Icon name="route" size={30} /></span>
          <p className="login-eyebrow">{c.eyebrow}</p>
          <h1 id={`${id}-intro`}>{c.title}</h1>
          <p className="login-description">{c.intro}</p>
          <ul className="login-benefits">
            <li><span><Icon name="flag" /></span>{c.personal}</li>
            <li><span><Icon name="people" /></span>{c.teamwork}</li>
            <li><span><Icon name="chart" /></span>{c.analytics}</li>
          </ul>
        </section>

        <section className="login-card" aria-labelledby={`${id}-heading`}>
          <div className="login-card-heading"><span><Icon name="shield" size={22} /></span><h2 id={`${id}-heading`}>{c.welcome}</h2></div>
          <p className="login-card-hint">{c.hint}</p>
          <form onSubmit={submit} aria-busy={busy}>
            <div className="login-field">
              <label htmlFor={`${id}-username`}>{c.username}</label>
              <input
                ref={usernameInput} id={`${id}-username`} name="username" type="text"
                autoComplete="username" autoCapitalize="none" autoCorrect="off" spellCheck={false}
                required maxLength={128} disabled={busy} value={username}
                aria-invalid={error === 'invalid' || error === 'missingUsername'}
                aria-describedby={`${usernameHintId}${error ? ` ${errorId}` : ''}`}
                onChange={(event) => { setUsername(event.target.value); setError(null) }}
              />
              <p id={usernameHintId} className="login-field-hint">{c.usernameHint}</p>
            </div>
            <div className="login-field">
              <label htmlFor={`${id}-password`}>{c.password}</label>
              <div className="login-password">
                <input
                  id={`${id}-password`} name="password" type={visible ? 'text' : 'password'}
                  autoComplete="current-password" required maxLength={1024} disabled={busy} value={password}
                  aria-invalid={error === 'invalid'} aria-describedby={error ? errorId : undefined}
                  onChange={(event) => { setPassword(event.target.value); setError(null) }}
                />
                <button type="button" className="login-reveal" disabled={busy} aria-controls={`${id}-password`}
                  aria-label={visible ? c.hidePassword : c.showPassword} title={visible ? c.hidePassword : c.showPassword}
                  aria-pressed={visible} onClick={() => setVisible((previous) => !previous)}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" />
                    <circle cx="12" cy="12" r="3" />
                    {visible && <path d="m3 3 18 18" />}
                  </svg>
                </button>
              </div>
            </div>
            {error && <p id={errorId} className="login-error" role="alert">{c[error]}</p>}
            <button type="submit" className="login-submit" disabled={busy}>
              {busy && <span className="login-spinner" aria-hidden="true" />}
              <span>{busy ? c.busy : c.submit}</span>
              {!busy && <Icon name="arrow" size={18} />}
            </button>
          </form>
          <p className="login-help">{c.help}</p>
        </section>
      </div>
    </main>
  </div>
}
