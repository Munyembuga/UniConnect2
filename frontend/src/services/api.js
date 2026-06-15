/**
 * Centralized API service.
 * Dev:  VITE_API_BASE_URL not set → '/api' (Vite proxy rewrites /api → /api/v1)
 * Prod: VITE_API_BASE_URL = 'https://uniconnect-backend.onrender.com/api/v1'
 */

const BASE = import.meta.env.VITE_API_BASE_URL || '/api'

// ── Token helpers ────────────────────────────────────────────────────────────

export function getToken()  { return localStorage.getItem('access_token') }
export function setToken(t) { localStorage.setItem('access_token', t) }
export function clearAuth() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
}
export function getUser() {
  try { return JSON.parse(localStorage.getItem('user') || 'null') } catch { return null }
}
export function isAdmin() { return getUser()?.role === 'admin' }

export function isTokenExpired() {
  const token = getToken()
  if (!token) return true
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp * 1000 < Date.now()
  } catch {
    return true
  }
}

function authHeaders(json = true) {
  const token = getToken()
  return {
    ...(json ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function handleResponse(res) {
  if (!res.ok) {
    let message = `HTTP ${res.status}`
    try { const d = await res.json(); message = d.detail || JSON.stringify(d) } catch (_) {}
    const err = new Error(message); err.status = res.status; throw err
  }
  if (res.status === 204) return null
  return res.json()
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export async function login(email, password) {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  const data = await handleResponse(res)
  setToken(data.access_token)
  return data
}

export async function register(email, password, full_name) {
  const res = await fetch(`${BASE}/auth/register`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name }),
  })
  return handleResponse(res)
}

export async function getMe() {
  return handleResponse(await fetch(`${BASE}/auth/me`, { headers: authHeaders() }))
}

export async function changePassword(old_password, new_password) {
  return handleResponse(await fetch(`${BASE}/auth/change-password`, {
    method: 'POST', headers: authHeaders(),
    body: JSON.stringify({ old_password, new_password }),
  }))
}

// ── Chat ─────────────────────────────────────────────────────────────────────

export async function askQuestion(question) {
  if (isTokenExpired()) clearAuth()
  const res = await fetch(`${BASE}/chat/ask`, {
    method: 'POST', headers: authHeaders(), body: JSON.stringify({ question }),
  })
  if (res.status === 401) {
    clearAuth()
    const retry = await fetch(`${BASE}/chat/ask`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    })
    return handleResponse(retry)
  }
  return handleResponse(res)
}

export async function getChatStatus() {
  return handleResponse(await fetch(`${BASE}/chat/status`))
}

// ── Documents ────────────────────────────────────────────────────────────────

export async function listDocuments() {
  return handleResponse(await fetch(`${BASE}/documents`, { headers: authHeaders() }))
}

export async function uploadDocument(file, onProgress) {
  const formData = new FormData()
  formData.append('file', file)
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${BASE}/documents/upload`)
    xhr.setRequestHeader('Authorization', `Bearer ${getToken()}`)
    if (onProgress) xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100))
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) { resolve(JSON.parse(xhr.responseText)) }
      else {
        let msg = `HTTP ${xhr.status}`
        try { msg = JSON.parse(xhr.responseText).detail || msg } catch (_) {}
        const err = new Error(msg); err.status = xhr.status; reject(err)
      }
    }
    xhr.onerror = () => reject(new Error('Network error'))
    xhr.send(formData)
  })
}

export async function ingestUrl(url, title = '') {
  return handleResponse(await fetch(`${BASE}/documents/ingest-url`, {
    method: 'POST', headers: authHeaders(),
    body: JSON.stringify({ url, title: title || undefined }),
  }))
}

export async function deleteDocument(id) {
  return handleResponse(await fetch(`${BASE}/documents/${id}`, {
    method: 'DELETE', headers: authHeaders(),
  }))
}

// ── Admin — Stats & Analytics ─────────────────────────────────────────────────

export async function getStats() {
  return handleResponse(await fetch(`${BASE}/admin/stats`, { headers: authHeaders() }))
}

export async function getQueryTrend(days = 7) {
  return handleResponse(await fetch(`${BASE}/admin/analytics/query-trend?days=${days}`, { headers: authHeaders() }))
}

export async function getCategoryBreakdown() {
  return handleResponse(await fetch(`${BASE}/admin/analytics/category-breakdown`, { headers: authHeaders() }))
}

export async function getTopTopics(limit = 8) {
  return handleResponse(await fetch(`${BASE}/admin/analytics/top-topics?limit=${limit}`, { headers: authHeaders() }))
}

export async function getRecentActivity(limit = 10) {
  return handleResponse(await fetch(`${BASE}/admin/analytics/recent-activity?limit=${limit}`, { headers: authHeaders() }))
}

// ── Admin — Unresolved Questions ──────────────────────────────────────────────

export async function listUnresolved(status = 'pending') {
  return handleResponse(await fetch(`${BASE}/admin/unresolved-questions?status=${status}`, { headers: authHeaders() }))
}

export async function answerQuestion(id, answer) {
  return handleResponse(await fetch(`${BASE}/admin/unresolved-questions/${id}/answer`, {
    method: 'POST', headers: authHeaders(), body: JSON.stringify({ answer }),
  }))
}

export async function ignoreQuestion(id) {
  return handleResponse(await fetch(`${BASE}/admin/unresolved-questions/${id}/ignore`, {
    method: 'POST', headers: authHeaders(),
  }))
}

export async function setQuestionStatus(id, status) {
  return handleResponse(await fetch(`${BASE}/admin/unresolved-questions/${id}/status`, {
    method: 'POST', headers: authHeaders(), body: JSON.stringify({ status }),
  }))
}

export async function pushToFaq(id, answer, category) {
  return handleResponse(await fetch(`${BASE}/admin/unresolved-questions/${id}/push-to-faq`, {
    method: 'POST', headers: authHeaders(),
    body: JSON.stringify({ answer, category }),
  }))
}

// ── Admin — Chat History ──────────────────────────────────────────────────────

export async function getAllChatHistory(skip = 0, limit = 200) {
  return handleResponse(await fetch(`${BASE}/admin/chat-history?skip=${skip}&limit=${limit}`, { headers: authHeaders() }))
}

// ── Admin — Users ─────────────────────────────────────────────────────────────

export async function listUsers(params = {}) {
  const qs = new URLSearchParams()
  if (params.search) qs.set('search', params.search)
  if (params.role)   qs.set('role', params.role)
  if (params.skip)   qs.set('skip', params.skip)
  if (params.limit)  qs.set('limit', params.limit)
  const query = qs.toString() ? `?${qs}` : ''
  return handleResponse(await fetch(`${BASE}/admin/users${query}`, { headers: authHeaders() }))
}

export async function createUser(email, password, full_name, role = 'student') {
  return handleResponse(await fetch(`${BASE}/admin/users`, {
    method: 'POST', headers: authHeaders(),
    body: JSON.stringify({ email, password, full_name, role }),
  }))
}

export async function updateUser(id, updates) {
  return handleResponse(await fetch(`${BASE}/admin/users/${id}`, {
    method: 'PUT', headers: authHeaders(), body: JSON.stringify(updates),
  }))
}

export async function deleteUser(id) {
  return handleResponse(await fetch(`${BASE}/admin/users/${id}`, {
    method: 'DELETE', headers: authHeaders(),
  }))
}

export async function suspendUser(id) {
  return handleResponse(await fetch(`${BASE}/admin/users/${id}/suspend`, {
    method: 'POST', headers: authHeaders(),
  }))
}

export async function activateUser(id) {
  return handleResponse(await fetch(`${BASE}/admin/users/${id}/activate`, {
    method: 'POST', headers: authHeaders(),
  }))
}

export async function resetUserPassword(id, new_password) {
  return handleResponse(await fetch(`${BASE}/admin/users/${id}/reset-password`, {
    method: 'POST', headers: authHeaders(),
    body: JSON.stringify({ new_password }),
  }))
}

export async function getUserQueryHistory(id, limit = 50) {
  return handleResponse(await fetch(`${BASE}/admin/users/${id}/query-history?limit=${limit}`, { headers: authHeaders() }))
}

export async function getUserStats(id) {
  return handleResponse(await fetch(`${BASE}/admin/users/${id}/stats`, { headers: authHeaders() }))
}

// ── Admin — FAQs ──────────────────────────────────────────────────────────────

export async function listFaqs(status = null, search = null) {
  const qs = new URLSearchParams()
  if (status) qs.set('status', status)
  if (search) qs.set('search', search)
  const query = qs.toString() ? `?${qs}` : ''
  return handleResponse(await fetch(`${BASE}/admin/faqs${query}`, { headers: authHeaders() }))
}

export async function createFaq(question, answer, category, status = 'active') {
  return handleResponse(await fetch(`${BASE}/admin/faqs`, {
    method: 'POST', headers: authHeaders(),
    body: JSON.stringify({ question, answer, category, status }),
  }))
}

export async function updateFaq(id, data) {
  return handleResponse(await fetch(`${BASE}/admin/faqs/${id}`, {
    method: 'PUT', headers: authHeaders(), body: JSON.stringify(data),
  }))
}

export async function deleteFaq(id) {
  return handleResponse(await fetch(`${BASE}/admin/faqs/${id}`, {
    method: 'DELETE', headers: authHeaders(),
  }))
}

// ── Admin — Export ────────────────────────────────────────────────────────────

export function buildExportUrl(type, params = {}) {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v) qs.set(k, v) })
  const query = qs.toString() ? `?${qs}` : ''
  return `${BASE}/admin/export/${type}${query}`
}

export async function downloadExport(type, params = {}) {
  const url = buildExportUrl(type, params)
  const res = await fetch(url, { headers: authHeaders(false) })
  if (!res.ok) throw new Error(`Export failed: HTTP ${res.status}`)
  const blob = await res.blob()
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  const ts = new Date().toISOString().slice(0, 10)
  link.download = `uniconnect_${type}_${ts}.csv`
  link.click()
  URL.revokeObjectURL(objectUrl)
}

// ── Admin — Settings ──────────────────────────────────────────────────────────

export async function getSettings() {
  return handleResponse(await fetch(`${BASE}/admin/settings`, { headers: authHeaders() }))
}

export async function saveSettings(settings) {
  return handleResponse(await fetch(`${BASE}/admin/settings`, {
    method: 'PUT', headers: authHeaders(),
    body: JSON.stringify({ settings }),
  }))
}
