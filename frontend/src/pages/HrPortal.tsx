import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api, ApiError } from '../api'
import { authApi, type HrSession } from '../authApi'
import { setCatalog } from '../catalog'
import { BrandLogo } from '../components/BrandLogo'
import { Icon } from '../components/Icon'
import { useI18n, type Lang } from '../i18n'
import { HrPage } from './HrPage'
import './HrPortal.css'

const words = {
  ru: { portal: 'Кабинет HR', title: 'Развитие команды начинается здесь', intro: 'Навыки, обучение и карьерный рост сотрудников — в одном кабинете.', login: 'Вход для HR', hint: 'Войдите с учётными данными HR, чтобы открыть аналитику команды.', username: 'Логин', password: 'Пароль', show: 'Показать пароль', hide: 'Скрыть пароль', enter: 'Войти в кабинет', busy: 'Входим…', logout: 'Выйти', employee: 'Кабинет сотрудника', invalid: 'Неверный логин или пароль.', limit: 'Слишком много попыток. Повторите через 5 минут.', setup: 'Вход для HR ещё не настроен. Обратитесь к администратору.', network: 'Не удалось подключиться. Попробуйте ещё раз.', expired: 'Сессия завершена. Войдите снова.', retry: 'Повторить', theme: 'Сменить тему', checking: 'Проверяем вход…', authenticated: 'Доступ HR' },
  kk: { portal: 'HR кабинеті', title: 'Команданың дамуы осы жерден басталады', intro: 'Қызметкерлердің дағдылары, оқуы және мансаптық өсуі — бір кабинетте.', login: 'HR үшін кіру', hint: 'Команда аналитикасын ашу үшін HR тіркелгісімен кіріңіз.', username: 'Логин', password: 'Құпиясөз', show: 'Құпиясөзді көрсету', hide: 'Құпиясөзді жасыру', enter: 'Кабинетке кіру', busy: 'Кіру…', logout: 'Шығу', employee: 'Қызметкер кабинеті', invalid: 'Логин немесе құпиясөз қате.', limit: 'Тым көп әрекет. 5 минуттан кейін қайталаңыз.', setup: 'HR кіруі әлі бапталмаған. Әкімшіге хабарласыңыз.', network: 'Қосылу мүмкін болмады. Қайталап көріңіз.', expired: 'Сессия аяқталды. Қайта кіріңіз.', retry: 'Қайталау', theme: 'Тақырыпты өзгерту', checking: 'Кіруді тексеру…', authenticated: 'HR рұқсаты' },
  en: { portal: 'HR workspace', title: 'Your team’s growth starts here', intro: 'Employee skills, learning and career growth, together in one workspace.', login: 'HR sign in', hint: 'Sign in with your HR credentials to view team analytics.', username: 'Username', password: 'Password', show: 'Show password', hide: 'Hide password', enter: 'Sign in', busy: 'Signing in…', logout: 'Sign out', employee: 'Employee workspace', invalid: 'Incorrect username or password.', limit: 'Too many attempts. Try again in 5 minutes.', setup: 'HR sign-in is not configured yet. Contact your administrator.', network: 'Could not connect. Please try again.', expired: 'Your session has ended. Please sign in again.', retry: 'Retry', theme: 'Change theme', checking: 'Checking session…', authenticated: 'HR access' },
}

export function HrPortal() {
  const { lang, setLang } = useI18n()
  const c = words[lang]
  const [session, setSession] = useState<HrSession | null>(null)
  const [error, setError] = useState<keyof typeof c | null>(null)
  const [busy, setBusy] = useState(false)
  const [ready, setReady] = useState(false)
  const [username, setUsername] = useState('hr')
  const [password, setPassword] = useState('')
  const [visible, setVisible] = useState(false)
  const [theme, setTheme] = useState(() => { try { return localStorage.getItem('cq_theme') === 'dark' ? 'dark' : 'light' } catch { return 'light' } })

  useEffect(() => {
    document.title = `Career City · ${c.portal}`
    document.documentElement.lang = lang
    document.documentElement.dataset.theme = theme
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#171b20' : '#f5f7f6')
    try { localStorage.setItem('cq_theme', theme) } catch { /* unavailable storage */ }
  }, [theme, lang, c.portal])

  const checkSession = useCallback(() => {
    setError(null)
    authApi.session().then(setSession).catch(() => setError('network'))
  }, [])
  useEffect(checkSession, [checkSession])

  const loadCatalog = useCallback(() => {
    setError(null)
    api.catalog().then((catalog) => { setCatalog(catalog); setReady(true) }).catch(() => setError('network'))
  }, [])
  useEffect(() => { if (session?.authenticated) loadCatalog() }, [session, loadCatalog])

  const onUnauthorized = useCallback(() => {
    setSession({ authenticated: false })
    setReady(false)
    setError('expired')
  }, [])
  useEffect(() => {
    if (!session?.authenticated) return
    const timeout = window.setTimeout(onUnauthorized, Math.max(0, Date.parse(session.expires_at) - Date.now()))
    return () => clearTimeout(timeout)
  }, [session, onUnauthorized])

  async function login(event: FormEvent) {
    event.preventDefault()
    if (busy) return
    setBusy(true); setError(null)
    try {
      setSession(await authApi.login(username.trim(), password))
      setPassword(''); setVisible(false)
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.status === 401 ? 'invalid' : cause.status === 429 ? 'limit' : cause.status === 503 ? 'setup' : 'network' : 'network')
    } finally { setBusy(false) }
  }

  async function logout() {
    if (!session?.authenticated || busy) return
    setBusy(true); setError(null)
    try { await authApi.logout(session.csrf_token); setSession({ authenticated: false }); setReady(false) }
    catch (cause) { if (cause instanceof ApiError && cause.status === 401) onUnauthorized(); else setError('network') }
    finally { setBusy(false) }
  }

  return <div className="hr-portal">
    <header className="hr-header">
      <a className="hr-brand" href="/hr" aria-label="HalykBank Career City"><span className="hr-brand-full"><BrandLogo /></span><span className="hr-brand-compact"><BrandLogo compact /></span></a>
      <span className="hr-portal-label"><Icon name="shield" size={16} />{c.portal}</span>
      <div className="hr-tools">
        <div className="lang" role="group" aria-label="Language">{(['kk', 'ru', 'en'] as Lang[]).map((l) => <button key={l} className={lang === l ? 'active' : ''} aria-pressed={lang === l} onClick={() => setLang(l)}>{l === 'kk' ? 'KZ' : l}</button>)}</div>
        <button className="icon-btn" aria-label={c.theme} onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}><Icon name={theme === 'dark' ? 'sun' : 'moon'} /></button>
      </div>
    </header>
    <main className={`hr-content ${session?.authenticated ? '' : 'hr-content-login'}`}>
      {!session ? <div className="card hr-session-state" role="status">{error ? <><p>{c[error]}</p><button className="btn" onClick={checkSession}>{c.retry}</button></> : c.checking}</div> : session.authenticated ? <>
        <div className="hr-account"><span><Icon name="shield" size={16} />{c.authenticated} · {session.username}</span><div><a href="/employee">{c.employee}</a><button className="btn ghost" disabled={busy} onClick={logout}>{c.logout}</button></div></div>
        {error && <div className="card state error" role="alert"><p>{c[error]}</p>{!ready && <button className="btn" onClick={loadCatalog}>{c.retry}</button>}</div>}
        {ready ? <HrPage onUnauthorized={onUnauthorized} /> : !error && <div className="skeleton" />}
      </> : <div className="hr-login-layout">
        <section className="hr-intro"><span className="hr-intro-icon"><Icon name="chart" size={32} /></span><h1>{c.title}</h1><p>{c.intro}</p><div className="hr-growth-art" aria-hidden="true"><i /><i /><i /><i /><Icon name="spark" size={30} /></div></section>
        <section className="card hr-login-card"><div className="hr-login-heading"><Icon name="shield" size={24} /><h2>{c.login}</h2></div><p>{c.hint}</p>
          <form onSubmit={login} aria-busy={busy}>
            <label htmlFor="hr-username">{c.username}</label><input id="hr-username" name="username" autoComplete="username" required maxLength={128} value={username} onChange={(e) => setUsername(e.target.value)} />
            <label htmlFor="hr-password">{c.password}</label><div className="hr-password-field"><input id="hr-password" name="password" type={visible ? 'text' : 'password'} autoComplete="current-password" required maxLength={1024} value={password} onChange={(e) => setPassword(e.target.value)} aria-describedby={error ? 'hr-login-error' : undefined} /><button type="button" aria-pressed={visible} onClick={() => setVisible(!visible)}>{visible ? c.hide : c.show}</button></div>
            {error && <p className="hr-login-error" id="hr-login-error" role="alert">{c[error]}</p>}
            <button className="btn hr-login-submit" type="submit" disabled={busy}>{busy ? c.busy : c.enter}<Icon name="arrow" size={18} /></button>
          </form>
          <a className="hr-employee-link" href="/employee">{c.employee}<Icon name="arrow" size={16} /></a>
        </section>
      </div>}
    </main>
  </div>
}
