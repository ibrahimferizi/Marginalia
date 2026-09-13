<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { API_BASE } from '../api'
import BookShelf from '../components/BookShelf.vue'
import { usePagedBooks } from '../composables/usePagedBooks'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const mode = ref('hybrid')
const source = ref('')
const { books, count, sources, next, previous, loading, error, load, clear } = usePagedBooks()

function filter() {
  router.push({ name: 'recommendations', query: { mode: mode.value, ...(source.value ? { source: source.value } : {}) } })
}

function page(url) {
  router.push({ query: { ...route.query, page: new URL(url).searchParams.get('page') || '1' } })
}

watch(() => [route.query, auth.username], ([params]) => {
  mode.value = ['hybrid', 'content', 'collaborative'].includes(params.mode) ? params.mode : 'hybrid'
  source.value = String(params.source ?? '')
  if (!auth.isLoggedIn) { clear(); return }
  const query = new URLSearchParams({ mode: mode.value, page: String(params.page || '1') })
  if (source.value) query.set('source', source.value)
  load(`${API_BASE}/books/explore/?${query}`)
}, { immediate: true })
</script>

<template>
  <main>
    <h1>Explore your recommendations</h1>
    <p v-if="!auth.isLoggedIn"><RouterLink to="/login">Log in</RouterLink> to explore your recommendations.</p>
    <template v-else>
      <p>Your recommendation shortlist, with different ways to discover a match.</p>
      <label>Discover through
        <select v-model="mode" @change="filter">
          <option value="hybrid">Your personal mix</option>
          <option value="content">Themes you gravitate toward</option>
          <option value="collaborative">Reader connections</option>
        </select>
      </label>
      <label>Reader connections from
        <select v-model="source" @change="filter">
          <option value="">All your books</option>
          <option v-if="source && !sources.some(item => String(item.id) === source)" :value="source">Selected book</option>
          <option v-for="item in sources" :key="item.id" :value="String(item.id)">{{ item.title }}</option>
        </select>
      </label>
      <p v-if="loading" role="status">Finding your matches...</p>
      <p v-else-if="error" role="alert">{{ error }}</p>
      <template v-else>
        <p v-if="!count">No matches for this selection. Try another view or rate more books.</p>
        <p v-else>{{ count }} recommendations in this shortlist</p>
        <BookShelf :books="books" reasons show-sources :mode="mode" />
        <button :disabled="!previous" @click="page(previous)">Previous</button>
        <button :disabled="!next" @click="page(next)">Next</button>
      </template>
    </template>
  </main>
</template>
