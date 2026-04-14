import { defineStore } from 'pinia'
import { reactive } from 'vue'
import type { Message, Thread } from '@/types'

export const useChatStore = defineStore('chat', {
  state: () => ({
    threads: reactive(new Map<string, Thread>()),
    currentThreadId: null as string | null,
    isStreaming: false,
  }),

  actions: {
    createThread(threadId: string, firstMessage: string) {
      const now = Date.now()
      const thread: Thread = {
        threadId,
        title: firstMessage.slice(0, 20),
        messages: [],
        createdAt: now,
        updatedAt: now,
      }
      this.threads.set(threadId, thread)
      this.currentThreadId = threadId
    },

    switchThread(threadId: string) {
      if (this.threads.has(threadId)) {
        this.currentThreadId = threadId
      }
    },

    getThreadList(): Thread[] {
      return Array.from(this.threads.values()).sort(
        (a, b) => b.updatedAt - a.updatedAt,
      )
    },

    addMessage(threadId: string, message: Message) {
      const thread = this.threads.get(threadId)
      if (!thread) return
      thread.messages.push(message)
      thread.updatedAt = Date.now()
    },

    appendToLastAIMessage(threadId: string, content: string) {
      const thread = this.threads.get(threadId)
      if (!thread) return

      const lastMsg = thread.messages[thread.messages.length - 1]
      if (lastMsg && lastMsg.role === 'assistant') {
        lastMsg.content += content
      } else {
        const newMsg: Message = {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
          role: 'assistant',
          content,
          timestamp: Date.now(),
        }
        thread.messages.push(newMsg)
      }
      thread.updatedAt = Date.now()
    },

    setFinalAnswer(threadId: string, content: string) {
      const thread = this.threads.get(threadId)
      if (!thread) return

      const lastMsg = thread.messages[thread.messages.length - 1]
      if (lastMsg && lastMsg.role === 'assistant') {
        lastMsg.content = content
      } else {
        const newMsg: Message = {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
          role: 'assistant',
          content,
          timestamp: Date.now(),
        }
        thread.messages.push(newMsg)
      }
      thread.updatedAt = Date.now()
    },

    setStreaming(value: boolean) {
      this.isStreaming = value
    },
  },
})
