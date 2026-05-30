/**
 * Shared helpers for HTTP fetches used inside Promise.all bundles.
 *
 * When a page loads a primary resource alongside cosmetic ones (e.g. an
 * agents map used only to display friendly names), a single rejected
 * cosmetic fetch must not collapse the whole `Promise.all`. These helpers
 * make it ergonomic to opt the cosmetic fetches out of failure
 * propagation without sprinkling `.catch(() => fallback)` at every callsite.
 */

/**
 * Wrap a fetch that returns an array so that any rejection resolves to an
 * empty array instead of propagating. Use for cosmetic / non-critical fetches
 * inside Promise.all where a failure should not block the primary content.
 */
export function fetchOrEmpty<T>(promise: Promise<T[]>): Promise<T[]> {
  return promise.catch(() => [] as T[])
}
