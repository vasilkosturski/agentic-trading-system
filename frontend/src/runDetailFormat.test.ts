import { describe, it, expect } from 'vitest'
import { formatDuration } from './runDetailFormat'

describe('formatDuration', () => {
  it('formats a completed run as seconds with one decimal', () => {
    // Arrange — a 2.5-second run.
    const startedAt = '2025-01-01T00:00:00.000Z'
    const completedAt = '2025-01-01T00:00:02.500Z'

    // Act
    const formatted = formatDuration(startedAt, completedAt)

    // Assert
    expect(formatted).toBe('2.5s')
  })

  it('returns "In progress" when completedAt is null', () => {
    expect(formatDuration('2025-01-01T00:00:00.000Z', null)).toBe('In progress')
  })
})
