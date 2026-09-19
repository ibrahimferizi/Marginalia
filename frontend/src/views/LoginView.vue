<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const username = ref('')
const password = ref('')
const error = ref(null)
const submitting = ref(false)
const auth = useAuthStore()
const router = useRouter()

async function handleLogin() {
  if (submitting.value) return
  error.value = null
  submitting.value = true
  try {
    await auth.login(username.value.trim(), password.value)
    await router.push('/')
  } catch (err) {
    error.value = err.message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="account-entry">
    <div class="account-intro">
      <p class="eyebrow">Your reading life</p>
      <h1>Back to your<br />next chapter.</h1>
      <p>Your shelves, your notes, and more books to fall into.</p>
    </div>
    <div class="account-panel">
      <h2>Welcome back</h2>
      <p class="muted">Log in to Marginalia.</p>
      <form class="account-form" @submit.prevent="handleLogin" :aria-busy="submitting">
        <label>Username<input v-model="username" name="username" autocomplete="username" autocapitalize="none" spellcheck="false" required :disabled="submitting" /></label>
        <label>Password<input v-model="password" name="password" type="password" autocomplete="current-password" required :disabled="submitting" /></label>
        <p v-if="error" role="alert">{{ error }}</p>
        <button class="account-primary" type="submit" :disabled="submitting">{{ submitting ? 'Logging in…' : 'Log in' }}</button>
      </form>
      <p class="account-footnote">New here? <RouterLink to="/register">Create an account</RouterLink></p>
    </div>
  </main>
</template>
