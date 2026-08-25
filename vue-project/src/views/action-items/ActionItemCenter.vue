<template>
  <div class="action-page">
    <header class="page-head">
      <div>
        <h1>行动项督办</h1>
        <p>会议部署事项全过程跟踪、督办与闭环管理</p>
      </div>
      <div v-if="mode === 'minutes' && permissions.minutesUpload">
        <button class="btn primary" :disabled="savingMinute" @click="selectMinuteFile">
          {{ savingMinute ? '解析与AI识别中…' : '上传会议纪要' }}
        </button>
        <input
          ref="minuteFile"
          hidden
          type="file"
          accept=".doc,.docx,.pdf,.txt"
          @change="submitMinute"
        >
      </div>
    </header>

    <nav class="action-tabs">
      <router-link to="/action-items/dashboard">驾驶舱</router-link>
      <router-link to="/action-items/minutes">会议纪要AI提取</router-link>
      <router-link to="/action-items/ledger">行动项台账</router-link>
      <router-link to="/action-items/my">我的行动项（接收/办理）</router-link>
      <router-link class="tab-with-badge" to="/action-items/messages">
        我的消息
        <span v-if="unreadMessageCount" class="tab-badge">
          {{ unreadMessageCount > 99 ? '99+' : unreadMessageCount }}
        </span>
      </router-link>
      <router-link to="/action-items/approvals">待我审批</router-link>
    </nav>

    <template v-if="mode === 'dashboard'">
      <section class="dashboard-banner">
        <div>
          <span class="dashboard-kicker">ACTION CONTROL CENTER</span>
          <h2>行动项全景驾驶舱</h2>
          <p>实时洞察任务进度与风险，点击任一指标即可下钻查看明细</p>
        </div>
        <div class="dashboard-live"><i></i> 数据实时更新</div>
      </section>
      <section class="metric-grid dashboard-metrics">
        <button
          v-for="card in metricCards"
          :key="card.key"
          class="metric-card"
          :data-metric="card.key"
          @click="drill(card)"
        >
          <i class="metric-icon">{{ card.icon }}</i>
          <span>{{ card.label }}</span>
          <div><strong>{{ card.value }}</strong><small v-if="card.suffix">{{ card.suffix }}</small></div>
          <em>查看明细 →</em>
        </button>
      </section>
      <section class="panel dashboard-panel">
        <div class="panel-title"><div><small>DEPARTMENT OVERVIEW</small><h2>各科室行动项完成情况</h2></div><span>点击科室可下钻台账</span></div>
        <div class="dept-stat-list">
          <button v-for="dept in dashboard.departments" :key="dept.department" class="dept-stat" @click="openDept(dept.department)">
            <div class="dept-stat-head"><strong>{{ dept.department }}</strong><span>{{ dept.total }} 项</span></div>
            <div class="bar"><i :style="{ width: dept.completionRate + '%' }"></i></div>
            <div class="dept-stat-meta"><span>完成率 {{ dept.completionRate }}%</span><span :class="{ danger: dept.overdue }">逾期率 {{ dept.overdueRate }}%</span></div>
          </button>
          <div v-if="!dashboard.departments.length" class="empty">暂无行动项数据</div>
        </div>
      </section>
    </template>

    <template v-else-if="mode === 'minutes'">
      <section class="panel filters">
        <input v-model.trim="minuteFilters.keyword" placeholder="会议名称、纪要编号、主题" @keyup.enter="loadMinutes(1)">
        <select v-model="minuteFilters.meeting_type" @change="loadMinutes(1)">
          <option value="">全部会议</option>
          <option>综合管理例会</option><option>质量例会</option><option>产品提升专题会</option><option>其他</option>
        </select>
        <button class="btn" @click="loadMinutes(1)">查询</button>
      </section>
      <section class="panel list-panel">
        <div v-if="loading" class="empty">正在加载会议纪要…</div>
        <article v-for="item in minutes" :key="item.id" class="minute-row">
          <div class="minute-main">
            <div class="row-title">
              <strong>{{ item.meeting_name }}</strong>
              <span class="status" :data-status="item.status">{{ item.status }}</span>
              <span v-if="item.meeting_type" class="tag">{{ item.meeting_type }}</span>
            </div>
            <p>{{ item.minutes_number || '无纪要编号' }} · {{ item.meeting_date || item.created_at }}</p>
            <small>{{ item.minutes_text_preview || '暂无正文预览' }}</small>
          </div>
          <div class="row-actions">
            <span>{{ item.action_count }} 条行动项</span>
            <button v-if="permissions.extract" class="link" :disabled="!!extractingId" @click="extract(item)">
              {{ extractingId === item.id ? '提取中…' : 'AI提取' }}
            </button>
            <router-link class="link" :to="`/action-items/review/${item.id}`">核对/查看</router-link>
            <button
              v-if="permissions.minutesManage && item.status !== '已发布'"
              class="link danger-link"
              @click="deleteMinute(item)"
            >删除</button>
          </div>
        </article>
        <div v-if="!loading && minuteLoadError" class="empty load-error">
          <p>{{ minuteLoadError }}</p>
          <button class="btn" @click="loadMinutes(1)">重新加载</button>
        </div>
        <div v-else-if="!loading && !minutes.length" class="empty">暂无会议纪要</div>
      </section>
    </template>

    <template v-else-if="mode === 'messages'">
      <section class="panel list-panel">
        <div class="panel-title message-title">
          <div>
            <h2>我的行动项消息</h2>
            <span>发布、催办、退回和审批结果等站内通知均在这里接收</span>
          </div>
          <label class="message-filter">
            <input v-model="unreadOnly" type="checkbox" @change="loadActionReminders">
            仅看未读
          </label>
        </div>
        <div v-if="loading" class="empty">加载中…</div>
        <article
          v-for="item in actionReminders"
          :key="item.id"
          class="message-row"
          :class="{ unread: !item.read_at }"
        >
          <div class="message-state">
            <i></i>
            <span>{{ item.read_at ? '已读' : '未读' }}</span>
          </div>
          <div class="message-main">
            <div class="row-title">
              <strong>{{ item.title || '行动项提醒' }}</strong>
              <span class="status">{{ item.reminder_type || '提醒' }}</span>
              <span v-if="item.current_status" class="tag">{{ item.current_status }}</span>
            </div>
            <p>{{ item.reminder_note || '您有一条行动项待处理' }}</p>
            <small>{{ item.action_number || '未编号' }} · {{ item.reminder_time }}</small>
          </div>
          <button class="btn primary" @click="openActionReminder(item)">
            {{ item.current_status === '待接收' ? '查看并接收' : '查看处理' }}
          </button>
        </article>
        <div v-if="!loading && !actionReminders.length" class="empty">
          {{ unreadOnly ? '暂无未读行动项消息' : '暂无行动项消息' }}
        </div>
      </section>
    </template>

    <template v-else-if="mode === 'approvals'">
      <section class="panel list-panel">
        <div class="panel-title"><h2>待我审批</h2><span>完工申请与延期、负责人、科室、内容和取消变更</span></div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>审批类型</th><th>行动项</th><th>责任科室/责任人</th><th>申请人</th><th>申请时间</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="item in pendingApprovals" :key="`${item.business_type}-${item.business_id}`">
                <td><span class="status">{{ item.business_type }}</span></td>
                <td class="action-title"><router-link :to="`/action-items/${item.action_item_id}`">{{ item.title }}</router-link><small>{{ item.action_number || '—' }} · {{ item.summary }}</small></td>
                <td>{{ item.responsible_department || item.responsible_department_ids?.join('、') || item.responsible_department_id || '—' }}<small>{{ item.responsible_person_ids?.join('、') || item.responsible_person_id || '—' }}</small></td>
                <td>{{ item.applicant }}</td>
                <td>{{ item.applied_at }}</td>
                <td><router-link class="link" :to="`/action-items/${item.action_item_id}`">去审批</router-link></td>
              </tr>
            </tbody>
          </table>
          <div v-if="!loading && !pendingApprovals.length" class="empty">暂无待审批事项</div>
        </div>
      </section>
    </template>

    <template v-else>
      <section class="panel filters">
        <input v-model.trim="filters.keyword" placeholder="编号、标题、内容关键字" @keyup.enter="loadActions(1)">
        <select v-model="filters.meeting_id" @change="loadActions(1)">
          <option value="">全部会议</option><option v-for="m in minuteOptions" :key="m.id" :value="m.id">{{ m.meeting_name }}</option>
        </select>
        <input v-model.trim="filters.minutes_number" placeholder="纪要编号" @keyup.enter="loadActions(1)">
        <select v-model="filters.department" @change="loadActions(1)">
          <option value="">全部责任科室</option><option v-for="dept in directory.departments" :key="dept">{{ dept }}</option>
        </select>
        <select v-model="filters.responsible_person" @change="loadActions(1)">
          <option value="">全部责任人</option><option v-for="p in directory.people" :key="p.name">{{ p.name }}</option>
        </select>
        <select v-model="filters.supervisor" @change="loadActions(1)">
          <option value="">全部主管领导</option><option v-for="p in directory.supervisors" :key="p.name">{{ p.name }}</option>
        </select>
        <select v-model="filters.status" @change="loadActions(1)">
          <option value="">全部状态</option>
          <option v-for="status in statuses" :key="status">{{ status }}</option>
        </select>
        <input v-model="filters.deadline_from" type="date" title="截止日期起">
        <input v-model="filters.deadline_to" type="date" title="截止日期止">
        <label><input v-model="filters.overdue" type="checkbox"> 仅逾期</label>
        <select v-model="filters.sort_by" title="排序字段" @change="loadActions(1)">
          <option value="updated_at">按更新时间</option><option value="deadline">按截止日期</option><option value="progress">按进度</option><option value="created_at">按创建时间</option><option value="priority">按优先级</option>
        </select>
        <select v-model="filters.sort_order" title="排序方向" @change="loadActions(1)"><option value="desc">降序</option><option value="asc">升序</option></select>
        <button class="btn" @click="loadActions(1)">查询</button>
        <button
          v-if="permissions.actionCreate && mode === 'ledger'"
          class="btn primary"
          @click="openCreateAction"
        >新建行动项</button>
        <button v-if="permissions.export && mode === 'ledger'" class="btn" @click="exportLedger">导出</button>
      </section>
      <section class="panel list-panel">
        <div class="table-wrap">
          <div v-if="loading" class="empty">正在加载行动项…</div>
          <table>
            <thead><tr><th>行动项</th><th>责任科室/责任人</th><th>主管领导</th><th>截止日期</th><th>进度</th><th>状态</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="item in actions" :key="item.id" :data-status="item.current_status" :data-priority="item.priority || '中'">
                <td class="action-title">
                  <router-link :to="`/action-items/${item.id}`">{{ item.title }}</router-link>
                  <small>
                    {{ item.action_number || '草稿' }} · {{ item.minutes_number || '人工新增' }}
                    <span class="priority-tag" :data-priority="item.priority || '中'">{{ item.priority || '中' }}优先级</span>
                  </small>
                  <div><span v-for="tag in item.risk_tags" :key="tag" class="risk" :class="{ overdue: tag === '已逾期' }">{{ tag }}</span></div>
                </td>
                <td>{{ item.responsible_department_ids?.join('、') || '待确认' }}<small>{{ item.responsible_person_ids?.join('、') || '待确认' }}</small></td>
                <td>{{ item.supervisor_id || '待确认' }}</td>
                <td>{{ item.required_completion_date || '待确认' }}</td>
                <td><div class="mini-progress"><i :style="{ width: item.current_progress + '%' }"></i></div>{{ item.current_progress }}%</td>
                <td><span class="status" :data-status="item.current_status">{{ item.current_status }}</span></td>
                <td>
                  <router-link class="link" :to="`/action-items/${item.id}`">详情</router-link>
                  <button
                    v-if="permissions.actionCreate && ['草稿', '待发布'].includes(item.current_status)"
                    type="button"
                    class="link"
                    @click="openEditDraft(item)"
                  >{{ permissions.publish ? '编辑/发布' : '编辑' }}</button>
                  <router-link
                    v-if="mode === 'my' && item.my_execution_status === '待接收'"
                    class="link receive-link"
                    :to="`/action-items/${item.id}`"
                  >去接收</router-link>
                  <template v-if="canManagePublished(item)">
                    <router-link class="link" :to="`/action-items/${item.id}?edit=1`">调整</router-link>
                    <button type="button" class="link success-link" @click="completePublished(item)">设为已完成</button>
                    <button type="button" class="link danger-link" @click="cancelPublished(item)">删除</button>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="!loading && actionLoadError" class="empty load-error">
            <p>{{ actionLoadError }}</p>
            <button class="btn" @click="loadActions(1)">重新加载</button>
          </div>
          <div v-else-if="!loading && !actions.length" class="empty">暂无符合条件的行动项</div>
        </div>
        <div class="pagination">
          <button class="btn" :disabled="page <= 1" @click="loadActions(page - 1)">上一页</button>
          <span>{{ page }} / {{ totalPages }}，共 {{ total }} 条</span>
          <button class="btn" :disabled="page >= totalPages" @click="loadActions(page + 1)">下一页</button>
        </div>
      </section>
    </template>

    <div v-if="showCreateAction" class="modal-mask" @click.self="showCreateAction = false">
      <form class="modal" @submit.prevent="saveCreatedAction(false)">
        <div class="modal-head">
          <h2>{{ createActionForm.id ? '编辑单条行动项' : '新建单条行动项' }}</h2>
          <button type="button" @click="showCreateAction = false">×</button>
        </div>
        <div class="form-grid">
          <label class="wide">行动项标题<input v-model.trim="createActionForm.title" required></label>
          <label class="wide">行动项内容<textarea v-model.trim="createActionForm.content" rows="4" required></textarea></label>
          <label>来源会议
            <select v-model="createActionForm.source_meeting_id" :disabled="!!createActionForm.id">
              <option value="">人工新增（无来源会议）</option>
              <option v-for="m in minuteOptions" :key="m.id" :value="m.id">{{ m.meeting_name }}</option>
            </select>
          </label>
          <label>优先级
            <select v-model="createActionForm.priority"><option>高</option><option>中</option><option>低</option></select>
          </label>
          <label>责任科室
            <select v-model="createActionForm.responsible_department_id" required>
              <option value="">请选择</option>
              <option v-for="dept in directory.departments" :key="dept">{{ dept }}</option>
            </select>
          </label>
          <label>责任人
            <select v-model="createActionForm.responsible_person_id" required>
              <option value="">请选择</option>
              <option v-for="person in createActionPeople" :key="person.name" :value="person.name">
                {{ person.name }}（{{ person.job || '员工' }}）
              </option>
            </select>
          </label>
          <label>主管领导
            <select v-model="createActionForm.supervisor_id" required>
              <option value="">请选择</option>
              <option v-for="person in directory.supervisors" :key="person.name" :value="person.name">{{ person.name }}</option>
            </select>
          </label>
          <label>要求完成时间<input v-model="createActionForm.required_completion_date" type="date" required></label>
          <label class="wide">任务依据/补充说明<textarea v-model.trim="createActionForm.source_quote" rows="2"></textarea></label>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn" @click="showCreateAction = false">取消</button>
          <button class="btn" :disabled="savingAction">{{ savingAction ? '保存中…' : '保存草稿' }}</button>
          <button
            v-if="permissions.publish"
            type="button"
            class="btn primary"
            :disabled="savingAction"
            @click="saveCreatedAction(true)"
          >保存并发布</button>
        </div>
      </form>
    </div>

    <div v-if="showAiLog" class="modal-mask ai-log-mask">
      <section class="modal ai-log-modal">
        <div class="modal-head ai-log-head">
          <div>
            <h2>AI 行动项提取日志</h2>
            <p>{{ aiLogMeeting?.meeting_name }} · {{ aiLogMeeting?.minutes_number || '无纪要编号' }}</p>
          </div>
          <div class="ai-log-head-actions">
            <span class="ai-run-status" :class="`is-${aiLogStatus}`">{{ aiStatusText }}</span>
            <button type="button" :disabled="aiLogStatus === 'running'" @click="closeAiLog">×</button>
          </div>
        </div>

        <div class="ai-log-grid">
          <section ref="aiWorkflowPanel" class="ai-log-pane workflow-pane">
            <div class="ai-pane-title"><strong>工作流</strong><span>{{ aiWorkflow.length }} 条日志</span></div>
            <ol class="workflow-list">
              <li v-for="(log, index) in aiWorkflow" :key="`${log.time}-${index}`" :class="`is-${log.status || 'info'}`">
                <i></i>
                <div><strong>{{ log.step }}</strong><p>{{ log.message }}</p><time>{{ log.time }}</time></div>
              </li>
            </ol>
            <div v-if="!aiWorkflow.length" class="ai-log-placeholder">正在建立提取任务…</div>
          </section>

          <section ref="aiOutputPanel" class="ai-log-pane output-pane">
            <div class="ai-pane-title"><strong>大模型流式输出</strong><span>实时展示</span></div>
            <section class="ai-stream-section ai-reasoning-section">
              <div class="ai-stream-section-title">
                <strong>模型思考过程</strong>
                <span>{{ aiReasoningOutput.length }} 字符 · 默认展示</span>
              </div>
              <pre>{{ aiReasoningOutput || (aiLogStatus === 'running' ? '等待模型返回思考流…' : '当前模型未返回独立思考内容') }}</pre>
            </section>
            <section class="ai-stream-section ai-result-section">
              <div class="ai-stream-section-title">
                <strong>结构化 JSON 输出</strong>
                <span>{{ aiRawOutput.length }} 字符</span>
              </div>
              <pre>{{ aiRawOutput || '等待模型输出 JSON…' }}</pre>
            </section>
          </section>
        </div>

        <p v-if="aiLogError" class="ai-log-error">{{ aiLogError }}</p>
        <div class="modal-actions">
          <button v-if="aiLogStatus === 'running'" type="button" class="btn warning" @click="stopAiExtraction">停止提取</button>
          <button v-if="['error', 'cancelled'].includes(aiLogStatus)" type="button" class="btn" @click="retryAiExtraction">重新提取</button>
          <button v-if="aiLogStatus === 'success'" type="button" class="btn primary" @click="openAiReview">进入人工核对</button>
          <button v-if="aiLogStatus !== 'running'" type="button" class="btn" @click="closeAiLog">关闭</button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  cancelPublishedAction, createActionDraft, createMeetingMinute, deleteMeetingMinute,
  exportActionItems, forceCompleteAction, getActionDashboard,
  getActionDirectory, getActionPermissions, getActions, getMeetingMinutes,
  getMyActionReminders, getPendingActionApprovals, publishActions, readActionReminder,
  updateAction,
} from '@/api/actionItems'

const props = defineProps({ mode: { type: String, default: 'dashboard' } })
const router = useRouter()
const route = useRoute()
const mode = computed(() => props.mode)
const currentUser = (() => {
  try { const u = JSON.parse(localStorage.getItem('userInfo') || '{}'); return (u.name || u.userName || '').trim() } catch { return '' }
})()
const permissions = reactive({})
const directory = reactive({ departments: [], people: [], supervisors: [] })
const dashboard = reactive({ summary: {}, departments: [] })
const minutes = ref([])
const minuteOptions = ref([])
const actions = ref([])
const actionReminders = ref([])
const unreadMessageCount = ref(0)
const pendingApprovals = ref([])
const unreadOnly = ref(true)
const loading = ref(false)
const minuteLoadError = ref('')
const actionLoadError = ref('')
const total = ref(0)
const page = ref(1)
const pageSize = 20
const extractingId = ref(0)
const showAiLog = ref(false)
const aiLogMeeting = ref(null)
const aiLogStatus = ref('idle')
const aiLogError = ref('')
const aiWorkflow = ref([])
const aiRawOutput = ref('')
const aiReasoningOutput = ref('')
const aiWorkflowPanel = ref(null)
const aiOutputPanel = ref(null)
let aiAbortController = null
let unreadMessageTimer = null
const savingMinute = ref(false)
const savingAction = ref(false)
const showCreateAction = ref(false)
const minuteFile = ref(null)
const statuses = ['草稿', '待发布', '待接收', '进行中', '待完工审批', '退回整改', '已完成', '已取消']
const minuteFilters = reactive({ keyword: '', meeting_type: '' })
const createActionForm = reactive({
  id: 0, title: '', content: '', source_meeting_id: '', source_quote: '',
  responsible_department_id: '', responsible_person_id: '',
  supervisor_id: '', required_completion_date: '', priority: '中',
})
const filters = reactive({
  keyword: '', meeting_id: '', minutes_number: '', department: '', responsible_person: '',
  supervisor: '', status: '', deadline_from: '', deadline_to: '', overdue: false,
  sort_by: 'updated_at', sort_order: 'desc', metric: '',
})
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const createActionPeople = computed(() => directory.people.filter(
  person => !createActionForm.responsible_department_id
    || person.department === createActionForm.responsible_department_id,
))
const aiStatusText = computed(() => ({
  idle: '等待开始', running: '提取中', success: '已完成',
  error: '执行失败', cancelled: '已停止',
}[aiLogStatus.value] || aiLogStatus.value))
const metricCards = computed(() => {
  const s = dashboard.summary || {}
  return [
    { key: 'total', label: '行动项总数', value: s.total || 0, icon: '⌁' },
    { key: 'completed', label: '完成率', value: s.completionRate || 0, suffix: '%', icon: '✓' },
    { key: 'inProgress', label: '进行中', value: s.inProgress || 0, icon: '↻' },
    { key: 'overdue', label: '已逾期', value: s.overdue || 0, icon: '!' },
    { key: 'dueSoon', label: '临期', value: s.dueSoon || 0, icon: '◷' },
    { key: 'pendingApproval', label: '待审批', value: s.pendingApproval || 0, icon: '⌘' },
    { key: 'stale', label: '长期未更新', value: s.stale || 0, icon: '…' },
    { key: 'newThisWeek', label: '本周新增', value: s.newThisWeek || 0, icon: '+' },
    { key: 'completedThisWeek', label: '本周完成', value: s.completedThisWeek || 0, icon: '↑' },
  ]
})

async function bootstrap() {
  if (!currentUser) return
  loading.value = true
  const [p, d, m, unread] = await Promise.allSettled([
    getActionPermissions(currentUser), getActionDirectory(currentUser),
    getMeetingMinutes({ current_user: currentUser, page: 1, page_size: 100 }),
    getMyActionReminders({ current_user: currentUser, unread_only: true, limit: 200 }),
  ])
  if (p.status === 'fulfilled') Object.assign(permissions, p.value?.permissions || {})
  if (d.status === 'fulfilled') Object.assign(directory, d.value || {})
  if (unread.status === 'fulfilled') unreadMessageCount.value = unread.value?.items?.length || 0
  if (m.status === 'fulfilled') {
    minuteOptions.value = m.value?.items || []
    if (mode.value === 'minutes') {
      minutes.value = m.value?.items || []
      minuteLoadError.value = ''
      loading.value = false
      return
    }
  }
  try {
    await loadCurrent()
  } finally {
    loading.value = false
  }
}
async function loadCurrent() {
  if (mode.value === 'dashboard') return loadDashboard()
  if (mode.value === 'minutes') return loadMinutes(1)
  if (mode.value === 'messages') return loadActionReminders()
  if (mode.value === 'approvals') return loadPendingApprovals()
  return loadActions(1)
}
async function loadDashboard() {
  loading.value = true
  try { const res = await getActionDashboard(currentUser); Object.assign(dashboard, res || {}) } finally { loading.value = false }
}
async function loadMinutes(nextPage = 1) {
  loading.value = true
  minuteLoadError.value = ''
  try {
    const params = { current_user: currentUser, page: nextPage, page_size: 100 }
    if (minuteFilters.keyword) params.keyword = minuteFilters.keyword
    if (minuteFilters.meeting_type) params.meeting_type = minuteFilters.meeting_type
    const res = await getMeetingMinutes(params)
    minutes.value = res?.items || []
    if (!minuteFilters.keyword && !minuteFilters.meeting_type) {
      minuteOptions.value = res?.items || []
    }
  } catch (e) {
    minuteLoadError.value = e?.response?.data?.detail || e?.message || '会议纪要加载失败'
  } finally { loading.value = false }
}
async function loadActions(nextPage = 1) {
  loading.value = true
  actionLoadError.value = ''
  page.value = nextPage
  try {
    const params = {
      current_user: currentUser,
      mine: mode.value === 'my',
      page: nextPage,
      page_size: pageSize,
      sort_by: filters.sort_by,
      sort_order: filters.sort_order,
    }
    for (const key of [
      'keyword', 'meeting_id', 'minutes_number', 'department',
      'responsible_person', 'supervisor', 'status',
      'deadline_from', 'deadline_to', 'metric',
    ]) {
      if (filters[key] !== '' && filters[key] != null) params[key] = filters[key]
    }
    if (filters.overdue) params.overdue = true
    const res = await getActions(params)
    actions.value = res?.items || []; total.value = res?.total || 0
  } catch (e) {
    actionLoadError.value = e?.response?.data?.detail || e?.message || '行动项加载失败'
  } finally { loading.value = false }
}
async function loadPendingApprovals() {
  loading.value = true
  try {
    const res = await getPendingActionApprovals(currentUser)
    pendingApprovals.value = res?.items || []
  } finally { loading.value = false }
}
async function loadActionReminders() {
  loading.value = true
  try {
    const res = await getMyActionReminders({
      current_user: currentUser,
      unread_only: unreadOnly.value,
      limit: 200,
    })
    actionReminders.value = res?.items || []
    unreadMessageCount.value = unreadOnly.value
      ? actionReminders.value.length
      : actionReminders.value.filter(item => !item.read_at).length
  } finally { loading.value = false }
}
async function refreshUnreadMessageCount() {
  if (!currentUser) return
  try {
    const res = await getMyActionReminders({
      current_user: currentUser,
      unread_only: true,
      limit: 200,
    })
    unreadMessageCount.value = res?.items?.length || 0
  } catch {
    // 顶部气泡刷新失败不影响当前页面的其他功能。
  }
}
async function openActionReminder(item) {
  try {
    if (!item.read_at) {
      await readActionReminder(item.id, { current_user: currentUser })
      item.read_at = new Date().toISOString()
      unreadMessageCount.value = Math.max(0, unreadMessageCount.value - 1)
    }
    router.push(`/action-items/${item.action_item_id}`)
  } catch (e) {
    alert(e?.response?.data?.detail || e?.message || '打开行动项消息失败')
  }
}
function scrollAiLogs() {
  nextTick(() => {
    if (aiWorkflowPanel.value) aiWorkflowPanel.value.scrollTop = aiWorkflowPanel.value.scrollHeight
    if (aiOutputPanel.value) aiOutputPanel.value.scrollTop = aiOutputPanel.value.scrollHeight
  })
}
function processAiStreamEvent(event) {
  if (event.type === 'workflow') {
    aiWorkflow.value.push(event)
  } else if (event.type === 'token') {
    aiRawOutput.value += event.content || ''
  } else if (event.type === 'reasoning') {
    aiReasoningOutput.value += event.content || ''
  } else if (event.type === 'complete') {
    aiLogStatus.value = 'success'
    aiWorkflow.value.push({
      time: event.time, step: '提取完成', status: 'done',
      message: event.result?.message || '行动项草稿已生成',
    })
  } else if (event.type === 'error') {
    aiLogStatus.value = 'error'
    aiLogError.value = event.message || 'AI 提取失败'
    aiWorkflow.value.push({
      time: event.time, step: '流程终止', status: 'error',
      message: aiLogError.value,
    })
  }
  scrollAiLogs()
}
async function extract(item) {
  if (extractingId.value) return
  extractingId.value = item.id
  aiLogMeeting.value = item
  aiLogStatus.value = 'running'
  aiLogError.value = ''
  aiWorkflow.value = []
  aiRawOutput.value = ''
  aiReasoningOutput.value = ''
  showAiLog.value = true
  aiAbortController = new AbortController()
  try {
    const url = `/api/action-items/minutes/${item.id}/extract/stream?current_user=${encodeURIComponent(currentUser)}`
    const response = await fetch(url, {
      method: 'POST',
      headers: { Accept: 'application/x-ndjson' },
      signal: aiAbortController.signal,
    })
    if (!response.ok) {
      let message = `请求失败（${response.status}）`
      try {
        const body = await response.json()
        message = body?.detail || body?.message || message
      } catch { /* 使用状态码提示 */ }
      throw new Error(message)
    }
    if (!response.body) throw new Error('浏览器未收到流式响应')
    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (!line.trim()) continue
        try { processAiStreamEvent(JSON.parse(line)) }
        catch { /* 等待后续完整 NDJSON 行 */ }
      }
    }
    buffer += decoder.decode()
    if (buffer.trim()) processAiStreamEvent(JSON.parse(buffer))
    if (aiLogStatus.value === 'running') {
      throw new Error('流式连接已结束，但未收到完成状态')
    }
  } catch (e) {
    if (e?.name === 'AbortError') {
      aiLogStatus.value = 'cancelled'
      aiWorkflow.value.push({
        time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
        step: '用户停止', status: 'info', message: '已停止接收本次提取流',
      })
    } else {
      aiLogStatus.value = 'error'
      aiLogError.value = e?.message || 'AI 提取失败'
      aiWorkflow.value.push({
        time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
        step: '连接异常', status: 'error', message: aiLogError.value,
      })
    }
    scrollAiLogs()
  } finally {
    aiAbortController = null
    extractingId.value = 0
    if (aiLogStatus.value === 'success') await loadMinutes(1)
  }
}
function stopAiExtraction() {
  aiAbortController?.abort()
}
function retryAiExtraction() {
  if (aiLogMeeting.value) extract(aiLogMeeting.value)
}
function openAiReview() {
  const id = aiLogMeeting.value?.id
  showAiLog.value = false
  if (id) router.push(`/action-items/review/${id}`)
}
function closeAiLog() {
  if (aiLogStatus.value === 'running') return
  showAiLog.value = false
}
function selectMinuteFile() {
  if (!savingMinute.value) minuteFile.value?.click()
}
async function submitMinute(event) {
  const file = event?.target?.files?.[0]
  if (!file) return
  savingMinute.value = true
  try {
    const data = new FormData()
    data.append('current_user', currentUser)
    data.append('file', file)
    const result = await createMeetingMinute(data)
    alert(result?.message || '会议纪要已上传并完成AI识别')
    await loadMinutes(1)
  } catch (e) { alert(e?.response?.data?.detail || e?.message || '保存失败') }
  finally {
    savingMinute.value = false
    if (minuteFile.value) minuteFile.value.value = ''
  }
}
function openCreateAction() {
  Object.assign(createActionForm, {
    id: 0, title: '', content: '', source_meeting_id: '', source_quote: '',
    responsible_department_id: '', responsible_person_id: '',
    supervisor_id: '', required_completion_date: '', priority: '中',
  })
  showCreateAction.value = true
}
function openEditDraft(item) {
  Object.assign(createActionForm, {
    id: item.id,
    title: item.title || '',
    content: item.content || '',
    source_meeting_id: item.source_meeting_id || '',
    source_quote: item.source_quote || '',
    responsible_department_id: item.responsible_department_ids?.[0] || item.responsible_department_id || '',
    responsible_person_id: item.responsible_person_ids?.[0] || item.responsible_person_id || '',
    supervisor_id: item.supervisor_id || '',
    required_completion_date: item.required_completion_date || '',
    priority: item.priority || '中',
  })
  showCreateAction.value = true
}
async function saveCreatedAction(publishNow) {
  if (
    !createActionForm.title || !createActionForm.content
    || !createActionForm.responsible_department_id
    || !createActionForm.responsible_person_id
    || !createActionForm.supervisor_id
    || !createActionForm.required_completion_date
  ) {
    alert('请完整填写标题、内容、责任科室、责任人、主管领导和完成时间')
    return
  }
  savingAction.value = true
  try {
    const payload = {
      current_user: currentUser,
      ...createActionForm,
      source_meeting_id: createActionForm.source_meeting_id || null,
      responsible_department_ids: [createActionForm.responsible_department_id],
      responsible_person_ids: [createActionForm.responsible_person_id],
    }
    const result = createActionForm.id
      ? await updateAction(createActionForm.id, payload)
      : await createActionDraft(payload)
    const actionId = createActionForm.id || result.id
    if (publishNow) {
      await publishActions({ current_user: currentUser, ids: [actionId] })
    }
    showCreateAction.value = false
    await loadActions(1)
    alert(publishNow ? '行动项已新建并发布' : '行动项草稿已保存')
  } catch (e) {
    alert(e?.response?.data?.detail || e?.message || '新建行动项失败')
  } finally {
    savingAction.value = false
  }
}
async function deleteMinute(item) {
  if (!confirm(`确认删除未发布会议纪要“${item.meeting_name}”？\n关联的行动项草稿和上传附件也会一并删除。`)) return
  try {
    const result = await deleteMeetingMinute(item.id, currentUser)
    minutes.value = minutes.value.filter(row => row.id !== item.id)
    minuteOptions.value = minuteOptions.value.filter(row => row.id !== item.id)
    alert(result?.message || '未发布会议纪要已删除')
  } catch (e) {
    alert(e?.response?.data?.detail || e?.message || '删除会议纪要失败')
  }
}
function drill(card) {
  const query = card.key === 'total' ? {} : { metric: card.key === 'inProgress' ? 'active' : card.key }
  router.push({ path: '/action-items/ledger', query })
}
function openDept(department) { router.push({ path: '/action-items/ledger', query: { department } }) }
function canManagePublished(item) {
  return !!permissions.managePublished && !['草稿', '待发布', '已取消', '已完成'].includes(item.current_status)
}
async function completePublished(item) {
  const note = prompt(`将「${item.title}」设为已完成并闭环。\n确认后不再推送逾期/未更新提醒。`, '领导确认闭环')
  if (note === null) return
  try {
    const result = await forceCompleteAction(item.id, { current_user: currentUser, note })
    alert(result?.message || '行动项已闭环')
    await loadActions(page.value)
  } catch (e) { alert(e?.response?.data?.detail || e?.message || '闭环失败') }
}
async function cancelPublished(item) {
  const reason = prompt(`删除「${item.title}」并保留历史记录。\n可填写删除原因：`, '台账管理删除')
  if (reason === null) return
  try {
    await cancelPublishedAction(item.id, { current_user: currentUser, reason })
    alert('已删除（取消）')
    await loadActions(page.value)
  } catch (e) { alert(e?.response?.data?.detail || e?.message || '删除失败') }
}
async function exportLedger() {
  try {
    const blob = await exportActionItems({ current_user: currentUser, keyword: filters.keyword, department: filters.department, status: filters.status })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = `行动项台账_${new Date().toISOString().slice(0, 10)}.csv`; a.click()
    URL.revokeObjectURL(url)
  } catch (e) { alert(e?.response?.data?.detail || '导出失败') }
}
function resetActionFiltersFromRoute() {
  Object.assign(filters, {
    keyword: '', meeting_id: '', minutes_number: '', department: '',
    responsible_person: '', supervisor: '', status: '',
    deadline_from: '', deadline_to: '', overdue: false,
    sort_by: 'updated_at', sort_order: 'desc', metric: '',
  })
  if (route.query.department) filters.department = String(route.query.department)
  if (route.query.status) filters.status = String(route.query.status)
  if (route.query.overdue) filters.overdue = true
  if (route.query.metric) filters.metric = String(route.query.metric)
}
watch(mode, () => {
  resetActionFiltersFromRoute()
  loadCurrent()
})
watch(() => createActionForm.responsible_department_id, (department) => {
  const selected = directory.people.find(
    person => person.name === createActionForm.responsible_person_id,
  )
  if (selected && selected.department !== department) {
    createActionForm.responsible_person_id = ''
  }
})
onMounted(() => {
  resetActionFiltersFromRoute()
  bootstrap()
  unreadMessageTimer = window.setInterval(refreshUnreadMessageCount, 30000)
})
onBeforeUnmount(() => {
  aiAbortController?.abort()
  if (unreadMessageTimer) window.clearInterval(unreadMessageTimer)
})
</script>

<style scoped>
.action-page{padding:0 0 32px;color:#1e293b}.page-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}.page-head h1{margin:0;font-size:24px}.page-head p{margin:5px 0 0;color:#64748b;font-size:13px}.action-tabs{display:flex;gap:4px;padding:4px;background:#eef2f7;border-radius:10px;margin-bottom:16px;overflow:auto}.action-tabs a{padding:8px 14px;border-radius:7px;color:#64748b;text-decoration:none;white-space:nowrap;font-size:13px}.action-tabs a.router-link-active{background:#fff;color:#2563eb;font-weight:700;box-shadow:0 1px 4px #cbd5e1}.tab-with-badge{display:inline-flex;align-items:center;gap:6px}.tab-badge{display:inline-flex;align-items:center;justify-content:center;min-width:18px;height:18px;padding:0 5px;border-radius:99px;background:#ef4444;color:#fff;font-size:10px;font-weight:700;line-height:1;box-shadow:0 0 0 2px #eef2f7}.router-link-active .tab-badge{box-shadow:0 0 0 2px #fff}.panel,.metric-card{background:#fff;border:1px solid #e2e8f0;border-radius:10px;box-shadow:0 1px 3px rgba(15,23,42,.05)}.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}.metric-card{border:1px solid #e2e8f0;padding:16px;text-align:left;cursor:pointer}.metric-card span{display:block;color:#64748b;font-size:12px}.metric-card strong{display:inline-block;font-size:26px;margin-top:7px;color:#0f172a}.metric-card small{margin-left:3px;color:#64748b}.panel{padding:16px;margin-bottom:14px}.panel-title{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}.panel-title h2{font-size:16px;margin:0}.panel-title span{font-size:12px;color:#94a3b8}.dept-stat-list{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.dept-stat{border:1px solid #e2e8f0;border-radius:8px;background:#f8fafc;padding:12px;text-align:left;cursor:pointer}.dept-stat-head,.dept-stat-meta{display:flex;justify-content:space-between;font-size:12px}.dept-stat-meta{color:#64748b}.danger{color:#dc2626}.bar,.mini-progress{height:6px;background:#e2e8f0;border-radius:99px;overflow:hidden;margin:9px 0}.bar i,.mini-progress i{display:block;height:100%;background:#3b82f6;border-radius:inherit}.filters{display:flex;align-items:center;gap:9px;flex-wrap:wrap}.filters input,.filters select,.form-grid input,.form-grid select,.form-grid textarea{border:1px solid #cbd5e1;border-radius:6px;padding:7px 9px;background:#fff;font:inherit}.filters>input:not([type=checkbox]){min-width:180px}.filters label{font-size:13px;color:#475569}.btn{border:1px solid #cbd5e1;background:#fff;color:#334155;border-radius:6px;padding:7px 12px;cursor:pointer}.btn.primary{background:#2563eb;border-color:#2563eb;color:#fff}.btn:disabled{opacity:.55;cursor:not-allowed}.minute-row{display:flex;justify-content:space-between;gap:16px;padding:15px 4px;border-bottom:1px solid #e2e8f0}.minute-row:last-child{border:0}.minute-main{min-width:0}.row-title{display:flex;gap:8px;align-items:center}.minute-main p,.minute-main small{display:block;margin:6px 0 0;color:#64748b;font-size:12px}.minute-main small{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:720px}.row-actions{display:flex;gap:10px;align-items:center;white-space:nowrap;font-size:12px;color:#64748b}.link{color:#2563eb;text-decoration:none;border:0;background:none;cursor:pointer;margin-right:8px}.danger-link{color:#dc2626}.tag,.status,.risk{display:inline-block;border-radius:99px;padding:2px 7px;background:#eff6ff;color:#1d4ed8;font-size:11px}.risk{margin:5px 4px 0 0;background:#fff7ed;color:#c2410c}.risk.overdue{background:#fef2f2;color:#dc2626}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:900px;font-size:13px}th,td{padding:11px 10px;border-bottom:1px solid #e2e8f0;text-align:left;vertical-align:middle}th{background:#f8fafc;color:#64748b;font-weight:600}.action-title{max-width:360px}.action-title>a{font-weight:650;color:#1e293b;text-decoration:none}.action-title small,td small{display:block;color:#94a3b8;margin-top:4px}.mini-progress{width:75px;margin:0 0 4px}.pagination{display:flex;justify-content:flex-end;align-items:center;gap:10px;padding-top:13px;font-size:12px}.empty{text-align:center;padding:40px;color:#94a3b8}.modal-mask{position:fixed;inset:0;background:rgba(15,23,42,.45);z-index:1000;display:flex;align-items:center;justify-content:center;padding:20px}.modal{width:min(760px,96vw);max-height:92vh;overflow:auto;background:#fff;border-radius:12px;padding:20px}.modal-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}.modal-head h2{margin:0;font-size:18px}.modal-head button{border:0;background:none;font-size:24px;cursor:pointer}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:13px}.form-grid label{display:flex;flex-direction:column;gap:6px;font-size:13px}.form-grid .wide{grid-column:1/-1}.modal-actions{display:flex;justify-content:flex-end;gap:9px;margin-top:18px}@media(max-width:900px){.metric-grid{grid-template-columns:repeat(2,1fr)}.dept-stat-list{grid-template-columns:1fr}.form-grid{grid-template-columns:1fr}.form-grid .wide{grid-column:auto}}@media(max-width:560px){.metric-grid{grid-template-columns:1fr}.minute-row{flex-direction:column}.row-actions{flex-wrap:wrap}}
.message-title>div{display:flex;flex-direction:column;gap:5px}.message-filter{display:flex;align-items:center;gap:6px;color:#475569;font-size:13px}.message-row{display:grid;grid-template-columns:58px minmax(0,1fr) auto;gap:14px;align-items:center;padding:15px 6px;border-top:1px solid #e2e8f0}.message-row.unread{background:#f8fbff}.message-state{display:flex;align-items:center;gap:6px;color:#94a3b8;font-size:11px}.message-state i{width:8px;height:8px;border-radius:50%;background:#cbd5e1}.message-row.unread .message-state{color:#2563eb}.message-row.unread .message-state i{background:#2563eb}.message-main{min-width:0}.message-main p{margin:6px 0;color:#475569;font-size:13px}.message-main small{color:#94a3b8;font-size:11px}@media(max-width:620px){.message-row{grid-template-columns:1fr}.message-state{order:2}.message-row>.btn{justify-self:start}}
.receive-link{font-weight:700}
.load-error p{margin:0 0 12px;color:#dc2626}
.success-link{color:#059669}.priority-tag[data-priority="高"]{background:#fef2f2;color:#dc2626}.priority-tag[data-priority="低"]{background:#ecfdf5;color:#047857}.status[data-status="草稿"]{background:#f1f5f9;color:#475569}.status[data-status="待发布"]{background:#f5f3ff;color:#7c3aed}.status[data-status="待接收"]{background:#eff6ff;color:#1d4ed8}.status[data-status="进行中"]{background:#ecfeff;color:#0e7490}.status[data-status="待完工审批"]{background:#fffbeb;color:#b45309}.status[data-status="退回整改"]{background:#fef2f2;color:#dc2626}.status[data-status="已完成"]{background:#ecfdf5;color:#047857}.status[data-status="已取消"]{background:#f1f5f9;color:#64748b}tbody tr[data-priority="高"]{box-shadow:inset 3px 0 #ef4444}tbody tr[data-priority="中"]{box-shadow:inset 3px 0 #f59e0b}tbody tr[data-priority="低"]{box-shadow:inset 3px 0 #22c55e}
.status[data-status="已解析"]{background:#eff6ff;color:#1d4ed8}.status[data-status="AI已提取"]{background:#f5f3ff;color:#7c3aed}.status[data-status="已发布"]{background:#ecfdf5;color:#047857}.status[data-status="解析失败"]{background:#fef2f2;color:#dc2626}
.ai-log-mask{background:rgba(15,23,42,.62)}.ai-log-modal{width:min(1120px,97vw);height:min(760px,94vh);padding:0;overflow:hidden;display:flex;flex-direction:column}.ai-log-head{padding:17px 20px;margin:0;border-bottom:1px solid #e2e8f0}.ai-log-head h2{margin:0 0 5px}.ai-log-head p{margin:0;color:#64748b;font-size:12px}.ai-log-head-actions{display:flex;align-items:center;gap:12px}.ai-run-status{font-size:11px;border-radius:99px;padding:4px 9px;background:#f1f5f9;color:#475569}.ai-run-status.is-running{background:#eff6ff;color:#1d4ed8}.ai-run-status.is-success{background:#ecfdf5;color:#047857}.ai-run-status.is-error{background:#fef2f2;color:#dc2626}.ai-run-status.is-cancelled{background:#fff7ed;color:#c2410c}.ai-log-grid{display:grid;grid-template-columns:minmax(300px,.8fr) minmax(0,1.4fr);gap:0;min-height:0;flex:1}.ai-log-pane{min-height:0;overflow:auto;background:#f8fafc}.workflow-pane{border-right:1px solid #e2e8f0}.output-pane{background:#0f172a;color:#dbeafe}.ai-pane-title{position:sticky;top:0;z-index:2;display:flex;justify-content:space-between;align-items:center;padding:11px 14px;background:rgba(255,255,255,.96);border-bottom:1px solid #e2e8f0;font-size:12px;color:#334155}.ai-pane-title span{color:#94a3b8;font-size:10px}.output-pane .ai-pane-title{background:rgba(15,23,42,.97);border-color:#334155;color:#e2e8f0}.workflow-list{list-style:none;margin:0;padding:15px 15px 20px}.workflow-list li{position:relative;display:flex;gap:10px;padding:0 0 16px 14px;border-left:2px solid #cbd5e1}.workflow-list li:last-child{padding-bottom:0}.workflow-list li>i{position:absolute;left:-6px;top:3px;width:10px;height:10px;border-radius:50%;background:#94a3b8}.workflow-list li.is-running>i{background:#3b82f6;box-shadow:0 0 0 4px #dbeafe}.workflow-list li.is-done>i{background:#10b981}.workflow-list li.is-error>i{background:#ef4444}.workflow-list strong{font-size:12px}.workflow-list p{margin:4px 0;color:#64748b;font-size:11px;line-height:1.5}.workflow-list time{font-size:10px;color:#94a3b8}.ai-log-placeholder{padding:30px;text-align:center;color:#94a3b8}.ai-stream-section{margin:14px;border:1px solid #334155;border-radius:8px;overflow:hidden;background:rgba(2,6,23,.28)}.ai-stream-section-title{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 11px;border-bottom:1px solid #334155;color:#bfdbfe;font-size:11px}.ai-stream-section-title span{color:#64748b;font-size:10px}.ai-stream-section pre{min-height:80px;margin:0;padding:11px;color:#bfdbfe;font:12px/1.65 Consolas,"Microsoft YaHei",monospace;white-space:pre-wrap;overflow-wrap:anywhere}.ai-reasoning-section{border-color:#475569;background:rgba(30,41,59,.45)}.ai-reasoning-section pre{color:#cbd5e1}.ai-result-section pre{min-height:160px}.ai-log-error{margin:0;padding:10px 20px;background:#fef2f2;color:#b91c1c;font-size:12px;border-top:1px solid #fecaca}.ai-log-modal>.modal-actions{margin:0;padding:12px 20px;border-top:1px solid #e2e8f0}.btn.warning{border-color:#f59e0b;color:#b45309}@media(max-width:760px){.ai-log-grid{grid-template-columns:1fr;grid-template-rows:45% 55%}.workflow-pane{border-right:0;border-bottom:1px solid #e2e8f0}}
.dashboard-banner{position:relative;display:flex;align-items:center;justify-content:space-between;overflow:hidden;margin-bottom:14px;padding:23px 26px;border-radius:16px;color:#fff;background:linear-gradient(120deg,#071a3d 0%,#123d83 52%,#087ea4 100%);box-shadow:0 14px 34px rgba(15,59,130,.22)}.dashboard-banner:before,.dashboard-banner:after{content:"";position:absolute;border-radius:50%;pointer-events:none}.dashboard-banner:before{width:250px;height:250px;right:7%;top:-170px;border:1px solid rgba(103,232,249,.38);box-shadow:0 0 60px rgba(34,211,238,.18)}.dashboard-banner:after{width:120px;height:120px;right:-30px;bottom:-72px;background:rgba(56,189,248,.18);filter:blur(2px)}.dashboard-banner>div{position:relative;z-index:1}.dashboard-kicker{font:700 10px/1.2 Arial,sans-serif;letter-spacing:2.4px;color:#67e8f9}.dashboard-banner h2{margin:7px 0 5px;font-size:23px;letter-spacing:1px}.dashboard-banner p{margin:0;color:#bfdbfe;font-size:12px}.dashboard-live{display:flex;align-items:center;gap:8px;padding:7px 11px;border:1px solid rgba(125,211,252,.35);border-radius:99px;background:rgba(2,18,48,.28);color:#dbeafe;font-size:11px;backdrop-filter:blur(8px)}.dashboard-live i{width:7px;height:7px;border-radius:50%;background:#34d399;box-shadow:0 0 0 4px rgba(52,211,153,.14),0 0 12px #34d399;animation:dashboardPulse 1.8s infinite}@keyframes dashboardPulse{50%{opacity:.45;transform:scale(.8)}}.dashboard-metrics{grid-template-columns:repeat(5,1fr);gap:11px}.dashboard-metrics .metric-card{position:relative;overflow:hidden;min-height:126px;padding:16px;border:1px solid #dbe7f5;border-radius:13px;background:linear-gradient(145deg,#fff 40%,#f0f7ff);transition:transform .2s,box-shadow .2s,border-color .2s}.dashboard-metrics .metric-card:after{content:"";position:absolute;width:70px;height:70px;right:-30px;bottom:-38px;border-radius:50%;background:var(--metric-color,#3b82f6);opacity:.09}.dashboard-metrics .metric-card:hover{z-index:1;transform:translateY(-4px);border-color:color-mix(in srgb,var(--metric-color,#3b82f6) 45%,white);box-shadow:0 13px 28px rgba(30,64,175,.14)}.dashboard-metrics .metric-card>span{margin-top:12px;color:#53657c}.dashboard-metrics .metric-card strong{margin-top:3px;font-size:29px;line-height:1.1}.dashboard-metrics .metric-card em{position:absolute;right:13px;top:16px;color:#94a3b8;font-size:9px;font-style:normal;opacity:0;transform:translateX(-4px);transition:.2s}.dashboard-metrics .metric-card:hover em{opacity:1;transform:none}.metric-icon{display:flex;align-items:center;justify-content:center;width:29px;height:29px;border-radius:9px;color:#fff;background:var(--metric-color,#3b82f6);box-shadow:0 6px 14px color-mix(in srgb,var(--metric-color,#3b82f6) 30%,transparent);font-size:15px;font-style:normal;font-weight:800}.metric-card[data-metric="completed"],.metric-card[data-metric="completedThisWeek"]{--metric-color:#10b981}.metric-card[data-metric="inProgress"],.metric-card[data-metric="newThisWeek"]{--metric-color:#3b82f6}.metric-card[data-metric="overdue"]{--metric-color:#ef4444}.metric-card[data-metric="dueSoon"],.metric-card[data-metric="pendingApproval"]{--metric-color:#f59e0b}.metric-card[data-metric="stale"]{--metric-color:#8b5cf6}.dashboard-panel{padding:20px;border-radius:14px;background:linear-gradient(180deg,#fff,#f8fbff);box-shadow:0 8px 25px rgba(15,50,90,.07)}.dashboard-panel .panel-title small{display:block;margin-bottom:4px;color:#3b82f6;font:700 9px/1 Arial,sans-serif;letter-spacing:1.5px}.dashboard-panel .dept-stat{position:relative;overflow:hidden;padding:14px;border-color:#dbe7f5;background:#fff;transition:.2s}.dashboard-panel .dept-stat:hover{transform:translateY(-2px);border-color:#93c5fd;box-shadow:0 9px 20px rgba(37,99,235,.1)}.dashboard-panel .dept-stat-head strong{color:#16365f}.dashboard-panel .bar{height:7px;background:#e8eff8}.dashboard-panel .bar i{position:relative;background:linear-gradient(90deg,#2563eb,#22d3ee);box-shadow:0 0 10px rgba(34,211,238,.35)}.dashboard-panel .bar i:after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(255,255,255,.65),transparent);animation:barShine 2.3s infinite}@keyframes barShine{from{transform:translateX(-100%)}to{transform:translateX(100%)}}@media(max-width:1100px){.dashboard-metrics{grid-template-columns:repeat(3,1fr)}}@media(max-width:700px){.dashboard-banner{align-items:flex-start;gap:18px;padding:19px;flex-direction:column}.dashboard-metrics{grid-template-columns:repeat(2,1fr)}}@media(max-width:430px){.dashboard-metrics{grid-template-columns:1fr}}
</style>
