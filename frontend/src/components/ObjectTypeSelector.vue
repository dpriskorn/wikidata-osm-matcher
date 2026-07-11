<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getObjectTypes, type ObjectTypeInfo } from '../api'

const router = useRouter()
const types = ref<ObjectTypeInfo[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    types.value = await getObjectTypes()
  } catch (e) {
    error.value = 'Kunde inte ladda objekttyper'
  } finally {
    loading.value = false
  }
})

function selectType(type: ObjectTypeInfo) {
  router.push(`/${type.qid}`)
}
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h2 class="h5 mb-0">Välj objekttyp</h2>
    </div>
    <div class="card-body">
      <p v-if="loading" class="text-muted">Laddar...</p>
      <p v-if="error" class="text-danger">{{ error }}</p>
      <div v-else class="row g-3">
        <div v-for="t in types" :key="t.qid" class="col-md-4 col-lg-3">
          <button
            @click="selectType(t)"
            class="btn btn-outline-primary w-100 text-start"
          >
            {{ t.label }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>