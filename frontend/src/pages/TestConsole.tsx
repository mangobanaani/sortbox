import { useState } from 'react'
import { testEmailClassification } from '../lib/api'
import { TestEmailResponse } from '../lib/types'

export function TestConsole() {
  const [sender, setSender] = useState('')
  const [subject, setSubject] = useState('')
  const [bodyPreview, setBodyPreview] = useState('')
  const [result, setResult] = useState<TestEmailResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    try {
      const response = await testEmailClassification({
        sender,
        subject,
        body_preview: bodyPreview,
      })
      setResult(response)
    } catch (error) {
      console.error('Failed to test email:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const loadSample = (sample: 'stripe' | 'newsletter' | 'security') => {
    const samples = {
      stripe: {
        sender: 'billing@stripe.com',
        subject: 'Invoice #1234',
        bodyPreview: 'Your invoice for January is ready. Amount: $49.00',
      },
      newsletter: {
        sender: 'news@techblog.com',
        subject: 'Weekly Tech Digest',
        bodyPreview: 'This weeks top articles about web development...',
      },
      security: {
        sender: 'security@github.com',
        subject: 'New login from Chrome on MacOS',
        bodyPreview: 'We detected a new login to your account...',
      },
    }
    const s = samples[sample]
    setSender(s.sender)
    setSubject(s.subject)
    setBodyPreview(s.bodyPreview)
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Test Console</h2>

      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Sample Emails
          </label>
          <div className="flex space-x-2">
            <button
              onClick={() => loadSample('stripe')}
              className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200"
            >
              Stripe Invoice
            </button>
            <button
              onClick={() => loadSample('newsletter')}
              className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200"
            >
              Newsletter
            </button>
            <button
              onClick={() => loadSample('security')}
              className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200"
            >
              Security Alert
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              From
            </label>
            <input
              type="email"
              value={sender}
              onChange={(e) => setSender(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded"
              placeholder="sender@example.com"
              required
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Subject
            </label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded"
              placeholder="Email subject"
              required
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Preview
            </label>
            <textarea
              value={bodyPreview}
              onChange={(e) => setBodyPreview(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded"
              rows={3}
              placeholder="Email body preview..."
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? 'Classifying...' : 'Classify Email'}
          </button>
        </form>
      </div>

      {result && (
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-bold mb-4">Results</h3>

          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">
                Matched Labels
              </span>
              <span className="text-sm text-gray-500">{result.time_ms}ms</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {result.matched_labels.length > 0 ? (
                result.matched_labels.map((label) => (
                  <span
                    key={label}
                    className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm"
                  >
                    {label}
                  </span>
                ))
              ) : (
                <span className="text-gray-500 text-sm">No labels matched</span>
              )}
            </div>
          </div>

          <div className="mb-4">
            <span className="text-sm font-medium text-gray-700">
              Confidence
            </span>
            <div className="mt-2 bg-gray-200 rounded-full h-2">
              <div
                className="bg-green-600 h-2 rounded-full"
                style={{ width: `${result.confidence * 100}%` }}
              />
            </div>
            <span className="text-sm text-gray-500">
              {(result.confidence * 100).toFixed(0)}%
            </span>
          </div>

          {result.matched_rules.length > 0 && (
            <div>
              <span className="text-sm font-medium text-gray-700 block mb-2">
                Matched Rules
              </span>
              <ul className="space-y-2">
                {result.matched_rules.map((mr, i) => (
                  <li key={i} className="text-sm text-gray-600 flex items-center">
                    <span className="text-green-600 mr-2">✓</span>
                    <span className="font-medium">{mr.label}</span>
                    <span className="mx-2">→</span>
                    <span>{mr.rule.type}</span>
                    {mr.rule.pattern && (
                      <span className="ml-2 font-mono text-xs">
                        {mr.rule.pattern}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-4 pt-4 border-t">
            <span className="text-sm text-gray-500">
              LLM Used: {result.llm_used ? 'Yes' : 'No'}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
