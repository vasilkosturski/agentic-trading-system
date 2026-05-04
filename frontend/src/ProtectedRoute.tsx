import type { ReactNode } from 'react'
import { Navigate, useSearchParams, useLocation } from 'react-router-dom'
import { isAuthenticated } from './auth'

interface ProtectedRouteProps {
  children: ReactNode
}

/**
 * Protected route wrapper that redirects to login if not authenticated.
 * Only protects routes when showAll=true query parameter is present.
 * Uses synchronous Navigate to prevent race conditions with API calls.
 * Passes the original URL to login page so user can be redirected back after authentication.
 */
function ProtectedRoute({ children }: ProtectedRouteProps) {
  const [searchParams] = useSearchParams()
  const location = useLocation()
  const showAll = searchParams.get('showAll') === 'true'

  // Check authentication synchronously BEFORE rendering children
  // This prevents the children from making API calls before redirect
  if (showAll && !isAuthenticated()) {
    // Encode the full current URL (path + query string) to return to after login
    const returnUrl = encodeURIComponent(`${location.pathname}${location.search}`)
    return <Navigate to={`/login?returnUrl=${returnUrl}`} replace />
  }

  return <>{children}</>
}

export default ProtectedRoute
