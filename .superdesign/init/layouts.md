# Layouts

## App Shell — `frontend/src/App.vue`
Renders on every page: a flat `v-app-bar` with the app title ("Sheet Email Sender") on the left, a spacer, and an "Upload" nav link on the right, all inside a 960px-max-width container. Below it, `v-main` renders the active route via `<router-view />`.

```vue
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
```

No sidebar, footer, or breadcrumb exists. The Status view (not yet built) will add a second nav link here ("Status").
