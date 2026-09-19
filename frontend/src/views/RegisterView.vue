<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const email = ref('')
const password = ref('')
const error = ref(null)
const submitting = ref(false)
const registered = ref(false)

async function handleSubmit() {
  if (submitting.value || registered.value) return
  error.value = null
  submitting.value = true
  try {
    await auth.register(username.value.trim(), email.value.trim(), password.value)
    registered.value = true
    await auth.login(username.value.trim(), password.value)
    await router.push('/')
  } catch (err) {
    error.value = registered.value ? 'Your account was created, but we could not log you in. Please log in to continue.' : err.message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="account-entry">
    <div class="account-intro">
      <p class="eyebrow">A place for your books</p>
      <h1>Make room for<br />a new favourite.</h1>
      <p>Keep a personal library, share what you think, and find recommendations shaped by your reading.</p>
    </div>
    <div class="account-panel">
      <h2>Start your library</h2>
      <p class="muted">Create your Marginalia account.</p>
      <form class="account-form" @submit.prevent="handleSubmit" :aria-busy="submitting">
        <label>Username<input v-model="username" name="username" autocomplete="username" autocapitalize="none" spellcheck="false" maxlength="150" required :disabled="submitting || registered" /></label>
        <label>Email<input v-model="email" name="email" type="email" autocomplete="email" required :disabled="submitting || registered" /></label>
        <label>Password<input v-model="password" name="password" type="password" autocomplete="new-password" minlength="8" required aria-describedby="password-hint" :disabled="submitting || registered" /><small id="password-hint">Use at least 8 characters.</small></label>
        <p v-if="error" role="alert">{{ error }}</p>
        <RouterLink v-if="registered && !submitting" class="button-link account-primary" to="/login">Continue to log in</RouterLink>
        <button v-else class="account-primary" type="submit" :disabled="submitting">{{ submitting ? 'Creating your account…' : 'Create account' }}</button>
      </form>
      <p class="account-footnote">Already have an account? <RouterLink to="/login">Log in</RouterLink></p>
    </div>
  </main>
</template>
