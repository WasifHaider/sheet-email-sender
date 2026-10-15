<template>
  <v-container class="py-10" style="max-width: 960px">
    <div class="d-flex flex-column flex-md-row align-md-end justify-space-between mb-8" style="gap: 16px">
      <div>
        <h1 class="text-h4 font-weight-bold mb-1">Job status</h1>
        <p class="text-body-2 text-medium-emphasis">
          Track the delivery progress of every uploaded batch.
        </p>
      </div>
      <v-btn variant="outlined" color="secondary" :loading="loading" @click="load">
        <v-icon icon="mdi-refresh" size="18" class="mr-2" />
        Refresh
      </v-btn>
    </div>

    <v-row class="mb-8" dense>
      <v-col cols="6" md="3">
        <v-card class="pa-4">
          <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase mb-1">Sent</div>
          <div class="text-h5 font-weight-bold text-success">{{ counts.sent }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card class="pa-4">
          <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase mb-1">Scheduled</div>
          <div class="text-h5 font-weight-bold text-warning">{{ counts.scheduled }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card class="pa-4">
          <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase mb-1">Failed</div>
          <div class="text-h5 font-weight-bold text-error">{{ counts.failed }}</div>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card class="pa-4">
          <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase mb-1">Pending review</div>
          <div class="text-h5 font-weight-bold text-primary">{{ counts.pending_review }}</div>
        </v-card>
      </v-col>
    </v-row>

    <v-alert v-if="errorMessage" type="error" density="compact" class="mb-4">
      {{ errorMessage }}
    </v-alert>

    <v-card>
      <v-data-table :headers="headers" :items="jobs" :loading="loading" density="comfortable" hover>
        <template #item.status="{ item }">
          <v-chip size="small" :class="`status-chip-${item.status}`" variant="flat">
            <v-icon :icon="statusIcon(item.status)" size="14" class="mr-1" />
            {{ statusLabel(item.status) }}
          </v-chip>
        </template>
        <template #item.error_message="{ item }">
          <span v-if="item.error_message" class="text-error text-body-2">{{ item.error_message }}</span>
          <span v-else class="text-medium-emphasis">—</span>
        </template>
        <template #item.sent_at="{ item }">
          <span v-if="item.sent_at" class="text-body-2">{{ item.sent_at }}</span>
          <span v-else class="text-medium-emphasis">—</span>
        </template>
      </v-data-table>
    </v-card>
  </v-container>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { listJobs } from '../api/client'

const jobs = ref([])
const loading = ref(true)
const errorMessage = ref('')

const headers = [
  { title: 'To', key: 'to_email' },
  { title: 'Subject', key: 'subject' },
  { title: 'Status', key: 'status' },
  { title: 'Sent at', key: 'sent_at' },
  { title: 'Error', key: 'error_message' }
]

const statusMeta = {
  pending_review: { label: 'Pending review', icon: 'mdi-file-document-outline' },
  scheduled: { label: 'Scheduled', icon: 'mdi-clock-outline' },
  queued: { label: 'Queued', icon: 'mdi-clock-outline' },
  sent: { label: 'Sent', icon: 'mdi-check-circle' },
  failed: { label: 'Failed', icon: 'mdi-alert-circle' }
}

function statusLabel(status) {
  return statusMeta[status]?.label || status
}

function statusIcon(status) {
  return statusMeta[status]?.icon || 'mdi-help-circle-outline'
}

const counts = computed(() => {
  const result = { sent: 0, scheduled: 0, failed: 0, pending_review: 0 }
  for (const job of jobs.value) {
    if (job.status === 'sent') result.sent += 1
    else if (job.status === 'scheduled' || job.status === 'queued') result.scheduled += 1
    else if (job.status === 'failed') result.failed += 1
    else if (job.status === 'pending_review') result.pending_review += 1
  }
  return result
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
