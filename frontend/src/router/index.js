import { createRouter, createWebHistory } from 'vue-router'
import UploadView from '../views/UploadView.vue'
import PreviewView from '../views/PreviewView.vue'
import StatusView from '../views/StatusView.vue'
import LoginView from '../views/LoginView.vue'
import { useAuth } from '../composables/useAuth'

const routes = [
  { path: '/', redirect: '/upload' },
  { path: '/login', name: 'login', component: LoginView },
  { path: '/upload', name: 'upload', component: UploadView },
  { path: '/preview/:batchId', name: 'preview', component: PreviewView, props: true },
  { path: '/status', name: 'status', component: StatusView }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  const { user, checked, checkAuth } = useAuth()
  if (!checked.value) {
    await checkAuth()
  }
  if (to.name !== 'login' && !user.value) {
    return { name: 'login' }
  }
  if (to.name === 'login' && user.value) {
    return { name: 'upload' }
  }
  return true
})

export default router
