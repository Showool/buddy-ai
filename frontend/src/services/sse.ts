import type { SSEJsonLine } from '@/types'

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

    // Determine event type: explicit SSE event field takes priority,
    // then fall back to the "event" field inside the JSON payload
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
    // JSON parse failed — treat as error
    options.onError(`Failed to parse SSE data: ${dataStr}`)
  }
}

/**
 * Create an SSE connection using fetch + ReadableStream.
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

  const run = async () => {
    try {
      const response = await fetch('/agent/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({
          user_id: userId,
          thread_id: threadId,
          user_input: userInput,
        }),
        signal: controller.signal,
      })

      if (!response.ok) {
        options.onError(`HTTP error: ${response.status} ${response.statusText}`)
        options.onComplete()
        return
      }

      const reader = response.body?.getReader()
      if (!reader) {
        options.onError('Response body is not readable')
        options.onComplete()
        return
      }

      const decoder = new TextDecoder()
      let buffer = ''
      // SSE parsing state
      let currentEvent: string | null = null
      let currentData = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Process complete lines from the buffer
        const lines = buffer.split('\n')
        // Keep the last incomplete line in the buffer
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          const trimmed = line.trim()

          if (trimmed === '') {
            // Empty line = end of an SSE event block
            if (currentData) {
              dispatchEvent(currentEvent, currentData, options)
              currentEvent = null
              currentData = ''
            }
            continue
          }

          if (trimmed.startsWith('event:')) {
            // SSE event type line
            currentEvent = trimmed.slice(6).trim()
          } else if (trimmed.startsWith('data:')) {
            // SSE data line (may span multiple lines, concatenate with newline)
            const dataValue = trimmed.slice(5).trim()
            currentData = currentData ? `${currentData}\n${dataValue}` : dataValue
          } else if (trimmed.startsWith(':')) {
            // SSE comment line — ignore
          } else if (trimmed.startsWith('{')) {
            // Plain JSON line (fallback for non-SSE format)
            dispatchEvent(null, trimmed, options)
          }
        }
      }

      // Flush any remaining data in the buffer
      const remaining = buffer.trim()
      if (remaining) {
        if (currentData || remaining.startsWith('data:')) {
          if (remaining.startsWith('data:')) {
            const dataValue = remaining.slice(5).trim()
            currentData = currentData ? `${currentData}\n${dataValue}` : dataValue
          }
          if (currentData) {
            dispatchEvent(currentEvent, currentData, options)
          }
        } else if (remaining.startsWith('{')) {
          dispatchEvent(null, remaining, options)
        }
      }
    } catch (err: unknown) {
      // AbortError is expected when the connection is intentionally closed
      if (err instanceof DOMException && err.name === 'AbortError') {
        // Connection was intentionally aborted — not an error
      } else {
        const message = err instanceof Error ? err.message : String(err)
        options.onError(message)
      }
    } finally {
      options.onComplete()
    }
  }

  run()

  return controller
}
