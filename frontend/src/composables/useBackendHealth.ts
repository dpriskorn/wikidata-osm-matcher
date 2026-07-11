import { ref, onMounted, onUnmounted } from 'vue'

const isBackendDown = ref(false)
let checkInterval: ReturnType<typeof setInterval> | null = null

export function useBackendHealth() {
  async function checkHealth() {
    try {
      const res = await fetch('/health', {
        signal: AbortSignal.timeout(3000),
      })
      isBackendDown.value = !res.ok
    } catch {
      isBackendDown.value = true
    }
  }

  function startPolling() {
    checkHealth()
    checkInterval = setInterval(checkHealth, 30000)
  }

  function stopPolling() {
    if (checkInterval) {
      clearInterval(checkInterval)
      checkInterval = null
    }
  }

  return {
    isBackendDown,
    checkHealth,
    startPolling,
    stopPolling,
  }
}
