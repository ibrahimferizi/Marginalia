import { ref, onBeforeUnmount } from 'vue'
import { apiFetch } from '../api'

export function usePagedBooks() {
  const books = ref([])
  const count = ref(0)
  const sources = ref([])
  const next = ref(null)
  const previous = ref(null)
  const loading = ref(false)
  const error = ref('')
  let controller

  function clear() {
    controller?.abort()
    books.value = []
    count.value = 0
    sources.value = []
    next.value = null
    previous.value = null
    error.value = ''
    loading.value = false
  }

  async function load(url) {
    clear()
    const request = new AbortController()
    controller = request
    loading.value = true
    try {
      const response = await apiFetch(url, { signal: request.signal })
      if (!response.ok) throw new Error(response.status === 401 ? 'Please log in to continue.' : 'Could not load books. Please try again.')
      const data = await response.json()
      if (request.signal.aborted) return
      books.value = data.results ?? data
      count.value = data.count ?? books.value.length
      sources.value = data.sources ?? []
      next.value = data.next ?? null
      previous.value = data.previous ?? null
    } catch (err) {
      if (!request.signal.aborted) error.value = err.message
    } finally {
      if (!request.signal.aborted) loading.value = false
    }
  }

  onBeforeUnmount(() => controller?.abort())
  return { books, count, sources, next, previous, loading, error, load, clear }
}
