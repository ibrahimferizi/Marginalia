<script setup>
import { ref, watch, onUnmounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { API_BASE } from '../api'
import ReaderAvatar from '../components/ReaderAvatar.vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const auth = useAuthStore()
const profile = ref(null)
const reviews = ref([])
const loading = ref(false)
const loadingMore = ref(false)
const error = ref('')
const reviewError = ref('')
const nextPage = ref(null)
let requestVersion = 0

async function fetchReviews(url, version, append = false) {
  const response = await fetch(url, { credentials: 'omit' })
  if (!response.ok) throw new Error('Could not load reviews')
  const data = await response.json()
  if (version !== requestVersion) return
  reviews.value = append ? [...reviews.value, ...(data.results ?? data)] : (data.results ?? data)
  nextPage.value = data.next ?? null
}

async function loadProfile() {
  const version = ++requestVersion
  loading.value = true
  loadingMore.value = false
  error.value = ''
  reviewError.value = ''
  profile.value = null
  reviews.value = []
  nextPage.value = null
  const username = encodeURIComponent(route.params.username)
  try {
    const response = await fetch(`${API_BASE}/accounts/${username}/`, { credentials: 'omit' })
    if (!response.ok) throw new Error(response.status === 404 ? 'Reader not found' : 'Could not load profile')
    const data = await response.json()
    if (version !== requestVersion) return
    profile.value = data
    try {
      await fetchReviews(`${API_BASE}/reviews/?username=${username}`, version)
    } catch (err) {
      if (version === requestVersion) reviewError.value = err.message
    }
  } catch (err) {
    if (version === requestVersion) error.value = err.message
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

async function loadMore() {
  if (!nextPage.value || loadingMore.value) return
  const version = requestVersion
  loadingMore.value = true
  reviewError.value = ''
  try {
    await fetchReviews(nextPage.value, version, true)
  } catch (err) {
    if (version === requestVersion) reviewError.value = err.message
  } finally {
    if (version === requestVersion) loadingMore.value = false
  }
}

async function retryReviews() {
  if (loadingMore.value) return
  const version = requestVersion
  loadingMore.value = true
  reviewError.value = ''
  try {
    await fetchReviews(`${API_BASE}/reviews/?username=${encodeURIComponent(route.params.username)}`, version)
  } catch (err) {
    if (version === requestVersion) reviewError.value = err.message
  } finally {
    if (version === requestVersion) loadingMore.value = false
  }
}

watch(() => route.params.username, loadProfile, { immediate: true })
onUnmounted(() => { requestVersion++ })
</script>

<template>
  <main class="public-profile-page">
    <p class="eyebrow">The readers of Marginalia</p>
    <p v-if="loading" role="status">Loading profile…</p>
    <div v-else-if="error" class="account-state"><h1>Reader profile</h1><p role="alert">{{ error }}</p><button @click="loadProfile">Try again</button></div>
    <template v-else-if="profile">
      <header class="public-reader-header">
        <ReaderAvatar :username="profile.username" :url="profile.avatar_url" />
        <div><h1>{{ profile.username }}</h1><p v-if="profile.bio" class="reader-bio">{{ profile.bio }}</p><p v-else class="muted">This reader hasn't added a bio yet.</p><RouterLink v-if="auth.username === profile.username" to="/profile">Edit my profile</RouterLink></div>
      </header>
      <section class="reader-reviews" aria-labelledby="reviews-heading">
        <h2 id="reviews-heading">Ratings &amp; reviews</h2>
        <div v-if="reviewError" class="account-state"><p role="alert">{{ reviewError }}</p><button v-if="!nextPage" :disabled="loadingMore" @click="retryReviews">{{ loadingMore ? 'Loading…' : 'Try again' }}</button></div>
        <p v-else-if="!reviews.length" class="account-state muted">No ratings or reviews yet.</p>
        <ul class="reader-review-list">
          <li v-for="review in reviews" :key="review.id">
            <div class="reader-review-heading"><h3><RouterLink :to="`/books/${review.book}`">{{ review.book_title }}</RouterLink></h3><span class="reader-rating" :aria-label="`${review.rating} out of 5 stars`">{{ review.rating }} / 5</span></div>
            <p v-if="review.text" class="reader-review-text">{{ review.text }}</p>
            <p v-else class="muted">Rated without a written review.</p>
          </li>
        </ul>
        <button v-if="nextPage" :disabled="loadingMore" @click="loadMore">{{ loadingMore ? 'Loading…' : reviewError ? 'Retry more reviews' : 'More reviews' }}</button>
      </section>
    </template>
  </main>
</template>
