import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'

interface Balance {
  balance: number
}

export default function ThankYou() {
  const [params] = useSearchParams()
  const status = params.get('status')
  const message = params.get('message')
  const txn = params.get('txn')

  const [balance, setBalance] = useState<number | null>(null)
  const isTestMode = params.get('mode') === 'test' || !!sessionStorage.getItem('sct_test_mode_token')

  useEffect(() => {
    if (status === 'error') return
    let cancelled = false
    const refresh = async () => {
      try {
        const res = await api.get<Balance>('/billing/balance')
        if (!cancelled) setBalance(res.balance)
      } catch {
        // ignore
      }
    }
    refresh()
    const t = setTimeout(refresh, 3000)
    return () => {
      cancelled = true
      clearTimeout(t)
    }
  }, [status])

  const isError = status === 'error'

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-950 px-4">
      <div className="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-2xl p-8 text-center">
        {isTestMode && (
          <div className="mb-4 bg-amber-500/10 border border-amber-500/30 text-amber-300 rounded-lg px-4 py-2 text-xs font-medium">
            Test mode: this was not a real charge
          </div>
        )}
        {isError ? (
          <>
            <div className="text-3xl mb-3">!</div>
            <h1 className="text-xl font-semibold text-white mb-2">Payment couldn't be confirmed</h1>
            <p className="text-sm text-zinc-400 mb-6">
              {message ? decodeURIComponent(message) : 'Something went wrong while processing your payment.'}
            </p>
          </>
        ) : (
          <>
            <div className="text-3xl mb-3 text-emerald-400">✓</div>
            <h1 className="text-xl font-semibold text-white mb-2">Payment received</h1>
            <p className="text-sm text-zinc-400 mb-2">
              Thanks - your credits have been added to your account.
            </p>
            {balance !== null && (
              <p className="text-sm text-zinc-300 mb-2">
                New balance: <span className="text-indigo-400 font-medium">${balance.toFixed(4)}</span>
              </p>
            )}
            {txn && (
              <p className="text-xs text-zinc-500 mb-6 break-all">Transaction: {txn}</p>
            )}
          </>
        )}

        <Link
          to="/billing"
          className="inline-block px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg transition-colors"
        >
          Back to billing
        </Link>
      </div>
    </div>
  )
}
