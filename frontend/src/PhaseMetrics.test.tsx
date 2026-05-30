import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MantineProvider } from '@mantine/core'
import PhaseMetrics from './PhaseMetrics'
import type { ResearchPhase } from './types'

describe('PhaseMetrics', () => {
  it('renders model name and token counts when metrics are present', () => {
    const phase: ResearchPhase = {
      researchId: 1,
      candidates: [],
      sources: [],
      researchNotes: '',
      toolCalls: [],
      latencyMs: 1000,
      systemPrompt: null,
      taskPrompt: null,
      metrics: {
        tokensUsed: 1500,
        inputTokens: 1000,
        outputTokens: 500,
        numTurns: 3,
        cachedTokens: 0,
        reasoningTokens: 0,
        costUsd: 0.0125,
        modelName: 'claude-opus-4',
      },
    }

    render(
      <MantineProvider>
        <PhaseMetrics phase={phase} />
      </MantineProvider>
    )

    expect(screen.getByText(/Model: claude-opus-4/)).toBeInTheDocument()
    expect(screen.getByText(/Turns: 3/)).toBeInTheDocument()
  })

  it('renders nothing when phase has no metrics', () => {
    const phase: ResearchPhase = {
      researchId: 1,
      candidates: [],
      sources: [],
      researchNotes: '',
      toolCalls: [],
      latencyMs: 1000,
      systemPrompt: null,
      taskPrompt: null,
      metrics: null,
    }

    const { container } = render(
      <MantineProvider>
        <PhaseMetrics phase={phase} />
      </MantineProvider>
    )

    // No model / tokens text rendered.
    expect(container.textContent).not.toMatch(/Model:/)
    expect(container.textContent).not.toMatch(/Tokens:/)
  })
})
