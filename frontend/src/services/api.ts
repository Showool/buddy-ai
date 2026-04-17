import type { KnowledgeFile, UploadFileResponse } from '@/types'
import { ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE } from '@/types'
import request from './request'

/**
 * 校验文件扩展名是否在允许列表中
 */
export function isFileAllowed(filename: string): boolean {
  const ext = filename.slice(filename.lastIndexOf('.')).toLowerCase()
  return ALLOWED_EXTENSIONS.includes(ext as typeof ALLOWED_EXTENSIONS[number])
}

/**
 * 校验文件大小是否在允许范围内
 */
export function isFileSizeAllowed(size: number): boolean {
  return size <= MAX_UPLOAD_SIZE
}

/**
 * 上传文件到 /knowledgebase/upload_file 接口
 */
export async function uploadFile(
  file: File,
  userId: string,
  knowledgeId: number,
): Promise<UploadFileResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('user_id', userId)
  formData.append('knowledge_id', String(knowledgeId))

  const { data } = await request.post<UploadFileResponse>(
    '/knowledgebase/upload_file',
    formData,
  )
  return data
}

/**
 * 获取知识库文件列表
 */
export async function getFiles(userId: string, knowledgeId: number): Promise<KnowledgeFile[]> {
  const { data } = await request.get<KnowledgeFile[]>('/knowledgebase/get_files', {
    params: { user_id: userId, knowledge_id: knowledgeId },
  })
  return data
}

/**
 * 删除知识库文件
 */
export async function deleteFile(userId: string, knowledgeId: number, fileId: number): Promise<void> {
  await request.post('/knowledgebase/delete_file', {
    user_id: userId,
    knowledge_id: knowledgeId,
    file_id: fileId,
  })
}

/**
 * 下载知识库文件
 */
export async function downloadFile(fileId: number, fileName: string): Promise<void> {
  const { data } = await request.get<Blob>('/knowledgebase/download_file', {
    params: { file_id: fileId },
    responseType: 'blob',
  })
  const url = URL.createObjectURL(data)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  a.click()
  URL.revokeObjectURL(url)
}
