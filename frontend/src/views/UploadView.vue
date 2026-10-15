<template>
  <v-container class="py-10" style="max-width: 480px">
    <h1 class="text-h5 font-weight-medium mb-1">Upload a sheet</h1>
    <p class="text-body-2 text-medium-emphasis mb-6">
      Columns: To, From, Subject, Email Content, CC, Attachment, Date, Time.
    </p>

    <v-card class="pa-6">
      <v-file-input
        v-model="sheetFile"
        label="Sheet (.xlsx or .csv)"
        accept=".xlsx,.csv"
        density="comfortable"
        variant="outlined"
      />
      <v-file-input
        v-model="attachmentFiles"
        label="Attachments (optional)"
        multiple
        density="comfortable"
        variant="outlined"
      />

      <v-alert v-if="errorMessage" type="error" density="compact" class="mb-4">
        {{ errorMessage }}
      </v-alert>

      <v-btn
        color="primary"
        block
        :loading="loading"
        :disabled="!sheetFile"
        @click="submit"
      >
        Upload
      </v-btn>
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
