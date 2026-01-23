import { useQuery } from '@tanstack/react-query'
import { fetchAnalytics } from '../lib/api'

export function useAnalytics() {
  return useQuery({
    queryKey: ['analytics'],
    queryFn: fetchAnalytics,
    refetchInterval: 30000, // Auto-refresh every 30 seconds
  })
}
