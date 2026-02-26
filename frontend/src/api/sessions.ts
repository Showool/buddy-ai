import api from './index'
import type { Session, Memory } from '@/types'

export interface SessionsResponse {
  sessions: Session[]
  total: number
}

export interface MemoriesResponse {
  memories: Memory[]
  total: number
}

export interface SaveMemoryRequest {
  user_id: string
  content: string
}

export const sessionsApi = {
  // 获取会话列表
  async list(userId: string): Promise<SessionsResponse> {
    const response = await api.get<SessionsResponse>('/api/v1/sessions', {
      params: { user_id: userId },
    })
    return response
  },

  // 获取单个会话
  async get(threadId: string): Promise<Session> {
    const response = await api.get<Session>(`/api/v1/sessions/${threadId}`)
    return response
  },

  // 创建新会话
  async create(userId: string): Promise<{ session: Session }> {
    const response = await api.post<{ session: Session }>(
      '/api/v1/sessions',
      null,
      { params: { user_id: userId } }
    )
    return response
  },

  // 删除会话
  async delete(threadId: string): Promise<{ status: string; message: string }> {
    const response = await api.delete<{ status: string; message: string }>(
      `/api/v1/sessions/${threadId}`
    )
    return response
  },

  // 更新会话标题
  async updateTitle(
    threadId: string,
    title: string
  ): Promise<{ status: string; message: string }> {
    const response = await api.patch<{ status: string; message: string }>(
      `/api/v1/sessions/${threadId}/title`,
      null,
      { params: { title } }
    )
    return response
  },
}

export const memoryApi = {
  // 获取记忆列表
  async list(userId: string, query?: string): Promise<MemoriesResponse> {
    const response = await api.get<MemoriesResponse>('/api/v1/memory', {
      params: { user_id: userId, query },
    })
    return response
  },

  // 保存记忆
  async save(request: SaveMemoryRequest): Promise<{
    status: string
    memory_id: string
    message: string
  }> {
    const response = await api.post<{
      status: string
      memory_id: string
      message: string
    }>('/api/v1/memory', request)
    return response
  },

  // 删除记忆
  async delete(memoryId: string): Promise<{ status: string; message: string }> {
    const response = await api.delete<{ status: string; message: string }>(
      `/api/v1/memory/${memoryId}`
    )
    return response
  },
}