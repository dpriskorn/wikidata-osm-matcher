<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import confetti from 'canvas-confetti'
import { getCandidates, type CandidateInfo } from '../api'

const { t } = useI18n()

const props = defineProps<{
  typeQid: string
  countryQid: string
  divisionQid: string
}>()

const router = useRouter()
const candidates = ref<CandidateInfo[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    candidates.value = await getCandidates(props.typeQid, props.countryQid, props.divisionQid)
    checkAllDone()
  } catch (e) {
    error.value = 'Kunde inte ladda kandidater'
  } finally {
    loading.value = false
  }
}

function checkAllDone() {
  if (candidates.value.length === 0 && !loading.value) {
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
      <p v-if="loading" class="text-muted p-3">{{ t('candidateList.loading') }}</p>
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
            <span class="fw-bold">{{ c.label }}</span>
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
    <div v-if="candidates.length" class="card-footer text-muted">
      {{ candidates.length }} objekt
    </div>
  </div>
</template>