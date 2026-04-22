import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import type { Session, User } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'

interface AuthState {
  session: Session | null
  user: User | null
  loading: boolean
  signOut: () => Promise<void>
}

export const AuthContext = createContext<AuthState>({
  session: null,
  user: null,
  loading: true,
  signOut: async () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    const init = async () => {
      // Parse hash tokens directly — more reliable than waiting for Supabase
      // to auto-detect them, which races against the INITIAL_SESSION event.
      // Check query params first, fall back to hash fragment.
      // SimplerClaw constructs the URL with #access_token= directly,
      // so we must handle both formats.
      const qp = new URLSearchParams(window.location.search)
      const hp = new URLSearchParams(window.location.hash.substring(1))
      const accessToken = qp.get('access_token') ?? hp.get('access_token')
      const refreshToken = qp.get('refresh_token') ?? hp.get('refresh_token')

      let resolvedSession = null

      if (accessToken && refreshToken) {
        // Both tokens present — set session directly (no network call needed)
        const { data } = await supabase.auth.setSession({
          access_token: accessToken,
          refresh_token: refreshToken,
        })
        resolvedSession = data.session
      } else if (refreshToken) {
        // Only refresh_token present — new flow from SimplerClaw keychain.
        // Exchanges the refresh_token for a fresh session via Supabase.
        const { data } = await supabase.auth.refreshSession({ refresh_token: refreshToken })
        resolvedSession = data.session
      } else {
        // No URL tokens — use existing session from localStorage
        const { data } = await supabase.auth.getSession()
        resolvedSession = data.session
      }

      // Clean tokens from URL bar regardless of which path was taken
      if (accessToken || refreshToken) {
        window.history.replaceState(null, '', window.location.pathname)
      }

      if (!cancelled) {
        setSession(resolvedSession)
        setLoading(false)
      }
    }

    init()

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        if (!cancelled) setSession(session)
      }
    )

    return () => {
      cancelled = true
      subscription.unsubscribe()
    }
  }, [])

  const signOut = async () => {
    await supabase.auth.signOut()
    setSession(null)
  }

  return (
    <AuthContext.Provider
      value={{
        session,
        user: session?.user ?? null,
        loading,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
