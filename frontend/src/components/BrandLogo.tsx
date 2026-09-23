import { useId } from 'react'

/** Keep the supplied wordmark intact; the small-screen mark is drawn as vectors. */
export function BrandLogo({ compact = false }: { compact?: boolean }) {
  const maskId = useId()
  return compact ? (
    <svg className="brand-mark" viewBox="60 128 666 574" aria-hidden="true" focusable="false">
      <path className="brand-mark-gold" d="M109 146h113c13 0 22 3 33 15l119 125H145c-42 0-70-29-70-69v-38c0-21 13-33 34-33Z" />
      <path className="brand-mark-green" d="M447 143h214c32 0 50 20 50 49v434c0 32-18 48-50 48h-73c-33 0-54-20-54-52V394L248 677c-20 19-40 15-57-2l-72-72c-18-18-15-38 2-56l279-269v-85c0-32 15-50 47-50Z" />
    </svg>
  ) : (
    <svg className="brand-lockup" viewBox="60 128 1844 574" aria-hidden="true" focusable="false">
      <defs>
        <mask id={maskId} maskUnits="userSpaceOnUse" x="0" y="0" width="1942" height="809" style={{ maskType: 'alpha' }}>
          <image href="/brand/halyk-career-city.png" width="1942" height="809" />
        </mask>
      </defs>
      <image className="brand-lockup-light" href="/brand/halyk-career-city.png" width="1942" height="809" />
      <g className="brand-lockup-dark" mask={`url(#${maskId})`}>
        <rect width="1942" height="809" fill="#83cbb6" />
        <path d="M60 128h330v162H60zM1357 250h545v185h-545z" fill="#f2bb4a" />
      </g>
    </svg>
  )
}
