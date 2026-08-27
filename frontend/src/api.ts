const API = 'http://127.0.0.1:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  if (init?.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const res = await fetch(`${API}${path}`, { ...init, headers })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {}
    throw new Error(detail)
  }
  return res.json()
}

export const api = {
  status: () => request<any>('/api/status'),
  dashboard: (days = 30) => request<any>(`/api/dashboard?days=${days}`),
  messages: (days = 90, search = '', category = '') => request<any[]>(`/api/messages?days=${days}&search=${encodeURIComponent(search)}&category=${encodeURIComponent(category)}&limit=200`),
  message: (id: number) => request<any>(`/api/messages/${id}`),
  senders: (days = 90) => request<any[]>(`/api/senders?days=${days}`),
  subscriptions: (days = 90) => request<any[]>(`/api/subscriptions?days=${days}`),
  reviewLater: () => request<any[]>('/api/review-later'),
  connect: () => request<any>('/api/auth/connect', { method: 'POST' }),
  disconnect: () => request<any>('/api/auth/disconnect', { method: 'POST' }),
  fullSync: (days: number) => request<any>('/api/sync/full', { method: 'POST', body: JSON.stringify({ days, include_sent: true }) }),
  incrementalSync: () => request<any>('/api/sync/incremental', { method: 'POST' }),
  classify: (limit = 100) => request<any>(`/api/ai/classify-pending?limit=${limit}`, { method: 'POST' }),
  embed: (limit = 200) => request<any>(`/api/embeddings/index-pending?limit=${limit}`, { method: 'POST' }),
  job: (id: string) => request<any>(`/api/jobs/${id}`),
  addReview: (id: number) => request<any>(`/api/messages/${id}/review-later`, { method: 'POST', body: JSON.stringify({ priority: 'NORMAL', reason: '' }) }),
  removeReview: (id: number) => request<any>(`/api/messages/${id}/review-later`, { method: 'DELETE' }),
  feedback: (id: number, useful: boolean) => request<any>(`/api/messages/${id}/feedback`, { method: 'POST', body: JSON.stringify({ useful, category_override: '', note: '' }) }),
  chat: (query: string, days = 90) => request<any>('/api/chat', { method: 'POST', body: JSON.stringify({ query, days }) }),
}
