import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore('user', () => {
  const userId = ref<string>('1')
  const userName = ref<string>('用户')

  function setUserId(id: string) {
    userId.value = id
  }

  function setUserName(name: string) {
    userName.value = name
  }

  return {
    userId,
    userName,
    setUserId,
    setUserName,
  }
})