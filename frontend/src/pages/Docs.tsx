import { Link } from 'react-router-dom'
import LanguageTabs from '../components/docs/LanguageTabs'
import CodeBlock from '../components/docs/CodeBlock'

const API_BASE = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/v1`
  : '/v1'

export default function Docs() {
  const quickstartExamples = [
    {
      label: 'Vuzo SDK',
      language: 'python',
      code: `# pip install vuzo
from vuzo import Vuzo

client = Vuzo("vz-sk_your_key_here")

# Simple chat with kimi-k2.5
response = client.chat.complete("kimi-k2.5", "Hello!")
print(response)`,
    },
    {
      label: 'Python (OpenAI SDK)',
      language: 'python',
      code: `from openai import OpenAI

client = OpenAI(
    api_key="vz-sk_your_key_here",
    base_url="${API_BASE}"
)

response = client.chat.completions.create(
    model="kimi-k2.5",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)`,
    },
    {
      label: 'Python (requests)',
      language: 'python',
      code: `import requests

response = requests.post(
    "${API_BASE}/chat/completions",
    headers={"Authorization": "Bearer vz-sk_your_key_here"},
    json={
        "model": "kimi-k2.5",
        "messages": [{"role": "user", "content": "Hello!"}]
    }
)

data = response.json()
print(data["choices"][0]["message"]["content"])`,
    },
    {
      label: 'JavaScript',
      language: 'javascript',
      code: `const response = await fetch('${API_BASE}/chat/completions', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer vz-sk_your_key_here',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    model: 'kimi-k2.5',
    messages: [{role: 'user', content: 'Hello!'}]
  })
})

const data = await response.json()
console.log(data.choices[0].message.content)`,
    },
    {
      label: 'cURL',
      language: 'bash',
      code: `curl ${API_BASE}/chat/completions \\
  -H "Authorization: Bearer vz-sk_your_key_here" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "kimi-k2.5",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'`,
    },
  ]

  const streamingExamples = [
    {
      label: 'Python (OpenAI SDK)',
      language: 'python',
      code: `from openai import OpenAI

client = OpenAI(
    api_key="vz-sk_your_key_here",
    base_url="${API_BASE}"
)

stream = client.chat.completions.create(
    model="kimi-k2.5",
    messages=[{"role": "user", "content": "Count to 10"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")`,
    },
    {
      label: 'JavaScript',
      language: 'javascript',
      code: `const response = await fetch('${API_BASE}/chat/completions', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer vz-sk_your_key_here',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    model: 'gpt-4o-mini',
    messages: [{role: 'user', content: 'Count to 10'}],
    stream: true
  })
})

const reader = response.body.getReader()
const decoder = new TextDecoder()

while (true) {
  const { done, value } = await reader.read()
  if (done) break
  
  const chunk = decoder.decode(value)
  const lines = chunk.split('\\n').filter(line => line.trim())
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = line.slice(6)
      if (data === '[DONE]') break
      
      const json = JSON.parse(data)
      const content = json.choices[0]?.delta?.content
      if (content) process.stdout.write(content)
    }
  }
}`,
    },
  ]

  return (
    <div className="max-w-5xl">
      <div className="mb-10">
        <h1 className="text-4xl font-bold text-white mb-3">Documentation</h1>
        <p className="text-zinc-400 text-lg">
          Learn how to use your SimplerClaw API key. Your <code className="px-1.5 py-0.5 bg-zinc-800 border border-zinc-700 rounded text-sm text-indigo-400">vz-sk_</code> key gives you access to Moonshot's kimi-k2.5 model, tracked and billed through your SimplerClaw dashboard.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        <aside className="lg:col-span-1">
          <nav className="sticky top-8 space-y-1">
            <NavLink href="#getting-started">Getting Started</NavLink>
            <NavLink href="#authentication">Authentication</NavLink>
            <NavLink href="#making-requests">Making Requests</NavLink>
            <NavLink href="#streaming">Streaming</NavLink>
            <NavLink href="#models">Available Models</NavLink>
            <NavLink href="#response-format">Response Format</NavLink>
            <NavLink href="#errors">Error Handling</NavLink>
            <NavLink href="#rate-limits">Rate Limits</NavLink>
            <NavLink href="#sdks">SDKs & Tools</NavLink>
            <NavLink href="#openclaw">OpenClaw</NavLink>
          </nav>
        </aside>

        <div className="lg:col-span-3 space-y-12">
          <Section id="getting-started" title="Getting Started">
            <p className="text-zinc-300 mb-4">
              Your API key is automatically generated when you authenticate through the SimplerClaw installer. No manual sign-up required.
            </p>
            <ol className="list-decimal list-inside space-y-2 text-zinc-300 mb-6">
              <li>Run the SimplerClaw installer and log in or register</li>
              <li>Your <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs text-indigo-400">vz-sk_</code> key is issued automatically and injected into OpenClaw</li>
              <li>
                View or manage your keys on the <Link to="/api-keys" className="text-indigo-400 hover:text-indigo-300">API Keys</Link> page
              </li>
              <li>Make your first request using the examples below</li>
            </ol>
            <LanguageTabs examples={quickstartExamples} />
          </Section>

          <Section id="authentication" title="Authentication">
            <p className="text-zinc-300 mb-4">
              Vuzo uses API keys for authentication. Your API key starts with <code className="px-2 py-1 bg-zinc-900 border border-zinc-800 rounded text-sm text-indigo-400">vz-sk_</code> and should be kept secret.
            </p>
            <p className="text-zinc-300 mb-4">
              Include your API key in the <code className="px-2 py-1 bg-zinc-900 border border-zinc-800 rounded text-sm">Authorization</code> header:
            </p>
            <CodeBlock
              language="bash"
              code={`Authorization: Bearer vz-sk_your_api_key_here`}
            />
            <div className="mt-4 p-4 bg-amber-950/30 border border-amber-900/50 rounded-lg">
              <div className="flex gap-2">
                <svg className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div>
                  <p className="text-amber-200 font-medium text-sm">Keep your API key secure</p>
                  <p className="text-amber-300/80 text-sm mt-1">
                    Never share your API key or commit it to version control. Use environment variables in production.
                  </p>
                </div>
              </div>
            </div>
          </Section>

          <Section id="making-requests" title="Making Requests">
            <p className="text-zinc-300 mb-4">
              Vuzo is fully compatible with the OpenAI API format. Send requests to <code className="px-2 py-1 bg-zinc-900 border border-zinc-800 rounded text-sm">/v1/chat/completions</code> with your chosen model.
            </p>
            <h4 className="text-white font-semibold mb-3">Request Parameters</h4>
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden mb-6">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-800">
                    <th className="text-left px-4 py-3 text-zinc-400 font-medium">Parameter</th>
                    <th className="text-left px-4 py-3 text-zinc-400 font-medium">Type</th>
                    <th className="text-left px-4 py-3 text-zinc-400 font-medium">Description</th>
                  </tr>
                </thead>
                <tbody className="text-zinc-300">
                  <tr className="border-b border-zinc-800/50">
                    <td className="px-4 py-3 font-mono text-xs text-indigo-400">model</td>
                    <td className="px-4 py-3">string</td>
                    <td className="px-4 py-3">Model ID (e.g. "kimi-k2.5")</td>
                  </tr>
                  <tr className="border-b border-zinc-800/50">
                    <td className="px-4 py-3 font-mono text-xs text-indigo-400">messages</td>
                    <td className="px-4 py-3">array</td>
                    <td className="px-4 py-3">Array of message objects with role and content</td>
                  </tr>
                  <tr className="border-b border-zinc-800/50">
                    <td className="px-4 py-3 font-mono text-xs">temperature</td>
                    <td className="px-4 py-3">number</td>
                    <td className="px-4 py-3">Optional. Sampling temperature (0-2)</td>
                  </tr>
                  <tr className="border-b border-zinc-800/50">
                    <td className="px-4 py-3 font-mono text-xs">max_tokens</td>
                    <td className="px-4 py-3">number</td>
                    <td className="px-4 py-3">Optional. Maximum tokens to generate</td>
                  </tr>
                  <tr className="border-b border-zinc-800/50">
                    <td className="px-4 py-3 font-mono text-xs">stream</td>
                    <td className="px-4 py-3">boolean</td>
                    <td className="px-4 py-3">Optional. Enable streaming responses</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <h4 className="text-white font-semibold mb-3">Examples</h4>
            <LanguageTabs examples={quickstartExamples} />
          </Section>

          <Section id="streaming" title="Streaming Responses">
            <p className="text-zinc-300 mb-4">
              Stream responses token-by-token for real-time output. Set <code className="px-2 py-1 bg-zinc-900 border border-zinc-800 rounded text-sm">stream: true</code> in your request.
            </p>
            <LanguageTabs examples={streamingExamples} />
          </Section>

          <Section id="models" title="Available Models">
            <p className="text-zinc-300 mb-4">
              Your SimplerClaw key gives you access to Moonshot's <strong className="text-white">kimi-k2.5</strong> model. All requests are proxied through our infrastructure — no separate provider account needed.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <ModelCard
                provider="Moonshot"
                models={['kimi-k2.5']}
                available
              />
              <ModelCard
                provider="OpenAI"
                models={['gpt-4o', 'gpt-4o-mini', 'gpt-4.1']}
                comingSoon
              />
              <ModelCard
                provider="Google"
                models={['gemini-2.0-flash', 'gemini-2.5-pro']}
                comingSoon
              />
            </div>
            <Link
              to="/models"
              className="inline-flex items-center gap-2 text-indigo-400 hover:text-indigo-300 text-sm font-medium"
            >
              View full pricing details
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </Link>
          </Section>

          <Section id="response-format" title="Response Format">
            <p className="text-zinc-300 mb-4">
              Vuzo returns OpenAI-compatible responses with token usage information:
            </p>
            <CodeBlock
              language="json"
              code={`{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4o-mini",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hello! How can I help you today?"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 9,
    "total_tokens": 19
  }
}`}
            />
          </Section>

          <Section id="errors" title="Error Handling">
            <p className="text-zinc-300 mb-4">
              Vuzo uses standard HTTP status codes. Here are the most common errors:
            </p>
            <div className="space-y-3">
              <ErrorCard
                code="401"
                title="Unauthorized"
                description="Invalid or missing API key. Check your Authorization header."
              />
              <ErrorCard
                code="402"
                title="Payment Required"
                description="Insufficient credits. Top up your balance in the Billing page."
              />
              <ErrorCard
                code="429"
                title="Too Many Requests"
                description="Rate limit exceeded. Each key has a requests-per-minute limit."
              />
              <ErrorCard
                code="400"
                title="Bad Request"
                description="Invalid request format or unsupported model name."
              />
              <ErrorCard
                code="500"
                title="Server Error"
                description="An error occurred on our end. Try again or contact support."
              />
            </div>
          </Section>

          <Section id="rate-limits" title="Rate Limits">
            <p className="text-zinc-300 mb-4">
              Each API key has a default rate limit of <strong className="text-white">60 requests per minute</strong>. You can view your current usage on the <Link to="/usage" className="text-indigo-400 hover:text-indigo-300">Usage</Link> page.
            </p>
            <p className="text-zinc-300">
              If you need higher limits, contact support or create multiple API keys to distribute load.
            </p>
          </Section>

          <Section id="sdks" title="SDKs & Tools">
            <div className="p-4 bg-gradient-to-r from-indigo-950/50 to-purple-950/30 border border-indigo-900/50 rounded-lg mb-6">
              <div className="flex gap-3">
                <div className="bg-indigo-600 rounded-lg p-2.5 shrink-0">
                  <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                  </svg>
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-1 flex-wrap">
                    <h4 className="text-white font-semibold">Official Vuzo Python SDK (Recommended)</h4>
                    <a
                      href="https://pypi.org/project/vuzo/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-indigo-900/60 hover:bg-indigo-800/60 border border-indigo-700/50 rounded text-xs text-indigo-300 font-medium transition-colors"
                    >
                      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z"/>
                      </svg>
                      PyPI
                    </a>
                  </div>
                  <p className="text-indigo-300/90 text-sm mb-3">
                    Simpler API with built-in usage tracking, billing, and key management.
                  </p>
                  <CodeBlock
                    language="bash"
                    code="pip install vuzo"
                  />
                  <div className="mt-3">
                    <CodeBlock
                      language="python"
                      code={`from vuzo import Vuzo

client = Vuzo("vz-sk_your_key_here")

# Chat with kimi-k2.5
response = client.chat.complete("kimi-k2.5", "Hello!")
print(response)

# Check balance
balance = client.billing.get_balance()
print(f"Balance: \${balance}")`}
                    />
                  </div>
                  <div className="flex items-center gap-4 mt-3 flex-wrap">
                    <a
                      href="https://pypi.org/project/vuzo/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 text-indigo-400 hover:text-indigo-300 text-sm font-medium"
                    >
                      View on PyPI
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                    <a
                      href="https://github.com/AurissoRnD/vuzo-python"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 text-indigo-400 hover:text-indigo-300 text-sm font-medium"
                    >
                      GitHub
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                  </div>
                </div>
              </div>
            </div>

            <h4 className="text-white font-semibold mb-3 mt-8">Alternative: OpenAI SDK</h4>
            <p className="text-zinc-300 mb-4">
              The SimplerClaw API is OpenAI-compatible. You can use the official OpenAI SDK with your <code className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-xs text-indigo-400">vz-sk_</code> key by pointing it at our endpoint:
            </p>
            <div className="space-y-4 mb-6">
              <div>
                <h4 className="text-white font-semibold mb-2">Python</h4>
                <CodeBlock language="bash" code="pip install openai" />
              </div>
              <div>
                <h4 className="text-white font-semibold mb-2">Node.js</h4>
                <CodeBlock language="bash" code="npm install openai" />
              </div>
            </div>
            <CodeBlock
              language="python"
              code={`from openai import OpenAI

client = OpenAI(
    api_key="vz-sk_your_key_here",
    base_url="${API_BASE}"
)

response = client.chat.completions.create(
    model="kimi-k2.5",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)`}
            />
          </Section>

          <Section id="openclaw" title="OpenClaw Integration">
            <div className="flex items-center gap-3 mb-4">
              <span className="text-4xl" role="img" aria-label="lobster">🦞</span>
              <p className="text-zinc-300">
                <a href="https://openclaw.ai" target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:text-indigo-300 font-medium">OpenClaw</a> is the AI agent this dashboard is built for. The SimplerClaw installer automatically configures OpenClaw to use your <code className="px-1.5 py-0.5 bg-zinc-800 rounded text-xs text-indigo-400">vz-sk_</code> key — no manual setup needed.
              </p>
            </div>

            <div className="mb-4 p-3 bg-amber-950/30 border border-amber-900/50 rounded-lg">
              <div className="flex gap-2">
                <svg className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <p className="text-amber-300/90 text-sm">
                  <strong className="text-amber-200">SimplerClaw keys are currently for use within OpenClaw only.</strong> Direct API access outside of the SimplerClaw ecosystem is not yet supported.
                </p>
              </div>
            </div>

            <h4 className="text-white font-semibold mb-3">How It Works</h4>
            <p className="text-zinc-300 mb-3">
              The installer sets two environment variables in your OpenClaw config. OpenClaw routes all AI requests through SimplerClaw, and usage is billed to your credits automatically.
            </p>
            <div className="mb-3 p-3 bg-emerald-950/30 border border-emerald-900/50 rounded-lg">
              <div className="flex gap-2">
                <svg className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-emerald-300/90 text-sm">
                  <strong className="text-emerald-200">No separate AI provider account needed.</strong> The variable is named <code className="px-1.5 py-0.5 bg-emerald-900/50 rounded text-xs">OPENAI_API_KEY</code> because that's what OpenClaw's SDK looks for — but your <strong className="text-emerald-200">SimplerClaw key</strong> (<code className="px-1.5 py-0.5 bg-emerald-900/50 rounded text-xs">vz-sk_...</code>) goes in there. SimplerClaw handles everything from there.
                </p>
              </div>
            </div>
            <CodeBlock
              language="bash"
              code={`OPENAI_API_KEY="vz-sk_your_key_here"   # your SimplerClaw key
OPENAI_BASE_URL="${API_BASE}"           # set automatically by the installer`}
            />

            <h4 className="text-white font-semibold mt-6 mb-3">Available Model</h4>
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 mb-4">
              <div className="flex items-start gap-3">
                <span className="mt-0.5 flex-shrink-0 w-5 h-5 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
                  <svg className="w-3 h-3 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                </span>
                <div>
                  <p className="text-white font-medium text-sm">Moonshot — kimi-k2.5</p>
                  <p className="text-zinc-400 text-sm mt-0.5">The model powering all SimplerClaw sessions.</p>
                </div>
              </div>
            </div>

            <div className="p-4 bg-indigo-950/30 border border-indigo-900/50 rounded-lg">
              <div className="flex gap-2">
                <svg className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <p className="text-indigo-300/90 text-sm">
                  <strong className="text-indigo-200">More models coming soon.</strong> We're working on expanding the model lineup available through your SimplerClaw key.
                </p>
              </div>
            </div>
          </Section>
        </div>
      </div>
    </div>
  )
}

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-8">
      <h2 className="text-2xl font-bold text-white mb-4">{title}</h2>
      {children}
    </section>
  )
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      className="block px-3 py-2 text-sm text-zinc-400 hover:text-white hover:bg-zinc-900 rounded-lg transition-colors"
    >
      {children}
    </a>
  )
}

function ModelCard({ provider, models, comingSoon }: { provider: string; models: string[]; available?: boolean; comingSoon?: boolean }) {
  return (
    <div className={`bg-zinc-900 border rounded-lg p-4 ${comingSoon ? 'border-zinc-800/50 opacity-50' : 'border-zinc-800'}`}>
      <div className="flex items-center justify-between mb-3">
        <h4 className={`font-semibold text-sm ${comingSoon ? 'text-zinc-500' : 'text-white'}`}>{provider}</h4>
        {comingSoon && (
          <span className="px-2 py-0.5 bg-zinc-800 border border-zinc-700 rounded text-[10px] text-zinc-500 font-medium">
            Coming soon
          </span>
        )}
      </div>
      <ul className="space-y-1.5">
        {models.map((model) => (
          <li key={model} className={`text-xs font-mono ${comingSoon ? 'text-zinc-600' : 'text-zinc-400'}`}>
            {model}
          </li>
        ))}
      </ul>
    </div>
  )
}

function ErrorCard({ code, title, description }: { code: string; title: string; description: string }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <span className="px-2 py-1 bg-red-950/50 text-red-400 text-xs font-mono rounded border border-red-900/50">
          {code}
        </span>
        <div>
          <h4 className="text-white font-semibold text-sm">{title}</h4>
          <p className="text-zinc-400 text-sm mt-1">{description}</p>
        </div>
      </div>
    </div>
  )
}
