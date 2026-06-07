import type { ReactNode } from 'react'
import { Navigate, useSearchParams, useLocation } from 'react-router-dom'
import { isAuthenticated } from '@/features/auth/auth'

interface ProtectedRouteProps {
  children: ReactNode
}

function ProtectedRoute({ children }: ProtectedRouteProps) {
  const [searchParams] = useSearchParams()
  const location = useLocation()
  const showAll = searchParams.get('showAll') === 'true'

  // Synchronous Navigate prevents race conditions: children must not fire API
  // calls before the redirect commits.
  if (showAll && !isAuthenticated()) {
    const returnUrl = encodeURIComponent(`${location.pathname}${location.search}`)
    return <Navigate to={`/login?returnUrl=${returnUrl}`} replace />
  }

  return <>{children}</>
}

export default ProtectedRoute
