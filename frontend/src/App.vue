<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const pageTitle = computed(() => {
  if (route.path === '/') return 'Wikidata-OSM Matcher'
  if (route.params.typeQid) return `Typ: ${route.params.typeQid}`
  return 'Wikidata-OSM Matcher'
})
</script>

<template>
  <div class="app container py-3">
    <header class="d-flex justify-content-between align-items-center mb-4">
      <h1 class="h4 mb-0">{{ pageTitle }}</h1>
      <nav v-if="route.path !== '/'">
        <router-link to="/" class="btn btn-outline-primary btn-sm">← Byt objekttyp</router-link>
      </nav>
    </header>
    <main>
      <router-view />
    </main>
  </div>
</template>

<style>
body {
  background-color: #f5f5f5;
}
</style>