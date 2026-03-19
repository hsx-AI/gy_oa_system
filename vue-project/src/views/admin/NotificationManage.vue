<template>
  <div class="notification-manage-page">
    <div class="container">
      <header class="page-header">
        <div class="header-content">
          <div class="header-info">
            <h1 class="header-title">消息推送管理</h1>
            <p class="header-subtitle">发布更新通知，员工登录时将看到所有未读通知的弹窗（仅系统管理员 admin1）</p>
          </div>
        </div>
      </header>

      <div v-if="!canAccess" class="card no-permission">
        <p>您暂无权限访问此页面，仅系统管理员（webconfig.admin1 对应用户）可操作。</p>
        <router-link to="/" class="btn btn-primary">返回首页</router-link>
      </div>

      <template v-else>
        <!-- 发布新通知 -->
        <div class="card edit-section">
          <h2 class="section-title">发布新通知</h2>
          <p class="section-hint">每次发布会新增一条通知记录。未读的员工下次登录将依次看到所有错过的通知。</p>
          <form @submit.prevent="handlePublish">
            <textarea
              v-model="newContent"
              class="notification-textarea"
              rows="6"
              placeholder="请输入通知内容（支持换行）…"
            ></textarea>
            <div class="form-actions">
              <button type="submit" class="btn btn-primary" :disabled="submitting || !newContent.trim()">
                {{ submitting ? '发布中…' : '发布通知' }}
              </button>
            </div>
          </form>
          <div v-if="resultMsg" class="result-msg" :class="{ success: resultOk, error: !resultOk }">
            {{ resultMsg }}
          </div>
        </div>

        <!-- 历史通知列表 -->
        <div class="card history-section">
          <h2 class="section-title">历史通知 <span class="badge">{{ historyList.length }}</span></h2>
          <div v-if="historyLoading" class="loading-text">加载中…</div>
          <div v-else-if="!historyList.length" class="empty-text">暂无通知记录</div>
          <div v-else class="history-list">
            <div v-for="item in historyList" :key="item.id" class="history-item">
              <div class="history-meta">
                <span class="history-id">#{{ item.id }}</span>
                <span class="history-time">{{ item.time }}</span>
                <span class="history-publisher">{{ item.publisher }}</span>
                <button type="button" class="btn-delete" @click="handleDelete(item)" :disabled="deleting === item.id">
                  {{ deleting === item.id ? '删除中…' : '删除' }}
                </button>
              </div>
              <div class="history-body" v-html="renderContent(item.content)"></div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { publishNotification, listNotifications, deleteNotification } from '@/api/admin'
import { getUploadConfig } from '@/api/attendance'

const canAccess = ref(false)
const newContent = ref('')
const submitting = ref(false)
const resultMsg = ref('')
const resultOk = ref(false)
const historyList = ref([])
const historyLoading = ref(false)
const deleting = ref(null)

function renderContent(text) {
  if (!text) return ''
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')
}

function getCurrentUser() {
  try {
    const u = JSON.parse(localStorage.getItem('userInfo') || '{}')
    return (u.name || u.userName || '').trim()
  } catch { return '' }
}

onMounted(async () => {
  const name = getCurrentUser()
  if (!name) return
  try {
    const cfg = await getUploadConfig()
    const a1 = (cfg?.admin1 || '').trim()
    canAccess.value = !!(a1 && name === a1)
  } catch {
    canAccess.value = false
  }
  if (canAccess.value) loadHistory()
})

async function loadHistory() {
  historyLoading.value = true
  try {
    const res = await listNotifications()
    historyList.value = (res && res.items) || []
  } catch { historyList.value = [] }
  finally { historyLoading.value = false }
}

async function handlePublish() {
  if (!newContent.value.trim()) return
  if (!confirm('确认发布此通知？')) return
  submitting.value = true
  resultMsg.value = ''
  try {
    const res = await publishNotification({
      current_user: getCurrentUser(),
      content: newContent.value.trim(),
    })
    if (res && res.success) {
      resultOk.value = true
      resultMsg.value = res.message || '发布成功'
      newContent.value = ''
      await loadHistory()
    } else {
      resultOk.value = false
      resultMsg.value = res?.message || '发布失败'
    }
  } catch (e) {
    resultOk.value = false
    resultMsg.value = e?.response?.data?.message || e?.message || '发布失败'
  } finally {
    submitting.value = false
  }
}

async function handleDelete(item) {
  if (!confirm(`确认删除通知 #${item.id}？`)) return
  deleting.value = item.id
  try {
    const res = await deleteNotification({ current_user: getCurrentUser(), id: item.id })
    if (res && res.success) {
      historyList.value = historyList.value.filter(i => i.id !== item.id)
    } else {
      alert(res?.message || '删除失败')
    }
  } catch (e) {
    alert(e?.response?.data?.message || '删除失败')
  } finally {
    deleting.value = null
  }
}
</script>

<style scoped>
.notification-manage-page {
  padding: 24px;
  max-width: 860px;
  margin: 0 auto;
}
.container { display: flex; flex-direction: column; gap: 20px; }
.page-header { margin-bottom: 4px; }
.header-title { font-size: 22px; font-weight: 700; color: var(--color-text-primary, #1a202c); }
.header-subtitle { font-size: 13px; color: var(--color-text-tertiary, #a0aec0); margin-top: 4px; }
.card {
  background: var(--color-bg-card, #fff);
  border-radius: var(--radius-lg, 12px);
  padding: 24px;
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,.08));
}
.no-permission { text-align: center; padding: 48px 24px; color: var(--color-text-secondary, #718096); }
.no-permission .btn { margin-top: 16px; display: inline-block; }
.section-title { font-size: 16px; font-weight: 600; margin-bottom: 12px; color: var(--color-text-primary, #1a202c); }
.section-hint { font-size: 13px; color: var(--color-text-tertiary, #a0aec0); margin-bottom: 12px; }
.badge {
  display: inline-block;
  font-size: 12px;
  background: var(--color-bg-secondary, #edf2f7);
  color: var(--color-text-secondary, #718096);
  padding: 1px 8px;
  border-radius: 10px;
  margin-left: 6px;
  font-weight: 500;
}

.notification-textarea {
  width: 100%;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-base, 8px);
  padding: 12px 14px;
  font-size: 14px;
  line-height: 1.7;
  resize: vertical;
  font-family: inherit;
  background: var(--color-bg-secondary, #f7fafc);
  color: var(--color-text-primary, #1a202c);
  transition: border-color .2s;
  box-sizing: border-box;
}
.notification-textarea:focus { outline: none; border-color: var(--color-primary, #4299e1); }

.form-actions { display: flex; gap: 12px; margin-top: 14px; }
.btn {
  padding: 8px 20px;
  border-radius: var(--radius-base, 8px);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: background .2s, opacity .2s;
}
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn-primary { background: var(--color-primary, #4299e1); color: #fff; }
.btn-primary:hover:not(:disabled) { background: var(--color-primary-hover, #3182ce); }

.result-msg { margin-top: 12px; font-size: 14px; padding: 10px 14px; border-radius: var(--radius-base, 8px); }
.result-msg.success { background: #f0fff4; color: #276749; border: 1px solid #c6f6d5; }
.result-msg.error { background: #fff5f5; color: #c53030; border: 1px solid #feb2b2; }

.loading-text, .empty-text { font-size: 14px; color: var(--color-text-tertiary, #a0aec0); padding: 12px 0; }

.history-list { display: flex; flex-direction: column; gap: 14px; }
.history-item {
  background: var(--color-bg-secondary, #f7fafc);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-base, 8px);
  padding: 14px 16px;
}
.history-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--color-text-tertiary, #a0aec0);
}
.history-id { font-weight: 600; color: var(--color-primary, #4299e1); }
.history-publisher { margin-left: auto; }
.btn-delete {
  background: none;
  border: 1px solid #feb2b2;
  color: #e53e3e;
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: background .15s;
}
.btn-delete:hover:not(:disabled) { background: #fff5f5; }
.btn-delete:disabled { opacity: .5; cursor: not-allowed; }
.history-body { font-size: 14px; line-height: 1.7; color: var(--color-text-primary, #1a202c); }
</style>
