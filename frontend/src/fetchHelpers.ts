/**
 * Wrap a cosmetic array-returning fetch so a rejection resolves to `[]` instead
 * of collapsing the surrounding Promise.all — keeps primary content rendering
 * when only a friendly-name lookup (or similar) fails.
 */
export function fetchOrEmpty<T>(promise: Promise<T[]>): Promise<T[]> {
  return promise.catch(() => [] as T[])
}
