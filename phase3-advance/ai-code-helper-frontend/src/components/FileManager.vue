<template>
  <div :class="['file-manager', theme === 'dark' ? 'theme-dark' : '']">
    <div class="file-manager-header" @click="expanded = !expanded">
      <span class="fm-icon">📁</span>
      <span class="fm-title">生成的文件管理</span>
      <span class="fm-badge" v-if="files.length > 0">{{ files.length }}</span>
      <span class="fm-toggle">{{ expanded ? '收起' : '展开' }}</span>
    </div>
    
    <div v-if="expanded" class="file-manager-body">
      <div v-if="loading" class="fm-loading">
        <div class="loading-spinner"></div>
        <p>正在加载文件列表...</p>
      </div>
      
      <div v-else-if="files.length === 0" class="fm-empty">
        <div class="fm-empty-icon">📂</div>
        <p>暂无生成的文件</p>
        <p class="fm-hint">在智能体模式下生成文档后，文件会出现在这里</p>
      </div>
      
      <div v-else class="fm-file-list">
        <div v-for="(file, index) in files" :key="index" class="fm-file-item">
          <div class="fm-file-icon">{{ getFileEmoji(file.type) }}</div>
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
    refreshTrigger: { type: Number, default: 0 },
    theme: { type: String, default: 'light' }
  },
  emits: ['preview'],
  data() {
    return { expanded: false, loading: false, files: [] }
  },
  watch: {
    refreshTrigger() { this.loadFiles() }
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
    previewFile(file) { this.$emit('preview', file) },
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
    getDownloadUrl(fileName) { return `/api/files/${encodeURIComponent(fileName)}` },
    getFileEmoji(type) { return { docx: '📄', xlsx: '📊', pptx: '📽️' }[type] || '📁' },
    getFileTypeLabel(type) { return { docx: 'Word', xlsx: 'Excel', pptx: 'PPT' }[type] || type },
    formatFileSize(bytes) {
      if (!bytes) return ''
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    },
    formatTime(timestamp) {
      if (!timestamp) return ''
      const date = new Date(timestamp)
      const diff = Date.now() - date
      if (diff < 60000) return '刚刚'
      if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
      if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
      return date.toLocaleDateString('zh-CN')
    }
  },
  mounted() { this.loadFiles() }
}
</script>

<style scoped>
.file-manager {
  background: var(--bg-tertiary, #f8fafc);
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: var(--radius-md, 12px);
  margin-bottom: 16px;
  overflow: hidden;
}
.file-manager-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  background: var(--bg-tertiary, #f1f5f9);
  transition: var(--transition, all 0.2s);
}
.file-manager-header:hover { background: var(--border-color, #e2e8f0); }
.fm-icon { font-size: 18px; margin-right: 8px; }
.fm-title { flex: 1; font-size: 14px; font-weight: 600; color: var(--text-primary, #334155); }
.fm-badge {
  background: var(--accent, #3b82f6);
  color: white;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  margin-right: 8px;
}
.fm-toggle { font-size: 12px; color: var(--text-muted, #64748b); }
.file-manager-body { padding: 12px 16px; }
.fm-loading { display: flex; flex-direction: column; align-items: center; padding: 20px; color: var(--text-muted, #64748b); }
.loading-spinner { width: 24px; height: 24px; border: 2px solid var(--border-color, #e2e8f0); border-top-color: var(--accent, #3b82f6); border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 8px; }
@keyframes spin { to { transform: rotate(360deg); } }
.fm-empty { text-align: center; padding: 20px; color: var(--text-muted, #94a3b8); }
.fm-empty-icon { font-size: 40px; margin-bottom: 8px; }
.fm-hint { font-size: 12px; margin-top: 4px; }
.fm-file-list { display: flex; flex-direction: column; gap: 8px; }
.fm-file-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  background: var(--bg-secondary, white);
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: var(--radius-sm, 8px);
  transition: var(--transition, all 0.2s);
}
.fm-file-item:hover { border-color: var(--accent, #93c5fd); box-shadow: 0 1px 4px rgba(59,130,246,0.1); }
.fm-file-icon { font-size: 24px; margin-right: 12px; }
.fm-file-info { flex: 1; min-width: 0; }
.fm-file-name { font-size: 13px; font-weight: 500; color: var(--text-primary, #1e293b); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fm-file-meta { display: flex; gap: 8px; margin-top: 2px; font-size: 11px; color: var(--text-muted, #94a3b8); }
.fm-file-type { background: var(--accent-light, #eef2ff); color: var(--accent, #4f46e5); padding: 0 6px; border-radius: 3px; font-weight: 500; }
.fm-file-actions { display: flex; gap: 4px; margin-left: 8px; }
.fm-btn { width: 32px; height: 32px; border: none; background: transparent; border-radius: 6px; cursor: pointer; font-size: 16px; display: flex; align-items: center; justify-content: center; transition: var(--transition, all 0.2s); text-decoration: none; }
.fm-btn:hover { background: var(--bg-tertiary, #f1f5f9); }
.fm-btn-preview:hover { background: #dbeafe; }
.fm-btn-download:hover { background: #dcfce7; }
.fm-btn-delete:hover { background: #fee2e2; }
</style>
