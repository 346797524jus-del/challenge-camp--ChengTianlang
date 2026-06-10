<template>
  <div class="chat-message" :class="{ 'user-message': isUser, 'ai-message': !isUser }">
    <div class="message-avatar">
      <div class="avatar" :class="{ 'user-avatar': isUser, 'ai-avatar': !isUser }" :title="isUser ? userName || '我' : 'AI'" :style="isUser && avatarColor ? { background: avatarColor } : null">
        {{ isUser ? (userName ? userName.charAt(0) : '我') : 'AI' }}
      </div>
    </div>
    <div class="message-content">
      <div class="message-bubble">
        <pre v-if="isUser" class="message-text">{{ message }}</pre>
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
    message: { type: String, required: true },
    isUser: { type: Boolean, default: false },
    timestamp: { type: Date, default: () => new Date() },
    userName: { type: String, default: '' },
    avatarColor: { type: String, default: '' }
  },
  computed: {
    renderedMessage() {
      if (this.isUser) return this.message
      marked.setOptions({ breaks: true, gfm: true, sanitize: false })
      return marked(this.message)
    }
  },
  methods: { formatTime }
}
</script>

<style scoped>
.chat-message { display: flex; margin-bottom: 16px; padding: 0 4px; align-items: flex-end; animation: fadeInUp 0.3s ease; }
@keyframes fadeInUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.user-message { justify-content: flex-end; }
.user-message .message-avatar { order: 2; }
.user-message .message-content { order: 1; }
.ai-message { justify-content: flex-start; }
.message-avatar { display: flex; align-items: flex-start; margin: 0 10px; }
.avatar { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; color: white; flex-shrink: 0; }
.user-avatar { background: var(--user-avatar-color, var(--accent, #0b74ff)); }
.ai-avatar { background: linear-gradient(135deg, #6366f1, #8b5cf6); }
.message-content { max-width: 75%; min-width: 100px; }
.message-bubble { padding: 12px 16px; border-radius: var(--radius-md, 12px); word-wrap: break-word; word-break: break-word; box-shadow: var(--shadow-sm, 0 1px 2px rgba(0,0,0,0.05)); }
.user-message .message-bubble { background: linear-gradient(135deg, var(--accent, #0b74ff), #6366f1); color: white; border-bottom-right-radius: 4px; }
.ai-message .message-bubble { background: var(--bg-tertiary, #f8fafc); color: var(--text-primary, #111827); border-bottom-left-radius: 4px; }
.message-text { font-size: 14px; line-height: 1.5; white-space: pre-wrap; margin: 0; }
.message-markdown { font-size: 14px; line-height: 1.7; }
.message-markdown code { background: rgba(0,0,0,0.06); padding: 0.15em 0.35em; border-radius: 4px; font-size: 13px; }
.message-markdown pre { background: #1e293b; color: #e2e8f0; padding: 12px 16px; border-radius: var(--radius-sm, 8px); overflow-x: auto; margin: 8px 0; }
.message-markdown pre code { background: transparent; padding: 0; color: inherit; }
.message-markdown table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 13px; }
.message-markdown th, .message-markdown td { border: 1px solid var(--border-color, #e2e8f0); padding: 8px 12px; text-align: left; }
.message-markdown th { background: var(--accent-light, #eef2ff); font-weight: 600; }
.message-markdown blockquote { border-left: 3px solid var(--accent, #0b74ff); padding-left: 12px; margin: 8px 0; color: var(--text-secondary, #64748b); }
.message-time { font-size: 12px; color: var(--text-muted, #9ca3af); margin-top: 6px; }
.user-message .message-time { text-align: right; }
.ai-message .message-time { text-align: left; }
@media (max-width:768px) { .message-content { max-width: 86%; } }
</style>
