import { createRouter, createWebHistory } from 'vue-router'
import UploadView from '../views/UploadView.vue'
import PreviewView from '../views/PreviewView.vue'
import StatusView from '../views/StatusView.vue'

const routes = [
  { path: '/', redirect: '/upload' },
  { path: '/upload', name: 'upload', component: UploadView },
  { path: '/preview/:batchId', name: 'preview', component: PreviewView, props: true },
  { path: '/status', name: 'status', component: StatusView }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
