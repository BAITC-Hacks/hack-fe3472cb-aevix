import { useMemo, useState } from 'react'
import { roleProfile, skillName } from '../catalog'
import { useI18n } from '../i18n'
import { Icon } from './Icon'

interface Props {
  skills: Record<string, number>
  targetRole: string
  targetGrade: string
}

export function SkillGap({ skills, targetRole, targetGrade }: Props) {
  const { t, lang } = useI18n()
  const [onlyGaps, setOnlyGaps] = useState(true)
  const profile = roleProfile(targetRole, targetGrade)
  const copy = {
    ru: {
      target: 'Требования к цели', missing: 'Требования к этой цели пока не заданы',
      missingNote: 'Сравнение навыков появится, когда будет добавлен профиль целевой роли.',
      empty: 'Для этой цели пока нет требований к навыкам',
      covered: 'Все требования к навыкам выполнены', coveredNote: 'Можно посмотреть свои уровни во вкладке «Все навыки».',
      atTarget: 'Требование выполнено', belowTarget: 'Нужно развить', targetLevel: 'Целевой уровень',
    },
    kk: {
      target: 'Мақсат талаптары', missing: 'Бұл мақсаттың талаптары әлі берілмеген',
      missingNote: 'Мақсатты рөлдің профилі қосылғанда дағдыларды салыстыру пайда болады.',
      empty: 'Бұл мақсатқа дағды талаптары әлі жоқ',
      covered: 'Дағдылардың барлық талаптары орындалды', coveredNote: 'Деңгейлеріңізді «Барлық дағдылар» бөлімінен көре аласыз.',
      atTarget: 'Талап орындалды', belowTarget: 'Дамыту қажет', targetLevel: 'Мақсатты деңгей',
    },
    en: {
      target: 'Target requirements', missing: 'Requirements for this goal are not available yet',
      missingNote: 'A skill comparison will appear when the target role profile is added.',
      empty: 'No skill requirements are defined for this goal yet',
      covered: 'All skill requirements are met', coveredNote: 'See your levels under “All skills”.',
      atTarget: 'Requirement met', belowTarget: 'Needs development', targetLevel: 'Target level',
    },
  }[lang]

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
      <div className="card-title">
        <h2>{t('skills_gap')}</h2>
        {rows.length > 0 && <div className="seg" role="group" aria-label={t('skills_gap')}>
          <button className={onlyGaps ? 'active' : ''} aria-pressed={onlyGaps} onClick={() => setOnlyGaps(true)}>
            {t('only_gaps')}
          </button>
          <button className={!onlyGaps ? 'active' : ''} aria-pressed={!onlyGaps} onClick={() => setOnlyGaps(false)}>
            {t('all_skills')}
          </button>
        </div>}
      </div>
      <p className="panel-hint">{copy.target}: {targetGrade} · {targetRole}</p>

      {!profile ? (
        <div className="state"><Icon name="shield" size={28} /><p>{copy.missing}</p><p className="panel-hint">{copy.missingNote}</p></div>
      ) : rows.length === 0 ? (
        <div className="state"><Icon name="shield" size={28} /><p>{copy.empty}</p></div>
      ) : visible.length === 0 ? (
        <div className="state"><Icon name="check" size={28} /><p>{copy.covered}</p><p className="panel-hint">{copy.coveredNote}</p><button className="btn ghost" onClick={() => setOnlyGaps(false)}>{t('all_skills')}</button></div>
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

      {visible.length > 0 && <div className="legend">
        <span>
          <i style={{ background: 'var(--primary)' }} />{copy.atTarget}
        </span>
        <span>
          <i style={{ background: 'color-mix(in srgb, var(--danger) 80%, var(--accent))' }} />{copy.belowTarget}
        </span>
        <span>
          <i style={{ background: 'var(--text)', width: 3 }} />
          {copy.targetLevel}
        </span>
        <span>
          <i style={{ background: 'var(--danger)', borderRadius: '50%' }} />
          {t('critical')}
        </span>
      </div>}
    </div>
  )
}
