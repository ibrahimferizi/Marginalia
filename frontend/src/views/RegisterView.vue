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

async function handleSubmit() {
  error.value = null
  submitting.value = true
  try {
    await auth.register(username.value, email.value, password.value)
    await auth.login(username.value, password.value)
    router.push('/')
  } catch (err) {
    error.value = err.message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main>
    <h1>Sign up</h1>
    <form @submit.prevent="handleSubmit">
      <label>
        Username:
        <input v-model="username" required />
      </label>
      <label>
        Email:
        <input v-model="email" type="email" required />
      </label>
      <label>
        Password:
        <input v-model="password" type="password" minlength="8" required />
      </label>
      <button type="submit" :disabled="submitting">Sign up</button>
      <p v-if="error">{{ error }}</p>
    </form>
    <p>
      Already have an account? <RouterLink to="/login">Log in</RouterLink>
    </p>
  </main>
</template>