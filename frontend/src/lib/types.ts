export interface Rule {
  type: string
  pattern?: string
  keywords?: string[]
}

export interface Label {
  description: string
  rules: Rule[]
}

export interface Settings {
  llm_provider: string
  confidence_threshold: number
  max_emails_per_run: number
}

export interface LabelsResponse {
  labels: Record<string, Label>
  settings: Settings
}

export interface TestEmailResponse {
  matched_labels: string[]
  matched_rules: Array<{
    label: string
    rule: Rule
  }>
  confidence: number
  llm_used: boolean
  time_ms: number
}

export interface AnalyticsData {
  total_all_time: number
  total_today: number
  total_this_week: number
  by_label: Record<string, number>
  rule_classifications: number
  llm_classifications: number
  avg_confidence: number
}
