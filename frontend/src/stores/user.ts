import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore('user', () => {
  const userId = ref<string>('1')
  const userName = ref<string>('用户')
  const sidebarCollapsed = ref<boolean>(false)

  function setUserId(id: string) {
    userId.value = id
  }

  function setUserName(name: string) {
    userName.value = name
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return {
    userId,
    userName,
    sidebarCollapsed,
    setUserId,
    setUserName,
    toggleSidebar,
  }
})