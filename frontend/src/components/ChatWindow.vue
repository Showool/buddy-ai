<template>
  <div class="chat-window-scroll">
    <div class="chat-window-inner">
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="message-row"
        :class="msg.role"
      >
        <div
          v-if="msg.role === 'user'"
          class="message-bubble user"
        >
          {{ msg.content }}
        </div>
        <div
          v-else
          class="message-bubble assistant"
          :class="{ error: msg.content.startsWith('❌') }"
          v-html="renderMarkdown(msg.content)"
        />
      </div>

      <div v-if="showTyping" class="typing-row">
        <div class="typing-indicator">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
      </div>

      <div ref="scrollAnchorRef"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch, nextTick, ref } from 'vue'
import { useChatStore } from '@/stores/chat'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

// 过滤危险协议链接 (javascript:, vbscript:, data:) 并为外部链接添加安全属性
const defaultLinkRender = md.renderer.rules.link_open ||
  function (tokens: any, idx: any, options: any, _env: any, self: any) {
    return self.renderToken(tokens, idx, options)
  }

md.renderer.rules.link_open = function (tokens, idx, options, env, self) {
  const hrefIndex = tokens[idx].attrIndex('href')
  if (hrefIndex >= 0) {
    const href = tokens[idx].attrs![hrefIndex][1]
    if (/^(javascript|vbscript|data):/i.test(href)) {
      tokens[idx].attrs![hrefIndex][1] = '#'
    }
  }
  tokens[idx].attrSet('target', '_blank')
  tokens[idx].attrSet('rel', 'noopener noreferrer')
  return defaultLinkRender(tokens, idx, options, env, self)
}

const props = defineProps<{ threadId: string }>()

const chatStore = useChatStore()
const scrollAnchorRef = ref<HTMLDivElement>()

const messages = computed(() => {
  const thread = chatStore.threads.get(props.threadId)
  return thread ? thread.messages : []
})

const showTyping = computed(() => {
  if (!chatStore.isStreaming) return false
  const msgs = messages.value
  if (msgs.length === 0) return true
  const last = msgs[msgs.length - 1]
  return last.role !== 'assistant' || !last.content
})

function renderMarkdown(content: string): string {
  const raw = md.render(content)
  return DOMPurify.sanitize(raw, {
    ALLOWED_TAGS: [
      'p', 'br', 'strong', 'em', 'code', 'pre', 'ul', 'ol', 'li', 'a',
      'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr',
      'table', 'thead', 'tbody', 'tr', 'th', 'td', 'del', 'span',
    ],
    ALLOWED_ATTR: ['href', 'target', 'rel', 'class'],
    ALLOW_DATA_ATTR: false,
  })
}

function scrollToBottom() {
  nextTick(() => {
    scrollAnchorRef.value?.scrollIntoView({ behavior: 'smooth' })
  })
}

watch(() => messages.value.length, () => scrollToBottom())
watch(
  () => {
    const msgs = messages.value
    if (msgs.length === 0) return ''
    return msgs[msgs.length - 1].content
  },
  () => scrollToBottom(),
)
</script>

<style scoped>
.chat-window-scroll {
  flex: 1;
  overflow-y: auto;
  width: 100%;
}

.chat-window-inner {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-row {
  display: flex;
  width: 100%;
}
.message-row.user { justify-content: flex-end; }
.message-row.assistant { justify-content: flex-start; }

.message-bubble {
  max-width: 90%;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.message-bubble.user {
  background-color: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
  border-radius: 20px;
  padding: 14px 20px;
  font-size: 16px;
  white-space: pre-wrap;
}

.message-bubble.assistant {
  background-color: transparent;
  color: var(--el-text-color-primary);
  padding: 10px 0;
}

.message-bubble.error {
  background-color: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
  border: 1px solid var(--el-color-danger-light-5);
  border-radius: 12px;
  padding: 10px 16px;
}

/* Markdown 样式 */
.message-bubble.assistant :deep(p) { margin: 0.5em 0; }
.message-bubble.assistant :deep(p:first-child) { margin-top: 0; }
.message-bubble.assistant :deep(p:last-child) { margin-bottom: 0; }

.message-bubble.assistant :deep(pre) {
  background-color: var(--el-fill-color);
  border-radius: 8px;
  padding: 12px 16px;
  overflow-x: auto;
  margin: 8px 0;
}

.message-bubble.assistant :deep(code) {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
}

.message-bubble.assistant :deep(:not(pre) > code) {
  background-color: var(--el-fill-color);
  padding: 2px 6px;
  border-radius: 4px;
}

.message-bubble.assistant :deep(ul),
.message-bubble.assistant :deep(ol) {
  padding-left: 1.5em;
  margin: 0.5em 0;
}

.message-bubble.assistant :deep(a) { color: var(--el-color-primary); text-decoration: none; }
.message-bubble.assistant :deep(a:hover) { text-decoration: underline; }

.message-bubble.assistant :deep(blockquote) {
  border-left: 3px solid var(--el-border-color);
  padding-left: 12px;
  margin: 8px 0;
  color: var(--el-text-color-secondary);
}

/* 打字指示器 */
.typing-row {
  display: flex;
  justify-content: flex-start;
  width: 100%;
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 10px 16px;
  background-color: var(--el-fill-color);
  border-radius: 12px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--el-text-color-secondary);
  animation: typing 1.4s infinite ease-in-out both;
}
.dot:nth-child(1) { animation-delay: 0s; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}
</style>
