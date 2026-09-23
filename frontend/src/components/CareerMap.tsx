import type { Grade } from '../api'
import { GRADES } from '../catalog'
import { useI18n } from '../i18n'

interface Props {
  role: string
  grade: Grade
  targetRole: string
  targetGrade: Grade
  progress: number
}

export function CareerMap({ role, grade, targetRole, targetGrade, progress }: Props) {
  const { t } = useI18n()
  const cur = GRADES.indexOf(grade)
  const roleChange = targetRole !== role
  // при смене роли цель может быть на том же или более низком грейде — тогда рисуем её отдельно
  const tgt = roleChange ? -1 : GRADES.indexOf(targetGrade)

  // заливка: пройденные сегменты + доля прогресса к цели
  const span = GRADES.length - 1
  const base = cur / span
  const toTarget = tgt > cur ? ((tgt - cur) / span) * (progress / 100) : 0
  const fill = Math.min(1, base + toTarget) * 100

  return (
    <div className="card">
      <h2 className="card-title">
        {t('career_map')}
        <small>{role}</small>
      </h2>
      <div className="track">
        <div className="track-line">
          <div className="track-fill" style={{ width: `${fill}%` }} />
        </div>
        {GRADES.map((g, i) => {
          const cls = i < cur ? 'passed' : i === cur ? 'current' : i === tgt ? 'target' : ''
          return (
            <div key={g} className={`stop ${cls}`}>
              <div className="stop-dot">{i < cur ? '✓' : i + 1}</div>
              <div className="stop-name">{g}</div>
              <div className="stop-tag">{i === cur ? t('you_are_here') : i === tgt ? t('target') : ''}</div>
            </div>
          )
        })}
      </div>
      {roleChange && (
        <div className="role-switch">
          {t('target')}: {grade} {role} → {targetGrade} {targetRole} · {Math.round(progress)}%
        </div>
      )}
    </div>
  )
}
