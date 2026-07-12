<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { getDivisions, getWikidataLabel, type DivisionInfo } from '../api'
import L from 'leaflet'

const { locale } = useI18n()

const props = defineProps<{
  typeQid: string
  countryQid: string
}>()

const router = useRouter()
const divisions = ref<DivisionInfo[]>([])
const loading = ref(true)
const labelsLoading = ref(true)
const error = ref<string | null>(null)
const labels = ref<Record<string, string>>({})
const mapContainer = ref<HTMLDivElement | null>(null)
let map: L.Map | null = null
const totalCandidates = computed(() => divisions.value.reduce((sum, d) => sum + d.count, 0))
const divisionsWithCandidates = computed(() => divisions.value.filter(d => d.count > 0).length)
const divisionsWithCoords = computed(() => divisions.value.filter(d => d.lat != null && d.lon != null))

onMounted(async () => {
  try {
    divisions.value = await getDivisions(props.typeQid, props.countryQid)
    await fetchLabels()
  } catch (e) {
    error.value = 'Kunde inte ladda administrativa enheter'
  } finally {
    loading.value = false
    labelsLoading.value = false
  }
})

async function fetchLabels() {
  const results = await Promise.all(
    divisions.value.map(d => getWikidataLabel(d.qid, locale.value))
  )
  results.forEach((label, i) => {
    labels.value[divisions.value[i].qid] = label
  })
  await nextTick()
  initMap()
}

function initMap() {
  if (!mapContainer.value || divisionsWithCoords.value.length === 0) return

  const coords = divisionsWithCoords.value.map(d => ({ lat: d.lat!, lon: d.lon! }))
  const centerLat = coords.reduce((sum, c) => sum + c.lat, 0) / coords.length
  const centerLon = coords.reduce((sum, c) => sum + c.lon, 0) / coords.length

  map = L.map(mapContainer.value).setView([centerLat, centerLon], 7)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap'
  }).addTo(map)

  divisions.value.forEach(d => {
    if (d.lat == null || d.lon == null) return

    const name = labels.value[d.qid] || d.qid
    L.circleMarker([d.lat, d.lon], {
      radius: 8,
      fillColor: '#0d6efd',
      color: '#fff',
      weight: 2,
      fillOpacity: 0.8
    }).addTo(map!).bindPopup(`
      <strong>${name}</strong><br>
      ${d.count} omatchade<br>
      <a href="/${props.typeQid}/${props.countryQid}/${d.qid}">Visa kandidater</a>
    `).on('click', () => {
      router.push(`/${props.typeQid}/${props.countryQid}/${d.qid}`)
    })
  })
}

function selectDivision(division: DivisionInfo) {
  router.push(`/${props.typeQid}/${props.countryQid}/${division.qid}`)
}
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <h2 class="h5 mb-0">Välj administrativ enhet</h2>
      <button @click="router.push(`/${typeQid}`)" class="btn btn-sm btn-outline-secondary">← Tillbaka</button>
    </div>
    <div class="card-body">
      <p v-if="loading || labelsLoading" class="text-muted">Laddar...</p>
      <p v-if="error" class="text-danger">{{ error }}</p>
      <p v-else-if="divisions.length === 0" class="text-muted">Inga enheter hittades.</p>
      <template v-else>
        <div v-if="divisionsWithCandidates > 0" class="mb-3">
          <small class="text-muted">{{ divisionsWithCandidates }} enheter med {{ totalCandidates }} omatchade</small>
        </div>
        <div v-if="divisionsWithCoords.length > 0" ref="mapContainer" class="mb-3" style="height: 400px; border-radius: 8px;"></div>
        <div class="list-group">
        <button
          v-for="d in divisions"
          :key="d.qid"
          @click="selectDivision(d)"
          class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
        >
          {{ labels[d.qid] || d.qid }}
          <span class="badge bg-primary rounded-pill">{{ d.count }}</span>
        </button>
      </div>
      </template>
    </div>
    <div class="card-footer">
      <button @click="router.push(`/${typeQid}`)" class="btn btn-sm btn-outline-secondary">← Tillbaka</button>
    </div>
  </div>
</template>