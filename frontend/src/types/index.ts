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

/** SSE workflow_node 事件数据 */
export interface WorkflowNodeEvent {
  content: string
  node: string
}

/** SSE final_answer 事件数据 */
export interface FinalAnswerEvent {
  content: string
}
