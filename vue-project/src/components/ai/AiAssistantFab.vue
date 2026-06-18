<template>
  <div class="ai-fab">
    <!-- 悬浮对话窗 -->
    <transition name="ai-fab-pop">
      <section v-if="open" class="ai-fab__panel" role="dialog" aria-label="AI 助手对话窗">
        <header class="ai-fab__head">
          <span class="ai-fab__head-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <rect x="4" y="7" width="16" height="12" rx="3" />
              <path d="M12 7V4" /><circle cx="12" cy="3" r="1" />
              <circle cx="9" cy="13" r="1.3" fill="currentColor" stroke="none" />
              <circle cx="15" cy="13" r="1.3" fill="currentColor" stroke="none" />
              <path d="M9.5 16.5c.7.5 1.6.7 2.5.7s1.8-.2 2.5-.7" />
            </svg>
          </span>
          <div class="ai-fab__head-text">
            <strong>智能制造工艺部 AI 助手</strong>
            <span>大模型驱动 · 按角色权限安全问答</span>
          </div>
          <button type="button" class="ai-fab__head-btn" title="全屏对话" @click="goFull">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <polyline points="15 3 21 3 21 9" /><polyline points="9 21 3 21 3 15" />
              <line x1="21" y1="3" x2="14" y2="10" /><line x1="3" y1="21" x2="10" y2="14" />
            </svg>
          </button>
          <button type="button" class="ai-fab__head-btn" title="收起" @click="open = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </header>
        <div class="ai-fab__body">
          <AiAssistantChat />
        </div>
      </section>
    </transition>

    <!-- 机器人气泡按钮 -->
    <button
      type="button"
      class="ai-fab__btn"
      :class="{ 'is-open': open }"
      :aria-label="open ? '收起 AI 助手' : '打开 AI 助手'"
      @click="open = !open"
    >
      <svg v-if="!open" class="ai-fab__btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
        <rect x="4" y="7" width="16" height="12" rx="3.5" />
        <path d="M12 7V4" /><circle cx="12" cy="3" r="1.1" fill="currentColor" stroke="none" />
        <circle cx="9" cy="13" r="1.5" fill="currentColor" stroke="none" />
        <circle cx="15" cy="13" r="1.5" fill="currentColor" stroke="none" />
        <path d="M9.3 16.3c.8.6 1.7.9 2.7.9s1.9-.3 2.7-.9" />
        <path d="M2 12v2M22 12v2" />
      </svg>
      <svg v-else class="ai-fab__btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
      </svg>
      <span v-if="!open" class="ai-fab__btn-pulse" aria-hidden="true"></span>
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AiAssistantChat from '@/components/ai/AiAssistantChat.vue'

const router = useRouter()
const open = ref(false)

function goFull() {
  open.value = false
  router.push('/ai-assistant')
}
</script>

<style scoped>
.ai-fab {
  position: fixed;
  right: 28px;
  bottom: 28px;
  z-index: 1200;
}

/* 气泡按钮 */
.ai-fab__btn {
  position: relative;
  width: 58px;
  height: 58px;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  color: #fff;
  background: linear-gradient(135deg, #1890ff, #36cfc9);
  box-shadow: 0 10px 26px rgba(24, 144, 255, 0.42);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: auto;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.ai-fab__btn:hover { transform: translateY(-2px) scale(1.04); box-shadow: 0 14px 30px rgba(24, 144, 255, 0.5); }
.ai-fab__btn.is-open { background: linear-gradient(135deg, #64748b, #94a3b8); box-shadow: 0 8px 20px rgba(100, 116, 139, 0.4); }
.ai-fab__btn-icon { width: 30px; height: 30px; }
.ai-fab__btn-pulse {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid rgba(24, 144, 255, 0.55);
  animation: aiFabPulse 2s ease-out infinite;
}
@keyframes aiFabPulse {
  0% { transform: scale(1); opacity: 0.7; }
  100% { transform: scale(1.55); opacity: 0; }
}

/* 对话面板 */
.ai-fab__panel {
  position: absolute;
  right: 0;
  bottom: 72px;
  width: 400px;
  height: min(620px, calc(100vh - 140px));
  display: flex;
  flex-direction: column;
  background: var(--color-bg-container, #fff);
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 16px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.26);
  overflow: hidden;
}
.ai-fab__head {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  color: #fff;
  background: linear-gradient(120deg, #1890ff, #36cfc9);
}
.ai-fab__head-icon {
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
}
.ai-fab__head-icon svg { width: 22px; height: 22px; }
.ai-fab__head-text { flex: 1 1 auto; min-width: 0; line-height: 1.3; }
.ai-fab__head-text strong { display: block; font-size: 14px; font-weight: 600; }
.ai-fab__head-text span {
  display: block;
  font-size: 11.5px;
  opacity: 0.9;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-fab__head-btn {
  flex: 0 0 auto;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.16s ease;
}
.ai-fab__head-btn:hover { background: rgba(255, 255, 255, 0.32); }
.ai-fab__head-btn svg { width: 16px; height: 16px; }
.ai-fab__body { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; }

/* 进出场动画 */
.ai-fab-pop-enter-active, .ai-fab-pop-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; transform-origin: bottom right; }
.ai-fab-pop-enter-from, .ai-fab-pop-leave-to { opacity: 0; transform: translateY(12px) scale(0.96); }

@media (max-width: 560px) {
  .ai-fab { right: 16px; bottom: 16px; }
  .ai-fab__panel {
    position: fixed;
    right: 12px;
    left: 12px;
    bottom: 84px;
    width: auto;
    height: min(70vh, calc(100vh - 120px));
  }
}
</style>
