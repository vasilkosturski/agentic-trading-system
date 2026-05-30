import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MantineProvider } from '@mantine/core'
import ToolCallsTable from './ToolCallsTable'
import type { ToolCall } from './types'

describe('ToolCallsTable', () => {
  it('renders one row per tool call with the formatted parameters', () => {
    const toolCalls: ToolCall[] = [
      {
        tool: 'web_search',
        params: { query: 'AAPL earnings' },
        error: null,
        errorMessage: null,
      },
    ]

    render(
      <MantineProvider>
        <ToolCallsTable toolCalls={toolCalls} />
      </MantineProvider>
    )

    expect(screen.getByText('web_search')).toBeInTheDocument()
    expect(screen.getByText(/query=AAPL earnings/)).toBeInTheDocument()
  })

  it('renders nothing when there are no tool calls', () => {
    const { container } = render(
      <MantineProvider>
        <ToolCallsTable toolCalls={[]} />
      </MantineProvider>
    )

    expect(container.querySelector('table')).toBeNull()
    expect(container.textContent).not.toMatch(/Tool Calls/)
  })
})
