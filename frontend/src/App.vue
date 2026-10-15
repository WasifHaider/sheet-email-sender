<template>
  <v-app>
    <v-app-bar color="surface">
      <v-container class="d-flex align-center" style="max-width: 960px">
        <v-icon icon="mdi-send" color="primary" size="20" class="mr-2" />
        <span class="text-subtitle-1 font-weight-bold">Sheet Email Sender</span>
        <v-spacer />
        <v-btn
          variant="text"
          :class="{ 'nav-link-active': route.name === 'upload' }"
          :to="{ name: 'upload' }"
        >
          Upload
        </v-btn>
        <v-btn
          variant="text"
          :class="{ 'nav-link-active': route.name === 'status' }"
          :to="{ name: 'status' }"
        >
          Status
        </v-btn>
      </v-container>
    </v-app-bar>
    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>

<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()
</script>
