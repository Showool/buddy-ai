<template>
  <div class="app-container">
    <Sidebar />
    <router-view :key="$route.path" />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import Sidebar from '@/components/Sidebar.vue'

const userStore = useUserStore()

onMounted(() => {
  userStore.loadFromStorage()
  userStore.applyTheme()
})
</script>
