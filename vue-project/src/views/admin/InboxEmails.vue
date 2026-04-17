<template>
  <div class="inbox-page">
    <div class="container">
      <header class="page-header">
        <div class="header-content">
          <div class="header-info">
            <h1 class="header-title">共用邮箱收件箱</h1>
            <p class="header-subtitle">自动同步共用邮箱收到的邮件并入库（仅系统管理员）</p>
          </div>
          <div class="header-actions">
            <button
              type="button"
              class="btn btn-secondary"
              :disabled="syncing"
              @click="manualSync"
            >
              <span v-if="syncing">同步中…</span>
              <span v-else>立即同步</span>
            </button>
          </div>
        </div>
      </header>

      <div v-if="!canAccess" class="card no-permission">
        <p>您暂无权限访问此页面，仅系统管理员（webconfig.admin1 对应用户）可操作。</p>
        <router-link to="/" class="btn btn-primary">返回首页</router-link>
      </div>

      <template v-else>
        <!-- 邮箱配置区 -->
        <div class="card config-section">
          <div class="section-header" @click="showConfig = !showConfig">
            <h3 class="section-title">共用邮箱配置</h3>
            <span class="config-status" :class="configured ? 'ok' : 'warn'">
              {{ configured ? '已配置' : '未配置' }}
            </span>
            <svg
              class="toggle-icon"
              :class="{ open: showConfig }"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>
          <div v-show="showConfig" class="config-body">
            <div class="config-hint">
              <p>IMAP 服务器：<code>{{ imapServer }}:{{ imapPort }}</code>（SSL）</p>
              <p>自动拉取间隔：约 <code>{{ pollIntervalSeconds }}</code> 秒。保存配置后后台将自动按此频率同步。</p>
            </div>
            <div class="config-form">
              <div class="form-row">
                <label>共用邮箱地址</label>
                <input
                  v-model="configForm.email_address"
                  type="text"
                  placeholder="如 shared@company.com"
                />
              </div>
              <div class="form-row">
                <label>授权码</label>
                <input
                  v-model="configForm.email_auth_code"
                  type="password"
                  placeholder="IMAP 授权码（非邮箱密码）"
                />
              </div>
              <div class="form-row">
                <button
                  class="btn btn-primary btn-sm"
                  :disabled="configSaving"
                  @click="saveConfig"
                >
                  {{ configSaving ? '保存中…' : '保存配置' }}
                </button>
                <span v-if="configMsg" class="config-msg" :class="configMsgType">{{ configMsg }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 邮件列表 -->
        <div class="card list-section">
          <div class="toolbar">
            <input
              v-model="keyword"
              class="search-input"
              type="text"
              placeholder="按主题 / 发件人 / 收件人 / 抄送 / 正文搜索"
              @keydown.enter="onSearch"
            />
            <button class="btn btn-primary btn-sm" @click="onSearch">搜索</button>
            <button class="btn btn-secondary btn-sm" @click="resetSearch">重置</button>
            <span class="list-count">共 {{ total }} 封邮件</span>
          </div>

          <div class="table-wrap">
            <table class="mail-table">
              <thead>
                <tr>
                  <th style="width: 16%">发件时间</th>
                  <th style="width: 22%">发件人</th>
                  <th>主题</th>
                  <th style="width: 20%">收件人</th>
                  <th style="width: 14%">抄送</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="loading">
                  <td colspan="5" class="empty">加载中…</td>
                </tr>
                <tr v-else-if="!items.length">
                  <td colspan="5" class="empty">暂无邮件</td>
                </tr>
                <tr
                  v-for="row in items"
                  v-else
                  :key="row.id"
                  class="mail-row"
                  @click="openDetail(row)"
                >
                  <td class="mono">{{ row.emailDate || row.receivedAt }}</td>
                  <td :title="row.from">{{ row.from || '—' }}</td>
                  <td class="subject" :title="row.subject">{{ row.subject || '（无主题）' }}</td>
                  <td :title="row.to">{{ row.to || '—' }}</td>
                  <td :title="row.cc">{{ row.cc || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="pagination" v-if="totalPages > 1">
            <button class="btn btn-sm" :disabled="page <= 1" @click="gotoPage(page - 1)">上一页</button>
            <span class="page-info">第 {{ page }} / {{ totalPages }} 页</span>
            <button class="btn btn-sm" :disabled="page >= totalPages" @click="gotoPage(page + 1)">下一页</button>
            <select v-model.number="pageSize" class="page-size-select" @change="gotoPage(1)">
              <option :value="10">10 / 页</option>
              <option :value="20">20 / 页</option>
              <option :value="50">50 / 页</option>
              <option :value="100">100 / 页</option>
            </select>
          </div>
        </div>
      </template>
    </div>

    <!-- 邮件详情弹窗 -->
    <div v-if="detailOpen" class="modal-overlay" @click.self="closeDetail">
      <div class="modal">
        <div class="modal-header">
          <h2 class="modal-title">邮件详情</h2>
          <button type="button" class="modal-close" aria-label="关闭" @click="closeDetail">×</button>
        </div>
        <div class="modal-body" v-if="detailItem">
          <div class="detail-meta">
            <div class="meta-row"><span class="meta-label">主题</span><span class="meta-value">{{ detailItem.subject || '（无主题）' }}</span></div>
            <div class="meta-row"><span class="meta-label">发件人</span><span class="meta-value">{{ detailItem.from || '—' }}</span></div>
            <div class="meta-row"><span class="meta-label">收件人</span><span class="meta-value">{{ detailItem.to || '—' }}</span></div>
            <div class="meta-row"><span class="meta-label">抄送</span><span class="meta-value">{{ detailItem.cc || '—' }}</span></div>
            <div class="meta-row"><span class="meta-label">发件时间</span><span class="meta-value mono">{{ detailItem.emailDate || '—' }}</span></div>
            <div class="meta-row"><span class="meta-label">入库时间</span><span class="meta-value mono">{{ detailItem.receivedAt || '—' }}</span></div>
          </div>
          <div class="body-toggle">
            <button
              type="button"
              class="toggle-btn"
              :class="{ active: bodyMode === 'html' }"
              :disabled="!detailItem.bodyHtml"
              @click="bodyMode = 'html'"
            >HTML</button>
            <button
              type="button"
              class="toggle-btn"
              :class="{ active: bodyMode === 'text' }"
              @click="bodyMode = 'text'"
            >纯文本</button>
          </div>
          <div class="body-box">
            <iframe
              v-if="bodyMode === 'html' && detailItem.bodyHtml"
              class="body-iframe"
              :srcdoc="safeHtml"
              sandbox=""
            ></iframe>
            <pre v-else class="body-text">{{ detailItem.bodyText || '（无正文）' }}</pre>
          </div>
        </div>
        <div class="modal-body" v-else>
          <p>加载中…</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  getInboxConfig,
  updateInboxConfig,
  listInboxEmails,
  getInboxEmailDetail,
  syncInboxEmails,
} from '@/api/inboxEmail'
import { getDbManagerPermission } from '@/api/dbManager'

const router = useRouter()

const canAccess = ref(false)
const currentUserName = ref('')

const showConfig = ref(false)
const configured = ref(false)
const imapServer = ref('')
const imapPort = ref('')
const pollIntervalSeconds = ref('')
const configForm = ref({ email_address: '', email_auth_code: '' })
const configSaving = ref(false)
const configMsg = ref('')
const configMsgType = ref('')

const keyword = ref('')
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const syncing = ref(false)

const totalPages = computed(() => {
  if (!total.value) return 1
  return Math.max(1, Math.ceil(total.value / pageSize.value))
})

const detailOpen = ref(false)
const detailItem = ref(null)
const bodyMode = ref('html')

const safeHtml = computed(() => {
  if (!detailItem.value || !detailItem.value.bodyHtml) return ''
  // iframe 的 sandbox="" 禁止脚本执行，直接塞入 srcdoc 即可
  return detailItem.value.bodyHtml
})

function resolveUserName() {
  try {
    const u = JSON.parse(localStorage.getItem('userInfo') || '{}')
    return (u.name || u.userName || '').trim()
  } catch {
    return ''
  }
}

async function loadConfig() {
  try {
    const res = await getInboxConfig(currentUserName.value)
    if (res && res.success) {
      configured.value = !!res.configured
      configForm.value.email_address = res.emailAddress || ''
      configForm.value.email_auth_code = ''
      imapServer.value = res.imapServer || 'imap.163.com'
      imapPort.value = res.imapPort || 993
      pollIntervalSeconds.value = res.pollIntervalSeconds || 120
    }
  } catch (e) {
    console.warn('加载共用邮箱配置失败', e)
  }
}

async function saveConfig() {
  const addr = (configForm.value.email_address || '').trim()
  const code = (configForm.value.email_auth_code || '').trim()
  if (!addr || !code) {
    configMsg.value = '请填写邮箱地址和授权码'
    configMsgType.value = 'error'
    return
  }
  configSaving.value = true
  configMsg.value = ''
  try {
    const res = await updateInboxConfig({
      current_user: currentUserName.value,
      email_address: addr,
      email_auth_code: code,
    })
    if (res && res.success) {
      configMsg.value = res.message || '已保存'
      configMsgType.value = 'success'
      configured.value = true
      configForm.value.email_auth_code = ''
      await loadConfig()
    } else {
      configMsg.value = (res && res.message) || '保存失败'
      configMsgType.value = 'error'
    }
  } catch (e) {
    configMsg.value = e.message || '保存失败'
    configMsgType.value = 'error'
  } finally {
    configSaving.value = false
    setTimeout(() => { configMsg.value = '' }, 4000)
  }
}

async function loadList() {
  loading.value = true
  try {
    const res = await listInboxEmails({
      current_user: currentUserName.value,
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value || undefined,
    })
    if (res && res.success) {
      items.value = res.items || []
      total.value = res.total || 0
    } else {
      items.value = []
      total.value = 0
    }
  } catch (e) {
    console.error('加载邮件列表失败', e)
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  loadList()
}

function resetSearch() {
  keyword.value = ''
  page.value = 1
  loadList()
}

function gotoPage(p) {
  if (p < 1) p = 1
  if (p > totalPages.value) p = totalPages.value
  page.value = p
  loadList()
}

async function openDetail(row) {
  detailOpen.value = true
  detailItem.value = null
  bodyMode.value = 'html'
  try {
    const res = await getInboxEmailDetail({
      current_user: currentUserName.value,
      id: row.id,
    })
    if (res && res.success) {
      detailItem.value = res.item
      bodyMode.value = res.item && res.item.bodyHtml ? 'html' : 'text'
    }
  } catch (e) {
    console.error('加载邮件详情失败', e)
    detailItem.value = { subject: '', from: '', to: '', cc: '', emailDate: '', receivedAt: '', bodyText: '加载失败', bodyHtml: '' }
  }
}

function closeDetail() {
  detailOpen.value = false
  detailItem.value = null
}

async function manualSync() {
  if (syncing.value) return
  syncing.value = true
  try {
    const res = await syncInboxEmails(currentUserName.value)
    if (res && res.success) {
      configMsg.value = res.message
      configMsgType.value = 'success'
      showConfig.value = true
      await loadList()
    } else {
      configMsg.value = (res && res.message) || '同步失败'
      configMsgType.value = 'error'
      showConfig.value = true
    }
  } catch (e) {
    configMsg.value = e.message || '同步失败'
    configMsgType.value = 'error'
    showConfig.value = true
  } finally {
    syncing.value = false
    setTimeout(() => { configMsg.value = '' }, 5000)
  }
}

onMounted(async () => {
  const name = resolveUserName()
  if (!name) {
    router.replace('/login')
    return
  }
  currentUserName.value = name
  try {
    const res = await getDbManagerPermission({ current_user: name })
    canAccess.value = !!(res && res.canAccess)
  } catch {
    canAccess.value = false
  }
  if (!canAccess.value) return
  await loadConfig()
  await loadList()
})
</script>

<style scoped>
.inbox-page {
  min-height: 100vh;
  background: var(--color-bg-layout);
}
.inbox-page .container {
  max-width: 1200px;
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

/* 配置区 */
.config-section {
  margin-bottom: var(--spacing-lg);
  padding: 0;
  overflow: hidden;
}
.section-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-lg);
  cursor: pointer;
  user-select: none;
  transition: background-color .15s;
}
.section-header:hover {
  background: rgba(0, 0, 0, 0.02);
}
.section-title {
  flex: 1;
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}
.config-status {
  font-size: 0.8rem;
  padding: 2px 10px;
  border-radius: 999px;
  font-weight: 500;
}
.config-status.ok {
  background: #dcfce7;
  color: #166534;
}
.config-status.warn {
  background: #fef3c7;
  color: #92400e;
}
.toggle-icon {
  width: 16px;
  height: 16px;
  transition: transform .2s;
  color: var(--color-text-tertiary);
}
.toggle-icon.open {
  transform: rotate(180deg);
}
.config-body {
  padding: var(--spacing-md) var(--spacing-lg) var(--spacing-lg);
  border-top: 1px solid var(--color-border);
}
.config-hint {
  background: #f8fafc;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: var(--spacing-sm) var(--spacing-md);
  margin-bottom: var(--spacing-md);
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}
.config-hint p { margin: 4px 0; }
.config-hint code {
  background: #e2e8f0;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 0.82rem;
}
.config-form .form-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}
.config-form label {
  width: 100px;
  color: var(--color-text-secondary);
  font-size: 0.88rem;
}
.config-form input[type="text"], .config-form input[type="password"] {
  flex: 1;
  max-width: 480px;
  padding: 6px 10px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 0.9rem;
}
.config-msg {
  font-size: 0.85rem;
}
.config-msg.success { color: #16a34a; }
.config-msg.error { color: #dc2626; }

/* 列表区 */
.list-section {
  padding: var(--spacing-lg);
}
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
  flex-wrap: wrap;
}
.search-input {
  flex: 1;
  min-width: 240px;
  max-width: 480px;
  padding: 6px 10px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 0.9rem;
}
.list-count {
  margin-left: auto;
  color: var(--color-text-secondary);
  font-size: 0.85rem;
}
.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--color-border);
  border-radius: 6px;
}
.mail-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}
.mail-table th, .mail-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 0;
}
.mail-table th {
  background: #f8fafc;
  font-weight: 600;
  color: var(--color-text-secondary);
  font-size: 0.82rem;
  position: sticky;
  top: 0;
}
.mail-table .subject {
  font-weight: 500;
  color: var(--color-text-primary);
}
.mail-row {
  cursor: pointer;
  transition: background-color .15s;
}
.mail-row:hover {
  background: #f1f5f9;
}
.mail-table .empty {
  text-align: center;
  color: var(--color-text-tertiary);
  padding: var(--spacing-xl);
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.82rem;
}
.pagination {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-md);
  justify-content: flex-end;
}
.page-info {
  font-size: 0.88rem;
  color: var(--color-text-secondary);
}
.page-size-select {
  margin-left: var(--spacing-md);
  padding: 4px 8px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 0.85rem;
}

/* 详情弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;
}
.modal {
  background: #fff;
  border-radius: 8px;
  width: min(920px, 100%);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.25);
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}
.modal-title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 600;
}
.modal-close {
  background: transparent;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--color-text-tertiary);
  line-height: 1;
}
.modal-body {
  overflow: auto;
  padding: var(--spacing-lg);
  flex: 1;
}
.detail-meta {
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
  background: #f8fafc;
}
.meta-row {
  display: flex;
  gap: var(--spacing-md);
  padding: 4px 0;
  font-size: 0.88rem;
}
.meta-label {
  width: 80px;
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}
.meta-value {
  flex: 1;
  word-break: break-all;
  color: var(--color-text-primary);
}
.body-toggle {
  display: flex;
  gap: 6px;
  margin-bottom: var(--spacing-sm);
}
.toggle-btn {
  padding: 4px 14px;
  font-size: 0.85rem;
  border: 1px solid var(--color-border);
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  color: var(--color-text-secondary);
}
.toggle-btn.active {
  background: var(--color-primary, #3b82f6);
  color: #fff;
  border-color: var(--color-primary, #3b82f6);
}
.toggle-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.body-box {
  border: 1px solid var(--color-border);
  border-radius: 6px;
  overflow: hidden;
  min-height: 260px;
  max-height: 60vh;
  background: #fff;
}
.body-iframe {
  width: 100%;
  height: 60vh;
  border: 0;
  background: #fff;
}
.body-text {
  margin: 0;
  padding: var(--spacing-md);
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.86rem;
  line-height: 1.55;
  color: var(--color-text-primary);
  max-height: 60vh;
  overflow: auto;
}
</style>
