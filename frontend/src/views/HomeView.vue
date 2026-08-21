<script setup>
import { ref, onMounted, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import placeholderCover from '@/assets/placeholder-cover.png'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const books = ref([])
const loading = ref(true)
const error = ref(null)
const search = ref('')
const nextUrl = ref(null)
const prevUrl = ref(null)
const count = ref(0)

const recommended = ref([])
const recommendedLoading = ref(false)
const recommendedError = ref(null)

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

async function fetchRecommended() {
  recommendedLoading.value = true
  recommendedError.value = null
  try {
    const response = await fetch(`${API_BASE}recommended/`, {
      credentials: 'include',
    })
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`)
    }
    recommended.value = await response.json()
  } catch (err) {
    recommendedError.value = err.message
  } finally {
    recommendedLoading.value = false
  }
}

function runSearch() {
  router.push({ path: '/', query: search.value ? { search: search.value } : {} })
}

watch(
  () => route.query.search,
  (searchQuery) => {
    search.value = searchQuery ?? ''
    const url = searchQuery
      ? `${API_BASE}?search=${encodeURIComponent(searchQuery)}`
      : API_BASE
    fetchBooks(url)
  },
  { immediate: true },
)

onMounted(() => {
  if (auth.isLoggedIn) {
    fetchRecommended()
  }
})
</script>

<template>
  <main>
    <h1>Marginalia</h1>

    <section v-if="auth.isLoggedIn">
      <h2>Recommended for you</h2>
      <p v-if="recommendedLoading">Loading recommendations...</p>
      <p v-else-if="recommendedError">Error: {{ recommendedError }}</p>
      <p v-else-if="recommended.length === 0">Rate a few books to get recommendations.</p>
      <ul v-else>
        <li v-for="book in recommended" :key="book.id">
          <img :src="book.cover_url || placeholderCover" :alt="book.title" width="60" />
          <RouterLink :to="`/books/${book.id}`">{{ book.title }}</RouterLink> — {{ book.author }}
        </li>
      </ul>
    </section>

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
          <img :src="book.cover_url || placeholderCover" :alt="book.title" width="60" />
          <RouterLink :to="`/books/${book.id}`">{{ book.title }}</RouterLink> — {{ book.author }}
        </li>
      </ul>

      <button :disabled="!prevUrl" @click="fetchBooks(prevUrl)">Previous</button>
      <button :disabled="!nextUrl" @click="fetchBooks(nextUrl)">Next</button>
    </template>
  </main>
</template>

<style scoped>
li img {
  width: 60px;
  height: 90px;
  object-fit: cover;
  border-radius: 2px;
  vertical-align: middle;
  margin-right: 0.5rem;
  margin-bottom: 0.5rem;
}
</style>