import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Message, Thread } from '@/types'
import { nanoid } from 'nanoid'

const STORAGE_KEY = 'buddy-ai-threads'

function loadThreads(): Map<string, Thread> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return new Map()
    const arr: Thread[] = JSON.parse(raw)
    return new Map(arr.map((t) => [t.threadId, t]))
  } catch {
    return new Map()
  }
}

function saveThreads(threads: Map<string, Thread>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(threads.values())))
  } catch { /* storage full or unavailable */ }
}

export const useChatStore = defineStore('chat', () => {
  const threads = ref(loadThreads())
  const currentThreadId = ref<string | null>(null)
  const isStreaming = ref(false)
  const pendingSend = ref(false)
  let activeController: AbortController | null = null

  const threadList = computed(() =>
    Array.from(threads.value.values()).sort((a, b) => b.updatedAt - a.updatedAt),
  )

  function persist() {
    saveThreads(threads.value)
  }

  function createThread(threadId: string, firstMessage: string) {
    threads.value.set(threadId, {
      threadId,
      title: firstMessage.slice(0, 20),
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    })
    currentThreadId.value = threadId
    persist()
  }

  function switchThread(threadId: string) {
    if (threads.value.has(threadId)) {
      currentThreadId.value = threadId
    }
  }

  function deleteThread(threadId: string) {
    if (currentThreadId.value === threadId && isStreaming.value) {
      cancelActiveStream()
    }
    threads.value.delete(threadId)
    if (currentThreadId.value === threadId) {
      currentThreadId.value = null
    }
    persist()
  }

  function addMessage(threadId: string, message: Message) {
    const thread = threads.value.get(threadId)
    if (!thread) return
    thread.messages.push(message)
    thread.updatedAt = Date.now()
    persist()
  }

  function addUserMessage(threadId: string, content: string) {
    addMessage(threadId, {
      id: nanoid(),
      role: 'user',
      content,
      timestamp: Date.now(),
    })
  }

  /**
   * 更新或创建最后一条 assistant 消息
   * @param append true=追加内容 false=替换内容
   */
  function upsertAssistantMessage(threadId: string, content: string, append: boolean) {
    const thread = threads.value.get(threadId)
    if (!thread) return
    const last = thread.messages[thread.messages.length - 1]
    if (last && last.role === 'assistant') {
      last.content = append ? last.content + content : content
    } else {
      thread.messages.push({ id: nanoid(), role: 'assistant', content, timestamp: Date.now() })
    }
    thread.updatedAt = Date.now()
  }

  function appendToLastAIMessage(threadId: string, content: string) {
    upsertAssistantMessage(threadId, content, true)
    // 流式追加时不频繁写 localStorage，等 setStreaming(false) 时统一持久化
  }

  function setFinalAnswer(threadId: string, content: string) {
    upsertAssistantMessage(threadId, content, false)
    persist()
  }

  function setStreaming(value: boolean) {
    isStreaming.value = value
    if (!value) persist() // 流结束时统一持久化
  }

  function setActiveController(ctrl: AbortController | null) {
    if (activeController) activeController.abort()
    activeController = ctrl
  }

  function cancelActiveStream() {
    if (activeController) {
      activeController.abort()
      activeController = null
    }
    isStreaming.value = false
    persist()
  }

  return {
    threads,
    currentThreadId,
    isStreaming,
    pendingSend,
    threadList,
    createThread,
    switchThread,
    deleteThread,
    addMessage,
    addUserMessage,
    appendToLastAIMessage,
    setFinalAnswer,
    setStreaming,
    setActiveController,
    cancelActiveStream,
  }
})
