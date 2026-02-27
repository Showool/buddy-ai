import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Message, DebugInfo } from '@/types'
import { MessageType, type WSMessage } from '@/types'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<Message[]>([])
  const isStreaming = ref(false)
  const debugInfo = ref<DebugInfo[]>([])
  const currentThreadId = ref<string | null>(null)
  const debugPanelVisible = ref(false)

  function addMessage(message: Message) {
    messages.value.push(message)
  }

  function updateLastMessage(content: string) {
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.content = content
    }
  }

  function clearMessages() {
    messages.value = []
    debugInfo.value = []
  }

  function addDebugInfo(info: DebugInfo) {
    debugInfo.value.push(info)
  }

  function clearDebug() {
    debugInfo.value = []
  }

  function handleWSMessage(data: WSMessage) {
    switch (data.type) {
      case MessageType.AGENT_STEP:
        // 添加调试信息
        debugInfo.value.push({
          type: 'agent_step',
          message_type: data.message_type,
          role: getMessageRole(data.message_type),
          content: data.content,
          tool_calls: data.tool_calls,
          node: data.node,
        })
        break
      case MessageType.AGENT_COMPLETE:
        // 添加最终回复
        addMessage({
          role: 'assistant',
          content: data.final_answer,
        })
        currentThreadId.value = data.thread_id
        isStreaming.value = false
        break
      case MessageType.ERROR:
        console.error(data.message)
        isStreaming.value = false
        break
    }
  }

  function getMessageRole(messageType: string): string {
    switch (messageType) {
      case 'HumanMessage':
        return 'user'
      case 'AIMessage':
        return 'assistant'
      case 'ToolMessage':
        return 'tool'
      default:
        return 'unknown'
    }
  }

  return {
    messages,
    isStreaming,
    debugInfo,
    currentThreadId,
    debugPanelVisible,
    addMessage,
    updateLastMessage,
    clearMessages,
    clearDebug,
    addDebugInfo,
    handleWSMessage,
  }
})