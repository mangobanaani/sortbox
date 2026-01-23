import { useState } from 'react'
import { useUpdateLabel } from '../hooks/useLabels'
import { Rule } from '../lib/types'
import { RuleEditor } from './RuleEditor'

interface Props {
  isOpen: boolean
  onClose: () => void
  labelName: string
  initialDescription: string
  initialRules: Rule[]
}

export function EditLabelDialog({
  isOpen,
  onClose,
  labelName,
  initialDescription,
  initialRules,
}: Props) {
  const [description, setDescription] = useState(initialDescription)
  const [rules, setRules] = useState<Rule[]>(initialRules)
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [isAddingRule, setIsAddingRule] = useState(false)
  const updateMutation = useUpdateLabel()

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await updateMutation.mutateAsync({
        name: labelName,
        data: { description, rules },
      })
      onClose()
    } catch (error) {
      console.error('Failed to update label:', error)
    }
  }

  const handleSaveRule = (rule: Rule) => {
    if (editingIndex !== null) {
      const newRules = [...rules]
      newRules[editingIndex] = rule
      setRules(newRules)
      setEditingIndex(null)
    } else {
      setRules([...rules, rule])
      setIsAddingRule(false)
    }
  }

  const handleDeleteRule = (index: number) => {
    setRules(rules.filter((_, i) => i !== index))
  }

  const handleCancelEdit = () => {
    setEditingIndex(null)
    setIsAddingRule(false)
  }

  const formatRuleDisplay = (rule: Rule) => {
    if (rule.type === 'from') {
      return `from: ${rule.pattern}`
    } else if (rule.type === 'subject_contains') {
      return `subject: ${rule.keywords?.join(', ')}`
    } else if (rule.type === 'has_header') {
      return `has header: ${rule.pattern}`
    }
    return rule.type
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-bold mb-4">Edit Label: {labelName}</h2>

        <form onSubmit={handleSubmit}>
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="e.g., Flight bookings and hotel reservations"
              rows={3}
              required
            />
          </div>

          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-3">
              Rules ({rules.length})
            </h3>

            {rules.length === 0 && !isAddingRule && (
              <p className="text-gray-500 text-sm mb-3">
                No rules defined. Add rules to classify emails automatically.
              </p>
            )}

            <ul className="space-y-2 mb-4">
              {rules.map((rule, index) => (
                <li key={index}>
                  {editingIndex === index ? (
                    <RuleEditor
                      rule={rule}
                      onSave={handleSaveRule}
                      onCancel={handleCancelEdit}
                    />
                  ) : (
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded border border-gray-200">
                      <span className="text-sm font-mono text-gray-700">
                        {formatRuleDisplay(rule)}
                      </span>
                      <div className="space-x-2">
                        <button
                          type="button"
                          onClick={() => setEditingIndex(index)}
                          className="px-3 py-1 text-sm text-blue-600 hover:text-blue-800"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteRule(index)}
                          className="px-3 py-1 text-sm text-red-600 hover:text-red-800"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  )}
                </li>
              ))}
            </ul>

            {isAddingRule && (
              <div className="mb-4">
                <RuleEditor onSave={handleSaveRule} onCancel={handleCancelEdit} />
              </div>
            )}

            {!isAddingRule && editingIndex === null && (
              <button
                type="button"
                onClick={() => setIsAddingRule(true)}
                className="px-4 py-2 text-sm bg-green-600 text-white rounded hover:bg-green-700"
              >
                Add Rule
              </button>
            )}
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={updateMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
