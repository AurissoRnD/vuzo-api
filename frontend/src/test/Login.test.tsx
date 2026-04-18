import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Login from '../pages/Login'
import { renderWithProviders } from './renderWithProviders'
import { supabase } from '../lib/supabase'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders email and password fields', () => {
    renderWithProviders(<Login />)
    expect(screen.getByPlaceholderText('you@example.com')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument()
  })

  it('renders the sign in button', () => {
    renderWithProviders(<Login />)
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('has a link to the register page', () => {
    renderWithProviders(<Login />)
    expect(screen.getByRole('link', { name: /create one/i })).toBeInTheDocument()
  })

  it('navigates to / on successful login', async () => {
    vi.mocked(supabase.auth.signInWithPassword).mockResolvedValueOnce({
      data: { user: null, session: null },
      error: null,
    } as any)

    renderWithProviders(<Login />)

    await userEvent.type(screen.getByPlaceholderText('you@example.com'), 'test@example.com')
    await userEvent.type(screen.getByPlaceholderText('••••••••'), 'password123')
    fireEvent.submit(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/')
    })
  })

  it('shows error message on failed login', async () => {
    vi.mocked(supabase.auth.signInWithPassword).mockResolvedValueOnce({
      data: { user: null, session: null },
      error: { message: 'Invalid login credentials' } as any,
    } as any)

    renderWithProviders(<Login />)

    await userEvent.type(screen.getByPlaceholderText('you@example.com'), 'bad@example.com')
    await userEvent.type(screen.getByPlaceholderText('••••••••'), 'wrongpass')
    fireEvent.submit(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText('Invalid login credentials')).toBeInTheDocument()
    })
  })

  it('disables the button while submitting', async () => {
    vi.mocked(supabase.auth.signInWithPassword).mockImplementation(
      () => new Promise(() => {}) // never resolves
    )

    renderWithProviders(<Login />)

    await userEvent.type(screen.getByPlaceholderText('you@example.com'), 'test@example.com')
    await userEvent.type(screen.getByPlaceholderText('••••••••'), 'password123')
    fireEvent.submit(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled()
    })
  })
})
