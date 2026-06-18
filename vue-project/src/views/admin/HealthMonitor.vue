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
              <h2 class="section-title">大模型配置</h2>
              <p class="section-desc">
                配置智能助手所用大模型。优先级：填写 DeepSeek 密钥时使用联网 DeepSeek；密钥为空时使用下方选中的本地模型（写入 webconfig 的 llm_base_url / llm_model）。
              </p>
            </div>
            <div class="config-actions">
              <button type="button" class="btn btn-secondary btn-sm" :disabled="llmLoading" @click="fetchLlmConfig">刷新</button>
            </div>
          </div>
          <div v-if="llmLoading" class="status-message">正在加载大模型配置…</div>
          <template v-else>
            <div class="llm-active-banner" :class="llmConfig.provider === 'deepseek' ? 'is-deepseek' : 'is-local'">
              <span class="llm-active-label">当前生效</span>
              <strong v-if="llmConfig.provider === 'deepseek'">联网 DeepSeek</strong>
              <strong v-else>本地模型：{{ llmConfig.active.model || '未设置' }}</strong>
              <span v-if="llmConfig.provider === 'local' && llmConfig.active.base_url" class="llm-active-url">{{ llmConfig.active.base_url }}</span>
            </div>

            <h3 class="email-settings-title">联网 DeepSeek 密钥</h3>
            <p class="email-settings-hint">
              {{ llmConfig.deepseek_configured ? `已配置（${llmConfig.deepseek_key_masked}），系统优先使用联网模型` : '未配置，系统将使用本地模型' }}
            </p>
            <div class="llm-key-row">
              <input v-model.trim="deepseekKeyInput" type="password" autocomplete="new-password" class="recipient-input llm-key-input" placeholder="输入新的 DeepSeek API Key">
              <button type="button" class="btn btn-primary btn-sm" :disabled="llmSaving" @click="saveDeepseekKeyAction">更新密钥</button>
              <button type="button" class="btn btn-secondary btn-sm" :disabled="llmSaving || !llmConfig.deepseek_configured" @click="clearDeepseekKeyAction">清空（用本地）</button>
            </div>

            <h3 class="email-settings-title">本地大模型候选</h3>
            <p v-if="!llmConfig.models.length" class="email-settings-hint">暂无本地模型，请在下方添加后点击「选用」。</p>
            <div v-else class="llm-model-list">
              <div v-for="m in llmConfig.models" :key="m.id" class="llm-model-row" :class="{ 'is-active': m.is_active }">
                <div class="llm-model-info">
                  <div class="llm-model-line">
                    <span class="llm-model-name">{{ m.name }}</span>
                    <span v-if="m.is_active" class="llm-model-badge">当前选中</span>
                    <span class="llm-model-tag">{{ m.use_extra ? 'Ollama 本地' : 'OpenAI 兼容网关' }}</span>
                    <span v-if="m.has_key" class="llm-model-tag llm-model-tag--key">需鉴权 {{ m.key_masked }}</span>
                  </div>
                  <span class="llm-model-meta">{{ m.model }} · {{ m.base_url }}</span>
                </div>
                <div class="llm-model-ops">
                  <button type="button" class="btn btn-secondary btn-sm" :disabled="llmSaving || m.is_active" @click="activateModel(m)">{{ m.is_active ? '已选用' : '选用' }}</button>
                  <button type="button" class="btn btn-secondary btn-sm" :disabled="llmSaving" @click="deleteModel(m)">删除</button>
                </div>
              </div>
            </div>

            <h3 class="email-settings-title">添加本地模型</h3>
            <div class="llm-add-grid">
              <input v-model.trim="newModel.name" type="text" class="recipient-input" placeholder="名称，如 本地 DeepSeek-V4">
              <input v-model.trim="newModel.model" type="text" class="recipient-input" placeholder="模型名，如 DeepSeek-V4">
              <select v-model="newModel.use_extra" class="recipient-select llm-add-wide">
                <option :value="true">接口类型：Ollama 本地（带 enable_thinking 参数）</option>
                <option :value="false">接口类型：OpenAI 兼容网关（如本地 DeepSeek-V4）</option>
              </select>
              <input v-model.trim="newModel.base_url" type="text" class="recipient-input llm-add-wide" placeholder="base_url，如 http://10.3.26.243:30080/prod-api/api_ability/202605212224_v1/v1">
              <input v-model.trim="newModel.api_key" type="password" autocomplete="new-password" class="recipient-input llm-add-wide" placeholder="鉴权 Token（Ollama 可留空；DeepSeek-V4 填 JWT）">
              <button type="button" class="btn btn-primary btn-sm llm-add-btn" :disabled="llmSaving" @click="addModel">添加模型</button>
            </div>

            <p v-if="llmMessage" class="config-message">{{ llmMessage }}</p>
          </template>
        </section>

        <section class="card admin-config-card">
          <div class="config-card-head">
            <div>
              <h2 class="section-title">打卡数据配置</h2>
              <p class="section-desc">
                配置每日自动拉取并处理数据的时间（可多条）；每条任务可单独设置智能建议截止日（今日 / 前一日）。时区：{{ attendanceFetchTimezone || 'Asia/Shanghai' }}（来自服务端配置）。
              </p>
            </div>
            <div class="config-actions">
              <button type="button" class="btn btn-secondary btn-sm" :disabled="attendanceFetchLoading || attendanceFetchSaving" @click="addAttendanceSchedule">新增时间</button>
              <button type="button" class="btn btn-primary btn-sm" :disabled="attendanceFetchLoading || attendanceFetchSaving" @click="saveAttendanceFetchConfig">
                {{ attendanceFetchSaving ? '保存中…' : '保存配置' }}
              </button>
            </div>
          </div>
          <div v-if="attendanceFetchLoading" class="status-message">正在加载打卡配置…</div>
          <template v-else>
            <p class="email-settings-hint attendance-schedule-intro">
              每条任务独立设置执行时间与建议截止日；拉取完成后仅生成到该条所选的今日或前一日，避免未上传日期被误判为全员缺勤。
            </p>
            <h3 class="email-settings-title">每日自动拉取任务</h3>
            <p v-if="!attendanceSchedules.length" class="email-settings-hint">暂无任务，请点击「新增时间」。</p>
            <div v-else class="attendance-schedule-list">
              <div v-for="(row, idx) in attendanceSchedules" :key="'sch-' + idx" class="attendance-schedule-row">
                <label class="schedule-enable">
                  <input v-model="row.enabled" type="checkbox">
                  <span>启用</span>
                </label>
                <label class="schedule-time-field">
                  <span>时</span>
                  <select v-model.number="row.hour" class="schedule-time-select">
                    <option v-for="h in hourOptions" :key="h" :value="h">{{ String(h).padStart(2, '0') }}</option>
                  </select>
                </label>
                <label class="schedule-time-field">
                  <span>分</span>
                  <select v-model.number="row.minute" class="schedule-time-select">
                    <option v-for="m in minuteOptions" :key="m" :value="m">{{ String(m).padStart(2, '0') }}</option>
                  </select>
                </label>
                <label class="schedule-cutoff-field">
                  <span>建议截止</span>
                  <select v-model="row.suggestion_cutoff" class="schedule-cutoff-select">
                    <option value="today">今日</option>
                    <option value="yesterday">前一日</option>
                  </select>
                </label>
                <span class="schedule-preview">
                  每日 {{ String(row.hour).padStart(2, '0') }}:{{ String(row.minute).padStart(2, '0') }} 执行，建议至{{ row.suggestion_cutoff === 'today' ? '今日' : '前一日' }}
                </span>
                <button type="button" class="btn btn-secondary btn-sm" :disabled="attendanceSchedules.length <= 1" @click="removeAttendanceSchedule(idx)">删除</button>
              </div>
            </div>
          </template>
          <p v-if="attendanceFetchMessage" class="config-message">{{ attendanceFetchMessage }}</p>
        </section>

        <section class="card admin-config-card">
          <div class="config-card-head">
            <div>
              <h2 class="section-title">排班邮件配置</h2>
              <p class="section-desc">控制各科室是否启用周排班自动/手动发送与提醒，并配置自动发送时间、排班区间是否含发送当天与收件人（固定 17:00 发送）。</p>
            </div>
            <div class="config-actions">
              <button type="button" class="btn btn-secondary btn-sm" :disabled="shiftEmailLoading || shiftEmailSaving" @click="setAllShiftEmailEnabled(true)">功能全选</button>
              <button type="button" class="btn btn-secondary btn-sm" :disabled="shiftEmailLoading || shiftEmailSaving" @click="setAllShiftEmailEnabled(false)">功能全关</button>
              <button type="button" class="btn btn-primary btn-sm" :disabled="shiftEmailLoading || shiftEmailSaving" @click="saveShiftEmailConfig">
                {{ shiftEmailSaving ? '保存中…' : '保存配置' }}
              </button>
            </div>
          </div>
          <div v-if="shiftEmailLoading" class="status-message">正在加载排班邮件配置…</div>
          <div v-else-if="!shiftEmailItems.length" class="status-message">暂无可配置科室。</div>
          <template v-else>
            <div class="dept-switch-grid">
              <label v-for="item in shiftEmailItems" :key="'sw-' + item.department" class="dept-switch">
                <span class="dept-name">{{ item.department }}</span>
                <input v-model="item.enabled" type="checkbox">
                <span class="switch-visual" :class="{ 'is-on': item.enabled }"></span>
                <span class="switch-text" :class="{ 'is-on': item.enabled }">{{ item.enabled ? '启用' : '关闭' }}</span>
              </label>
            </div>
            <div v-if="shiftEmailEnabledItems.length" class="shift-email-preview-panel">
              <h3 class="shift-email-preview-panel-title">邮件发送信息汇总</h3>
              <p class="shift-email-preview-intro">
                按发送时间与收件人单位合并发送：同一单位、同一发送时间只发一封邮件（可含多个科室附件）。
                排班表收件人为邮件收件人；各科室主任/副主任/班组长及公司经理/副经理/经理助理（已配置企业邮箱）为抄送。
              </p>
              <ul class="shift-email-preview-list">
                <li v-for="(line, idx) in shiftEmailPreviewLines" :key="'pv-' + idx">
                  {{ line }}
                </li>
              </ul>
            </div>
            <h3 v-if="shiftEmailEnabledItems.length" class="email-settings-title">各科室邮件发送时间与收件人</h3>
            <p v-else class="email-settings-hint">当前无启用邮件功能的科室；在上方打开开关后可配置发送时间与收件人。</p>
            <div v-if="shiftEmailEnabledItems.length" class="dept-email-list">
              <div v-for="item in shiftEmailEnabledItems" :key="'em-' + item.department" class="dept-email-card">
                <div class="dept-email-head">
                  <span class="dept-email-name">{{ item.department }}</span>
                  <label class="dept-email-send">
                    <span>自动发送</span>
                    <select v-model.number="item.email_send_weekday" class="email-send-select" @click.stop>
                      <option v-for="opt in emailSendWeekdayOptions" :key="opt.value" :value="opt.value">
                        每周{{ opt.label }} 17:00
                      </option>
                    </select>
                  </label>
                  <label class="dept-email-include-send">
                    <span>含发送日</span>
                    <select v-model="item.email_include_send_day" class="email-include-send-select" @click.stop>
                      <option :value="false">否</option>
                      <option :value="true">是</option>
                    </select>
                  </label>
                </div>
                <div class="recipient-toolbar">
                  <span class="recipient-label">排班表收件人</span>
                  <button type="button" class="btn btn-secondary btn-sm" @click="addShiftEmailRecipient(item)">新增收件人</button>
                </div>
                <div v-if="item.email_recipients.length" class="recipient-list">
                  <div v-for="(recipient, idx) in item.email_recipients" :key="idx" class="recipient-row">
                    <input v-model.trim="recipient.name" type="text" class="recipient-input" placeholder="姓名">
                    <select v-model="recipient.unit" class="recipient-select recipient-select-unit">
                      <option v-for="u in recipientUnitOptions" :key="u" :value="u">{{ u }}</option>
                    </select>
                    <input v-model.trim="recipient.email" type="email" class="recipient-input recipient-input-email" placeholder="邮箱">
                    <button type="button" class="btn btn-secondary btn-sm" @click="removeShiftEmailRecipient(item, idx)">删除</button>
                  </div>
                </div>
                <p v-else class="recipient-empty">暂未配置收件人</p>
              </div>
            </div>
          </template>
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
            <p v-if="todoReminderResult.skippedOverThreshold">跳过（2天内已发）：{{ todoReminderResult.skippedOverThreshold }} 人</p>
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
  getAttendanceFetchConfig,
  saveAttendanceFetchConfig as saveAttendanceFetchConfigApi,
  runTodoReminder,
  getLlmConfig,
  saveDeepseekKey,
  addLlmModel,
  deleteLlmModel,
  activateLlmModel,
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
const shiftEmailCompanyLeaders = ref([])
const shiftEmailMessage = ref('')
const attendanceFetchLoading = ref(false)
const attendanceFetchSaving = ref(false)
const attendanceFetchMessage = ref('')
const attendanceSchedules = ref([])
const attendanceFetchTimezone = ref('Asia/Shanghai')

const llmLoading = ref(false)
const llmSaving = ref(false)
const llmMessage = ref('')
const llmConfig = ref({
  provider: 'local',
  deepseek_configured: false,
  deepseek_key_masked: '',
  active: { base_url: '', model: '' },
  models: [],
})
const deepseekKeyInput = ref('')
const newModel = ref({ name: '', base_url: '', model: '', api_key: '', use_extra: true })

function currentName() {
  const user = JSON.parse(localStorage.getItem('userInfo') || '{}')
  return (user.name || user.userName || '').trim()
}

const hourOptions = Array.from({ length: 24 }, (_, i) => i)
const minuteOptions = Array.from({ length: 60 }, (_, i) => i)

const emailSendWeekdayOptions = [
  { value: 0, label: '周一' },
  { value: 1, label: '周二' },
  { value: 2, label: '周三' },
  { value: 3, label: '周四' },
  { value: 4, label: '周五' },
  { value: 5, label: '周六' },
  { value: 6, label: '周日' },
]

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/
const recipientUnitOptions = [
  '水电分厂',
  '汽发分厂',
  '线圈分厂',
  '冲剪分厂',
  '冷作分厂',
  '成品分厂',
  '大电机研究所',
  '金工分厂',
  '其他',
]

function shiftEmailRangeHint(sendWeekday, includeSendDay) {
  const sendWd = Number.isFinite(Number(sendWeekday)) ? Number(sendWeekday) : 4
  const sendLabel = emailSendWeekdayOptions.find((o) => o.value === sendWd)?.label || '周五'
  if (includeSendDay) {
    const endWd = (sendWd + 6) % 7
    const endLabel = emailSendWeekdayOptions.find((o) => o.value === endWd)?.label || ''
    return `${sendLabel}至${endLabel}（7天，含发送日）`
  }
  const startWd = (sendWd + 1) % 7
  const startLabel = emailSendWeekdayOptions.find((o) => o.value === startWd)?.label || ''
  return `${startLabel}至下${sendLabel}（7天）`
}

function mapShiftEmailItem(item) {
  return {
    department: item.department,
    enabled: !!item.enabled,
    email_send_weekday: Number.isFinite(Number(item.email_send_weekday)) ? Number(item.email_send_weekday) : 4,
    email_include_send_day: !!item.email_include_send_day,
    email_recipients: (item.email_recipients || []).map((r) => ({
      name: (r?.name || '').trim(),
      email: (r?.email || '').trim(),
      unit: recipientUnitOptions.includes((r?.unit || '').trim()) ? (r?.unit || '').trim() : '其他',
    })),
    leader_recipients: (item.leader_recipients || []).map((r) => ({
      name: (r?.name || '').trim(),
      email: (r?.email || '').trim(),
      jb: (r?.jb || '').trim(),
    })),
  }
}

const SHIFT_EMAIL_SEND_HOUR = 17

function nextShiftEmailSendTime(sendWeekdayPython, nowDate = new Date()) {
  const wd = Number.isFinite(Number(sendWeekdayPython)) ? Number(sendWeekdayPython) : 4
  const jsWeekday = (wd + 1) % 7
  const target = new Date(nowDate.getFullYear(), nowDate.getMonth(), nowDate.getDate())
  const addDays = (jsWeekday - target.getDay() + 7) % 7
  target.setDate(target.getDate() + addDays)
  target.setHours(SHIFT_EMAIL_SEND_HOUR, 0, 0, 0)
  if (target <= nowDate) target.setDate(target.getDate() + 7)
  return target
}

function formatShiftEmailSendWhen(d) {
  return `${d.getMonth() + 1}月${d.getDate()}日${SHIFT_EMAIL_SEND_HOUR}:00`
}

function normalizeRecipientUnit(unit) {
  const u = (unit || '').trim()
  return recipientUnitOptions.includes(u) ? u : '其他'
}

const shiftEmailPreviewLines = computed(() => {
  const buckets = new Map()
  const companyLeaders = shiftEmailCompanyLeaders.value || []
  const companyLeaderNames = companyLeaders.map((l) => (l?.name || '').trim()).filter(Boolean)
  const companyLeaderEmails = new Set(
    companyLeaders.map((l) => (l?.email || '').trim().toLowerCase()).filter(Boolean),
  )
  for (const item of shiftEmailEnabledItems.value) {
    const wd = item.email_send_weekday
    const includeSend = !!item.email_include_send_day
    const leaders = item.leader_recipients || []
    const config = item.email_recipients || []
    const units = new Set()
    for (const r of config) {
      if ((r.email || '').trim()) units.add(normalizeRecipientUnit(r.unit))
    }
    if (!units.size && leaders.some((l) => (l.email || '').trim())) {
      units.add('其他')
    }
    if (!units.size) continue

    const leaderEmails = new Set([
      ...leaders.map((l) => (l.email || '').trim().toLowerCase()).filter(Boolean),
      ...companyLeaderEmails,
    ])

    for (const unit of units) {
      const key = `${wd}|${includeSend ? 1 : 0}|${unit}`
      if (!buckets.has(key)) {
        buckets.set(key, {
          sendWeekday: wd,
          includeSendDay: includeSend,
          unit,
          departments: [],
          configNames: new Set(),
          leadersByDept: [],
          sortAt: nextShiftEmailSendTime(wd).getTime(),
        })
      }
      const bucket = buckets.get(key)
      bucket.departments.push(item.department)

      const leaderNames = leaders.map((l) => l.name).filter(Boolean)
      if (leaderNames.length) {
        bucket.leadersByDept.push({ dept: item.department, names: leaderNames })
      }
      for (const r of config) {
        if (normalizeRecipientUnit(r.unit) !== unit) continue
        const email = (r.email || '').trim().toLowerCase()
        if (r.name && (!email || !leaderEmails.has(email))) {
          bucket.configNames.add(r.name)
        }
      }
    }
  }

  return [...buckets.values()]
    .sort((a, b) => a.sortAt - b.sortAt || a.unit.localeCompare(b.unit, 'zh-CN'))
    .map((bucket) => {
      const whenStr = formatShiftEmailSendWhen(nextShiftEmailSendTime(bucket.sendWeekday))
      const deptPart = bucket.departments.join('、')
      const configPart = [...bucket.configNames].join('、')
      const ccPart = bucket.leadersByDept
        .map(({ dept, names }) => `${dept}管理人员（${names.join('、')}）`)
        .join('；')
      const ccPieces = []
      if (ccPart) ccPieces.push(ccPart)
      if (companyLeaderNames.length) {
        ccPieces.push(`公司领导（${companyLeaderNames.join('、')}）`)
      }

      const toPart = configPart ? `收件人（${configPart}）` : '收件人（未配置）'
      const ccSuffix = ccPieces.length ? `，抄送${ccPieces.join('；')}` : ''

      const rangeHint = shiftEmailRangeHint(bucket.sendWeekday, bucket.includeSendDay)
      return `将于${whenStr}，向${bucket.unit}发送${deptPart}排班表（${rangeHint}），${toPart}${ccSuffix}。`
    })
})

function addShiftEmailRecipient(item) {
  item.email_recipients.push({ name: '', unit: '其他', email: '' })
}

function removeShiftEmailRecipient(item, index) {
  item.email_recipients.splice(index, 1)
}

function normalizeDeptEmailRecipients(recipients) {
  const normalized = []
  const seen = new Set()
  for (const row of recipients || []) {
    const name = (row?.name || '').trim()
    const email = (row?.email || '').trim()
    const unit = (row?.unit || '').trim()
    if (!name && !email) continue
    if (!name || !email) {
      return { error: '请完整填写各科室排班表收件人的姓名和邮箱' }
    }
    if (!unit || !recipientUnitOptions.includes(unit)) {
      return { error: '请为收件人选择单位' }
    }
    if (!EMAIL_PATTERN.test(email)) {
      return { error: `排班表收件人邮箱格式不正确：${email}` }
    }
    const key = email.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    normalized.push({ name, unit, email })
  }
  return { recipients: normalized }
}

const shiftEmailEnabledItems = computed(() => shiftEmailItems.value.filter((item) => item.enabled))

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
    shiftEmailItems.value = (res?.items || []).map(mapShiftEmailItem)
    shiftEmailCompanyLeaders.value = (res?.company_leader_recipients || []).map((r) => ({
      name: (r?.name || '').trim(),
      email: (r?.email || '').trim(),
      jb: (r?.jb || '').trim(),
    }))
  } catch (e) {
    console.error(e)
    shiftEmailItems.value = []
    shiftEmailCompanyLeaders.value = []
    shiftEmailMessage.value = e?.response?.data?.detail || e?.message || '排班邮件配置加载失败'
  } finally {
    shiftEmailLoading.value = false
  }
}

function setAllShiftEmailEnabled(enabled) {
  shiftEmailItems.value.forEach((item) => {
    item.enabled = enabled
  })
}

function mapAttendanceSchedule(row) {
  return {
    hour: Number.isFinite(Number(row?.hour)) ? Number(row.hour) : 0,
    minute: Number.isFinite(Number(row?.minute)) ? Number(row.minute) : 0,
    enabled: row?.enabled !== false,
    suggestion_cutoff: row?.suggestion_cutoff === 'today' ? 'today' : 'yesterday',
  }
}

async function fetchAttendanceFetchConfig() {
  const user = JSON.parse(localStorage.getItem('userInfo') || '{}')
  const name = (user.name || user.userName || '').trim()
  if (!name) return
  attendanceFetchLoading.value = true
  attendanceFetchMessage.value = ''
  try {
    const res = await getAttendanceFetchConfig({ current_user: name })
    attendanceFetchTimezone.value = res?.timezone || 'Asia/Shanghai'
    const rows = (res?.schedules || []).map(mapAttendanceSchedule)
    attendanceSchedules.value = rows.length ? rows : [{ hour: 0, minute: 0, enabled: true, suggestion_cutoff: 'yesterday' }]
  } catch (e) {
    console.error(e)
    attendanceSchedules.value = [{ hour: 0, minute: 0, enabled: true, suggestion_cutoff: 'yesterday' }]
    attendanceFetchMessage.value = e?.response?.data?.detail || e?.message || '打卡配置加载失败'
  } finally {
    attendanceFetchLoading.value = false
  }
}

function addAttendanceSchedule() {
  if (attendanceSchedules.value.length >= 24) {
    attendanceFetchMessage.value = '最多添加 24 条执行时间'
    return
  }
  attendanceSchedules.value.push({ hour: 0, minute: 0, enabled: true, suggestion_cutoff: 'yesterday' })
}

function removeAttendanceSchedule(index) {
  if (attendanceSchedules.value.length <= 1) return
  attendanceSchedules.value.splice(index, 1)
}

async function saveAttendanceFetchConfig() {
  const user = JSON.parse(localStorage.getItem('userInfo') || '{}')
  const name = (user.name || user.userName || '').trim()
  if (!name) return
  const enabledRows = attendanceSchedules.value.filter((r) => r.enabled)
  if (!enabledRows.length) {
    attendanceFetchMessage.value = '请至少启用一条拉取时间'
    return
  }
  attendanceFetchSaving.value = true
  attendanceFetchMessage.value = ''
  try {
    const res = await saveAttendanceFetchConfigApi({
      current_user: name,
      schedules: attendanceSchedules.value.map(mapAttendanceSchedule),
    })
    attendanceFetchTimezone.value = res?.timezone || attendanceFetchTimezone.value
    attendanceSchedules.value = (res?.schedules || []).map(mapAttendanceSchedule)
    attendanceFetchMessage.value = res?.message || '打卡配置已保存'
    await fetchOverview()
  } catch (e) {
    attendanceFetchMessage.value = e?.response?.data?.detail || e?.message || '保存打卡配置失败'
  } finally {
    attendanceFetchSaving.value = false
  }
}

async function saveShiftEmailConfig() {
  const user = JSON.parse(localStorage.getItem('userInfo') || '{}')
  const name = (user.name || user.userName || '').trim()
  if (!name) return
  shiftEmailSaving.value = true
  shiftEmailMessage.value = ''
  const departmentsPayload = []
  for (const item of shiftEmailItems.value) {
    const parsed = normalizeDeptEmailRecipients(item.email_recipients)
    if (parsed.error) {
      shiftEmailMessage.value = parsed.error
      shiftEmailSaving.value = false
      return
    }
    departmentsPayload.push({
      department: item.department,
      email_send_weekday: item.email_send_weekday,
      email_include_send_day: !!item.email_include_send_day,
      email_recipients: parsed.recipients,
    })
  }
  try {
    const enabledDepartments = shiftEmailItems.value
      .filter((item) => item.enabled)
      .map((item) => item.department)
    const res = await saveShiftEmailFeatureConfig({
      current_user: name,
      enabled_departments: enabledDepartments,
      departments: departmentsPayload,
    })
    shiftEmailItems.value = (res?.items || []).map(mapShiftEmailItem)
    shiftEmailCompanyLeaders.value = (res?.company_leader_recipients || []).map((r) => ({
      name: (r?.name || '').trim(),
      email: (r?.email || '').trim(),
      jb: (r?.jb || '').trim(),
    }))
    shiftEmailMessage.value = res?.message || '排班邮件配置已保存'
  } catch (e) {
    shiftEmailMessage.value = e?.response?.data?.detail || e?.message || '保存排班邮件功能配置失败'
  } finally {
    shiftEmailSaving.value = false
  }
}

async function fetchLlmConfig() {
  const name = currentName()
  if (!name) return
  llmLoading.value = true
  llmMessage.value = ''
  try {
    const res = await getLlmConfig({ current_user: name })
    llmConfig.value = {
      provider: res?.provider || 'local',
      deepseek_configured: !!res?.deepseek_configured,
      deepseek_key_masked: res?.deepseek_key_masked || '',
      active: { base_url: res?.active?.base_url || '', model: res?.active?.model || '' },
      models: (res?.models || []).map((m) => ({ ...m, is_active: !!m.is_active })),
    }
  } catch (e) {
    llmMessage.value = e?.response?.data?.detail || e?.message || '大模型配置加载失败'
  } finally {
    llmLoading.value = false
  }
}

async function saveDeepseekKeyAction() {
  const name = currentName()
  if (!name) return
  if (!deepseekKeyInput.value) {
    llmMessage.value = '请输入要保存的 DeepSeek 密钥'
    return
  }
  llmSaving.value = true
  llmMessage.value = ''
  try {
    const res = await saveDeepseekKey({ current_user: name, deepseek_api_key: deepseekKeyInput.value, clear: false })
    deepseekKeyInput.value = ''
    llmMessage.value = res?.message || '已保存'
    await fetchLlmConfig()
  } catch (e) {
    llmMessage.value = e?.response?.data?.detail || e?.message || '保存失败'
  } finally {
    llmSaving.value = false
  }
}

async function clearDeepseekKeyAction() {
  const name = currentName()
  if (!name) return
  if (!window.confirm('确定清空 DeepSeek 密钥并改用本地模型？')) return
  llmSaving.value = true
  llmMessage.value = ''
  try {
    const res = await saveDeepseekKey({ current_user: name, deepseek_api_key: '', clear: true })
    llmMessage.value = res?.message || '已清空'
    await fetchLlmConfig()
  } catch (e) {
    llmMessage.value = e?.response?.data?.detail || e?.message || '清空失败'
  } finally {
    llmSaving.value = false
  }
}

async function addModel() {
  const name = currentName()
  if (!name) return
  if (!newModel.value.name || !newModel.value.base_url || !newModel.value.model) {
    llmMessage.value = '请填写完整：名称 / base_url / 模型名'
    return
  }
  llmSaving.value = true
  llmMessage.value = ''
  try {
    const res = await addLlmModel({
      current_user: name,
      name: newModel.value.name,
      base_url: newModel.value.base_url,
      model: newModel.value.model,
      api_key: newModel.value.api_key,
      use_extra: newModel.value.use_extra,
    })
    newModel.value = { name: '', base_url: '', model: '', api_key: '', use_extra: true }
    llmMessage.value = res?.message || '已添加'
    await fetchLlmConfig()
  } catch (e) {
    llmMessage.value = e?.response?.data?.detail || e?.message || '添加失败'
  } finally {
    llmSaving.value = false
  }
}

async function deleteModel(m) {
  const name = currentName()
  if (!name) return
  if (!window.confirm(`确定删除本地模型「${m.name}」？`)) return
  llmSaving.value = true
  llmMessage.value = ''
  try {
    const res = await deleteLlmModel(m.id, { current_user: name })
    llmMessage.value = res?.message || '已删除'
    await fetchLlmConfig()
  } catch (e) {
    llmMessage.value = e?.response?.data?.detail || e?.message || '删除失败'
  } finally {
    llmSaving.value = false
  }
}

async function activateModel(m) {
  const name = currentName()
  if (!name) return
  llmSaving.value = true
  llmMessage.value = ''
  try {
    const res = await activateLlmModel(m.id, { current_user: name })
    llmMessage.value = res?.message || '已切换'
    await fetchLlmConfig()
    await fetchOverview()
  } catch (e) {
    llmMessage.value = e?.response?.data?.detail || e?.message || '切换失败'
  } finally {
    llmSaving.value = false
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
      await Promise.all([fetchOverview(), fetchShiftEmailConfig(), fetchAttendanceFetchConfig(), fetchLlmConfig()])
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
  max-width: 1080px;
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
.email-settings-title {
  margin: var(--spacing-lg) 0 var(--spacing-md);
  font-size: 0.95rem;
  font-weight: 600;
}
.email-settings-hint {
  margin: var(--spacing-lg) 0 0;
  font-size: 0.85rem;
  color: var(--color-text-tertiary);
}
.dept-email-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.dept-email-card {
  padding: 12px 14px;
  border: 1px solid var(--color-border-base);
  border-radius: 8px;
  background: var(--color-bg-layout);
}
.dept-email-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.dept-email-name {
  font-weight: 600;
  font-size: 0.92rem;
}
.dept-email-send,
.dept-email-include-send {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}
.email-send-select {
  min-width: 168px;
}
.email-include-send-select {
  min-width: 56px;
}
.email-send-select,
.email-include-send-select {
  padding: 4px 8px;
  border: 1px solid var(--color-border-base);
  border-radius: 6px;
  font-size: 0.85rem;
  background: var(--color-bg-container);
}
.recipient-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.recipient-label {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}
.recipient-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.recipient-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.recipient-input {
  flex: 1;
  min-width: 100px;
  padding: 4px 8px;
  border: 1px solid var(--color-border-base);
  border-radius: 6px;
  font-size: 0.85rem;
}
.recipient-input-email {
  flex: 2;
  min-width: 180px;
}
.recipient-select {
  padding: 4px 8px;
  border: 1px solid var(--color-border-base);
  border-radius: 6px;
  font-size: 0.85rem;
  background: var(--color-bg-container);
}
.recipient-select-unit {
  min-width: 120px;
}
.recipient-empty {
  margin: 0;
  font-size: 0.82rem;
  color: var(--color-text-tertiary);
}
.attendance-schedule-intro {
  margin: 0 0 var(--spacing-md);
}
.attendance-schedule-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.attendance-schedule-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--color-border-base);
  border-radius: 8px;
  background: var(--color-bg-layout);
}
.schedule-enable {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  min-width: 64px;
}
.schedule-time-field {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}
.schedule-time-select {
  min-width: 72px;
  padding: 4px 8px;
  border: 1px solid var(--color-border-base);
  border-radius: 6px;
  font-size: 0.85rem;
  background: var(--color-bg-container);
}
.schedule-cutoff-field {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}
.schedule-cutoff-select {
  min-width: 96px;
  padding: 4px 8px;
  border: 1px solid var(--color-border-base);
  border-radius: 6px;
  font-size: 0.85rem;
  background: var(--color-bg-container);
}
.schedule-preview {
  flex: 1 1 140px;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}
.shift-email-preview-panel {
  margin-top: var(--spacing-lg);
  padding: 14px 16px;
  border-radius: 8px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
}
.shift-email-preview-panel-title {
  margin: 0 0 8px;
  font-size: 0.95rem;
  font-weight: 600;
  color: #1d4ed8;
}
.shift-email-preview-intro {
  margin: 0 0 12px;
  font-size: 0.82rem;
  color: #475569;
}
.shift-email-preview-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.shift-email-preview-list li {
  padding: 10px 12px;
  font-size: 0.86rem;
  line-height: 1.55;
  color: #1e3a8a;
  background: rgba(255, 255, 255, 0.75);
  border-radius: 6px;
  border: 1px solid #dbeafe;
}
.llm-active-banner {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 0.88rem;
}
.llm-active-banner.is-deepseek {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1d4ed8;
}
.llm-active-banner.is-local {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
}
.llm-active-label {
  font-size: 0.78rem;
  padding: 1px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
}
.llm-active-url {
  font-size: 0.8rem;
  opacity: 0.8;
  word-break: break-all;
}
.llm-key-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.llm-key-input {
  flex: 1;
  min-width: 240px;
}
.llm-model-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.llm-model-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 10px 14px;
  border: 1px solid var(--color-border-base);
  border-radius: 8px;
  background: var(--color-bg-layout);
}
.llm-model-row.is-active {
  border-color: #22c55e;
  background: #f0fdf4;
}
.llm-model-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 200px;
}
.llm-model-line {
  display: flex;
  align-items: center;
  gap: 8px;
}
.llm-model-name {
  font-weight: 600;
  font-size: 0.92rem;
}
.llm-model-badge {
  font-size: 0.72rem;
  padding: 1px 8px;
  border-radius: 999px;
  background: #dcfce7;
  color: #166534;
}
.llm-model-meta {
  font-size: 0.8rem;
  color: var(--color-text-tertiary);
  word-break: break-all;
}
.llm-model-tag {
  font-size: 0.72rem;
  padding: 1px 8px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4338ca;
}
.llm-model-tag--key {
  background: #fef3c7;
  color: #92400e;
}
.llm-model-ops {
  display: flex;
  align-items: center;
  gap: 8px;
}
.llm-add-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  align-items: center;
}
.llm-add-wide {
  grid-column: 1 / -1;
}
.llm-add-btn {
  grid-column: 1 / -1;
  justify-self: end;
}
@media (max-width: 640px) {
  .llm-add-grid {
    grid-template-columns: 1fr;
  }
  .llm-add-btn {
    justify-self: stretch;
  }
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
