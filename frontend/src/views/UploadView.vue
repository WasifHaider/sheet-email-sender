<template>
  <v-container class="py-12" style="max-width: 480px">
    <div class="mb-8">
      <h1 class="text-h4 font-weight-bold mb-2">Upload a sheet</h1>
      <p class="text-body-2 text-medium-emphasis">
        Import your spreadsheet to start sending emails. Supports .xlsx and .csv formats.
      </p>
    </div>

    <v-card class="pa-8">
      <div class="dropzone-hint d-flex flex-column align-center justify-center py-6 mb-6">
        <v-icon icon="mdi-cloud-upload-outline" color="primary" size="36" class="mb-2" />
        <span class="text-body-2 font-weight-medium text-primary">Select your files below</span>
      </div>

      <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase mb-1">
        Sheet data
      </div>
      <v-file-input
        v-model="sheetFile"
        prepend-icon=""
        prepend-inner-icon="mdi-file-table-outline"
        placeholder="Select sheet..."
        accept=".xlsx,.csv"
        density="comfortable"
        variant="outlined"
        bg-color="background"
      />

      <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase mb-1">
        Attachments (optional)
      </div>
      <v-file-input
        v-model="attachmentFiles"
        prepend-icon=""
        prepend-inner-icon="mdi-paperclip"
        placeholder="Select files..."
        multiple
        density="comfortable"
        variant="outlined"
        bg-color="background"
        class="mb-4"
      />

      <v-alert v-if="errorMessage" type="error" density="compact" class="mb-4">
        {{ errorMessage }}
      </v-alert>

      <v-btn
        block
        height="44"
        class="gradient-btn"
        :loading="loading"
        :disabled="!sheetFile"
        @click="submit"
      >
        <v-icon icon="mdi-upload" size="18" class="mr-2" />
        Upload & Preview
      </v-btn>
    </v-card>

    <v-card class="mt-6 pa-4 d-flex" variant="outlined">
      <v-icon icon="mdi-information-outline" color="primary" size="18" class="mr-3 mt-1" />
      <p class="text-caption text-medium-emphasis">
        Required columns: <span class="font-weight-medium text-high-emphasis">To, From, Subject, Email Content</span>.
        Optional: <span class="font-weight-medium text-high-emphasis">CC, Attachment, Date, Time</span>.
      </p>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { uploadSheet } from '../api/client'

const router = useRouter()
const sheetFile = ref(null)
const attachmentFiles = ref([])
const loading = ref(false)
const errorMessage = ref('')

async function submit() {
  loading.value = true
  errorMessage.value = ''
  try {
    const file = Array.isArray(sheetFile.value) ? sheetFile.value[0] : sheetFile.value
    const result = await uploadSheet(file, attachmentFiles.value || [])
    router.push({ name: 'preview', params: { batchId: result.batch_id } })
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Upload failed. Check your sheet and try again.'
  } finally {
    loading.value = false
  }
}
</script>
