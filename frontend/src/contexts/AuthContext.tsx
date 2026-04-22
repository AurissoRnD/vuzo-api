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
    // If the URL contains hash tokens (from dashboard_url), Supabase processes
    // them asynchronously. INITIAL_SESSION fires with null before that completes,
    // which would incorrectly show "Session expired". Skip that null event and
    // wait for SIGNED_IN / TOKEN_REFRESHED to arrive instead.
    const hasHashTokens = window.location.hash.includes('access_token=')

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        if (event === 'INITIAL_SESSION' && session === null && hasHashTokens) {
          return
        }
        setSession(session)
        setLoading(false)
      }
    )

    // Safety valve: if hash processing never resolves (expired/revoked tokens),
    // unblock the UI after 5 s so the user sees "Session expired" rather than
    // a spinner forever.
    const timeout = setTimeout(() => setLoading(false), 5000)

    return () => {
      subscription.unsubscribe()
      clearTimeout(timeout)
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
