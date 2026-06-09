<template>
  <div class="file-preview-overlay" @click.self="close">
    <div class="file-preview-modal">
      <div class="preview-header">
        <span class="preview-title">📄 {{ fileName }}</span>
        <div class="preview-actions">
          <a :href="downloadUrl" class="btn-download" download>⬇️ 下载</a>
          <button class="btn-close" @click="close">✕</button>
        </div>
      </div>
      <div class="preview-body">
        <!-- 加载中 -->
        <div v-if="loading" class="preview-loading">
          <div class="loading-spinner"></div>
          <p>正在加载文件...</p>
        </div>

        <!-- 错误提示 -->
        <div v-if="error" class="preview-error">
          <span class="error-icon">⚠️</span>
          <p>{{ error }}</p>
        </div>

        <!-- Word 预览 -->
        <div v-if="fileType === 'docx' && !loading && !error" ref="wordPreview" class="word-preview"></div>

        <!-- Excel 预览 -->
        <div v-if="fileType === 'xlsx' && !loading && !error" class="excel-preview">
          <div v-for="(sheet, sIndex) in excelData" :key="sIndex" class="excel-sheet">
            <h4 class="sheet-name">{{ sheet.name }}</h4>
            <div class="table-wrapper">
              <table class="excel-table">
                <thead>
                  <tr>
                    <th v-for="(col, cIndex) in sheet.headers" :key="cIndex">{{ col }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, rIndex) in sheet.rows" :key="rIndex">
                    <td v-for="(cell, cIndex) in row" :key="cIndex">{{ cell }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- PPT 预览 -->
        <div v-if="fileType === 'pptx' && !loading && !error" class="pptx-preview">
          <div class="pptx-controls">
            <button @click="prevSlide" :disabled="currentSlide <= 0">◀ 上一页</button>
            <span class="slide-indicator">{{ currentSlide + 1 }} / {{ pptxSlides.length }}</span>
            <button @click="nextSlide" :disabled="currentSlide >= pptxSlides.length - 1">下一页 ▶</button>
          </div>
          <div class="pptx-slide" ref="pptxContainer"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'FilePreview',
  props: {
    fileName: { type: String, required: true },
    fileType: { type: String, default: '' }
  },
  emits: ['close'],
  data() {
    return {
      loading: true,
      error: null,
      excelData: [],
      pptxSlides: [],
      currentSlide: 0,
      wordHtml: ''
    }
  },
  computed: {
    downloadUrl() {
      return `/api/files/${encodeURIComponent(this.fileName)}`
    }
  },
  async mounted() {
    await this.loadFile()
  },
  methods: {
    close() {
      this.$emit('close')
    },
    async loadFile() {
      this.loading = true
      this.error = null
      try {
        const response = await axios.get(this.downloadUrl, {
          responseType: 'arraybuffer',
          timeout: 30000
        })
        const data = new Uint8Array(response.data)
        
        switch (this.fileType) {
          case 'docx':
            await this.renderWord(data)
            break
          case 'xlsx':
            await this.renderExcel(data)
            break
          case 'pptx':
            await this.renderPptx(data)
            break
          default:
            this.error = '不支持预览该文件类型'
        }
      } catch (err) {
        console.error('文件加载失败:', err)
        this.error = '文件加载失败，请尝试下载查看'
      } finally {
        this.loading = false
      }
    },
    async renderWord(data) {
      try {
        const docx = await import('docx-preview')
        const container = this.$refs.wordPreview
        if (container) {
          await docx.renderAsync(data, container, null, {
            className: 'docx-viewer',
            inWrapper: true,
            ignoreWidth: false,
            ignoreHeight: false,
            ignoreFonts: false,
            breakPages: true,
            ignoreLastRenderedPageBreak: false,
            experimental: false,
            trimXmlDeclaration: true,
            useBase64URL: false,
            renderHeaders: true,
            renderFooters: true,
            renderFootnotes: true,
            renderEndnotes: true
          })
        }
      } catch (err) {
        console.error('Word 渲染失败:', err)
        this.error = 'Word 文档预览失败，请尝试下载查看'
      }
    },
    async renderExcel(data) {
      try {
        const XLSX = await import('xlsx')
        const workbook = XLSX.read(data, { type: 'array' })
        const sheets = []
        workbook.SheetNames.forEach(name => {
          const sheet = workbook.Sheets[name]
          const jsonData = XLSX.utils.sheet_to_json(sheet, { header: 1 })
          if (jsonData.length > 0) {
            sheets.push({
              name: name,
              headers: jsonData[0] || [],
              rows: jsonData.slice(1) || []
            })
          }
        })
        this.excelData = sheets
      } catch (err) {
        console.error('Excel 解析失败:', err)
        this.error = 'Excel 表格预览失败，请尝试下载查看'
      }
    },
    async renderPptx(data) {
      try {
        // 使用简单的 PPTX 预览 - 提取文本内容
        const JSZip = await import('jszip')
        const zip = await JSZip.loadAsync(data)
        
        // 获取幻灯片文件列表
        const slideFiles = Object.keys(zip.files)
          .filter(name => name.match(/^ppt\/slides\/slide\d+\.xml$/))
          .sort()
        
        const slides = []
        for (const slideFile of slideFiles) {
          const content = await zip.file(slideFile).async('text')
          // 简单提取文本内容
          const texts = content.match(/<a:t[^>]*>([^<]+)<\/a:t>/g) || []
          const slideTexts = texts.map(t => t.replace(/<[^>]+>/g, ''))
          slides.push(slideTexts)
        }
        this.pptxSlides = slides
        this.currentSlide = 0
      } catch (err) {
        console.error('PPT 解析失败:', err)
        this.error = 'PPT 预览失败，请尝试下载查看'
      }
    },
    prevSlide() {
      if (this.currentSlide > 0) this.currentSlide--
    },
    nextSlide() {
      if (this.currentSlide < this.pptxSlides.length - 1) this.currentSlide++
    }
  }
}
</script>

<style scoped>
.file-preview-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
}

.file-preview-modal {
  background: #fff;
  border-radius: 12px;
  width: 90%;
  max-width: 1000px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}

.preview-title {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.btn-download {
  padding: 6px 14px;
  background: #0b74ff;
  color: white;
  border-radius: 6px;
  text-decoration: none;
  font-size: 13px;
  transition: background 0.2s;
}

.btn-download:hover {
  background: #0056d6;
}

.btn-close {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  font-size: 18px;
  cursor: pointer;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  transition: all 0.2s;
}

.btn-close:hover {
  background: #e2e8f0;
  color: #1e293b;
}

.preview-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  min-height: 400px;
}

.preview-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  color: #64748b;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e2e8f0;
  border-top-color: #0b74ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.preview-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  color: #ef4444;
}

.error-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

/* Word 预览样式 */
.word-preview {
  max-width: 100%;
}

.word-preview :deep(.docx-viewer) {
  background: #fff;
  padding: 20px;
}

.word-preview :deep(.docx-wrapper) {
  background: #fff !important;
  padding: 0 !important;
}

.word-preview :deep(.docx) {
  padding: 20px !important;
}

/* Excel 预览样式 */
.excel-sheet {
  margin-bottom: 24px;
}

.sheet-name {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 8px;
  padding: 8px 12px;
  background: #f1f5f9;
  border-radius: 6px;
}

.table-wrapper {
  overflow-x: auto;
}

.excel-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.excel-table th {
  background: #0b74ff;
  color: white;
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  white-space: nowrap;
}

.excel-table td {
  padding: 6px 12px;
  border-bottom: 1px solid #e2e8f0;
  color: #334155;
}

.excel-table tr:nth-child(even) td {
  background: #f8fafc;
}

.excel-table tr:hover td {
  background: #eef2ff;
}

/* PPT 预览样式 */
.pptx-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-bottom: 16px;
}

.pptx-controls button {
  padding: 8px 16px;
  border: 1px solid #d1d5db;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #374151;
  transition: all 0.2s;
}

.pptx-controls button:hover:not(:disabled) {
  background: #f3f4f6;
  border-color: #0b74ff;
  color: #0b74ff;
}

.pptx-controls button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.slide-indicator {
  font-size: 14px;
  font-weight: 600;
  color: #64748b;
}

.pptx-slide {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 40px;
  min-height: 400px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

/* 深色主题 */
.theme-dark .file-preview-modal {
  background: #0f172a;
}

.theme-dark .preview-header {
  background: #1e293b;
  border-color: #334155;
}

.theme-dark .preview-title {
  color: #e2e8f0;
}

.theme-dark .btn-close {
  color: #94a3b8;
}

.theme-dark .btn-close:hover {
  background: #334155;
  color: #e2e8f0;
}

.theme-dark .excel-table td {
  color: #cbd5e1;
  border-color: #334155;
}

.theme-dark .excel-table tr:nth-child(even) td {
  background: #1e293b;
}

.theme-dark .excel-table tr:hover td {
  background: #1e3a5f;
}

.theme-dark .sheet-name {
  background: #1e293b;
  color: #e2e8f0;
}

.theme-dark .pptx-slide {
  background: #1e293b;
  border-color: #334155;
}

.theme-dark .pptx-controls button {
  background: #1e293b;
  border-color: #334155;
  color: #cbd5e1;
}

.theme-dark .pptx-controls button:hover:not(:disabled) {
  background: #334155;
}
</style>
