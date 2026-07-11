<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getMatches, confirmMatch, type MatchResponse } from '../api'

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
const confirming = ref(false)
const statusMsg = ref<string | null>(null)

onMounted(async () => {
  await load()
})

async function load() {
  loading.value = true
  error.value = null
  statusMsg.value = null
  try {
    data.value = await getMatches(props.typeQid, props.countryQid, props.divisionQid, props.qid)
  } catch (e) {
    error.value = 'Kunde inte ladda matcher'
  } finally {
    loading.value = false
  }
}

async function handleConfirm(osmId: string, osmType: string, osmName: string) {
  confirming.value = true
  statusMsg.value = null
  try {
    await confirmMatch(props.typeQid, props.countryQid, props.divisionQid, props.qid, osmId, osmType, osmName)
    statusMsg.value = 'Matchning sparad!'
    setTimeout(() => router.push(`/${props.typeQid}/${props.countryQid}/${props.divisionQid}`), 1500)
  } catch (e) {
    error.value = 'Kunde inte spara matchning'
  } finally {
    confirming.value = false
  }
}

function openWikidata() {
  window.open(`https://www.wikidata.org/wiki/${props.qid}`, '_blank')
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

function getSimilarityClass(sim: number): string {
  if (sim >= 0.7) return 'bg-success'
  if (sim >= 0.5) return 'bg-warning'
  return 'bg-danger'
}

function formatRelativeTime(isoTimestamp: string): string {
  const diff = Date.now() - new Date(isoTimestamp).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "nyss"
  if (mins < 60) return `${mins} minut${mins === 1 ? '' : 'er'} sedan`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} timme${hours === 1 ? '' : 'r'} sedan`
  const days = Math.floor(hours / 24)
  return `${days} dag${days === 1 ? '' : 'ar'} sedan`
}

function isDataStale(isoTimestamp: string | null): boolean {
  if (!isoTimestamp) return false
  const diff = Date.now() - new Date(isoTimestamp).getTime()
  return diff > 5 * 60 * 1000
}
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <span class="fw-bold">{{ data?.label || qid }}</span>
      <button @click="openWikidata" class="btn btn-outline-secondary btn-sm">
        Wikidata ↗
      </button>
    </div>
    <div class="card-body">
      <p v-if="loading" class="text-muted">Laddar...</p>
      <p v-if="error" class="text-danger">{{ error }}</p>
      <p v-if="statusMsg" class="text-success">{{ statusMsg }}</p>

      <div v-if="data?.error" class="alert alert-warning" role="alert">
        <strong>Overpass timeout:</strong> {{ data.error }}
        <button @click="load" class="btn btn-sm btn-outline-warning ms-2">
          Försök igen
        </button>
      </div>

      <div v-if="data?.osmTimestamp" class="mb-2">
        <small class="text-muted">OSM-data: {{ formatRelativeTime(data.osmTimestamp) }}</small>
      </div>

      <div v-if="isDataStale(data?.osmTimestamp)" class="alert alert-warning" role="alert">
        OSM-datan är mer än 5 minuter gammal, uppdatera sidan för färsk data
        <button @click="load" class="btn btn-sm btn-outline-warning ms-2">
          Uppdatera
        </button>
      </div>

      <div v-if="data && !data.error && data.matches.length === 0" class="text-center py-4">
        <p class="text-muted mb-3">Inga OSM-kandidater hittades.</p>
        <div v-if="data.coord" class="d-flex justify-content-center gap-2 mb-3">
          <a :href="getOsmViewUrl(data.coord.lat, data.coord.lon, 18)"
             target="_blank" class="btn btn-primary">
            Visa i OSM ↗
          </a>
          <a :href="getOsmEditUrl(data.coord.lat, data.coord.lon, 18)"
             target="_blank" class="btn btn-success">
            Skapa i OSM ↗
          </a>
        </div>
      </div>

      <ul v-if="data && !data.error && data.matches.length" class="list-unstyled">
        <li v-for="m in data.matches" :key="m.osm_id" class="card mb-3">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-start mb-2">
              <div>
                <span class="badge bg-secondary me-2">{{ m.osm_type.toUpperCase() }}/{{ m.osm_id }}</span>
                <span class="badge" :class="getSimilarityClass(m.similarity)">
                  {{ Math.round(m.similarity * 100) }}%
                </span>
              </div>
              <span class="fw-bold">{{ m.osm_name }}</span>
            </div>
            <div class="d-flex gap-2">
              <a :href="getEditUrl(m.osm_type, m.osm_id, m.zoom)"
                 target="_blank" class="btn btn-outline-primary btn-sm">
                Redigera i OSM ↗
              </a>
              <button
                @click="handleConfirm(m.osm_id, m.osm_type, m.osm_name)"
                :disabled="confirming"
                class="btn btn-success btn-sm"
              >
                {{ confirming ? 'Sparar...' : 'Bekräfta' }}
              </button>
            </div>
          </div>
        </li>
      </ul>
    </div>
    <div class="card-footer">
      <button @click="router.push(`/${typeQid}/${countryQid}/${divisionQid}`)" class="btn btn-sm btn-outline-secondary">
        ← Tillbaka till lista
      </button>
    </div>
  </div>
</template>
