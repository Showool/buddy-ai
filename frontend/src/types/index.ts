/** 消息角色 */
export type MessageRole = 'user' | 'assistant'

/** 单条消息 */
export interface Message {
  id: string
  role: MessageRole
  content: string
  timestamp: number
}

/** 对话线程 */
export interface Thread {
  threadId: string
  title: string
  messages: Message[]
  createdAt: number
  updatedAt: number
}

/** 主题类型 */
export type ThemeMode = 'light' | 'dark'

/** SSE 后端返回的单行 JSON 对象 */
export interface SSEJsonLine {
  event?: string
  content?: string
  node?: string
  error?: string
}

/** 知识库文件 */
export interface KnowledgeFile {
  id: number
  knowledge_id: number
  file_name: string
  file_type: string
  file_size: number
  file_path: string | null
  file_md5: string | null
  creator_id: string
  create_time: string
  update_id: string
  update_time: string
}

/** 文件上传允许的扩展名 */
export const ALLOWED_EXTENSIONS = ['.txt', '.docx', '.md'] as const

/** 默认知识库 ID */
export const DEFAULT_KNOWLEDGE_ID = 1

/** 文件上传响应 */
export interface UploadFileResponse {
  filename: string
  content: string[]
}
