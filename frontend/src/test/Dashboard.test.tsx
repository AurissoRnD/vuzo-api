import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import Dashboard from '../pages/Dashboard'
import { renderWithProviders, mockSession } from './renderWithProviders'
import { api } from '../lib/api'

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    vi.mocked(api.get).mockImplementation(() => new Promise(() => {}))
    renderWithProviders(<Dashboard />, { session: mockSession() })
    expect(screen.getByText(/loading dashboard/i)).toBeInTheDocument()
  })

  it('renders all six stat cards after data loads', async () => {
    vi.mocked(api.get)
      .mockResolvedValueOnce({ balance: 2.5 })
      .mockResolvedValueOnce({
        total_requests: 42,
        total_input_tokens: 1000,
        total_output_tokens: 500,
        total_tokens: 1500,
        total_provider_cost: 0.0002,
        total_vuzo_cost: 0.00024,
      })

    renderWithProviders(<Dashboard />, { session: mockSession() })

    await waitFor(() => {
      expect(screen.getByText('Credit Balance')).toBeInTheDocument()
      expect(screen.getByText('Total Requests')).toBeInTheDocument()
      expect(screen.getByText('Total Spend')).toBeInTheDocument()
      expect(screen.getByText('Input Tokens')).toBeInTheDocument()
      expect(screen.getByText('Output Tokens')).toBeInTheDocument()
      expect(screen.getByText('Total Tokens')).toBeInTheDocument()
    })
  })

  it('displays the balance value correctly', async () => {
    vi.mocked(api.get)
      .mockResolvedValueOnce({ balance: 1.2345 })
      .mockResolvedValueOnce({
        total_requests: 0, total_input_tokens: 0, total_output_tokens: 0,
        total_tokens: 0, total_provider_cost: 0, total_vuzo_cost: 0,
      })

    renderWithProviders(<Dashboard />, { session: mockSession() })

    await waitFor(() => {
      expect(screen.getByText('$1.2345')).toBeInTheDocument()
    })
  })

  it('displays total requests formatted with locale', async () => {
    vi.mocked(api.get)
      .mockResolvedValueOnce({ balance: 0 })
      .mockResolvedValueOnce({
        total_requests: 1234,
        total_input_tokens: 0, total_output_tokens: 0,
        total_tokens: 0, total_provider_cost: 0, total_vuzo_cost: 0,
      })

    renderWithProviders(<Dashboard />, { session: mockSession() })

    await waitFor(() => {
      expect(screen.getByText('1,234')).toBeInTheDocument()
    })
  })

  it('shows zeros when API returns no data', async () => {
    vi.mocked(api.get).mockRejectedValue(new Error('Network error'))

    renderWithProviders(<Dashboard />, { session: mockSession() })

    await waitFor(() => {
      const zeros = screen.getAllByText('$0.0000')
      expect(zeros.length).toBeGreaterThanOrEqual(1)
    })
  })
})
