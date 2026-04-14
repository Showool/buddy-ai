import { defineStore } from 'pinia'
import type { ThemeMode } from '@/types'

const USER_ID_KEY = 'buddy-ai-user-id'
const THEME_KEY = 'buddy-ai-theme'

export const useUserStore = defineStore('user', {
  state: () => ({
    userId: '' as string,
    theme: 'light' as ThemeMode,
  }),

  actions: {
    setUserId(id: string) {
      this.userId = id
      localStorage.setItem(USER_ID_KEY, id)
    },

    toggleTheme() {
      this.theme = this.theme === 'light' ? 'dark' : 'light'
      localStorage.setItem(THEME_KEY, this.theme)
      this.applyTheme()
    },

    applyTheme() {
      if (this.theme === 'dark') {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    },

    loadFromStorage() {
      const savedUserId = localStorage.getItem(USER_ID_KEY)
      if (savedUserId !== null) {
        this.userId = savedUserId
      }

      const savedTheme = localStorage.getItem(THEME_KEY)
      if (savedTheme === 'light' || savedTheme === 'dark') {
        this.theme = savedTheme
      }
    },
  },
})
