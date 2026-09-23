import { useEffect, useState } from 'react'
import { api, type EmployeeListItem } from './api'
import { EmployeePicker } from './components/EmployeePicker'
import { cityCopy } from './cityCopy'
import { Icon } from './components/Icon'
import { useI18n, type Lang } from './i18n'
import { EmployeePage } from './pages/EmployeePage'
import { HrPage } from './pages/HrPage'

type View = 'me' | 'hr'
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
  const [section, setSection] = useState('home')
  const [query, setQuery] = useState('')
  const navigate = (id: string) => {
    setSection(id)
    setView('me')
    history.replaceState(null, '', '#')
    requestAnimationFrame(() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }
  const [view, setView] = useState<View>(() => (location.hash === '#hr' ? 'hr' : 'me'))
  const [employees, setEmployees] = useState<EmployeeListItem[]>([])
  const [employeeId, setEmployeeId] = useState(() => readStored('cq_employee') ?? 'E0002')
  const [listError, setListError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = readStored('cq_theme')
    if (saved === 'light' || saved === 'dark') return saved
    return 'light'
  })

  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  useEffect(() => {
    document.documentElement.lang = lang
  }, [lang])

  useEffect(() => {
    api.employees().then(setEmployees, (e: Error) => setListError(e.message))
  }, [])

  useEffect(() => {
    if (!toast) return
    const id = setTimeout(() => setToast(null), 4000)
    return () => clearTimeout(id)
  }, [toast])

  const go = (v: View) => {
    setView(v)
    history.replaceState(null, '', v === 'hr' ? '#hr' : '#')
    window.scrollTo({ top: 0 })
  }

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
          <span className="halyk-mark">✦</span><span>Halyk<small>Бірге өсеміз</small></span>
        </a>
        <nav className="side-nav" aria-label={c.navigation}>
          {([
            ['home', 'home', c.home], ['learning', 'book', c.learning], ['city', 'city', c.city],
            ['recommendations', 'spark', c.recommendations], ['skills', 'shield', c.skills],
            ['achievements', 'trophy', c.achievements],
          ] as const).map(([id, icon, label]) => (
            <button key={id} className={view === 'me' && section === id ? 'active' : ''} onClick={() => navigate(id)}>
              <Icon name={icon} size={21} />{label}
            </button>
          ))}
          <button className={view === 'hr' ? 'active' : ''} onClick={() => go('hr')}><Icon name="chart" size={21} />{t('nav_hr')}</button>
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
        <label className="global-search"><Icon name="search" size={21} /><input aria-label={c.search} placeholder={c.search} value={query} onChange={(e) => { setQuery(e.target.value); if (view !== 'me') go('me') }} /><span>⌕</span></label>
        <div className="header-profile">
          {listError ? <span className="hero-sub">{t('error_backend')}</span> : <EmployeePicker employees={employees} selectedId={employeeId} onSelect={selectEmployee} />}
        </div>
      </header>

      <main>
        {view === 'me' ? (
          <>
            <EmployeePage key={employeeId} employeeId={employeeId} onToast={setToast} query={query} />
          </>
        ) : (
          <HrPage />
        )}
      </main>

      <nav className="bottom-nav">
        <button className={view === 'me' ? 'active' : ''} onClick={() => go('me')}>
          <Icon name="route" size={22} />
          {t('nav_me')}
        </button>
        <button className={view === 'hr' ? 'active' : ''} onClick={() => go('hr')}>
          <Icon name="chart" size={22} />
          {t('nav_hr')}
        </button>
      </nav>

      {toast && (
        <div className="toast" role="status">
          <Icon name="check" /> {toast}
        </div>
      )}
    </>
  )
}
