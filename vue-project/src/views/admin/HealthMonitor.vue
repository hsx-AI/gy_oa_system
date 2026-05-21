<template>
  <div class="health-monitor-page">
    <div class="container">
      <header class="page-header">
        <div class="header-content">
          <div class="header-info">
            <h1 class="header-title">系统管理员页面</h1>
            <p class="header-subtitle">系统配置与各组件连接状态（仅系统管理员 webconfig.admin1）</p>
          </div>
          <div class="header-actions">
            <button type="button" class="btn btn-primary" :disabled="loading" @click="fetchOverview">
              <span v-if="loading">检测中…</span>
              <span v-else>刷新</span>
            </button>
            <button type="button" class="btn btn-secondary" :disabled="todoReminderLoading" @click="triggerTodoReminder">
              <span v-if="todoReminderLoading">发送中…</span>
              <span v-else>触发待办提醒</span>
            </button>
          </div>
        </div>
      </header>

      <div v-if="!canAccess" class="card no-permission">
        <p>您暂无权限访问此页面，仅系统管理员（webconfig.admin1 对应用户）可查看。</p>
        <router-link to="/" class="btn btn-primary">返回首页</router-link>
      </div>

      <template v-else>
        <section class="card admin-config-card">
          <div class="config-card-head">
            <div>
              <h2 class="section-title">排班邮件功能配置</h2>
              <p class="section-desc">控制各科室是否启用周排班自动发送、手动发送和发送提醒。</p>
            </div>
            <div class="config-actions">
              <button type="button" class="btn btn-secondary btn-sm" :disabled="shiftEmailLoading || shiftEmailSaving" @click="setAllShiftEmailEnabled(true)">全选</button>
              <button type="button" class="btn btn-secondary btn-sm" :disabled="shiftEmailLoading || shiftEmailSaving" @click="setAllShiftEmailEnabled(false)">全部关闭</button>
              <button type="button" class="btn btn-primary btn-sm" :disabled="shiftEmailLoading || shiftEmailSaving" @click="saveShiftEmailConfig">
                {{ shiftEmailSaving ? '保存中…' : '保存配置' }}
              </button>
            </div>
          </div>
          <div v-if="shiftEmailLoading" class="status-message">正在加载排班邮件功能配置…</div>
          <div v-else-if="!shiftEmailItems.length" class="status-message">暂无可配置科室。</div>
          <div v-else class="dept-switch-grid">
            <label v-for="item in shiftEmailItems" :key="item.department" class="dept-switch">
              <span class="dept-name">{{ item.department }}</span>
              <input v-model="item.enabled" type="checkbox">
              <span class="switch-visual" :class="{ 'is-on': item.enabled }"></span>
              <span class="switch-text" :class="{ 'is-on': item.enabled }">{{ item.enabled ? '启用' : '关闭' }}</span>
            </label>
          </div>
          <p v-if="shiftEmailMessage" class="config-message">{{ shiftEmailMessage }}</p>
        </section>

        <div class="status-grid">
          <div
            v-for="item in items"
            :key="item.id"
            class="card status-card"
            :class="'status-' + item.status"
          >
            <div class="status-header">
              <span class="status-name">{{ item.name }}</span>
              <span class="status-badge" :class="'badge-' + item.status">
                {{ statusLabel(item.status) }}
              </span>
            </div>
            <p class="status-message">{{ item.message || '—' }}</p>
          </div>
        </div>
        <div v-if="todoReminderResult" class="card todo-reminder-result">
          <div class="status-header">
            <span class="status-name">待办提醒执行结果</span>
            <span class="status-badge" :class="todoReminderResult.error ? 'badge-error' : 'badge-ok'">
              {{ todoReminderResult.error ? '失败' : '成功' }}
            </span>
          </div>
          <pre v-if="todoReminderResult.error" class="status-message">{{ todoReminderResult.error }}</pre>
          <div v-else class="status-message">
            <p><strong>状态：</strong>{{ todoReminderResult.message || '—' }}</p>
            <p>检查人数：{{ todoReminderResult.checked || 0 }}</p>
            <p>发送邮件：{{ todoReminderResult.sent || 0 }} 封</p>
            <p v-if="todoReminderResult.skippedOverThreshold">跳过（3天内已发）：{{ todoReminderResult.skippedOverThreshold }} 人</p>
            <p v-if="todoReminderResult.failures?.length">
              失败：{{ todoReminderResult.failures.map(f => f.name).join('、') }}
            </p>
            <div v-if="todoReminderResult._debugOverThreshold?.length" class="debug-list">
              <p><strong>调试（邮箱未配置，待发送）：</strong></p>
              <table class="debug-table">
                <thead>
                  <tr><th>姓名</th><th>待办数</th><th>邮箱</th></tr>
                </thead>
                <tbody>
                  <tr v-for="item in todoReminderResult._debugOverThreshold" :key="item.name">
                    <td>{{ item.name }}</td>
                    <td>{{ item.count }}</td>
                    <td>{{ item.email || '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
        <p class="update-hint">最后更新：{{ lastUpdateText }}</p>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  getHealthMonitorPermission,
  getHealthOverview,
  getShiftEmailFeatureConfig,
  saveShiftEmailFeatureConfig,
  runTodoReminder,
} from '@/api/healthMonitor'

const router = useRouter()
const canAccess = ref(false)
const loading = ref(false)
const items = ref([])
const lastUpdate = ref(null)
const todoReminderLoading = ref(false)
const todoReminderResult = ref(null)
const shiftEmailLoading = ref(false)
const shiftEmailSaving = ref(false)
const shiftEmailItems = ref([])
const shiftEmailMessage = ref('')

const lastUpdateText = computed(() => {
  if (!lastUpdate.value) return '—'
  const d = new Date(lastUpdate.value)
  return d.toLocaleString('zh-CN')
})

function statusLabel(status) {
  const map = { ok: '正常', error: '异常', unconfigured: '未配置' }
  return map[status] || status
}

async function fetchOverview() {
  const user = JSON.parse(localStorage.getItem('userInfo') || '{}')
  const name = (user.name || user.userName || '').trim()
  if (!name) {
    router.replace('/login')
    return
  }
  loading.value = true
  try {
    const res = await getHealthOverview({ current_user: name })
    if (res && res.success && Array.isArray(res.items)) {
      items.value = res.items
      lastUpdate.value = new Date().toISOString()
    }
  } catch (e) {
    console.error(e)
    items.value = []
  } finally {
    loading.value = false
  }
}

async function fetchShiftEmailConfig() {
  const user = JSON.parse(localStorage.getItem('userInfo') || '{}')
  const name = (user.name || user.userName || '').trim()
  if (!name) return
  shiftEmailLoading.value = true
  shiftEmailMessage.value = ''
  try {
    const res = await getShiftEmailFeatureConfig({ current_user: name })
    shiftEmailItems.value = (res?.items || []).map((item) => ({
      department: item.department,
      enabled: !!item.enabled,
    }))
  } catch (e) {
    console.error(e)
    shiftEmailItems.value = []
    shiftEmailMessage.value = e?.response?.data?.detail || e?.message || '排班邮件功能配置加载失败'
  } finally {
    shiftEmailLoading.value = false
  }
}

function setAllShiftEmailEnabled(enabled) {
  shiftEmailItems.value.forEach((item) => {
    item.enabled = enabled
  })
}

async function saveShiftEmailConfig() {
  const user = JSON.parse(localStorage.getItem('userInfo') || '{}')
  const name = (user.name || user.userName || '').trim()
  if (!name) return
  shiftEmailSaving.value = true
  shiftEmailMessage.value = ''
  try {
    const enabledDepartments = shiftEmailItems.value
      .filter((item) => item.enabled)
      .map((item) => item.department)
    const res = await saveShiftEmailFeatureConfig({
      current_user: name,
      enabled_departments: enabledDepartments,
    })
    shiftEmailItems.value = (res?.items || []).map((item) => ({
      department: item.department,
      enabled: !!item.enabled,
    }))
    shiftEmailMessage.value = res?.message || '排班邮件功能配置已保存'
  } catch (e) {
    shiftEmailMessage.value = e?.response?.data?.detail || e?.message || '保存排班邮件功能配置失败'
  } finally {
    shiftEmailSaving.value = false
  }
}

async function triggerTodoReminder() {
  const user = JSON.parse(localStorage.getItem('userInfo') || '{}')
  const name = (user.name || user.userName || '').trim()
  if (!name) return
  todoReminderLoading.value = true
  todoReminderResult.value = null
  try {
    const res = await runTodoReminder({ current_user: name })
    todoReminderResult.value = res?.result || res
  } catch (e) {
    todoReminderResult.value = { error: e?.response?.data?.detail || e?.message || '请求失败' }
  } finally {
    todoReminderLoading.value = false
  }
}

onMounted(async () => {
  const user = JSON.parse(localStorage.getItem('userInfo') || '{}')
  const name = (user.name || user.userName || '').trim()
  if (!name) {
    router.replace('/login')
    return
  }
  try {
    const res = await getHealthMonitorPermission({ current_user: name })
    canAccess.value = !!(res && res.canAccess)
    if (canAccess.value) {
      await Promise.all([fetchOverview(), fetchShiftEmailConfig()])
    }
  } catch {
    canAccess.value = false
  }
})
</script>

<style scoped>
.health-monitor-page {
  min-height: 100vh;
  background: var(--color-bg-layout);
}
.health-monitor-page .container {
  max-width: 900px;
  margin: 0 auto;
  padding: var(--spacing-xl) var(--spacing-lg);
}
.page-header {
  margin-bottom: var(--spacing-xl);
}
.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--spacing-md);
}
.header-title {
  margin: 0 0 4px 0;
  font-size: 1.35rem;
  font-weight: 600;
}
.header-subtitle {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 0.9rem;
}
.no-permission {
  text-align: center;
  padding: var(--spacing-xxl);
}
.no-permission p {
  margin-bottom: var(--spacing-lg);
}
.admin-config-card {
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}
.config-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}
.section-title {
  margin: 0 0 4px 0;
  font-size: 1.05rem;
  font-weight: 600;
}
.section-desc {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 0.86rem;
}
.config-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
  justify-content: flex-end;
}
.dept-switch-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 10px;
}
.dept-switch {
  position: relative;
  display: grid;
  grid-template-columns: 1fr auto auto;
  align-items: center;
  gap: 10px;
  min-height: 40px;
  padding: 8px 10px;
  border: 1px solid var(--color-border-base);
  border-radius: 8px;
  background: var(--color-bg-container);
}
.dept-switch input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
.dept-name {
  font-size: 0.9rem;
  font-weight: 500;
}
.switch-visual {
  position: relative;
  width: 38px;
  height: 20px;
  border-radius: 999px;
  background: #cbd5e1;
  transition: background-color 0.15s ease;
}
.switch-visual::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.15s ease;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.24);
}
.switch-visual.is-on {
  background: #2563eb;
}
.switch-visual.is-on::after {
  transform: translateX(18px);
}
.switch-text {
  min-width: 32px;
  font-size: 0.8rem;
  color: var(--color-text-tertiary);
}
.switch-text.is-on {
  color: #166534;
}
.config-message {
  margin: var(--spacing-sm) 0 0;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}
.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--spacing-lg);
}
.status-card {
  padding: var(--spacing-lg);
  border-left: 4px solid var(--color-border);
}
.status-card.status-ok {
  border-left-color: #22c55e;
}
.status-card.status-error {
  border-left-color: #ef4444;
}
.status-card.status-unconfigured {
  border-left-color: #94a3b8;
}
.status-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}
.status-name {
  font-weight: 600;
  font-size: 1rem;
}
.status-badge {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 999px;
  font-weight: 500;
}
.badge-ok {
  background: #dcfce7;
  color: #166534;
}
.badge-error {
  background: #fee2e2;
  color: #b91c1c;
}
.badge-unconfigured {
  background: #f1f5f9;
  color: #64748b;
}
.status-message {
  margin: 0;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  line-height: 1.4;
}
.update-hint {
  margin-top: var(--spacing-xl);
  font-size: 0.85rem;
  color: var(--color-text-tertiary);
}

/* 触发待办提醒按钮 */
.btn-secondary {
  color: var(--color-text-primary);
  background-color: var(--color-bg-container);
  border-color: var(--color-border-base);
}
.btn-secondary:hover:not(:disabled) {
  background-color: var(--color-bg-layout);
}

/* 执行结果卡片 */
.todo-reminder-result {
  margin-top: var(--spacing-lg);
  padding: var(--spacing-lg);
}
.todo-reminder-result pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 0.875rem;
}
.todo-reminder-result p {
  margin: 2px 0;
  font-size: 0.875rem;
}
.debug-list {
  margin-top: 8px;
}
.debug-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
  margin-top: 4px;
}
.debug-table th,
.debug-table td {
  border: 1px solid var(--color-border-base);
  padding: 4px 8px;
  text-align: left;
}
.debug-table th {
  background: var(--color-bg-layout);
  font-weight: 600;
}

@media (max-width: 640px) {
  .config-card-head {
    display: block;
  }
  .config-actions {
    justify-content: flex-start;
    margin-top: var(--spacing-md);
  }
}
</style>
