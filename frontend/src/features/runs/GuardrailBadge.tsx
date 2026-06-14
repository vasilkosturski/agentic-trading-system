import { useState } from 'react'
import {
  Badge,
  Popover,
  ActionIcon,
  List,
  Stack,
  Code,
  Group,
  Box,
} from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'
import type { GuardrailOutcome } from '@/lib/types.ts'

interface GuardrailBadgeProps {
  outcome: GuardrailOutcome
  attempts: number
  issues: string[] | null
  failedOutput?: Record<string, unknown> | null
}

function GuardrailBadge({ outcome, attempts, issues, failedOutput }: GuardrailBadgeProps) {
  const [opened, setOpened] = useState(false)

  if (outcome === 'first_try') {
    return null
  }

  const hasIssues = issues != null && issues.length > 0

  const badgeElement = outcome === 'recovered' ? (
    <Badge color="orange" variant="light" aria-label="guardrail recovered">
      ⚠️ Recovered after {attempts} attempts
    </Badge>
  ) : (
    <Badge color="red" variant="light" aria-label="guardrail exhausted">
      🚨 Guardrail exhausted
    </Badge>
  )

  const badgeWithPopover = (
    <Group gap={6} wrap="nowrap">
      {badgeElement}
      {hasIssues && (
        <Popover
          opened={opened}
          onChange={setOpened}
          withinPortal
          position="bottom"
          shadow="md"
          radius="md"
          closeOnClickOutside
          closeOnEscape
          transitionProps={{ duration: 0 }}
        >
          <Popover.Target>
            <ActionIcon
              variant="subtle"
              size="sm"
              aria-label="Show validation issues"
              onClick={() => setOpened((o) => !o)}
            >
              <IconInfoCircle size={16} />
            </ActionIcon>
          </Popover.Target>
          <Popover.Dropdown>
            <Box style={{ maxWidth: 560, overflowX: 'auto' }}>
              <List size="sm" spacing={2}>
                {issues!.map((issue, i) => (
                  <List.Item key={`${issue}-${i}`}>{issue}</List.Item>
                ))}
              </List>
            </Box>
          </Popover.Dropdown>
        </Popover>
      )}
    </Group>
  )

  if (!failedOutput) {
    return badgeWithPopover
  }

  return (
    <Stack gap={4}>
      {badgeWithPopover}
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
