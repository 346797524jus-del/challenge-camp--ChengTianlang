<template>
  <div class="chat-message" :class="{ 'user-message': isUser, 'ai-message': !isUser }">
    <div class="message-avatar">
      <div class="avatar" :class="{ 'user-avatar': isUser, 'ai-avatar': !isUser }" :title="isUser ? userName || '我' : 'AI'" :style="isUser && avatarColor ? { background: avatarColor } : null">
          {{ isUser ? (userName ? userName.charAt(0) : '我') : 'AI' }}
        </div>
    </div>
    <div class="message-content">
      <div class="message-bubble">
        <!-- 用户消息使用普通文本 -->
        <pre v-if="isUser" class="message-text">{{ message }}</pre>
        <!-- AI回复使用Markdown渲染 -->
        <div v-else class="message-markdown" v-html="renderedMessage"></div>
      </div>
      <div class="message-time">{{ formatTime(timestamp) }}</div>
    </div>
  </div>
</template>

<script>
import { formatTime } from '../utils/index.js'
import { marked } from 'marked'

export default {
  name: 'ChatMessage',
  props: {
    message: {
      type: String,
      required: true
    },
    isUser: {
      type: Boolean,
      default: false
    },
    timestamp: {
      type: Date,
      default: () => new Date()
    }
    ,
    userName: {
      type: String,
      default: ''
    }
    ,
    avatarColor: {
      type: String,
      default: ''
    }
  },
  computed: {
    renderedMessage() {
      if (this.isUser) {
        return this.message
      }
      // 配置marked选项
      marked.setOptions({
        breaks: true, // 支持换行
        gfm: true, // 支持GitHub风格的Markdown
        sanitize: false, // 不过滤HTML（根据需要可以开启）
        highlight: function(code, lang) {
          // 可以在这里添加代码高亮功能
          return code
        }
      })
      return marked(this.message)
    }
  },
  methods: {
    formatTime
  }
}
</script>

<style scoped>
.chat-message { display:flex; margin-bottom:12px; padding:0 8px; align-items:flex-end }

.user-message { justify-content:flex-end }
.user-message .message-avatar { order:2 }
.user-message .message-content { order:1 }

.ai-message { justify-content:flex-start }
.ai-message .message-avatar { order:1 }
.ai-message .message-content { order:2 }

.message-avatar { display:flex; align-items:flex-start; margin:0 8px }

.avatar { width:36px; height:36px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:700; color:#fff }
.user-avatar { background: var(--user-avatar-color, #0b74ff) }
.ai-avatar { background:#6c757d }

.message-content { max-width:72%; min-width:110px }

.message-bubble { padding:10px 14px; border-radius:12px; word-wrap:break-word; word-break:break-word; box-shadow: 0 1px 0 rgba(0,0,0,0.02) }
.user-message .message-bubble { background: linear-gradient(90deg,#0966ff,#007bff); color:#fff }
.ai-message .message-bubble { background:#f8fafc; color:#111827 }

.message-text { font-size:14px; line-height:1.5; white-space:pre-wrap; margin:0 }

.message-markdown { font-size:14px; line-height:1.6 }
.message-markdown code { background: rgba(0,0,0,0.06); padding:0.15em 0.35em; border-radius:4px }
.message-markdown pre { background: rgba(0,0,0,0.06); padding:0.8em; border-radius:6px; overflow:auto }

.message-time { font-size:12px; color:#9ca3af; margin-top:6px }
.user-message .message-time { text-align:right }
.ai-message .message-time { text-align:left }

@media (max-width:768px) { .message-content { max-width:86% } }
</style>