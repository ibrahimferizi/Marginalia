<script setup>
import { ref, computed, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { API_BASE } from '../api'
import { useAuthStore } from '../stores/auth'
import { usePagedBooks } from '../composables/usePagedBooks'
import BookShelf from '../components/BookShelf.vue'
import LibraryShelf from '../components/LibraryShelf.vue'

const auth = useAuthStore()
const statusFilter = ref('')
const view = ref('grid')
try { if (localStorage.getItem('marginalia:library-view') === 'shelf') view.value = 'shelf' } catch {}
const { books: entries, count, next, previous, loading, error, load, clear } = usePagedBooks()
const statuses = [
  { value: '', label: 'All books' },
  { value: 'want_to_read', label: 'Want to read' },
  { value: 'reading', label: 'Reading' },
  { value: 'finished', label: 'Finished' },
  { value: 'dropped', label: 'Set aside' },
]
const books = computed(() => entries.value.map(entry => ({ ...entry.book_details, reading_status: statuses.find(status => status.value === entry.status)?.label })))
function setView(value) {
  view.value = value
  try { localStorage.setItem('marginalia:library-view', value) } catch {}
}
watch(() => [statusFilter.value, auth.username], () => {
  if (!auth.isLoggedIn) { clear(); return }
  load(`${API_BASE}/reading-lists/?${new URLSearchParams({ status: statusFilter.value })}`)
}, { immediate: true })
</script>

<template>
  <main>
    <div class="library-heading">
      <div><p class="eyebrow">Your personal collection</p><h1>My library<span>.</span></h1><p class="muted">The books you’ve read. The ones waiting for you.</p></div>
      <RouterLink class="button-link" to="/search">Find a book ↗</RouterLink>
    </div>
    <p v-if="!auth.isLoggedIn"><RouterLink to="/login">Log in</RouterLink> to browse your library.</p>
    <template v-else>
      <div class="library-toolbar">
        <div class="status-filters" role="group" aria-label="Filter by reading status">
          <button v-for="status in statuses" :key="status.value" :aria-pressed="statusFilter === status.value" @click="statusFilter = status.value">{{ status.label }}</button>
        </div>
        <div class="view-switch" role="group" aria-label="Library view">
          <button :aria-pressed="view === 'grid'" @click="setView('grid')">Grid</button>
          <button :aria-pressed="view === 'shelf'" @click="setView('shelf')">3D shelf</button>
        </div>
      </div>
      <p v-if="loading" class="empty-state" role="status">Opening your library...</p>
      <p v-else-if="error" class="empty-state" role="alert">{{ error }} <button @click="load(`${API_BASE}/reading-lists/?status=${statusFilter}`)">Try again</button></p>
      <div v-else-if="!books.length" class="empty-state"><h2>A little room for another story.</h2><p>Add books from their detail pages to see them here.</p><RouterLink to="/search">Explore the collection →</RouterLink></div>
      <template v-else>
        <div class="collection-count"><span>{{ count }} {{ count === 1 ? 'book' : 'books' }}</span><span v-if="count > books.length">Showing {{ books.length }} on this page</span></div>
        <LibraryShelf v-if="view === 'shelf'" :books="books" />
        <BookShelf v-else :books="books" />
        <div v-if="next || previous" class="pagination"><button :disabled="!previous" @click="load(previous)">Previous page</button><button :disabled="!next" @click="load(next)">Next page</button></div>
      </template>
    </template>
  </main>
</template>

<style scoped>
.library-heading { display: flex; justify-content: space-between; align-items: center; gap: 24px; flex-wrap: wrap; margin-bottom: 40px; }
h1 { margin-bottom: 16px; } h1 span { color: #8b9770; }
.library-toolbar { border-top: 1px solid var(--color-border); border-bottom: 1px solid var(--color-border); display: flex; justify-content: space-between; gap: 20px; align-items: center; padding: 16px 0; flex-wrap: wrap; }
.status-filters { display: flex; flex-wrap: wrap; gap: 4px; }
.status-filters button { border-color: transparent; padding: 8px 13px; margin: 0; }
.status-filters [aria-pressed='true'] { background: #e3e6d8; color: #344029; }
.view-switch { display: flex; padding: 3px; border: 1px solid var(--color-border); border-radius: 5px; }
.view-switch button { min-height: 32px; border: 0; padding: 5px 12px; margin: 0; }
.view-switch [aria-pressed='true'] { background: #fffdf7; box-shadow: 0 1px 4px #0001; }
.collection-count { display: flex; justify-content: space-between; font-size: 12px; color: var(--color-muted); margin: 22px 0; }
.empty-state { padding: 70px 0; text-align: center; }
.pagination { display: flex; justify-content: end; margin-top: 24px; }
</style>
