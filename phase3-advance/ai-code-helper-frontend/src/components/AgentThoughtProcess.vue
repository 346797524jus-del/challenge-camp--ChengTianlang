<template>
  <div class="thought-process">
    <div class="thought-header" @click="expanded = !expanded">
      <span class="thought-icon">🧠</span>
      <span class="thought-title">AI 思考过程</span>
      <span class="thought-toggle">{{ expanded ? '收起' : '展开' }}</span>
    </div>
    
    <div v-if="expanded" class="thought-steps">
      <div
        v-for="(step, index) in steps"
        :key="index"
        class="thought-step"
      >
        <div class="step-indicator">
          <div class="step-number">{{ index + 1 }}</div>
          <div class="step-line" v-if="index < steps.length - 1"></div>
        </div>
        
        <div class="step-content">
          <!-- 思考 -->
          <div v-if="step.thought" class="step-thought">
            <span class="step-label">💭 思考</span>
            <p class="step-text">{{ step.thought }}</p>
          </div>
          
          <!-- 行动 -->
          <div v-if="step.action" class="step-action">
            <span class="step-label">🔧 行动</span>
            <div class="action-detail">
              <span class="action-name">{{ step.action }}</span>
              <span v-if="step.actionInput" class="action-input">{{ step.actionInput }}</span>
            </div>
          </div>
          
          <!-- 观察 -->
          <div v-if="step.observation" class="step-observation">
            <span class="step-label">👀 观察</span>
            <p class="step-text observation-text">{{ step.observation }}</p>
          </div>
          
          <!-- 最终答案 -->
          <div v-if="step.finalAnswer" class="step-final">
            <span class="step-label">✅ 最终答案</span>
            <p class="step-text final-text">{{ step.finalAnswer }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AgentThoughtProcess',
  props: {
    steps: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      expanded: true
    }
  },
  watch: {
    steps() {
      // 当有新的步骤时自动展开
      if (this.steps.length > 0) {
        this.expanded = true
      }
    }
  }
}
</script>

<style scoped>
.thought-process {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  margin-bottom: 16px;
  overflow: hidden;
}

.thought-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  background: #f1f5f9;
  transition: background 0.2s;
}

.thought-header:hover {
  background: #e2e8f0;
}

.thought-icon {
  font-size: 18px;
  margin-right: 8px;
}

.thought-title {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}

.thought-toggle {
  font-size: 12px;
  color: #64748b;
}

.thought-steps {
  padding: 12px 16px;
}

.thought-step {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
}

.step-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 28px;
}

.step-number {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #3b82f6;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.step-line {
  width: 2px;
  flex: 1;
  background: #cbd5e1;
  margin: 4px 0;
}

.step-content {
  flex: 1;
  padding-bottom: 12px;
}

.step-label {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  display: block;
  margin-bottom: 4px;
}

.step-text {
  font-size: 13px;
  color: #334155;
  line-height: 1.5;
  margin: 0;
  padding: 8px 12px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.action-detail {
  padding: 8px 12px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.action-name {
  font-size: 13px;
  font-weight: 600;
  color: #2563eb;
  display: block;
  margin-bottom: 4px;
}

.action-input {
  font-size: 12px;
  color: #64748b;
  font-family: monospace;
  display: block;
  word-break: break-all;
}

.observation-text {
  background: #fef3c7;
  border-color: #fde68a;
}

.final-text {
  background: #dcfce7;
  border-color: #86efac;
}

/* 深色主题 */
.theme-dark .thought-process {
  background: #0f172a;
  border-color: #1e293b;
}

.theme-dark .thought-header {
  background: #1e293b;
}

.theme-dark .thought-title {
  color: #e2e8f0;
}

.theme-dark .step-text {
  background: #1e293b;
  border-color: #334155;
  color: #e2e8f0;
}

.theme-dark .action-detail {
  background: #1e293b;
  border-color: #334155;
}
</style>
