import { Anchor, Badge, Group, Text } from '@mantine/core'
import Markdown from 'react-markdown'
import type { ResearchPhase } from '@/lib/types.ts'
import PhaseCard from './PhaseCard.tsx'
import PhaseEmptyState from './PhaseEmptyState.tsx'
import classes from './RunDetail.module.css'

function ResearchSection({ research }: { research: ResearchPhase | null }) {
  if (!research) return <PhaseEmptyState title="Research Phase" />

  const webSources = research.sources.filter((s) => s.type !== 'system_context')

  return (
    <PhaseCard title="Research Phase" phase={research} promptLabel="Research Instructions">
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
    </PhaseCard>
  )
}

export default ResearchSection
