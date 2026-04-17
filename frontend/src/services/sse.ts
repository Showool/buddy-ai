import type { SSEJsonLine } from '@/types'
import request from './request'

export interface SSEClientOptions {
  onWorkflowNode: (data: { content: string; node: string }) => void
  onFinalAnswer: (data: { content: string }) => void
  onError: (error: string) => void
  onComplete: () => void
}

/**
 * Parse a single SSE data payload and dispatch to the appropriate callback.
 */
function dispatchEvent(
  eventType: string | null,
  dataStr: string,
  options: SSEClientOptions,
): void {
  if (!dataStr) return

  try {
    const parsed: SSEJsonLine = JSON.parse(dataStr)

    const event = eventType || parsed.event

    if (parsed.error) {
      options.onError(parsed.error)
      return
    }

    if (event === 'workflow_node') {
      options.onWorkflowNode({
        content: parsed.content ?? '',
        node: parsed.node ?? '',
      })
    } else if (event === 'final_answer') {
      options.onFinalAnswer({
        content: parsed.content ?? '',
      })
    }
  } catch {
    options.onError(`Failed to parse SSE data: ${dataStr}`)
  }
}

/**
 * 处理 SSE 流式响应的行解析
 */
function processStreamBuffer(
  buffer: string,
  state: { currentEvent: string | null; currentData: string },
  options: SSEClientOptions,
): string {
  const lines = buffer.split('\n')
  const remaining = lines.pop() ?? ''

  for (const line of lines) {
    const trimmed = line.trim()

    if (trimmed === '') {
      if (state.currentData) {
        dispatchEvent(state.currentEvent, state.currentData, options)
        state.currentEvent = null
        state.currentData = ''
      }
      continue
    }

    if (trimmed.startsWith('event:')) {
      state.currentEvent = trimmed.slice(6).trim()
    } else if (trimmed.startsWith('data:')) {
      const dataValue = trimmed.slice(5).trim()
      state.currentData = state.currentData ? `${state.currentData}\n${dataValue}` : dataValue
    } else if (trimmed.startsWith(':')) {
      // SSE comment — ignore
    } else if (trimmed.startsWith('{')) {
      dispatchEvent(null, trimmed, options)
    }
  }

  return remaining
}


/**
 * Create an SSE connection using axios + ReadableStream.
 *
 * Sends a POST request to /agent/chat with JSON body containing
 * user_id, thread_id, and user_input. Reads the response stream
 * line by line, parsing both standard SSE format (event:/data: lines)
 * and plain JSON lines.
 *
 * Returns an AbortController that can be used to cancel the connection.
 */
export function createSSEConnection(
  userId: string,
  threadId: string,
  userInput: string,
  options: SSEClientOptions,
): AbortController {
  const controller = new AbortController()

  // 空闲超时：连续 120 秒无数据则认为连接异常，主动断开
  const IDLE_TIMEOUT_MS = 120_000

  const run = async () => {
    let idleTimer: ReturnType<typeof setTimeout> | null = null

    const resetIdleTimer = () => {
      if (idleTimer) clearTimeout(idleTimer)
      idleTimer = setTimeout(() => {
        controller.abort()
        options.onError('连接超时：服务端长时间无响应')
      }, IDLE_TIMEOUT_MS)
    }

    const clearIdleTimer = () => {
      if (idleTimer) {
        clearTimeout(idleTimer)
        idleTimer = null
      }
    }

    try {
      resetIdleTimer()

      const response = await request.post('/agent/chat', {
        user_id: userId,
        thread_id: threadId,
        user_input: userInput,
      }, {
        headers: { Accept: 'text/event-stream' },
        responseType: 'stream',
        adapter: 'fetch',
        signal: controller.signal,
        timeout: 0, // SSE 长连接，禁用 axios 请求级超时，由空闲超时接管
      })

      const stream: ReadableStream<Uint8Array> = response.data
      const reader = stream.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      const state = { currentEvent: null as string | null, currentData: '' }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        resetIdleTimer()
        buffer += decoder.decode(value, { stream: true })
        buffer = processStreamBuffer(buffer, state, options)
      }

      // Flush remaining buffer
      const remaining = buffer.trim()
      if (remaining) {
        if (state.currentData || remaining.startsWith('data:')) {
          if (remaining.startsWith('data:')) {
            const dataValue = remaining.slice(5).trim()
            state.currentData = state.currentData
              ? `${state.currentData}\n${dataValue}`
              : dataValue
          }
          if (state.currentData) {
            dispatchEvent(state.currentEvent, state.currentData, options)
          }
        } else if (remaining.startsWith('{')) {
          dispatchEvent(null, remaining, options)
        }
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        // Connection was intentionally aborted
      } else {
        const message = err instanceof Error ? err.message : String(err)
        options.onError(message)
      }
    } finally {
      clearIdleTimer()
      options.onComplete()
    }
  }

  run()

  return controller
}
