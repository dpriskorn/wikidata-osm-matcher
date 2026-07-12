<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { getWikidataLabel, getAuthStatus, type AuthStatus } from './api'
import { availableLocales } from './i18n'
import HealthBanner from './components/HealthBanner.vue'

const { t, locale } = useI18n()
const route = useRoute()
const typeLabel = ref<string | null>(null)
const authStatus = ref<AuthStatus>({ logged_in: false, username: null })
const selectedRadius = ref(0.5)
const RADIUS_STORAGE_KEY = 'overpass_radius'

const radiusOptions = [
  { value: 0.5, label: '500m' },
  { value: 1.0, label: '1000m' },
]

function setRadius(radius: number) {
  selectedRadius.value = radius
  localStorage.setItem(RADIUS_STORAGE_KEY, String(radius))
}

async function fetchTypeLabel() {
  if (route.params.typeQid) {
    try {
      typeLabel.value = await getWikidataLabel(route.params.typeQid as string, locale.value)
    } catch {
      typeLabel.value = null
    }
  } else {
    typeLabel.value = null
  }
}

async function fetchAuthStatus() {
  try {
    authStatus.value = await getAuthStatus()
  } catch {
    authStatus.value = { logged_in: false, username: null }
  }
}

function changeLocale(code: string) {
  locale.value = code
  localStorage.setItem('locale', code)
  fetchTypeLabel()
}

watch(() => route.params.typeQid, fetchTypeLabel, { immediate: true })
watch(locale, fetchTypeLabel)

const pageTitle = computed(() => {
  if (route.path === '/') return t('app.title')
  if (route.params.typeQid) {
    const qid = route.params.typeQid
    if (typeLabel.value) return `${typeLabel.value} (${qid})`
    return qid
  }
  return t('app.title')
})

onMounted(() => {
  const saved = localStorage.getItem('locale')
  if (saved && availableLocales.some(l => l.code === saved)) {
    locale.value = saved
  }
  const savedRadius = localStorage.getItem(RADIUS_STORAGE_KEY)
  if (savedRadius) {
    selectedRadius.value = parseFloat(savedRadius)
  }
  fetchAuthStatus()
})
</script>

<template>
  <div class="app">
    <HealthBanner />
    <nav class="navbar navbar-expand-lg navbar-light bg-light mb-3">
      <div class="container">
        <span class="navbar-brand mb-0 h1">{{ t('app.title') }}</span>
        <div class="d-flex align-items-center">
          <router-link v-if="route.path !== '/'" to="/" class="btn btn-outline-primary btn-sm me-2">
            {{ t('app.changeObjectType') }}
          </router-link>
          <div class="dropdown me-2">
            <button class="btn btn-outline-secondary btn-sm dropdown-toggle" type="button" data-bs-toggle="dropdown">
              {{ availableLocales.find(l => l.code === locale)?.name || locale }}
            </button>
            <ul class="dropdown-menu dropdown-menu-end">
              <li v-for="loc in availableLocales" :key="loc.code">
                <button class="dropdown-item" :class="{ active: locale === loc.code }" @click="changeLocale(loc.code)">
                  {{ loc.name }}
                </button>
              </li>
            </ul>
          </div>
          <div class="dropdown me-2">
            <button class="btn btn-outline-secondary btn-sm dropdown-toggle" type="button" data-bs-toggle="dropdown">
              {{ radiusOptions.find(r => r.value === selectedRadius)?.label || '500m' }}
            </button>
            <ul class="dropdown-menu dropdown-menu-end">
              <li v-for="r in radiusOptions" :key="r.value">
                <button class="dropdown-item" :class="{ active: selectedRadius === r.value }" @click="setRadius(r.value)">
                  {{ r.label }}
                </button>
              </li>
            </ul>
          </div>
          <div class="dropdown">
            <button class="btn btn-outline-secondary btn-sm dropdown-toggle" type="button" data-bs-toggle="dropdown">
              {{ authStatus.logged_in ? authStatus.username : t('auth.notLoggedIn') }}
            </button>
            <ul class="dropdown-menu dropdown-menu-end">
              <li v-if="authStatus.logged_in">
                <span class="dropdown-item-text">{{ t('auth.loggedInAs', { username: authStatus.username }) }}</span>
              </li>
              <li v-if="authStatus.logged_in">
                <button class="dropdown-item" @click="fetchAuthStatus">{{ t('auth.refresh') }}</button>
              </li>
              <li v-else>
                <button class="dropdown-item disabled">{{ t('auth.loginWithWikimediaOAuth') }}</button>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </nav>
    <div class="container py-3">
      <main>
        <router-view />
      </main>
    </div>
  </div>
</template>

<style>
body {
  background-color: #f5f5f5;
}
</style>