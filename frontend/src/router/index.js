import { createRouter, createWebHistory } from 'vue-router'
import UploadView from '../views/UploadView.vue'

const routes = [
  { path: '/', redirect: '/upload' },
  { path: '/upload', name: 'upload', component: UploadView }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
