<script setup>
import { RouterLink, RouterView } from 'vue-router'
import { ref } from 'vue'
import { useAuthStore } from './stores/auth'
const auth = useAuthStore()
const loggingOut = ref(false)
const logoutError = ref('')

async function logout() {
  if (loggingOut.value) return
  loggingOut.value = true
  logoutError.value = ''
  try {
    await auth.logout()
  } catch {
    logoutError.value = 'Could not log out. Please try again.'
  } finally {
    loggingOut.value = false
  }
}
</script>

<template>
  <a class="skip-link" href="#main-content">Skip to content</a>
  <header class="site-header">
    <RouterLink to="/" class="wordmark" aria-label="Marginalia home">marginalia<span aria-hidden="true">.</span></RouterLink>
    <nav aria-label="Main navigation">
      <RouterLink to="/">Discover</RouterLink>
      <RouterLink to="/search">Search</RouterLink>
      <template v-if="auth.isLoggedIn">
        <RouterLink to="/recommendations">For you</RouterLink>
        <RouterLink to="/my-reading-list">My library</RouterLink>
      </template>
    </nav>
    <div class="account-nav">
      <template v-if="auth.isLoggedIn">
        <RouterLink to="/profile" class="profile-link">{{ auth.username }}</RouterLink>
        <button :disabled="loggingOut" @click="logout">{{ loggingOut ? 'Logging out…' : 'Log out' }}</button>
      </template>
      <template v-else><RouterLink to="/login">Log in</RouterLink><RouterLink to="/register" class="button-link">Join the library</RouterLink></template>
    </div>
  </header>
  <p v-if="logoutError" class="logout-error" role="alert">{{ logoutError }}</p>
  <div id="main-content" tabindex="-1"><RouterView /></div>
  <footer><span>marginalia.</span><p>A place for the books that stay with you.</p></footer>
</template>

<style scoped>
.site-header { display: flex; align-items: center; gap: 32px; min-height: 100px; border-bottom: 1px solid var(--color-border); flex-wrap: wrap; padding: 20px 0; }
.logout-error { margin: 16px 0 0; text-align: right; font-size: 13px; }
.wordmark { font: 34px/1 var(--font-display); letter-spacing: -.065em; color: var(--color-heading); text-decoration: none; }
.wordmark span { color: #859264; }
nav { display: flex; gap: 24px; align-items: center; }
nav a, .account-nav a { font-size: 13px; text-decoration: none; }
nav .router-link-exact-active { color: var(--color-heading); text-decoration: underline; text-underline-offset: 9px; }
.account-nav { margin-left: auto; display: flex; gap: 18px; align-items: center; }
.profile-link { max-width: 140px; overflow: hidden; text-overflow: ellipsis; }
footer { border-top: 1px solid var(--color-border); display: flex; justify-content: space-between; gap: 20px; padding: 24px 0; color: var(--color-muted); font-size: 12px; }
footer span { font: 22px var(--font-display); letter-spacing: -.05em; }
.skip-link { position: absolute; top: -100px; padding: 12px; background: var(--color-background); z-index: 100; }
.skip-link:focus { top: 0; }
@media (max-width: 850px) { nav { order: 3; width: 100%; gap: 24px; flex-wrap: wrap; } .site-header { gap: 20px; } }
@media (max-width: 450px) { .wordmark { font-size: 29px; } .account-nav { gap: 8px; } .account-nav button, .account-nav .button-link { padding: 7px 10px; } footer { flex-direction: column; gap: 8px; } }
</style>
