import { useState } from 'react'
import type { CityProgress } from '../api'
import { useI18n, type Lang } from '../i18n'
import { Icon } from './Icon'

export const CITY_LEVEL_COUNT = 10
const levelNames: Record<Lang, string[]> = {
  ru: ['Пустой участок', 'Первое здание', 'Небольшой квартал', 'Растущий район', 'Малый город', 'Развивающийся город', 'Современный город', 'Динамичный мегаполис', 'Процветающий город', 'Город будущего'],
  kk: ['Бос алаң', 'Алғашқы ғимарат', 'Шағын квартал', 'Өсіп келе жатқан аудан', 'Шағын қала', 'Дамып келе жатқан қала', 'Заманауи қала', 'Қарқынды мегаполис', 'Гүлденген қала', 'Болашақ қаласы'],
  en: ['Empty plot', 'First building', 'Small quarter', 'Growing district', 'Small city', 'Developing city', 'Modern city', 'Dynamic metropolis', 'Thriving city', 'City of the future'],
}
export const cityLevelCopy = {
  ru: { level: 'Уровень', growth: 'Рост города', nextProgress: 'До следующего уровня', completed: 'Занятий завершено', rule: 'Каждые 2 новых завершённых занятия повышают уровень.', next: 'Ещё новых занятий до следующего уровня', maximum: 'Город будущего построен!', earned: 'Текущий уровень', preview: 'Предпросмотр', restore: 'Вернуться к моему городу', gallery: 'Все 10 уровней', available: 'Уровень достигнут', locked: 'Ещё впереди' },
  kk: { level: 'Деңгей', growth: 'Қаланың дамуы', nextProgress: 'Келесі деңгейге дейін', completed: 'Аяқталған сабақтар', rule: 'Әр 2 жаңа аяқталған сабақ қала деңгейін көтереді.', next: 'Келесі деңгейге дейінгі жаңа сабақтар', maximum: 'Болашақ қаласы салынды!', earned: 'Қазіргі деңгей', preview: 'Алдын ала қарау', restore: 'Менің қалама оралу', gallery: 'Барлық 10 деңгей', available: 'Деңгейге жеттіңіз', locked: 'Әлі алда' },
  en: { level: 'Level', growth: 'City growth', nextProgress: 'To the next level', completed: 'Activities completed', rule: 'Every 2 new completed activities unlock a city level.', next: 'New activities until the next level', maximum: 'Your city of the future is complete!', earned: 'Current level', preview: 'Preview', restore: 'Back to my city', gallery: 'All 10 levels', available: 'Level reached', locked: 'Still ahead' },
}

// The light sprite sheet contains ten aligned city stages and is fetched once.
export function CityLevelArtwork({ level, label }: { level: number; label: string }) {
  const safeLevel = Number.isFinite(level) ? Math.max(1, Math.min(CITY_LEVEL_COUNT, Math.floor(level))) : 1
  const column = (safeLevel - 1) % 5
  const secondRow = safeLevel > 5
  const sourceX = 18 + column * 300
  const sourceY = secondRow ? 488 : 98
  const sourceHeight = secondRow ? 326 : 260
  return <svg className="city-level-art" viewBox="0 0 300 326" role="img" aria-label={label} data-city-art-level={safeLevel}>
    <svg x="0" y={326 - sourceHeight} width="300" height={sourceHeight} viewBox={`${sourceX} ${sourceY} 300 ${sourceHeight}`} overflow="hidden" aria-hidden="true">
      <image href="/images/city-levels/city-levels-light.png" width="1536" height="1024" />
    </svg>
  </svg>
}

export function CityEvolution({ progress }: { progress: CityProgress }) {
  const { lang } = useI18n()
  const c = cityLevelCopy[lang]
  const [previewLevel, setPreviewLevel] = useState<number | null>(null)
  const level = previewLevel ?? progress.level
  const previewing = level !== progress.level
  const name = levelNames[lang][level - 1]
  const atMaximum = progress.level === progress.max_level
  return <section className="city-evolution" aria-label={c.growth}>
    <div className="city-evolution-scene">
      <div className="city-art-status"><span><Icon name="city" size={16} />{previewing ? c.preview : c.earned}</span><strong>{c.level} {level} / {CITY_LEVEL_COUNT}</strong></div>
      <CityLevelArtwork key={level} level={level} label={`${c.level} ${level}: ${name}`} />
      <div className="city-art-caption" aria-live="polite"><h3>{name}</h3>{previewing ? <><span>{c.earned}: {progress.level}</span><button onClick={() => setPreviewLevel(null)} className="text-button">{c.restore}<Icon name="arrow" size={15} /></button></> : <span>{c.rule}</span>}</div>
    </div>
    <div className="city-level-progress" aria-live="polite">
      <div className="city-growth-stats">
        <div><strong>{progress.completed_courses}</strong><span>{c.completed}</span></div>
        <div><strong>{atMaximum ? progress.max_level : progress.courses_to_next_level}</strong><span>{atMaximum ? c.maximum : c.next}</span></div>
      </div>
      <div className="city-progress-label"><span>{atMaximum ? c.growth : c.nextProgress}</span><strong>{atMaximum ? `${progress.max_level} / ${progress.max_level}` : `${progress.courses_per_level - progress.courses_to_next_level} / ${progress.courses_per_level}`}</strong></div>
      <progress aria-label={atMaximum ? c.growth : c.nextProgress} value={progress.progress_to_next_level} max={100} />
    </div>
    <details className="city-level-gallery">
      <summary>{c.gallery}<Icon name="chevron" size={17} /></summary>
      <div className="city-level-options">{levelNames[lang].map((title, i) => {
        const itemLevel = i + 1
        return <button key={itemLevel} onClick={() => setPreviewLevel(itemLevel === progress.level ? null : itemLevel)} className={`city-level-option ${itemLevel === level ? 'selected' : ''}`} aria-pressed={itemLevel === level} aria-label={`${c.level} ${itemLevel}: ${title}. ${itemLevel <= progress.level ? c.available : c.locked}`}>
          <CityLevelArtwork level={itemLevel} label={`${c.level} ${itemLevel}: ${title}`} />
          <span>{c.level} {itemLevel}{itemLevel === progress.level && <Icon name="flag" size={12} />}{itemLevel < progress.level && <Icon name="check" size={12} />}</span>
          <small>{title}</small>
        </button>
      })}</div>
    </details>
  </section>
}
