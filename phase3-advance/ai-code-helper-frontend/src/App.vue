<template>
  <div :class="['app', theme === 'dark' ? 'theme-dark' : '']">
    <!-- 顶部导航栏 -->
    <header class="app-header">
      <div class="header-left">
        <div class="app-logo">
          <span class="logo-icon">🤖</span>
          <div class="logo-text">
            <h1 class="app-title">AI 智能助手</h1>
            <span class="app-subtitle">WPS文件生成 · 项目扫描清洗 · 智能检索</span>
          </div>
        </div>
      </div>
      <div class="header-right">
        <div class="mode-switch" @click="toggleMode" :title="isAgentMode ? '切换到普通对话模式' : '切换到智能体模式'">
          <span class="mode-option" :class="{ active: isAgentMode }">🤖 智能体</span>
          <span class="mode-option" :class="{ active: !isAgentMode }">💬 对话</span>
          <div class="mode-slider" :style="{ left: isAgentMode ? '2px' : '50%' }"></div>
        </div>
        <button class="icon-btn" v-if="isAgentMode" @click="handleNewSession" title="新建会话（清除短时记忆）" :disabled="isAiTyping" style="font-size:16px">
          🆕
        </button>
        <button class="icon-btn settings-btn" @click="showSettings = true" title="设置">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
        </button>
      </div>
    </header>

    <!-- 主聊天区域 -->
    <main class="chat-container">
      <!-- 消息列表 -->
      <div class="messages-container" ref="messagesContainer">
        <!-- 欢迎消息 -->
        <div v-if="messages.length === 0 && !isAiTyping" class="welcome-message">
          <div class="welcome-content">
            <div class="welcome-icon">{{ isAgentMode ? '🤖' : '💬' }}</div>
            <h2>{{ isAgentMode ? '欢迎使用 AI 智能助手' : '欢迎使用 AI 编程小助手' }}</h2>
            <p class="welcome-desc">{{ isAgentMode ? '我可以帮您生成WPS文档、扫描项目、清洗数据、合并文件、搜索面试题' : '我可以帮助您解答编程问题，提供代码示例' }}</p>
            <div v-if="isAgentMode" class="feature-cards">
              <div class="feature-card" @click="quickSend('帮我生成一份Java学习计划')">
                <span class="feature-icon">📊</span>
                <span class="feature-text">生成学习计划</span>
              </div>
              <div class="feature-card" @click="quickSend('帮我生成一份个人简历，姓名张三，计算机专业应届生')">
                <span class="feature-icon">📄</span>
                <span class="feature-text">生成简历文档</span>
              </div>
              <div class="feature-card" @click="quickSend('帮我生成一个项目汇报PPT，主题是AI智能助手开发')">
                <span class="feature-icon">📽️</span>
                <span class="feature-text">生成PPT演示</span>
              </div>
              <div class="feature-card" @click="quickSend('搜索Java面试题')">
                <span class="feature-icon">🔍</span>
                <span class="feature-text">搜索面试题</span>
              </div>
              <div class="feature-card" @click="quickSend('扫描当前项目的文件结构')">
                <span class="feature-icon">📂</span>
                <span class="feature-text">扫描项目结构</span>
              </div>
              <div class="feature-card" @click="quickSend('帮我清洗项目中的数据文件')">
                <span class="feature-icon">🧹</span>
                <span class="feature-text">数据清洗</span>
              </div>
              <div class="feature-card" @click="quickSend('帮我合并所有CSV文件')">
                <span class="feature-icon">🔗</span>
                <span class="feature-text">文件合并</span>
              </div>
              <div class="feature-card" @click="quickSend('深度分析这个项目的代码构成')">
                <span class="feature-icon">🔬</span>
                <span class="feature-text">深度分析</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 历史消息 -->
        <ChatMessage
          v-for="message in messages"
          :key="message.id"
          :message="message.content"
          :is-user="message.isUser"
          :timestamp="message.timestamp"
          :user-name="message.userName"
          :avatar-color="message.avatarColor"
        />

        <!-- AI 正在回复 -->
        <div v-if="isAiTyping" class="chat-message ai-message">
          <div class="message-avatar">
            <div class="avatar ai-avatar">AI</div>
          </div>
          <div class="message-content">
            <div class="message-bubble">
              <div class="ai-typing-content">
                <div class="ai-response-text message-markdown" v-html="currentAiResponseRendered"></div>
                <LoadingDots v-if="isStreaming" />
              </div>
            </div>
          </div>
        </div>

        <!-- 智能体思考过程 -->
        <AgentThoughtProcess 
          v-if="isAgentMode && agentSteps.length > 0"
          :steps="agentSteps"
        />
      </div>

      <!-- 文件管理面板 -->
      <FileManager 
        v-if="isAgentMode"
        :refresh-trigger="fileRefreshTrigger"
        :theme="theme"
        @preview="openPreview"
      />

      <!-- 输入区域 -->
      <div class="input-area">
        <div class="input-container">
          <textarea
            ref="inputRef"
            v-model="inputMessage"
            :placeholder="inputPlaceholder"
            :disabled="isAiTyping"
            class="input-textarea"
            rows="1"
            @keydown="handleKeyDown"
            @input="adjustHeight"
          />
          <button
            :disabled="isAiTyping || !inputMessage.trim()"
            @click="sendMessage"
            class="send-button"
            :title="isAiTyping ? 'AI 正在回复...' : '发送消息'"
          >
            <svg v-if="!isAiTyping" width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M2 21l21-9L2 3v7l15 2-15 2v7z" fill="currentColor"/>
            </svg>
            <div v-else class="sending-spinner"></div>
          </button>
        </div>
      </div>
    </main>

    <!-- 设置弹窗 -->
    <Teleport to="body">
      <div v-if="showSettings" class="modal-overlay" @click.self="showSettings = false">
        <div class="settings-modal">
          <div class="modal-header">
            <h3>⚙️ 用户设置</h3>
            <button class="modal-close" @click="showSettings = false">✕</button>
          </div>
          <div class="modal-body">
            <div class="setting-group">
              <label class="setting-label">用户名</label>
              <input v-model="userName" placeholder="输入你的名字" class="setting-input" />
            </div>
            <div class="setting-group">
              <label class="setting-label">头像颜色</label>
              <div class="color-picker">
                <button v-for="c in avatarColors" :key="c" :style="{ background: c }" :class="['color-swatch', { selected: avatarColor === c }]" @click="avatarColor = c"></button>
              </div>
            </div>
            <div class="setting-group">
              <label class="setting-label">主题模式</label>
              <div class="theme-toggle">
                <button :class="['theme-btn', { active: theme === 'light' }]" @click="theme = 'light'">☀️ 浅色</button>
                <button :class="['theme-btn', { active: theme === 'dark' }]" @click="theme = 'dark'">🌙 深色</button>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button @click="saveSettings" class="btn-primary">保存设置</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 文件预览弹窗 -->
    <FilePreview
      v-if="previewFile"
      :file-name="previewFile.name"
      :file-type="previewFile.type"
      @close="previewFile = null"
    />

    <!-- 连接错误提示 -->
    <Transition name="slide-down">
      <div v-if="connectionError" class="connection-error">
        <span class="error-icon">⚠️</span>
        <span>连接服务器失败，请检查后端服务是否启动</span>
        <button class="error-close" @click="connectionError = false">✕</button>
      </div>
    </Transition>
  </div>
</template>

<script>
import ChatMessage from './components/ChatMessage.vue'
import LoadingDots from './components/LoadingDots.vue'
import AgentThoughtProcess from './components/AgentThoughtProcess.vue'
import FilePreview from './components/FilePreview.vue'
import FileManager from './components/FileManager.vue'
import { chatWithAgent, clearMemory } from './api/agentApi.js'
import { generateMemoryId } from './utils/index.js'
import { marked } from 'marked'

export default {
  name: 'App',
  components: {
    ChatMessage,
    LoadingDots,
    AgentThoughtProcess,
    FilePreview,
    FileManager
  },
  data() {
    return {
      messages: [],
      memoryId: null,
      isAiTyping: false,
      isStreaming: false,
      currentAiResponse: '',
      connectionError: false,
      isAgentMode: true,
      agentSteps: [],
      fileRefreshTrigger: 0,
      previewFile: null,
      showSettings: false,
      userName: '',
      theme: 'light',
      avatarColor: '#0b74ff',
      avatarColors: ['#0b74ff', '#6366f1', '#8b5cf6', '#ec4899', '#ef4444', '#f59e0b', '#10b981', '#14b8a6'],
      inputMessage: '',
      showClearConfirm: false
    }
  },
  computed: {
    currentAiResponseRendered() {
      if (!this.currentAiResponse) return ''
      marked.setOptions({ breaks: true, gfm: true, sanitize: false })
      return marked(this.currentAiResponse)
    },
    inputPlaceholder() {
      const prefix = this.userName ? this.userName + '，' : ''
      if (this.isAgentMode) {
        return prefix + '请输入您的问题，我可以生成文档、扫描项目、清洗数据...'
      }
      return prefix + '请输入您的编程问题...'
    }
  },
  watch: {
    avatarColor(newColor) {
      document.documentElement.style.setProperty('--user-avatar-color', newColor)
    },
    theme(newTheme) {
      document.documentElement.setAttribute('data-theme', newTheme)
    }
  },
  methods: {
    toggleMode() {
      this.isAgentMode = !this.isAgentMode
      this.messages = []
      this.agentSteps = []
      this.currentAiResponse = ''
      this.isAiTyping = false
      this.isStreaming = false
    },
    quickSend(text) {
      this.inputMessage = text
      this.sendMessage()
    },
    async handleNewSession() {
      this.messages = []
      this.agentSteps = []
      this.currentAiResponse = ''
      this.isAiTyping = false
      this.isStreaming = false
      try {
        await clearMemory()
      } catch (e) {
        // 清除失败不影响
      }
      this.scrollToBottom()
    },
    sendMessage() {
      if (!this.inputMessage.trim() || this.isAiTyping) return
      const message = this.inputMessage.trim()
      this.inputMessage = ''
      this.adjustHeight()
      this.addMessage(message, true)
      if (this.isAgentMode) {
        this.startAgentResponse(message)
      }
    },
    async startAgentResponse(userMessage) {
      this.isAiTyping = true
      this.isStreaming = true
      this.agentSteps = []
      this.currentAiResponse = ''
      this.connectionError = false
      try {
        const response = await chatWithAgent(userMessage)
        if (response.steps) this.agentSteps = response.steps
        if (response.finalAnswer) this.currentAiResponse = response.finalAnswer
        if (response.generatedFiles && response.generatedFiles.length > 0) {
          let html = '\n\n---\n\n### 📁 生成的文件\n\n'
          response.generatedFiles.forEach((fp) => {
            const fn = fp.split('\\').pop() || fp.split('/').pop()
            const ext = fn.split('.').pop().toLowerCase()
            const emoji = ext === 'docx' ? '📄' : ext === 'xlsx' ? '📊' : ext === 'pptx' ? '📽️' : '📁'
            html += `<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px;margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;">
              <span>${emoji} <strong>${fn}</strong></span>
              <span style="display:flex;gap:8px;">
                <a href="/api/files/${encodeURIComponent(fn)}" download style="padding:4px 12px;background:#0b74ff;color:white;border-radius:4px;text-decoration:none;font-size:12px;">⬇️ 下载</a>
                <button data-preview="${fn}" data-ext="${ext}" style="padding:4px 12px;background:#10b981;color:white;border:none;border-radius:4px;cursor:pointer;font-size:12px;">👁️ 预览</button>
              </span>
            </div>`
          })
          this.currentAiResponse += html
          this.fileRefreshTrigger++
        }
        await this.$nextTick()
        this.finishAiResponse()
      } catch (error) {
        console.error('智能体响应出错:', error)
        this.currentAiResponse = '抱歉，智能体处理请求时出现错误。请检查后端服务是否正常运行。'
        this.connectionError = true
        setTimeout(() => { this.connectionError = false }, 5000)
        this.finishAiResponse()
      }
    },
    finishAiResponse() {
      this.isStreaming = false
      if (this.currentAiResponse.trim()) {
        this.addMessage(this.currentAiResponse.trim(), false)
      }
      this.isAiTyping = false
      this.currentAiResponse = ''
    },
    addMessage(content, isUser = false) {
      this.messages.push({
        id: Date.now() + Math.random(),
        content,
        isUser,
        timestamp: new Date(),
        userName: isUser ? (this.userName || '我') : 'AI',
        avatarColor: isUser ? this.avatarColor : null
      })
      this.scrollToBottom()
    },
    scrollToBottom() {
      this.$nextTick(() => {
        const el = this.$refs.messagesContainer
        if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
      })
    },
    handleKeyDown(e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.sendMessage() }
    },
    adjustHeight() {
      this.$nextTick(() => {
        const ta = this.$refs.inputRef
        if (ta) { ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight, 120) + 'px' }
      })
    },
    openPreview(file) {
      this.previewFile = { name: file.name, type: file.type }
    },
    saveSettings() {
      localStorage.setItem('aich_userName', this.userName)
      localStorage.setItem('aich_theme', this.theme)
      localStorage.setItem('aich_avatarColor', this.avatarColor)
      this.showSettings = false
      document.documentElement.style.setProperty('--user-avatar-color', this.avatarColor)
    },
    loadSettings() {
      const n = localStorage.getItem('aich_userName')
      const t = localStorage.getItem('aich_theme')
      const c = localStorage.getItem('aich_avatarColor')
      if (n) this.userName = n
      if (t) this.theme = t
      if (c) this.avatarColor = c
      document.documentElement.style.setProperty('--user-avatar-color', this.avatarColor)
      document.documentElement.setAttribute('data-theme', this.theme)
    }
  },
  mounted() {
    this.memoryId = generateMemoryId()
    this.loadSettings()
    window.__openPreview = (fn, ft) => { this.previewFile = { name: fn, type: ft } }
  },
  beforeUnmount() { delete window.__openPreview }
}
</script>

<style>
:root {
  --bg-primary: #f0f2f5;
  --bg-secondary: #ffffff;
  --bg-tertiary: #f8fafc;
  --text-primary: #1e293b;
  --text-secondary: #64748b;
  --text-muted: #94a3b8;
  --border-color: #e2e8f0;
  --accent: #0b74ff;
  --accent-hover: #0056d6;
  --accent-light: #eef2ff;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
  --shadow-lg: 0 8px 30px rgba(0,0,0,0.12);
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --transition: all 0.2s ease;
}
[data-theme="dark"] {
  --bg-primary: #0b1120;
  --bg-secondary: #0f172a;
  --bg-tertiary: #1e293b;
  --text-primary: #e2e8f0;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --border-color: #1e293b;
  --accent: #3b82f6;
  --accent-hover: #60a5fa;
  --accent-light: #1e3a5f;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.2);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.3);
  --shadow-lg: 0 8px 30px rgba(0,0,0,0.4);
}
</style>

<style scoped>
.app { height: 100vh; display: flex; flex-direction: column; background: var(--bg-primary); color: var(--text-primary); transition: var(--transition); }

/* 顶部导航栏 */
.app-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 24px; background: var(--bg-secondary); border-bottom: 1px solid var(--border-color); box-shadow: var(--shadow-sm); z-index: 100; }
.header-left { display: flex; align-items: center; }
.app-logo { display: flex; align-items: center; gap: 12px; }
.logo-icon { font-size: 32px; line-height: 1; }
.logo-text { display: flex; flex-direction: column; }
.app-title { font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0; line-height: 1.3; }
.app-subtitle { font-size: 12px; color: var(--text-muted); line-height: 1.3; }
.header-right { display: flex; align-items: center; gap: 12px; }

/* 模式切换 */
.mode-switch { position: relative; display: flex; background: var(--bg-tertiary); border-radius: var(--radius-sm); padding: 2px; cursor: pointer; border: 1px solid var(--border-color); overflow: hidden; }
.mode-option { position: relative; z-index: 1; padding: 6px 14px; font-size: 13px; font-weight: 500; color: var(--text-muted); transition: var(--transition); white-space: nowrap; }
.mode-option.active { color: white; }
.mode-slider { position: absolute; top: 2px; width: calc(50% - 2px); height: calc(100% - 4px); background: var(--accent); border-radius: 6px; transition: left 0.25s cubic-bezier(0.4,0,0.2,1); z-index: 0; }

.icon-btn { width: 36px; height: 36px; border: 1px solid var(--border-color); background: var(--bg-secondary); border-radius: var(--radius-sm); cursor: pointer; display: flex; align-items: center; justify-content: center; color: var(--text-secondary); transition: var(--transition); }
.icon-btn:hover:not(:disabled) { background: var(--bg-tertiary); color: var(--accent); border-color: var(--accent); }
.icon-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* 聊天区域 */
.chat-container { flex: 1; display: flex; flex-direction: column; max-width: 960px; width: 100%; margin: 0 auto; padding: 16px; overflow: hidden; }
.messages-container { flex: 1; overflow-y: auto; background: var(--bg-secondary); border-radius: var(--radius-lg); box-shadow: var(--shadow-md); padding: 24px; margin-bottom: 12px; scroll-behavior: smooth; }
.messages-container::-webkit-scrollbar { width: 6px; }
.messages-container::-webkit-scrollbar-track { background: transparent; }
.messages-container::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 3px; }
.messages-container::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

/* 欢迎消息 */
.welcome-message { display: flex; justify-content: center; align-items: center; min-height: 300px; padding: 20px; }
.welcome-content { text-align: center; max-width: 680px; }
.welcome-icon { font-size: 56px; margin-bottom: 16px; animation: float 3s ease-in-out infinite; }
@keyframes float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
.welcome-content h2 { font-size: 22px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary); }
.welcome-desc { font-size: 14px; color: var(--text-secondary); margin-bottom: 24px; line-height: 1.6; }
.feature-cards { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; max-width: 480px; margin: 0 auto; }
.feature-card { display: flex; align-items: center; gap: 10px; padding: 14px 16px; background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: var(--radius-md); cursor: pointer; transition: var(--transition); }
.feature-card:hover { border-color: var(--accent); background: var(--accent-light); transform: translateY(-2px); box-shadow: var(--shadow-md); }
.feature-icon { font-size: 24px; }
.feature-text { font-size: 13px; font-weight: 500; color: var(--text-primary); }

/* 消息 */
.chat-message { display: flex; margin-bottom: 16px; padding: 0 4px; align-items: flex-end; animation: fadeInUp 0.3s ease; }
@keyframes fadeInUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.user-message { justify-content: flex-end; }
.user-message .message-avatar { order: 2; }
.user-message .message-content { order: 1; }
.ai-message { justify-content: flex-start; }
.message-avatar { display: flex; align-items: flex-start; margin: 0 10px; }
.avatar { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; color: white; flex-shrink: 0; }
.user-avatar { background: var(--user-avatar-color, var(--accent)); }
.ai-avatar { background: linear-gradient(135deg, #6366f1, #8b5cf6); }
.message-content { max-width: 75%; min-width: 100px; }
.message-bubble { padding: 12px 16px; border-radius: var(--radius-md); word-wrap: break-word; word-break: break-word; box-shadow: var(--shadow-sm); }
.user-message .message-bubble { background: linear-gradient(135deg, var(--accent), #6366f1); color: white; border-bottom-right-radius: 4px; }
.ai-message .message-bubble { background: var(--bg-tertiary); color: var(--text-primary); border-bottom-left-radius: 4px; }
.ai-typing-content { display: flex; flex-direction: column; gap: 8px; }
.ai-response-text { font-size: 14px; line-height: 1.7; }
.ai-response-text.message-markdown h1,.ai-response-text.message-markdown h2,.ai-response-text.message-markdown h3 { margin: 0.6em 0 0.3em; color: var(--text-primary); }
.ai-response-text.message-markdown h1 { font-size: 20px; }
.ai-response-text.message-markdown h2 { font-size: 17px; }
.ai-response-text.message-markdown h3 { font-size: 15px; }
.ai-response-text.message-markdown p { margin: 0.4em 0; }
.ai-response-text.message-markdown code { background: rgba(0,0,0,0.06); padding: 0.15em 0.35em; border-radius: 4px; font-size: 13px; }
.ai-response-text.message-markdown pre { background: #1e293b; color: #e2e8f0; padding: 12px 16px; border-radius: var(--radius-sm); overflow-x: auto; margin: 8px 0; }
.ai-response-text.message-markdown pre code { background: transparent; padding: 0; color: inherit; }
.ai-response-text.message-markdown ul,.ai-response-text.message-markdown ol { padding-left: 20px; margin: 0.4em 0; }
.ai-response-text.message-markdown li { margin-bottom: 4px; }
.ai-response-text.message-markdown table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 13px; }
.ai-response-text.message-markdown th,.ai-response-text.message-markdown td { border: 1px solid var(--border-color); padding: 8px 12px; text-align: left; }
.ai-response-text.message-markdown th { background: var(--accent-light); font-weight: 600; }
.ai-response-text.message-markdown blockquote { border-left: 3px solid var(--accent); padding-left: 12px; margin: 8px 0; color: var(--text-secondary); }

/* 输入区域 */
.input-area { padding: 8px 0; }
.input-container { display: flex; align-items: flex-end; gap: 10px; background: var(--bg-secondary); padding: 10px; border-radius: var(--radius-md); box-shadow: var(--shadow-md); border: 1px solid var(--border-color); transition: var(--transition); }
.input-container:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(11,116,255,0.1); }
.input-textarea { flex: 1; padding: 10px 14px; border: none; border-radius: var(--radius-sm); font-size: 14px; line-height: 1.5; resize: none; outline: none; background: transparent; color: var(--text-primary); min-height: 44px; max-height: 120px; overflow-y: auto; font-family: inherit; }
.input-textarea::placeholder { color: var(--text-muted); }
.input-textarea:disabled { opacity: 0.6; }
.send-button { width: 44px; height: 44px; background: linear-gradient(135deg, var(--accent), #6366f1); border: none; border-radius: var(--radius-sm); color: white; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: var(--transition); box-shadow: 0 4px 12px rgba(11,116,255,0.25); flex-shrink: 0; }
.send-button:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(11,116,255,0.35); }
.send-button:active:not(:disabled) { transform: translateY(0); }
.send-button:disabled { opacity: 0.5; cursor: not-allowed; box-shadow: none; }
.sending-spinner { width: 18px; height: 18px; border: 2px solid rgba(255,255,255,0.3); border-top-color: white; border-radius: 50%; animation: spin 0.6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* 设置弹窗 */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1500; backdrop-filter: blur(4px); }
.settings-modal { background: var(--bg-secondary); border-radius: var(--radius-lg); width: 380px; box-shadow: var(--shadow-lg); overflow: hidden; }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--border-color); }
.modal-header h3 { font-size: 16px; font-weight: 600; color: var(--text-primary); margin: 0; }
.modal-close { width: 28px; height: 28px; border: none; background: transparent; border-radius: 6px; cursor: pointer; font-size: 16px; color: var(--text-muted); display: flex; align-items: center; justify-content: center; transition: var(--transition); }
.modal-close:hover { background: var(--bg-tertiary); color: var(--text-primary); }
.modal-body { padding: 20px; }
.setting-group { margin-bottom: 20px; }
.setting-label { display: block; font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px; }
.setting-input { width: 100%; padding: 10px 12px; border: 1px solid var(--border-color); border-radius: var(--radius-sm); font-size: 14px; outline: none; background: var(--bg-tertiary); color: var(--text-primary); transition: var(--transition); }
.setting-input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(11,116,255,0.1); }
.color-picker { display: flex; gap: 8px; flex-wrap: wrap; }
.color-swatch { width: 32px; height: 32px; border-radius: 8px; border: 2px solid transparent; cursor: pointer; transition: var(--transition); }
.color-swatch:hover { transform: scale(1.1); }
.color-swatch.selected { border-color: var(--text-primary); box-shadow: 0 0 0 2px var(--bg-secondary); }
.theme-toggle { display: flex; gap: 8px; }
.theme-btn { flex: 1; padding: 10px; border: 1px solid var(--border-color); border-radius: var(--radius-sm); background: var(--bg-tertiary); color: var(--text-secondary); cursor: pointer; font-size: 13px; transition: var(--transition); }
.theme-btn.active { border-color: var(--accent); background: var(--accent-light); color: var(--accent); font-weight: 600; }
.modal-footer { padding: 16px 20px; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end; }
.btn-primary { padding: 10px 24px; background: var(--accent); color: white; border: none; border-radius: var(--radius-sm); font-size: 14px; font-weight: 500; cursor: pointer; transition: var(--transition); }
.btn-primary:hover { background: var(--accent-hover); }

/* 连接错误 */
.connection-error { position: fixed; top: 16px; left: 50%; transform: translateX(-50%); background: #ef4444; color: white; padding: 12px 20px; border-radius: var(--radius-md); display: flex; align-items: center; gap: 8px; z-index: 2000; box-shadow: var(--shadow-lg); font-size: 14px; }
.error-close { background: transparent; border: none; color: white; cursor: pointer; font-size: 16px; padding: 0 4px; opacity: 0.8; }
.error-close:hover { opacity: 1; }
.slide-down-enter-active { animation: slideDown 0.3s ease; }
.slide-down-leave-active { animation: slideDown 0.3s ease reverse; }
@keyframes slideDown { from { transform: translateX(-50%) translateY(-100%); opacity: 0; } to { transform: translateX(-50%) translateY(0); opacity: 1; } }
</style>