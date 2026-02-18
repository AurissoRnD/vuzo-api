import { useState } from 'react'
import CodeBlock from './CodeBlock'

interface LanguageExample {
  label: string
  language: string
  code: string
}

interface LanguageTabsProps {
  examples: LanguageExample[]
}

export default function LanguageTabs({ examples }: LanguageTabsProps) {
  const [activeIndex, setActiveIndex] = useState(0)

  return (
    <div>
      <div className="flex gap-2 mb-3 flex-wrap">
        {examples.map((example, index) => (
          <button
            key={index}
            onClick={() => setActiveIndex(index)}
            className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
              activeIndex === index
                ? 'bg-indigo-600 text-white'
                : 'bg-zinc-900 text-zinc-400 hover:text-white hover:bg-zinc-800 border border-zinc-800'
            }`}
          >
            {example.label}
          </button>
        ))}
      </div>
      <CodeBlock code={examples[activeIndex].code} language={examples[activeIndex].language} />
    </div>
  )
}
