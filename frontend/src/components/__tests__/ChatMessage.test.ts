"""
前端组件测试示例
"""

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatMessage from '@/components/ChatMessage.vue'

describe('ChatMessage', () => {
  it('正确渲染用户消息', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        message: {
          role: 'user',
          content: '你好',
        },
      },
    })

    expect(wrapper.find('.message-user').exists()).toBe(true)
    expect(wrapper.text()).toContain('你好')
  })

  it('正确渲染助手消息', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        message: {
          role: 'assistant',
          content: '你好！有什么我可以帮助你的吗？',
        },
      },
    })

    expect(wrapper.find('.message-assistant').exists()).toBe(true)
    expect(wrapper.text()).toContain('你好')
  })

  it('正确渲染 Markdown 内容', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        message: {
          role: 'assistant',
          content: '# 标题\n\n这是一段**加粗**文本。',
        },
      },
    })

    const content = wrapper.find('.message-text')
    expect(content.html()).toContain('<h1>')
    expect(content.html()).toContain('<strong>')
  })
})