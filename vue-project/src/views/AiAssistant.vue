<template>
  <div class="ai-page">
    <header class="ai-page__header">
      <div class="ai-page__header-main">
        <span class="ai-page__icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M12 2a2 2 0 0 1 2 2v1h3a2 2 0 0 1 2 2v3h1a2 2 0 0 1 0 4h-1v3a2 2 0 0 1-2 2h-3v1a2 2 0 0 1-4 0v-1H7a2 2 0 0 1-2-2v-3H4a2 2 0 0 1 0-4h1V7a2 2 0 0 1 2-2h3V4a2 2 0 0 1 2-2z"/>
            <circle cx="9.5" cy="11" r="1.2" fill="currentColor"/>
            <circle cx="14.5" cy="11" r="1.2" fill="currentColor"/>
            <path d="M9 15c.8.7 1.9 1 3 1s2.2-.3 3-1"/>
          </svg>
        </span>
        <div>
          <h1 class="ai-page__title">智能制造工艺部 AI 助手</h1>
          <p class="ai-page__subtitle">大模型驱动 · 整合全系统数据资源 · 按角色权限安全问答 · 流式输出</p>
        </div>
      </div>
      <div class="ai-page__tags">
        <span class="ai-page__tag">制度与工艺知识库</span>
        <span class="ai-page__tag">个人考勤查询</span>
        <span class="ai-page__tag">科室人员与职级</span>
        <span class="ai-page__tag">权限内统计分析</span>
        <span class="ai-page__tag">本地统计图表</span>
        <span class="ai-page__tag">权限内报表导出</span>
        <span class="ai-page__tag">报表汇聚导出</span>
        <span class="ai-page__tag">排班与节假日</span>
        <span class="ai-page__tag">天气/新闻</span>
      </div>
    </header>

    <section class="ai-page__chat card">
      <AiAssistantChat />
    </section>
  </div>
</template>

<script setup>
import AiAssistantChat from '@/components/ai/AiAssistantChat.vue'
</script>

<style scoped>
.ai-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 130px);
  min-height: 520px;
  gap: var(--spacing-lg, 16px);
}
.ai-page__header {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-lg, 16px);
  background: linear-gradient(120deg, #eaf4ff 0%, #eafaf7 100%);
  border: 1px solid var(--color-border-secondary, #eef0f3);
  border-radius: var(--radius-lg, 12px);
  padding: 18px 22px;
  flex-wrap: wrap;
}
.ai-page__header-main { display: flex; align-items: center; gap: 14px; }
.ai-page__icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, #1890ff, #36cfc9);
  box-shadow: 0 8px 20px rgba(24, 144, 255, 0.3);
}
.ai-page__icon svg { width: 28px; height: 28px; }
.ai-page__title {
  margin: 0;
  font-size: var(--font-size-xl, 20px);
  font-weight: 700;
  color: var(--color-text-primary, #1f2937);
}
.ai-page__subtitle {
  margin: 4px 0 0;
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text-tertiary, #6b7280);
}
.ai-page__tags { display: flex; flex-wrap: wrap; gap: 8px; }
.ai-page__tag {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.75);
  color: var(--color-primary, #1890ff);
  border: 1px solid rgba(24, 144, 255, 0.25);
}
.ai-page__chat {
  flex: 1 1 auto;
  min-height: 0;
  padding: 0;
  overflow: hidden;
}
</style>
