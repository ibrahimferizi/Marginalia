<script setup>
import { ref, watch } from 'vue'

const props = defineProps({ username: { type: String, default: '' }, url: { type: String, default: '' } })
const broken = ref(false)
watch(() => props.url, () => { broken.value = false })
</script>

<template>
  <div class="reader-avatar" aria-hidden="true">
    <img v-if="url && !broken" :src="url" alt="" referrerpolicy="no-referrer" @error="broken = true" />
    <span v-else>{{ username.slice(0, 1).toUpperCase() || 'M' }}</span>
  </div>
</template>
