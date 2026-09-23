import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import { createPortal } from 'react-dom'
import type { EmployeeListItem } from '../api'
import { useI18n } from '../i18n'
import { Icon } from './Icon'

export const initials = (name: string) =>
  name
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

interface Props {
  employees: EmployeeListItem[]
  selectedId: string
  onSelect: (id: string) => void
  preview?: boolean
}

export function EmployeePicker({ employees, selectedId, onSelect, preview = false }: Props) {
  const { t, lang } = useI18n()
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const dialogId = useId()
  const titleId = useId()
  const selected = employees.find((e) => e.employee_id === selectedId)
  const previewLabel = { ru: 'Просмотр сотрудника', kk: 'Қызметкерді қарау', en: 'Employee preview' }[lang]
  const copy = {
    ru: { title: 'Выберите сотрудника', close: 'Закрыть', empty: 'Никого не нашли. Попробуйте другое имя или роль.', found: 'Найдено', more: 'Показаны первые 200. Уточните поиск.', choose: 'Выбрать сотрудника' },
    kk: { title: 'Қызметкерді таңдаңыз', close: 'Жабу', empty: 'Ешкім табылмады. Басқа ат немесе рөлді іздеңіз.', found: 'Табылды', more: 'Алғашқы 200 көрсетілген. Іздеуді нақтылаңыз.', choose: 'Қызметкерді таңдау' },
    en: { title: 'Choose an employee', close: 'Close', empty: 'No employees found. Try another name or role.', found: 'Results', more: 'Showing the first 200. Refine your search.', choose: 'Choose employee' },
  }[lang]

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return employees
    return employees.filter((e) =>
      [e.full_name, e.employee_id, e.role, e.grade, e.department].some((v) => (v ?? '').toLowerCase().includes(s)),
    )
  }, [employees, q])

  useEffect(() => {
    if (!open) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    inputRef.current?.focus()
    const trigger = triggerRef.current
    return () => {
      document.body.style.overflow = previousOverflow
      trigger?.focus()
    }
  }, [open])

  function handleDialogKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape') {
      event.preventDefault()
      setOpen(false)
      return
    }
    if (event.key !== 'Tab') return
    const focusable = dialogRef.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), [tabindex="0"]')
    if (!focusable?.length) return
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className="picker-btn"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? dialogId : undefined}
        aria-label={`${preview ? previewLabel : copy.choose}${selected ? `: ${selected.full_name}` : ''}`}
        onClick={() => { setQ(''); setOpen(true) }}
      >
        <span className="picker-avatar" aria-hidden="true">{selected ? initials(selected.full_name) : <Icon name="people" />}</span>
        <span className="picker-copy">
          <span className="picker-name">{selected?.full_name ?? t('pick_employee')}</span>
          <span className="picker-role">{preview ? previewLabel : selected ? `${selected.role} · ${selected.grade}` : copy.choose}</span>
        </span>
        <Icon name="chevron" />
      </button>

      {open && createPortal(
        <div className="sheet-backdrop" onClick={(event) => { if (event.target === event.currentTarget) setOpen(false) }}>
          <div ref={dialogRef} id={dialogId} className="sheet" role="dialog" aria-modal="true" aria-labelledby={titleId} onKeyDown={handleDialogKeyDown}>
            <div className="sheet-heading">
              <h2 id={titleId}>{copy.title}</h2>
              <button type="button" className="sheet-close" aria-label={copy.close} onClick={() => setOpen(false)}><Icon name="close" size={20} /></button>
            </div>
            <div className="sheet-search">
              <div className="sheet-search-field">
                <Icon name="search" />
                <input ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)} placeholder={t('search')} aria-label={t('search')} autoComplete="off" />
              </div>
              <p className="sheet-count" role="status">{copy.found}: {filtered.length}{filtered.length > 200 ? ` · ${copy.more}` : ''}</p>
            </div>
            <div className="sheet-list">
              {filtered.slice(0, 200).map((e) => (
                <button
                  key={e.employee_id}
                  type="button"
                  className={`sheet-item ${e.employee_id === selectedId ? 'active' : ''}`}
                  aria-current={e.employee_id === selectedId ? 'true' : undefined}
                  onClick={() => {
                    onSelect(e.employee_id)
                    setOpen(false)
                    setQ('')
                  }}
                >
                  <span className="mini-avatar" aria-hidden="true">{initials(e.full_name)}</span>
                  <span className="sheet-item-copy">
                    <span className="name">{e.full_name}</span>
                    <span className="sub">{e.role} · {e.grade}</span>
                    <span className="sub">{e.department} · {e.employee_id}</span>
                  </span>
                  {e.employee_id === selectedId && <Icon name="check" size={18} />}
                </button>
              ))}
              {filtered.length === 0 && <div className="state">{copy.empty}</div>}
            </div>
          </div>
        </div>,
        document.body,
      )}
    </>
  )
}
