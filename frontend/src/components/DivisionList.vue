<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getDivisions, type DivisionInfo } from '../api'

const props = defineProps<{
  typeQid: string
  countryQid: string
}>()

const router = useRouter()
const divisions = ref<DivisionInfo[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    divisions.value = await getDivisions(props.typeQid, props.countryQid)
  } catch (e) {
    error.value = 'Kunde inte ladda administrativa enheter'
  } finally {
    loading.value = false
  }
})

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
      <p v-if="loading" class="text-muted">Laddar...</p>
      <p v-if="error" class="text-danger">{{ error }}</p>
      <p v-else-if="divisions.length === 0" class="text-muted">Inga enheter hittades.</p>
      <div v-else class="list-group">
        <button
          v-for="d in divisions"
          :key="d.qid"
          @click="selectDivision(d)"
          class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
        >
          {{ d.label }}
          <span class="badge bg-primary rounded-pill">{{ d.count }}</span>
        </button>
      </div>
    </div>
  </div>
</template>