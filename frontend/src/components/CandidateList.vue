<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import confetti from 'canvas-confetti'
import { getCandidates, getWikidataLabel, type CandidateInfo } from '../api'

const { t, locale } = useI18n()

const props = defineProps<{
  typeQid: string
  countryQid: string
  divisionQid: string
}>()

const router = useRouter()
const candidates = ref<CandidateInfo[]>([])
const loading = ref(true)
const labelsLoading = ref(true)
const error = ref<string | null>(null)
const hasLoaded = ref(false)
const LABEL_CACHE_KEY = 'wikidata_labels'

const labels = ref<Record<string, string>>(loadLabelsFromCache())

function loadLabelsFromCache(): Record<string, string> {
  try {
    const cached = localStorage.getItem(LABEL_CACHE_KEY)
    return cached ? JSON.parse(cached) : {}
  } catch {
    return {}
  }
}

function saveLabelsToCache() {
  try {
    localStorage.setItem(LABEL_CACHE_KEY, JSON.stringify(labels.value))
  } catch {}
}

function clearLabelCache() {
  localStorage.removeItem(LABEL_CACHE_KEY)
  labels.value = {}
}

async function load() {
  loading.value = true
  labelsLoading.value = true
  error.value = null
  candidates.value = []
  try {
    candidates.value = await getCandidates(props.typeQid, props.countryQid, props.divisionQid)
    await fetchLabels()
    hasLoaded.value = true
    checkAllDone()
  } catch (e) {
    error.value = 'Kunde inte ladda kandidater'
  } finally {
    loading.value = false
    labelsLoading.value = false
  }
}

async function fetchLabels() {
  const uncached = candidates.value.filter(c => !labels.value[c.qid])
  if (uncached.length === 0) return
  const results = await Promise.all(
    uncached.map(c => getWikidataLabel(c.qid, locale.value))
  )
  results.forEach((label, i) => {
    labels.value[uncached[i].qid] = label
  })
  saveLabelsToCache()
}

function checkAllDone() {
  if (hasLoaded.value && !loading.value && candidates.value.length === 0) {
    celebrateAllDone()
  }
}

function celebrateAllDone() {
  const myCanvas = document.createElement('canvas')
  document.body.appendChild(myCanvas)
  const myConfetti = confetti.create(myCanvas, { resize: true })
  myConfetti({
    particleCount: 150,
    spread: 70,
    origin: { y: 0.6 },
    colors: ['#28a745', '#17a2b8', '#ffc107', '#dc3545'],
  })
  setTimeout(() => document.body.removeChild(myCanvas), 2000)
}

onMounted(load)
watch(() => [props.typeQid, props.countryQid, props.divisionQid], load)

function selectCandidate(qid: string) {
  router.push(`/${props.typeQid}/${props.countryQid}/${props.divisionQid}/${qid}`)
}
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <h2 class="h5 mb-0">Kandidater</h2>
      <button @click="router.push(`/${typeQid}/${countryQid}`)" class="btn btn-sm btn-outline-secondary">← Tillbaka</button>
    </div>
    <div class="card-body p-0">
      <p v-if="loading || labelsLoading" class="text-muted p-3">
        {{ labelsLoading ? 'Laddar etiketter...' : t('candidateList.loading') }}
      </p>
      <p v-if="error" class="text-danger p-3">{{ error }}</p>
      <ul v-else-if="candidates.length" class="list-group list-group-flush">
        <li
          v-for="c in candidates"
          :key="c.qid"
          @click="selectCandidate(c.qid)"
          class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
          style="cursor: pointer"
        >
          <div>
            <span class="fw-bold">{{ labels[c.qid] }}</span>
            <span class="text-muted ms-2">{{ c.qid }}</span>
          </div>
        </li>
      </ul>
      <div v-else class="text-center py-5">
        <p class="text-success fs-1 mb-2">🎉</p>
        <p class="text-success fw-bold">{{ t('candidateList.allDone') }}</p>
        <p class="text-muted">{{ t('candidateList.allDoneMessage') }}</p>
      </div>
    </div>
    <div class="card-footer d-flex justify-content-between align-items-center">
      <button @click="router.push(`/${typeQid}/${countryQid}`)" class="btn btn-sm btn-outline-secondary">← Tillbaka</button>
      <div v-if="candidates.length" class="text-muted">
        <span>{{ candidates.length }} objekt</span>
        <button @click="clearLabelCache" class="btn btn-sm btn-outline-secondary ms-2">Rensa cache</button>
      </div>
    </div>
  </div>
</template>