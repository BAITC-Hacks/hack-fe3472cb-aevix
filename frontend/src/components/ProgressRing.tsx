import { useId } from 'react'

export function ProgressRing({ value, caption, size = 120 }: { value: number; caption: string; size?: number }) {
  const gradientId = useId()
  const stroke = 11
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const pct = Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0
  return (
    <div className="ring" role="progressbar" aria-label={caption} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pct)} style={{ width: `var(--ring-size, ${size}px)`, height: `var(--ring-size, ${size}px)` }}>
      <svg width="100%" height="100%" viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--primary)" />
            <stop offset="100%" stopColor="var(--primary-2)" />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--surface-2)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct / 100)}
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
      </svg>
      <div className="ring-label">
        <div>
          <div className="ring-value">{Math.round(pct)}%</div>
          <div className="ring-caption">{caption}</div>
        </div>
      </div>
    </div>
  )
}
