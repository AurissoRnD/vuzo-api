import { useEffect, useState } from 'react'
import { api } from '../lib/api'

interface Balance {
  balance: number
}

interface Transaction {
  id: string
  amount: number
  type: 'topup' | 'usage' | 'refund'
  description: string
  created_at: string
}

interface CheckoutResponse {
  checkout_url: string
}

const PRESET_AMOUNTS = [5, 10, 25, 50]

export default function Billing() {
  const [balance, setBalance] = useState<number>(0)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [customAmount, setCustomAmount] = useState('')
  const [checkingOut, setCheckingOut] = useState(false)

  const loadData = async () => {
    try {
      const [bal, txns] = await Promise.all([
        api.get<Balance>('/billing/balance'),
        api.get<Transaction[]>('/billing/transactions'),
      ])
      setBalance(bal.balance)
      setTransactions(txns)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [])

  const handleCheckout = async (amount: number) => {
    setCheckingOut(true)
    try {
      const result = await api.post<CheckoutResponse>('/billing/checkout', { amount })
      window.open(result.checkout_url, '_blank')
      // Poll for balance update after a delay
      setTimeout(() => loadData(), 5000)
      setTimeout(() => loadData(), 15000)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Checkout failed')
    } finally {
      setCheckingOut(false)
    }
  }

  const handleCustomCheckout = () => {
    const amount = parseFloat(customAmount)
    if (isNaN(amount) || amount <= 0) return
    handleCheckout(amount)
  }

  if (loading) return <div className="text-zinc-400">Loading...</div>

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6">Billing</h2>

      {/* Balance */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 mb-6">
        <div className="text-sm text-zinc-400 mb-1">Current Balance</div>
        <div className="text-4xl font-bold text-indigo-400">${balance.toFixed(4)}</div>
      </div>

      {/* Add Credits */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 mb-6">
        <h3 className="text-lg font-semibold mb-4">Add Credits</h3>

        {/* Preset tiers */}
        <div className="flex flex-wrap gap-3 mb-4">
          {PRESET_AMOUNTS.map((amount) => (
            <button
              key={amount}
              onClick={() => handleCheckout(amount)}
              disabled={checkingOut}
              className="px-6 py-3 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 border border-zinc-700 rounded-lg text-white font-medium transition-colors"
            >
              ${amount}
            </button>
          ))}
        </div>

        {/* Custom amount */}
        <div className="flex gap-3">
          <div className="relative flex-1 max-w-xs">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500">$</span>
            <input
              type="number"
              value={customAmount}
              onChange={(e) => setCustomAmount(e.target.value)}
              placeholder="Custom amount"
              min="1"
              step="0.01"
              className="w-full pl-7 pr-3 py-2.5 bg-zinc-800 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <button
            onClick={handleCustomCheckout}
            disabled={checkingOut || !customAmount}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium rounded-lg transition-colors"
          >
            {checkingOut ? 'Opening...' : 'Pay'}
          </button>
        </div>
        <p className="text-xs text-zinc-500 mt-2">Payments are processed securely via Polar.</p>
      </div>

      {/* Transaction History */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800">
          <h3 className="text-sm font-medium text-zinc-300">Transaction History</h3>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-zinc-400">
              <th className="text-left px-4 py-3 font-medium">Type</th>
              <th className="text-right px-4 py-3 font-medium">Amount</th>
              <th className="text-left px-4 py-3 font-medium">Description</th>
              <th className="text-left px-4 py-3 font-medium">Date</th>
            </tr>
          </thead>
          <tbody>
            {transactions.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-zinc-500">
                  No transactions yet.
                </td>
              </tr>
            ) : (
              transactions.map((tx) => (
                <tr key={tx.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                      tx.type === 'topup'
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : tx.type === 'refund'
                        ? 'bg-blue-500/10 text-blue-400'
                        : 'bg-zinc-700/50 text-zinc-400'
                    }`}>
                      {tx.type}
                    </span>
                  </td>
                  <td className={`px-4 py-3 text-right font-mono ${
                    tx.amount >= 0 ? 'text-emerald-400' : 'text-zinc-400'
                  }`}>
                    {tx.amount >= 0 ? '+' : ''}${tx.amount.toFixed(6)}
                  </td>
                  <td className="px-4 py-3 text-zinc-400 truncate max-w-xs">{tx.description}</td>
                  <td className="px-4 py-3 text-zinc-500 text-xs">
                    {new Date(tx.created_at).toLocaleString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
