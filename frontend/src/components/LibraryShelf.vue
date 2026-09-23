<script setup>
import { ref, computed, nextTick, onBeforeUnmount, watch } from 'vue'
import { RouterLink } from 'vue-router'
import GoogleBooksAttribution from './GoogleBooksAttribution.vue'

const props = defineProps({ books: { type: Array, required: true } })
const rail = ref(null)
const dialog = ref(null)
const selected = ref(null)
const hovered = ref(null)
const brokenCovers = ref(new Set())
let lastTrigger
let savedOverflow
const palette = ['#434e43', '#725541', '#423d49', '#405465', '#76504c', '#776744', '#384846']
const styledBooks = computed(() => props.books.map(book => {
  const hash = [...String(book.id)].reduce((value, char) => ((value * 31 + char.charCodeAt(0)) >>> 0), 0)
  return { ...book, style: {
    '--thickness': `${book.page_count ? Math.max(22, Math.min(54, book.page_count * .075)) : 30}px`,
    '--book-height': `${226 + hash % 33}px`,
    '--book-color': palette[hash % palette.length],
    '--lean': `${hash % 3 === 0 ? -1 : 0}deg`,
  } }
}))

function broken(id) {
  brokenCovers.value = new Set([...brokenCovers.value, id])
}

async function openBook(book, event) {
  lastTrigger = event.currentTarget
  selected.value = book
  await nextTick()
  savedOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  dialog.value.showModal()
}

function restore() {
  if (savedOverflow !== undefined) document.body.style.overflow = savedOverflow
  savedOverflow = undefined
  selected.value = null
  lastTrigger?.focus()
}

function scroll(direction) {
  rail.value?.scrollBy({ left: direction * rail.value.clientWidth * .7, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' })
}

watch(() => props.books, () => { dialog.value?.close(); hovered.value = null })
onBeforeUnmount(() => {
  if (savedOverflow !== undefined) document.body.style.overflow = savedOverflow
})
</script>

<template>
  <div class="library-shelf">
    <div class="shelf-topline">
      <span class="eyebrow">On your shelf</span>
      <div><button aria-label="Scroll shelf left" @click="scroll(-1)">←</button><button aria-label="Scroll shelf right" @click="scroll(1)">→</button></div>
    </div>
    <div ref="rail" class="shelf-rail" role="region" aria-label="Your books in 3D" tabindex="0" @keydown.left.prevent="scroll(-1)" @keydown.right.prevent="scroll(1)">
      <ul class="spines">
        <li v-for="book in styledBooks" :key="book.id" :style="book.style" :class="{ 'google-book': book.google_books_id }">
          <button class="book-target" :aria-label="`Preview ${book.title} by ${book.author}`" @mouseenter="hovered = book" @mouseleave="hovered = null" @focus="hovered = book" @blur="hovered = null" @click="openBook(book, $event)">
            <span class="volume" aria-hidden="true">
              <span class="book-front">
                <img v-if="book.cover_url && !brokenCovers.has(book.id)" :src="book.cover_url" alt="" loading="lazy" @error="broken(book.id)" />
                <span v-else class="cover-fallback"><span>{{ book.title }}</span><small>{{ book.author }}</small></span>
              </span>
              <span class="book-spine"><span class="spine-title">{{ book.title }}</span><span class="spine-author">{{ book.author }}</span><span class="spine-mark">m.</span></span>
              <span class="book-pages"></span>
            </span>
          </button>
          <GoogleBooksAttribution :book="book" class="spine-attribution" />
        </li>
      </ul>
    </div>
    <div class="shelf-caption">
      <p v-if="hovered"><strong>{{ hovered.title }}</strong><span> — {{ hovered.author }}</span></p>
      <p v-else>Every spine, a story. Select a book to take a closer look.</p>
      <span class="navigation-hint">Scroll sideways · use ← →</span>
    </div>
    <dialog ref="dialog" class="book-dialog" aria-labelledby="preview-title" @close="restore" @click="($event.target === dialog) && dialog.close()">
      <template v-if="selected">
        <button class="close-preview" aria-label="Close book preview" autofocus @click="dialog.close()">✕</button>
        <div class="preview-layout">
          <div>
          <div class="preview-cover" :style="selected.style">
            <img v-if="selected.cover_url && !brokenCovers.has(selected.id)" :src="selected.cover_url" :alt="selected.title" @error="broken(selected.id)" />
            <div v-else class="cover-fallback"><span>{{ selected.title }}</span><small>{{ selected.author }}</small></div>
          </div>
          <GoogleBooksAttribution :book="selected" />
          </div>
          <div class="preview-copy">
            <p class="eyebrow">{{ selected.reading_status }}</p>
            <h2 id="preview-title">{{ selected.title }}</h2>
            <p class="preview-author">{{ selected.author }}</p>
            <p class="muted"><span v-if="selected.published_year">{{ selected.published_year }} · </span>{{ selected.page_count ? `${selected.page_count} pages` : 'Page count unavailable' }}</p>
            <p class="preview-description" tabindex="0" aria-label="Book description">{{ selected.description || 'No description available for this edition.' }}</p>
            <RouterLink class="button-link" :to="`/books/${selected.id}`" @click="dialog.close()">Book details &amp; reading status →</RouterLink>
          </div>
        </div>
      </template>
    </dialog>
  </div>
</template>

<style scoped>
.library-shelf { margin: 32px -12px 0; }
.shelf-topline { display: flex; justify-content: space-between; align-items: center; padding: 0 12px; }
.shelf-topline .eyebrow { margin: 0; }
.shelf-topline button { min-height: 34px; padding: 3px 12px; }
.shelf-rail { overflow-x: auto; overflow-y: hidden; scrollbar-width: thin; scrollbar-color: #b4b4a2 transparent; background: linear-gradient(transparent calc(100% - 27px), #c6c2b0 calc(100% - 26px), #e0ddce calc(100% - 24px), transparent); }
.spines { display: flex; align-items: end; gap: 14px; padding: 80px 80px 28px 32px; margin: 0; list-style: none; min-width: max-content; min-height: 380px; }
.spines > li { width: calc(var(--thickness) + 21px); height: var(--book-height); perspective: 1100px; position: relative; }
.spines > li:focus-within, .spines > li:hover { z-index: 2; }
.spines:has(.google-book) { padding-bottom: 70px; }
.spines > li.google-book { min-width: 62px; }
.spine-attribution { position: absolute; top: 100%; left: 0; }
.book-target { border: 0; border-radius: 0; padding: 0; display: block; width: 100%; height: 100%; background: none !important; position: relative; }
.volume { display: block; position: absolute; top: 0; left: 0; width: 156px; height: 100%; transform-style: preserve-3d; transform-origin: 0 50%; transform: rotateY(78deg) rotateZ(var(--lean)); transition: transform .55s cubic-bezier(.2,.75,.25,1); }
.book-target:focus-visible .volume { transform: translateY(-18px) rotateY(35deg); }
@media (hover: hover) { .book-target:hover .volume { transform: translateY(-18px) rotateY(35deg); } }
.book-front { position: absolute; inset: 0; transform: translateZ(calc(var(--thickness) / 2)); background: var(--book-color); box-shadow: inset 3px 0 5px #0004, 5px 8px 13px #0002; border-radius: 1px 3px 3px 1px; overflow: hidden; backface-visibility: hidden; }
.book-front img { width: 100%; height: 100%; object-fit: cover; }
.book-front::after { content: ''; position: absolute; inset: 0; box-shadow: inset 4px 0 5px #0005; background: linear-gradient(100deg, #fff2, transparent 25%); }
.book-spine { position: absolute; top: 0; left: 0; height: 100%; width: var(--thickness); transform-origin: left center; transform: translateZ(calc(var(--thickness) / -2)) rotateY(-90deg); background: linear-gradient(90deg, #0004, transparent 20%, #ffffff12 55%, #0003), var(--book-color); color: #faf4dd; display: flex; align-items: center; padding: 15px 2px; border-radius: 2px; box-shadow: inset 0 2px #ffffff25, inset 0 -3px #0004; }
.spine-title { writing-mode: vertical-rl; font: 14px/1.15 var(--font-display); text-align: left; max-height: calc(100% - 38px); overflow: hidden; }
.spine-author { writing-mode: vertical-rl; font-size: 8px; max-height: calc(100% - 38px); overflow: hidden; opacity: .8; margin-left: 3px; }
.spine-mark { position: absolute; bottom: 8px; left: 0; width: 100%; text-align: center; font: 13px var(--font-display); border-top: 1px solid #fff3; padding-top: 3px; }
.book-pages { position: absolute; top: 1px; left: 3px; width: 150px; height: var(--thickness); transform-origin: top; transform: translateZ(calc(var(--thickness) / -2)) rotateX(90deg); background: repeating-linear-gradient(#e7e1cf 0 1px, #f7f3e8 1px 3px); }
.shelf-caption { display: flex; justify-content: space-between; gap: 20px; padding: 20px 12px; min-height: 100px; color: var(--color-muted); font-size: 13px; }
.shelf-caption p { max-width: 70%; }
.shelf-caption strong { color: var(--color-heading); font-weight: 500; }
.navigation-hint { white-space: nowrap; font-size: 11px; }
.book-dialog { width: min(920px, calc(100vw - 32px)); max-height: calc(100dvh - 40px); padding: 56px; background: #f5f2eb; color: var(--color-text); border: 1px solid var(--color-border); border-radius: 6px; box-shadow: 0 24px 90px #171e2540; }
.book-dialog::backdrop { background: #30312866; backdrop-filter: blur(6px); }
.close-preview { position: absolute; right: 14px; top: 14px; min-height: 34px; padding: 3px 11px; }
.preview-layout { display: grid; grid-template-columns: 240px 1fr; gap: 48px; align-items: start; }
.preview-cover { background: var(--book-color); box-shadow: -5px 0 0 #353a30, 0 18px 25px #242b2526; transform: rotate(-2deg); min-height: 320px; }
.preview-cover img { display: block; width: 100%; max-height: 390px; object-fit: contain; }
.cover-fallback { color: #fff7df; padding: 24px 12px; min-height: 100%; display: flex; flex-direction: column; justify-content: space-between; gap: 30px; font: 22px/1.2 var(--font-display); }
.cover-fallback small { color: inherit; font-size: 12px; }
.preview-copy h2 { font-size: clamp(25px, 3vw, 38px); }
.preview-author { font-family: var(--font-display); font-size: 20px; font-style: italic; }
.preview-description { max-height: 230px; overflow-y: auto; white-space: pre-line; font-size: 14px; }
.book-dialog[open] .preview-layout { animation: reveal .3s ease-out; }
@keyframes reveal { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
@media (max-width: 650px) { .book-dialog { padding: 52px 24px 28px; } .preview-layout { grid-template-columns: 1fr; gap: 30px; } .preview-cover { width: 150px; min-height: 210px; margin: auto; } .shelf-caption { flex-direction: column; gap: 0; } .shelf-caption p { max-width: 100%; } }
</style>
