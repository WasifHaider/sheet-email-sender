<template>
  <v-container class="py-10" style="max-width: 960px">
    <h1 class="text-h5 font-weight-medium mb-1">Preview</h1>
    <p class="text-body-2 text-medium-emphasis mb-6">
      Review the parsed rows below. To fix a mistake, re-upload the sheet instead of editing here.
    </p>

    <v-card class="pa-4">
      <v-data-table :headers="headers" :items="rows" :loading="loading" density="comfortable">
        <template #item.content="{ item }">
          {{ truncate(item.content) }}
        </template>
      </v-data-table>

      <v-alert v-if="errorMessage" type="error" density="compact" class="mt-4">
        {{ errorMessage }}
      </v-alert>

      <div class="d-flex justify-end mt-4">
        <v-btn color="primary" :loading="confirming" :disabled="rows.length === 0" @click="confirm">
          Confirm & Queue
        </v-btn>
      </div>
    </v-card>
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
  { title: 'Date', key: 'send_date' },
  { title: 'Time', key: 'send_time' },
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
