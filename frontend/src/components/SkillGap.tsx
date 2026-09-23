import { useMemo, useState } from 'react'
import { roleProfile, skillName } from '../catalog'
import { useI18n } from '../i18n'

interface Props {
  skills: Record<string, number>
  targetRole: string
  targetGrade: string
}

export function SkillGap({ skills, targetRole, targetGrade }: Props) {
  const { t } = useI18n()
  const [onlyGaps, setOnlyGaps] = useState(true)
  const profile = roleProfile(targetRole, targetGrade)

  const rows = useMemo(() => {
    if (!profile) return []
    const critical = new Set(profile.critical_skills)
    return Object.entries(profile.required_skills)
      .map(([id, need]) => {
        const have = skills[id] ?? 0
        return { id, need, have, gap: need - have, critical: critical.has(id) }
      })
      .sort((a, b) => Number(b.critical) - Number(a.critical) || b.gap - a.gap || a.id.localeCompare(b.id))
  }, [profile, skills])

  const visible = onlyGaps ? rows.filter((r) => r.gap > 0) : rows

  return (
    <div className="card">
      <h2 className="card-title">
        {t('skills_gap')}
        <div className="seg">
          <button className={onlyGaps ? 'active' : ''} onClick={() => setOnlyGaps(true)}>
            {t('only_gaps')}
          </button>
          <button className={!onlyGaps ? 'active' : ''} onClick={() => setOnlyGaps(false)}>
            {t('all_skills')}
          </button>
        </div>
      </h2>

      {visible.length === 0 ? (
        <div className="state">{t('no_recs')}</div>
      ) : (
        <div className="skills">
          {visible.map((r) => (
            <div key={r.id} className="skill">
              <div className="skill-name">
                {r.critical && <i className="crit" title={t('critical')} />}
                <span>{skillName(r.id)}</span>
              </div>
              <div className={`skill-lvl ${r.gap > 0 ? 'gap' : ''}`}>
                <b>{r.have}</b> / {r.need}
              </div>
              <div className="bar">
                <div className={`bar-fill ${r.gap > 0 ? 'short' : ''}`} style={{ width: `${(Math.min(r.have, 5) / 5) * 100}%` }} />
                <div className="bar-need" style={{ left: `${(r.need / 5) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="legend">
        <span>
          <i style={{ background: 'var(--primary)' }} />≥
        </span>
        <span>
          <i style={{ background: 'color-mix(in srgb, var(--danger) 80%, var(--accent))' }} />&lt;
        </span>
        <span>
          <i style={{ background: 'var(--text)', width: 3 }} />
          {targetGrade}
        </span>
        <span>
          <i style={{ background: 'var(--danger)', borderRadius: '50%' }} />
          {t('critical')}
        </span>
      </div>
    </div>
  )
}
