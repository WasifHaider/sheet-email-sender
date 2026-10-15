<template>
  <div style="min-height: 100vh; display: flex; align-items: center; justify-content: center">
    <div :style="cardStyle">
      <h1 style="font-size: 1.5rem; font-weight: 700; margin: 0 0 8px; text-align: center">
        Sheet Email Sender
      </h1>
      <p style="font-size: 14px; text-align: center; margin: 0 0 24px" :style="{ color: t.muted }">
        Sign in to upload sheets and send email from your own Gmail.
      </p>
      <button :style="buttonStyle" @click="signIn">
        <svg width="18" height="18" viewBox="0 0 24 24">
          <path fill="#4285F4" d="M23.52 12.27c0-.85-.07-1.66-.21-2.45H12v4.64h6.47a5.53 5.53 0 0 1-2.4 3.63v3h3.87c2.27-2.09 3.58-5.17 3.58-8.82z" />
          <path fill="#34A853" d="M12 24c3.24 0 5.96-1.07 7.94-2.91l-3.87-3c-1.08.72-2.45 1.15-4.07 1.15-3.13 0-5.78-2.11-6.73-4.96H1.27v3.11A12 12 0 0 0 12 24z" />
          <path fill="#FBBC05" d="M5.27 14.28A7.2 7.2 0 0 1 4.89 12c0-.79.14-1.56.38-2.28V6.61H1.27A12 12 0 0 0 0 12c0 1.94.46 3.77 1.27 5.39l4-3.11z" />
          <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0A12 12 0 0 0 1.27 6.61l4 3.11C6.22 6.86 8.87 4.75 12 4.75z" />
        </svg>
        Sign in with Google
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useTheme } from '../composables/useTheme'
import { API_BASE_URL } from '../api/client'

const { t } = useTheme()

const cardStyle = computed(
  () =>
    `background:${t.value.card};border:1px solid ${t.value.line};border-radius:${t.value.r};padding:32px;box-shadow:${t.value.shadow};width:320px`
)

const buttonStyle = computed(
  () =>
    `display:flex;align-items:center;justify-content:center;gap:10px;width:100%;height:44px;border-radius:${t.value.br};border:1px solid ${t.value.line};background:${t.value.card};color:${t.value.ink};font:600 14px 'Geist',sans-serif;cursor:pointer`
)

function signIn() {
  window.location.href = `${API_BASE_URL}/auth/google/login`
}
</script>
