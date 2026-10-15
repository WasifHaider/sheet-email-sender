<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; margin-bottom: 20px">
      <div>
        <h1 style="font-size: 30px; letter-spacing: -0.03em; margin: 0 0 6px">Preview</h1>
        <div style="display: flex; align-items: center; gap: 8px; font-size: 14px" :style="{ color: t.muted }">
          <span :style="countPillStyle">{{ rows.length }} rows</span> parsed from your sheet
        </div>
      </div>
      <div style="display: flex; gap: 10px">
        <button :style="secondaryStyle" @click="router.push({ name: 'upload' })">Back</button>
        <button :style="primaryStyle" :disabled="rows.length === 0 || confirming" @click="confirm">
          {{ confirming ? 'Queuing…' : 'Confirm & Queue Batch' }}
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 12h14M13 6l6 6-6 6"></path>
          </svg>
        </button>
      </div>
    </div>

    <div v-if="errorMessage" :style="errorStyle" class="mb-4">{{ errorMessage }}</div>

    <div :style="tableWrapStyle">
      <div style="min-width: 820px">
        <div :style="headerRowStyle">
          <span>To</span><span>Subject</span><span>Content</span><span>Schedule</span><span>Attachment</span>
        </div>
        <div v-if="loading" style="padding: 24px; text-align: center" :style="{ color: t.muted }">Loading…</div>
        <div v-for="row in rows" :key="row.id" :style="bodyRowStyle">
          <span style="font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ row.to_email }}</span>
          <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ row.subject }}</span>
          <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap" :style="{ color: t.muted }">{{ truncate(row.content) }}</span>
          <span style="display: flex; align-items: center; gap: 6px; font-size: 13px; font-family: 'Geist Mono', monospace" :style="{ color: t.muted }">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <circle cx="12" cy="12" r="9"></circle>
              <path d="M12 7v5l3 2"></path>
            </svg>
            {{ schedule(row) }}
          </span>
          <span style="display: flex; align-items: center; gap: 6px; font-size: 13px" :style="{ color: t.muted }">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="m21 11-9 9a5 5 0 0 1-7-7l9-9a3.5 3.5 0 0 1 5 5l-9 9a2 2 0 0 1-3-3l8-8"></path>
            </svg>
            {{ row.attachment_filename || '—' }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from '../composables/useTheme'
import { primaryStyle as primaryStyleFn, secondaryStyle as secondaryStyleFn } from '../theme/mono'
import { confirmBatch, getBatch } from '../api/client'

const props = defineProps({ batchId: { type: String, required: true } })
const router = useRouter()
const { t } = useTheme()

const rows = ref([])
const loading = ref(true)
const confirming = ref(false)
const errorMessage = ref('')

const primaryStyle = computed(() => primaryStyleFn(t.value))
const secondaryStyle = computed(() => secondaryStyleFn(t.value))

const countPillStyle = computed(
  () =>
    `padding:3px 10px;border-radius:999px;background:${t.value.chipBg};border:1px solid ${t.value.line};color:${t.value.ink};font-weight:600;font-size:12px`
)

const errorStyle = computed(
  () => `padding:10px 14px;border-radius:${t.value.r3};background:${t.value.fl[0]};color:${t.value.fl[1]};font-size:13px;margin-bottom:16px`
)

const tableWrapStyle = computed(
  () => `background:${t.value.card};border:1px solid ${t.value.line};border-radius:${t.value.r};box-shadow:${t.value.shadow};overflow-x:auto`
)

const headerRowStyle = computed(
  () =>
    `display:grid;grid-template-columns:1.4fr 1.3fr 2fr 1.2fr 1.1fr;gap:16px;padding:12px 20px;font-size:12px;font-weight:600;color:${t.value.muted};text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid ${t.value.line};background:${t.value.well};border-radius:${t.value.r} ${t.value.r} 0 0`
)

const bodyRowStyle = computed(
  () => `display:grid;grid-template-columns:1.4fr 1.3fr 2fr 1.2fr 1.1fr;gap:16px;padding:14px 20px;font-size:14px;align-items:center;border-bottom:1px solid ${t.value.line}`
)

function truncate(text) {
  if (!text) return ''
  return text.length > 60 ? `${text.slice(0, 60)}…` : text
}

function schedule(row) {
  if (!row.send_date) return 'Now'
  return row.send_time ? `${row.send_date} · ${row.send_time}` : row.send_date
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const data = await getBatch(props.batchId)
    rows.value = data.rows
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Could not load this batch.'
  } finally {
    loading.value = false
  }
}

async function confirm() {
  confirming.value = true
  errorMessage.value = ''
  try {
    await confirmBatch(props.batchId)
    router.push({ name: 'status' })
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Could not confirm this batch.'
  } finally {
    confirming.value = false
  }
}

onMounted(load)
</script>
