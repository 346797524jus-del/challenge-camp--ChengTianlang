<template>
  <div :class="['file-manager', theme === 'dark' ? 'theme-dark' : '']">
    <div class="file-manager-header" @click="expanded = !expanded">
      <span class="fm-icon">📁</span>
      <span class="fm-title">生成的文件管理</span>
      <span class="fm-badge" v-if="files.length > 0">{{ files.length }}</span>
      <span class="fm-toggle">{{ expanded ? '收起' : '展开' }}</span>
    </div>
    
    <div v-if="expanded" class="file-manager-body">
      <!-- 加载中 -->
      <div v-if="loading" class="fm-loading">
        <div class="loading-spinner"></div>
        <p>正在加载文件列表...</p>
      </div>
      
      <!-- 空状态 -->
      <div v-else-if="files.length === 0" class="fm-empty">
        <p>暂无生成的文件</p>
        <p class="fm-hint">在智能体模式下生成文档后，文件会出现在这里</p>
      </div>
      
      <!-- 文件列表 -->
      <div v-else class="fm-file-list">
        <div
          v-for="(file, index) in files"
          :key="index"
          class="fm-file-item"
        >
          <div class="fm-file-icon">
            {{ getFileEmoji(file.type) }}
          </div>
          <div class="fm-file-info">
            <div class="fm-file-name" :title="file.name">{{ file.name }}</div>
            <div class="fm-file-meta">
              <span class="fm-file-type">{{ getFileTypeLabel(file.type) }}</span>
              <span class="fm-file-size">{{ formatFileSize(file.size) }}</span>
              <span class="fm-file-time">{{ formatTime(file.lastModified) }}</span>
            </div>
          </div>
          <div class="fm-file-actions">
            <button class="fm-btn fm-btn-preview" @click="previewFile(file)" title="预览">👁️</button>
            <a :href="getDownloadUrl(file.name)" download class="fm-btn fm-btn-download" title="下载">⬇️</a>
            <button class="fm-btn fm-btn-delete" @click="deleteFile(file)" title="删除">🗑️</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { getGeneratedFiles, deleteGeneratedFile } from '../api/agentApi.js'

export default {
  name: 'FileManager',
  props: {
    refreshTrigger: {
      type: Number,
      default: 0
    },
    theme: {
      type: String,
      default: 'light'
    }
  },
  emits: ['preview'],
  data() {
    return {
      expanded: false,
      loading: false,
      files: []
    }
  },
  watch: {
    refreshTrigger() {
      this.loadFiles()
    }
  },
  methods: {
    async loadFiles() {
      this.loading = true
      try {
        const data = await getGeneratedFiles()
        this.files = data.files || []
      } catch (err) {
        console.error('加载文件列表失败:', err)
      } finally {
        this.loading = false
      }
    },
    previewFile(file) {
      this.$emit('preview', file)
    },
    async deleteFile(file) {
      if (!confirm(`确定要删除 "${file.name}" 吗？`)) return
      try {
        await deleteGeneratedFile(file.name)
        this.files = this.files.filter(f => f.name !== file.name)
      } catch (err) {
        console.error('删除文件失败:', err)
        alert('删除文件失败')
      }
    },
    getDownloadUrl(fileName) {
      return `/api/files/${encodeURIComponent(fileName)}`
    },
    getFileEmoji(type) {
      const map = { docx: '📄', xlsx: '📊', pptx: '📽️' }
      return map[type] || '📁'
    },
    getFileTypeLabel(type) {
      const map = { docx: 'Word', xlsx: 'Excel', pptx: 'PPT' }
      return map[type] || type
    },
    formatFileSize(bytes) {
      if (!bytes) return ''
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    },
    formatTime(timestamp) {
      if (!timestamp) return ''
      const date = new Date(timestamp)
      const now = new Date()
      const diff = now - date
      if (diff < 60000) return '刚刚'
      if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
      if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
      return date.toLocaleDateString('zh-CN')
    }
  },
  mounted() {
    this.loadFiles()
  }
}
</script>

<style scoped>
.file-manager {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  margin-bottom: 16px;
  overflow: hidden;
}

.file-manager-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  background: #f1f5f9;
  transition: background 0.2s;
}

.file-manager-header:hover {
  background: #e2e8f0;
}

.fm-icon {
  font-size: 18px;
  margin-right: 8px;
}

.fm-title {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}

.fm-badge {
  background: #3b82f6;
  color: white;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  margin-right: 8px;
}

.fm-toggle {
  font-size: 12px;
  color: #64748b;
}

.file-manager-body {
  padding: 12px 16px;
}

.fm-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  color: #64748b;
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 8px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.fm-empty {
  text-align: center;
  padding: 20px;
  color: #94a3b8;
}

.fm-hint {
  font-size: 12px;
  margin-top: 4px;
}

.fm-file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.fm-file-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  transition: all 0.2s;
}

.fm-file-item:hover {
  border-color: #93c5fd;
  box-shadow: 0 1px 4px rgba(59, 130, 246, 0.1);
}

.fm-file-icon {
  font-size: 24px;
  margin-right: 12px;
}

.fm-file-info {
  flex: 1;
  min-width: 0;
}

.fm-file-name {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fm-file-meta {
  display: flex;
  gap: 8px;
  margin-top: 2px;
  font-size: 11px;
  color: #94a3b8;
}

.fm-file-type {
  background: #eef2ff;
  color: #4f46e5;
  padding: 0 6px;
  border-radius: 3px;
  font-weight: 500;
}

.fm-file-actions {
  display: flex;
  gap: 4px;
  margin-left: 8px;
}

.fm-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  text-decoration: none;
}

.fm-btn:hover {
  background: #f1f5f9;
}

.fm-btn-preview:hover {
  background: #dbeafe;
}

.fm-btn-download:hover {
  background: #dcfce7;
}

.fm-btn-delete:hover {
  background: #fee2e2;
}

/* 深色主题 */
.theme-dark .file-manager {
  background: #0f172a;
  border-color: #1e293b;
}

.theme-dark .file-manager-header {
  background: #1e293b;
}

.theme-dark .fm-title {
  color: #e2e8f0;
}

.theme-dark .fm-file-item {
  background: #1e293b;
  border-color: #334155;
}

.theme-dark .fm-file-name {
  color: #e2e8f0;
}

.theme-dark .fm-btn:hover {
  background: #334155;
}
</style>
