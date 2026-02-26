import api from './index'
import type { UploadedFile } from '@/types'

export interface FileUploadResponse extends UploadedFile {}

export interface VectorizeRequest {
  file_ids: string[]
}

export interface VectorizeResponse {
  status: string
  chunk_count: number
  message?: string
}

export const filesApi = {
  // 上传文件
  async upload(file: File): Promise<FileUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post<FileUploadResponse>(
      '/api/v1/files/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )
    return response
  },

  // 向量化文件
  async vectorize(fileIds: string[]): Promise<VectorizeResponse> {
    const response = await api.post<VectorizeResponse>(
      '/api/v1/files/vectorize',
      { file_ids: fileIds }
    )
    return response
  },

  // 获取文件列表
  async list(): Promise<{ files: UploadedFile[] }> {
    const response = await api.get<{ files: UploadedFile[] }>('/api/v1/files')
    return response
  },

  // 删除文件
  async delete(fileId: string): Promise<{ status: string; message: string }> {
    const response = await api.delete<{ status: string; message: string }>(
      `/api/v1/files/${fileId}`
    )
    return response
  },
}