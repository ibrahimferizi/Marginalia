import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import { API_BASE } from '../api'

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
      throw new Error('Invalid username or password')
    }
    username.value = usernameInput
  }

  async function logout() {
    await fetch(`${API_BASE}/accounts/logout/`, {
      method: 'POST',
      credentials: 'include',
    })
    username.value = null
  }

  async function fetchCurrentUser() {
    const response = await fetch(`${API_BASE}/accounts/me/`, {
      credentials: 'include',
    })
    if (response.ok) {
      const data = await response.json()
      username.value = data.username
    } else {
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
      throw new Error(Array.isArray(firstError) ? firstError[0] : 'Registration failed')
    }
  }

  return { username, isLoggedIn, login, logout, fetchCurrentUser, register }
})