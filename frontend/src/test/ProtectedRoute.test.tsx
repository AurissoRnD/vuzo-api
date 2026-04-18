import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import ProtectedRoute from '../components/ProtectedRoute'
import { renderWithProviders, mockSession } from './renderWithProviders'

function ChildPage() {
  return <div>Protected Content</div>
}

function LoginPage() {
  return <div>Login Page</div>
}

function renderRoute(authState: Parameters<typeof renderWithProviders>[1]) {
  return renderWithProviders(
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <ChildPage />
          </ProtectedRoute>
        }
      />
    </Routes>,
    authState
  )
}

describe('ProtectedRoute', () => {
  it('shows loading indicator while auth is resolving', () => {
    renderRoute({ loading: true, session: null })
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('redirects to /login when there is no session', () => {
    renderRoute({ loading: false, session: null })
    expect(screen.getByText('Login Page')).toBeInTheDocument()
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })

  it('renders children when session is present', () => {
    renderRoute({ loading: false, session: mockSession() })
    expect(screen.getByText('Protected Content')).toBeInTheDocument()
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument()
  })

  it('does not render children while still loading', () => {
    renderRoute({ loading: true, session: mockSession() })
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })
})
