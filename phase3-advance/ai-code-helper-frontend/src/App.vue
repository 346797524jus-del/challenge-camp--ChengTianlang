<template>
  <div :class="['app', theme === 'dark' ? 'theme-dark' : '']">
    <!-- 头部标题 -->
    <div class="app-header">
      <h1 class="app-title">AI 编程小助手</h1>
      <div class="app-subtitle">智能体模式 - 生成 WPS 文档并在线预览</div>
      <div class="header-actions">
        <button 
          class="mode-button" 
          :class="{ active: isAgentMode }"
          @click="toggleMode" 
          :title="isAgentMode ? '切换到普通模式' : '切换到智能体模式'"
        >
          {{ isAgentMode ? '🤖 智能体' : '💬 对话' }}
        </button>
        <button class="settings-button" @click="toggleSettings" title="设置">⚙️</button>
      </div>
    </div>

    <!-- 聊天区域 -->
    <div class="chat-container">
      <!-- 消息列表 -->
      <div class="messages-container" ref="messagesContainer">
        <!-- 欢迎消息（无历史消息时显示） -->
        <div v-if="messages.length === 0 && !isAiTyping" class="welcome-message">
          <div class="welcome-content">
            <div class="welcome-icon">{{ isAgentMode ? '🤖' : '🤖' }}</div>
            <h2>{{ isAgentMode ? '欢迎使用 AI 智能体' : '欢迎使用 AI 编程小助手' }}</h2>
            <p>{{ isAgentMode ? '我可以帮您：' : '我可以帮助您：' }}</p>
            <ul v-if="isAgentMode">
              <li>📄 生成 Word 文档（简历、报告、学习笔记）</li>
              <li>📊 生成 Excel 表格（学习计划、数据统计）</li>
              <li>📽️ 生成 PPT 演示文稿（项目汇报、知识分享）</li>
              <li>🔍 搜索面试题和编程知识</li>
              <li>💡 解答编程技术问题</li>
            </ul>
            <ul v-else>
              <li>解答编程技术问题</li>
              <li>提供代码示例和解释</li>
              <li>协助求职面试准备</li>
              <li>分享编程学习建议</li>
            </ul>
            <p>请随时向我提问吧！</p>
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

        <!-- AI 正在回复的消息 -->
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

        <!-- 智能体思考过程（显示在AI回复下方） -->
        <AgentThoughtProcess 
          v-if="isAgentMode && agentSteps.length > 0"
          :steps="agentSteps"
        />
      </div>

      <!-- 文件管理面板（智能体模式下，固定在输入框上方） -->
      <FileManager 
        v-if="isAgentMode"
        :refresh-trigger="fileRefreshTrigger"
        :theme="theme"
        @preview="openPreview"
      />

      <!-- 输入框 -->
      <ChatInput
        :disabled="isAiTyping"
        @send-message="sendMessage"
        :placeholder="inputPlaceholder"
      />
    </div>

    <!-- 设置弹窗 -->
    <div v-if="showSettings" class="settings-modal-overlay">
      <div class="settings-modal">
        <h3>用户设置</h3>
        <div class="setting-row">
          <label>用户名</label>
          <input v-model="userName" placeholder="输入你的名字，显示在头像上" />
        </div>
        <div class="setting-row">
          <label>头像颜色</label>
          <div class="color-preview" :style="{ background: avatarColor }"></div>
          <div class="color-list">
            <button
              v-for="c in avatarColors"
              :key="c"
              :style="{ background: c }"
              :class="['color-swatch', { selected: avatarColor === c }]"
              @click="avatarColor = c"
            ></button>
          </div>
        </div>
        <div class="setting-row">
          <label>主题</label>
          <select v-model="theme">
            <option value="light">浅色</option>
            <option value="dark">深色</option>
          </select>
        </div>
        <div class="settings-actions">
          <button @click="saveSettings" class="btn-primary">保存</button>
          <button @click="showSettings = false" class="btn-link">取消</button>
        </div>
      </div>
    </div>

    <!-- 文件预览弹窗 -->
    <FilePreview
      v-if="previewFile"
      :file-name="previewFile.name"
      :file-type="previewFile.type"
      @close="previewFile = null"
    />

    <div v-if="connectionError" class="connection-error">
      <div class="error-content">
        <span class="error-icon">⚠️</span>
        <span>连接服务器失败，请检查后端服务是否启动</span>
      </div>
    </div>
  </div>
</template>

<script>
import ChatMessage from './components/ChatMessage.vue'
import ChatInput from './components/ChatInput.vue'
import LoadingDots from './components/LoadingDots.vue'
import AgentThoughtProcess from './components/AgentThoughtProcess.vue'
import FilePreview from './components/FilePreview.vue'
import FileManager from './components/FileManager.vue'
import { chatWithSSE } from './api/chatApi.js'
import { chatWithAgent } from './api/agentApi.js'
import { generateMemoryId } from './utils/index.js'
import { marked } from 'marked'

export default {
  name: 'App',
  components: {
    ChatMessage,
    ChatInput,
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
      currentEventSource: null,
      connectionError: false,
      // 智能体模式
      isAgentMode: true, // 默认启用智能体模式
      agentSteps: [],
      fileRefreshTrigger: 0,
      // 文件预览
      previewFile: null,
      // personalization
      showSettings: false,
      userName: '',
      theme: 'light',
      avatarColor: '#0b74ff',
      avatarColors: ['#0b74ff', '#ff6b6b', '#6c757d', '#10b981', '#ef9a00']
    }
  },
  computed: {
    currentAiResponseRendered() {
      if (!this.currentAiResponse) return ''
      marked.setOptions({
        breaks: true,
        gfm: true,
        sanitize: false,
        highlight: function(code, lang) {
          return code
        }
      })
      let html = marked(this.currentAiResponse)
      return html
    },
    inputPlaceholder() {
      const prefix = this.userName ? this.userName + '，' : ''
      if (this.isAgentMode) {
        return prefix + '请输入您的问题，我可以生成文档、搜索面试题...'
      }
      return prefix + '请输入您的编程问题...'
    }
  },
  watch: {
    avatarColor(newColor) {
      document.documentElement.style.setProperty('--user-avatar-color', newColor)
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

    sendMessage(message) {
      // 添加用户消息
      this.addMessage(message, true)
      
      if (this.isAgentMode) {
        // 智能体模式
        this.startAgentResponse(message)
      } else {
        // 普通对话模式
        this.startAiResponse(message)
      }
    },

    // ===== 智能体模式 =====
    async startAgentResponse(userMessage) {
      this.isAiTyping = true
      this.isStreaming = true
      this.agentSteps = []
      this.currentAiResponse = ''
      this.connectionError = false

      try {
        const response = await chatWithAgent(userMessage)
        
        // 显示思考过程
        if (response.steps) {
          this.agentSteps = response.steps
        }
        
        // 显示最终答案
        if (response.finalAnswer) {
          this.currentAiResponse = response.finalAnswer
        }
        
        // 如果有生成的文件，添加文件下载和预览区域
        if (response.generatedFiles && response.generatedFiles.length > 0) {
          let fileLinksHtml = '\n\n---\n\n### 📁 生成的文件\n\n'
          response.generatedFiles.forEach((filePath, index) => {
            // 提取文件名
            const fileName = filePath.split('\\').pop() || filePath.split('/').pop()
            // 获取文件扩展名
            const ext = fileName.split('.').pop().toLowerCase()
            const fileType = ext === 'docx' ? 'Word' : ext === 'xlsx' ? 'Excel' : ext === 'pptx' ? 'PPT' : '文件'
            const emoji = ext === 'docx' ? '📄' : ext === 'xlsx' ? '📊' : ext === 'pptx' ? '📽️' : '📁'
            
            fileLinksHtml += `<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px;margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;">
              <span>${emoji} <strong>${fileName}</strong></span>
              <span style="display:flex;gap:8px;">
                <a href="/api/files/${encodeURIComponent(fileName)}" download style="padding:4px 12px;background:#0b74ff;color:white;border-radius:4px;text-decoration:none;font-size:12px;">⬇️ 下载</a>
                <button onclick="window.__openPreview('${fileName}', '${ext}')" style="padding:4px 12px;background:#10b981;color:white;border:none;border-radius:4px;cursor:pointer;font-size:12px;">👁️ 预览</button>
              </span>
            </div>`
          })
          this.currentAiResponse += fileLinksHtml
          
          // 刷新文件管理列表
          this.fileRefreshTrigger++
        }
        
        // 等待渲染完成
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

    // ===== 普通对话模式 =====
    startAiResponse(userMessage) {
      this.isAiTyping = true
      this.isStreaming = true
      this.currentAiResponse = ''
      this.connectionError = false
      
      if (this.currentEventSource) {
        this.currentEventSource.close()
      }

      this.currentEventSource = chatWithSSE(
        this.memoryId,
        userMessage,
        this.handleAiMessage,
        this.handleAiError,
        this.handleAiClose
      )
    },

    handleAiMessage(data) {
      this.currentAiResponse += data
      this.scrollToBottom()
    },

    handleAiError(error) {
      console.error('AI 回复出错:', error)
      if (!this.currentAiResponse.trim()) {
        this.connectionError = true
        setTimeout(() => { this.connectionError = false }, 5000)
      }
      this.finishAiResponse()
    },

    handleAiClose() {
      this.finishAiResponse()
    },

    finishAiResponse() {
      this.isStreaming = false
      if (this.currentAiResponse.trim()) {
        this.addMessage(this.currentAiResponse.trim(), false)
      }
      this.isAiTyping = false
      this.currentAiResponse = ''
      if (this.currentEventSource) {
        this.currentEventSource.close()
        this.currentEventSource = null
      }
    },

    addMessage(content, isUser = false) {
      const message = {
        id: Date.now() + Math.random(),
        content,
        isUser,
        timestamp: new Date(),
        userName: isUser ? (this.userName || '我') : 'AI',
        avatarColor: isUser ? this.avatarColor : null
      }
      this.messages.push(message)
      this.scrollToBottom()
    },

    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.messagesContainer
        if (container) {
          container.scrollTop = container.scrollHeight
        }
      })
    },

    initializeChat() {
      this.memoryId = generateMemoryId()
      console.log('聊天室ID:', this.memoryId)
    },

    toggleSettings() {
      this.showSettings = !this.showSettings
    },

    saveSettings() {
      localStorage.setItem('aich_userName', this.userName)
      localStorage.setItem('aich_theme', this.theme)
      localStorage.setItem('aich_avatarColor', this.avatarColor)
      this.showSettings = false
      document.documentElement.style.setProperty('--user-avatar-color', this.avatarColor)
    },

    loadSettings() {
      const name = localStorage.getItem('aich_userName')
      const theme = localStorage.getItem('aich_theme')
      const color = localStorage.getItem('aich_avatarColor')
      if (name) this.userName = name
      if (theme) this.theme = theme
      if (color) this.avatarColor = color
      document.documentElement.style.setProperty('--user-avatar-color', this.avatarColor)
    },

    openPreview(file) {
      this.previewFile = { name: file.name, type: file.type }
    }
  },
  mounted() {
    this.initializeChat()
    this.loadSettings()
    // 注册全局预览函数
    window.__openPreview = (fileName, fileType) => {
      this.previewFile = { name: fileName, type: fileType }
    }
  },
  
  beforeUnmount() {
    if (this.currentEventSource) {
      this.currentEventSource.close()
    }
    delete window.__openPreview
  }
}
</script>

<style scoped>
.app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg,#f7fafc 0%, #eef2f6 100%);
  font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial;
  color: #333;
}

.app-header {
  position: relative;
  background-color: #fff;
  padding: 18px 20px;
  border-bottom: 1px solid rgba(0,0,0,0.06);
  text-align: center;
  box-shadow: 0 1px 0 rgba(0,0,0,0.03);
}

.app-title { font-size: 20px; font-weight:700; color:#111827; margin:0 }
.app-subtitle { font-size:13px; color:#6b7280; margin-top:4px }

.header-actions {
  position: absolute;
  right: 14px;
  top: 14px;
  display: flex;
  gap: 8px;
  align-items: center;
}

.mode-button {
  background: transparent;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  color: #374151;
}

.mode-button:hover {
  border-color: #0b74ff;
  color: #0b74ff;
}

.mode-button.active {
  background: #0b74ff;
  border-color: #0b74ff;
  color: white;
}

.settings-button {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 18px;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.2s;
}

.settings-button:hover {
  background: #f3f4f6;
}

.chat-container { flex:1; display:flex; flex-direction:column; align-items:center; overflow:hidden; padding:20px 12px }
.messages-container { flex:1; overflow-y:auto; width:100%; max-width:960px; background:#fff; border-radius:12px; box-shadow:0 6px 20px rgba(16,24,40,0.06); padding:20px; margin-bottom:12px }
.welcome-message { display:flex; justify-content:center; align-items:center; min-height:240px; padding:10px 20px }
.welcome-content { text-align:center; max-width:600px; color:#4b5563 }
.welcome-icon { font-size:48px; margin-bottom:16px }
.welcome-content h2 { font-size:20px; margin-bottom:12px; color:#111827 }
.welcome-content p { margin-bottom:10px; line-height:1.6 }
.welcome-content ul { text-align:left; margin:10px auto }
.welcome-content li { margin-bottom:6px }

.chat-message { display:flex; margin-bottom:16px; padding:0 8px; align-items:flex-end }
.ai-message { justify-content:flex-start }
.message-avatar { display:flex; align-items:flex-start; margin:0 10px }
.avatar { width:40px; height:40px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:14px; font-weight:700; color:white }
.ai-avatar { background-color:#6c757d }
.user-avatar { background-color: var(--user-avatar-color, #0b74ff) }
.message-content { max-width:72%; min-width:120px }
.message-bubble { padding:12px 16px; border-radius:14px; position:relative; word-wrap:break-word; word-break:break-word; background-color:#f8fafc; color:#111827; box-shadow:0 1px 0 rgba(0,0,0,0.03) }
.user-message .message-bubble { background:linear-gradient(90deg,#0966ff,#007bff); color:#fff }
.ai-typing-content { display:flex; flex-direction:column; gap:8px }
.ai-response-text { font-size:15px; line-height:1.6 }
.ai-response-text.message-markdown h1,.ai-response-text.message-markdown h2,.ai-response-text.message-markdown h3 { margin:0.5em 0 }
.ai-response-text.message-markdown code { background-color:rgba(0,0,0,0.06); padding:0.15em 0.35em; border-radius:4px }
.message-time { font-size:12px; color:#9ca3af; margin-top:6px }

.connection-error { position:fixed; top:20px; left:50%; transform:translateX(-50%); background-color:#ff4444; color:white; padding:10px 20px; border-radius:5px; z-index:1000; animation:slideDown .3s ease-out }
.error-content { display:flex; align-items:center; gap:8px }
.error-icon { font-size:16px }
@keyframes slideDown { from { transform:translateX(-50%) translateY(-100%); opacity:0 } to { transform:translateX(-50%) translateY(0); opacity:1 } }
.messages-container::-webkit-scrollbar { width:6px }
.messages-container::-webkit-scrollbar-track { background:#f1f1f1 }
.messages-container::-webkit-scrollbar-thumb { background:#c1c1c1; border-radius:3px }
.messages-container::-webkit-scrollbar-thumb:hover { background:#a8a8a8 }
@media (max-width:768px) { .app-header { padding:15px } .app-title { font-size:20px } .messages-container { padding:15px 0 } .welcome-content { padding:0 10px } .message-content { max-width:85% } .chat-message { padding:0 10px } }

/* settings modal and button */
.settings-modal-overlay { position:fixed; inset:0; display:flex; align-items:center; justify-content:center; background:rgba(0,0,0,0.4); z-index:1500 }
.settings-modal { background:#fff; padding:18px; border-radius:8px; width:320px; box-shadow:0 8px 40px rgba(2,6,23,0.2) }
.settings-modal h3 { margin:0 0 12px 0 }
.setting-row { display:flex; flex-direction:column; gap:6px; margin-bottom:10px }
.color-list { display:flex; gap:8px; align-items:center }
.color-preview { width:28px; height:28px; border-radius:50%; border:2px solid #d1d5db; margin-bottom:8px }
.color-swatch { width:28px; height:28px; border-radius:6px; border:2px solid #fff; cursor:pointer }
.color-swatch.selected { box-shadow: 0 0 0 2px rgba(15,23,42,0.16); border-color: rgba(255,255,255,0.8) }
.settings-actions { display:flex; gap:8px; justify-content:flex-end }
.btn-primary { background:#0b74ff; color:#fff; border:none; padding:6px 10px; border-radius:6px; cursor:pointer }
.btn-link { background:transparent; border:none; color:#374151; cursor:pointer }

/* dark theme */
.theme-dark { background: linear-gradient(180deg,#0b1220 0%, #071022 100%); color:#e6eef8 }
.theme-dark .app-header { background:#071022 }
.theme-dark .messages-container { background:#071929 }
.theme-dark .message-bubble { background:#042235; color:#dbeafe }
.theme-dark .user-message .message-bubble { background:linear-gradient(90deg,#1d4ed8,#2563eb) }
</style>
