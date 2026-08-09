<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const username = ref('')
const password = ref('')
const error = ref(null)
const auth = useAuthStore()
const router = useRouter()

async function handleLogin() {
  error.value = null
  try {
    await auth.login(username.value, password.value)
    router.push('/')
  } catch (err) {
    error.value = err.message
  }
}
</script>

<template>
  <main>
    <h1>Login</h1>
    <form @submit.prevent="handleLogin">
      <input v-model="username" placeholder="Username" />
      <input v-model="password" type="password" placeholder="Password" />
      <button type="submit">Log in</button>
    </form>
    <p v-if="error">{{ error }}</p>
  </main>
</template>