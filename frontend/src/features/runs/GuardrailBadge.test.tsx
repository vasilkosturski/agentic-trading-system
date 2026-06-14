import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MantineProvider } from '@mantine/core'
import GuardrailBadge from './GuardrailBadge'

const LONG_URL_ISSUE =
  "webSources contain placeholder URLs: ['https://finance.yahoo.com/quote/JNJ/', 'https://finance.yahoo.com/quote/PEP/']"

function renderBadge(props: Parameters<typeof GuardrailBadge>[0]) {
  return render(
    <MantineProvider>
      <GuardrailBadge {...props} />
    </MantineProvider>,
  )
}

describe('GuardrailBadge click-popover behavior', () => {
  it('hides validation issues by default and shows them after clicking the info icon', async () => {
    renderBadge({
      outcome: 'recovered',
      attempts: 2,
      issues: [LONG_URL_ISSUE],
      failedOutput: null,
    })

    expect(screen.queryByText(LONG_URL_ISSUE)).not.toBeInTheDocument()

    const trigger = screen.getByLabelText('Show validation issues')
    await userEvent.click(trigger)

    expect(screen.getByText(LONG_URL_ISSUE)).toBeInTheDocument()
  })

  it('closes the popover when the info icon is clicked again', async () => {
    renderBadge({
      outcome: 'exhausted',
      attempts: 3,
      issues: [LONG_URL_ISSUE],
      failedOutput: null,
    })

    const trigger = screen.getByLabelText('Show validation issues')
    await userEvent.click(trigger)
    expect(screen.getByText(LONG_URL_ISSUE)).toBeInTheDocument()

    await userEvent.click(trigger)
    expect(screen.queryByText(LONG_URL_ISSUE)).not.toBeInTheDocument()
  })

  it('closes the popover on Escape from the dropdown', async () => {
    renderBadge({
      outcome: 'recovered',
      attempts: 2,
      issues: [LONG_URL_ISSUE],
      failedOutput: null,
    })

    const trigger = screen.getByLabelText('Show validation issues')
    await userEvent.click(trigger)
    const issue = screen.getByText(LONG_URL_ISSUE)
    expect(issue).toBeInTheDocument()

    const dropdownId = trigger.getAttribute('aria-controls')!
    const dropdown = document.getElementById(dropdownId)!
    fireEvent.keyDown(dropdown, { key: 'Escape' })
    expect(screen.queryByText(LONG_URL_ISSUE)).not.toBeInTheDocument()
  })

  it('does not render the info icon when there are no issues', () => {
    renderBadge({
      outcome: 'recovered',
      attempts: 2,
      issues: [],
      failedOutput: null,
    })

    expect(screen.queryByLabelText('Show validation issues')).not.toBeInTheDocument()
  })

  it('renders nothing for first_try', () => {
    renderBadge({
      outcome: 'first_try',
      attempts: 1,
      issues: null,
      failedOutput: null,
    })

    expect(screen.queryByLabelText('guardrail recovered')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('guardrail exhausted')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Show validation issues')).not.toBeInTheDocument()
  })

})
