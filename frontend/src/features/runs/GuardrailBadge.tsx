import { Badge, Tooltip, List, Stack, Code } from '@mantine/core'
import type { GuardrailOutcome } from '@/lib/types.ts'

interface GuardrailBadgeProps {
  outcome: GuardrailOutcome
  attempts: number
  issues: string[] | null
  failedOutput?: Record<string, unknown> | null
}

/**
 * Per-phase guardrail outcome indicator. Renders nothing for first-try
 * success so clean runs stay visually quiet; an orange / red badge with
 * a hover-Tooltip listing the last failed attempt's issues surfaces only
 * on recovery or exhaustion. When the backend captured the LLM's rejected
 * output, a collapsible accordion underneath the badge pretty-prints the
 * payload so operators can inspect what the model produced.
 */
function GuardrailBadge({ outcome, attempts, issues, failedOutput }: GuardrailBadgeProps) {
  if (outcome === 'first_try') {
    return null
  }

  const tooltipLabel = issues && issues.length > 0
    ? (
      <List size="sm" spacing={2}>
        {issues.map((issue, i) => (
          <List.Item key={`${issue}-${i}`}>{issue}</List.Item>
        ))}
      </List>
    )
    : 'No issue details captured'

  const badge = outcome === 'recovered' ? (
    <Tooltip label={tooltipLabel} multiline w={280} withArrow>
      <Badge color="orange" variant="light" aria-label="guardrail recovered">
        ⚠️ Recovered after {attempts} attempts
      </Badge>
    </Tooltip>
  ) : (
    <Tooltip label={tooltipLabel} multiline w={280} withArrow>
      <Badge color="red" variant="light" aria-label="guardrail exhausted">
        🚨 Guardrail exhausted
      </Badge>
    </Tooltip>
  )

  if (!failedOutput) {
    return badge
  }

  // Native <details> element keeps the panel collapsed by default and
  // mounts the formatted JSON straight into the DOM (no transitions, no
  // lazy mount) so it's trivially testable and adds zero runtime cost
  // when the user never expands it.
  return (
    <Stack gap={4}>
      {badge}
      <details>
        <summary
          style={{ cursor: 'pointer', fontSize: 'var(--mantine-font-size-sm)' }}
        >
          View rejected output
        </summary>
        <Code block>{JSON.stringify(failedOutput, null, 2)}</Code>
      </details>
    </Stack>
  )
}

export default GuardrailBadge
