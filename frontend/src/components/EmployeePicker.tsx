import { useEffect, useMemo, useRef, useState } from 'react'
import type { EmployeeListItem } from '../api'
import { useI18n } from '../i18n'
import { Icon } from './Icon'

export const initials = (name: string) =>
  name
    .split(/\s+/)
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

interface Props {
  employees: EmployeeListItem[]
  selectedId: string
  onSelect: (id: string) => void
}

export function EmployeePicker({ employees, selectedId, onSelect }: Props) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const selected = employees.find((e) => e.employee_id === selectedId)

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return employees
    return employees.filter((e) =>
      [e.full_name, e.employee_id, e.role, e.grade, e.department].some((v) => v.toLowerCase().includes(s)),
    )
  }, [employees, q])

  useEffect(() => {
    if (!open) return
    inputRef.current?.focus()
    const onKey = (ev: KeyboardEvent) => ev.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  return (
    <>
      <button className="picker-btn" onClick={() => setOpen(true)}>
        <Icon name="search" />
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="label">{t('pick_employee')}</div>
          <div className="value">
            {selected ? `${selected.full_name} · ${selected.employee_id}` : '—'}
          </div>
        </div>
        <Icon name="chevron" />
      </button>

      {open && (
        <div className="sheet-backdrop" onClick={() => setOpen(false)}>
          <div className="sheet" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <div className="sheet-search">
              <input ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)} placeholder={t('search')} />
            </div>
            <div className="sheet-list">
              {filtered.slice(0, 200).map((e) => (
                <button
                  key={e.employee_id}
                  className={`sheet-item ${e.employee_id === selectedId ? 'active' : ''}`}
                  onClick={() => {
                    onSelect(e.employee_id)
                    setOpen(false)
                    setQ('')
                  }}
                >
                  <div className="mini-avatar">{initials(e.full_name)}</div>
                  <div style={{ minWidth: 0 }}>
                    <div className="name">{e.full_name}</div>
                    <div className="sub">
                      {e.employee_id} · {e.grade} {e.role}
                      {e.target ? ` → ${e.target.target_grade} ${e.target.target_role}` : ''}
                    </div>
                  </div>
                </button>
              ))}
              {filtered.length === 0 && <div className="state">—</div>}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
