import { ReactNode } from 'react'
import { Navigate, useSearchParams } from 'react-router-dom'
import { isAuthenticated } from './auth'

interface ProtectedRouteProps {
  children: ReactNode
}

/**
 * Protected route wrapper that redirects to login if not authenticated.
 * Only protects routes when showAll=true query parameter is present.
 * Uses synchronous Navigate to prevent race conditions with API calls.
 */
function ProtectedRoute({ children }: ProtectedRouteProps) {
  const [searchParams] = useSearchParams()
  const showAll = searchParams.get('showAll') === 'true'

  // Check authentication synchronously BEFORE rendering children
  // This prevents the children from making API calls before redirect
  if (showAll && !isAuthenticated()) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

export default ProtectedRoute
