import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import { API_BASE, apiFetch } from '../api'

export const useAuthStore = defineStore('auth', () => {
  const username = ref(null)
  const isLoggedIn = computed(() => !!username.value)

  async function login(usernameInput, password) {
    const response = await fetch(`${API_BASE}/accounts/token/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ username: usernameInput, password }),
    })
    if (!response.ok) {
      throw new Error(response.status === 400 || response.status === 401 ? 'Invalid username or password.' : 'Could not log in right now. Please try again.')
    }
    username.value = usernameInput
  }

  async function logout() {
    const response = await fetch(`${API_BASE}/accounts/logout/`, {
      method: 'POST',
      credentials: 'include',
    })
    if (!response.ok) throw new Error('Could not log out. Please try again.')
    username.value = null
  }

  async function fetchCurrentUser() {
    try {
      const response = await apiFetch(`${API_BASE}/accounts/me/`)
      if (response.ok) {
        const data = await response.json()
        username.value = data.username
      } else {
        username.value = null
      }
    } catch {
      username.value = null
    }
  }

  async function register(usernameInput, email, password) {
    const response = await fetch(`${API_BASE}/accounts/register/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ username: usernameInput, email, password }),
    })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      const firstError = Object.values(data)[0]
      throw new Error(Array.isArray(firstError) ? firstError[0] : typeof firstError === 'string' ? firstError : 'Could not create your account. Please try again.')
    }
  }

  return { username, isLoggedIn, login, logout, fetchCurrentUser, register }
})
