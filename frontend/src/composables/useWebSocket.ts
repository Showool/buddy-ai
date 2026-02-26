import { ref, onUnmounted, type Ref } from 'vue'
import { useChatStore } from '@/stores/chat'
import type { WSMessage, UserMessageRequest } from '@/types'
import { MessageType } from '@/types'

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'

export function useWebSocket(userId: string) {
  const chatStore = useChatStore()
  const ws: Ref<WebSocket | null> = ref(null)
  const isConnected = ref(false)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 5

  function connect() {
    try {
      ws.value = new WebSocket(`${WS_BASE_URL}/api/v1/ws/chat/${userId}`)

      ws.value.onopen = () => {
        console.log('WebSocket 已连接')
        isConnected.value = true
        reconnectAttempts.value = 0
      }

      ws.value.onmessage = (event) => {
        try {
          const data: WSMessage = JSON.parse(event.data)
          chatStore.handleWSMessage(data)
        } catch (error) {
          console.error('解析 WebSocket 消息失败:', error)
        }
      }

      ws.value.onerror = (error) => {
        console.error('WebSocket 错误:', error)
      }

      ws.value.onclose = () => {
        console.log('WebSocket 已断开')
        isConnected.value = false

        // 自动重连
        if (reconnectAttempts.value < maxReconnectAttempts) {
          reconnectAttempts.value++
          console.log(`尝试重连 (${reconnectAttempts.value}/${maxReconnectAttempts})...`)
          setTimeout(() => {
            connect()
          }, 1000 * reconnectAttempts.value)
        }
      }
    } catch (error) {
      console.error('创建 WebSocket 连接失败:', error)
    }
  }

  function sendMessage(content: string, threadId?: string) {
    if (!ws.value || !isConnected.value) {
      console.error('WebSocket 未连接')
      return
    }

    const message: UserMessageRequest = {
      type: MessageType.USER_MESSAGE,
      content,
      thread_id: threadId,
    }

    ws.value.send(JSON.stringify(message))
  }

  function disconnect() {
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
  }

  function reconnect() {
    disconnect()
    reconnectAttempts.value = 0
    connect()
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected,
    reconnectAttempts,
    connect,
    sendMessage,
    disconnect,
    reconnect,
  }
}