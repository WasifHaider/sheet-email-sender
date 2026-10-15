<template>
  <v-app>
    <v-app-bar color="background" flat>
      <v-container class="d-flex align-center" style="max-width: 960px">
        <span class="text-subtitle-1 font-weight-medium">Sheet Email Sender</span>
        <v-spacer />
        <v-btn variant="text" :to="{ name: 'upload' }">Upload</v-btn>
      </v-container>
    </v-app-bar>
    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>

<script setup></script>
