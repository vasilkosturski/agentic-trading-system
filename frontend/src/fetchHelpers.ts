/**
 * Wrap a cosmetic array-returning fetch so a real rejection resolves to `[]`
 * instead of collapsing the surrounding Promise.all — keeps primary content
 * rendering when only a friendly-name lookup (or similar) fails.
 *
 * `AbortError` is re-thrown so caller-side `controller.signal.aborted` checks
 * still see the cancellation cleanly; otherwise an unmount-driven abort gets
 * silently masked as "200 with empty array" and the loading guard never trips.
 */
export function fetchOrEmpty<T>(promise: Promise<T[]>): Promise<T[]> {
  return promise.catch((err) => {
    if (err && (err as { name?: string }).name === 'AbortError') throw err
    return [] as T[]
  })
}
