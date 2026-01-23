import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchLabels, createLabel, updateLabel } from '../lib/api'

export function useLabels() {
  return useQuery({
    queryKey: ['labels'],
    queryFn: fetchLabels,
  })
}

export function useCreateLabel() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createLabel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['labels'] })
    },
  })
}

export function useUpdateLabel() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ name, data }: { name: string; data: { description: string; rules: any[] } }) =>
      updateLabel(name, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['labels'] })
    },
  })
}
