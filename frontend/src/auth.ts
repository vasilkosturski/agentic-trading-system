/**
 * JWT authentication utilities for frontend.
 * Handles login, logout, token storage, and authentication status.
 *
 * SECURITY NOTE: This implementation stores JWT tokens in localStorage, which is
 * vulnerable to XSS (Cross-Site Scripting) attacks. This is an accepted trade-off for:
 * - Simplicity of implementation
 * - No additional backend complexity (httpOnly cookies require CSRF protection)
 * - Admin-only functionality (limited user base, trusted environment)
 *
 * MITIGATIONS IN PLACE:
 * - React auto-escapes all rendered content (prevents XSS injection)
 * - No dangerouslySetInnerHTML usage in the codebase
 * - Tokens expire after 1 hour (configurable on backend)
 * - HTTPS required in production (prevents token interception)
 *
 * ALTERNATIVE APPROACHES (for higher security requirements):
 * 1. Use httpOnly cookies (requires backend CSRF protection)
 * 2. Implement Content Security Policy (CSP) headers
 * 3. Add frontend token expiration validation before API calls
 * 4. Use secure token refresh mechanism (short-lived access token + refresh token)
 */

const TOKEN_KEY = 'jwt_token'

export interface LoginResponse {
  token: string
  username: string
}

/**
 * Login with username and password.
 * Stores JWT token in localStorage on success.
 *
 * @param username - admin username
 * @param password - admin password
 * @returns username on success
 * @throws Error if login fails
 */
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

/**
 * Logout by removing JWT token from localStorage.
 */
export function logout(): void {
  localStorage.removeItem(TOKEN_KEY)
}

/**
 * Get JWT token from localStorage.
 *
 * @returns JWT token or null if not authenticated
 */
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

/**
 * Check if user is authenticated (has valid token in localStorage).
 *
 * @returns true if token exists
 */
export function isAuthenticated(): boolean {
  return getToken() !== null
}
