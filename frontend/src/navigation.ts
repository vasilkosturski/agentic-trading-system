import type { NavigateFunction, NavigateOptions } from 'react-router-dom'

/**
 * Module-level bridge so non-component code (api.ts) can trigger SPA
 * navigation via react-router's `useNavigate`. `<NavigatorSetup />`
 * registers a NavigateFunction here after mounting under `<BrowserRouter>`.
 *
 * Why not `window.location.href`: the assignment is async — the current
 * JS task and its microtasks finish before the browser unloads, so React
 * commits "Failed to fetch ... 403" before the redirect happens.
 * useNavigate swaps components in place and avoids that paint-before-
 * navigation race.
 */

let navigator: NavigateFunction | null = null

export function setNavigator(nav: NavigateFunction): void {
  navigator = nav
}

export function resetNavigator(): void {
  navigator = null
}

export function navigate(to: string, options?: NavigateOptions): void {
  if (navigator) {
    navigator(to, options)
    return
  }
  // Fallback before NavigatorSetup mounts: full-page reload preserves the
  // redirect at the cost of losing in-flight React state.
  window.location.href = to
}
