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
import Login from './Login.tsx'
import ProtectedRoute from './ProtectedRoute.tsx'
import NavigatorSetup from './NavigatorSetup.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MantineProvider>
      <BrowserRouter>
        <NavigatorSetup />
        <AppLayout>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<ProtectedRoute><RunsTable /></ProtectedRoute>} />
            <Route path="/runs/:id" element={<RunDetail />} />
            <Route path="/agents/:id" element={<AgentDetail />} />
            <Route path="/disclaimer" element={<Disclaimer />} />
          </Routes>
        </AppLayout>
      </BrowserRouter>
    </MantineProvider>
  </StrictMode>,
)
