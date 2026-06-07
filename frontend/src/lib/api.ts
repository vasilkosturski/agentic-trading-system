import type { PortfolioSnapshot, TradingRun, Agent, RunDetailResponse, AgentPortfolio } from './types.ts'
import { getToken, logout } from '@/features/auth/auth'
import { navigate } from './navigation'

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

  // 403: do NOT throw — a thrown error would let callers' catch blocks paint
  // "Failed to fetch ... 403" before SPA navigation commits. Trigger navigate()
  // and return a never-resolving promise so the await never resumes; the
  // unmounting component's AbortController cleanup tears down the inflight req.
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
