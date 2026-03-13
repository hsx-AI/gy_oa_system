<template>
  <div class="health-monitor-page">
    <div class="container">
      <header class="page-header">
        <div class="header-content">
          <div class="header-info">
            <h1 class="header-title">系统健康监控</h1>
            <p class="header-subtitle">各组件连接与可用性状态（仅系统管理员 webconfig.admin1）</p>
          </div>
          <div class="header-actions">
            <button type="button" class="btn btn-primary" :disabled="loading" @click="fetchOverview">
              <span v-if="loading">检测中…</span>
              <span v-else>刷新</span>
            </button>
          </div>
        </div>
      </header>

      <div v-if="!canAccess" class="card no-permission">
        <p>您暂无权限访问此页面，仅系统管理员（webconfig.admin1 对应用户）可查看。</p>
        <router-link to="/" class="btn btn-primary">返回首页</router-link>
      </div>

      <template v-else>
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
        <p class="update-hint">最后更新：{{ lastUpdateText }}</p>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getHealthMonitorPermission, getHealthOverview } from '@/api/healthMonitor'

const router = useRouter()
const canAccess = ref(false)
const loading = ref(false)
const items = ref([])
const lastUpdate = ref(null)

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
    if (canAccess.value) await fetchOverview()
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
</style>
