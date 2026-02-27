import { ref, computed, watch, onMounted } from 'vue'

export type Theme = 'dark' | 'light'

const STORAGE_KEY = 'buddy-ai-theme'

const theme = ref<Theme>('light')

// 获取初始主题
function getInitialTheme(): Theme {
  // 1. 检查 localStorage
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'dark' || stored === 'light') {
    return stored
  }

  // 2. 检查系统偏好
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }

  // 默认浅色主题
  return 'light'
}

export function useTheme() {
  // 设置主题到 DOM (Element Plus 使用 dark 类)
  function applyTheme(newTheme: Theme) {
    const htmlElement = document.documentElement
    if (newTheme === 'dark') {
      htmlElement.classList.add('dark')
    } else {
      htmlElement.classList.remove('dark')
    }
  }

  // 切换主题
  function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }

  // 设置特定主题
  function setTheme(newTheme: Theme) {
    theme.value = newTheme
  }

  // 监听主题变化，应用到 DOM 和 localStorage
  watch(theme, (newTheme) => {
    applyTheme(newTheme)
    localStorage.setItem(STORAGE_KEY, newTheme)
  }, { immediate: true })

  onMounted(() => {
    // 初始化主题
    const initialTheme = getInitialTheme()
    theme.value = initialTheme

    // 监听系统主题变化
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      const handleChange = (e: MediaQueryListEvent) => {
        // 只有当用户没有手动设置主题时才跟随系统
        const stored = localStorage.getItem(STORAGE_KEY)
        if (!stored) {
          theme.value = e.matches ? 'dark' : 'light'
        }
      }

      mediaQuery.addEventListener('change', handleChange)

      // 清理监听器
      return () => {
        mediaQuery.removeEventListener('change', handleChange)
      }
    }
  })

  return {
    theme,
    toggleTheme,
    setTheme,
    isDark: computed(() => theme.value === 'dark'),
    isLight: computed(() => theme.value === 'light')
  }
}