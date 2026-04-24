import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import '@mantine/core/styles.css'
import '@mantine/charts/styles.css'
import './index.css'
import AppLayout from './AppLayout.tsx'
import RunsTable from './App.tsx'
import RunDetail from './RunDetail.tsx'
import AgentDetail from './AgentDetail.tsx'
import Disclaimer from './Disclaimer.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MantineProvider>
      <BrowserRouter>
        <AppLayout>
          <Routes>
            <Route path="/" element={<RunsTable />} />
            <Route path="/runs/:id" element={<RunDetail />} />
            <Route path="/agents/:id" element={<AgentDetail />} />
            <Route path="/disclaimer" element={<Disclaimer />} />
          </Routes>
        </AppLayout>
      </BrowserRouter>
    </MantineProvider>
  </StrictMode>,
)
