import axios from 'axios'
import { env } from '@/config/env'

/**
 * 全局 axios 实例
 * - 开发环境通过 vite proxy 转发，baseURL 留空
 * - 生产环境使用 VITE_API_BASE_URL
 */
const request = axios.create({
  baseURL: env.isProd ? env.apiBaseUrl : '',
  timeout: 30000,
})

// 响应拦截器：统一提取 data、处理错误
request.interceptors.response.use(
  (res) => res,
  (error) => {
    const detail = error.response?.data?.detail
    const message = detail ?? error.message ?? '请求失败'
    return Promise.reject(new Error(message))
  },
)

export default request
