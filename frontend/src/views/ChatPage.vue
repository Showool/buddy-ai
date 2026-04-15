<template>
  <div class="chat-page">
    <ChatWindow :threadId="threadId" />
    <ChatInput
      v-model="inputText"
      :disabled="chatStore.isStreaming"
      :show-attach="true"
      :user-id="userStore.userId"
      placeholder="有问题，尽管问"
      @send="handleSend"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'
import { createSSEConnection } from '@/services/sse'
import { nanoid } from 'nanoid'
import ChatWindow from '@/components/ChatWindow.vue'
import ChatInput from '@/components/ChatInput.vue'

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()
const userStore = useUserStore()

// 输入文本
const inputText = ref('')

// 安全解析 threadId
const rawId = route.params.threadId
const threadId = Array.isArray(rawId) ? rawId[0] : rawId

// 校验 thread 是否存在，不存在则重定向
if (!threadId || !chatStore.threads.has(threadId)) {
  router.replace('/')
}

chatStore.switchThread(threadId)

/**
 * 发送消息到 SSE
 */
function sendToSSE(content: string) {
  chatStore.setStreaming(true)

  const controller = createSSEConnection(
    userStore.userId,
    threadId,
    content,
    {
      onWorkflowNode(data) {
        chatStore.appendToLastAIMessage(threadId, data.content)
      },
      onFinalAnswer(data) {
        chatStore.setFinalAnswer(threadId, data.content)
      },
      onError(error) {
        chatStore.appendToLastAIMessage(threadId, '❌ ' + error)
      },
      onComplete() {
        chatStore.setStreaming(false)
      },
    }
  )

  // 保存 controller，切换对话时可取消
  chatStore.setActiveController(controller)
}

/**
 * 处理发送消息
 */
function handleSend(message: string) {
  if (!userStore.userId) {
    ElMessage.warning('请先在侧边栏设置中配置 User ID')
    return
  }

  chatStore.addMessage(threadId, {
    id: nanoid(),
    role: 'user',
    content: message,
    timestamp: Date.now(),
  })

  sendToSSE(message)
}

// 处理自动发送（从欢迎页跳转）
onMounted(() => {
  if (route.query.autoSend === 'true') {
    const thread = chatStore.threads.get(threadId)
    if (thread && thread.messages.length > 0) {
      const lastUserMsg = [...thread.messages]
        .reverse()
        .find((m) => m.role === 'user')
      if (lastUserMsg) {
        sendToSSE(lastUserMsg.content)
      }
    }
    router.replace({ name: 'Chat', params: { threadId } })
  }
})

// 组件卸载时取消 SSE 连接
onUnmounted(() => {
  chatStore.cancelActiveStream()
})
</script>

<style scoped>
.chat-page {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
</style>
