import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MantineProvider } from '@mantine/core'
import ResearchSection from './ResearchSection'
import { makeMockResearchPhase } from '@/test/factories.ts'

function renderSection(phase: ReturnType<typeof makeMockResearchPhase>) {
  return render(
    <MantineProvider>
      <ResearchSection research={phase} />
    </MantineProvider>,
  )
}

describe('ResearchSection guardrail badge', () => {
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
        guardrailIssues: ['fake_url'],
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
    renderSection(overrides ? makeMockResearchPhase(overrides) : makeMockResearchPhase())

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

describe('ResearchSection rejected-output accordion', () => {
  const REJECTED_OUTPUT = {
    summary: 'Banks look strong this quarter.',
    candidates: [{ symbol: 'JPM', price: 195.42 }],
  }

  it('hides the accordion on first_try', () => {
    renderSection(makeMockResearchPhase())
    expect(screen.queryByText(/View rejected output/i)).not.toBeInTheDocument()
  })

  it('hides the accordion when failed_output is null even if outcome is recovered', () => {
    renderSection(
      makeMockResearchPhase({
        guardrailOutcome: 'recovered',
        guardrailAttempts: 2,
        guardrailIssues: ['fake_url'],
        guardrailFailedOutput: null,
      }),
    )
    expect(screen.queryByText(/View rejected output/i)).not.toBeInTheDocument()
  })

  it.each(['recovered', 'exhausted'] as const)(
    'renders the accordion and shows pretty-printed JSON when expanded (%s)',
    async (outcome) => {
      renderSection(
        makeMockResearchPhase({
          guardrailOutcome: outcome,
          guardrailAttempts: outcome === 'recovered' ? 2 : 3,
          guardrailIssues: ['fake_url'],
          guardrailFailedOutput: REJECTED_OUTPUT,
        }),
      )

      const toggle = screen.getByText(/View rejected output/i)
      expect(toggle).toBeInTheDocument()

      await userEvent.click(toggle)

      // Pretty-printed JSON includes indentation + the original keys.
      // getByText collapses whitespace by default; opt out so we can
      // assert the literal multi-line indented payload.
      const expected = JSON.stringify(REJECTED_OUTPUT, null, 2)
      expect(
        screen.getByText(expected, { normalizer: (text) => text }),
      ).toBeInTheDocument()
    },
  )
})
