let csrfToken: string | null = null
let previewOnly = false

export const SESSION_EXPIRED_EVENT = 'cq:session-expired'

export function setSessionTransport(token: string | null, readOnly = false) {
  csrfToken = token
  previewOnly = readOnly
}

export const isPreviewOnly = () => previewOnly

export function sessionHeaders(init?: RequestInit) {
  const headers = new Headers(init?.headers)
  const method = (init?.method ?? 'GET').toUpperCase()
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method) && csrfToken) headers.set('X-CSRF-Token', csrfToken)
  return headers
}

export function sessionExpired() {
  setSessionTransport(null)
  window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT))
}
