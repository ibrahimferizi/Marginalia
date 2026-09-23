<script setup>
defineProps({ book: { type: Object, required: true } })
</script>

<template>
  <span v-if="book.google_books_id" class="google-attribution">
    <a :href="`https://books.google.com/books?id=${encodeURIComponent(book.google_books_id)}`" target="_blank" rel="noopener noreferrer" :aria-label="`View ${book.title} on Google Books (opens in a new tab)`" title="View on Google Books">
      <img src="https://books.google.com/googlebooks/images/poweredby.png" alt="Powered by Google" width="62" height="30" />
    </a>
  </span>
</template>

<style scoped>
.google-attribution { display: block; margin: 8px 0; line-height: 0; }
.google-attribution a { display: inline-block; }
.google-attribution img { display: block; width: 62px; height: 30px; max-width: none; margin: 0; padding: 0; border: 0; filter: none; }
</style>
