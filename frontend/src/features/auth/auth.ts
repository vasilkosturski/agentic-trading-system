/**
 * JWT tokens are stored in localStorage — vulnerable to XSS — accepted trade-off
 * given the admin-only surface and the absence of cookie-based CSRF handling.
 * Mitigations: React auto-escaping on all rendered content, no dangerouslySetInnerHTML
 * anywhere in the codebase, 1-hour backend-issued token expiry, HTTPS-only in prod.
 */

const TOKEN_KEY = 'jwt_token'

export interface LoginResponse {
  token: string
  username: string
}

export async function login(username: string, password: string): Promise<string> {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password }),
  })

  if (!response.ok) {
    throw new Error('Login failed')
  }

  const data: LoginResponse = await response.json()
  localStorage.setItem(TOKEN_KEY, data.token)
  return data.username
}

export function logout(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function isAuthenticated(): boolean {
  return getToken() !== null
}
