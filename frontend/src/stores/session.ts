import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Session } from '@/types'

export const useSessionStore = defineStore('session', () => {
  const sessions = ref<Session[]>([])
  const currentSession = ref<Session | null>(null)
  const userId = ref<string>('1')

  function setUserId(id: string) {
    userId.value = id
  }

  function setCurrentSession(session: Session) {
    currentSession.value = session
  }

  function createNewThread(): string {
    const threadId = crypto.randomUUID()
    const now = new Date().toISOString()

    const newSession: Session = {
      thread_id: threadId,
      user_id: userId.value,
      title: undefined,
      created_at: now,
      updated_at: now,
      message_count: 0,
    }

    sessions.value.unshift(newSession)
    setCurrentSession(newSession)

    return threadId
  }

  function updateSessionTitle(threadId: string, title: string) {
    const session = sessions.value.find(s => s.thread_id === threadId)
    if (session) {
      session.title = title
      session.updated_at = new Date().toISOString()
    }
  }

  function updateSessionMessageCount(threadId: string) {
    const session = sessions.value.find(s => s.thread_id === threadId)
    if (session) {
      session.message_count += 1
      session.updated_at = new Date().toISOString()
    }
  }

  function deleteSession(threadId: string) {
    const index = sessions.value.findIndex(s => s.thread_id === threadId)
    if (index !== -1) {
      sessions.value.splice(index, 1)
      if (currentSession.value?.thread_id === threadId) {
        currentSession.value = null
      }
    }
  }

  return {
    sessions,
    currentSession,
    userId,
    setUserId,
    setCurrentSession,
    createNewThread,
    updateSessionTitle,
    updateSessionMessageCount,
    deleteSession,
  }
})