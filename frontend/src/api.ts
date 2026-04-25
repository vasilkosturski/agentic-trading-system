import type { PortfolioSnapshot, TradingRun, Agent, RunDetailResponse, AgentPortfolio } from './types.ts'

/**
 * Shared API client for backend HTTP calls.
 * Centralizes endpoint URLs, error handling, and response typing.
 */

async function fetchJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(url, signal ? { signal } : undefined)
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
  const showAllParam = showAll ? '&showAll=true' : ''
  return fetchJson<PaginatedRuns>(`/api/runs?page=${page}&limit=${limit}${showAllParam}`, signal)
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
