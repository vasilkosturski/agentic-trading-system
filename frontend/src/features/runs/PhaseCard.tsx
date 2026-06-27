import type { ReactNode } from 'react'
import { Paper, Group, Title, Text } from '@mantine/core'
import type { ResearchPhase, DecisionPhase } from '@/lib/types.ts'
import GuardrailBadge from './GuardrailBadge.tsx'
import PhaseMetrics from './PhaseMetrics.tsx'
import PromptsAccordion from './PromptsAccordion.tsx'
import ToolCallsTable from './ToolCallsTable.tsx'

interface PhaseCardProps {
  title: string
  phase: ResearchPhase | DecisionPhase
  promptLabel: string
  children: ReactNode
}

function PhaseCard({ title, phase, promptLabel, children }: PhaseCardProps) {
  return (
    <Paper p="lg" shadow="xs" mb="md">
      <Group justify="space-between" mb="sm">
        <Group gap="sm">
          <Title order={3}>{title}</Title>
          <GuardrailBadge
            outcome={phase.guardrailOutcome}
            attempts={phase.guardrailAttempts}
            issues={phase.guardrailIssues}
            failedOutput={phase.guardrailFailedOutput}
          />
        </Group>
        {phase.latencyMs != null && (
          <Text c="dimmed" size="sm">Completed in {phase.latencyMs.toLocaleString()}ms</Text>
        )}
      </Group>

      <PhaseMetrics phase={phase} />

      <PromptsAccordion
        label={promptLabel}
        systemPrompt={phase.systemPrompt}
        taskPrompt={phase.taskPrompt}
      />

      {children}

      <ToolCallsTable toolCalls={phase.toolCalls} />
    </Paper>
  )
}

export default PhaseCard
