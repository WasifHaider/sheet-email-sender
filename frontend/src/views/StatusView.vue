<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; margin-bottom: 20px">
      <div>
        <h1 style="font-size: 30px; letter-spacing: -0.03em; margin: 0 0 6px">Status</h1>
        <div style="font-size: 14px" :style="{ color: t.muted }">Delivery across all queued jobs</div>
      </div>
      <button :style="secondaryStyle" @click="load">
        <svg
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.2"
          stroke-linecap="round"
          stroke-linejoin="round"
          :class="{ spin: loading }"
        >
          <path d="M20 11a8 8 0 0 0-14-4L4 9M4 4v5h5M4 13a8 8 0 0 0 14 4l2-2M20 20v-5h-5"></path>
        </svg>
        Refresh
      </button>
    </div>

    <div v-if="errorMessage" :style="errorStyle">{{ errorMessage }}</div>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px">
      <div v-for="stat in stats" :key="stat.key" :style="statCardStyle">
        <div>
          <div style="font-size: 13px; font-weight: 500; margin-bottom: 6px" :style="{ color: t.muted }">{{ stat.label }}</div>
          <div style="font-size: 34px; font-weight: 700; letter-spacing: -0.03em; line-height: 1">{{ stat.n }}</div>
        </div>
        <div :style="statIconStyle(stat.key)">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path :d="ICON[stat.key][0]"></path>
            <path :d="ICON[stat.key][1]"></path>
          </svg>
        </div>
      </div>
    </div>

    <div :style="tableWrapStyle">
      <div style="min-width: 760px">
        <div :style="headerRowStyle">
          <span>Job</span><span>Recipient</span><span>Subject</span><span>Time</span><span>Status</span>
        </div>
        <div v-if="loading" style="padding: 24px; text-align: center" :style="{ color: t.muted }">Loading…</div>
        <div v-for="job in jobs" :key="job.id" :style="bodyRowStyle">
          <span style="font-family: 'Geist Mono', monospace; font-size: 12px" :style="{ color: t.muted }">#{{ job.id.slice(0, 4) }}</span>
          <span style="font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ job.to_email }}</span>
          <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap" :style="{ color: t.muted }">{{ job.subject }}</span>
          <span style="font-family: 'Geist Mono', monospace; font-size: 13px" :style="{ color: t.muted }">{{ job.sent_at || job.send_date || '—' }}</span>
          <span>
            <span :style="chipStyle(statusKey(job.status))">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path :d="ICON[statusKey(job.status)][0]"></path>
                <path :d="ICON[statusKey(job.status)][1]"></path>
              </svg>
              {{ statusLabel(job.status) }}
            </span>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useTheme } from '../composables/useTheme'
import {
  ICON,
  chipStyle as chipStyleFn,
  secondaryStyle as secondaryStyleFn,
  statIconStyle as statIconStyleFn
} from '../theme/mono'
import { listJobs } from '../api/client'

const { t } = useTheme()

const jobs = ref([])
const loading = ref(true)
const errorMessage = ref('')

const secondaryStyle = computed(() => secondaryStyleFn(t.value))

const errorStyle = computed(
  () => `padding:10px 14px;border-radius:${t.value.r3};background:${t.value.fl[0]};color:${t.value.fl[1]};font-size:13px;margin-bottom:16px`
)

const statCardStyle = computed(
  () =>
    `background:${t.value.card};border:1px solid ${t.value.line};border-radius:${t.value.r2};padding:18px 20px;box-shadow:${t.value.shadow};display:flex;justify-content:space-between;align-items:center`
)

const tableWrapStyle = computed(
  () => `background:${t.value.card};border:1px solid ${t.value.line};border-radius:${t.value.r};box-shadow:${t.value.shadow};overflow-x:auto`
)

const headerRowStyle = computed(
  () =>
    `display:grid;grid-template-columns:60px 1.5fr 1.5fr 1.2fr 1fr;gap:16px;padding:12px 20px;font-size:12px;font-weight:600;color:${t.value.muted};text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid ${t.value.line};background:${t.value.well};border-radius:${t.value.r} ${t.value.r} 0 0`
)

const bodyRowStyle = computed(
  () => `display:grid;grid-template-columns:60px 1.5fr 1.5fr 1.2fr 1fr;gap:16px;padding:14px 20px;font-size:14px;align-items:center;border-bottom:1px solid ${t.value.line}`
)

function statIconStyle(key) {
  return statIconStyleFn(key, t.value)
}

function chipStyle(key) {
  return chipStyleFn(key, t.value)
}

function statusKey(status) {
  if (status === 'sent') return 'sent'
  if (status === 'scheduled' || status === 'queued') return 'scheduled'
  if (status === 'failed') return 'failed'
  return 'pending'
}

function statusLabel(status) {
  const key = statusKey(status)
  return key.charAt(0).toUpperCase() + key.slice(1)
}

const stats = computed(() => {
  const counts = { sent: 0, scheduled: 0, failed: 0, pending: 0 }
  for (const job of jobs.value) counts[statusKey(job.status)] += 1
  return [
    { key: 'sent', label: 'Sent', n: counts.sent },
    { key: 'scheduled', label: 'Scheduled', n: counts.scheduled },
    { key: 'failed', label: 'Failed', n: counts.failed },
    { key: 'pending', label: 'Pending', n: counts.pending }
  ]
})

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const data = await listJobs()
    jobs.value = data.jobs
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Could not load job status.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
