<template>
  <main>
    <p class="eyebrow">Page not found</p>
    <h1>A page out of place.</h1>
    <p>This address doesn’t lead to a page in Marginalia.</p>
    <div class="recovery-links"><RouterLink class="button-link" to="/">Back to Discover</RouterLink><RouterLink class="button-link" to="/search">Find a book</RouterLink></div>
  </main>
</template>

<style scoped>
.recovery-links { display: flex; gap: 12px; flex-wrap: wrap; }
</style>
