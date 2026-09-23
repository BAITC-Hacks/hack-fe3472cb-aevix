export function ProgressRing({ value, caption, size = 120 }: { value: number; caption: string; size?: number }) {
  const stroke = 11
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(100, value))
  return (
    <div className="ring" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <defs>
          <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
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
          stroke="url(#ringGrad)"
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
