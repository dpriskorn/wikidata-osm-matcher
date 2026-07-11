<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import confetti from 'canvas-confetti'
import { getMatches, confirmMatch, getAuthStatus, rejectMatch, type MatchResponse, type AuthStatus } from '../api'
import L from 'leaflet'

const { t } = useI18n()

const props = defineProps<{
  typeQid: string
  countryQid: string
  divisionQid: string
  qid: string
}>()

const router = useRouter()
const loading = ref(true)
const error = ref<string | null>(null)
const data = ref<MatchResponse | null>(null)
const confirmingId = ref<string | null>(null)
const statusMsg = ref<string | null>(null)
const mapContainer = ref<HTMLDivElement | null>(null)
const authStatus = ref<AuthStatus>({ logged_in: false, username: null })
let map: L.Map | null = null

onMounted(async () => {
  authStatus.value = await getAuthStatus()
  await load()
})

watch(data, async () => {
  await nextTick()
  if (data.value?.coord && mapContainer.value && !map) {
    initMap()
  }
})

function initMap() {
  if (!data.value?.coord || !mapContainer.value) return

  const wdCoord = data.value.coord
  map = L.map(mapContainer.value).setView([wdCoord.lat, wdCoord.lon], 16)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap'
  }).addTo(map)

  L.marker([wdCoord.lat, wdCoord.lon], {
    icon: L.divIcon({ className: 'wd-marker', html: '📍', iconSize: [24, 24] })
  }).addTo(map).bindPopup(`Wikidata: ${data.value?.label}`)

  data.value.matches.forEach(m => {
    if (m.lat && m.lon) {
      const color = m.wikidata_match ? '#198754' : '#0d6efd'
      L.circleMarker([m.lat, m.lon], {
        radius: 8,
        fillColor: color,
        color: '#fff',
        weight: 2,
        fillOpacity: 0.8
      }).addTo(map!).bindPopup(`OSM: ${m.osm_name || m.osm_type}/${m.osm_id}<br>${formatDistance(m.distance_m)}`)
    }
  })
}

async function load() {
  loading.value = true
  error.value = null
  statusMsg.value = null
  try {
    data.value = await getMatches(props.typeQid, props.countryQid, props.divisionQid, props.qid)
  } catch (e) {
    error.value = t('matchReview.couldNotLoadMatches')
  } finally {
    loading.value = false
  }
}

async function handleConfirm(osmId: string, osmType: string, osmName: string) {
  confirmingId.value = osmId
  statusMsg.value = null
  try {
    await confirmMatch(props.typeQid, props.countryQid, props.divisionQid, props.qid, osmId, osmType, osmName)
    statusMsg.value = t('matchReview.saved')
    celebrateSave()
    setTimeout(() => router.push(`/${props.typeQid}/${props.countryQid}/${props.divisionQid}`), 1500)
  } catch (e) {
    error.value = t('matchReview.couldNotSaveMatch')
  } finally {
    confirmingId.value = null
  }
}

async function handleReject() {
  try {
    await rejectMatch(props.typeQid, props.countryQid, props.divisionQid, props.qid)
    statusMsg.value = t('matchReview.rejected')
    setTimeout(() => router.push(`/${props.typeQid}/${props.countryQid}/${props.divisionQid}`), 1500)
  } catch (e) {
    error.value = t('matchReview.couldNotReject')
  }
}

function celebrateSave() {
  const myCanvas = document.createElement('canvas')
  document.body.appendChild(myCanvas)
  const myConfetti = confetti.create(myCanvas, { resize: true })
  myConfetti({
    particleCount: 50,
    spread: 40,
    origin: { y: 0.5 },
    colors: ['#28a745'],
    startVelocity: 30,
  })
  setTimeout(() => document.body.removeChild(myCanvas), 1500)
}

function openWikidata() {
  window.open(`https://www.wikidata.org/wiki/${props.qid}`, '_blank')
}

async function copyQid() {
  try {
    await navigator.clipboard.writeText(props.qid)
  } catch (e) {
    console.error('Failed to copy QID:', e)
  }
}

function getEditUrl(osmType: string, osmId: string, zoom: number): string {
  return `https://www.openstreetmap.org/edit?${osmType}=${osmId}&zoom=${zoom}`
}

function getOsmViewUrl(lat: number, lon: number, zoom: number): string {
  return `https://www.openstreetmap.org/#map=${zoom}/${lat}/${lon}`
}

function getOsmEditUrl(lat: number, lon: number, zoom: number): string {
  return `https://www.openstreetmap.org/edit?lat=${lat}&lon=${lon}&zoom=${zoom}`
}

function getJosmUrl(lat: number, lon: number, label: string): string {
  const osmXml = `<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="Wikidata-OSM Matcher">
  <node id="-1" lat="${lat}" lon="${lon}" version="0">
    <tag k="wikidata" v="${props.qid}"/>
    <tag k="leisure" v="bathing_place"/>
    <tag k="name" v="${label}"/>
  </node>
</osm>`
  const encoded = encodeURIComponent(osmXml)
  return `http://localhost:8111/load_data?new_layer=true&data=${encoded}`
}

function getSimilarityClass(sim: number): string {
  if (sim >= 0.7) return 'bg-success'
  if (sim >= 0.5) return 'bg-warning'
  return 'bg-danger'
}

function formatRelativeTime(isoTimestamp: string): string {
  const diff = Date.now() - new Date(isoTimestamp).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return t('matchReview.justNow') || "just now"
  if (mins < 60) return `${mins} min`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h`
  const days = Math.floor(hours / 24)
  return `${days}d`
}

function isDataStale(isoTimestamp: string | null): boolean {
  if (!isoTimestamp) return false
  const diff = Date.now() - new Date(isoTimestamp).getTime()
  return diff > 5 * 60 * 1000
}

function formatDistance(meters: number | null): string {
  if (meters === null) return '-'
  if (meters < 1000) return `${Math.round(meters)} m`
  return `${(meters / 1000).toFixed(1)} km`
}

function formatOsmTypeId(type: string, id: string): string {
  return t('matchReview.osmTypeId', { type: type.toUpperCase(), id })
}

function filteredTags(tags: Record<string, string>): Record<string, string> {
  const exclude = ['name', 'name:sv', 'wikidata', 'source']
  const filtered: Record<string, string> = {}
  for (const [key, value] of Object.entries(tags)) {
    if (!exclude.includes(key)) {
      filtered[key] = value
    }
  }
  return filtered
}
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <span class="fw-bold">{{ data?.label || qid }}</span>
      <div class="btn-group btn-group-sm">
        <button @click="copyQid" class="btn btn-outline-secondary" title="Copy QID">
          📋 {{ qid }}
        </button>
        <button @click="openWikidata" class="btn btn-outline-secondary">
          Wikidata ↗
        </button>
        <a v-if="data?.badkartan" :href="`https://www.badkartan.se/${data.badkartan}`" target="_blank" class="btn btn-info">
          Badkartan ↗
        </a>
      </div>
      <small class="text-muted">
        {{ authStatus.logged_in ? authStatus.username : t('auth.notLoggedIn') }}
      </small>
    </div>
    <div class="card-body">
      <p v-if="loading" class="text-muted">{{ t('matchReview.loading') }}</p>
      <p v-if="error" class="text-danger">{{ error }}</p>
      <p v-if="statusMsg" class="text-success">{{ statusMsg }}</p>

      <div v-if="data?.error" class="alert alert-warning" role="alert">
        <strong>{{ t('matchReview.overpassTimeout', { error: data.error }) }}</strong>
        <button @click="load" class="btn btn-sm btn-outline-warning ms-2">
          {{ t('matchReview.tryAgain') }}
        </button>
      </div>

      <div v-if="data?.osmTimestamp" class="mb-2">
        <small class="text-muted">{{ t('matchReview.osmDataAge', { age: formatRelativeTime(data.osmTimestamp) }) }}</small>
      </div>

      <div v-if="isDataStale(data?.osmTimestamp)" class="alert alert-warning" role="alert">
        {{ t('matchReview.osmDataStale') }}
        <button @click="load" class="btn btn-sm btn-outline-warning ms-2">
          {{ t('matchReview.refresh') }}
        </button>
      </div>

      <div v-if="data && !data.error && data.matches.length === 0" class="text-center py-4">
        <p class="text-muted mb-3">{{ t('matchReview.noMatchesFound') }}</p>
        <div v-if="data.coord" class="d-flex justify-content-center gap-2 mb-3">
          <a :href="getOsmViewUrl(data.coord.lat, data.coord.lon, 18)"
             target="_blank" class="btn btn-primary">
            {{ t('matchReview.viewInOSM') }}
          </a>
          <a :href="getOsmEditUrl(data.coord.lat, data.coord.lon, 18)"
             target="_blank" class="btn btn-success">
            {{ t('matchReview.createInOSM') }}
          </a>
          <a :href="getJosmUrl(data.coord.lat, data.coord.lon, data.label)"
              target="_blank" class="btn btn-warning">
            {{ t('matchReview.josmAddNode') }}
          </a>
          <button @click="handleReject" class="btn btn-warning">
            {{ t('matchReview.markMissing') }}
          </button>
        </div>
      </div>

      <ul v-if="data && !data.error && data.matches.length" class="list-unstyled">
        <li v-for="m in data.matches" :key="m.osm_id" class="card mb-3">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-start mb-2">
              <div class="d-flex flex-wrap gap-2 align-items-center">
                <span class="badge bg-secondary">{{ formatOsmTypeId(m.osm_type, m.osm_id) }}</span>
                <span v-if="m.wikidata_match" class="badge bg-info">{{ t('matchReview.wikidataLinkExists') }}</span>
                <span class="badge" :class="getSimilarityClass(m.similarity)">
                  {{ t('matchReview.similarity', { percent: Math.round(m.similarity * 100) }) }}
                </span>
                <span v-if="m.distance_m !== null" class="badge bg-light text-dark">
                  {{ t('matchReview.distance', { distance: formatDistance(m.distance_m) }) }}
                </span>
                <span v-if="m.needs_investigation" class="badge bg-warning">{{ t('matchReview.needsInvestigation') }}</span>
              </div>
              <span class="fw-bold">{{ m.osm_name || t('matchReview.noName') }}</span>
            </div>
            <div v-if="Object.keys(filteredTags(m.tags)).length > 0" class="mb-2">
              <small class="text-muted">
                <span v-for="(value, key) in filteredTags(m.tags)" :key="key" class="me-2">
                  <code>{{ key }}={{ value }}</code>
                </span>
              </small>
            </div>
              <div class="d-flex gap-2">
              <a :href="getEditUrl(m.osm_type, m.osm_id, m.zoom)"
                 target="_blank" class="btn btn-outline-primary btn-sm"
                 :class="{ disabled: confirmingId !== null }">
                {{ t('matchReview.editInOSM') }}
              </a>
              <button
                @click="handleConfirm(m.osm_id, m.osm_type, m.osm_name)"
                :disabled="confirmingId !== null"
                class="btn btn-success btn-sm"
              >
                {{ confirmingId === m.osm_id ? t('matchReview.saving') : t('matchReview.uploadOsmIdToWikidata') }}
              </button>
            </div>
          </div>
        </li>
      </ul>

      <div v-if="data?.coord" ref="mapContainer" id="match-map" class="mt-3" style="height: 400px; border-radius: 8px;"></div>
    </div>
    <div class="card-footer">
      <button @click="router.push(`/${typeQid}/${countryQid}/${divisionQid}`)" class="btn btn-sm btn-outline-secondary">
        {{ t('matchReview.backToList') }}
      </button>
    </div>
  </div>
</template>

<style>
.wd-marker {
  background: none;
  border: none;
}
</style>
