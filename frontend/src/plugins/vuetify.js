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
          background: '#F8FAFC',
          surface: '#FFFFFF',
          primary: '#6366F1',
          secondary: '#64748B',
          error: '#EF4444',
          success: '#22C55E',
          warning: '#F59E0B'
        }
      }
    }
  },
  defaults: {
    VCard: { elevation: 0, rounded: 'xl', class: 'elevated-card' },
    VBtn: { elevation: 0, rounded: 'lg' },
    VAppBar: { elevation: 0, class: 'app-bar-shadow' }
  }
})
