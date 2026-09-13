<script setup>
import { watch } from 'vue'
import { RouterLink } from 'vue-router'
import { API_BASE } from '../api'
import { useAuthStore } from '@/stores/auth'
import BookShelf from '@/components/BookShelf.vue'
import { usePagedBooks } from '@/composables/usePagedBooks'

const auth = useAuthStore()
const { books: popular, loading, error, load } = usePagedBooks()
const { books: recommended, loading: recommendedLoading, error: recommendedError, load: loadRecommended, clear } = usePagedBooks()

function shuffle() {
  load(`${API_BASE}/books/popular/`)
}

watch(() => auth.username, () => {
  shuffle()
  if (auth.isLoggedIn) loadRecommended(`${API_BASE}/books/recommended/`)
  else clear()
}, { immediate: true })
</script>

<template>
  <main>
    <h1>Marginalia</h1>
    <section>
      <div class="shelf-heading">
        <h2>{{ auth.isLoggedIn ? 'Popular books you haven’t read' : 'Popular with readers' }}</h2>
        <button :disabled="loading" @click="shuffle">Shuffle books</button>
      </div>
      <p>A fresh selection from the most widely rated books.</p>
      <p v-if="loading" role="status">Loading books...</p>
      <p v-else-if="error" role="alert">{{ error }}</p>
      <BookShelf v-else :books="popular" horizontal />
    </section>
    <section v-if="auth.isLoggedIn">
      <div class="shelf-heading">
        <h2>Recommended for you</h2>
        <RouterLink :to="{ name: 'recommendations' }">Explore recommendations</RouterLink>
      </div>
      <p>Your personal mix, based on the books you rate.</p>
      <p v-if="recommendedLoading" role="status">Loading recommendations...</p>
      <p v-else-if="recommendedError" role="alert">{{ recommendedError }}</p>
      <p v-else-if="!recommended.length">Rate a few books to get recommendations.</p>
      <BookShelf v-else :books="recommended" horizontal reasons />
    </section>
    <p><RouterLink :to="{ name: 'search' }">Search the collection</RouterLink></p>
  </main>
</template>

<style scoped>
section { margin-bottom: 2rem; }
.shelf-heading { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
</style>
