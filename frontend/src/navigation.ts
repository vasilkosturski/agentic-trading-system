import type { NavigateFunction, NavigateOptions } from 'react-router-dom'

/**
 * Module-level bridge that lets non-component code (e.g. the fetch wrapper
 * in api.ts) trigger SPA navigation via react-router-dom's `useNavigate`
 * without ever rendering a hook outside a component.
 *
 * `<NavigatorSetup />` registers a `NavigateFunction` here once it mounts
 * under `<BrowserRouter>`. Until that happens, `navigate()` falls back to
 * `window.location.href` so very-early failures (before the React tree
 * has mounted) still redirect — at the cost of a full page reload.
 *
 * Why this exists: assigning to `window.location.href` is asynchronous —
 * the current JS task (and any microtasks queued during it) runs to
 * completion before the browser unloads the page. That gives React time
 * to commit a re-render that paints "Failed to fetch ... 403" before the
 * navigation actually happens. Using `useNavigate` swaps components in
 * place without that race.
 */

let navigator: NavigateFunction | null = null

export function setNavigator(nav: NavigateFunction): void {
  navigator = nav
}

/**
 * Reset to the unregistered state. Intended for tests; production code
 * should never call this.
 */
export function resetNavigator(): void {
  navigator = null
}

export function navigate(to: string, options?: NavigateOptions): void {
  if (navigator) {
    navigator(to, options)
    return
  }
  // Fallback: full-page reload. Imperfect, but preserves the redirect
  // behavior in the rare case of an API call before NavigatorSetup has
  // mounted (e.g. SSR, or a fetch fired during the very first render).
  window.location.href = to
}
