# Extractable Components

No components are currently extracted into their own files — `App.vue`, `UploadView.vue`, and `PreviewView.vue` each inline their own markup directly using raw Vuetify primitives. The items below are candidates worth extracting as the redesign happens, since the same patterns will repeat once `StatusView.vue` is added.

## Layout Components (appear on most pages)

### AppBar (currently inline in `App.vue`)
- Source: `frontend/src/App.vue` (not yet a separate file)
- Category: layout
- Description: Top app bar with app title, spacer, nav link(s)
- Extractable props: none yet — nav links are hardcoded (`Upload`); will need an `Upload`/`Status` active-state indicator once `/status` exists
- Hardcoded: app title text "Sheet Email Sender", nav link labels

## Basic Components (used across pages / will repeat on Status page)

### PageHeader (pattern repeated in both views: `h1` + subtext paragraph)
- Source: inline in `UploadView.vue` and `PreviewView.vue` (not extracted)
- Category: basic
- Description: Page title (`text-h5 font-weight-medium`) + muted subtext paragraph (`text-body-2 text-medium-emphasis`)
- Extractable props: `title` (string), `subtitle` (string)
- Hardcoded: none — fully data-driven if extracted

### ErrorAlert (pattern repeated in both views: conditional `v-alert type="error"`)
- Source: inline in `UploadView.vue` and `PreviewView.vue`
- Category: basic
- Description: Compact error alert shown when an API call fails
- Extractable props: `message` (string)
- Hardcoded: `type="error"`, `density="compact"`

### StatusChip (needed for the upcoming Status page, doesn't exist yet)
- Source: not yet created — would live at `frontend/src/components/StatusChip.vue`
- Category: basic
- Description: Color/icon-coded chip for a job's status (pending_review, scheduled, queued, sent, failed)
- Extractable props: `status` (string)
- Hardcoded: the status→color/icon mapping
