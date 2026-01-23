import { useState } from 'react'
import { Rule } from '../lib/types'

interface Props {
  rule?: Rule
  onSave: (rule: Rule) => void
  onCancel: () => void
}

export function RuleEditor({ rule, onSave, onCancel }: Props) {
  const [ruleType, setRuleType] = useState(rule?.type || 'from')
  const [pattern, setPattern] = useState(rule?.pattern || '')
  const [keywords, setKeywords] = useState(
    rule?.keywords ? rule.keywords.join(', ') : ''
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const newRule: Rule = { type: ruleType }

    if (ruleType === 'from') {
      newRule.pattern = pattern
    } else if (ruleType === 'subject_contains') {
      newRule.keywords = keywords
        .split(',')
        .map((k) => k.trim())
        .filter((k) => k.length > 0)
    } else if (ruleType === 'has_header') {
      newRule.pattern = pattern
    }

    onSave(newRule)
  }

  return (
    <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Rule Type
          </label>
          <select
            value={ruleType}
            onChange={(e) => setRuleType(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          >
            <option value="from">From pattern</option>
            <option value="subject_contains">Subject contains</option>
            <option value="has_header">Has header</option>
          </select>
        </div>

        {ruleType === 'from' && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Pattern
            </label>
            <input
              type="text"
              value={pattern}
              onChange={(e) => setPattern(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="e.g., *@stripe.com"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Examples: *@domain.com, *@*.domain.com, *noreply@*
            </p>
          </div>
        )}

        {ruleType === 'subject_contains' && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Keywords (comma-separated)
            </label>
            <input
              type="text"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="e.g., invoice, receipt, payment"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Email subject must contain at least one keyword
            </p>
          </div>
        )}

        {ruleType === 'has_header' && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Header Name
            </label>
            <input
              type="text"
              value={pattern}
              onChange={(e) => setPattern(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="e.g., list-unsubscribe"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Check if email has this header (e.g., list-unsubscribe for newsletters)
            </p>
          </div>
        )}

        <div className="flex justify-end space-x-3">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-gray-700 border border-gray-300 rounded hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            {rule ? 'Update Rule' : 'Add Rule'}
          </button>
        </div>
      </form>
    </div>
  )
}
