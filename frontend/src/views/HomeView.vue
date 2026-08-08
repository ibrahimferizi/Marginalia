<script setup>
import { ref, onMounted } from 'vue'

const books = ref([])
const loading = ref(true)
const error = ref(null)

onMounted(async () => {
  try {
    const response = await fetch('http://127.0.0.1:8000/api/books/')
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`)
    }
    const data = await response.json()
    books.value = data.results ?? data
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main>
    <h1>Marginalia</h1>

    <p v-if="loading">Loading books...</p>
    <p v-else-if="error">Error: {{ error }}</p>

    <ul v-else>
      <li v-for="book in books" :key="book.id">
        {{ book.title }} — {{ book.author }}
      </li>
    </ul>
  </main>
</template>