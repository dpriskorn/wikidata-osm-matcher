<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { getDivisions, getWikidataLabel, type DivisionInfo } from '../api'

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
const totalCandidates = computed(() => divisions.value.reduce((sum, d) => sum + d.count, 0))
const divisionsWithCandidates = computed(() => divisions.value.filter(d => d.count > 0).length)

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
  </div>
</template>