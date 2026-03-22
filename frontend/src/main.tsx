import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import '@mantine/core/styles.css'
import './index.css'
import RunsTable from './App.tsx'
import RunDetail from './RunDetail.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MantineProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<RunsTable />} />
          <Route path="/runs/:id" element={<RunDetail />} />
        </Routes>
      </BrowserRouter>
    </MantineProvider>
  </StrictMode>,
)
