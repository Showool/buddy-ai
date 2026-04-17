function validateEnv(): void {
  const required = ['VITE_API_BASE_URL'] as const
  for (const key of required) {
    if (!import.meta.env[key]) {
      throw new Error(`缺少必需的环境变量: ${key}`)
    }
  }
}

function parseBool(value: string | undefined): boolean {
  return value?.toLowerCase() === 'true'
}

validateEnv()

export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL,
  appTitle: import.meta.env.VITE_APP_TITLE,
  appVersion: import.meta.env.VITE_APP_VERSION,
  enableDebug: parseBool(import.meta.env.VITE_ENABLE_DEBUG),
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
  mode: import.meta.env.MODE,
} as const
