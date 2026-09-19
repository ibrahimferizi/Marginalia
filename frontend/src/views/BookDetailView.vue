<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { API_BASE, apiFetch } from '../api'
import BookShelf from '../components/BookShelf.vue'

const route = useRoute()
const auth = useAuthStore()
const book = ref(null)
const loading = ref(true)
const error = ref('')
const coverBroken = ref(false)
const expanded = ref(false)
const similarBooks = ref([])
const similarLoading = ref(false)
const similarError = ref('')
const reviews = ref([])
const reviewCount = ref(0)
const reviewsLoading = ref(false)
const reviewsError = ref('')
const nextReviews = ref(null)
const previousReviews = ref(null)
const ownReview = ref(null)
const ownReviewLoading = ref(false)
const ownReviewError = ref('')
const newRating = ref(0)
const newText = ref('')
const submitting = ref(false)
const submitError = ref('')
const submitMessage = ref('')
const readingListEntry = ref(null)
const readingListLoading = ref(false)
const readingListError = ref('')
const statusSaving = ref(false)
const statusMessage = ref('')
let controller
let reviewsController

const statuses = [
  { value: 'want_to_read', label: 'Want to read' },
  { value: 'reading', label: 'Reading' },
  { value: 'finished', label: 'Finished' },
  { value: 'dropped', label: 'Set aside' },
]
const genres = computed(() => Object.entries(book.value?.genres || {}).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([name]) => name))
const ratingLabels = ['Choose a rating', 'Not for me', 'It was okay', 'I liked it', 'I really liked it', 'A favourite']

async function request(url, signal, options = {}) {
  const response = await apiFetch(url, { credentials: auth.isLoggedIn ? 'include' : 'omit', signal, ...options })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (response.status === 404) throw new Error('This book could not be found.')
    if (response.status === 401 || response.status === 403) throw new Error('Please log in to continue.')
    const detail = data.detail || Object.values(data).flat().find(value => typeof value === 'string')
    throw new Error(detail || 'Something went wrong. Please try again.')
  }
  return data
}

async function fetchBook(signal) {
  loading.value = true
  error.value = ''
  try {
    const data = await request(`${API_BASE}/books/${route.params.id}/`, signal)
    if (signal.aborted) return
    book.value = data
    document.title = `${data.title} — Marginalia`
  } catch (err) {
    if (!signal.aborted) error.value = err.message
  } finally {
    if (!signal.aborted) loading.value = false
  }
}

async function fetchSimilar(signal = controller.signal) {
  similarLoading.value = true
  similarError.value = ''
  try {
    const data = await request(`${API_BASE}/books/${route.params.id}/similar/`, signal)
    if (!signal.aborted) similarBooks.value = data
  } catch (err) {
    if (!signal.aborted) similarError.value = err.message
  } finally {
    if (!signal.aborted) similarLoading.value = false
  }
}

async function fetchReviews(url = `${API_BASE}/reviews/?book=${route.params.id}`) {
  reviewsController?.abort()
  const current = new AbortController()
  reviewsController = current
  reviewsLoading.value = true
  reviewsError.value = ''
  try {
    const data = await request(url, current.signal)
    if (current.signal.aborted) return
    reviews.value = data.results ?? data
    reviewCount.value = data.count ?? reviews.value.length
    nextReviews.value = data.next ?? null
    previousReviews.value = data.previous ?? null
  } catch (err) {
    if (!current.signal.aborted) reviewsError.value = err.message
  } finally {
    if (!current.signal.aborted) reviewsLoading.value = false
  }
}

async function fetchReadingEntry(signal = controller.signal) {
  if (!auth.isLoggedIn) return
  readingListLoading.value = true
  readingListError.value = ''
  try {
    const data = await request(`${API_BASE}/reading-lists/?book=${route.params.id}`, signal)
    if (!signal.aborted) readingListEntry.value = (data.results ?? data)[0] ?? null
  } catch (err) {
    if (!signal.aborted) readingListError.value = err.message
  } finally {
    if (!signal.aborted) readingListLoading.value = false
  }
}

async function fetchOwnReview(signal = controller.signal) {
  if (!auth.isLoggedIn) return
  ownReviewLoading.value = true
  ownReviewError.value = ''
  try {
    const query = new URLSearchParams({ book: route.params.id, username: auth.username })
    const data = await request(`${API_BASE}/reviews/?${query}`, signal)
    if (signal.aborted) return
    ownReview.value = (data.results ?? data)[0] ?? null
    newRating.value = ownReview.value?.rating ?? 0
    newText.value = ownReview.value?.text ?? ''
  } catch (err) {
    if (!signal.aborted) ownReviewError.value = err.message
  } finally {
    if (!signal.aborted) ownReviewLoading.value = false
  }
}

async function submitReview() {
  if (submitting.value || !newRating.value) return
  const signal = controller.signal
  submitting.value = true
  submitError.value = ''
  submitMessage.value = ''
  try {
    const url = ownReview.value ? `${API_BASE}/reviews/${ownReview.value.id}/` : `${API_BASE}/reviews/`
    const data = await request(url, signal, {
      method: ownReview.value ? 'PATCH' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ book: route.params.id, rating: newRating.value, text: newText.value }),
    })
    if (signal.aborted) return
    ownReview.value = data
    submitMessage.value = 'Your rating and review are saved.'
    fetchReviews()
    const updated = await request(`${API_BASE}/books/${route.params.id}/`, signal)
    if (!signal.aborted) book.value = updated
  } catch (err) {
    if (!signal.aborted) submitError.value = submitMessage.value ? 'Your review was saved, but the book rating could not refresh. Reload to see it.' : err.message
  } finally {
    if (!signal.aborted) submitting.value = false
  }
}

async function setStatus(event) {
  const status = event.target.value
  if (statusSaving.value || status === readingListEntry.value?.status) return
  const signal = controller.signal
  statusSaving.value = true
  statusMessage.value = ''
  readingListError.value = ''
  try {
    const existing = readingListEntry.value
    const data = await request(existing ? `${API_BASE}/reading-lists/${existing.id}/` : `${API_BASE}/reading-lists/`, signal, {
      method: existing ? 'PATCH' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(existing ? { status } : { book: route.params.id, status }),
    })
    if (!signal.aborted) {
      readingListEntry.value = data
      statusMessage.value = 'Saved to your library.'
    }
  } catch (err) {
    if (!signal.aborted) { readingListError.value = err.message; event.target.value = readingListEntry.value?.status ?? '' }
  } finally {
    if (!signal.aborted) statusSaving.value = false
  }
}

function loadPage() {
  controller?.abort()
  reviewsController?.abort()
  controller = new AbortController()
  document.title = 'Marginalia — Book details'
  book.value = null
  coverBroken.value = false
  expanded.value = false
  reviews.value = []
  reviewCount.value = 0
  nextReviews.value = previousReviews.value = null
  ownReview.value = readingListEntry.value = null
  newRating.value = 0
  newText.value = submitError.value = submitMessage.value = statusMessage.value = ownReviewError.value = readingListError.value = ''
  submitting.value = statusSaving.value = ownReviewLoading.value = readingListLoading.value = false
  similarBooks.value = []
  fetchBook(controller.signal)
  fetchSimilar(controller.signal)
  fetchReviews()
  fetchReadingEntry(controller.signal)
  fetchOwnReview(controller.signal)
}

watch(() => [route.params.id, auth.username], loadPage, { immediate: true })
onBeforeUnmount(() => { controller?.abort(); reviewsController?.abort(); document.title = 'Marginalia — Your personal library' })
</script>

<template>
  <main class="book-page">
    <nav class="breadcrumb" aria-label="Breadcrumb"><RouterLink to="/search">Collection</RouterLink><span aria-hidden="true">/</span><span>Book details</span></nav>
    <div v-if="loading" class="page-state" role="status">Opening the book...</div>
    <div v-else-if="error" class="page-state"><h1>We couldn’t open this book.</h1><p role="alert">{{ error }}</p><button @click="loadPage">Try again</button><RouterLink class="button-link" to="/search">Back to search</RouterLink></div>
    <template v-else-if="book">
      <article class="book-overview">
        <aside class="book-aside" aria-label="Cover and your reading status">
          <div class="cover-stage">
            <img v-if="book.cover_url && !coverBroken" :src="book.cover_url" :alt="`Cover of ${book.title}`" class="main-cover" @error="coverBroken = true" />
            <div v-else class="fallback-cover"><span>{{ book.title }}</span><small>{{ book.author }}</small><span class="fallback-mark" aria-hidden="true">m.</span></div>
          </div>
          <div class="reading-controls">
            <template v-if="auth.isLoggedIn">
              <label for="reading-status">In your library</label>
              <p v-if="readingListLoading" role="status">Loading reading status...</p>
              <select v-else id="reading-status" :value="readingListEntry?.status ?? ''" :disabled="statusSaving || !!readingListError" @change="setStatus">
                <option value="" disabled>Add to my library</option>
                <option v-for="status in statuses" :key="status.value" :value="status.value">{{ status.label }}</option>
              </select>
              <p v-if="statusSaving" class="control-message" role="status">Saving...</p>
              <p v-else-if="statusMessage" class="control-message" role="status">{{ statusMessage }}</p>
              <template v-if="readingListError"><p class="control-message" role="alert">{{ readingListError }}</p><button @click="fetchReadingEntry()">Retry</button></template>
              <RouterLink v-if="readingListEntry" to="/my-reading-list" class="library-link">View my library →</RouterLink>
            </template>
            <RouterLink v-else class="button-link" to="/login">Log in to save this book</RouterLink>
          </div>
        </aside>
        <div class="book-copy">
          <p class="eyebrow">Between the covers</p>
          <h1>{{ book.title }}</h1>
          <p class="book-author">by {{ book.author || 'Unknown author' }}</p>
          <div class="book-rating" v-if="book.ratings_count"><span class="rating-value"><span aria-hidden="true">★</span> {{ Number(book.avg_rating).toFixed(2) }}</span><span>out of 5 · {{ Number(book.ratings_count).toLocaleString() }} ratings</span></div>
          <p v-else class="muted">No ratings yet.</p>
          <dl class="book-facts">
            <div v-if="book.published_year"><dt>Published</dt><dd>{{ book.published_year }}</dd></div>
            <div v-if="book.page_count"><dt>Length</dt><dd>{{ Number(book.page_count).toLocaleString() }} pages</dd></div>
            <div v-if="book.isbn"><dt>ISBN</dt><dd>{{ book.isbn }}</dd></div>
          </dl>
          <ul v-if="genres.length" class="genre-tags" aria-label="Genres"><li v-for="genre in genres" :key="genre">{{ genre }}</li></ul>
          <div class="about-book">
            <h2>About this book</h2>
            <p id="book-description" class="description" :class="{ collapsed: !expanded && book.description?.length > 700 }">{{ book.description || 'A description isn’t available for this edition yet.' }}</p>
            <button v-if="book.description?.length > 700" class="text-button" :aria-expanded="expanded" aria-controls="book-description" @click="expanded = !expanded">{{ expanded ? 'Show less ↑' : 'Read the full description ↓' }}</button>
          </div>
        </div>
      </article>

      <section class="similar-section" aria-labelledby="similar-heading">
        <div class="section-heading"><div><p class="eyebrow">Keep exploring</p><h2 id="similar-heading">On a similar page</h2></div><p class="muted">More books to spend time with.</p></div>
        <p v-if="similarLoading" role="status">Finding similar books...</p>
        <div v-else-if="similarError"><p role="alert">{{ similarError }}</p><button @click="fetchSimilar()">Try again</button></div>
        <p v-else-if="!similarBooks.length" class="muted">No similar books available yet.</p>
        <BookShelf v-else :books="similarBooks" horizontal similar />
      </section>

      <section class="reviews-section" aria-labelledby="reviews-heading">
        <div class="section-heading"><div><p class="eyebrow">In the margins</p><h2 id="reviews-heading">Readers’ thoughts</h2></div><span class="muted">{{ reviewCount }} {{ reviewCount === 1 ? 'review' : 'reviews' }} on Marginalia</span></div>
        <div class="reviews-layout">
          <div>
            <p v-if="reviewsLoading" role="status">Loading reviews...</p>
            <div v-else-if="reviewsError"><p role="alert">{{ reviewsError }}</p><button @click="fetchReviews()">Try again</button></div>
            <template v-else>
              <ul v-if="reviews.length" class="review-list"><li v-for="review in reviews" :key="review.id">
                <div class="review-heading"><RouterLink :to="{ name: 'public-profile', params: { username: review.username } }">{{ review.username }}</RouterLink><span class="review-stars" :aria-label="`${review.rating} out of 5 stars`"><span aria-hidden="true">{{ '★'.repeat(review.rating) }}{{ '☆'.repeat(5 - review.rating) }}</span></span></div>
                <p v-if="review.text" class="review-text">{{ review.text }}</p><p v-else class="muted rating-only">Rated this book without a written review.</p>
              </li></ul>
              <p v-else class="muted">No reviews here yet. Your thoughts could be the first.</p>
              <div v-if="nextReviews || previousReviews" class="review-pagination"><button :disabled="!previousReviews" @click="fetchReviews(previousReviews)">Previous</button><button :disabled="!nextReviews" @click="fetchReviews(nextReviews)">Next</button></div>
            </template>
          </div>
          <div class="your-review">
            <h3>{{ ownReview ? 'Your review' : 'What did you think?' }}</h3>
            <p v-if="!auth.isLoggedIn"><RouterLink to="/login">Log in</RouterLink> to rate this book and share your thoughts.</p>
            <p v-else-if="ownReviewLoading" role="status">Loading your rating...</p>
            <div v-else-if="ownReviewError"><p role="alert">{{ ownReviewError }}</p><button @click="fetchOwnReview()">Try again</button></div>
            <form v-else @submit.prevent="submitReview">
              <fieldset :disabled="submitting"><legend>Your rating</legend><div class="rating-options"><label v-for="n in 5" :key="n"><input v-model="newRating" type="radio" name="rating" :value="n" :aria-label="`${n} out of 5 stars`" required /><span aria-hidden="true" :class="{ filled: newRating >= n }">★</span></label></div><p class="rating-label">{{ ratingLabels[newRating] }}</p></fieldset>
              <label for="review-text">Your thoughts <span class="muted">(optional)</span></label>
              <textarea id="review-text" v-model="newText" :disabled="submitting" placeholder="What stayed with you?" rows="4"></textarea>
              <button class="save-review" type="submit" :disabled="submitting || !newRating">{{ submitting ? 'Saving...' : ownReview ? 'Save changes' : 'Save my review' }}</button>
              <p v-if="submitError" class="control-message" role="alert">{{ submitError }}</p><p v-if="submitMessage" class="control-message" role="status">{{ submitMessage }}</p>
            </form>
          </div>
        </div>
      </section>
    </template>
  </main>
</template>

<style scoped>
.breadcrumb { display: flex; gap: 12px; font-size: 12px; color: var(--color-muted); margin-bottom: 42px; }
.breadcrumb a { text-decoration: none; }
.book-overview { display: grid; grid-template-columns: minmax(220px, 300px) minmax(0, 1fr); gap: clamp(32px, 6vw, 90px); align-items: start; }
.cover-stage { min-height: 360px; padding: 24px 25px 32px; display: flex; align-items: center; justify-content: center; background: radial-gradient(ellipse at 50% 80%, #dedacb 0, #eeeadf 65%); border-radius: 3px; }
.main-cover { display: block; max-width: 100%; width: 230px; max-height: 360px; object-fit: contain; filter: drop-shadow(5px 12px 8px #34352535); }
.fallback-cover { min-height: 290px; width: 210px; padding: 28px 24px; background: #556049; color: #f9f3df; box-shadow: inset 5px 0 #0002, 6px 8px 14px #0002; display: flex; flex-direction: column; justify-content: space-between; gap: 24px; font: 26px/1.2 var(--font-display); }
.fallback-cover small { color: inherit; font-size: 15px; }.fallback-mark { font-style: italic; }
.reading-controls { display: grid; gap: 10px; margin-top: 24px; }
.reading-controls > label { color: var(--color-muted); font-size: 12px; }
.reading-controls select { width: 100%; background: #e5e9dc; border-color: #bdc6ae; }
.library-link { font-size: 12px; text-align: center; margin-top: 4px; }
.control-message { font-size: 12px; margin: 0; }
.book-copy h1 { font-size: clamp(34px, 4.2vw, 58px); margin-bottom: 16px; }
.book-author { font: italic 24px/1.3 var(--font-display); color: var(--color-muted); margin-bottom: 24px; }
.book-rating { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; font-size: 13px; color: var(--color-muted); margin-bottom: 28px; }
.rating-value { color: var(--color-heading); font-size: 24px; }.rating-value > span { color: #877544; font-size: 20px; }
.book-facts { display: flex; flex-wrap: wrap; gap: 20px 40px; border-top: 1px solid var(--color-border); padding-top: 20px; margin: 0 0 22px; }
dt { font: 10px 'Courier New', monospace; text-transform: uppercase; letter-spacing: .12em; color: var(--color-muted); margin-bottom: 8px; }dd { margin: 0; font-size: 14px; }
.genre-tags { display: flex; gap: 8px; flex-wrap: wrap; list-style: none; padding: 0; margin: 0 0 32px; }.genre-tags li { padding: 4px 10px; border: 1px solid var(--color-border); border-radius: 20px; font-size: 11px; text-transform: capitalize; }
.about-book h2 { font-size: 25px; }.description { white-space: pre-line; overflow-wrap: anywhere; line-height: 1.85; }.description.collapsed { max-height: 190px; overflow: hidden; mask-image: linear-gradient(#000 75%, transparent); }
.text-button { padding: 4px 0; border: 0; border-radius: 0; border-bottom: 1px solid var(--color-border); min-height: 34px; }
.similar-section, .reviews-section { border-top: 1px solid var(--color-border); padding-top: 32px; margin-top: 64px; }
.section-heading { display: flex; align-items: end; justify-content: space-between; gap: 24px; flex-wrap: wrap; margin-bottom: 26px; }.section-heading h2 { margin-bottom: 0; }.section-heading .eyebrow { margin-bottom: 10px; }.section-heading > p, .section-heading > span { font-size: 13px; margin: 0; }
.reviews-layout { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 60px; }.review-list { list-style: none; margin: 0; padding: 0; }.review-list li { padding: 0 0 24px; margin-bottom: 24px; border-bottom: 1px solid var(--color-border); }.review-heading { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 12px; }.review-heading a { font-weight: 500; text-decoration: none; overflow-wrap: anywhere; }.review-stars { color: #877544; white-space: nowrap; letter-spacing: 2px; }.review-text { white-space: pre-line; overflow-wrap: anywhere; }.rating-only { font-size: 13px; }
.your-review { background: #eeeadf; border: 1px solid var(--color-border); border-radius: 4px; padding: 26px; align-self: start; }.your-review h3 { margin: 0 0 20px; }.your-review form { display: grid; gap: 12px; margin: 0; }.your-review fieldset { border: 0; margin: 0; padding: 0; }.your-review legend { font-size: 13px; }.rating-options { display: flex; gap: 6px; margin-top: 5px; }.rating-options label { position: relative; cursor: pointer; display: flex; align-items: center; justify-content: center; width: 40px; height: 44px; }.rating-options input { position: absolute; width: 1px; height: 1px; opacity: 0; min-height: 0; margin: 0; padding: 0; }.rating-options span { color: #aaa798; font-size: 33px; line-height: 1; }.rating-options span.filled { color: #85713b; }.rating-options input:focus-visible + span { outline: 2px solid var(--color-accent); outline-offset: 4px; }.rating-label { font-size: 12px; color: var(--color-muted); margin-bottom: 6px; }.save-review { background: #566046; color: #fffdf5; border-color: #566046; }.save-review:hover:not(:disabled) { background: #414b34; color: #fffdf5; }
.page-state { padding: 60px 0; }.page-state h1 { font-size: 36px; }.page-state .button-link { margin-left: 12px; }
@media (max-width: 750px) { .book-overview { grid-template-columns: 1fr; gap: 36px; }.book-aside { max-width: 300px; width: 100%; margin: auto; }.book-copy h1 { font-size: 38px; }.reviews-layout { grid-template-columns: 1fr; gap: 28px; }.breadcrumb { margin-bottom: 28px; }.similar-section, .reviews-section { margin-top: 42px; }.book-facts { gap: 20px; } }
@media (max-width: 400px) { .your-review { padding: 20px; }.rating-options { gap: 2px; } }
</style>
