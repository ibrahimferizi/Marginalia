<script setup>
import { RouterLink } from 'vue-router'
import placeholderCover from '@/assets/placeholder-cover.png'
import GoogleBooksAttribution from './GoogleBooksAttribution.vue'

defineProps({ books: { type: Array, required: true }, horizontal: Boolean, reasons: Boolean, similar: Boolean, showSources: Boolean, mode: { type: String, default: 'hybrid' } })

function reasonText(reason) {
  if (reason.type === 'hybrid') return 'A match for your reading themes, with a connection through other readers.'
  if (reason.type === 'collaborative') return 'Connected through readers who rated books you’ve rated.'
  return 'Shares themes with the books you’ve rated.'
}

function coverError(event) {
  if (event.target.getAttribute('src') !== placeholderCover) event.target.src = placeholderCover
}
</script>

<template>
  <ul :class="['books', { horizontal }]">
    <li v-for="book in books" :key="book.id">
      <RouterLink :to="`/books/${book.id}`">
        <img :src="book.cover_url || placeholderCover" :alt="book.title" loading="lazy" @error="coverError" />
      </RouterLink>
      <GoogleBooksAttribution :book="book" />
      <RouterLink :to="`/books/${book.id}`">
        <span>{{ book.title }}</span>
      </RouterLink>
      <p>{{ book.author }}</p>
      <p v-if="book.reading_status" class="reading-status">{{ book.reading_status }}</p>
      <small v-if="book.ratings_count">{{ Number(book.ratings_count).toLocaleString() }} ratings · {{ book.avg_rating }}/5</small>
      <small v-else>No ratings yet</small>
      <p v-if="similar && book.recommendation_reason" class="similar-reason">{{ book.recommendation_reason.type === 'collaborative' ? 'Readers also rated' : 'Related genres and themes' }}</p>
      <details v-if="reasons && book.recommendation_reason" class="recommendation-explanation">
        <summary>Why this book?</summary>
        <p>{{ reasonText(book.recommendation_reason) }}</p>
        <template v-if="book.recommendation_reason.source_book">
          <span class="connection-label">Reader connection from</span>
          <RouterLink :to="{ name: 'recommendations', query: { mode, source: book.recommendation_reason.source_book.id } }">{{ book.recommendation_reason.source_book.title }} →</RouterLink>
        </template>
        <RouterLink v-else :to="{ name: 'recommendations', query: { mode: 'content' } }">Explore your reading themes →</RouterLink>
        <div v-if="showSources && book.recommendation_sources?.length > 1" class="all-connections">
          <span class="connection-label">All reader connections</span>
          <ul><li v-for="source in book.recommendation_sources" :key="source.id"><RouterLink :to="{ name: 'recommendations', query: { mode, source: source.id } }">{{ source.title }}</RouterLink></li></ul>
        </div>
      </details>
    </li>
  </ul>
</template>

<style scoped>
.books { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 32px; padding: 0; list-style: none; margin: 30px 0; }
.books.horizontal { display: flex; overflow-x: auto; padding-bottom: 1rem; }
.horizontal > li { flex: 0 0 170px; }
img { display: block; width: 128px; height: 192px; object-fit: contain; object-position: left bottom; margin-bottom: 18px; filter: drop-shadow(3px 5px 4px #24291e20); }
.books > li > a { display: block; font: 19px/1.25 var(--font-display); text-decoration: none; color: var(--color-heading); }
.books > li > p { font-size: 13px; color: var(--color-muted); }
.reading-status { color: var(--color-accent) !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: .05em; }
p { margin: .5rem 0; }
small { display: block; }
small, details { font-size: 12px; }
.recommendation-explanation { margin-top: 12px; border-top: 1px solid var(--color-border); padding-top: 10px; line-height: 1.65; }
.recommendation-explanation summary { cursor: pointer; color: var(--color-accent); }
.recommendation-explanation p { color: var(--color-muted); margin: 10px 0; }
.connection-label { display: block; font-size: 10px; text-transform: uppercase; letter-spacing: .04em; margin: 12px 0 6px; color: var(--color-muted); }
.all-connections ul { list-style: none; padding: 0; margin: 0; }.all-connections li + li { margin-top: 8px; }
@media (max-width: 420px) { .books { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; } img { max-width: 100%; } }
</style>
