import type { PortfolioSnapshot, TradingRun, Agent, RunDetailResponse, AgentPortfolio } from './types.ts'
import { getToken, logout } from './auth'
import { navigate } from './navigation'

/**
 * Shared API client for backend HTTP calls.
 * Centralizes endpoint URLs, error handling, and response typing.
 */

async function fetchJson<T>(url: string, signal?: AbortSignal, includeAuth: boolean = false): Promise<T> {
  const options: RequestInit = signal ? { signal } : {}

  if (includeAuth) {
    const token = getToken()
    if (token) {
      options.headers = {
        'Authorization': `Bearer ${token}`
      }
    }
  }

  const res = await fetch(url, options)

  // Handle 403 Forbidden — token is invalid/expired or user lacks required roles.
  //
  // We MUST NOT throw here: if we did, every caller's catch block would run
  // and `setError(err.message)` would paint "Failed to fetch ... 403" before
  // the SPA navigation completes. Instead we trigger navigate() (which is
  // synchronous as far as React is concerned — it commits the new route on
  // the next render) and return a never-resolving promise. The caller's
  // `await` then never resumes, so its catch never fires; the component
  // unmounts within a tick when the new route renders, and the AbortController
  // cleanup in its useEffect tears down the inflight request.
  if (res.status === 403) {
    logout()
    const currentPath = window.location.pathname + window.location.search
    const returnUrl = encodeURIComponent(currentPath)
    navigate(`/login?returnUrl=${returnUrl}`, { replace: true })
    return new Promise<never>(() => {})
  }

  if (!res.ok) throw new Error(`Failed to fetch ${url}: ${res.status}`)
  return res.json() as Promise<T>
}

export function fetchSnapshots(signal?: AbortSignal): Promise<PortfolioSnapshot[]> {
  return fetchJson<PortfolioSnapshot[]>('/api/portfolio/snapshots', signal)
}

export interface PaginatedRuns {
  runs: TradingRun[]
  total: number
  page: number
  limit: number
}

export function fetchRuns(page: number = 0, limit: number = 20, signal?: AbortSignal, showAll: boolean = false): Promise<PaginatedRuns> {
  const endpoint = showAll ? '/api/runs/admin' : '/api/runs'
  return fetchJson<PaginatedRuns>(`${endpoint}?page=${page}&limit=${limit}`, signal, showAll)
}

export function fetchAgents(signal?: AbortSignal): Promise<Agent[]> {
  return fetchJson<Agent[]>('/api/agents', signal)
}

export function fetchRunDetail(id: string, signal?: AbortSignal): Promise<RunDetailResponse> {
  return fetchJson<RunDetailResponse>(`/api/runs/${id}`, signal)
}

export function fetchAgentPortfolio(agentId: number, signal?: AbortSignal): Promise<AgentPortfolio> {
  return fetchJson<AgentPortfolio>(`/api/accounts/resources/accounts/${agentId}`, signal)
}
