<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getCandidates, type CandidateInfo } from '../api'

const props = defineProps<{
  typeQid: string
  countryQid: string
}>()

const router = useRouter()
const candidates = ref<CandidateInfo[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    candidates.value = await getCandidates(props.typeQid, props.countryQid)
  } catch (e) {
    error.value = 'Kunde inte ladda kandidater'
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => [props.typeQid, props.countryQid], load)

function selectCandidate(qid: string) {
  router.push(`/${props.typeQid}/${props.countryQid}/${qid}`)
}
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <h2 class="h5 mb-0">Kandidater</h2>
      <button @click="router.push(`/${typeQid}`)" class="btn btn-sm btn-outline-secondary">← Tillbaka</button>
    </div>
    <div class="card-body p-0">
      <p v-if="loading" class="text-muted p-3">Laddar...</p>
      <p v-if="error" class="text-danger p-3">{{ error }}</p>
      <ul v-else-if="candidates.length" class="list-group list-group-flush">
        <li
          v-for="c in candidates"
          :key="c.qid"
          @click="selectCandidate(c.qid)"
          class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
        >
          <div>
            <span class="fw-bold">{{ c.label }}</span>
            <span class="text-muted ms-2">{{ c.qid }}</span>
          </div>
        </li>
      </ul>
      <p v-else class="text-muted p-3">Inga kandidater hittades.</p>
    </div>
    <div class="card-footer text-muted">
      {{ candidates.length }} objekt
    </div>
  </div>
</template>