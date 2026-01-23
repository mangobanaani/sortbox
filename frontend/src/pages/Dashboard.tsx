import { useLabels } from '../hooks/useLabels'

export function Dashboard() {
  const { data, isLoading, error } = useLabels()

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

  const labelCount = Object.keys(data?.labels || {}).length
  const totalRules = Object.values(data?.labels || {}).reduce(
    (sum: number, label: any) => sum + label.rules.length,
    0
  )
  const llmProvider = data?.settings?.llm_provider || 'unknown'

  return (
    <div className="px-4 py-6 sm:px-0">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Dashboard</h1>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-3 mb-8">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-500">Labels</div>
                <div className="mt-1 text-3xl font-semibold text-gray-900">
                  {labelCount}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-500">Rules</div>
                <div className="mt-1 text-3xl font-semibold text-gray-900">
                  {totalRules}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-500">
                  LLM Provider
                </div>
                <div className="mt-1 text-xl font-semibold text-gray-900 capitalize">
                  {llmProvider}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Quick Actions
        </h2>
        <div className="flex gap-4">
          <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
            Add Label
          </button>
          <button className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300">
            Test Email
          </button>
        </div>
      </div>
    </div>
  )
}
