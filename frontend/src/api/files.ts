import api from './index'

export interface FileUploadResponse {
  id: string
  filename: string
  size: number
  file_size: number
  file_type: string
  status: string
  vectorized: boolean
  upload_time: string
  task_id?: string  // 已弃用，保留用于向后兼容
}

export interface VectorizationTaskStatus {
  id: string
  file_id: string
  user_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  total_chunks: number
  processed_chunks: number
  error_message?: string
  created_at: string
  updated_at: string
  completed_at?: string
}

export interface KnowledgeBaseFile {
  id: string
  filename: string
  file_type: string
  file_size: number
  chunk_count: number
  summary?: string
  last_vectorized?: string
  upload_time?: string
  is_public?: boolean
}

export interface KnowledgeBaseResponse {
  private: KnowledgeBaseFile[]
  public: KnowledgeBaseFile[]
}

export const filesApi = {
  // 上传文件（自动向量化）
  async upload(file: File, userId: string, isPublic = false): Promise<FileUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('user_id', userId)
    formData.append('is_public', isPublic.toString())

    return api.post<FileUploadResponse>(
      '/api/v1/files/upload',
      formData,
      // 不设置 Content-Type，让浏览器自动设置并生成正确的 boundary
    )
  },

  // 获取文件列表
  async list(userId: string): Promise<{ files: FileUploadResponse[]; total: number }> {
    return api.get<{ files: FileUploadResponse[]; total: number }>('/api/v1/files', {
      params: { user_id: userId }
    })
  },

  // 删除文件
  async delete(fileId: string, userId: string): Promise<{ status: string; message: string; file_id: string }> {
    return api.delete<{ status: string; message: string; file_id: string }>(
      `/api/v1/files/${fileId}`,
      { params: { user_id: userId } }
    )
  },

  // 获取向量化进度
  async getVectorizationProgress(fileId: string): Promise<VectorizationTaskStatus> {
    return api.get<VectorizationTaskStatus>(
      `/api/v1/files/vectorization/progress/${fileId}`
    )
  },

  // 获取知识库文件列表（私有+公开）
  async getKnowledgeBaseFiles(userId: string, includePublic = true): Promise<KnowledgeBaseResponse> {
    return api.get<KnowledgeBaseResponse>('/api/v1/files/knowledge-base', {
      params: { user_id: userId, include_public: includePublic }
    })
  },
}