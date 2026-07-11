<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getCountries, type CountryInfo } from '../api'

const props = defineProps<{
  typeQid: string
}>()

const router = useRouter()
const countries = ref<CountryInfo[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    countries.value = await getCountries(props.typeQid)
  } catch (e) {
    error.value = 'Kunde inte ladda länder'
  } finally {
    loading.value = false
  }
})

function selectCountry(country: CountryInfo) {
  router.push(`/${props.typeQid}/${country.qid}`)
}
</script>

<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <h2 class="h5 mb-0">Välj land</h2>
      <button @click="router.push('/')" class="btn btn-sm btn-outline-secondary">← Tillbaka</button>
    </div>
    <div class="card-body">
      <p v-if="loading" class="text-muted">Laddar...</p>
      <p v-if="error" class="text-danger">{{ error }}</p>
      <p v-else-if="countries.length === 0" class="text-muted">Inga länder med kandidater hittades.</p>
      <div v-else class="list-group">
        <button
          v-for="c in countries"
          :key="c.qid"
          @click="selectCountry(c)"
          class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
        >
          {{ c.label }}
          <span class="badge bg-primary rounded-pill">{{ c.count }}</span>
        </button>
      </div>
    </div>
  </div>
</template>