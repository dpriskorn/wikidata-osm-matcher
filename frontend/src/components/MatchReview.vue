<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getMatches, confirmMatch, rejectMatch, type MatchResponse } from '../api'

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
const rejecting = ref(false)
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

async function handleReject() {
  rejecting.value = true
  statusMsg.value = null
  try {
    await rejectMatch(props.typeQid, props.countryQid, props.divisionQid, props.qid)
    statusMsg.value = 'Markerad som "ingen match"'
    setTimeout(() => router.push(`/${props.typeQid}/${props.countryQid}/${props.divisionQid}`), 1500)
  } catch (e) {
    error.value = 'Kunde inte spara'
  } finally {
    rejecting.value = false
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

      <div v-if="data && data.matches.length === 0" class="text-center py-4">
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
        <button
          @click="handleReject"
          :disabled="rejecting"
          class="btn btn-outline-danger"
        >
          {{ rejecting ? 'Sparar...' : 'Markera som "ingen match"' }}
        </button>
      </div>

      <ul v-if="data && data.matches.length" class="list-unstyled">
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

      <div v-if="data && data.matches.length > 1" class="mt-3 pt-3 border-top">
        <button
          @click="handleReject"
          :disabled="rejecting"
          class="btn btn-outline-secondary"
        >
          {{ rejecting ? 'Sparar...' : 'Ingen av dessa matchar' }}
        </button>
      </div>
    </div>
    <div class="card-footer">
      <button @click="router.push(`/${typeQid}/${countryQid}/${divisionQid}`)" class="btn btn-sm btn-outline-secondary">
        ← Tillbaka till lista
      </button>
    </div>
  </div>
</template>