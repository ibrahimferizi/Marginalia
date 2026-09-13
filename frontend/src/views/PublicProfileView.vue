<script setup>
import { ref, watch } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { API_BASE } from '../api'

const route = useRoute()
const profile = ref(null)
const reviews = ref([])
const loading = ref(false)
const loadingMore = ref(false)
const error = ref('')
const reviewError = ref('')
const nextPage = ref(null)
let requestVersion = 0

async function fetchReviews(url, version, append = false) {
  const response = await fetch(url)
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
    const response = await fetch(`${API_BASE}/accounts/${username}/`)
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

watch(() => route.params.username, loadProfile, { immediate: true })
</script>

<template>
  <main>
    <p v-if="loading">Loading profile...</p>
    <p v-else-if="error" role="alert">{{ error }}</p>
    <template v-else-if="profile">
      <h1>{{ profile.username }}</h1>
      <img v-if="profile.avatar_url" :src="profile.avatar_url" :alt="`${profile.username}'s avatar`" width="96" height="96" />
      <p v-if="profile.bio">{{ profile.bio }}</p>
      <p v-else>This reader hasn't added a bio yet.</p>
      <h2>Ratings and reviews</h2>
      <p v-if="reviewError" role="alert">{{ reviewError }}</p>
      <p v-else-if="!reviews.length">No ratings or reviews yet.</p>
      <ul>
        <li v-for="review in reviews" :key="review.id">
          <RouterLink :to="`/books/${review.book}`">{{ review.book_title }}</RouterLink>
          <span> — {{ review.rating }}/5</span>
          <p v-if="review.text">{{ review.text }}</p>
        </li>
      </ul>
      <button v-if="nextPage" :disabled="loadingMore" @click="loadMore">{{ loadingMore ? 'Loading...' : 'More reviews' }}</button>
    </template>
  </main>
</template>
