import { useState } from 'react'
import { useLabels } from '../hooks/useLabels'
import { CreateLabelDialog } from '../components/CreateLabelDialog'
import { EditLabelDialog } from '../components/EditLabelDialog'
import { Label } from '../lib/types'

export function Labels() {
  const { data, isLoading, error } = useLabels()
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [editingLabel, setEditingLabel] = useState<{
    name: string
    label: Label
  } | null>(null)

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-red-500">Error: {error.message}</div>
      </div>
    )
  }

  const labels = data?.labels || {}

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Labels</h1>
        <button
          onClick={() => setIsCreateOpen(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Add Label
        </button>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <ul className="divide-y divide-gray-200">
          {Object.entries(labels).map(([name, label]) => {
            const typedLabel = label as Label
            return (
            <li key={name} className="p-6 hover:bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {name}
                  </h3>
                  <p className="text-sm text-gray-600 mt-1">
                    {typedLabel.description}
                  </p>
                  <div className="flex items-center mt-2 text-sm text-gray-500">
                    <span>
                      {typedLabel.rules.length} rule{typedLabel.rules.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                </div>
                <div className="ml-4">
                  <button
                    onClick={() => setEditingLabel({ name, label: typedLabel })}
                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                  >
                    Edit
                  </button>
                </div>
              </div>
            </li>
          )}
          )}
        </ul>
      </div>

      {Object.keys(labels).length === 0 && (
        <div className="bg-white shadow rounded-lg p-12 text-center">
          <p className="text-gray-500">No labels found. Create your first label to get started.</p>
        </div>
      )}

      <CreateLabelDialog
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
      />

      {editingLabel && (
        <EditLabelDialog
          isOpen={true}
          onClose={() => setEditingLabel(null)}
          labelName={editingLabel.name}
          initialDescription={editingLabel.label.description}
          initialRules={editingLabel.label.rules}
        />
      )}
    </div>
  )
}
