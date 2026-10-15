<template>
  <div :style="rootStyle">
    <nav :style="navStyle">
      <div style="display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 16px; letter-spacing: -0.01em">
        <div :style="logoStyle">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="5" width="18" height="14" rx="2"></rect>
            <path d="m3 7 9 6 9-6"></path>
          </svg>
        </div>
        Sheet Email Sender
      </div>
      <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap">
        <button :style="toggleStyle" @click="toggle" :aria-label="mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'">
          <svg v-if="mode === 'dark'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="5"></circle>
            <path d="M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"></path>
          </svg>
          <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
          </svg>
        </button>
        <span v-if="user" style="font-size: 13px" :style="{ color: t.muted }">{{ user.email }}</span>
        <button v-if="user" :style="toggleStyle" @click="handleLogout" aria-label="Log out">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"></path>
          </svg>
        </button>
        <div v-if="user" style="display: flex; gap: 4px">
          <router-link :to="{ name: 'upload' }" :style="navLinkStyle(route.name !== 'status')">Upload</router-link>
          <router-link :to="{ name: 'status' }" :style="navLinkStyle(route.name === 'status')">Status</router-link>
        </div>
      </div>
    </nav>

    <div style="max-width: 1080px; margin: 0 auto; padding: 48px 32px 80px">
      <div v-if="user" style="display: flex; align-items: center; gap: 10px; margin-bottom: 32px; font-size: 13px" :style="{ color: t.muted }">
        <span :style="stepStyle(route.name === 'upload')">1 Upload</span><span>—</span>
        <span :style="stepStyle(route.name === 'preview')">2 Preview</span><span>—</span>
        <span :style="stepStyle(route.name === 'status')">3 Status</span>
      </div>

      <router-view />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTheme } from './composables/useTheme'
import { useAuth } from './composables/useAuth'
import { navLinkStyle as navLinkStyleFn, stepStyle as stepStyleFn } from './theme/mono'

const route = useRoute()
const router = useRouter()
const { mode, toggle, t } = useTheme()
const { user, logout } = useAuth()

async function handleLogout() {
  await logout()
  router.push({ name: 'login' })
}

const rootStyle = computed(() => ({
  minHeight: '100vh',
  background: t.value.bg,
  color: t.value.ink,
  fontFamily: "'Geist', system-ui, sans-serif",
  transition: 'background .3s'
}))

const navStyle = computed(
  () =>
    `position:sticky;top:0;z-index:5;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;padding:14px 32px;background:${t.value.nav};backdrop-filter:blur(12px);border-bottom:1px solid ${t.value.line}`
)

const logoStyle = computed(
  () =>
    `width:30px;height:30px;border-radius:${t.value.logoR};background:${t.value.btn};display:grid;place-items:center;color:${t.value.btnInk};box-shadow:${t.value.btnShadow}`
)

const toggleStyle = computed(
  () =>
    `display:grid;place-items:center;width:30px;height:30px;border-radius:999px;border:1px solid ${t.value.line};background:${t.value.card};color:${t.value.ink};cursor:pointer`
)

function navLinkStyle(active) {
  return navLinkStyleFn(active, t.value)
}

function stepStyle(active) {
  return stepStyleFn(active, t.value)
}
</script>
