# Design System — Sheet Email Sender

## Product context
Small internal tool: upload an Excel/CSV sheet of emails → preview parsed rows → confirm → send/schedule via SMTP → track status. Single user, no auth, no multi-tenant complexity. Audience is the one person running it, not a public product — but the user wants it to feel like a polished modern SaaS dashboard, not a bare internal tool.

Three screens total: **Upload** (file picker), **Preview** (data table + confirm action), **Status** (data table of all jobs with status chips, not yet built). A shared top app bar wraps every screen.

## Visual direction: Modern SaaS
Moving away from the current flat/zero-elevation look toward something with depth and visual hierarchy — think Linear/Stripe dashboard feel. Still clean and uncluttered, not flashy or dark. Concretely:
- Soft shadow elevation on cards (not flat `elevation: 0` anymore)
- Richer accent color with a gradient treatment on primary actions, instead of a single flat blue
- Bolder, clearer type hierarchy between heading/subtext/body
- Icons used throughout (file/mail/upload/clock/check/alert) — currently zero icons are used despite `@mdi/font` already being installed
- Rounded corners stay generous (`lg`/`xl`) — that part of the current look is kept
- Status is communicated with icon + color together, not color alone

## Color
Base palette evolves from the current flat tokens, not a wholesale replacement:
- Background: `#F8FAFC` (very light slate, slightly cooler than the current `#FAFAFA`)
- Surface (cards): `#FFFFFF`
- Primary: `#6366F1` (indigo-500) — was `#3B82F6` flat blue; primary actions use a subtle gradient from `#6366F1` to `#8B5CF6` (indigo → violet)
- Secondary / muted text: `#64748B` (unchanged — slate-500)
- Success: `#22C55E` (unchanged — green-500) — used for "sent" status
- Warning: `#F59E0B` (unchanged — amber-500) — used for "scheduled"/"queued" status
- Error: `#EF4444` (unchanged — red-500) — used for "failed" status and form errors

## Typography
Vuetify/Roboto default type scale is kept (no new font load — stay lightweight). Hierarchy becomes more deliberate:
- Page titles: `text-h4` or `text-h5`, heavier weight (`font-weight-bold`/`700`) — was `font-weight-medium`
- Subtext: `text-body-2`, muted color, kept as-is
- Table/body text: default weight, no change

## Elevation & shape
- Cards: soft shadow (`elevation: 2` to `4`, or a custom subtle `box-shadow` — not flat `0` anymore), `rounded: 'xl'`
- Buttons: primary buttons get the gradient fill; keep `rounded: 'lg'`
- App bar: very subtle bottom shadow/border instead of fully flat, so it reads as a distinct layer above the page content

## Icons
`@mdi/font` (Material Design Icons) is already installed — use it everywhere relevant:
- Upload screen: large cloud-upload icon in/above the empty-state card
- File inputs: file icon (Vuetify's `v-file-input` already shows one by default — keep it, style consistently)
- Status chips: `mdi-check-circle` (sent), `mdi-clock-outline` (scheduled/queued), `mdi-alert-circle` (failed), `mdi-file-document-outline` (pending_review)
- Buttons: leading icon on primary actions where it clarifies intent (e.g. upload icon on the Upload button, send icon on Confirm & Queue)

## Motion
Keep minimal — this is a utility tool, not a marketing site. Vuetify's built-in transitions (button ripple, table row hover) are sufficient. No custom animation library, no page-transition choreography.

## Layout structure
- Single-column, centered, max-width containers (480px for Upload's form, 960px for Preview/Status tables) — unchanged from current structure, it already works well for this content
- Top app bar persists across all screens with nav links (Upload, Status)

## Specific constraints
- Vue 3 + Vuetify 3 only — no new UI library, no Tailwind, no custom CSS framework
- Keep the app lightweight: no new npm dependencies beyond what's already installed (`@mdi/font` covers icons)
- This is a redesign of the *visual layer only* — no change to data flow, routes, or component logic
