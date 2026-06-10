/**
 * Centralized API service.
 * All calls go to /api/... which Vite proxies to http://localhost:8000/api/v1/...
 */

const BASE = '/api'

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
export function isAdmin() {
  const u = getUser()
  return u?.role === 'admin'
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
    try {
      const data = await res.json()
      message = data.detail || JSON.stringify(data)
    } catch (_) { /* ignore */ }
    const err = new Error(message)
    err.status = res.status
    throw err
  }
  // 204 No Content
  if (res.status === 204) return null
  return res.json()
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export async function login(email, password) {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  const data = await handleResponse(res)
  setToken(data.access_token)
  return data
}

export async function register(email, password, full_name) {
  const res = await fetch(`${BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name }),
  })
  return handleResponse(res)
}

export async function getMe() {
  const res = await fetch(`${BASE}/auth/me`, { headers: authHeaders() })
  return handleResponse(res)
}

// ── Chat ─────────────────────────────────────────────────────────────────────

export async function askQuestion(question) {
  const res = await fetch(`${BASE}/chat/ask`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ question }),
  })
  return handleResponse(res)
}

export async function getChatStatus() {
  const res = await fetch(`${BASE}/chat/status`)
  return handleResponse(res)
}

// ── Documents (admin) ────────────────────────────────────────────────────────

export async function listDocuments() {
  const res = await fetch(`${BASE}/documents`, { headers: authHeaders() })
  return handleResponse(res)
}

export async function uploadDocument(file, onProgress) {
  const formData = new FormData()
  formData.append('file', file)

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${BASE}/documents/upload`)
    xhr.setRequestHeader('Authorization', `Bearer ${getToken()}`)

    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100))
      }
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText))
      } else {
        let msg = `HTTP ${xhr.status}`
        try { msg = JSON.parse(xhr.responseText).detail || msg } catch (_) {}
        const err = new Error(msg)
        err.status = xhr.status
        reject(err)
      }
    }
    xhr.onerror = () => reject(new Error('Network error'))
    xhr.send(formData)
  })
}

export async function ingestUrl(url, title = '') {
  const res = await fetch(`${BASE}/documents/ingest-url`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ url, title: title || undefined }),
  })
  return handleResponse(res)
}

export async function deleteDocument(id) {
  const res = await fetch(`${BASE}/documents/${id}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  return handleResponse(res)
}

// ── Admin — Unresolved Questions ─────────────────────────────────────────────

export async function listUnresolved(status = 'pending') {
  const res = await fetch(`${BASE}/admin/unresolved-questions?status=${status}`, {
    headers: authHeaders(),
  })
  return handleResponse(res)
}

export async function answerQuestion(id, answer) {
  const res = await fetch(`${BASE}/admin/unresolved-questions/${id}/answer`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ answer }),
  })
  return handleResponse(res)
}

export async function ignoreQuestion(id) {
  const res = await fetch(`${BASE}/admin/unresolved-questions/${id}/ignore`, {
    method: 'POST',
    headers: authHeaders(),
  })
  return handleResponse(res)
}

// ── Admin — Chat History ──────────────────────────────────────────────────────

export async function getAllChatHistory() {
  const res = await fetch(`${BASE}/admin/chat-history`, { headers: authHeaders() })
  return handleResponse(res)
}

// ── Admin — Users ─────────────────────────────────────────────────────────────

export async function listUsers() {
  const res = await fetch(`${BASE}/admin/users`, { headers: authHeaders() })
  return handleResponse(res)
}
