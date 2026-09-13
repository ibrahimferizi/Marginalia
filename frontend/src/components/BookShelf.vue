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
      <small>{{ Number(book.ratings_count).toLocaleString() }} ratings · {{ book.avg_rating }}/5</small>
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
.books { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 1.5rem; padding: 0; list-style: none; }
.books.horizontal { display: flex; overflow-x: auto; padding-bottom: 1rem; }
.horizontal > li { flex: 0 0 170px; }
img { display: block; width: 120px; height: 180px; object-fit: contain; margin-bottom: .5rem; }
p { margin: .5rem 0; }
small { display: block; }
</style>
