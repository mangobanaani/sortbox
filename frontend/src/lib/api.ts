import { LabelsResponse, Rule, TestEmailResponse, AnalyticsData } from './types'

const API_BASE = '/api'

export async function fetchLabels(): Promise<LabelsResponse> {
  const response = await fetch(`${API_BASE}/labels`)
  if (!response.ok) {
    throw new Error('Failed to fetch labels')
  }
  return response.json()
}

export interface CreateLabelRequest {
  name: string
  description: string
  rules: Rule[]
}

export async function createLabel(data: CreateLabelRequest): Promise<void> {
  const response = await fetch(`${API_BASE}/labels`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to create label')
  }
}

export interface UpdateLabelRequest {
  description: string
  rules: Rule[]
}

export async function updateLabel(name: string, data: UpdateLabelRequest): Promise<void> {
  const response = await fetch(`${API_BASE}/labels/${name}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to update label')
  }
}

export async function testEmailClassification(email: {
  sender: string
  subject: string
  body_preview: string
}): Promise<TestEmailResponse> {
  const response = await fetch(`${API_BASE}/labels/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  if (!response.ok) {
    throw new Error('Failed to test email')
  }
  return response.json()
}

export async function fetchAnalytics(): Promise<AnalyticsData> {
  const response = await fetch(`${API_BASE}/analytics`)
  if (!response.ok) {
    throw new Error('Failed to fetch analytics')
  }
  return response.json()
}
