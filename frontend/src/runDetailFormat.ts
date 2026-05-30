/**
 * Pure formatting helpers for the run-detail view.
 *
 * Lives outside RunDetail.tsx so the formatting concerns can be unit-tested
 * without mounting React and so the extracted phase components can share them.
 */

export function formatDuration(startedAt: string, completedAt: string | null): string {
  if (!completedAt) return 'In progress'
  const ms = new Date(completedAt).getTime() - new Date(startedAt).getTime()
  const seconds = (ms / 1000).toFixed(1)
  return `${seconds}s`
}

export function formatParams(params: Record<string, unknown>): string {
  return Object.entries(params)
    .map(([key, val]) => `${key}=${typeof val === 'string' ? val : JSON.stringify(val)}`)
    .join(', ')
}
