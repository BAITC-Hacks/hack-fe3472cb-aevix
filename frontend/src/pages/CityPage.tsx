import { CityEvolution } from '../components/CityEvolution'
import type { EmployeeProfile, GameMap, RecommendationsResponse } from '../api'
import type { Page } from '../routes'
import { eventTitle, skillName, roleProfile, eventLabel } from '../catalog'
import { cityCopy } from '../cityCopy'
import { useI18n } from '../i18n'
import { CareerMap } from '../components/CareerMap'
import { Icon, type IconName } from '../components/Icon'
import { ProgressRing } from '../components/ProgressRing'

const districtIcons: Record<string, IconName> = { engineering: 'code', security: 'shield', communication: 'people', leadership: 'flag' }
const names = {
  ru: { engineering: 'Технологии', security: 'Безопасность', communication: 'Коммуникации', leadership: 'Лидерство' },
  kk: { engineering: 'Технологиялар', security: 'Қауіпсіздік', communication: 'Коммуникация', leadership: 'Көшбасшылық' },
  en: { engineering: 'Engineering', security: 'Security', communication: 'Communication', leadership: 'Leadership' },
}
const copy = {
  ru: { readiness: 'Карьерная цель', readinessNote: 'Готовность по навыкам для выбранной роли.', wallet: 'Ваш баланс', walletNote: 'Монеты начисляются за новые завершения обучения. Прошлая история учитывается в уровне города.', learned: 'Уникальных занятий завершено', next: 'Следующий шаг', districtNote: 'Прогресс навыков, которые нужны для вашей цели.', outsideGoal: 'Не входит в текущую цель', selected: 'В вашей подборке', unavailable: 'Требования к этой цели пока не заданы.' },
  kk: { readiness: 'Мансаптық мақсат', readinessNote: 'Таңдалған рөлге қажетті дағдылар бойынша дайындық.', wallet: 'Сіздің балансыңыз', walletNote: 'Монеталар жаңа аяқталған оқу үшін беріледі. Бұрынғы оқу қала деңгейінде ескеріледі.', learned: 'Аяқталған бірегей сабақтар', next: 'Келесі қадам', districtNote: 'Мақсатыңызға қажет дағдылардың прогресі.', outsideGoal: 'Қазіргі мақсатқа кірмейді', selected: 'Сіздің ұсыныстарыңызда', unavailable: 'Бұл мақсаттың талаптары әлі берілмеген.' },
  en: { readiness: 'Career goal', readinessNote: 'Skill readiness for your chosen role.', wallet: 'Your balance', walletNote: 'Coins are earned for new learning completions. Previous learning counts toward your city level.', learned: 'Unique activities completed', next: 'Next step', districtNote: 'Progress in the skills required for your goal.', outsideGoal: 'Outside your current goal', selected: 'In your shortlist', unavailable: 'Requirements for this goal are not available yet.' },
}
export function CityPage({ profile, recs, map, navigate }: { profile: EmployeeProfile; recs: RecommendationsResponse; map: GameMap; navigate: (page: Page) => void }) {
  const { t, lang } = useI18n()
  const c = cityCopy[lang]
  const labels = copy[lang]
  const target = roleProfile(recs.target_role, recs.target_grade)
  const required = target?.required_skills ?? {}
  const hasRequirements = Object.keys(required).length > 0
  const next = recs.recommendations[0]
  return <div className="grid city-page">
    <div className="city-workspace">
      <CityEvolution key={`${map.employee_id}-${map.city_level}`} progress={map.city_progress} />
      <aside className="city-insights">
        <section className="card city-goal-panel"><h2>{labels.readiness}</h2><div className="city-goal-content">{hasRequirements && <ProgressRing value={map.progress_to_next_grade} caption={t('progress')} size={92} />}<div><span className="goal-transition">{profile.grade} <span aria-hidden="true">→</span> {recs.target_grade}</span><h3>{recs.target_role}</h3><p>{hasRequirements ? labels.readinessNote : labels.unavailable}</p></div></div><button className="text-button" onClick={() => navigate('skills')}>{c.openSkills}<Icon name="arrow" size={15} /></button></section>
        <section className="card city-wallet-panel"><div className="city-panel-heading"><h2>{labels.wallet}</h2><span className="metric-icon gold"><Icon name="leaf" size={20} /></span></div><div className="wallet-value">{map.center?.wallet_balance.toLocaleString(lang) ?? '—'}<span>{c.balance.toLowerCase()}</span></div><p className="panel-hint">{labels.walletNote}</p><div className="city-completed"><span>{labels.learned}</span><strong>{map.city_progress.completed_courses}</strong></div></section>
        {next && <section className="card city-next-panel"><span className="eyebrow">{labels.next}</span><h3>{next.quest_title}</h3><p><Icon name="clock" size={13} />{next.duration_hours} {t('hours')}<span>·</span>{eventLabel(next.format, lang)}</p><button className="text-button" onClick={() => navigate('recommendations')}>{c.details}<Icon name="arrow" size={15} /></button></section>}
      </aside>
    </div>
    <CareerMap role={profile.role} grade={profile.grade} targetRole={recs.target_role} targetGrade={recs.target_grade} progress={map.progress_to_next_grade} />
    {!!map.districts?.length && <section><div className="city-section-heading"><h2>{c.districts}</h2><p>{labels.districtNote}</p></div><div className="district-grid">{map.districts.map((district) => {
      const relevantSkills = district.related_skills.filter((id) => id in required)
      const relevant = relevantSkills.length > 0
      return <details className={`card district ${relevant ? '' : 'district-outside'}`} key={district.id}>
        <summary><span className="district-icon"><Icon name={districtIcons[district.id] ?? 'city'} size={24} /></span><span className="district-heading"><strong>{names[lang][district.id as keyof typeof names.ru] ?? district.name}</strong><small>{relevant ? `${district.progress}% · ${labels.selected}: ${district.recommended_event_ids.length}` : labels.outsideGoal}</small></span><Icon name="chevron" size={16} /></summary>
        {relevant && <progress value={district.progress} max={100} aria-label={district.name} />}
        <div className="district-details"><div className="meta">{relevantSkills.map((id) => <span className="chip" key={id}>{skillName(id)}</span>)}</div>{district.recommended_event_ids.length ? <><ul>{district.recommended_event_ids.map((id) => <li key={id}>{eventTitle(id)}</li>)}</ul><button className="text-button" onClick={() => navigate('recommendations')}>{c.explore}<Icon name="arrow" size={16} /></button></> : <p>{relevant ? c.noDistrict : labels.outsideGoal}</p>}</div>
      </details>
    })}</div></section>}
  </div>
}
