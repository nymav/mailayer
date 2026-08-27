export type Message = {
  id: number
  gmail_id: string
  thread_id: string
  sender_name: string
  sender_email: string
  sender_domain: string
  subject: string
  snippet: string
  body_text: string
  received_at: string
  is_read: boolean
  is_starred: boolean
  is_important: boolean
  is_inbox: boolean
  has_attachment: boolean
  list_unsubscribe: boolean
  category: string
  importance: number
  usefulness: number
  confidence: number
  action_required: boolean
  urgency: string
  summary: string
  reason: string
  classification_source: string
}

export type Job = {
  id: string
  name: string
  status: 'queued' | 'running' | 'done' | 'error'
  progress: number
  message: string
  result?: unknown
  error?: string | null
}
