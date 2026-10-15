# Pages

## /upload (Upload Page)
Entry: `frontend/src/views/UploadView.vue`
Dependencies:
- `frontend/src/api/client.js` (`uploadSheet`)
- `frontend/src/App.vue` (shell, always wraps every page)
- `frontend/src/plugins/vuetify.js` (theme/components, global)

Renders: page heading + subtext, one `v-card` containing two `v-file-input`s (sheet, attachments), an error `v-alert` (conditional), and a full-width "Upload" `v-btn`. On successful upload, navigates to `/preview/:batchId`.

## /preview/:batchId (Preview Page)
Entry: `frontend/src/views/PreviewView.vue`
Dependencies:
- `frontend/src/api/client.js` (`getBatch`, `confirmBatch`)
- `frontend/src/App.vue` (shell)
- `frontend/src/plugins/vuetify.js` (theme/components, global)

Renders: page heading + subtext, one `v-card` containing a `v-data-table` of parsed rows (To, Subject, Content, Date, Time, Attachment), an error `v-alert` (conditional), and a right-aligned "Confirm & Queue" `v-btn`. On confirm, navigates to `/status` (route not yet built).

## /status (Status Page) — NOT YET BUILT
Planned entry: `frontend/src/views/StatusView.vue` (does not exist yet)
Will depend on: `frontend/src/api/client.js` (`listJobs`), `App.vue`, `vuetify.js`.

Per the implementation plan: a `v-data-table` of all jobs across batches (To, Subject, Status, Sent at, Error), with the Status column rendered as color-coded `v-chip`s (pending_review/scheduled/queued → secondary/warning, sent → success, failed → error), plus a manual "Refresh" button in the page header. This is the page the current redesign work is building toward — it should match whatever new visual language is chosen for Upload/Preview.
