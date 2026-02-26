<template>
  <div class="debug-panel">
    <div class="debug-header">
      <h3>🔍 调试信息</h3>
      <button class="close-button" @click="$emit('close')">×</button>
    </div>
    <div class="debug-content">
      <div v-if="debugInfo.length === 0" class="empty-debug">
        暂无调试信息
      </div>
      <div v-else class="debug-list">
        <div
          v-for="(item, index) in debugInfo"
          :key="index"
          class="debug-item"
          @click="expandedIndex = expandedIndex === index ? -1 : index"
        >
          <div class="debug-item-header">
            <span class="debug-icon">{{ getDebugIcon(item) }}</span>
            <span class="debug-title">{{ getDebugTitle(item) }}</span>
            <span class="debug-arrow">{{ expandedIndex === index ? '▼' : '▶' }}</span>
          </div>
          <div v-if="expandedIndex === index" class="debug-item-content">
            <div v-if="item.tool_calls" class="tool-calls">
              <div class="section-title">工具调用:</div>
              <pre>{{ JSON.stringify(item.tool_calls, null, 2) }}</pre>
            </div>
            <div class="section-title">内容:</div>
            <pre>{{ item.content }}</pre>
          </div>
        </div>
      </div>
    </div>
    <div class="debug-footer">
      <button class="clear-button" @click="$emit('clear')">清除调试信息</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { DebugInfo } from '@/types'

defineEmits<{
  (e: 'close'): void
  (e: 'clear'): void
}>()

defineProps<{
  debugInfo: DebugInfo[]
}>()

const expandedIndex = ref(-1)

function getDebugIcon(item: DebugInfo): string {
  switch (item.message_type) {
    case 'HumanMessage':
      return '👤'
    case 'AIMessage':
      return '🤖'
    case 'ToolMessage':
      return '🔧'
    default:
      return '📝'
  }
}

function getDebugTitle(item: DebugInfo): string {
  const role = item.message_type || 'Unknown'
  let title = `${role}`

  if (item.tool_calls && item.tool_calls.length > 0) {
    const toolNames = item.tool_calls.map((t) => t.name).join(', ')
    title += ` (工具: ${toolNames})`
  }

  if (item.node) {
    title += ` - ${item.node}`
  }

  return title
}
</script>

<style scoped>
.debug-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f5f5;
}

.debug-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid #e5e5e5;
}

.debug-header h3 {
  font-size: 14px;
  font-weight: 600;
  margin: 0;
}

.close-button {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: #666;
  font-size: 18px;
  cursor: pointer;
  border-radius: 4px;
}

.close-button:hover {
  background: rgba(0, 0, 0, 0.04);
}

.debug-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.empty-debug {
  padding: 24px;
  text-align: center;
  color: #999;
  font-size: 14px;
}

.debug-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.debug-item {
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
}

.debug-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  font-size: 13px;
}

.debug-icon {
  font-size: 16px;
}

.debug-title {
  flex: 1;
  color: #1a1a1a;
}

.debug-arrow {
  color: #999;
  font-size: 10px;
}

.debug-item-content {
  padding: 0 12px 12px;
  border-top: 1px solid #f0f0f0;
}

.section-title {
  font-size: 11px;
  font-weight: 600;
  color: #666;
  margin: 8px 0 4px;
}

.debug-item-content pre {
  background: #f5f5f5;
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.tool-calls {
  margin-bottom: 8px;
}

.debug-footer {
  padding: 12px 16px;
  border-top: 1px solid #e5e5e5;
}

.clear-button {
  width: 100%;
  padding: 8px;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  background: #fff;
  color: #666;
  font-size: 13px;
  cursor: pointer;
}

.clear-button:hover {
  background: #f0f0f0;
}
</style>