<template>
  <div style="max-width: 560px; margin: 0 auto">
    <h1 style="font-size: 34px; line-height: 1.1; letter-spacing: -0.03em; margin: 0 0 8px; text-align: center">
      Send a sheet of emails
    </h1>
    <p style="margin: 0 0 28px; text-align: center; font-size: 15px" :style="{ color: t.muted }">
      Upload your sheet, review the rows, then send or schedule.
    </p>

    <div :style="cardStyle">
      <label :style="dropzoneStyle">
        <input type="file" accept=".xlsx,.csv" style="display: none" @change="onPickSheet" />
        <div :style="dropzoneIconStyle">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M7 18a4.5 4.5 0 0 1-.5-9A6 6 0 0 1 18 9.5 4 4 0 0 1 17 18"></path>
            <path d="m12 12-3.5 3.5M12 12l3.5 3.5M12 12v9"></path>
          </svg>
        </div>
        <div style="font-weight: 600; font-size: 15px">{{ sheetName }}</div>
        <div style="font-size: 13px" :style="{ color: t.muted }">.xlsx or .csv, up to 10 MB</div>
      </label>

      <label :style="attachRowStyle">
        <input type="file" multiple style="display: none" @change="onPickAtt" />
        <span style="display: grid" :style="{ color: t.muted }">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m21 11-9 9a5 5 0 0 1-7-7l9-9a3.5 3.5 0 0 1 5 5l-9 9a2 2 0 0 1-3-3l8-8"></path>
          </svg>
        </span>
        <div style="flex: 1; font-size: 14px; font-weight: 500">{{ attName }}</div>
        <span style="font-size: 12px" :style="{ color: t.muted }">Optional</span>
      </label>

      <div v-if="errorMessage" :style="errorStyle">{{ errorMessage }}</div>

      <button :style="primaryStyle" :disabled="!sheetFile || loading" @click="submit">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 16V4M7 9l5-5 5 5M4 20h16"></path>
        </svg>
        {{ loading ? 'Uploading…' : 'Upload & Preview' }}
      </button>
    </div>

    <div style="margin-top: 24px; display: flex; flex-direction: column; gap: 10px; align-items: center; font-size: 13px" :style="{ color: t.muted }">
      <div style="display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; align-items: center">
        <span style="font-weight: 600" :style="{ color: t.ink }">Required</span>
        <span v-for="c in reqCols" :key="c" :style="pillStyle(false)">{{ c }}</span>
      </div>
      <div style="display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; align-items: center">
        <span style="font-weight: 600" :style="{ color: t.ink }">Optional</span>
        <span v-for="c in optCols" :key="c" :style="pillStyle(true)">{{ c }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from '../composables/useTheme'
import { primaryStyle as primaryStyleFn } from '../theme/mono'
import { uploadSheet } from '../api/client'

const router = useRouter()
const { t } = useTheme()

const sheetFile = ref(null)
const attachmentFiles = ref([])
const loading = ref(false)
const errorMessage = ref('')

const reqCols = ['To', 'From', 'Subject', 'Email Content']
const optCols = ['CC', 'Attachment', 'Date', 'Time']

const sheetName = computed(() => sheetFile.value?.name || 'Choose a sheet or drop it here')
const attName = computed(() =>
  attachmentFiles.value.length ? `${attachmentFiles.value.length} attachment${attachmentFiles.value.length > 1 ? 's' : ''}` : 'Add attachments'
)

const cardStyle = computed(
  () =>
    `background:${t.value.card};border:1px solid ${t.value.line};border-radius:${t.value.r};padding:28px;box-shadow:${t.value.shadow};display:flex;flex-direction:column;gap:20px`
)

const dropzoneStyle = computed(
  () =>
    `display:flex;flex-direction:column;align-items:center;gap:10px;padding:36px 20px;border:1.5px dashed ${t.value.dash};border-radius:${t.value.r2};background:${t.value.well};cursor:pointer;text-align:center`
)

const dropzoneIconStyle = computed(
  () =>
    `width:48px;height:48px;border-radius:50%;background:${t.value.card};box-shadow:${t.value.shadowSm};display:grid;place-items:center;color:${t.value.accent}`
)

const attachRowStyle = computed(
  () =>
    `display:flex;align-items:center;gap:12px;padding:12px 14px;border:1px solid ${t.value.line};border-radius:${t.value.r3};cursor:pointer;background:${t.value.card}`
)

const primaryStyle = computed(() => primaryStyleFn(t.value))

const errorStyle = computed(
  () =>
    `padding:10px 14px;border-radius:${t.value.r3};background:${t.value.fl[0]};color:${t.value.fl[1]};font-size:13px`
)

function pillStyle(optional) {
  return optional
    ? `font-family:'Geist Mono',monospace;font-size:12px;padding:3px 9px;border-radius:999px;border:1px dashed ${t.value.dash};color:${t.value.ink}`
    : `font-family:'Geist Mono',monospace;font-size:12px;padding:3px 9px;border-radius:999px;background:${t.value.card};border:1px solid ${t.value.line};color:${t.value.ink}`
}

function onPickSheet(e) {
  sheetFile.value = e.target.files[0] || null
}

function onPickAtt(e) {
  attachmentFiles.value = Array.from(e.target.files || [])
}

async function submit() {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await uploadSheet(sheetFile.value, attachmentFiles.value)
    router.push({ name: 'preview', params: { batchId: result.batch_id } })
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Upload failed. Check your sheet and try again.'
  } finally {
    loading.value = false
  }
}
</script>
