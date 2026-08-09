<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const auth = useAuthStore()

const API_BASE = 'http://127.0.0.1:8000/api'

const book = ref(null)
const loading = ref(true)
const error = ref(null)

const reviews = ref([])
const reviewsLoading = ref(true)

const newRating = ref(5)
const newText = ref('')
const submitError = ref(null)
const submitting = ref(false)

const readingListEntry = ref(null)
const readingListLoading = ref(true)
const readingListError = ref(null)

const STATUS_OPTIONS = [
  { value: 'want_to_read', label: 'Want to Read' },
  { value: 'reading', label: 'Reading' },
  { value: 'finished', label: 'Finished' },
  { value: 'dropped', label: 'Dropped' },
]

async function fetchBook() {
  try {
    const response = await fetch(`${API_BASE}/books/${route.params.id}/`)
    if (!response.ok) throw new Error(`Request failed: ${response.status}`)
    book.value = await response.json()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function fetchReviews() {
  reviewsLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/reviews/?book=${route.params.id}`)
    const data = await response.json()
    reviews.value = data.results ?? data
  } finally {
    reviewsLoading.value = false
  }
}

async function submitReview() {
  submitError.value = null
  submitting.value = true
  try {
    const response = await fetch(`${API_BASE}/reviews/`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        book: route.params.id,
        rating: newRating.value,
        text: newText.value,
      }),
    })
    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.non_field_errors?.[0] ?? 'Could not submit review')
    }
    newText.value = ''
    await fetchReviews()
    await fetchBook()
  } catch (err) {
    submitError.value = err.message
  } finally {
    submitting.value = false
  }
}

async function fetchReadingListEntry() {
  if (!auth.isLoggedIn) {
    readingListLoading.value = false
    return
  }
  try {
    const response = await fetch(`${API_BASE}/reading-lists/?book=${route.params.id}`, {
      credentials: 'include',
    })
    const data = await response.json()
    const entries = data.results ?? data
    readingListEntry.value = entries[0] ?? null
  } finally {
    readingListLoading.value = false
  }
}

async function setStatus(status) {
  readingListError.value = null
  try {
    const isUpdate = !!readingListEntry.value
    const url = isUpdate
      ? `${API_BASE}/reading-lists/${readingListEntry.value.id}/`
      : `${API_BASE}/reading-lists/`
    const response = await fetch(url, {
      method: isUpdate ? 'PATCH' : 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(isUpdate ? { status } : { book: route.params.id, status }),
    })
    if (!response.ok) throw new Error('Could not update reading list')
    readingListEntry.value = await response.json()
  } catch (err) {
    readingListError.value = err.message
  }
}

function handleCoverError(event) {
  const img = event.target
  const attempts = Number(img.dataset.retryCount || 0)
  if (attempts >= 3) return
  img.dataset.retryCount = attempts + 1
  setTimeout(() => {
    img.src = `${book.value.cover_url}?retry=${attempts}`
  }, 1500 * (attempts + 1))
}

onMounted(() => {
  fetchBook()
  fetchReviews()
  fetchReadingListEntry()
})
</script>

<template>
  <main>
    <p v-if="loading">Loading...</p>
    <p v-else-if="error">Error: {{ error }}</p>

    <article v-else>
      <h1>{{ book.title }}</h1>
      <p>by {{ book.author }}</p>
      <p v-if="book.published_year">Published: {{ book.published_year }}</p>
      <p>Rating: {{ book.avg_rating }} ({{ book.ratings_count }} ratings)</p>
      <p v-if="book.description">{{ book.description }}</p>
      <img v-if="book.cover_url" :src="book.cover_url" :alt="book.title" @error="handleCoverError" />
      <div v-if="auth.isLoggedIn">
        <p v-if="!readingListLoading">
          Status:
          <select :value="readingListEntry?.status ?? ''" @change="setStatus($event.target.value)">
            <option value="" disabled>Add to reading list</option>
            <option v-for="opt in STATUS_OPTIONS" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </p>
        <p v-if="readingListError">{{ readingListError }}</p>
      </div>
    </article>

    <section>
      <h2>Reviews</h2>
      <p v-if="reviewsLoading">Loading reviews...</p>
      <ul v-else-if="reviews.length">
        <li v-for="review in reviews" :key="review.id">
          <strong>{{ review.username }}</strong> — {{ review.rating }}/5
          <p v-if="review.text">{{ review.text }}</p>
        </li>
      </ul>
      <p v-else>No reviews yet.</p>

      <form v-if="auth.isLoggedIn" @submit.prevent="submitReview">
        <h3>Leave a review</h3>
        <label>
          Rating:
          <select v-model="newRating">
            <option v-for="n in 5" :key="n" :value="n">{{ n }}</option>
          </select>
        </label>
        <textarea v-model="newText" placeholder="Your review (optional)"></textarea>
        <button type="submit" :disabled="submitting">Submit review</button>
        <p v-if="submitError">{{ submitError }}</p>
      </form>
      <p v-else>
        <RouterLink to="/login">Log in</RouterLink> to leave a review.
      </p>
    </section>
  </main>
</template>