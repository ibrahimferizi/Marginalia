<script setup>
import { RouterLink, RouterView } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()

</script>

<template>
  <nav>
    <RouterLink to="/">Home</RouterLink>
    | <RouterLink to="/search">Search</RouterLink>
    <span v-if="auth.isLoggedIn">
      | <RouterLink to="/recommendations">Recommendations</RouterLink>
      | <RouterLink to="/my-reading-list">My Reading List</RouterLink>
      | Logged in as {{ auth.username }} <button @click="auth.logout()">Logout</button>
      | <RouterLink to="/profile">Profile</RouterLink>
    </span>
    <span v-else> | <RouterLink to="/login">Login</RouterLink> | <RouterLink to="/register">Sign up</RouterLink></span>
  </nav>

  <RouterView />
</template>