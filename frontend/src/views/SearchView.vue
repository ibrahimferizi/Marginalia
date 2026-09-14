<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { API_BASE } from '../api'
import BookShelf from '../components/BookShelf.vue'
import { usePagedBooks } from '../composables/usePagedBooks'

const route = useRoute()
const router = useRouter()
const resultsHeading = ref(null)
const query = ref('')
const mode = computed(() => route.query.mode === 'semantic' ? 'semantic' : 'keyword')
const submittedQuery = computed(() => String(route.query.q ?? '').trim())
const sort = computed(() => ['popular', 'relevance'].includes(route.query.sort) ? route.query.sort : mode.value === 'semantic' ? 'relevance' : 'popular')
const currentPage = computed(() => Math.max(1, Number(route.query.page) || 1))
const { books, count, next, previous, loading, error, load, clear } = usePagedBooks()
const emptySemantic = computed(() => mode.value === 'semantic' && !submittedQuery.value)

function loadResults() {
  if (emptySemantic.value) { clear(); return }
  const params = new URLSearchParams({ sort: sort.value, page: String(currentPage.value) })
  params.set(mode.value === 'semantic' ? 'q' : 'search', submittedQuery.value)
  load(`${API_BASE}/books/${mode.value === 'semantic' ? 'semantic_search/' : ''}?${params}`)
}
function search() {
  const q = query.value.trim()
  if (q === submittedQuery.value && currentPage.value === 1) { loadResults(); return }
  router.push({ name: 'search', query: { q, mode: mode.value, sort: sort.value } })
}
function changeMode(value) {
  if (value === mode.value) return
  router.push({ name: 'search', query: { q: query.value.trim(), mode: value, sort: value === 'semantic' ? 'relevance' : 'popular' } })
}
function changeSort(event) {
  router.push({ name: 'search', query: { q: submittedQuery.value, mode: mode.value, sort: event.target.value } })
}
async function page(url) {
  await router.push({ query: { ...route.query, page: new URL(url).searchParams.get('page') || '1' } })
  resultsHeading.value?.scrollIntoView({ block: 'start' })
}
watch(() => route.query, () => { query.value = submittedQuery.value; loadResults() }, { immediate: true })
</script>

<template>
  <main class="discovery-page">
    <header class="discovery-heading"><p class="eyebrow">Follow your curiosity</p><h1>Find your next book.</h1><p class="muted">A title you remember. An idea you want to explore.</p></header>
    <div class="search-panel">
      <div class="discovery-tabs" role="group" aria-label="Search mode"><button :aria-pressed="mode === 'keyword'" @click="changeMode('keyword')">Title or author</button><button :aria-pressed="mode === 'semantic'" @click="changeMode('semantic')">Themes &amp; ideas</button></div>
      <form class="search-form" role="search" @submit.prevent="search">
        <label class="search-input" for="book-query"><span class="visually-hidden">{{ mode === 'semantic' ? 'Describe a theme or idea' : 'Search by title or author' }}</span><input id="book-query" v-model="query" type="search" maxlength="500" :placeholder="mode === 'semantic' ? 'What would you like to read about?' : 'Search for a book or an author…'" /></label>
        <button class="primary-button" type="submit">Find books <span aria-hidden="true">→</span></button>
      </form>
      <p class="search-help">{{ mode === 'semantic' ? 'Describe a theme, mood or idea. Short, focused descriptions work best.' : 'Search the collection by title or author, or browse the most widely rated books below.' }}</p>
    </div>
    <div ref="resultsHeading" class="results-toolbar">
      <div><h2>{{ submittedQuery ? `Results for “${submittedQuery}”` : mode === 'semantic' ? 'Explore an idea' : 'Browse the collection' }}</h2><p class="result-count" role="status">{{ loading ? 'Finding books…' : error ? 'Results unavailable' : emptySemantic ? 'Start with a theme or a mood.' : `${count.toLocaleString()} ${mode === 'semantic' ? 'matches in this shortlist' : 'books found'}` }}</p></div>
      <label v-if="!emptySemantic" class="sort-control" for="search-sort">Sort by<select id="search-sort" :value="sort" @change="changeSort"><option value="popular">Most popular</option><option value="relevance">Best match</option></select></label>
    </div>
    <p v-if="!emptySemantic" class="ranking-note">{{ sort === 'popular' ? mode === 'semantic' ? 'Ordered by rating count within the matching shortlist.' : 'Ordered by number of ratings, not the average star score.' : mode === 'semantic' ? 'Ordered by similarity to your description, with exact title matches first.' : 'Exact titles appear first, followed by title and author matches.' }}</p>
    <div v-if="loading" class="discovery-state" aria-hidden="true"><span class="loading-line"></span><p>Looking through the collection…</p></div>
    <div v-else-if="error" class="discovery-state"><h3>We couldn’t load these books.</h3><p role="alert">{{ error }}</p><button @click="loadResults">Try again</button></div>
    <div v-else-if="emptySemantic" class="discovery-state"><h3>There’s a book for that feeling.</h3><p>Try a simple description, such as “friendship and loneliness”.</p></div>
    <div v-else-if="!count" class="discovery-state"><h3>No books found this time.</h3><p>{{ mode === 'semantic' ? 'Try a shorter description or search for a title instead.' : 'Check the spelling, try an author’s name, or use fewer words.' }}</p><button @click="router.push({ name: 'search' })">Browse all books</button></div>
    <template v-else>
      <BookShelf :books="books" />
      <nav v-if="next || previous" class="discovery-pagination" aria-label="Search results pages"><span>Page {{ currentPage }}</span><div><button :disabled="!previous" @click="page(previous)">← Previous</button><button :disabled="!next" @click="page(next)">Next →</button></div></nav>
    </template>
  </main>
</template>
