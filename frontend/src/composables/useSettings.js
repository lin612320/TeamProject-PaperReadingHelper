import { ref, watch } from 'vue'

const STORAGE_KEY = 'papermind:ai-settings'

const defaults = {
  apiKey: '',
  baseUrl: 'https://api.deepseek.com',
  model: 'deepseek-chat',
}

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...defaults }
    const parsed = JSON.parse(raw)
    return {
      apiKey: parsed.apiKey || '',
      baseUrl: parsed.baseUrl || defaults.baseUrl,
      model: parsed.model || defaults.model,
    }
  } catch {
    return { ...defaults }
  }
}

const settings = ref(load())

watch(
  settings,
  (value) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
  },
  { deep: true }
)

export function useSettings() {
  function updateSettings(patch) {
    settings.value = { ...settings.value, ...patch }
  }

  function resetSettings() {
    settings.value = { ...defaults }
  }

  function isConfigured() {
    return settings.value.apiKey.trim().length > 0
  }

  return { settings, updateSettings, resetSettings, isConfigured }
}