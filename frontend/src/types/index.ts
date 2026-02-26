// 类型定义

export type MessageRole = 'user' | 'assistant'

export interface Message {
  role: MessageRole
  content: string
  timestamp?: string
}

export interface DebugInfo {
  type: string
  message_type?: string
  role?: string
  content: string
  tool_calls?: ToolCall[]
  node?: string
}

export interface ToolCall {
  name: string
  args: Record<string, any>
}

export interface Session {
  thread_id: string
  user_id: string
  title?: string
  created_at: string
  updated_at: string
  message_count: number
}

export interface Memory {
  id: string
  user_id: string
  content: string
  created_at: string
}

export interface UploadedFile {
  id: string
  filename: string
  size: number
  status: string
  vectorized: boolean
  upload_time: string
}

// WebSocket 消息类型
export enum MessageType {
  USER_MESSAGE = 'user_message',
  AGENT_STEP = 'agent_step',
  AGENT_COMPLETE = 'agent_complete',
  ERROR = 'error',
}

export interface AgentStepMessage {
  type: MessageType.AGENT_STEP
  node: string
  message_type: string
  content: string
  tool_calls?: ToolCall[]
}

export interface AgentCompleteMessage {
  type: MessageType.AGENT_COMPLETE
  final_answer: string
  thread_id: string
}

export interface ErrorMessage {
  type: MessageType.ERROR
  message: string
  code?: string
}

export type WSMessage = AgentStepMessage | AgentCompleteMessage | ErrorMessage