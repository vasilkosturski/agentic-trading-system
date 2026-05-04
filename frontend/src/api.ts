import type { PortfolioSnapshot, TradingRun, Agent, RunDetailResponse, AgentPortfolio } from './types.ts'
import { getToken, logout } from './auth'

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

  // Handle 403 Forbidden - token is invalid/expired or user lacks required roles
  if (res.status === 403) {
    // Clear invalid token from localStorage
    logout()

    // Redirect to login with current URL as returnUrl so user can return after re-authentication
    const currentPath = window.location.pathname + window.location.search
    const returnUrl = encodeURIComponent(currentPath)
    window.location.href = `/login?returnUrl=${returnUrl}`

    // Throw error to stop execution
    throw new Error(`Failed to fetch ${url}: ${res.status}`)
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
