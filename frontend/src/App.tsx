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
    if (next !== 'recommendations') setQuery('')
    if (next !== page) location.hash = `/${next}`
    window.scrollTo({ top: 0 })
  }
  useEffect(() => {
    const update = () => { const next = readPage(); setPage(next); if (next !== 'recommendations') setQuery(''); window.scrollTo({ top: 0 }) }
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
      <a className="skip-link" href="#workspace" onClick={(event) => { event.preventDefault(); document.getElementById('workspace')?.focus() }}>{c.navigation}</a>
      <aside className="sidebar">
        <a className="halyk-brand" aria-label="Career City" href="#" onClick={(e) => { e.preventDefault(); navigate('home') }}>
          <img className="product-logo" src="/brand/career-city-logo.png" alt="" /><span className="brand-wordmark">Career <b>City</b></span>
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
          <button aria-current={page === 'hr' ? 'page' : undefined} className={page === 'hr' ? 'active' : ''} onClick={() => navigate('hr')}><Icon name="chart" size={21} />{t('nav_hr')}</button>
        </nav>
        <div className="sidebar-partner"><span>{c.partner}</span><img src="/images/halyk-bank-logo.png" alt="Halyk Bank" /></div>
        <div className="sidebar-settings">
          <div className="lang" role="group" aria-label="Language">
            {(['kk', 'ru', 'en'] as Lang[]).map((l) => <button key={l} className={lang === l ? 'active' : ''} aria-pressed={lang === l} onClick={() => setLang(l)}>{l === 'kk' ? 'KZ' : l}</button>)}
          </div>
          <button className="icon-btn" onClick={toggleTheme} aria-label={c.theme}><Icon name={theme === 'dark' ? 'sun' : 'moon'} /></button>
        </div>
      </aside>
      <header className="workspace-header">
        <label className="global-search"><Icon name="search" size={21} /><input onKeyDown={(e) => { if (e.key === 'Enter') navigate('recommendations') }} aria-label={c.search} placeholder={c.search} value={query} onChange={(e) => { setQuery(e.target.value); if (page !== 'recommendations') navigate('recommendations') }} />{query && <button className="search-clear" onClick={() => setQuery('')} aria-label={c.clear}><Icon name="close" size={16} /></button>}</label>
        <div className="header-profile">
          {listError ? <span className="hero-sub">{t('error_backend')}</span> : <EmployeePicker employees={employees} selectedId={employeeId} onSelect={selectEmployee} />}
        </div>
      </header>

      <div className="mobile-settings">
        <a className="mobile-brand" href="#/home" aria-label="Career City"><img className="product-logo" src="/brand/career-city-logo.png" alt="" /><span className="brand-wordmark">Career <b>City</b></span></a>
        <div className="lang" role="group" aria-label="Language">{(['kk', 'ru', 'en'] as Lang[]).map((l) => <button key={l} className={lang === l ? 'active' : ''} aria-pressed={lang === l} onClick={() => setLang(l)}>{l === 'kk' ? 'KZ' : l}</button>)}</div>
        <button className="icon-btn" onClick={toggleTheme} aria-label={c.theme}><Icon name={theme === 'dark' ? 'sun' : 'moon'} /></button>
      </div>
      <main id="workspace" tabIndex={-1} className={page === 'home' ? 'home-main' : 'page-main'}>
        {listError ? <div className="card state error"><p>{t('error_backend')}</p><button className="btn" onClick={loadWorkspace}>{t('retry')}</button></div> : !ready ? <div className="skeleton" /> : page === 'hr' ? <HrPage /> :
          <EmployeePage key={employeeId} employeeId={employeeId} onToast={setToast} query={query} page={page} navigate={navigate} />}
      </main>
      <nav className="bottom-nav" aria-label={c.navigation}>
        {([['home', 'home', c.home], ['learning', 'book', c.learning], ['city', 'city', c.city]] as const).map(([id, icon, label]) => <button key={id} aria-current={page === id ? 'page' : undefined} className={page === id ? 'active' : ''} onClick={() => navigate(id)}><Icon name={icon} size={20} />{label}</button>)}
        <label className={`mobile-menu ${!['home', 'learning', 'city'].includes(page) ? 'active' : ''}`}><Icon name="route" size={20} /><span>{c.more}</span><select aria-label={c.navigation} value={page} onChange={(e) => navigate(e.target.value as Page)}>{(['home', 'learning', 'city', 'recommendations', 'skills', 'achievements', 'hr'] as Page[]).map((id) => <option key={id} value={id}>{id === 'hr' ? t('nav_hr') : c[id]}</option>)}</select></label>
      </nav>

      {toast && (
        <div className="toast" role="status">
          <Icon name={toast.startsWith('⚠') ? 'bell' : 'check'} /> {toast.replace(/^⚠\s*/, '')}
        </div>
      )}
    </>
  )
}
