<template>
  <el-switch
    :model-value="userStore.theme === 'dark'"
    active-text="🌙"
    inactive-text="☀️"
    @change="userStore.toggleTheme()"
  />
</template>

<script setup lang="ts">
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
</script>
