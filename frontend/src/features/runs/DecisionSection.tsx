import { Paper, Group, Text, Badge } from '@mantine/core'
import Markdown from 'react-markdown'
import type { DecisionPhase } from '@/lib/types.ts'
import { decisionColor } from '@/lib/utils.ts'
import PhaseCard from './PhaseCard.tsx'
import PhaseEmptyState from './PhaseEmptyState.tsx'
import classes from './RunDetail.module.css'

function DecisionSection({ decision }: { decision: DecisionPhase | null }) {
  if (!decision) return <PhaseEmptyState title="Decision Phase" />

  return (
    <PhaseCard title="Decision Phase" phase={decision} promptLabel="Decision Instructions">
      <Group gap="sm" mb="md">
        <Badge color={decisionColor(decision.decision)} variant="light" size="lg">
          {decision.decision}
        </Badge>
        {decision.symbol && <Text fw={600}>{decision.symbol}</Text>}
        {decision.quantity != null && <Text c="dimmed">x{decision.quantity} shares</Text>}
      </Group>

      {decision.reasoning?.rationale && (
        <>
          <Text fw={600} mb={4}>Decision Notes</Text>
          <div className={classes.researchNotes}>
            <Markdown>{decision.reasoning.rationale}</Markdown>
          </div>
        </>
      )}

      {decision.reasoning && (
        <>
          <Paper withBorder p="sm" mb="xs">
            <Text size="sm" fw={600} mb={4}>Research Context</Text>
            <div className={classes.markdownSmall}>
              <Markdown>{decision.reasoning.researchContext}</Markdown>
            </div>
          </Paper>

          <Paper withBorder p="sm" mb="xs">
            <Text size="sm" fw={600} mb={4}>Portfolio Context</Text>
            <div className={classes.markdownSmall}>
              <Markdown>{decision.reasoning.portfolioContext}</Markdown>
            </div>
          </Paper>

          <Paper withBorder p="sm" mb="md">
            <Text size="sm" fw={600} mb={4}>Historical Context</Text>
            <div className={classes.markdownSmall}>
              <Markdown>{decision.reasoning.historicalContext}</Markdown>
            </div>
          </Paper>
        </>
      )}
    </PhaseCard>
  )
}

export default DecisionSection
