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

const CREDIT_AMOUNTS = [
  { label: '$10',  amount: 10,  note: null },
  { label: '$25',  amount: 25,  note: null },
  { label: '$50',  amount: 50,  note: null },
  { label: '$100', amount: 100, note: 'Most popular' },
  { label: '$150', amount: 150, note: null },
  { label: '$200', amount: 200, note: null },
  { label: '$300', amount: 300, note: 'Best value' },
]

export default function Billing() {
  const [balance, setBalance] = useState<number>(0)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedAmount, setSelectedAmount] = useState<number>(100)
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

  const handleCheckout = async () => {
    setCheckingOut(true)
    try {
      const result = await api.post<CheckoutResponse>('/billing/checkout', { amount: selectedAmount })
      window.open(result.checkout_url, '_blank')
      setTimeout(() => loadData(), 5000)
      setTimeout(() => loadData(), 15000)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Checkout failed')
    } finally {
      setCheckingOut(false)
    }
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
        <h3 className="text-lg font-semibold mb-1">Add Credits</h3>
        <p className="text-sm text-zinc-400 mb-5">Select an amount to top up your balance.</p>

        <div className="grid grid-cols-4 gap-3 mb-6">
          {CREDIT_AMOUNTS.map(({ label, amount, note }) => {
            const isSelected = selectedAmount === amount
            return (
              <button
                key={amount}
                onClick={() => setSelectedAmount(amount)}
                className={`relative flex flex-col items-center justify-center py-4 rounded-xl border font-medium transition-all ${
                  isSelected
                    ? 'bg-indigo-600/20 border-indigo-500 text-white'
                    : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:text-white'
                }`}
              >
                {note && (
                  <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-indigo-600 text-white text-[10px] font-semibold rounded-full whitespace-nowrap">
                    {note}
                  </span>
                )}
                <span className="text-lg">{label}</span>
              </button>
            )
          })}
        </div>

        <button
          onClick={handleCheckout}
          disabled={checkingOut}
          className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold rounded-xl transition-colors"
        >
          {checkingOut ? 'Redirecting...' : `Pay $${selectedAmount}`}
        </button>
        <p className="text-xs text-zinc-500 mt-3 text-center">Payments are processed securely via Polar.</p>
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
