<template>
  <div class="thought-process">
    <div class="thought-header" @click="expanded = !expanded">
      <span class="thought-icon">🧠</span>
      <span class="thought-title">AI 思考过程</span>
      <span class="thought-toggle">{{ expanded ? '收起' : '展开' }}</span>
    </div>
    
    <div v-if="expanded" class="thought-steps">
      <div v-for="(step, index) in steps" :key="index" class="thought-step">
        <div class="step-indicator">
          <div class="step-number">{{ index + 1 }}</div>
          <div class="step-line" v-if="index < steps.length - 1"></div>
        </div>
        
        <div class="step-content">
          <div v-if="step.thought" class="step-thought">
            <span class="step-label">💭 思考</span>
            <p class="step-text">{{ step.thought }}</p>
          </div>
          
          <div v-if="step.action" class="step-action">
            <span class="step-label">🔧 行动</span>
            <div class="action-detail">
              <span class="action-name">{{ step.action }}</span>
              <span v-if="step.actionInput" class="action-input">{{ step.actionInput }}</span>
            </div>
          </div>
          
          <div v-if="step.observation" class="step-observation">
            <span class="step-label">👀 观察</span>
            <p class="step-text observation-text">{{ step.observation }}</p>
          </div>
          
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
    steps: { type: Array, default: () => [] }
  },
  data() {
    return { expanded: true }
  },
  watch: {
    steps() {
      if (this.steps.length > 0) this.expanded = true
    }
  }
}
</script>

<style scoped>
.thought-process {
  background: var(--bg-tertiary, #f8fafc);
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: var(--radius-md, 12px);
  margin-bottom: 16px;
  overflow: hidden;
}
.thought-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  background: var(--bg-tertiary, #f1f5f9);
  transition: var(--transition, all 0.2s);
}
.thought-header:hover { background: var(--border-color, #e2e8f0); }
.thought-icon { font-size: 18px; margin-right: 8px; }
.thought-title { flex: 1; font-size: 14px; font-weight: 600; color: var(--text-primary, #334155); }
.thought-toggle { font-size: 12px; color: var(--text-muted, #64748b); }
.thought-steps { padding: 12px 16px; }
.thought-step { display: flex; gap: 12px; margin-bottom: 8px; }
.step-indicator { display: flex; flex-direction: column; align-items: center; min-width: 28px; }
.step-number { width: 28px; height: 28px; border-radius: 50%; background: var(--accent, #3b82f6); color: white; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; }
.step-line { width: 2px; flex: 1; background: var(--border-color, #cbd5e1); margin: 4px 0; }
.step-content { flex: 1; padding-bottom: 12px; }
.step-label { font-size: 12px; font-weight: 600; color: var(--text-muted, #64748b); display: block; margin-bottom: 4px; }
.step-text { font-size: 13px; color: var(--text-primary, #334155); line-height: 1.5; margin: 0; padding: 8px 12px; background: var(--bg-secondary, white); border-radius: var(--radius-sm, 8px); border: 1px solid var(--border-color, #e2e8f0); }
.action-detail { padding: 8px 12px; background: var(--bg-secondary, white); border-radius: var(--radius-sm, 8px); border: 1px solid var(--border-color, #e2e8f0); }
.action-name { font-size: 13px; font-weight: 600; color: var(--accent, #2563eb); display: block; margin-bottom: 4px; }
.action-input { font-size: 12px; color: var(--text-muted, #64748b); font-family: monospace; display: block; word-break: break-all; }
.observation-text { background: #fef3c7; border-color: #fde68a; }
.final-text { background: #dcfce7; border-color: #86efac; }
</style>
