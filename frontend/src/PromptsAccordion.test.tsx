import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MantineProvider } from '@mantine/core'
import PromptsAccordion from './PromptsAccordion'

describe('PromptsAccordion', () => {
  it('renders the accordion label when at least one prompt is provided', () => {
    render(
      <MantineProvider>
        <PromptsAccordion
          label="Research Instructions"
          systemPrompt="You are a researcher."
          taskPrompt={null}
        />
      </MantineProvider>
    )

    expect(screen.getByText('Research Instructions')).toBeInTheDocument()
  })

  it('renders nothing when both system and task prompts are null', () => {
    const { container } = render(
      <MantineProvider>
        <PromptsAccordion
          label="Research Instructions"
          systemPrompt={null}
          taskPrompt={null}
        />
      </MantineProvider>
    )

    expect(container.textContent).not.toMatch(/Research Instructions/)
  })
})
