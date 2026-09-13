<script setup>
import { ref, onMounted } from 'vue'

import { API_BASE } from '../api'

const bio = ref('')
const avatarUrl = ref('')
const username = ref('')
const loading = ref(true)
const error = ref(null)
const saving = ref(false)
const saveMessage = ref(null)
const stats = ref(null)
const statsError = ref('')

async function fetchStats() {
  try {
    const response = await fetch(`${API_BASE}/accounts/me/stats/`, { credentials: 'include' })
    if (!response.ok) throw new Error('Could not load reading stats')
    stats.value = await response.json()
  } catch (err) {
    statsError.value = err.message
  }
}

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
onMounted(fetchStats)
</script>

<template>
  <main>
    <h1>My Profile</h1>
    <RouterLink v-if="username" :to="{ name: 'public-profile', params: { username } }">View my public profile</RouterLink>

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
    <section v-if="stats">
      <h2>My reading stats</h2>
      <p>{{ stats.rated_books }} books rated · Average rating: {{ stats.average_rating ?? '—' }}</p>
      <ul>
        <li>Want to read: {{ stats.reading_list.want_to_read }}</li>
        <li>Reading: {{ stats.reading_list.reading }}</li>
        <li>Finished: {{ stats.reading_list.finished }}</li>
        <li>Dropped: {{ stats.reading_list.dropped }}</li>
      </ul>
      <p>Finished in {{ stats.year }}: {{ stats.finished_this_year }}</p>
      <p v-if="stats.finished_without_date">{{ stats.finished_without_date }} finished entries have no completion date and aren't included in the yearly total.</p>
      <h3>My ratings</h3>
      <ul>
        <li v-for="rating in [1, 2, 3, 4, 5]" :key="rating">{{ rating }} stars: {{ stats.rating_distribution[rating] }}</li>
      </ul>
    </section>
    <p v-else-if="statsError" role="alert">{{ statsError }}</p>
  </main>
</template>
