import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import RunsTable from './App'
import * as auth from './auth'
import * as navigation from './navigation'

/**
 * Integration test for the 403 → /login redirect path that exercises the
 * REAL api.ts (no api mocking) and the REAL App.tsx render. Asserts that
 * a stale-token user NEVER sees the "Failed to fetch ... 403" string.
 *
 * Stubs only the lowest-level boundary (`fetch`) and the navigation bridge
 * (`navigate`), so the test exercises the full fetchJson → setState →
 * render path that originally caused the bug.
 */

vi.mock('./auth', () => ({
  getToken: vi.fn(),
  logout: vi.fn(),
  isAuthenticated: vi.fn(() => true),
}))

vi.mock('./navigation', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./navigation')>()
  return {
    ...actual,
    navigate: vi.fn(),
  }
})

describe('App.tsx + api.ts integration — 403 no-flash redirect', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn()
    vi.mocked(auth.getToken).mockReturnValue('expired.jwt.token')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('does not paint "Failed to fetch ... 403" when backend returns 403 for /api/runs/admin', async () => {
    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
    } as Response)

    render(
      <MantineProvider>
        <MemoryRouter initialEntries={['/?showAll=true']}>
          <RunsTable />
        </MemoryRouter>
      </MantineProvider>
    )

    await waitFor(() => {
      expect(navigation.navigate).toHaveBeenCalled()
    })

    await new Promise((r) => setTimeout(r, 50))

    expect(screen.queryByText(/Failed to fetch/i)).toBeNull()
    expect(screen.queryByText(/\b403\b/)).toBeNull()

    expect(auth.logout).toHaveBeenCalled()
    expect(navigation.navigate).toHaveBeenCalledWith(
      expect.stringMatching(/^\/login\?returnUrl=/),
      { replace: true },
    )
  })
})
