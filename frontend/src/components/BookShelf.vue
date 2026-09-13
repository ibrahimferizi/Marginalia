<script setup>
import { RouterLink } from 'vue-router'
import placeholderCover from '@/assets/placeholder-cover.png'

defineProps({ books: { type: Array, required: true }, horizontal: Boolean, reasons: Boolean, showSources: Boolean, mode: { type: String, default: 'hybrid' } })

function reasonText(reason) {
  if (reason.type === 'hybrid') return `Matches your reading interests, with reader overlap from ${reason.source_book.title}`
  if (reason.type === 'collaborative') return `Readers of ${reason.source_book.title} also rated this`
  return 'Based on themes in books you rated'
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
        <span>{{ book.title }}</span>
      </RouterLink>
      <p>{{ book.author }}</p>
      <p v-if="book.reading_status" class="reading-status">{{ book.reading_status }}</p>
      <small v-if="book.ratings_count">{{ Number(book.ratings_count).toLocaleString() }} ratings · {{ book.avg_rating }}/5</small>
      <small v-else>No ratings yet</small>
      <p v-if="reasons && book.recommendation_reason">
        <RouterLink :to="{ name: 'recommendations', query: book.recommendation_reason.source_book ? { mode, source: book.recommendation_reason.source_book.id } : { mode: 'content' } }">
          {{ reasonText(book.recommendation_reason) }}
        </RouterLink>
      </p>
      <details v-if="showSources && book.recommendation_sources?.length > 1">
        <summary>All reader connections</summary>
        <ul>
          <li v-for="source in book.recommendation_sources" :key="source.id">
            <RouterLink :to="{ name: 'recommendations', query: { mode, source: source.id } }">{{ source.title }}</RouterLink>
          </li>
        </ul>
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
@media (max-width: 420px) { .books { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; } img { max-width: 100%; } }
</style>
