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
  dashboard: (_days = 30) => Promise.resolve({"total": 248, "unread": 53, "actionable": 17, "useful": 162, "low_value": 36, "daily": [{"date": "2026-09-01", "count": 6}, {"date": "2026-09-02", "count": 9}, {"date": "2026-09-03", "count": 3}, {"date": "2026-09-04", "count": 11}, {"date": "2026-09-05", "count": 7}, {"date": "2026-09-06", "count": 4}, {"date": "2026-09-07", "count": 12}, {"date": "2026-09-08", "count": 8}, {"date": "2026-09-09", "count": 6}, {"date": "2026-09-10", "count": 10}, {"date": "2026-09-11", "count": 5}, {"date": "2026-09-12", "count": 13}, {"date": "2026-09-13", "count": 7}, {"date": "2026-09-14", "count": 9}, {"date": "2026-09-15", "count": 4}, {"date": "2026-09-16", "count": 8}, {"date": "2026-09-17", "count": 6}, {"date": "2026-09-18", "count": 12}, {"date": "2026-09-19", "count": 10}, {"date": "2026-09-20", "count": 3}, {"date": "2026-09-21", "count": 7}, {"date": "2026-09-22", "count": 9}, {"date": "2026-09-23", "count": 11}, {"date": "2026-09-24", "count": 6}, {"date": "2026-09-25", "count": 8}, {"date": "2026-09-26", "count": 5}, {"date": "2026-09-27", "count": 14}, {"date": "2026-09-28", "count": 7}, {"date": "2026-09-29", "count": 6}, {"date": "2026-09-30", "count": 11}], "top_senders": [{"sender": "research@example.test", "count": 31}, {"sender": "team@example.test", "count": 27}, {"sender": "updates@example.test", "count": 24}], "top_domains": [{"domain": "example.test", "count": 82}, {"domain": "sample.test", "count": 43}], "categories": {"WORK": 96, "EDUCATION": 58, "NEWSLETTER": 41, "SECURITY": 17, "OTHER": 36}}),
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
