<script setup>
import { computed, ref, watch, onUnmounted } from 'vue'
import { API_BASE, apiFetch } from '../api'
import { useAuthStore } from '../stores/auth'
import ReaderAvatar from '../components/ReaderAvatar.vue'

const auth = useAuthStore()
const profile = ref(null)
const bio = ref('')
const avatarUrl = ref('')
const loading = ref(false)
const error = ref('')
const saving = ref(false)
const saveMessage = ref('')
const saveError = ref('')
const stats = ref(null)
const statsLoading = ref(false)
const statsError = ref('')
const changed = computed(() => profile.value && (bio.value !== profile.value.bio || avatarUrl.value !== profile.value.avatar_url))
const maxRatingCount = computed(() => Math.max(1, ...Object.values(stats.value?.rating_distribution ?? {})))
const shelves = [
  { key: 'want_to_read', label: 'Want to read' },
  { key: 'reading', label: 'Reading' },
  { key: 'finished', label: 'Finished' },
  { key: 'dropped', label: 'Set aside' },
]
let controller

async function fetchStats(signal = controller?.signal) {
  statsLoading.value = true
  statsError.value = ''
  try {
    const response = await apiFetch(`${API_BASE}/accounts/me/stats/`, { signal })
    if (!response.ok) throw new Error('Could not load your reading statistics. Please try again.')
    const data = await response.json()
    if (!signal?.aborted) stats.value = data
  } catch (err) {
    if (!signal?.aborted) statsError.value = err.message
  } finally {
    if (!signal?.aborted) statsLoading.value = false
  }
}

async function loadProfile() {
  controller?.abort()
  controller = new AbortController()
  const { signal } = controller
  profile.value = null
  stats.value = null
  error.value = ''
  statsError.value = ''
  saveMessage.value = ''
  saveError.value = ''
  saving.value = false
  loading.value = false
  statsLoading.value = false
  if (!auth.isLoggedIn) return
  loading.value = true
  fetchStats(signal)
  try {
    const response = await apiFetch(`${API_BASE}/accounts/me/`, { signal })
    if (!response.ok) throw new Error(response.status === 401 ? 'Your session has expired. Please log in again.' : 'Could not load your profile. Please try again.')
    const data = await response.json()
    if (signal.aborted) return
    profile.value = { ...data, bio: data.bio ?? '', avatar_url: data.avatar_url ?? '' }
    bio.value = profile.value.bio
    avatarUrl.value = profile.value.avatar_url
  } catch (err) {
    if (!signal.aborted) error.value = err.message
  } finally {
    if (!signal.aborted) loading.value = false
  }
}

async function saveProfile() {
  if (saving.value || !changed.value) return
  const signal = controller.signal
  saving.value = true
  saveMessage.value = ''
  saveError.value = ''
  try {
    const response = await apiFetch(`${API_BASE}/accounts/me/`, {
      method: 'PATCH', credentials: 'include', signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bio: bio.value, avatar_url: avatarUrl.value.trim() }),
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      const detail = Object.values(data)[0]
      throw new Error(Array.isArray(detail) ? detail[0] : typeof detail === 'string' ? detail : 'Could not save your profile. Please try again.')
    }
    if (signal.aborted) return
    profile.value = { ...data, bio: data.bio ?? '', avatar_url: data.avatar_url ?? '' }
    bio.value = profile.value.bio
    avatarUrl.value = profile.value.avatar_url
    saveMessage.value = 'Your profile is saved.'
  } catch (err) {
    if (!signal.aborted) saveError.value = err.message
  } finally {
    if (!signal.aborted) saving.value = false
  }
}

watch([bio, avatarUrl], () => { saveMessage.value = ''; saveError.value = '' }, { flush: 'sync' })
watch(() => auth.username, loadProfile, { immediate: true })
onUnmounted(() => controller?.abort())
</script>

<template>
  <main class="profile-page">
    <p class="eyebrow">Your corner of Marginalia</p>
    <h1>My profile</h1>
    <div v-if="!auth.isLoggedIn" class="account-panel account-state">
      <h2>A little about you</h2><p>Log in to edit your profile and see your reading statistics.</p>
      <RouterLink class="button-link" to="/login">Log in</RouterLink>
    </div>
    <p v-else-if="loading" role="status">Loading your profile…</p>
    <div v-else-if="error" class="account-state"><p role="alert">{{ error }}</p><button @click="loadProfile">Try again</button> <RouterLink to="/login">Log in</RouterLink></div>
    <div v-else-if="profile" class="profile-layout">
      <section class="account-panel profile-editor" aria-labelledby="profile-heading">
        <div class="reader-identity">
          <ReaderAvatar :username="profile.username" :url="profile.avatar_url" />
          <div><p class="eyebrow">Reader profile</p><h2 id="profile-heading">{{ profile.username }}</h2><RouterLink :to="{ name: 'public-profile', params: { username: profile.username } }">View public profile</RouterLink></div>
        </div>
        <form class="account-form" @submit.prevent="saveProfile" :aria-busy="saving">
          <label>About you<textarea v-model="bio" :disabled="saving" placeholder="The books you love, what you’re reading, or a little about yourself." /></label>
          <label>Profile image URL<input v-model="avatarUrl" type="url" maxlength="200" :disabled="saving" placeholder="https://…" aria-describedby="avatar-hint" /><small id="avatar-hint">Link to an image, or leave blank to use your initial.</small></label>
          <p class="muted account-footnote">Your bio, profile image, ratings, and reviews are public. Your reading shelves and statistics are private.</p>
          <button class="account-primary" type="submit" :disabled="saving || !changed">{{ saving ? 'Saving…' : 'Save profile' }}</button>
          <p v-if="saveMessage" role="status">{{ saveMessage }}</p><p v-if="saveError" role="alert">{{ saveError }}</p>
        </form>
      </section>
      <section class="reading-statistics" aria-labelledby="stats-heading">
        <div class="shelf-heading"><h2 id="stats-heading">Your reading, in numbers</h2><RouterLink to="/my-reading-list">My library</RouterLink></div>
        <p v-if="statsLoading" role="status">Loading reading statistics…</p>
        <div v-else-if="statsError" class="account-state"><p role="alert">{{ statsError }}</p><button @click="fetchStats()">Try again</button></div>
        <template v-else-if="stats">
          <dl class="reading-totals">
            <div><dt>Books rated</dt><dd>{{ stats.rated_books }}</dd></div>
            <div><dt>Average rating</dt><dd>{{ stats.average_rating ?? '—' }}<small v-if="stats.average_rating != null"> / 5</small></dd></div>
            <div><dt>Finished in {{ stats.year }}</dt><dd>{{ stats.finished_this_year }}</dd></div>
          </dl>
          <div class="stats-shelves"><div v-for="shelf in shelves" :key="shelf.key"><span>{{ shelf.label }}</span><strong>{{ stats.reading_list[shelf.key] }}</strong></div></div>
          <p v-if="stats.finished_without_date" class="stats-note">{{ stats.finished_without_date }} finished {{ stats.finished_without_date === 1 ? 'book has' : 'books have' }} no completion date and {{ stats.finished_without_date === 1 ? 'is' : 'are' }} not included in the yearly total.</p>
          <h3>Your ratings</h3>
          <p v-if="!stats.rated_books" class="muted">Rate a book to start your reading story.</p>
          <ol class="rating-distribution" aria-label="Number of books by star rating">
            <li v-for="rating in [5, 4, 3, 2, 1]" :key="rating"><span>{{ rating }} {{ rating === 1 ? 'star' : 'stars' }}</span><span class="rating-track" aria-hidden="true"><span :style="{ width: `${(stats.rating_distribution[rating] || 0) / maxRatingCount * 100}%` }" /></span><strong>{{ stats.rating_distribution[rating] || 0 }}</strong></li>
          </ol>
        </template>
      </section>
    </div>
  </main>
</template>
