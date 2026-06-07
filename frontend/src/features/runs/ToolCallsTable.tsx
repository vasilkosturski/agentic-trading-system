import { Table, Text } from '@mantine/core'
import type { ToolCall } from '@/lib/types.ts'
import { formatParams } from './runDetailFormat.ts'

interface ToolCallsTableProps {
  toolCalls: ToolCall[]
}

function ToolCallsTable({ toolCalls }: ToolCallsTableProps) {
  if (toolCalls.length === 0) return null
  return (
    <>
      <Text fw={600} mt="sm" mb={4}>Tool Calls</Text>
      <Table striped>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Tool</Table.Th>
            <Table.Th>Parameters</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {toolCalls.map((tc, i) => (
            <Table.Tr key={`${tc.tool}-${i}`}>
              <Table.Td><Text size="sm" ff="monospace">{tc.tool}</Text></Table.Td>
              <Table.Td><Text size="sm" ff="monospace">{formatParams(tc.params)}</Text></Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </>
  )
}

export default ToolCallsTable
