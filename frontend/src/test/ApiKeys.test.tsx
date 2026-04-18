import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ApiKeys from '../pages/ApiKeys'
import { renderWithProviders, mockSession } from './renderWithProviders'
import { api } from '../lib/api'

const MOCK_KEYS = [
  {
    id: 'key-1',
    name: 'Production',
    key_prefix: 'vz-sk_aa',
    is_active: true,
    rate_limit_rpm: 60,
    created_at: '2024-01-01T00:00:00Z',
    last_used_at: '2024-06-01T00:00:00Z',
  },
  {
    id: 'key-2',
    name: 'Staging',
    key_prefix: 'vz-sk_bb',
    is_active: false,
    rate_limit_rpm: 60,
    created_at: '2024-02-01T00:00:00Z',
    last_used_at: null,
  },
]

describe('ApiKeys', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    vi.mocked(api.get).mockImplementation(() => new Promise(() => {}))
    renderWithProviders(<ApiKeys />, { session: mockSession() })
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('renders keys list after load', async () => {
    vi.mocked(api.get).mockResolvedValue(MOCK_KEYS)
    renderWithProviders(<ApiKeys />, { session: mockSession() })

    await waitFor(() => {
      expect(screen.getByText('Production')).toBeInTheDocument()
      expect(screen.getByText('Staging')).toBeInTheDocument()
    })
  })

  it('shows empty state when no keys exist', async () => {
    vi.mocked(api.get).mockResolvedValue([])
    renderWithProviders(<ApiKeys />, { session: mockSession() })

    await waitFor(() => {
      expect(screen.getByText(/no api keys yet/i)).toBeInTheDocument()
    })
  })

  it('shows active/revoked status badges correctly', async () => {
    vi.mocked(api.get).mockResolvedValue(MOCK_KEYS)
    renderWithProviders(<ApiKeys />, { session: mockSession() })

    await waitFor(() => {
      expect(screen.getByText('Active')).toBeInTheDocument()
      expect(screen.getByText('Revoked')).toBeInTheDocument()
    })
  })

  it('shows "Never" for keys with no last_used_at', async () => {
    vi.mocked(api.get).mockResolvedValue(MOCK_KEYS)
    renderWithProviders(<ApiKeys />, { session: mockSession() })

    await waitFor(() => {
      expect(screen.getByText('Never')).toBeInTheDocument()
    })
  })

  it('only shows Revoke button for active keys', async () => {
    vi.mocked(api.get).mockResolvedValue(MOCK_KEYS)
    renderWithProviders(<ApiKeys />, { session: mockSession() })

    await waitFor(() => {
      const revokeButtons = screen.getAllByRole('button', { name: /revoke/i })
      expect(revokeButtons).toHaveLength(1)
    })
  })

  it('opens create key modal when Create Key is clicked', async () => {
    vi.mocked(api.get).mockResolvedValue([])
    renderWithProviders(<ApiKeys />, { session: mockSession() })

    await waitFor(() => screen.getByText(/no api keys yet/i))

    await userEvent.click(screen.getByRole('button', { name: /create key/i }))
    expect(screen.getByText('Create API Key')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/key name/i)).toBeInTheDocument()
  })

  it('closes modal when Cancel is clicked', async () => {
    vi.mocked(api.get).mockResolvedValue([])
    renderWithProviders(<ApiKeys />, { session: mockSession() })

    await waitFor(() => screen.getByText(/no api keys yet/i))
    await userEvent.click(screen.getByRole('button', { name: /create key/i }))
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))

    expect(screen.queryByText('Create API Key')).not.toBeInTheDocument()
  })

  it('shows new key banner after successful creation', async () => {
    vi.mocked(api.get).mockResolvedValue([])
    vi.mocked(api.post).mockResolvedValue({
      id: 'key-new',
      name: 'My Key',
      key: 'vz-sk_fullkeyhere',
      key_prefix: 'vz-sk_fu',
      created_at: '2024-01-01T00:00:00Z',
    })

    renderWithProviders(<ApiKeys />, { session: mockSession() })

    await waitFor(() => screen.getByText(/no api keys yet/i))
    await userEvent.click(screen.getByRole('button', { name: /create key/i }))
    await userEvent.type(screen.getByPlaceholderText(/key name/i), 'My Key')
    await userEvent.click(screen.getByRole('button', { name: /^create$/i }))

    await waitFor(() => {
      expect(screen.getByText(/copy it now/i)).toBeInTheDocument()
      expect(screen.getByText('vz-sk_fullkeyhere')).toBeInTheDocument()
    })
  })

  it('dismisses the key banner when Dismiss is clicked', async () => {
    vi.mocked(api.get).mockResolvedValue([])
    vi.mocked(api.post).mockResolvedValue({
      id: 'key-new', name: 'Key', key: 'vz-sk_abc', key_prefix: 'vz-sk_ab',
      created_at: '2024-01-01T00:00:00Z',
    })

    renderWithProviders(<ApiKeys />, { session: mockSession() })
    await waitFor(() => screen.getByText(/no api keys yet/i))
    await userEvent.click(screen.getByRole('button', { name: /create key/i }))
    await userEvent.click(screen.getByRole('button', { name: /^create$/i }))
    await waitFor(() => screen.getByText(/copy it now/i))

    await userEvent.click(screen.getByRole('button', { name: /dismiss/i }))
    expect(screen.queryByText(/copy it now/i)).not.toBeInTheDocument()
  })
})
