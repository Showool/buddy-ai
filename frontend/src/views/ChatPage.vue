<template>
  <div class="chat-page">
    <ChatWindow :threadId="threadId" />
    <MessageInput @send="handleSend" />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'
import { createSSEConnection } from '@/services/sse'
import ChatWindow from '@/components/ChatWindow.vue'
import MessageInput from '@/components/MessageInput.vue'

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()
const userStore = useUserStore()

const threadId = route.params.threadId as string

chatStore.switchThread(threadId)

function sendToSSE(content: string) {
  chatStore.setStreaming(true)

  createSSEConnection(userStore.userId, threadId, content, {
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
  })
}

function handleSend(message: string) {
  const userMessage = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    role: 'user' as const,
    content: message,
    timestamp: Date.now(),
  }

  chatStore.addMessage(threadId, userMessage)
  sendToSSE(message)
}

onMounted(() => {
  if (route.query.autoSend === 'true') {
    const thread = chatStore.threads.get(threadId)
    if (thread && thread.messages.length > 0) {
      const lastUserMsg = [...thread.messages].reverse().find(m => m.role === 'user')
      if (lastUserMsg) {
        sendToSSE(lastUserMsg.content)
      }
    }
    // Remove the query param after processing
    router.replace({ name: 'Chat', params: { threadId } })
  }
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
