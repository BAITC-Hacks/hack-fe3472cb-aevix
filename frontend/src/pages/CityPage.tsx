import { CityEvolution } from '../components/CityEvolution'
import type { EmployeeProfile, GameMap, RecommendationsResponse } from '../api'
import type { Page } from '../routes'
import { eventTitle, skillName } from '../catalog'
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
export function CityPage({ profile, recs, map, navigate }: { profile: EmployeeProfile; recs: RecommendationsResponse; map: GameMap; navigate: (page: Page) => void }) {
  const { t, lang } = useI18n()
  const c = cityCopy[lang]
  return <div className="grid">
    <section className="city-overview card city-with-evolution">
      <div className="city-overview-info"><span className="chip primary">{c.level} {map.city_level} / 10</span><h2>{map.city_name ?? 'Career City'}</h2><p>{map.current_zone} <span aria-hidden="true">→</span> {map.target_zone} · {recs.target_role}</p>{map.center && <span className="wallet"><Icon name="leaf" size={18} /><strong>{map.center.wallet_balance.toLocaleString(lang)}</strong> {c.balance.toLowerCase()}</span>}<div className="city-career-progress"><ProgressRing value={map.progress_to_next_grade} caption={t('progress')} /><div><small>{c.target}</small><strong>{recs.target_grade}</strong><span>{t('progress')}</span></div></div></div>
      <CityEvolution key={`${map.employee_id}-${map.city_level}`} progress={map.city_progress} />
    </section>
    <CareerMap role={profile.role} grade={profile.grade} targetRole={recs.target_role} targetGrade={recs.target_grade} progress={map.progress_to_next_grade} />
    {!!map.districts?.length && <section><h2 className="section-title">{c.districts}</h2><div className="district-grid">{map.districts.map((district) => <details className="card district" key={district.id}><summary><span className="district-icon"><Icon name={districtIcons[district.id] ?? 'city'} size={24} /></span><span className="district-heading"><strong>{names[lang][district.id as keyof typeof names.ru] ?? district.name}</strong><small>{district.progress}% · {district.recommended_event_ids.length} {c.available.toLowerCase()}</small></span><Icon name="chevron" size={16} /></summary><progress value={district.progress} max={100} aria-label={district.name} /><div className="district-details"><div className="meta">{district.related_skills.map((id) => <span className="chip" key={id}>{skillName(id)}</span>)}</div>{district.recommended_event_ids.length ? <><ul>{district.recommended_event_ids.map((id) => <li key={id}>{eventTitle(id)}</li>)}</ul><button className="text-button" onClick={() => navigate('recommendations')}>{c.explore}<Icon name="arrow" size={16} /></button></> : <p>{c.noDistrict}</p>}</div></details>)}</div></section>}
  </div>
}
