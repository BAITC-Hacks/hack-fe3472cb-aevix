import { useEffect, useState } from 'react'
import { api, type EmployeeListItem } from './api'
import { EmployeePicker } from './components/EmployeePicker'
import { cityCopy } from './cityCopy'
import { Icon } from './components/Icon'
import { useI18n, type Lang } from './i18n'
import { EmployeePage } from './pages/EmployeePage'
import { HrPage } from './pages/HrPage'

import { readPage, type Page } from './routes'
import { setCatalog } from './catalog'
type Theme = 'light' | 'dark'

function readStored(key: string) {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}
function writeStored(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
  } catch {
    /* ignore */
  }
}

export default function App() {
  const { t, lang, setLang } = useI18n()
  const c = cityCopy[lang]
  const [page, setPage] = useState<Page>(readPage)
  const [query, setQuery] = useState('')
  const [ready, setReady] = useState(false)
  const navigate = (next: Page) => {
    if (next !== page) location.hash = `/${next}`
    window.scrollTo({ top: 0 })
  }
  useEffect(() => {
    const update = () => { setPage(readPage()); window.scrollTo({ top: 0 }) }
    window.addEventListener('hashchange', update)
    return () => window.removeEventListener('hashchange', update)
  }, [])
  const [employees, setEmployees] = useState<EmployeeListItem[]>([])
  const [employeeId, setEmployeeId] = useState(() => readStored('cq_employee') ?? 'E0002')
  const [listError, setListError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = readStored('cq_theme')
    if (saved === 'light' || saved === 'dark') return saved
    return 'light'
  })

  const loadWorkspace = () => {
    setListError(null)
    Promise.all([api.catalog(), api.employees()]).then(([catalog, list]) => {
      setCatalog(catalog)
      setEmployees(list)
      if (list.length && !list.some((employee) => employee.employee_id === employeeId)) selectEmployee(list[0].employee_id)
      setReady(true)
    }, (e: Error) => setListError(e.message))
  }

  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  useEffect(() => {
    document.documentElement.lang = lang
  }, [lang])

  useEffect(() => {
    loadWorkspace()
  }, [])

  useEffect(() => {
    if (!toast) return
    const id = setTimeout(() => setToast(null), 4000)
    return () => clearTimeout(id)
  }, [toast])

  const selectEmployee = (id: string) => {
    setEmployeeId(id)
    writeStored('cq_employee', id)
  }

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    writeStored('cq_theme', next)
  }

  return (
    <>
      <aside className="sidebar">
        <a className="halyk-brand" href="#" onClick={(e) => { e.preventDefault(); navigate('home') }}>
          <img className="halyk-logo" src="/images/halyk-bank-logo.png" alt="Halyk Bank" />
        </a>
        <nav className="side-nav" aria-label={c.navigation}>
          {([
            ['home', 'home', c.home], ['learning', 'book', c.learning], ['city', 'city', c.city],
            ['recommendations', 'spark', c.recommendations], ['skills', 'shield', c.skills],
            ['achievements', 'trophy', c.achievements],
          ] as const).map(([id, icon, label]) => (
            <button key={id} aria-current={page === id ? 'page' : undefined} className={page === id ? 'active' : ''} onClick={() => navigate(id)}>
              <Icon name={icon} size={21} />{label}
            </button>
          ))}
          <button className={page === 'hr' ? 'active' : ''} onClick={() => navigate('hr')}><Icon name="chart" size={21} />{t('nav_hr')}</button>
        </nav>
        <div className="sidebar-quote"><Icon name="leaf" size={28} /><p>{c.quote}</p><span>Halyk Bank</span><div className="quote-hills" /></div>
        <div className="sidebar-settings">
          <div className="lang" role="group" aria-label="Language">
            {(['kk', 'ru', 'en'] as Lang[]).map((l) => <button key={l} className={lang === l ? 'active' : ''} onClick={() => setLang(l)}>{l === 'kk' ? 'KZ' : l}</button>)}
          </div>
          <button className="icon-btn" onClick={toggleTheme} aria-label={c.theme}><Icon name={theme === 'dark' ? 'sun' : 'moon'} /></button>
        </div>
      </aside>
      <header className="workspace-header">
        <label className="global-search"><Icon name="search" size={21} /><input onKeyDown={(e) => { if (e.key === 'Enter') navigate('recommendations') }} aria-label={c.search} placeholder={c.search} value={query} onChange={(e) => { setQuery(e.target.value); if (page !== 'recommendations') navigate('recommendations') }} /><span>⌕</span></label>
        <div className="header-profile">
          {listError ? <span className="hero-sub">{t('error_backend')}</span> : <EmployeePicker employees={employees} selectedId={employeeId} onSelect={selectEmployee} />}
        </div>
      </header>

      <div className="mobile-settings">
        <a className="mobile-brand" href="#/home" aria-label="Halyk Bank"><img className="halyk-logo" src="/images/halyk-bank-logo.png" alt="Halyk Bank" /></a>
        <div className="lang" role="group" aria-label="Language">{(['kk', 'ru', 'en'] as Lang[]).map((l) => <button key={l} className={lang === l ? 'active' : ''} onClick={() => setLang(l)}>{l === 'kk' ? 'KZ' : l}</button>)}</div>
        <button className="icon-btn" onClick={toggleTheme} aria-label={c.theme}><Icon name={theme === 'dark' ? 'sun' : 'moon'} /></button>
      </div>
      <main className={page === 'home' ? 'home-main' : 'page-main'}>
        {listError ? <div className="card state error"><p>{t('error_backend')}</p><button className="btn" onClick={loadWorkspace}>{t('retry')}</button></div> : !ready ? <div className="skeleton" /> : page === 'hr' ? <HrPage /> :
          <EmployeePage key={employeeId} employeeId={employeeId} onToast={setToast} query={query} page={page} navigate={navigate} />}
      </main>
      <nav className="bottom-nav" aria-label={c.navigation}>
        {([['home', 'home', c.home], ['learning', 'book', c.learning], ['city', 'city', c.city], ['recommendations', 'spark', c.recommendations], ['skills', 'shield', c.skills], ['achievements', 'trophy', c.achievements], ['hr', 'chart', t('nav_hr')]] as const).map(([id, icon, label]) => <button key={id} aria-current={page === id ? 'page' : undefined} className={page === id ? 'active' : ''} onClick={() => navigate(id)}><Icon name={icon} size={20} />{label}</button>)}
      </nav>

      {toast && (
        <div className="toast" role="status">
          <Icon name="check" /> {toast}
        </div>
      )}
    </>
  )
}
