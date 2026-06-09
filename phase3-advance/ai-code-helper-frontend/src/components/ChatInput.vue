<template>
  <div class="chat-input">
    <div class="input-container">
      <textarea
        ref="inputRef"
        v-model="inputMessage"
        :placeholder="placeholder"
        :disabled="disabled"
        class="input-textarea"
        rows="1"
        @keydown="handleKeyDown"
        @input="adjustHeight"
      />
      <button
        :disabled="disabled || !inputMessage.trim()"
        @click="sendMessage"
        class="send-button"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M2 21l21-9L2 3v7l15 2-15 2v7z" fill="currentColor"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ChatInput',
  props: {
    disabled: {
      type: Boolean,
      default: false
    },
    placeholder: {
      type: String,
      default: '请输入您的问题...'
    }
  },
  data() {
    return {
      inputMessage: ''
    }
  },
  methods: {
    sendMessage() {
      if (this.inputMessage.trim() && !this.disabled) {
        this.$emit('send-message', this.inputMessage.trim())
        this.inputMessage = ''
        this.adjustHeight()
      }
    },
    handleKeyDown(event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault()
        this.sendMessage()
      }
    },
    adjustHeight() {
      this.$nextTick(() => {
        const textarea = this.$refs.inputRef
        textarea.style.height = 'auto'
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px'
      })
    },
    focus() {
      this.$refs.inputRef.focus()
    }
  },
  mounted() {
    this.adjustHeight()
  }
}
</script>

<style scoped>
.chat-input {
  padding: 12px 16px;
  background-color: transparent;
  border-top: 1px solid rgba(0,0,0,0.04);
  width: 100%;
}

.input-container {
  display: flex;
  align-items: center;
  gap: 12px;
  max-width: 960px;
  margin: 0 auto;
  background: #fff;
  padding: 10px;
  border-radius: 12px;
  box-shadow: 0 6px 18px rgba(16,24,40,0.06);
}

.input-textarea {
  flex: 1;
  padding: 12px 14px;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 12px;
  font-size: 15px;
  line-height: 1.4;
  resize: none;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
  min-height: 44px;
  max-height: 120px;
  overflow-y: auto;
}

.input-textarea:focus { border-color: #0b74ff; box-shadow: 0 4px 18px rgba(11,116,255,0.08) }

.input-textarea:disabled { background-color: #f5f7fa; color: #9aa4b2 }

.send-button {
  width: 44px; height:44px; background: linear-gradient(90deg,#0966ff,#007bff); border:none; border-radius:10px; color:#fff; cursor:pointer; display:flex; align-items:center; justify-content:center; transition: transform .08s ease, box-shadow .08s ease; box-shadow: 0 6px 12px rgba(3,102,214,0.15);
}

.send-button:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 8px 20px rgba(3,102,214,0.18) }
.send-button:disabled { opacity:0.6; cursor:not-allowed }

@media (max-width: 768px) {
  .chat-input { padding: 10px }
  .input-container { padding:8px }
  .input-textarea { font-size:16px }
}
</style>