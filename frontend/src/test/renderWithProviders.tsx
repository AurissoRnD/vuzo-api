import { type ReactNode } from 'react'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthContext } from '../contexts/AuthContext'
import type { Session, User } from '@supabase/supabase-js'

interface AuthOverrides {
  session?: Session | null
  user?: User | null
  loading?: boolean
  signOut?: () => Promise<void>
}

export function renderWithProviders(
  ui: ReactNode,
  {
    session = null,
    user = null,
    loading = false,
    signOut = async () => {},
    initialPath = '/',
  }: AuthOverrides & { initialPath?: string } = {}
) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AuthContext.Provider value={{ session, user, loading, signOut }}>
        {ui}
      </AuthContext.Provider>
    </MemoryRouter>
  )
}

/** A minimal mock Session object */
export function mockSession(overrides: Partial<Session> = {}): Session {
  return {
    access_token: 'mock-access-token',
    refresh_token: 'mock-refresh-token',
    expires_in: 3600,
    token_type: 'bearer',
    user: {
      id: 'user-123',
      email: 'test@example.com',
      app_metadata: {},
      user_metadata: {},
      aud: 'authenticated',
      created_at: '2024-01-01T00:00:00Z',
    } as User,
    ...overrides,
  } as Session
}
