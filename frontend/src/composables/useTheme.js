import { computed, ref } from 'vue'
import { DARK, LIGHT } from '../theme/mono'

const STORAGE_KEY = 'ses-mode'

function readStoredMode() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === 'dark' ? 'dark' : 'light'
  } catch {
    return 'light'
  }
}

const mode = ref(readStoredMode())

function toggle() {
  mode.value = mode.value === 'light' ? 'dark' : 'light'
  try {
    localStorage.setItem(STORAGE_KEY, mode.value)
  } catch {
    // ignore storage errors (private browsing, etc.)
  }
}

const t = computed(() => (mode.value === 'dark' ? DARK : LIGHT))

export function useTheme() {
  return { mode, toggle, t }
}
