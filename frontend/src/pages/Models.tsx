import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'

interface ModelPricing {
  provider: string
  model_name: string
  vuzo_input_price_per_million: number
  vuzo_output_price_per_million: number
}

export default function Models() {
  const [models, setModels] = useState<ModelPricing[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get<ModelPricing[]>('/models')
      .then(setModels)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-zinc-400">Loading models...</div>

  const grouped = models.reduce<Record<string, ModelPricing[]>>((acc, m) => {
    if (!acc[m.provider]) acc[m.provider] = []
    acc[m.provider].push(m)
    return acc
  }, {})

  const providerLabels: Record<string, string> = {
    openai: 'OpenAI',
    anthropic: 'Anthropic',
    google: 'Google',
  }

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-2">Models & Pricing</h2>
      <p className="text-zinc-400 text-sm mb-6">
        All prices shown per 1,000,000 tokens.
      </p>

      <div className="bg-gradient-to-br from-indigo-950/50 to-purple-950/30 border border-indigo-900/50 rounded-xl p-6 mb-8">
        <div className="flex items-start gap-4">
          <div className="bg-indigo-600 rounded-lg p-3 shrink-0">
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-semibold text-white mb-2">New to Vuzo?</h3>
            <p className="text-zinc-300 text-sm mb-4">
              Learn how to integrate Vuzo into your application with our comprehensive documentation. 
              Get started with code examples in Python, JavaScript, and more.
            </p>
            <Link
              to="/docs"
              className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
            >
              View Documentation
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </Link>
          </div>
        </div>
      </div>

      {Object.entries(grouped).map(([provider, providerModels]) => (
        <div key={provider} className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-3">
            {providerLabels[provider] ?? provider}
          </h3>
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-400">
                  <th className="text-left px-4 py-3 font-medium">Model</th>
                  <th className="text-right px-4 py-3 font-medium">Input Price</th>
                  <th className="text-right px-4 py-3 font-medium">Output Price</th>
                </tr>
              </thead>
              <tbody>
                {providerModels.map((m) => (
                  <tr key={m.model_name} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                    <td className="px-4 py-3 font-mono text-white text-xs">{m.model_name}</td>
                    <td className="px-4 py-3 text-right text-indigo-400 font-medium">
                      ${m.vuzo_input_price_per_million.toFixed(4)}
                    </td>
                    <td className="px-4 py-3 text-right text-indigo-400 font-medium">
                      ${m.vuzo_output_price_per_million.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  )
}
