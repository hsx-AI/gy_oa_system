<template>
  <div class="ai-chat" :class="{ 'ai-chat--compact': compact }">
    <!-- 顶部工具栏：当前模型（只读）+ 历史对话 + 新建对话 -->
    <div v-if="!compact" ref="barEl" class="ai-chat__bar">
      <div class="ai-chat__model" :title="currentModel ? `当前使用：${currentModel}` : ''">
        <span class="ai-chat__model-dot"></span>
        <span class="ai-chat__model-text">{{ currentModel ? `当前模型：${currentModel}` : '正在获取模型…' }}</span>
      </div>
      <div class="ai-chat__bar-actions">
        <div v-if="sessions.length" class="ai-chat__history">
          <button type="button" class="ai-chat__bar-btn" @click="historyOpen = !historyOpen">
            历史对话 · {{ sessions.length }}
          </button>
          <div v-if="historyOpen" class="ai-chat__history-pop">
            <div
              v-for="s in sessions"
              :key="s.id"
              class="ai-chat__history-item"
              :class="{ 'is-current': s.id === currentSessionId }"
            >
              <span class="ai-chat__history-title" @click="onSwitch(s.id)">{{ s.title }}</span>
              <button type="button" class="ai-chat__history-del" title="删除该对话" @click.stop="deleteSession(s.id)">×</button>
            </div>
          </div>
        </div>
        <button type="button" class="ai-chat__bar-btn ai-chat__bar-btn--new" @click="newConversation">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          新建对话
        </button>
      </div>
    </div>

    <!-- 消息列表 -->
    <div ref="scrollEl" class="ai-chat__scroll">
      <!-- 空状态 -->
      <div v-if="messages.length === 0" class="ai-chat__welcome">
        <div class="ai-chat__welcome-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M12 2a2 2 0 0 1 2 2v1h3a2 2 0 0 1 2 2v3h1a2 2 0 0 1 0 4h-1v3a2 2 0 0 1-2 2h-3v1a2 2 0 0 1-4 0v-1H7a2 2 0 0 1-2-2v-3H4a2 2 0 0 1 0-4h1V7a2 2 0 0 1 2-2h3V4a2 2 0 0 1 2-2z"/>
            <circle cx="9.5" cy="11" r="1.2" fill="currentColor"/>
            <circle cx="14.5" cy="11" r="1.2" fill="currentColor"/>
            <path d="M9 15c.8.7 1.9 1 3 1s2.2-.3 3-1"/>
          </svg>
        </div>
        <h3 class="ai-chat__welcome-title">智能制造工艺部 AI 助手</h3>
        <p class="ai-chat__welcome-sub">大模型驱动，整合考勤、制度、知识库、报表等全系统数据资源，并按你的角色权限安全作答。</p>
        <div class="ai-chat__suggestions">
          <button
            v-for="(s, idx) in suggestions"
            :key="idx"
            type="button"
            class="ai-chat__suggestion"
            @click="onSuggestion(s)"
          >{{ s }}</button>
        </div>
      </div>

      <!-- 消息 -->
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="ai-msg"
        :class="msg.role === 'user' ? 'ai-msg--user' : 'ai-msg--assistant'"
      >
        <div v-if="msg.role === 'assistant'" class="ai-msg__avatar" aria-hidden="true">AI</div>
        <div class="ai-msg__bubble">
          <!-- 技能调用提示 -->
          <div v-if="msg.tools && msg.tools.length" class="ai-msg__tools">
            <span
              v-for="(t, ti) in msg.tools"
              :key="ti"
              class="ai-tool-chip"
              :class="{ 'is-running': t.status === 'running' }"
            >
              <span class="ai-tool-chip__dot" :class="t.status === 'running' ? 'is-spin' : 'is-done'"></span>
              {{ t.label }}<span v-if="t.summary" class="ai-tool-chip__summary"> · {{ t.summary }}</span>
            </span>
          </div>

          <!-- 思考过程（思维链） -->
          <div v-if="msg.reasoning" class="ai-reason">
            <button type="button" class="ai-reason__toggle" @click="toggleReasoning(msg)">
              <svg class="ai-reason__caret" :class="{ 'is-open': isReasoningOpen(msg) }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <polyline points="9 18 15 12 9 6"/>
              </svg>
              <span class="ai-reason__title">
                {{ msg.streaming && !msg.content ? '正在思考…' : '思考过程' }}
              </span>
            </button>
            <div v-show="isReasoningOpen(msg)" class="ai-reason__body">{{ msg.reasoning }}</div>
          </div>

          <!-- 正文 -->
          <div
            v-if="msg.content"
            class="ai-msg__content md-body"
            v-html="renderMarkdown(msg.content)"
          ></div>

          <!-- 流式光标 / 加载（展示后端实时工作状态） -->
          <div v-if="msg.streaming && !msg.content && !msg.reasoning" class="ai-msg__typing">
            <span class="ai-msg__dots"><span></span><span></span><span></span></span>
            <span v-if="msg.status" class="ai-msg__status">{{ msg.status }}</span>
          </div>

          <!-- 附件（报表下载 / 图表预览） -->
          <div v-if="msg.attachments && msg.attachments.length" class="ai-msg__attachments">
            <template v-for="(att, ai2) in msg.attachments" :key="ai2">
              <div v-if="att.kind === 'image'" class="ai-chart-preview">
                <img class="ai-chart-preview__img" :src="att.url" :alt="att.label || att.filename" loading="lazy">
                <div class="ai-chart-preview__foot">
                  <span class="ai-chart-preview__label">{{ att.label || att.filename }}</span>
                  <a class="ai-chart-preview__dl" :href="att.url" :download="att.filename">下载 PNG</a>
                </div>
              </div>
              <a
                v-else
                class="ai-attachment"
                :href="att.url"
                :download="att.filename"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="12" y1="18" x2="12" y2="12"/>
                  <polyline points="9 15 12 18 15 15"/>
                </svg>
                <span class="ai-attachment__label">{{ att.label || att.filename }}</span>
                <span class="ai-attachment__ext">下载</span>
              </a>
            </template>
          </div>

          <!-- 错误 -->
          <div v-if="msg.error" class="ai-msg__error">{{ msg.error }}</div>
        </div>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="ai-chat__composer">
      <textarea
        ref="inputEl"
        v-model="draft"
        class="ai-chat__input"
        :rows="compact ? 1 : 2"
        :placeholder="placeholder"
        @keydown.enter.exact.prevent="onSend"
      ></textarea>
      <button
        v-if="loading"
        type="button"
        class="ai-chat__btn ai-chat__btn--stop"
        title="停止生成"
        @click="stop"
      >
        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
      </button>
      <button
        v-else
        type="button"
        class="ai-chat__btn ai-chat__btn--send"
        :disabled="!draft.trim()"
        title="发送 (Enter)"
        @click="onSend"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="22" y1="2" x2="11" y2="13"/>
          <polygon points="22 2 15 22 11 13 2 9 22 2"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useAiChat } from '@/composables/useAiChat'
import { renderMarkdown } from '@/utils/renderMarkdown'

const props = defineProps({
  compact: { type: Boolean, default: false },
})

const {
  messages, loading, send, stop,
  sessions, currentSessionId, currentModel,
  loadSessions, newConversation, switchSession, deleteSession, fetchModel,
} = useAiChat({ persist: !props.compact })

const historyOpen = ref(false)
const barEl = ref(null)

function onSwitch(id) {
  switchSession(id)
  historyOpen.value = false
}

function onBarOutsideClick(e) {
  if (barEl.value && !barEl.value.contains(e.target)) historyOpen.value = false
}

// 思考过程展开状态：用户未手动设置时，流式中默认展开、完成后默认折叠
const reasoningOpen = reactive({})
function isReasoningOpen(msg) {
  if (msg.id in reasoningOpen) return reasoningOpen[msg.id]
  return !!msg.streaming
}
function toggleReasoning(msg) {
  reasoningOpen[msg.id] = !isReasoningOpen(msg)
}

const draft = ref('')
const scrollEl = ref(null)
const inputEl = ref(null)

const placeholder = '输入你的问题，例如：查询我本月加班、导出本科室报表、科室男女比例、某工艺问题怎么处理…'

const suggestions = [
  '查询我本月的加班记录',
  '我们科室一共有多少人？男女比例如何？',
  '帮我导出我们科室今年的加班报表',
  '智能室最近的排班情况？',
  '统计我们科室近三个月加班趋势并生成图表',
  '公出（出差）报销有哪些规定？',
  '关于焊接变形的工艺问题怎么处理？',
  '2026 年端午节是哪天？',
]

function onSend() {
  const text = draft.value.trim()
  if (!text || loading.value) return
  draft.value = ''
  send(text)
}

function onSuggestion(text) {
  if (loading.value) return
  send(text)
}

function scrollToBottom() {
  nextTick(() => {
    if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
  })
}

watch(messages, scrollToBottom, { deep: true })

onMounted(() => {
  if (!props.compact) {
    loadSessions()
    fetchModel()
    document.addEventListener('click', onBarOutsideClick)
    if (inputEl.value) inputEl.value.focus()
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onBarOutsideClick)
})

defineExpose({ send })
</script>

<style scoped>
.ai-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--color-bg-container, #fff);
}

/* 顶部工具栏 */
.ai-chat__bar {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 14px;
  border-bottom: 1px solid var(--color-border-secondary, #eef0f3);
  background: var(--color-bg-container, #fff);
}
.ai-chat__model {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 12.5px;
  color: var(--color-text-secondary, #4b5563);
  overflow: hidden;
}
.ai-chat__model-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.18);
  flex: 0 0 auto;
}
.ai-chat__model-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ai-chat__bar-actions { display: flex; align-items: center; gap: 8px; flex: 0 0 auto; }
.ai-chat__history { position: relative; }
.ai-chat__bar-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 1px solid var(--color-border, #e5e7eb);
  background: var(--color-bg-layout, #f7f9fb);
  color: var(--color-text-secondary, #4b5563);
  padding: 5px 11px;
  border-radius: 8px;
  font-size: 12.5px;
  cursor: pointer;
  transition: all 0.16s ease;
}
.ai-chat__bar-btn:hover { border-color: var(--color-primary, #1890ff); color: var(--color-primary, #1890ff); }
.ai-chat__bar-btn svg { width: 13px; height: 13px; }
.ai-chat__bar-btn--new { background: var(--color-primary-bg, #e6f4ff); color: var(--color-primary, #1890ff); border-color: rgba(24, 144, 255, 0.3); }
.ai-chat__history-pop {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  width: 260px;
  max-height: 320px;
  overflow-y: auto;
  background: #fff;
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.16);
  padding: 6px;
  z-index: 20;
}
.ai-chat__history-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 8px;
  border-radius: 7px;
  cursor: pointer;
}
.ai-chat__history-item:hover { background: var(--color-bg-layout, #f5f7fa); }
.ai-chat__history-item.is-current { background: var(--color-primary-bg, #e6f4ff); }
.ai-chat__history-title {
  flex: 1 1 auto;
  font-size: 13px;
  color: var(--color-text-primary, #1f2937);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-chat__history-del {
  flex: 0 0 auto;
  border: none;
  background: none;
  color: var(--color-text-quaternary, #c0c4cc);
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  padding: 0 4px;
}
.ai-chat__history-del:hover { color: var(--color-error, #ff4d4f); }

.ai-chat__scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding: var(--spacing-lg, 16px);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md, 12px);
  scroll-behavior: smooth;
}

/* 欢迎/空状态 */
.ai-chat__welcome {
  margin: auto;
  text-align: center;
  max-width: 560px;
  padding: var(--spacing-lg, 16px);
}
.ai-chat__welcome-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto var(--spacing-md, 12px);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, #1890ff, #36cfc9);
  box-shadow: 0 8px 20px rgba(24, 144, 255, 0.28);
}
.ai-chat__welcome-icon svg { width: 30px; height: 30px; }
.ai-chat__welcome-title {
  margin: 0 0 6px;
  font-size: var(--font-size-lg, 18px);
  font-weight: 700;
  color: var(--color-text-primary, #1f2937);
}
.ai-chat__welcome-sub {
  margin: 0 0 var(--spacing-lg, 16px);
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text-tertiary, #8c8c8c);
  line-height: 1.6;
}
.ai-chat__suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}
.ai-chat__suggestion {
  border: 1px solid var(--color-border, #e5e7eb);
  background: var(--color-bg-layout, #f7f9fb);
  color: var(--color-text-secondary, #4b5563);
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.18s ease;
}
.ai-chat__suggestion:hover {
  border-color: var(--color-primary, #1890ff);
  color: var(--color-primary, #1890ff);
  background: var(--color-primary-bg, #e6f4ff);
}

/* 消息 */
.ai-msg {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  max-width: 100%;
}
.ai-msg--user { flex-direction: row-reverse; }
.ai-msg__avatar {
  flex: 0 0 auto;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #1890ff, #36cfc9);
}
.ai-msg__bubble {
  max-width: min(88%, 720px);
  padding: 10px 14px;
  border-radius: 14px;
  font-size: var(--font-size-sm, 14px);
  line-height: 1.65;
  word-break: break-word;
}
.ai-msg--user .ai-msg__bubble {
  background: var(--color-primary, #1890ff);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.ai-msg--assistant .ai-msg__bubble {
  background: var(--color-bg-layout, #f5f7fa);
  color: var(--color-text-primary, #1f2937);
  border-bottom-left-radius: 4px;
  border: 1px solid var(--color-border-secondary, #eef0f3);
}

/* 技能调用 chip */
.ai-msg__tools {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.ai-tool-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--color-primary-bg, #e6f4ff);
  color: var(--color-primary, #1890ff);
  border: 1px solid rgba(24, 144, 255, 0.25);
}
.ai-tool-chip__dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: currentColor;
}
.ai-tool-chip__dot.is-spin { animation: aiPulse 1s ease-in-out infinite; }
.ai-tool-chip__summary { opacity: 0.8; }

/* 思考过程（思维链） */
.ai-reason {
  margin-bottom: 8px;
  border-left: 2px solid var(--color-border, #e5e7eb);
  padding-left: 10px;
}
.ai-reason__toggle {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: none;
  border: none;
  padding: 2px 0;
  cursor: pointer;
  color: var(--color-text-tertiary, #8c8c8c);
  font-size: 12px;
}
.ai-reason__toggle:hover { color: var(--color-primary, #1890ff); }
.ai-reason__caret {
  width: 13px;
  height: 13px;
  transition: transform 0.18s ease;
}
.ai-reason__caret.is-open { transform: rotate(90deg); }
.ai-reason__title { font-weight: 500; }
.ai-reason__body {
  margin-top: 4px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--color-text-tertiary, #8c8c8c);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 260px;
  overflow-y: auto;
}

/* 正文 markdown */
.ai-msg__content :deep(.md-p) { margin: 0 0 8px; }
.ai-msg__content :deep(.md-p:last-child) { margin-bottom: 0; }
.ai-msg__content :deep(.md-h) { margin: 10px 0 6px; font-size: 15px; font-weight: 700; }
.ai-msg__content :deep(.md-ul),
.ai-msg__content :deep(.md-ol) { margin: 4px 0 8px; padding-left: 20px; }
.ai-msg__content :deep(li) { margin: 2px 0; }
.ai-msg__content :deep(.md-code) {
  background: rgba(0,0,0,0.06);
  padding: 1px 5px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.9em;
}
.ai-msg__content :deep(.md-pre) {
  background: #1e293b;
  color: #e2e8f0;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}
.ai-msg__content :deep(.md-pre code) { background: none; padding: 0; }
.ai-msg__content :deep(.md-link) { color: var(--color-primary, #1890ff); text-decoration: underline; }
.ai-msg--user .ai-msg__content :deep(.md-link) { color: #fff; }
.ai-msg__content :deep(.md-table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
  font-size: 13px;
}
.ai-msg__content :deep(.md-table th),
.ai-msg__content :deep(.md-table td) {
  border: 1px solid var(--color-border, #e5e7eb);
  padding: 6px 10px;
  text-align: left;
}
.ai-msg__content :deep(.md-table th) {
  background: var(--color-bg-layout, #f0f5ff);
  font-weight: 600;
}

/* typing */
.ai-msg__typing { display: inline-flex; align-items: center; gap: 8px; padding: 4px 0; }
.ai-msg__dots { display: inline-flex; gap: 4px; }
.ai-msg__dots span {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--color-text-quaternary, #c0c4cc);
  animation: aiBounce 1.2s infinite ease-in-out;
}
.ai-msg__dots span:nth-child(2) { animation-delay: 0.15s; }
.ai-msg__dots span:nth-child(3) { animation-delay: 0.3s; }
.ai-msg__status {
  font-size: 12.5px;
  color: var(--color-text-tertiary, #6b7280);
  animation: aiStatusFade 0.25s ease;
}
@keyframes aiStatusFade {
  from { opacity: 0; transform: translateY(2px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 附件 */
.ai-msg__attachments { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; }
.ai-chart-preview {
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
  max-width: 100%;
}
.ai-chart-preview__img {
  display: block;
  width: 100%;
  max-width: 520px;
  height: auto;
}
.ai-chart-preview__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 12px;
  background: var(--color-bg-layout, #f5f7fa);
  font-size: 13px;
}
.ai-chart-preview__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-text-primary, #1f2937);
}
.ai-chart-preview__dl {
  flex: 0 0 auto;
  color: var(--color-primary, #1890ff);
  text-decoration: none;
  font-weight: 600;
}
.ai-chart-preview__dl:hover { text-decoration: underline; }
.ai-attachment {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid var(--color-border, #e5e7eb);
  color: var(--color-text-primary, #1f2937);
  text-decoration: none;
  font-size: 13px;
  transition: all 0.18s ease;
  max-width: 100%;
}
.ai-attachment:hover {
  border-color: var(--color-primary, #1890ff);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.15);
}
.ai-attachment svg { width: 18px; height: 18px; color: #16a34a; flex: 0 0 auto; }
.ai-attachment__label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ai-attachment__ext {
  margin-left: auto;
  color: var(--color-primary, #1890ff);
  font-weight: 600;
  flex: 0 0 auto;
}

.ai-msg__error {
  margin-top: 6px;
  color: var(--color-error, #ff4d4f);
  font-size: 13px;
}

/* 输入区 */
.ai-chat__composer {
  flex: 0 0 auto;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: var(--spacing-md, 12px);
  border-top: 1px solid var(--color-border-secondary, #eef0f3);
  background: var(--color-bg-container, #fff);
}
.ai-chat__input {
  flex: 1 1 auto;
  resize: none;
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 14px;
  line-height: 1.5;
  font-family: inherit;
  max-height: 140px;
  outline: none;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
  background: var(--color-bg-layout, #f7f9fb);
}
.ai-chat__input:focus {
  border-color: var(--color-primary, #1890ff);
  box-shadow: 0 0 0 3px rgba(24, 144, 255, 0.12);
  background: #fff;
}
.ai-chat__btn {
  flex: 0 0 auto;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  transition: all 0.18s ease;
}
.ai-chat__btn svg { width: 20px; height: 20px; }
.ai-chat__btn--send { background: var(--color-primary, #1890ff); }
.ai-chat__btn--send:hover:not(:disabled) { background: var(--color-primary-hover, #40a9ff); }
.ai-chat__btn--send:disabled { opacity: 0.45; cursor: not-allowed; }
.ai-chat__btn--stop { background: var(--color-error, #ff4d4f); }
.ai-chat__btn--stop:hover { background: #ff7875; }

/* 紧凑模式（首页卡片） */
.ai-chat--compact .ai-chat__scroll { padding: var(--spacing-md, 12px); gap: 10px; }
.ai-chat--compact .ai-chat__welcome { padding: 4px; }
.ai-chat--compact .ai-chat__welcome-icon { width: 44px; height: 44px; margin-bottom: 8px; }
.ai-chat--compact .ai-chat__welcome-icon svg { width: 24px; height: 24px; }
.ai-chat--compact .ai-chat__welcome-title { font-size: 15px; }
.ai-chat--compact .ai-chat__welcome-sub { font-size: 12px; margin-bottom: 12px; }
.ai-chat--compact .ai-chat__suggestion { padding: 6px 11px; font-size: 12px; }
.ai-chat--compact .ai-msg__bubble { font-size: 13px; padding: 8px 11px; }
.ai-chat--compact .ai-chat__composer { padding: 10px; }
.ai-chat--compact .ai-chat__btn { width: 36px; height: 36px; }

@keyframes aiBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
  30% { transform: translateY(-5px); opacity: 1; }
}
@keyframes aiPulse {
  0%, 100% { opacity: 0.4; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}
</style>
