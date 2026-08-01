<template>
  <div class="inbox-page">
    <div class="container" :class="{ 'tasks-mode': activeTab === 'tasks' }">

      <div v-if="!canAccess" class="card no-permission">
        <p>您暂无权限访问此页面。</p>
        <router-link to="/" class="btn btn-primary">返回首页</router-link>
      </div>

      <template v-else>
        <div class="view-tabs-wrap">
          <div class="view-tabs">
            <button
              type="button"
              class="tab-btn"
              :class="{ active: activeTab === 'tasks' }"
              @click="activeTab = 'tasks'"
            >AI 待办看板</button>
            <button
              type="button"
              class="tab-btn"
              :class="{ active: activeTab === 'emails' }"
              @click="activeTab = 'emails'"
            >邮件列表</button>
          </div>
        </div>

        <!-- AI 看板主视图 -->
        <div v-if="activeTab === 'tasks'" class="card board-section board-main">
          <div class="board-head">
            <div class="board-title-wrap">
              <span class="board-badge">AI</span>
              <h3 class="board-title">待办任务看板</h3>
              <span class="board-sub">由本地大模型从每封邮件抽取任务与截止时间</span>
            </div>
            <div class="board-stats">
              <span class="stat-item"><em>{{ taskStats.taskCount }}</em>个任务</span>
              <span class="stat-item">待分析 <em>{{ taskStats.pending }}</em></span>
              <span class="stat-item" :class="{ 'stat-warn': taskStats.failed > 0 }">失败 <em>{{ taskStats.failed }}</em></span>
              <button class="btn btn-sm btn-ghost" @click="loadTasks" :disabled="taskLoading">
                {{ taskLoading ? '刷新中…' : '刷新' }}
              </button>
            </div>
          </div>

          <div class="board-actions">
            <button
              type="button"
              class="btn btn-secondary btn-sm"
              :disabled="analyzing"
              @click="manualAnalyze"
            >
              <span v-if="analyzing">分析中…</span>
              <span v-else>立即分析</span>
            </button>
            <template v-if="selectionMode">
              <button
                type="button"
                class="btn btn-sm btn-ghost"
                :disabled="!displayTasks.length || batchCompleting"
                @click="selectAllTasks"
              >全选</button>
              <button
                type="button"
                class="btn btn-sm btn-ghost"
                :disabled="!selectedTaskIds.length || batchCompleting"
                @click="clearSelection"
              >清空</button>
              <button
                type="button"
                class="btn btn-sm batch-complete-btn"
                :disabled="!selectedTaskIds.length || batchCompleting"
                @click="batchCompleteTasks"
              >
                <span v-if="batchCompleting">处理中…</span>
                <span v-else>批量完成 ({{ selectedTaskIds.length }})</span>
              </button>
              <button
                type="button"
                class="btn btn-sm btn-ghost"
                :disabled="batchCompleting"
                @click="exitSelectionMode"
              >取消多选</button>
            </template>
            <button
              v-else
              type="button"
              class="btn btn-sm btn-ghost"
              :disabled="!displayTasks.length"
              @click="enterSelectionMode"
            >多选完成</button>
            <button
              type="button"
              class="btn btn-sm btn-ghost"
              :disabled="syncing || !configured"
              :title="configured ? '同步公用邮箱全部新邮件' : '请联系系统管理员配置邮箱'"
              @click="manualSync"
            >
              <span v-if="syncing">同步中…</span>
              <span v-else>立即同步</span>
            </button>
            <button
              v-if="isSystemAdmin"
              type="button"
              class="btn btn-sm btn-ghost board-config-toggle"
              @click="toggleBoardConfig"
            >
              {{ showBoardConfig ? '收起邮箱配置' : '邮箱配置' }}
            </button>
            <span
              v-if="!showBoardConfig"
              class="config-status config-status-inline"
              :class="configured ? 'ok' : 'warn'"
            >{{ configured ? '已配置' : '未配置' }}</span>
          </div>

          <div v-if="isSystemAdmin && showBoardConfig" class="board-config-panel">
            <InboxEmailConfigBody
              compact
              :configured="configured"
              :imap-server="imapServer"
              :imap-port="imapPort"
              :poll-interval-seconds="pollIntervalSeconds"
              v-model:email-address="configForm.email_address"
              v-model:email-auth-code="configForm.email_auth_code"
              :saving="configSaving"
              :message="configMsg"
              :message-type="configMsgType"
              @save="saveConfig"
            />
          </div>

          <div v-if="taskMsg" class="board-toast" :class="taskMsgType">{{ taskMsg }}</div>

          <div class="board-body board-body-main">
            <div v-if="!tasks.length && !taskLoading" class="board-empty">
              <p>暂无识别出的待办任务。系统会从公用邮箱的全部新邮件中智能筛选；如邮箱未配置，请联系系统管理员。</p>
            </div>

            <div
              v-else
              ref="marqueeMainRef"
              class="marquee marquee-main"
              @mouseenter="marqueePaused = true"
              @mouseleave="marqueePaused = false"
              @wheel="onBoardWheel"
            >
              <div class="marquee-track no-anim">
                <div
                  v-for="(t, idx) in displayTasks"
                  :key="`${t.id}-${idx}`"
                  class="task-card"
                  :class="{
                    'task-card-selectable': selectionMode,
                    'task-card-selected': selectionMode && isTaskSelected(t.id),
                  }"
                  @click="onTaskCardClick(t.id)"
                >
                  <label
                    v-if="selectionMode"
                    class="task-select-wrap"
                    @click.stop
                  >
                    <input
                      type="checkbox"
                      :checked="isTaskSelected(t.id)"
                      :disabled="batchCompleting"
                      @change="toggleTaskSelection(t.id)"
                    />
                  </label>
                  <div class="task-top">
                    <span
                      v-if="editingDeadlineId !== t.id"
                      class="task-deadline"
                      :class="deadlineClass(t.taskDeadline)"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="ico">
                        <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
                      </svg>
                      {{ t.taskDeadline || '未指定截止时间' }}
                      <button
                        type="button"
                        class="deadline-edit-btn"
                        title="修改截止时间"
                        @click.stop="startEditDeadline(t)"
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M12 20h9" />
                          <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z" />
                        </svg>
                      </button>
                    </span>
                    <span v-else class="deadline-editor" @click.stop>
                      <input
                        v-model="deadlineDraft"
                        type="datetime-local"
                        class="deadline-input"
                        @keydown.enter.prevent="saveDeadline(t.id)"
                        @keydown.esc.prevent="cancelEditDeadline"
                      />
                      <button type="button" class="deadline-save-btn" :disabled="deadlineSavingId === t.id" @click.stop="saveDeadline(t.id)">
                        保存
                      </button>
                      <button type="button" class="deadline-cancel-btn" @click.stop="cancelEditDeadline">
                        取消
                      </button>
                    </span>
                    <span class="task-from" :title="t.from">{{ shortFrom(t.from) }}</span>
                    <button
                      v-if="!selectionMode"
                      type="button"
                      class="task-complete-btn"
                      title="标记已完成（去除旗帜并删除记录）"
                      @click.stop="completeTask(t.id)"
                      :disabled="completingId === t.id"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10" />
                      </svg>
                      {{ completingId === t.id ? '处理中…' : '待完成' }}
                    </button>
                  </div>
                  <div class="task-summary" :title="t.taskSummary">{{ t.taskSummary }}</div>
                  <div class="task-sub">
                    <span class="task-subject" :title="t.subject">{{ t.subject || '（无主题）' }}</span>
                    <span class="task-time">{{ t.emailDate || t.receivedAt }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 邮件列表模式 -->
        <template v-else>
          <!-- 邮箱配置区 -->
          <div v-if="isSystemAdmin" class="card config-section">
            <div class="section-header" @click="showConfig = !showConfig">
              <h3 class="section-title">经理层公用邮箱配置</h3>
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
              <InboxEmailConfigBody
                :configured="configured"
                :imap-server="imapServer"
                :imap-port="imapPort"
                :poll-interval-seconds="pollIntervalSeconds"
                v-model:email-address="configForm.email_address"
                v-model:email-auth-code="configForm.email_auth_code"
                :saving="configSaving"
                :message="configMsg"
                :message-type="configMsgType"
                @save="saveConfig"
              />
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
            <button class="btn btn-secondary btn-sm" :disabled="syncing" @click="manualSync">
              <span v-if="syncing">同步中…</span>
              <span v-else>立即同步</span>
            </button>
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
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  getInboxConfig,
  updateInboxConfig,
  listInboxEmails,
  getInboxEmailDetail,
  syncInboxEmails,
  listInboxTasks,
  analyzeInboxEmails,
  updateInboxTaskDeadline,
  completeInboxTask,
} from '@/api/inboxEmail'
import { getDbManagerPermission } from '@/api/dbManager'
import { isManagerLevel } from '@/utils/roleMatch'
import InboxEmailConfigBody from '@/components/inbox/InboxEmailConfigBody.vue'

const router = useRouter()
const route = useRoute()

const canAccess = ref(false)
const isSystemAdmin = ref(false)
const currentUserName = ref('')

const showConfig = ref(false)
const showBoardConfig = ref(false)
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
const activeTab = ref('tasks')

const tasks = ref([])
const taskStats = ref({ pending: 0, failed: 0, taskCount: 0, total: 0 })
const taskLoading = ref(false)
const marqueePaused = ref(false)
const analyzing = ref(false)
const taskMsg = ref('')
const taskMsgType = ref('')
const marqueeMainRef = ref(null)
const completingId = ref(null)
const selectionMode = ref(false)
const selectedTaskIds = ref([])
const batchCompleting = ref(false)
const editingDeadlineId = ref(null)
const deadlineDraft = ref('')
const deadlineSavingId = ref(null)
let taskRefreshTimer = null

const displayTasks = computed(() => tasks.value || [])

const totalPages = computed(() => {
  if (!total.value) return 1
  return Math.max(1, Math.ceil(total.value / pageSize.value))
})

const detailOpen = ref(false)
const detailItem = ref(null)
const bodyMode = ref('html')

const safeHtml = computed(() => {
  if (!detailItem.value || !detailItem.value.bodyHtml) return ''
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
      imapServer.value = res.imapServer || 'imap.qiye.163.com'
      imapPort.value = res.imapPort || 993
      pollIntervalSeconds.value = res.pollIntervalSeconds || 120
    }
  } catch (e) {
    console.warn('加载共用邮箱配置失败', e)
  }
}

function toggleBoardConfig() {
  showBoardConfig.value = !showBoardConfig.value
  if (showBoardConfig.value) {
    loadConfig()
  }
}

async function saveConfig() {
  const addr = (configForm.value.email_address || '').trim()
  const code = (configForm.value.email_auth_code || '').trim()
  if (!addr || !code) {
    configMsg.value = configured.value
      ? '请填写企业邮箱地址和新的 IMAP 授权码'
      : '请填写邮箱地址和授权码'
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

async function loadTasks() {
  if (taskLoading.value) return
  taskLoading.value = true
  try {
    const res = await listInboxTasks({ current_user: currentUserName.value, limit: 50 })
    if (res && res.success) {
      tasks.value = res.items || []
      taskStats.value = res.stats || { pending: 0, failed: 0, taskCount: 0, total: 0 }
    }
  } catch (e) {
    console.warn('加载任务看板失败', e)
  } finally {
    taskLoading.value = false
  }
}

async function manualAnalyze() {
  if (analyzing.value) return
  analyzing.value = true
  taskMsg.value = '正在调用本地大模型抽取任务，请耐心等待…'
  taskMsgType.value = 'info'
  try {
    const res = await analyzeInboxEmails({ current_user: currentUserName.value, limit: 10 })
    if (res && res.success) {
      taskMsg.value = res.message || '分析完成'
      taskMsgType.value = 'success'
      await loadTasks()
      await loadList()
    } else {
      taskMsg.value = (res && res.message) || '分析失败'
      taskMsgType.value = 'error'
    }
  } catch (e) {
    taskMsg.value = e.message || '分析失败'
    taskMsgType.value = 'error'
  } finally {
    analyzing.value = false
    setTimeout(() => { taskMsg.value = '' }, 6000)
  }
}

function shortFrom(from) {
  if (!from) return '—'
  const m = String(from).match(/^(.*?)\s*<([^>]+)>$/)
  if (m) {
    const name = (m[1] || '').trim()
    return name || m[2]
  }
  return from.length > 20 ? from.slice(0, 20) + '…' : from
}

function deadlineClass(deadline) {
  if (!deadline) return 'none'
  const d = new Date(deadline.replace(/\//g, '-').replace(/-(\d)(?!\d)/g, '-0$1'))
  if (Number.isNaN(d.getTime())) return 'neutral'
  const now = new Date()
  const diffDays = (d.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
  if (diffDays < 0) return 'overdue'
  if (diffDays <= 2) return 'urgent'
  if (diffDays <= 7) return 'soon'
  return 'neutral'
}

function onBoardWheel(e) {
  const el = marqueeMainRef.value
  if (!el) return
  const deltaY = Number(e?.deltaY || 0)
  if (!deltaY) return
  const maxScroll = el.scrollHeight - el.clientHeight
  if (maxScroll <= 0) return
  e.preventDefault()
  el.scrollTop += deltaY
}

function deadlineToInputValue(deadline) {
  const text = String(deadline || '').trim()
  if (!text) return ''
  const normalized = text.replace(/\//g, '-').replace(/\s+/, 'T')
  if (/^\d{4}-\d{1,2}-\d{1,2}$/.test(normalized)) {
    return `${normalized}T00:00`
  }
  const match = normalized.match(/^(\d{4}-\d{1,2}-\d{1,2})T(\d{1,2}:\d{2})/)
  return match ? `${match[1]}T${match[2]}` : ''
}

function inputValueToDeadline(value) {
  return String(value || '').trim().replace('T', ' ')
}

function startEditDeadline(task) {
  editingDeadlineId.value = task.id
  deadlineDraft.value = deadlineToInputValue(task.taskDeadline)
}

function cancelEditDeadline() {
  editingDeadlineId.value = null
  deadlineDraft.value = ''
  deadlineSavingId.value = null
}

async function saveDeadline(id) {
  if (!id || deadlineSavingId.value) return
  const taskDeadline = inputValueToDeadline(deadlineDraft.value)
  deadlineSavingId.value = id
  try {
    const res = await updateInboxTaskDeadline({
      current_user: currentUserName.value,
      id,
      task_deadline: taskDeadline,
    })
    if (res && res.success) {
      tasks.value = tasks.value.map(task => (
        task.id === id ? { ...task, taskDeadline: res.taskDeadline || '' } : task
      ))
      taskMsg.value = res.message || '截止时间已更新'
      taskMsgType.value = 'success'
      cancelEditDeadline()
      await loadTasks()
      await loadList()
    } else {
      taskMsg.value = (res && res.message) || '更新截止时间失败'
      taskMsgType.value = 'error'
    }
  } catch (e) {
    taskMsg.value = e.message || '更新截止时间失败'
    taskMsgType.value = 'error'
  } finally {
    deadlineSavingId.value = null
    setTimeout(() => { taskMsg.value = '' }, 5000)
  }
}

function isTaskSelected(id) {
  return selectedTaskIds.value.includes(id)
}

function enterSelectionMode() {
  selectionMode.value = true
  selectedTaskIds.value = []
}

function exitSelectionMode() {
  selectionMode.value = false
  selectedTaskIds.value = []
}

function toggleTaskSelection(id) {
  if (!id || batchCompleting.value) return
  const ids = selectedTaskIds.value
  if (ids.includes(id)) {
    selectedTaskIds.value = ids.filter(itemId => itemId !== id)
  } else {
    selectedTaskIds.value = [...ids, id]
  }
}

function selectAllTasks() {
  selectedTaskIds.value = displayTasks.value.map(t => t.id).filter(Boolean)
}

function clearSelection() {
  selectedTaskIds.value = []
}

function onTaskCardClick(id) {
  if (selectionMode.value) {
    toggleTaskSelection(id)
    return
  }
  openDetailById(id)
}

async function completeTask(id) {
  if (!id || completingId.value || batchCompleting.value) return
  completingId.value = id
  try {
    const res = await completeInboxTask({ current_user: currentUserName.value, id })
    if (res && res.success) {
      taskMsg.value = res.message || '任务已完成'
      taskMsgType.value = 'success'
      await loadTasks()
      await loadList()
    } else {
      taskMsg.value = (res && res.message) || '操作失败'
      taskMsgType.value = 'error'
    }
  } catch (e) {
    taskMsg.value = e.message || '操作失败'
    taskMsgType.value = 'error'
  } finally {
    completingId.value = null
    setTimeout(() => { taskMsg.value = '' }, 5000)
  }
}

async function batchCompleteTasks() {
  const ids = [...selectedTaskIds.value]
  if (!ids.length || batchCompleting.value) return
  if (!window.confirm(`确认将选中的 ${ids.length} 个任务标记为已完成？将去除邮件旗帜并删除记录。`)) return
  batchCompleting.value = true
  let ok = 0
  let fail = 0
  try {
    for (const id of ids) {
      try {
        const res = await completeInboxTask({ current_user: currentUserName.value, id })
        if (res && res.success) ok += 1
        else fail += 1
      } catch {
        fail += 1
      }
    }
    if (fail === 0) {
      taskMsg.value = `已批量完成 ${ok} 个任务`
      taskMsgType.value = 'success'
    } else if (ok === 0) {
      taskMsg.value = `批量完成失败（${fail} 个）`
      taskMsgType.value = 'error'
    } else {
      taskMsg.value = `部分完成：成功 ${ok} 个，失败 ${fail} 个`
      taskMsgType.value = 'error'
    }
    exitSelectionMode()
    await loadTasks()
    await loadList()
  } finally {
    batchCompleting.value = false
    setTimeout(() => { taskMsg.value = '' }, 6000)
  }
}

async function openDetailById(id) {
  if (!id) return
  await openDetail({ id })
}

async function manualSync() {
  if (syncing.value) return
  syncing.value = true
  try {
    const res = await syncInboxEmails(currentUserName.value)
    if (res && res.success) {
      taskMsg.value = res.message
      taskMsgType.value = 'success'
      await loadList()
      await loadTasks()
    } else {
      taskMsg.value = (res && res.message) || '同步失败'
      taskMsgType.value = 'error'
    }
  } catch (e) {
    taskMsg.value = e.message || '同步失败'
    taskMsgType.value = 'error'
  } finally {
    syncing.value = false
    setTimeout(() => { taskMsg.value = '' }, 5000)
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
    let jb = ''
    try {
      const u = JSON.parse(localStorage.getItem('userInfo') || '{}')
      jb = (u.jb || '').trim()
    } catch {}
    const res = await getDbManagerPermission({ current_user: name })
    isSystemAdmin.value = !!(res && res.canAccess)
    canAccess.value = isSystemAdmin.value || isManagerLevel(jb)
  } catch {
    let jb = ''
    try {
      const u = JSON.parse(localStorage.getItem('userInfo') || '{}')
      jb = (u.jb || '').trim()
    } catch {}
    canAccess.value = isManagerLevel(jb)
  }
  if (!canAccess.value) return
  // 支持从首页跳转时自动打开邮件列表+配置区
  if (route.query.tab === 'emails') {
    activeTab.value = 'emails'
    showConfig.value = isSystemAdmin.value
  }
  await loadConfig()
  await loadList()
  await loadTasks()
  taskRefreshTimer = setInterval(() => {
    loadTasks()
  }, 60000)
})

onBeforeUnmount(() => {
  if (taskRefreshTimer) {
    clearInterval(taskRefreshTimer)
    taskRefreshTimer = null
  }
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
.inbox-page .container.tasks-mode {
  max-width: 100%;
  padding-top: var(--spacing-xl);
  min-height: calc(100dvh - 120px);
  display: flex;
  flex-direction: column;
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
.config-status-inline {
  font-size: 0.78rem;
  padding: 2px 10px;
  border-radius: 999px;
  font-weight: 500;
}
.board-config-panel {
  margin-bottom: var(--spacing-sm);
  padding: var(--spacing-md);
  background: #f8fafc;
  border: 1px solid #e0e7ff;
  border-radius: 8px;
}

.view-tabs-wrap {
  display: flex;
  justify-content: flex-start;
  margin-bottom: var(--spacing-md);
}

.view-tabs {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%);
  border: 1px solid #c7d2fe;
  padding: 6px;
  border-radius: 12px;
  box-shadow: 0 6px 16px rgba(79, 70, 229, 0.12);
}

.tab-btn {
  border: none;
  background: transparent;
  color: #4b5563;
  font-size: 0.92rem;
  font-weight: 600;
  padding: 9px 18px;
  border-radius: 10px;
  cursor: pointer;
  transition: all .2s ease;
}

.tab-btn:hover {
  background: rgba(255, 255, 255, 0.72);
  color: #4338ca;
}

.tab-btn.active {
  background: #fff;
  color: #312e81;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.2);
}

/* 任务看板 */
.board-section {
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md) var(--spacing-lg) var(--spacing-lg);
  background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%);
  border: 1px solid #e0e7ff;
}
.board-main {
  flex: 1;
  height: calc(100dvh - 180px);
  min-height: calc(100dvh - 180px);
  max-height: none;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.board-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}
.board-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.board-badge {
  background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
  color: #fff;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  letter-spacing: 0.5px;
}
.board-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #1e1b4b;
}
.board-sub {
  font-size: 0.82rem;
  color: #6b7280;
}
.board-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.82rem;
  color: var(--color-text-secondary);
}
.board-stats .stat-item em {
  color: #4338ca;
  font-weight: 700;
  font-style: normal;
  margin: 0 4px;
}
.board-stats .stat-warn em {
  color: #dc2626;
}
.board-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: var(--spacing-sm);
}
.batch-complete-btn {
  color: #fff;
  background: #16a34a;
  border: 1px solid #15803d;
}
.batch-complete-btn:hover:not(:disabled) {
  background: #15803d;
}
.batch-complete-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.btn-ghost {
  background: #fff;
  border: 1px solid #c7d2fe;
  color: #4338ca;
}
.btn-ghost:hover {
  background: #eef2ff;
}
.board-toast {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.85rem;
  margin-bottom: var(--spacing-sm);
}
.board-toast.info { background: #e0e7ff; color: #3730a3; }
.board-toast.success { background: #dcfce7; color: #166534; }
.board-toast.error { background: #fee2e2; color: #991b1b; }

.board-empty {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-tertiary);
  font-size: 0.88rem;
  background: rgba(255,255,255,0.65);
  border-radius: 8px;
}

.board-body {
  position: relative;
}
.board-body-main {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.marquee {
  position: relative;
  overflow: hidden;
  max-height: 240px;
  mask-image: linear-gradient(to bottom, transparent 0, #000 24px, #000 calc(100% - 24px), transparent 100%);
  -webkit-mask-image: linear-gradient(to bottom, transparent 0, #000 24px, #000 calc(100% - 24px), transparent 100%);
}
.marquee-main {
  flex: 1;
  height: 100%;
  max-height: 100%;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
  scroll-behavior: smooth;
  mask-image: none;
  -webkit-mask-image: none;
}
.marquee-track {
  display: flex;
  flex-direction: column;
  gap: 10px;
  animation: marquee-scroll 40s linear infinite;
  will-change: transform;
}
.marquee-track.paused { animation-play-state: paused; }
.marquee-track.no-anim { animation: none; }

@keyframes marquee-scroll {
  0% { transform: translateY(0); }
  100% { transform: translateY(-50%); }
}

.task-card {
  position: relative;
  background: #fff;
  border: 1px solid #e0e7ff;
  border-left: 4px solid #6366f1;
  border-radius: 8px;
  padding: 10px 14px;
  box-shadow: 0 2px 6px rgba(99, 102, 241, 0.08);
  cursor: pointer;
  transition: transform .15s, box-shadow .15s;
}
.task-card-selected {
  background: #f5f3ff;
  border-color: #a5b4fc;
  box-shadow: 0 2px 10px rgba(99, 102, 241, 0.2);
}
.task-select-wrap {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}
.task-select-wrap input {
  width: 16px;
  height: 16px;
  accent-color: #4f46e5;
  cursor: pointer;
}
.task-card-selectable {
  padding-left: 34px;
}
.task-card:hover {
  transform: translateX(2px);
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.18);
}
.task-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 4px;
}
.task-deadline {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.82rem;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4338ca;
}
.task-deadline .ico {
  width: 12px;
  height: 12px;
}
.deadline-edit-btn {
  width: 18px;
  height: 18px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 50%;
  color: currentColor;
  background: rgba(255, 255, 255, 0.65);
  cursor: pointer;
}
.deadline-edit-btn svg {
  width: 11px;
  height: 11px;
}
.deadline-editor {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  max-width: 60%;
}
.deadline-input {
  width: 170px;
  height: 26px;
  padding: 0 8px;
  border: 1px solid #c7d2fe;
  border-radius: 6px;
  font-size: 12px;
  color: #1f2937;
  background: #fff;
}
.deadline-save-btn,
.deadline-cancel-btn {
  height: 26px;
  padding: 0 8px;
  border-radius: 6px;
  border: 1px solid #c7d2fe;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.deadline-save-btn {
  color: #fff;
  background: #4f46e5;
  border-color: #4f46e5;
}
.deadline-cancel-btn {
  color: #4b5563;
  background: #fff;
}
.task-deadline.none {
  background: #f3f4f6;
  color: #6b7280;
}
.task-deadline.overdue {
  background: #fee2e2;
  color: #b91c1c;
}
.task-deadline.urgent {
  background: #ffedd5;
  color: #c2410c;
}
.task-deadline.soon {
  background: #fef9c3;
  color: #854d0e;
}
.task-from {
  font-size: 0.8rem;
  color: #6b7280;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.task-complete-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 3px 10px;
  font-size: 0.76rem;
  font-weight: 600;
  color: #16a34a;
  background: #dcfce7;
  border: 1px solid #bbf7d0;
  border-radius: 999px;
  cursor: pointer;
  transition: all .15s;
  white-space: nowrap;
  flex-shrink: 0;
}
.task-complete-btn svg {
  width: 12px;
  height: 12px;
}
.task-complete-btn:hover {
  background: #16a34a;
  color: #fff;
  border-color: #16a34a;
}
.task-complete-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.task-summary {
  font-size: 0.95rem;
  color: #1f2937;
  line-height: 1.5;
  margin: 4px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.task-sub {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 0.78rem;
  color: #9ca3af;
}
.task-subject {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.task-time {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

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
