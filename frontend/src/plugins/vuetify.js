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
