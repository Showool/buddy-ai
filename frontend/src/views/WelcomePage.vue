<template>
  <div class="welcome-page">
    <div class="welcome-content">
      <h1 class="welcome-title">你今天在想些什么？</h1>
      <ChatInput
        v-model="inputText"
        :disabled="false"
        :show-attach="true"
        :user-id="userStore.userId"
        placeholder="有问题，尽管问"
        class="welcome-input"
        @send="handleSend"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'
import { nanoid } from 'nanoid'
import ChatInput from '@/components/ChatInput.vue'

const router = useRouter()
const chatStore = useChatStore()
const userStore = useUserStore()

const inputText = ref('')

/**
 * 处理发送消息
 */
function handleSend(message: string) {
  if (!userStore.userId) {
    ElMessage.warning('请先在侧边栏设置中配置 User ID')
    return
  }

  const threadId = nanoid()

  chatStore.createThread(threadId, message)

  chatStore.addMessage(threadId, {
    id: nanoid(),
    role: 'user',
    content: message,
    timestamp: Date.now(),
  })

  inputText.value = ''

  router.push({
    name: 'Chat',
    params: { threadId },
    query: { autoSend: 'true' },
  })
}
</script>

<style scoped>
.welcome-page {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.welcome-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 800px;
  padding: 0 24px;
}

.welcome-title {
  font-size: 28px;
  font-weight: 600;
  margin-bottom: 32px;
  color: var(--el-text-color-primary);
}

.welcome-input {
  width: 100%;
}

.welcome-input :deep(.chat-input-wrapper) {
  padding: 0;
}
</style>
