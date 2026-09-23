import { ApiError } from './api'
import { sessionHeaders } from './sessionTransport'

export type AuthenticatedSession = { authenticated: true; role: 'hr' | 'employee'; username: string; employee_id: string | null; csrf_token: string; expires_at: string }
export type AuthSession = { authenticated: false } | AuthenticatedSession
const BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')

async function request(path: string, init?: RequestInit): Promise<AuthSession> {
  const response = await fetch(`${BASE}/api/auth${path}`, { ...init, credentials: 'include', cache: 'no-store', headers: sessionHeaders(init) })
  if (!response.ok) throw new ApiError('Authentication failed', response.status)
  const session: AuthSession = await response.json()
  return session
}

export const authApi = {
  session: () => request('/session'),
  login: (username: string, password: string) => request('/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) }),
  logout: () => request('/logout', { method: 'POST' }),
}
