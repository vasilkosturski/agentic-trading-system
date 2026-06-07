import { Paper, Title, Group, Text, Badge, Anchor } from '@mantine/core'
import Markdown from 'react-markdown'
import type { ResearchPhase } from '@/lib/types.ts'
import PhaseMetrics from './PhaseMetrics.tsx'
import PromptsAccordion from './PromptsAccordion.tsx'
import ToolCallsTable from './ToolCallsTable.tsx'
import classes from './RunDetail.module.css'

function ResearchSection({ research }: { research: ResearchPhase | null }) {
  if (!research) {
    return (
      <Paper p="lg" shadow="xs" mb="md">
        <Title order={3} mb="sm">Research Phase</Title>
        <Text c="dimmed">Phase not completed</Text>
      </Paper>
    )
  }

  const webSources = research.sources.filter((s) => s.type !== 'system_context')

  return (
    <Paper p="lg" shadow="xs" mb="md">
      <Group justify="space-between" mb="sm">
        <Title order={3}>Research Phase</Title>
        {research.latencyMs != null && <Text c="dimmed" size="sm">Completed in {research.latencyMs.toLocaleString()}ms</Text>}
      </Group>

      <PhaseMetrics phase={research} />

      <PromptsAccordion
        label="Research Instructions"
        systemPrompt={research.systemPrompt}
        taskPrompt={research.taskPrompt}
      />

      <Text fw={600} mb={4}>Candidates</Text>
      <Group gap="xs" mb="md">
        {research.candidates.map((c) => (
          <Badge key={c} variant="outline">{c}</Badge>
        ))}
      </Group>

      <Text fw={600} mb={4}>Research Notes</Text>
      <div className={classes.researchNotes}>
        <Markdown>{research.researchNotes}</Markdown>
      </div>

      {webSources.length > 0 && (
        <>
          <Text fw={600} mb={4}>Web Sources</Text>
          <ul className={classes.sourcesList}>
            {webSources.map((s, i) => (
              <li key={s.url ?? s.title ?? i}>
                {s.url ? (
                  <Anchor href={s.url} target="_blank" rel="noopener noreferrer" size="sm">
                    {s.title ?? s.url}
                  </Anchor>
                ) : (
                  <Text size="sm">{s.title ?? 'Untitled source'}</Text>
                )}
              </li>
            ))}
          </ul>
        </>
      )}

      <ToolCallsTable toolCalls={research.toolCalls} />
    </Paper>
  )
}

export default ResearchSection
