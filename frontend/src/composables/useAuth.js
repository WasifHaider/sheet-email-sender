import { ref } from 'vue'
import client from '../api/client'

const user = ref(null)
const checked = ref(false)

async function checkAuth() {
  try {
    const response = await client.get('/auth/me')
    user.value = response.data
  } catch {
    user.value = null
  } finally {
    checked.value = true
  }
}

async function logout() {
  await client.post('/auth/logout')
  user.value = null
}

export function useAuth() {
  return { user, checked, checkAuth, logout }
}
