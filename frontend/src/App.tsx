import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { createPortal } from 'react-dom'
import { api, ApiError, type EmployeeListItem } from './api'
import { authApi, type AuthSession } from './authApi'
import { PreviewContext } from './PreviewContext'
import { SESSION_EXPIRED_EVENT, setSessionTransport } from './sessionTransport'
import { EmployeePicker, initials } from './components/EmployeePicker'
import { BrandLogo } from './components/BrandLogo'
import { LoginPage } from './components/LoginPage'
import { cityCopy } from './cityCopy'
import { Icon, type IconName } from './components/Icon'
import { useI18n, type Lang } from './i18n'
import { EmployeePage } from './pages/EmployeePage'
import { HrPage } from './pages/HrPage'
import { readPage, type Page } from './routes'
import { setCatalog } from './catalog'
import './workspaceShell.css'

type Theme = 'light' | 'dark'
type NavItem = { page: Page; icon: IconName; label: string }
function readStored(key: string) { try { return localStorage.getItem(key) } catch { return null } }
function writeStored(key: string, value: string) { try { localStorage.setItem(key, value) } catch { /* Storage is optional. */ } }
const copy = {
  ru: { menu: 'Меню', close: 'Закрыть меню', logout: 'Выйти', exiting: 'Выходим…', checking: 'Проверяем вход…', expired: 'Сессия завершена. Войдите снова.', connection: 'Не удалось подключиться. Попробуйте ещё раз.', preview: 'Просмотр от имени сотрудника', readOnly: 'Только просмотр: действия сотрудника недоступны.', hr: 'HR-аналитика', account: 'Личная учётная запись', noEmployees: 'Сотрудники пока не добавлены.', language: 'Язык интерфейса', hrAccount: 'Учётная запись HR' },
  kk: { menu: 'Мәзір', close: 'Мәзірді жабу', logout: 'Шығу', exiting: 'Шығуда…', checking: 'Кіруді тексеру…', expired: 'Сессия аяқталды. Қайта кіріңіз.', connection: 'Қосылу мүмкін болмады. Қайта көріңіз.', preview: 'Қызметкер атынан қарау', readOnly: 'Тек қарау: қызметкер әрекеттері қолжетімсіз.', hr: 'HR-талдау', account: 'Жеке тіркелгі', noEmployees: 'Қызметкерлер әлі қосылмаған.', language: 'Интерфейс тілі', hrAccount: 'HR тіркелгісі' },
  en: { menu: 'Menu', close: 'Close menu', logout: 'Sign out', exiting: 'Signing out…', checking: 'Checking session…', expired: 'Your session has ended. Please sign in again.', connection: 'Could not connect. Please try again.', preview: 'Employee preview', readOnly: 'Read-only: employee actions are unavailable.', hr: 'HR analytics', account: 'Personal account', noEmployees: 'No employees have been added yet.', language: 'Interface language', hrAccount: 'HR account' },
}

export default function App() {
  const { t, lang, setLang } = useI18n()
  const c = cityCopy[lang], words = copy[lang]
  const [session, setSession] = useState<AuthSession | null>(null)
  const [sessionError, setSessionError] = useState(false)
  const [expired, setExpired] = useState(false)
  const [authBusy, setAuthBusy] = useState(false)
  const [page, setPage] = useState<Page>(readPage)
  const [query, setQuery] = useState('')
  const [ready, setReady] = useState(false)
  const [listError, setListError] = useState(false)
  const [employees, setEmployees] = useState<EmployeeListItem[]>([])
  const [previewId, setPreviewId] = useState('')
  const [toast, setToast] = useState<string | null>(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const [theme, setTheme] = useState<Theme>(() => readStored('cq_theme') === 'dark' ? 'dark' : 'light')
  const mounted = useRef(false), authLock = useRef(false)
  const authVersion = useRef(0), workspaceVersion = useRef(0)
  const menuTrigger = useRef<HTMLElement | null>(null)
  const drawer = useRef<HTMLDivElement>(null)
  const isHr = !!session?.authenticated && session.role === 'hr'
  const employeeId = session?.authenticated ? isHr ? previewId : session.employee_id ?? '' : ''
  const currentPage: Page = page === 'hr' && !isHr ? 'home' : page
  const selected = employees.find((employee) => employee.employee_id === employeeId)

  const onUnauthorized = useCallback(() => {
    authVersion.current += 1; workspaceVersion.current += 1
    setSessionTransport(null)
    setSession({ authenticated: false }); setReady(false); setEmployees([]); setPreviewId('')
    setMenuOpen(false); setExpired(true); setToast(null); setQuery('')
  }, [])
  const checkSession = useCallback(async () => {
    const version = ++authVersion.current
    setSessionError(false)
    try {
      const result = await authApi.session()
      if (mounted.current && version === authVersion.current) {
        setSessionTransport(result.authenticated ? result.csrf_token : null, result.authenticated && result.role === 'hr')
        setSession(result)
      }
    }
    catch { if (mounted.current && version === authVersion.current) setSessionError(true) }
  }, [])
  useEffect(() => {
    mounted.current = true
    if (/^\/(?:employee|hr)(?:\/|$)/.test(location.pathname)) history.replaceState(null, '', `/${location.search}${location.hash}`)
    void checkSession()
    window.addEventListener(SESSION_EXPIRED_EVENT, onUnauthorized)
    return () => { mounted.current = false; authVersion.current += 1; workspaceVersion.current += 1; window.removeEventListener(SESSION_EXPIRED_EVENT, onUnauthorized) }
  }, [checkSession, onUnauthorized])
  useEffect(() => {
    document.documentElement.dataset.theme = theme; document.documentElement.lang = lang; document.title = 'Career City'
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#171b20' : '#f5f7f6')
    writeStored('cq_theme', theme)
  }, [theme, lang])
  useEffect(() => {
    const update = () => { setPage(readPage()); setMenuOpen(false); if (readPage() !== 'recommendations') setQuery(''); window.scrollTo({ top: 0 }) }
    window.addEventListener('hashchange', update)
    return () => window.removeEventListener('hashchange', update)
  }, [])
  useEffect(() => {
    if (session?.authenticated && session.role === 'employee' && page === 'hr') {
      history.replaceState(null, '', `${location.pathname}${location.search}#/home`); setPage('home')
    }
  }, [session, page])
  useEffect(() => {
    if (!session?.authenticated) return
    const expiry = Date.parse(session.expires_at)
    if (!Number.isFinite(expiry)) return
    const timeout = window.setTimeout(onUnauthorized, Math.max(0, Math.min(2_147_483_647, expiry - Date.now())))
    return () => clearTimeout(timeout)
  }, [session, onUnauthorized])
  const loadWorkspace = useCallback(async () => {
    if (!session?.authenticated) return
    const version = ++workspaceVersion.current
    setListError(false)
    try {
      const [catalog, list] = await Promise.all([api.catalog(), api.employees()])
      if (!mounted.current || version !== workspaceVersion.current) return
      setCatalog(catalog); setEmployees(list)
      if (session.role === 'hr') {
        const saved = readStored(`cq_hr_preview_${session.username}`)
        setPreviewId((previous) => list.some((employee) => employee.employee_id === previous) ? previous : list.find((employee) => employee.employee_id === saved)?.employee_id ?? list[0]?.employee_id ?? '')
      }
      setReady(true)
    } catch { if (mounted.current && version === workspaceVersion.current) setListError(true) }
  }, [session])
  useEffect(() => { setReady(false); if (session?.authenticated) void loadWorkspace() }, [session, loadWorkspace])
  useEffect(() => { if (!toast) return; const timeout = setTimeout(() => setToast(null), 5000); return () => clearTimeout(timeout) }, [toast])
  useEffect(() => {
    if (!menuOpen) return
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'; drawer.current?.querySelector<HTMLButtonElement>('button')?.focus()
    const trigger = menuTrigger.current
    return () => { document.body.style.overflow = overflow; if (trigger?.isConnected) trigger.focus() }
  }, [menuOpen])

  async function login(username: string, password: string) {
    if (authLock.current) return
    authLock.current = true; setAuthBusy(true); setExpired(false)
    const version = ++authVersion.current
    try {
      const result = await authApi.login(username, password)
      if (!result.authenticated) throw new ApiError('Authentication failed', 401)
      if (mounted.current && version === authVersion.current) { setSessionTransport(result.csrf_token, result.role === 'hr'); setSession(result); setQuery(''); setSessionError(false) }
    } finally { authLock.current = false; if (mounted.current) setAuthBusy(false) }
  }
  async function logout() {
    if (authLock.current) return
    authLock.current = true; setAuthBusy(true)
    try { await authApi.logout(); onUnauthorized(); setExpired(false) }
    catch (error) { if (error instanceof ApiError && error.status === 401) { onUnauthorized(); setExpired(false) } else setToast(`⚠ ${words.connection}`) }
    finally { authLock.current = false; if (mounted.current) setAuthBusy(false) }
  }
  function navigate(next: Page) {
    if (next === 'hr' && !isHr) return
    if (next !== 'recommendations') setQuery('')
    if (next !== currentPage) location.hash = `/${next}`
    setMenuOpen(false); window.scrollTo({ top: 0 })
  }
  function selectEmployee(id: string) {
    if (!session?.authenticated || session.role !== 'hr' || !employees.some((employee) => employee.employee_id === id)) return
    setPreviewId(id); writeStored(`cq_hr_preview_${session.username}`, id)
    if (currentPage === 'hr') navigate('home')
  }
  function drawerKeys(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape') { event.preventDefault(); setMenuOpen(false); return }
    if (event.key !== 'Tab') return
    const controls = drawer.current?.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],[tabindex="0"]')
    if (!controls?.length) return
    const first = controls[0], last = controls[controls.length - 1]
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
  }
  const toggleTheme = () => setTheme((previous) => previous === 'light' ? 'dark' : 'light')
  const languageControls = <div className="lang" role="group" aria-label={words.language}>{(['kk', 'ru', 'en'] as Lang[]).map((value) => <button key={value} className={lang === value ? 'active' : ''} aria-pressed={lang === value} onClick={() => setLang(value)}>{value === 'kk' ? 'KZ' : value}</button>)}</div>
  const themeControl = <button className="icon-btn" onClick={toggleTheme} aria-label={c.theme}><Icon name={theme === 'dark' ? 'sun' : 'moon'} /></button>
  if (!session) return <div className="session-check"><BrandLogo /><div className="card state" role="status">{sessionError ? <><p>{words.connection}</p><button className="btn" onClick={() => void checkSession()}>{t('retry')}</button></> : words.checking}</div></div>
  if (!session.authenticated) return <><LoginPage onLogin={login} loading={authBusy} theme={theme} onToggleTheme={toggleTheme} />{expired && <div className="toast" role="status"><Icon name="clock" />{words.expired}</div>}</>

  const items: NavItem[] = [
    { page: 'home', icon: 'home', label: c.home }, { page: 'learning', icon: 'book', label: c.learning }, { page: 'city', icon: 'city', label: c.city },
    { page: 'collaboration', icon: 'people', label: c.collaboration }, { page: 'recommendations', icon: 'spark', label: c.recommendations },
    { page: 'skills', icon: 'shield', label: c.skills }, { page: 'achievements', icon: 'trophy', label: c.achievements },
    ...(isHr ? [{ page: 'hr' as const, icon: 'chart' as const, label: words.hr }] : []),
  ]
  const menuButton = (bottom = false) => <button className={bottom ? (!['home', 'learning', 'city'].includes(currentPage) ? 'active' : '') : 'icon-btn workspace-menu-trigger'} aria-label={words.menu} aria-haspopup="dialog" aria-expanded={menuOpen} aria-controls={menuOpen ? 'workspace-menu' : undefined} onClick={(event) => { menuTrigger.current = event.currentTarget; setMenuOpen(true) }}><Icon name="menu" size={bottom ? 20 : 21} />{bottom && c.more}</button>
  return <>
    <a className="skip-link" href="#workspace" onClick={(event) => { event.preventDefault(); document.getElementById('workspace')?.focus() }}>{c.navigation}</a>
    <aside className="sidebar"><a className="halyk-brand" aria-label="HalykBank Career City" href="#/home" onClick={(event) => { event.preventDefault(); navigate('home') }}><BrandLogo /></a><nav className="side-nav" aria-label={c.navigation}>{items.map((item) => <button key={item.page} className={currentPage === item.page ? 'active' : ''} aria-current={currentPage === item.page ? 'page' : undefined} onClick={() => navigate(item.page)}><Icon name={item.icon} size={21} />{item.label}</button>)}</nav><div className="sidebar-settings">{languageControls}{themeControl}</div></aside>
    <header className="workspace-header"><label className="global-search"><Icon name="search" size={21} /><input aria-label={c.search} placeholder={c.search} value={query} onKeyDown={(event) => { if (event.key === 'Enter') navigate('recommendations') }} onChange={(event) => { setQuery(event.target.value); if (currentPage !== 'recommendations') navigate('recommendations') }} />{query && <button className="search-clear" onClick={() => setQuery('')} aria-label={c.clear}><Icon name="close" size={16} /></button>}</label><div className="workspace-account-controls"><div className="header-profile">{isHr ? <EmployeePicker employees={employees} selectedId={employeeId} onSelect={selectEmployee} preview /> : <div className="own-profile" aria-label={words.account}><span className="picker-avatar" aria-hidden="true">{initials(selected?.full_name ?? employeeId)}</span><span className="picker-copy"><span className="picker-name">{selected?.full_name ?? session.username}</span><span className="picker-role">{selected?.role ?? employeeId}</span></span></div>}</div>{menuButton()}</div></header>
    <div className="mobile-settings"><a className="mobile-brand" href="#/home" aria-label="HalykBank Career City" onClick={(event) => { event.preventDefault(); navigate('home') }}><BrandLogo compact /></a>{languageControls}{themeControl}</div>
    <main id="workspace" tabIndex={-1} className={currentPage === 'home' ? 'home-main' : 'page-main'}>
      {isHr && currentPage !== 'hr' && ready && employeeId && <aside className="employee-preview-banner"><Icon name="shield" size={19} /><div><strong>{words.preview} · {selected?.full_name ?? employeeId}</strong><p>{words.readOnly}</p></div><button className="text-button" onClick={() => navigate('hr')}>{words.hr}<Icon name="arrow" size={15} /></button></aside>}
      {listError ? <div className="card state error"><p>{t('error_backend')}</p><button className="btn" onClick={() => void loadWorkspace()}>{t('retry')}</button></div> : !ready ? <div className="skeleton" /> : currentPage === 'hr' && isHr ? <HrPage onUnauthorized={onUnauthorized} /> : !employeeId ? <div className="card state"><p>{words.noEmployees}</p></div> : <PreviewContext.Provider value={isHr}><EmployeePage key={`${session.username}:${employeeId}`} employeeId={employeeId} onToast={setToast} query={query} page={currentPage === 'hr' ? 'home' : currentPage} navigate={navigate} /></PreviewContext.Provider>}
    </main>
    <nav className="bottom-nav" aria-label={c.navigation}>{items.slice(0, 3).map((item) => <button key={item.page} className={currentPage === item.page ? 'active' : ''} aria-current={currentPage === item.page ? 'page' : undefined} onClick={() => navigate(item.page)}><Icon name={item.icon} size={20} />{item.label}</button>)}{menuButton(true)}</nav>
    {menuOpen && createPortal(<div className="workspace-drawer-backdrop" onClick={(event) => { if (event.target === event.currentTarget) setMenuOpen(false) }}><div className="workspace-drawer" ref={drawer} id="workspace-menu" role="dialog" aria-modal="true" aria-labelledby="workspace-menu-title" onKeyDown={drawerKeys}><header><h2 id="workspace-menu-title">{words.menu}</h2><button className="icon-btn" aria-label={words.close} onClick={() => setMenuOpen(false)}><Icon name="close" /></button></header><div className="workspace-drawer-account"><strong>{session.username}</strong><span>{isHr ? words.hrAccount : words.account}</span></div><nav aria-label={c.navigation}>{items.map((item) => <button key={item.page} className={currentPage === item.page ? 'active' : ''} aria-current={currentPage === item.page ? 'page' : undefined} onClick={() => navigate(item.page)}><Icon name={item.icon} size={20} />{item.label}</button>)}</nav><button className="workspace-logout" disabled={authBusy} onClick={() => void logout()}><Icon name="logout" size={19} />{authBusy ? words.exiting : words.logout}</button></div></div>, document.body)}
    {toast && <div className="toast" role="status"><Icon name={toast.startsWith('⚠') ? 'bell' : 'check'} />{toast.replace(/^⚠\s*/, '')}</div>}
  </>
}
