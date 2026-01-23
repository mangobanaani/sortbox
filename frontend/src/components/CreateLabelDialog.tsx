import { useState } from 'react'
import { useCreateLabel } from '../hooks/useLabels'

interface Props {
  isOpen: boolean
  onClose: () => void
}

export function CreateLabelDialog({ isOpen, onClose }: Props) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const createMutation = useCreateLabel()

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await createMutation.mutateAsync({
        name,
        description,
        rules: [],
      })
      onClose()
      setName('')
      setDescription('')
    } catch (error) {
      console.error('Failed to create label:', error)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-bold mb-4">Create New Label</h2>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="e.g., travel"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Lowercase, alphanumeric, hyphens only
            </p>
          </div>

          <div className="mb-4">
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

          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {createMutation.isPending ? 'Creating...' : 'Create Label'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
