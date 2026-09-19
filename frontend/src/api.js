export const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api').replace(/\/$/, '')

let refreshRequest

export async function apiFetch(url, options = {}) {
  const requestOptions = { credentials: 'include', ...options }
  const response = await fetch(url, requestOptions)
  if (response.status !== 401 || requestOptions.credentials === 'omit') return response

  if (!refreshRequest) {
    refreshRequest = fetch(`${API_BASE}/accounts/token/refresh/`, {
      method: 'POST', credentials: 'include',
    }).finally(() => { refreshRequest = null })
  }
  const refreshed = await refreshRequest
  requestOptions.signal?.throwIfAborted()
  if (refreshed.ok) return fetch(url, requestOptions)
  if (refreshed.status === 400 || refreshed.status === 401) {
    if ((requestOptions.method ?? 'GET').toUpperCase() === 'GET') {
      return fetch(url, { ...requestOptions, credentials: 'omit' })
    }
  }
  return response
}
