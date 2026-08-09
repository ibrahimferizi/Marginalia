<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'

const books = ref([])
const loading = ref(true)
const error = ref(null)
const search = ref('')
const nextUrl = ref(null)
const prevUrl = ref(null)
const count = ref(0)

const API_BASE = 'http://127.0.0.1:8000/api/books/'

async function fetchBooks(url) {
  loading.value = true
  error.value = null
  try {
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`)
    }
    const data = await response.json()
    books.value = data.results ?? data
    nextUrl.value = data.next ?? null
    prevUrl.value = data.previous ?? null
    count.value = data.count ?? books.value.length
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function runSearch() {
  const url = search.value
    ? `${API_BASE}?search=${encodeURIComponent(search.value)}`
    : API_BASE
  fetchBooks(url)
}

onMounted(() => {
  fetchBooks(API_BASE)
})
</script>

<template>
  <main>
    <h1>Marginalia</h1>

    <form @submit.prevent="runSearch">
      <input v-model="search" placeholder="Search by title or author" />
      <button type="submit">Search</button>
    </form>

    <p v-if="loading">Loading books...</p>
    <p v-else-if="error">Error: {{ error }}</p>

    <template v-else>
      <p>{{ count }} books found</p>

      <ul>
        <li v-for="book in books" :key="book.id">
          <RouterLink :to="`/books/${book.id}`">{{ book.title }}</RouterLink> — {{ book.author }}
        </li>
      </ul>

      <button :disabled="!prevUrl" @click="fetchBooks(prevUrl)">Previous</button>
      <button :disabled="!nextUrl" @click="fetchBooks(nextUrl)">Next</button>
    </template>
  </main>
</template>