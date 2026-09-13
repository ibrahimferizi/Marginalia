<script setup>
import { API_BASE } from '../api'
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

const searchMode = ref('keyword')

const BOOKS_API = `${API_BASE}/books/`

async function fetchBooks(url) {
  loading.value = true
  error.value = null
  try {
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`)
    }
    const data = await response.json()
    if (Array.isArray(data)) {
      books.value = data
      nextUrl.value = null
      prevUrl.value = null
      count.value = data.length
    } else {
      books.value = data.results ?? data
      nextUrl.value = data.next ?? null
      prevUrl.value = data.previous ?? null
      count.value = data.count ?? books.value.length
    }
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
    const response = await fetch(`${BOOKS_API}recommended/`, {
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
  router.push({
    path: '/',
    query: search.value
      ? { search: search.value, mode: searchMode.value }
      : {},
  })
}

function formatReason(reason) {
  if (!reason) return ''
  if (reason.type === 'hybrid') {
    return `Matches your reading interests, with reader overlap from ${reason.source_book.title}`
  }
  if (reason.type === 'content') {
    if (reason.method === 'embedding') return 'Based on themes in books you rated'
    return `Because you enjoy ${reason.shared_genres.join(' and ')}`
  }
  if (reason.type === 'collaborative') {
    return `Readers of ${reason.source_book.title} also rated this`
  }
  return ''
}

watch(
  () => [route.query.search, route.query.mode],
  ([searchQuery, mode]) => {
    search.value = searchQuery ?? ''
    searchMode.value = mode ?? 'keyword'
    if (!searchQuery) {
      fetchBooks(BOOKS_API)
      return
    }
    const url =
      searchMode.value === 'semantic'
        ? `${BOOKS_API}semantic_search/?q=${encodeURIComponent(searchQuery)}`
        : `${BOOKS_API}?search=${encodeURIComponent(searchQuery)}`
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
          <RouterLink :to="`/books/${book.id}`">{{ book.title }}</RouterLink>” — {{ book.author }}
          <p v-if="book.recommendation_reason" class="reason">
            {{ formatReason(book.recommendation_reason) }}
          </p>
        </li>
      </ul>
    </section>

    <form @submit.prevent="runSearch">
      <input v-model="search" placeholder="Search by title or author" />
      <label>
        <input type="radio" value="keyword" v-model="searchMode" /> Keyword
      </label>
      <label>
        <input type="radio" value="semantic" v-model="searchMode" /> Smart search
      </label>
      <button type="submit">Search</button>
    </form>

    <p v-if="loading">Loading books...</p>
    <p v-else-if="error">Error: {{ error }}</p>

    <template v-else>
      <p>{{ count }} books found</p>

      <ul>
        <li v-for="book in books" :key="book.id">
          <img :src="book.cover_url || placeholderCover" :alt="book.title" width="60" />
          <RouterLink :to="`/books/${book.id}`">{{ book.title }}</RouterLink>” — {{ book.author }}
        </li>
      </ul>

      <template v-if="searchMode === 'keyword'">
        <button :disabled="!prevUrl" @click="fetchBooks(prevUrl)">Previous</button>
        <button :disabled="!nextUrl" @click="fetchBooks(nextUrl)">Next</button>
      </template>
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
