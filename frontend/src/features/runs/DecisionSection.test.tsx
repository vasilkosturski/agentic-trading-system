import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MantineProvider } from '@mantine/core'
import DecisionSection from './DecisionSection'
import { makeMockDecisionPhase } from '@/test/factories.ts'

function renderSection(phase: ReturnType<typeof makeMockDecisionPhase>) {
  return render(
    <MantineProvider>
      <DecisionSection decision={phase} />
    </MantineProvider>,
  )
}

describe('DecisionSection guardrail badge', () => {
  it.each([
    {
      case: 'first_try (no badge)',
      overrides: undefined,
      expectedLabel: null,
    },
    {
      case: 'recovered (orange badge with attempts)',
      overrides: {
        guardrailOutcome: 'recovered' as const,
        guardrailAttempts: 2,
        guardrailIssues: ['invalid_quantity'],
      },
      expectedLabel: 'guardrail recovered',
      expectedText: /Recovered after 2 attempts/,
    },
    {
      case: 'exhausted (red badge)',
      overrides: {
        guardrailOutcome: 'exhausted' as const,
        guardrailAttempts: 3,
        guardrailIssues: ['final_issue'],
      },
      expectedLabel: 'guardrail exhausted',
      expectedText: /Guardrail exhausted/,
    },
  ])('renders correctly for $case', ({ overrides, expectedLabel, expectedText }) => {
    renderSection(overrides ? makeMockDecisionPhase(overrides) : makeMockDecisionPhase())

    if (expectedLabel === null) {
      expect(screen.queryByLabelText('guardrail recovered')).not.toBeInTheDocument()
      expect(screen.queryByLabelText('guardrail exhausted')).not.toBeInTheDocument()
    } else {
      const badge = screen.getByLabelText(expectedLabel)
      expect(badge).toBeInTheDocument()
      if (expectedText) expect(badge.textContent).toMatch(expectedText)
    }
  })
})

describe('DecisionSection rejected-output accordion', () => {
  const REJECTED_OUTPUT = {
    action: 'BUY',
    symbol: 'JPM',
    quantity: 0,
    rationale: 'Hesitant buy',
  }

  it('hides the accordion on first_try', () => {
    renderSection(makeMockDecisionPhase())
    expect(screen.queryByText(/View rejected output/i)).not.toBeInTheDocument()
  })

  it('hides the accordion when failed_output is null even if outcome is recovered', () => {
    renderSection(
      makeMockDecisionPhase({
        guardrailOutcome: 'recovered',
        guardrailAttempts: 2,
        guardrailIssues: ['invalid_quantity'],
        guardrailFailedOutput: null,
      }),
    )
    expect(screen.queryByText(/View rejected output/i)).not.toBeInTheDocument()
  })

  it.each(['recovered', 'exhausted'] as const)(
    'renders the accordion and shows pretty-printed JSON when expanded (%s)',
    async (outcome) => {
      renderSection(
        makeMockDecisionPhase({
          guardrailOutcome: outcome,
          guardrailAttempts: outcome === 'recovered' ? 2 : 3,
          guardrailIssues: ['invalid_quantity'],
          guardrailFailedOutput: REJECTED_OUTPUT,
        }),
      )

      const toggle = screen.getByText(/View rejected output/i)
      expect(toggle).toBeInTheDocument()

      await userEvent.click(toggle)

      const expected = JSON.stringify(REJECTED_OUTPUT, null, 2)
      expect(
        screen.getByText(expected, { normalizer: (text) => text }),
      ).toBeInTheDocument()
    },
  )
})
