import axios from 'axios'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const client = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true
})

export function uploadSheet(sheetFile, attachmentFiles) {
  const form = new FormData()
  form.append('sheet', sheetFile)
  for (const file of attachmentFiles) {
    form.append('attachments', file)
  }
  return client.post('/upload', form).then((res) => res.data)
}

export function getBatch(batchId) {
  return client.get(`/batches/${batchId}`).then((res) => res.data)
}

export function confirmBatch(batchId) {
  return client.post(`/batches/${batchId}/confirm`).then((res) => res.data)
}

export function listJobs(params = {}) {
  return client.get('/jobs', { params }).then((res) => res.data)
}

export default client
