<script setup>
import { ref, onMounted } from 'vue'

const API_BASE = 'http://127.0.0.1:8000/api'

const bio = ref('')
const avatarUrl = ref('')
const username = ref('')
const loading = ref(true)
const error = ref(null)
const saving = ref(false)
const saveMessage = ref(null)

async function fetchProfile() {
  try {
    const response = await fetch(`${API_BASE}/accounts/me/`, { credentials: 'include' })
    if (!response.ok) throw new Error('Could not load profile')
    const data = await response.json()
    username.value = data.username
    bio.value = data.bio
    avatarUrl.value = data.avatar_url
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function saveProfile() {
  saving.value = true
  saveMessage.value = null
  try {
    const response = await fetch(`${API_BASE}/accounts/me/`, {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bio: bio.value, avatar_url: avatarUrl.value }),
    })
    if (!response.ok) throw new Error('Could not save profile')
    saveMessage.value = 'Saved.'
  } catch (err) {
    saveMessage.value = err.message
  } finally {
    saving.value = false
  }
}

onMounted(fetchProfile)
</script>

<template>
  <main>
    <h1>My Profile</h1>

    <p v-if="loading">Loading...</p>
    <p v-else-if="error">{{ error }}</p>

    <form v-else @submit.prevent="saveProfile">
      <p>Username: {{ username }}</p>

      <label>
        Bio:
        <textarea v-model="bio"></textarea>
      </label>

      <label>
        Avatar URL:
        <input v-model="avatarUrl" placeholder="https://..." />
      </label>

      <button type="submit" :disabled="saving">Save</button>
      <p v-if="saveMessage">{{ saveMessage }}</p>
    </form>
  </main>
</template>