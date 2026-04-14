<template>
  <div class="sidebar-settings">
    <el-input
      :model-value="userStore.userId"
      placeholder="请输入用户ID"
      @update:model-value="(val: string) => userStore.setUserId(val)"
    />
    <ThemeSwitcher />
  </div>
</template>

<script setup lang="ts">
import { useUserStore } from '@/stores/user'
import ThemeSwitcher from './ThemeSwitcher.vue'

const userStore = useUserStore()
</script>

<style scoped>
.sidebar-settings {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px 0;
}
</style>
