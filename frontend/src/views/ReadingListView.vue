<script setup>
import { ref, onMounted, watch } from 'vue'
import { RouterLink } from 'vue-router'

const API_BASE = 'http://127.0.0.1:8000/api'

const entries = ref([])
const loading = ref(true)
const error = ref(null)
const statusFilter = ref('')

const STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'want_to_read', label: 'Want to Read' },
  { value: 'reading', label: 'Reading' },
  { value: 'finished', label: 'Finished' },
  { value: 'dropped', label: 'Dropped' },
]

async function fetchEntries() {
  loading.value = true
  error.value = null
  try {
    const url = statusFilter.value
      ? `${API_BASE}/reading-lists/?status=${statusFilter.value}`
      : `${API_BASE}/reading-lists/`
    const response = await fetch(url, { credentials: 'include' })
    if (!response.ok) throw new Error('Could not load reading list')
    const data = await response.json()
    entries.value = data.results ?? data
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

watch(statusFilter, fetchEntries)
onMounted(fetchEntries)
</script>

<template>
  <main>
    <h1>My Reading List</h1>

    <label>
      Filter:
      <select v-model="statusFilter">
        <option v-for="opt in STATUS_OPTIONS" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </option>
      </select>
    </label>

    <p v-if="loading">Loading...</p>
    <p v-else-if="error">{{ error }}</p>
    <p v-else-if="!entries.length">Nothing here yet.</p>

    <ul v-else>
      <li v-for="entry in entries" :key="entry.id">
        <RouterLink :to="`/books/${entry.book}`">{{ entry.book_title }}</RouterLink>
        — {{ entry.status }}
      </li>
    </ul>
  </main>
</template>