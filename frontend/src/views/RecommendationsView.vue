<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { API_BASE } from '../api'
import BookShelf from '../components/BookShelf.vue'
import { usePagedBooks } from '../composables/usePagedBooks'

const route = useRoute()
const router = useRouter()
const resultsHeading = ref(null)
const auth = useAuthStore()
const choices = [
  { value: 'hybrid', label: 'Your personal mix', description: 'Reading themes and connections with other readers, together.' },
  { value: 'content', label: 'Themes you gravitate toward', description: 'Books that share themes with the books you’ve rated.' },
  { value: 'collaborative', label: 'Reader connections', description: 'Books connected through other readers’ ratings.' },
]
const mode = computed(() => choices.some(choice => choice.value === route.query.mode) ? route.query.mode : 'hybrid')
const source = computed(() => String(route.query.source ?? ''))
const currentPage = computed(() => Math.max(1, Number(route.query.page) || 1))
const activeChoice = computed(() => choices.find(choice => choice.value === mode.value))
const availableSources = ref([])
const { books, count, sources, next, previous, loading, error, load, clear } = usePagedBooks()
const sourceTitle = computed(() => availableSources.value.find(item => String(item.id) === source.value)?.title || 'Selected book')
function filter(nextMode = mode.value, nextSource = source.value) {
  router.push({ name: 'recommendations', query: { mode: nextMode, ...(nextSource ? { source: nextSource } : {}) } })
}
async function page(url) {
  await router.push({ query: { ...route.query, page: new URL(url).searchParams.get('page') || '1' } })
  resultsHeading.value?.scrollIntoView({ block: 'start' })
}
function loadResults() {
  if (!auth.isLoggedIn) { clear(); availableSources.value = []; return }
  const query = new URLSearchParams({ mode: mode.value, page: String(currentPage.value) })
  if (source.value) query.set('source', source.value)
  load(`${API_BASE}/books/explore/?${query}`)
}
watch(() => auth.username, () => { availableSources.value = [] })
watch(() => [route.query, auth.username], loadResults, { immediate: true })
watch([sources, loading], ([items, waiting]) => { if (!waiting && !error.value) availableSources.value = items })
</script>

<template>
  <main class="discovery-page">
    <header class="discovery-heading"><p class="eyebrow">A little more like you</p><h1>Your next chapter.</h1><p class="muted">Follow a familiar thread, or find a connection you didn’t expect.</p></header>
    <div v-if="!auth.isLoggedIn" class="discovery-state"><h2>A reading list with you in mind.</h2><p>Log in and rate a few books to start finding your matches.</p><RouterLink class="button-link primary-button" to="/login">Log in to explore →</RouterLink></div>
    <template v-else>
      <div class="recommendation-modes" role="group" aria-label="Recommendation approach"><button v-for="choice in choices" :key="choice.value" :aria-pressed="mode === choice.value" @click="filter(choice.value)"><span class="mode-number" aria-hidden="true"></span><span class="mode-title">{{ choice.label }}</span><span class="mode-description">{{ choice.description }}</span></button></div>
      <div class="source-panel"><label for="recommendation-source">Reader connections from<select id="recommendation-source" :value="source" :disabled="loading || !availableSources.length && !source" @change="filter(mode, $event.target.value)"><option value="">All contributing books</option><option v-if="source && !availableSources.some(item => String(item.id) === source)" :value="source">{{ sourceTitle }}</option><option v-for="item in availableSources" :key="item.id" :value="String(item.id)">{{ item.title }}</option></select></label><p>Choose a book you rated to see its reader connections within this view.</p><button v-if="source" class="clear-filter" @click="filter(mode, '')">Clear book filter ×</button></div>
      <div ref="resultsHeading" class="results-toolbar"><div><h2>{{ activeChoice.label }}</h2><p class="result-count" role="status">{{ loading ? 'Finding your matches…' : error ? 'Recommendations unavailable' : `${count.toLocaleString()} recommendations in this shortlist` }}</p></div><RouterLink class="library-shortcut" to="/my-reading-list">Your library ↗</RouterLink></div>
      <p v-if="source" class="ranking-note">Reader connections from <strong>{{ sourceTitle }}</strong>. Results keep the order of your selected view.</p>
      <p v-else class="ranking-note">Open a book’s explanation to follow the connections behind it.</p>
      <div v-if="loading" class="discovery-state" aria-hidden="true"><span class="loading-line"></span><p>Bringing your shortlist together…</p></div>
      <div v-else-if="error" class="discovery-state"><h3>We couldn’t load your matches.</h3><p role="alert">{{ error }}</p><button @click="loadResults">Try again</button></div>
      <div v-else-if="!count" class="discovery-state"><h3>{{ source ? 'No connections in this selection.' : 'Your next match starts with a rating.' }}</h3><p>{{ source ? 'Clear the book filter or try another recommendation view.' : 'Try another view, or rate more books to give us a fuller picture of your reading.' }}</p><button v-if="source" @click="filter(mode, '')">Clear book filter</button><RouterLink v-else class="button-link" to="/search">Find books to rate →</RouterLink></div>
      <template v-else><BookShelf :books="books" reasons show-sources :mode="mode" /><nav v-if="next || previous" class="discovery-pagination" aria-label="Recommendation pages"><span>Page {{ currentPage }}</span><div><button :disabled="!previous" @click="page(previous)">← Previous</button><button :disabled="!next" @click="page(next)">Next →</button></div></nav></template>
    </template>
  </main>
</template>
