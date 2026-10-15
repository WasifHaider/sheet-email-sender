# Theme

## Part 1 — Compact token summary

Styling system: **Vuetify 3 theme tokens** (not Tailwind, not plain CSS vars in a stylesheet — tokens are defined in JS and consumed via Vuetify's internal CSS variable layer, e.g. `rgb(var(--v-theme-primary))`).

Current theme name: `minimal` (light only, no dark mode defined).

| Token | Value | Usage |
|---|---|---|
| `background` | `#FAFAFA` | page background |
| `surface` | `#FFFFFF` | cards, app bar |
| `primary` | `#3B82F6` (blue-500) | primary buttons, links, active states |
| `secondary` | `#64748B` (slate-500) | muted text/status |
| `error` | `#EF4444` (red-500) | error alerts |
| `success` | `#22C55E` (green-500) | success status |
| `warning` | `#F59E0B` (amber-500) | warning/pending status |

**Component defaults** (global, set once in the Vuetify plugin):
- `VCard`: `elevation: 0` (flat, no shadow), `rounded: 'lg'`, `class: 'pa-2'`
- `VBtn`: `elevation: 0` (flat), `rounded: 'lg'`
- `VAppBar`: `elevation: 0` (flat, no shadow/border)

Typography: Vuetify defaults (Roboto-based type scale: `text-h5`, `text-subtitle-1`, `text-body-2`, etc. — no custom font loaded). Icons: `@mdi/font` (Material Design Icons) is installed but not yet used anywhere in markup.

**Overall current impression: deliberately flat/minimal** — zero elevation, no gradients, no icons in UI, single flat accent blue. This is the exact thing being redesigned — the user wants a more "Modern SaaS" feel (soft shadows/depth, bolder accent, icons, visual hierarchy) while keeping it clean, not going flashy/dark.

## Part 2 — Raw source dump

`frontend/src/plugins/vuetify.js` (full file):

```js
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'minimal',
    themes: {
      minimal: {
        dark: false,
        colors: {
          background: '#FAFAFA',
          surface: '#FFFFFF',
          primary: '#3B82F6',
          secondary: '#64748B',
          error: '#EF4444',
          success: '#22C55E',
          warning: '#F59E0B'
        }
      }
    }
  },
  defaults: {
    VCard: { elevation: 0, rounded: 'lg', class: 'pa-2' },
    VBtn: { elevation: 0, rounded: 'lg' },
    VAppBar: { elevation: 0 }
  }
})
```

No `tailwind.config`, no `globals.css`/`index.css` with custom variables exist in this project — Vuetify's own `vuetify/styles` import is the only global stylesheet.
