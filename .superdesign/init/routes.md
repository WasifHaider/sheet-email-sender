# Routes

Router: **vue-router 4**, config-based, history mode. Full config at `frontend/src/router/index.js`:

```js
import { createRouter, createWebHistory } from 'vue-router'
import UploadView from '../views/UploadView.vue'
import PreviewView from '../views/PreviewView.vue'

const routes = [
  { path: '/', redirect: '/upload' },
  { path: '/upload', name: 'upload', component: UploadView },
  { path: '/preview/:batchId', name: 'preview', component: PreviewView, props: true }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
```

| Path | Name | Component | Summary |
|---|---|---|---|
| `/` | — | redirect → `/upload` | |
| `/upload` | `upload` | `src/views/UploadView.vue` | File picker for the sheet + optional attachments, posts to backend, navigates to `/preview/:batchId` on success. |
| `/preview/:batchId` | `preview` | `src/views/PreviewView.vue` | Shows a data table of parsed rows for the batch; "Confirm & Queue" button triggers send/schedule and (will) navigate to `/status`. |

**Planned, not yet built:** `/status` (name: `status`) → `StatusView.vue` — table of all jobs across batches with status chips (pending_review/scheduled/queued/sent/failed) and a manual refresh button. This is the page currently being redesigned/built next.
