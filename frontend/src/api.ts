import type { PortfolioSnapshot, TradingRun, Agent, RunDetailResponse } from './types.ts'

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

export function fetchRuns(signal?: AbortSignal): Promise<{ runs: TradingRun[] }> {
  return fetchJson<{ runs: TradingRun[] }>('/api/runs?limit=20', signal)
}

export function fetchAgents(signal?: AbortSignal): Promise<Agent[]> {
  return fetchJson<Agent[]>('/api/agents', signal)
}

export function fetchRunDetail(id: string, signal?: AbortSignal): Promise<RunDetailResponse> {
  return fetchJson<RunDetailResponse>(`/api/runs/${id}`, signal)
}
