import { Accordion, Text } from '@mantine/core'
import Markdown from 'react-markdown'
import classes from './RunDetail.module.css'

interface PromptsAccordionProps {
  label: string
  systemPrompt: string | null
  taskPrompt: string | null
}

function PromptsAccordion({ label, systemPrompt, taskPrompt }: PromptsAccordionProps) {
  if (!systemPrompt && !taskPrompt) return null

  return (
    <Accordion variant="separated" mb="sm">
      <Accordion.Item value="prompts">
        <Accordion.Control>
          <Text fw={600} size="sm">{label}</Text>
        </Accordion.Control>
        <Accordion.Panel>
          {systemPrompt && (
            <>
              <Text fw={600} size="sm" mb={4}>System Prompt</Text>
              <div className={classes.scrollableContent}>
                <Markdown>{systemPrompt}</Markdown>
              </div>
            </>
          )}
          {taskPrompt && (
            <>
              <Text fw={600} size="sm" mb={4}>Task Prompt</Text>
              <div className={classes.scrollableContentLast}>
                <Markdown>{taskPrompt}</Markdown>
              </div>
            </>
          )}
        </Accordion.Panel>
      </Accordion.Item>
    </Accordion>
  )
}

export default PromptsAccordion
