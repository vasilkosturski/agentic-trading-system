import { Group, Text } from '@mantine/core'
import type { ResearchPhase, DecisionPhase } from './types.ts'

interface PhaseMetricsProps {
  phase: ResearchPhase | DecisionPhase
}

function PhaseMetrics({ phase }: PhaseMetricsProps) {
  const m = phase.metrics
  if (!m) return null

  const hasTokens = m.inputTokens != null || m.outputTokens != null
  if (!hasTokens && !m.modelName && !m.numTurns) return null

  return (
    <Group gap="lg" mb="sm">
      {m.modelName && <Text size="xs" c="dimmed">Model: {m.modelName}</Text>}
      {m.numTurns != null && <Text size="xs" c="dimmed">Turns: {m.numTurns}</Text>}
      {hasTokens && (
        <Text size="xs" c="dimmed">
          Tokens: {m.inputTokens?.toLocaleString() ?? '?'} in / {m.outputTokens?.toLocaleString() ?? '?'} out / {m.tokensUsed?.toLocaleString() ?? '?'} total
        </Text>
      )}
      {(m.cachedTokens ?? 0) > 0 && <Text size="xs" c="dimmed">Cached: {m.cachedTokens!.toLocaleString()}</Text>}
      {(m.reasoningTokens ?? 0) > 0 && <Text size="xs" c="dimmed">Reasoning: {m.reasoningTokens!.toLocaleString()}</Text>}
      {m.costUsd != null && <Text size="xs" c="dimmed">Cost: ${m.costUsd.toFixed(4)}</Text>}
    </Group>
  )
}

export default PhaseMetrics
