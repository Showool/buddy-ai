import type { KnowledgeFile, UploadFileResponse } from '@/types'
import { ALLOWED_EXTENSIONS } from '@/types'

/**
 * 校验文件扩展名是否在允许列表中
 */
export function isFileAllowed(filename: string): boolean {
  const ext = filename.slice(filename.lastIndexOf('.')).toLowerCase()
  return (ALLOWED_EXTENSIONS as readonly string[]).includes(ext)
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

  const res = await fetch('/knowledgebase/upload_file', {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `上传失败: ${res.status}`)
  }

  return res.json()
}

/**
 * 获取知识库文件列表
 */
export async function getFiles(userId: string, knowledgeId: number): Promise<KnowledgeFile[]> {
  const params = new URLSearchParams({ user_id: userId, knowledge_id: String(knowledgeId) })
  const res = await fetch(`/knowledgebase/get_files?${params}`)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `获取文件列表失败: ${res.status}`)
  }
  return res.json()
}

/**
 * 删除知识库文件
 */
export async function deleteFile(userId: string, knowledgeId: number, fileId: number): Promise<void> {
  const res = await fetch('/knowledgebase/delete_file', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, knowledge_id: knowledgeId, file_id: fileId }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `删除文件失败: ${res.status}`)
  }
}

/**
 * 下载知识库文件
 */
export async function downloadFile(fileId: number, fileName: string): Promise<void> {
  const res = await fetch(`/knowledgebase/download_file?file_id=${fileId}`)
  if (!res.ok) {
    throw new Error(`下载失败: ${res.status}`)
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  a.click()
  URL.revokeObjectURL(url)
}
