<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { API_BASE } from '../api'
import BookShelf from '../components/BookShelf.vue'
import { usePagedBooks } from '../composables/usePagedBooks'

const route = useRoute()
const router = useRouter()
const query = ref('')
const mode = ref('keyword')
const sort = ref('popular')
const { books, count, next, previous, loading, error, load, clear } = usePagedBooks()

function search() {
  router.push({ name: 'search', query: { q: query.value.trim(), mode: mode.value, sort: sort.value } })
}

function page(url) {
  router.push({ query: { ...route.query, page: new URL(url).searchParams.get('page') || '1' } })
}

watch(() => route.query, (params) => {
  query.value = String(params.q ?? '')
  mode.value = params.mode === 'semantic' ? 'semantic' : 'keyword'
  sort.value = params.sort === 'relevance' ? 'relevance' : (params.sort === 'popular' ? 'popular' : mode.value === 'semantic' ? 'relevance' : 'popular')
  if (mode.value === 'semantic' && !query.value.trim()) { clear(); return }
  const searchParams = new URLSearchParams({ sort: sort.value, page: String(params.page || '1') })
  searchParams.set(mode.value === 'semantic' ? 'q' : 'search', query.value)
  load(`${API_BASE}/books/${mode.value === 'semantic' ? 'semantic_search/' : ''}?${searchParams}`)
}, { immediate: true })
</script>

<template>
  <main>
    <h1>Find your next book</h1>
    <form @submit.prevent="search">
      <label>Search <input v-model="query" maxlength="500" :placeholder="mode === 'semantic' ? 'Describe a theme or idea' : 'Book title or author'" /></label>
      <label>Search by
        <select v-model="mode" @change="sort = mode === 'semantic' ? 'relevance' : 'popular'">
          <option value="keyword">Title or author</option><option value="semantic">Themes and ideas</option>
        </select>
      </label>
      <label>Sort by <select v-model="sort"><option value="popular">Most popular</option><option value="relevance">Best match</option></select></label>
      <button>Search</button>
    </form>
    <p v-if="mode === 'semantic'">Explore a shortlist of semantic matches. “Most popular” sorts that shortlist by rating count.</p>
    <p v-if="loading" role="status">Searching...</p>
    <p v-else-if="error" role="alert">{{ error }}</p>
    <template v-else>
      <p v-if="mode === 'semantic' && !query.trim()">Describe what you'd like to read to begin.</p>
      <p v-else>{{ count }} {{ mode === 'semantic' ? 'semantic matches' : 'books found' }}</p>
      <BookShelf :books="books" />
      <button :disabled="!previous" @click="page(previous)">Previous</button>
      <button :disabled="!next" @click="page(next)">Next</button>
    </template>
  </main>
</template>
