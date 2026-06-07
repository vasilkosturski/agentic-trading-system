import { within } from '@testing-library/react'
import { expect } from 'vitest'

/**
 * Common disclaimer-text assertions shared by Footer + DisclaimerBanner.
 * Both surfaces must communicate the same three facts: 7-day delay,
 * educational-only framing, and a link to the full /disclaimer page.
 */
export function assertDisclaimerSemantics(container: HTMLElement) {
  const scope = within(container)
  expect(scope.getByText(/educational/i)).toBeInTheDocument()
  expect(scope.getByText(/7\+? days?/i)).toBeInTheDocument()
  const link = scope.getByRole('link', { name: /disclaimer|learn more|view full/i })
  expect(link).toHaveAttribute('href', '/disclaimer')
}
