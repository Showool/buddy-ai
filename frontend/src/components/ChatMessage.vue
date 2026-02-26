<template>
  <div class="chat-message" :class="`message-${message.role}`">
    <div class="message-avatar">
      {{ message.role === 'user' ? '👤' : '🤖' }}
    </div>
    <div class="message-content">
      <div class="message-sender">
        {{ message.role === 'user' ? '用户' : 'Buddy-AI' }}
      </div>
      <div class="message-text" v-html="renderedContent"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import type { Message } from '@/types'

interface Props {
  message: Message
}

const props = defineProps<Props>()

// 配置 marked
marked.setOptions({
  highlight: (code, lang) => {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true,
})

const renderedContent = computed(() => {
  return marked(props.message.content)
})
</script>

<style scoped>
.chat-message {
  display: flex;
  gap: 12px;
  max-width: 800px;
  margin: 0 auto;
}

.chat-message.message-user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.message-content {
  flex: 1;
}

.message-sender {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}

.message-text {
  font-size: 15px;
  line-height: 1.6;
  color: #1a1a1a;
}

/* Markdown 样式 */
.message-text :deep(h1),
.message-text :deep(h2),
.message-text :deep(h3),
.message-text :deep(h4),
.message-text :deep(h5),
.message-text :deep(h6) {
  margin: 16px 0 8px;
  font-weight: 600;
}

.message-text :deep(h1) { font-size: 24px; }
.message-text :deep(h2) { font-size: 20px; }
.message-text :deep(h3) { font-size: 18px; }

.message-text :deep(p) {
  margin: 8px 0;
}

.message-text :deep(code) {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
}

.message-text :deep(pre) {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
}

.message-text :deep(pre code) {
  background: transparent;
  padding: 0;
}

.message-text :deep(ul),
.message-text :deep(ol) {
  margin: 8px 0;
  padding-left: 24px;
}

.message-text :deep(li) {
  margin: 4px 0;
}

.message-text :deep(blockquote) {
  border-left: 4px solid #e5e5e5;
  padding-left: 16px;
  margin: 12px 0;
  color: #666;
}

.message-text :deep(a) {
  color: #1890ff;
  text-decoration: none;
}

.message-text :deep(a:hover) {
  text-decoration: underline;
}

.message-text :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
}

.message-text :deep(th),
.message-text :deep(td) {
  border: 1px solid #e5e5e5;
  padding: 8px 12px;
  text-align: left;
}

.message-text :deep(th) {
  background: #f5f5f5;
  font-weight: 600;
}
</style>