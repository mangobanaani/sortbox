import { useAnalytics } from '../hooks/useAnalytics'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16']

function StatCard({ title, value }: { title: string; value: number }) {
  return (
    <div className="bg-white overflow-hidden shadow rounded-lg">
      <div className="px-4 py-5 sm:p-6">
        <dt className="text-sm font-medium text-gray-500 truncate">{title}</dt>
        <dd className="mt-1 text-3xl font-semibold text-gray-900">{value}</dd>
      </div>
    </div>
  )
}

function LabelPieChart({ data }: { data: Record<string, number> }) {
  if (Object.keys(data).length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        No classification data yet
      </div>
    )
  }

  const chartData = Object.entries(data).map(([label, count]) => ({
    name: label,
    value: count,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={chartData}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={80}
          label={(entry) => `${entry.name}: ${entry.value}`}
        >
          {chartData.map((_, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const percent = (confidence * 100).toFixed(1)
  const colorClass = confidence >= 0.9 ? 'bg-green-100 text-green-800' :
                      confidence >= 0.7 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'

  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${colorClass}`}>
      Average Confidence: {percent}%
    </span>
  )
}

export function Analytics() {
  const { data, isLoading } = useAnalytics()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading analytics...</div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">No analytics data available</div>
      </div>
    )
  }

  const totalMethod = data.rule_classifications + data.llm_classifications
  const rulePercent = totalMethod > 0 ? (data.rule_classifications / totalMethod) * 100 : 0
  const llmPercent = totalMethod > 0 ? (data.llm_classifications / totalMethod) * 100 : 0

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Analytics</h2>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3 mb-8">
        <StatCard title="All Time" value={data.total_all_time} />
        <StatCard title="Today" value={data.total_today} />
        <StatCard title="This Week" value={data.total_this_week} />
      </div>

      {/* Classification Method */}
      <div className="bg-white shadow rounded-lg p-6 mb-8">
        <h3 className="text-lg font-semibold mb-4">Classification Method</h3>
        {totalMethod > 0 ? (
          <div>
            <div className="flex justify-between mb-2 text-sm">
              <span>Rule: {rulePercent.toFixed(0)}%</span>
              <span>LLM: {llmPercent.toFixed(0)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div
                className="bg-green-500 h-4 rounded-full transition-all duration-300"
                style={{ width: `${rulePercent}%` }}
              />
            </div>
            <div className="flex justify-between mt-2 text-xs text-gray-600">
              <span>{data.rule_classifications} classifications</span>
              <span>{data.llm_classifications} classifications</span>
            </div>
          </div>
        ) : (
          <div className="text-gray-500 text-center py-4">No classifications yet</div>
        )}
      </div>

      {/* Label Distribution */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <h3 className="text-lg font-semibold mb-4">Label Distribution</h3>
        <LabelPieChart data={data.by_label} />
      </div>

      {/* Average Confidence */}
      <div className="flex justify-center">
        <ConfidenceBadge confidence={data.avg_confidence} />
      </div>
    </div>
  )
}
