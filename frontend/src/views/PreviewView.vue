<template>
  <v-container class="py-12" style="max-width: 960px">
    <div class="d-flex flex-column flex-md-row align-md-end justify-space-between mb-8" style="gap: 16px">
      <div style="max-width: 560px">
        <h1 class="text-h4 font-weight-bold mb-2">Preview emails</h1>
        <p class="text-body-2 text-medium-emphasis">
          Review the parsed rows below. If you notice an error, re-upload your sheet. Emails will be processed
          exactly as shown.
        </p>
      </div>
      <div class="stat-chip d-flex align-center px-3 py-2">
        <v-icon icon="mdi-table" color="primary" size="18" class="mr-2" />
        <span class="text-caption font-weight-bold text-primary">{{ rows.length }} rows parsed</span>
      </div>
    </div>

    <v-card>
      <v-data-table :headers="headers" :items="rows" :loading="loading" density="comfortable" hover>
        <template #item.content="{ item }">
          <span class="text-medium-emphasis font-italic">{{ truncate(item.content) }}</span>
        </template>
        <template #header.send_date="{ column }">
          <v-icon icon="mdi-clock-outline" size="14" class="mr-1" />{{ column.title }}
        </template>
        <template #item.send_date="{ item }">
          <span v-if="item.send_date" class="text-caption text-medium-emphasis">{{ item.send_date }}</span>
          <span v-if="item.send_time" class="text-caption font-weight-bold text-medium-emphasis ml-1">{{ item.send_time }}</span>
          <span v-if="!item.send_date && !item.send_time" class="text-caption text-medium-emphasis">Immediate</span>
        </template>
        <template #header.attachment_filename="{ column }">
          <v-icon icon="mdi-paperclip" size="14" class="mr-1" />{{ column.title }}
        </template>
        <template #item.attachment_filename="{ item }">
          <v-chip v-if="item.attachment_filename" size="small" color="primary" variant="tonal">
            {{ item.attachment_filename }}
          </v-chip>
          <span v-else class="text-medium-emphasis">—</span>
        </template>
      </v-data-table>

      <v-alert v-if="errorMessage" type="error" density="compact" class="ma-4">
        {{ errorMessage }}
      </v-alert>

      <v-divider />
      <div class="d-flex flex-column flex-sm-row align-sm-center justify-space-between pa-6" style="gap: 16px">
        <div class="d-flex align-center text-caption text-medium-emphasis">
          <v-icon icon="mdi-alert-circle" color="warning" size="18" class="mr-2" />
          Double check all addresses before sending
        </div>
        <v-btn class="gradient-btn" :loading="confirming" :disabled="rows.length === 0" @click="confirm">
          <v-icon icon="mdi-send" size="18" class="mr-2" />
          Confirm & Queue Batch
        </v-btn>
      </div>
    </v-card>

    <div class="d-flex justify-center mt-8">
      <v-btn variant="text" color="secondary" :to="{ name: 'upload' }">
        <v-icon icon="mdi-chevron-left" size="18" class="mr-1" />
        Back to Upload
      </v-btn>
    </div>
  </v-container>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { confirmBatch, getBatch } from '../api/client'

const props = defineProps({ batchId: { type: String, required: true } })
const router = useRouter()

const rows = ref([])
const loading = ref(true)
const confirming = ref(false)
const errorMessage = ref('')

const headers = [
  { title: 'To', key: 'to_email' },
  { title: 'Subject', key: 'subject' },
  { title: 'Content', key: 'content' },
  { title: 'Schedule', key: 'send_date' },
  { title: 'Attachment', key: 'attachment_filename' }
]

function truncate(text) {
  if (!text) return ''
  return text.length > 60 ? `${text.slice(0, 60)}…` : text
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
