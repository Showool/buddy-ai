import type { UploadFileResponse } from '@/types'
import { ALLOWED_EXTENSIONS } from '@/types'

/**
 * 校验文件扩展名是否在允许列表中
 */
export function isFileAllowed(filename: string): boolean {
  const ext = filename.slice(filename.lastIndexOf('.')).toLowerCase()
  return (ALLOWED_EXTENSIONS as readonly string[]).includes(ext)
}

/**
 * 上传文件到 /upload_file 接口
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

  const res = await fetch('/upload_file', {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `上传失败: ${res.status}`)
  }

  return res.json()
}
