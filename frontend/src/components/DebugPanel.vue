<template>
  <div class="debug-panel">
    <div class="debug-header">
      <h3>🔍 调试信息</h3>
      <el-button text size="small" @click="$emit('close')">
        <el-icon><Close /></el-icon>
      </el-button>
    </div>
    <div class="debug-content">
      <div v-if="debugInfo.length === 0" class="empty-debug">
        暂无调试信息
      </div>
      <el-collapse v-else class="debug-list">
        <el-collapse-item
          v-for="(item, index) in debugInfo"
          :key="index"
          :name="index"
        >
          <template #title>
            <div class="debug-item-header">
              <span class="debug-icon">{{ getDebugIcon(item) }}</span>
              <span class="debug-title">{{ getDebugTitle(item) }}</span>
            </div>
          </template>
          <div class="debug-item-content">
            <div v-if="item.tool_calls" class="tool-calls">
              <div class="section-title">工具调用:</div>
              <pre>{{ JSON.stringify(item.tool_calls, null, 2) }}</pre>
            </div>
            <div class="section-title">内容:</div>
            <pre>{{ item.content }}</pre>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>
    <div class="debug-footer">
      <el-button type="warning" size="small" @click="$emit('clear')">
        <el-icon><Delete /></el-icon>
        清除调试信息
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DebugInfo } from '@/types'
import { Close, Delete } from '@element-plus/icons-vue'

defineEmits<{
  (e: 'close'): void
  (e: 'clear'): void
}>()

defineProps<{
  debugInfo: DebugInfo[]
}>()

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
  background: var(--el-bg-color-page);
}

.debug-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color);
}

.debug-header h3 {
  font-size: 14px;
  font-weight: 600;
  margin: 0;
  color: var(--el-text-color-primary);
}

.debug-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.empty-debug {
  padding: 24px;
  text-align: center;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.debug-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.debug-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--el-text-color-primary);
}

.debug-icon {
  font-size: 16px;
}

.debug-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.debug-item-content {
  padding: 0 12px 12px;
  border-top: 1px solid var(--el-border-color-lighter);
  margin-top: 8px;
}

.section-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
  margin: 8px 0 4px;
}

.debug-item-content pre {
  background: var(--el-fill-color-light);
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--el-text-color-primary);
}

.tool-calls {
  margin-bottom: 8px;
}

.debug-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--el-border-color);
}
</style>