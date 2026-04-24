import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import Disclaimer from './Disclaimer'

describe('Routes', () => {
  it('renders Disclaimer component at /disclaimer route', () => {
    render(
      <MantineProvider>
        <MemoryRouter initialEntries={['/disclaimer']}>
          <Routes>
            <Route path="/disclaimer" element={<Disclaimer />} />
          </Routes>
        </MemoryRouter>
      </MantineProvider>
    )

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/educational demonstration/i)
  })
})
