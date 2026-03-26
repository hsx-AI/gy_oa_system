<template>
  <div class="email-sender-page">
    <div class="container">
      <header class="page-header">
        <div class="header-content">
          <div class="header-info">
            <h1 class="header-title">邮件发送</h1>
            <p class="header-subtitle">通过企业邮箱向公司员工发送邮件（仅系统管理员）</p>
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
            <h3 class="section-title">
              <svg class="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
              邮箱配置
            </h3>
            <span class="config-status" :class="configured ? 'ok' : 'warn'">
              {{ configured ? '已配置' : '未配置' }}
            </span>
            <svg class="toggle-icon" :class="{ open: showConfig }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
          </div>
          <div v-show="showConfig" class="config-body">
            <div class="config-form">
              <div class="form-row">
                <label>发件邮箱</label>
                <input v-model="configForm.email_address" type="text" placeholder="如 yourname@company.com" />
              </div>
              <div class="form-row">
                <label>授权码</label>
                <input v-model="configForm.email_auth_code" type="password" placeholder="SMTP 授权码（非邮箱密码）" />
              </div>
              <div class="form-row">
                <button class="btn btn-primary btn-sm" :disabled="configSaving" @click="saveConfig">
                  {{ configSaving ? '保存中…' : '保存配置' }}
                </button>
                <span v-if="configMsg" class="config-msg" :class="configMsgType">{{ configMsg }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 考勤异常提醒区 -->
        <div class="card reminder-section">
          <h3 class="section-title">
            <svg class="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            考勤异常提醒邮件
          </h3>
          <p class="section-desc">一键向所有考勤异常人员发送提醒邮件，附带考勤异常报表</p>

          <div class="reminder-config">
            <div class="reminder-row">
              <label>选择月份</label>
              <div class="month-picker">
                <select v-model="reminderYear" class="select-input">
                  <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option>
                </select>
                <select v-model="reminderMonth" class="select-input">
                  <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
                </select>
              </div>
            </div>
            <div class="reminder-row">
              <label>抄送</label>
              <div class="cc-area">
                <div class="recipient-tags" v-if="reminderCc.length">
                  <span v-for="(addr, i) in reminderCc" :key="'cc-'+i" class="tag tag-cc">
                    {{ addr }}
                    <button type="button" class="tag-remove" @click="reminderCc.splice(i, 1)">&times;</button>
                  </span>
                </div>
                <div class="recipient-input-wrap">
                  <input
                    v-model="reminderCcInput"
                    type="text"
                    placeholder="输入抄送邮箱地址或搜索员工，回车添加"
                    @keydown.enter.prevent="addReminderCc"
                    @input="reminderCcShowSuggestions = true"
                    @focus="reminderCcShowSuggestions = true"
                  />
                  <div v-if="reminderCcShowSuggestions && reminderCcFiltered.length" class="suggestion-dropdown">
                    <div
                      v-for="emp in reminderCcFiltered"
                      :key="'ccsug-'+emp.name"
                      class="suggestion-item"
                      @mousedown.prevent="selectReminderCc(emp)"
                    >
                      <span class="emp-name">{{ emp.name }}</span>
                      <span class="emp-email">{{ emp.email || '无邮箱' }}</span>
                      <span class="emp-dept">{{ emp.dept }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="reminder-row">
              <label class="checkbox-label">
                <input type="checkbox" v-model="reminderTestMode" />
                测试模式（不发给全部异常人员，仅发给下方测试收件人）
              </label>
            </div>
            <div v-show="reminderTestMode" class="reminder-row">
              <label>测试收件人</label>
              <input
                v-model="reminderTestRecipientsInput"
                type="text"
                class="text-input-full"
                placeholder="多个邮箱用英文逗号或中文逗号分隔，留空则默认 hsx@hec-china.com"
              />
            </div>
          </div>

          <div class="reminder-actions">
            <button class="btn btn-outline" :disabled="previewing" @click="handlePreview">
              <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              {{ previewing ? '加载中…' : '预览邮件' }}
            </button>
            <button class="btn btn-warning" :disabled="reminderSending || !previewData" @click="handleSendReminder">
              <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
              {{ reminderSending ? '发送中…' : '发送考勤提醒' }}
            </button>
            <span v-if="reminderMsg" class="send-msg" :class="reminderMsgType">{{ reminderMsg }}</span>
          </div>

          <!-- 预览区域 -->
          <div v-if="previewData" class="preview-card">
            <div class="preview-header">
              <h4>邮件预览</h4>
              <div class="preview-stats">
                <span class="stat-badge">{{ previewData.total_persons }} 人异常</span>
                <span class="stat-badge">{{ previewData.total_days }} 天次</span>
                <span class="stat-badge ok" v-if="previewData.has_email_count">{{ previewData.has_email_count }} 人有邮箱</span>
                <span class="stat-badge warn" v-if="previewData.no_email_count">{{ previewData.no_email_count }} 人无邮箱</span>
              </div>
            </div>
            <div class="preview-field">
              <strong>主题：</strong>{{ previewData.subject }}
            </div>
            <div class="preview-field">
              <strong>正文：</strong>
              <pre class="preview-body">{{ previewData.body }}</pre>
            </div>
            <div v-if="previewData.no_email_names && previewData.no_email_names.length" class="preview-field warn-box">
              <strong>⚠ 以下人员无企业邮箱，将无法收到邮件：</strong>
              <span>{{ previewData.no_email_names.join('、') }}</span>
            </div>
            <div class="preview-field">
              <strong>收件人列表：</strong>
              <div class="recipients-list">
                <div v-for="r in previewData.recipients" :key="r.name" class="recipient-item">
                  <span class="r-name">{{ r.name }}</span>
                  <span class="r-days">{{ r.days }}天</span>
                  <span class="r-email" :class="{ missing: !r.has_email }">{{ r.email || '无邮箱' }}</span>
                </div>
              </div>
            </div>
            <div class="preview-field">
              <strong>附件：</strong>考勤异常表_{{ reminderYear }}年{{ reminderMonth }}月.xlsx
            </div>
          </div>
        </div>

        <!-- 邮件编辑区 -->
        <div class="card compose-section">
          <h3 class="section-title">
            <svg class="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
            撰写邮件
          </h3>

          <div class="compose-form">
            <!-- 收件人 -->
            <div class="form-row">
              <label>收件人</label>
              <div class="recipients-area">
                <div class="recipient-tags">
                  <span v-for="(addr, i) in recipients" :key="i" class="tag">
                    {{ addr }}
                    <button type="button" class="tag-remove" @click="removeRecipient(i)">&times;</button>
                  </span>
                </div>
                <div class="recipient-input-wrap">
                  <input
                    v-model="recipientInput"
                    type="text"
                    placeholder="输入邮箱地址或搜索员工姓名，回车添加"
                    @keydown.enter.prevent="addRecipient"
                    @input="onSearchInput"
                    @focus="showSuggestions = true"
                  />
                  <div v-if="showSuggestions && filteredEmployees.length" class="suggestion-dropdown">
                    <div
                      v-for="emp in filteredEmployees"
                      :key="emp.name"
                      class="suggestion-item"
                      @mousedown.prevent="selectEmployee(emp)"
                    >
                      <span class="emp-name">{{ emp.name }}</span>
                      <span class="emp-email">{{ emp.email || '' }}</span>
                      <span class="emp-dept">{{ emp.dept }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 抄送 -->
            <div class="form-row">
              <label>抄送 (CC)</label>
              <div class="recipients-area">
                <div class="recipient-tags">
                  <span v-for="(addr, i) in ccRecipients" :key="'cc-'+i" class="tag tag-cc">
                    {{ addr }}
                    <button type="button" class="tag-remove" @click="ccRecipients.splice(i, 1)">&times;</button>
                  </span>
                </div>
                <div class="recipient-input-wrap">
                  <input
                    v-model="ccInput"
                    type="text"
                    placeholder="输入抄送邮箱或搜索员工，回车添加"
                    @keydown.enter.prevent="addCcRecipient"
                    @input="ccShowSuggestions = true"
                    @focus="ccShowSuggestions = true"
                  />
                  <div v-if="ccShowSuggestions && ccFilteredEmployees.length" class="suggestion-dropdown">
                    <div
                      v-for="emp in ccFilteredEmployees"
                      :key="'ccsug2-'+emp.name"
                      class="suggestion-item"
                      @mousedown.prevent="selectCcEmployee(emp)"
                    >
                      <span class="emp-name">{{ emp.name }}</span>
                      <span class="emp-email">{{ emp.email || '' }}</span>
                      <span class="emp-dept">{{ emp.dept }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 主题 -->
            <div class="form-row">
              <label>主题</label>
              <input v-model="emailForm.subject" type="text" placeholder="邮件主题" />
            </div>

            <!-- 正文 -->
            <div class="form-row">
              <label>正文</label>
              <textarea v-model="emailForm.content" rows="12" placeholder="请输入邮件正文内容…"></textarea>
            </div>

            <!-- 附件 -->
            <div class="form-row">
              <label>附件</label>
              <div class="attachment-area">
                <div v-if="attachmentFiles.length" class="attachment-list">
                  <div v-for="(f, i) in attachmentFiles" :key="'att-'+i" class="attachment-item">
                    <svg class="att-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>
                    <span class="att-name">{{ f.name }}</span>
                    <span class="att-size">{{ formatSize(f.size) }}</span>
                    <button type="button" class="tag-remove" @click="removeAttachment(i)">&times;</button>
                  </div>
                </div>
                <label class="btn btn-outline btn-sm attachment-btn">
                  <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>
                  添加附件
                  <input type="file" multiple @change="onFileSelect" style="display:none" />
                </label>
              </div>
            </div>

            <!-- 发送按钮 -->
            <div class="form-actions">
              <button class="btn btn-primary btn-send" :disabled="sending || !canSend" @click="handleSend">
                <svg v-if="!sending" class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                {{ sending ? '发送中…' : '发送邮件' }}
              </button>
              <span v-if="sendMsg" class="send-msg" :class="sendMsgType">{{ sendMsg }}</span>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getEmailConfig, updateEmailConfig, sendEmail, previewAttendanceReminder, sendAttendanceReminder } from '@/api/email'

const canAccess = ref(false)
const configured = ref(false)
const showConfig = ref(false)

const employees = ref([])
const recipients = ref([])
const recipientInput = ref('')
const showSuggestions = ref(false)

const ccRecipients = ref([])
const ccInput = ref('')
const ccShowSuggestions = ref(false)

const attachmentFiles = ref([])
const attachmentData = ref([])

const emailForm = ref({ subject: '', content: '' })
const configForm = ref({ email_address: '', email_auth_code: '' })

const configSaving = ref(false)
const configMsg = ref('')
const configMsgType = ref('')
const sending = ref(false)
const sendMsg = ref('')
const sendMsgType = ref('')

const now = new Date()
const reminderYear = ref(now.getFullYear())
const reminderMonth = ref(now.getMonth() + 1)
const yearOptions = computed(() => {
  const cur = now.getFullYear()
  return [cur - 1, cur, cur + 1]
})
const reminderCc = ref([])
const reminderCcInput = ref('')
const reminderCcShowSuggestions = ref(false)
const reminderTestMode = ref(true)
const reminderTestRecipientsInput = ref('hsx@hec-china.com')
const previewing = ref(false)
const previewData = ref(null)
const reminderSending = ref(false)
const reminderMsg = ref('')
const reminderMsgType = ref('')

function getCurrentUser() {
  try {
    const s = localStorage.getItem('userInfo')
    const u = s ? JSON.parse(s) : {}
    return (u.name || u.userName || '').trim()
  } catch { return '' }
}

const canSend = computed(() => recipients.value.length > 0 && emailForm.value.subject.trim() && emailForm.value.content.trim())

const filteredEmployees = computed(() => {
  const q = recipientInput.value.trim().toLowerCase()
  if (!q) return []
  return employees.value
    .filter(e => e.name.toLowerCase().includes(q) || (e.dept || '').toLowerCase().includes(q))
    .slice(0, 15)
})

const ccFilteredEmployees = computed(() => {
  const q = ccInput.value.trim().toLowerCase()
  if (!q) return []
  return employees.value
    .filter(e => e.name.toLowerCase().includes(q) || (e.dept || '').toLowerCase().includes(q) || (e.email || '').toLowerCase().includes(q))
    .slice(0, 15)
})

const reminderCcFiltered = computed(() => {
  const q = reminderCcInput.value.trim().toLowerCase()
  if (!q) return []
  return employees.value
    .filter(e => e.name.toLowerCase().includes(q) || (e.dept || '').toLowerCase().includes(q) || (e.email || '').toLowerCase().includes(q))
    .slice(0, 15)
})

function onSearchInput() {
  showSuggestions.value = true
}

function selectEmployee(emp) {
  const addr = emp.email || emp.name
  if (!recipients.value.includes(addr)) {
    recipients.value.push(addr)
  }
  recipientInput.value = ''
  showSuggestions.value = false
}

function addRecipient() {
  const val = recipientInput.value.trim()
  if (val && !recipients.value.includes(val)) {
    recipients.value.push(val)
  }
  recipientInput.value = ''
  showSuggestions.value = false
}

function removeRecipient(i) {
  recipients.value.splice(i, 1)
}

function selectCcEmployee(emp) {
  const addr = emp.email || emp.name
  if (!ccRecipients.value.includes(addr)) {
    ccRecipients.value.push(addr)
  }
  ccInput.value = ''
  ccShowSuggestions.value = false
}

function addCcRecipient() {
  const val = ccInput.value.trim()
  if (val && !ccRecipients.value.includes(val)) {
    ccRecipients.value.push(val)
  }
  ccInput.value = ''
  ccShowSuggestions.value = false
}

function selectReminderCc(emp) {
  const addr = emp.email || emp.name
  if (!reminderCc.value.includes(addr)) {
    reminderCc.value.push(addr)
  }
  reminderCcInput.value = ''
  reminderCcShowSuggestions.value = false
}

function addReminderCc() {
  const val = reminderCcInput.value.trim()
  if (val && !reminderCc.value.includes(val)) {
    reminderCc.value.push(val)
  }
  reminderCcInput.value = ''
  reminderCcShowSuggestions.value = false
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function onFileSelect(e) {
  const files = Array.from(e.target.files || [])
  for (const file of files) {
    if (file.size > 20 * 1024 * 1024) {
      alert(`文件 ${file.name} 超过 20MB 限制`)
      continue
    }
    attachmentFiles.value.push({ name: file.name, size: file.size })
    const reader = new FileReader()
    reader.onload = (ev) => {
      const b64 = ev.target.result.split(',')[1]
      attachmentData.value.push({ filename: file.name, content_base64: b64 })
    }
    reader.readAsDataURL(file)
  }
  e.target.value = ''
}

function removeAttachment(i) {
  attachmentFiles.value.splice(i, 1)
  attachmentData.value.splice(i, 1)
}

async function loadConfig() {
  const name = getCurrentUser()
  if (!name) return
  try {
    const res = await getEmailConfig(name)
    if (res && res.success) {
      canAccess.value = true
      configured.value = res.configured
      employees.value = res.employees || []
      if (res.emailAddress) configForm.value.email_address = res.emailAddress
    }
  } catch (e) {
    if (e?.response?.status === 403) {
      canAccess.value = false
    }
  }
}

async function saveConfig() {
  configSaving.value = true
  configMsg.value = ''
  try {
    const res = await updateEmailConfig({
      current_user: getCurrentUser(),
      email_address: configForm.value.email_address,
      email_auth_code: configForm.value.email_auth_code,
    })
    if (res && res.success) {
      configMsg.value = '保存成功'
      configMsgType.value = 'success'
      configured.value = true
      configForm.value.email_auth_code = ''
    } else {
      configMsg.value = res?.message || '保存失败'
      configMsgType.value = 'error'
    }
  } catch (e) {
    configMsg.value = e?.response?.data?.detail || '保存失败'
    configMsgType.value = 'error'
  } finally {
    configSaving.value = false
  }
}

async function handleSend() {
  sending.value = true
  sendMsg.value = ''
  try {
    const payload = {
      current_user: getCurrentUser(),
      to: recipients.value,
      cc: ccRecipients.value.length ? ccRecipients.value : undefined,
      subject: emailForm.value.subject,
      content: emailForm.value.content,
      content_type: 'plain',
    }
    if (attachmentData.value.length) {
      payload.attachments = attachmentData.value
    }
    const res = await sendEmail(payload)
    if (res && res.success) {
      sendMsg.value = res.message || '发送成功'
      sendMsgType.value = 'success'
      recipients.value = []
      ccRecipients.value = []
      emailForm.value.subject = ''
      emailForm.value.content = ''
      attachmentFiles.value = []
      attachmentData.value = []
    } else {
      sendMsg.value = res?.detail || res?.message || '发送失败'
      sendMsgType.value = 'error'
    }
  } catch (e) {
    sendMsg.value = e?.response?.data?.detail || '发送失败'
    sendMsgType.value = 'error'
  } finally {
    sending.value = false
  }
}

async function handlePreview() {
  previewing.value = true
  previewData.value = null
  reminderMsg.value = ''
  try {
    const res = await previewAttendanceReminder({
      current_user: getCurrentUser(),
      year: reminderYear.value,
      month: reminderMonth.value,
    })
    if (res && res.success) {
      if (!res.has_exceptions) {
        reminderMsg.value = res.message || '无考勤异常'
        reminderMsgType.value = 'success'
      } else {
        previewData.value = res
      }
    } else {
      reminderMsg.value = res?.detail || res?.message || '预览失败'
      reminderMsgType.value = 'error'
    }
  } catch (e) {
    reminderMsg.value = e?.response?.data?.detail || '预览失败'
    reminderMsgType.value = 'error'
  } finally {
    previewing.value = false
  }
}

async function handleSendReminder() {
  if (!previewData.value) return
  const testList = parseReminderTestEmails(reminderTestRecipientsInput.value)
  const testDisplay = testList.length ? testList.join('、') : 'hsx@hec-china.com（默认）'
  if (!confirm(`确认发送${reminderMonth.value}月考勤异常提醒邮件？${reminderTestMode.value ? `（测试模式，将发送到：${testDisplay}）` : `将发送给 ${previewData.value.has_email_count} 位收件人`}`)) return

  reminderSending.value = true
  reminderMsg.value = ''
  try {
    const payload = {
      current_user: getCurrentUser(),
      year: reminderYear.value,
      month: reminderMonth.value,
      cc: reminderCc.value.length ? reminderCc.value : undefined,
      test_mode: reminderTestMode.value,
    }
    if (reminderTestMode.value && testList.length) {
      payload.test_recipients = testList
    }
    const res = await sendAttendanceReminder(payload)
    if (res && res.success) {
      reminderMsg.value = res.message || '发送成功'
      reminderMsgType.value = 'success'
    } else {
      reminderMsg.value = res?.detail || res?.message || '发送失败'
      reminderMsgType.value = 'error'
    }
  } catch (e) {
    reminderMsg.value = e?.response?.data?.detail || '发送失败'
    reminderMsgType.value = 'error'
  } finally {
    reminderSending.value = false
  }
}

function parseReminderTestEmails(s) {
  if (!s || !String(s).trim()) return []
  return String(s)
    .split(/[,，;；\n]+/)
    .map((x) => x.trim())
    .filter(Boolean)
}

onMounted(loadConfig)
</script>

<style scoped>
.email-sender-page {
  padding: 24px 0;
  min-height: 100vh;
  background: var(--color-bg-layout, #f0f2f5);
}
.container {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 24px;
}

.page-header { margin-bottom: 24px; }
.header-content { display: flex; justify-content: space-between; align-items: center; }
.header-title { font-size: 24px; font-weight: 700; color: #1f2937; margin: 0 0 4px; }
.header-subtitle { font-size: 14px; color: #6b7280; margin: 0; }

.card {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.no-permission { text-align: center; padding: 60px 24px; color: #6b7280; }

.section-header {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
  gap: 12px;
}
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
  flex: 1;
}
.section-icon { width: 20px; height: 20px; color: #6366f1; flex-shrink: 0; }
.section-desc { font-size: 13px; color: #6b7280; margin: 8px 0 16px; }
.config-status {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 99px;
  font-weight: 500;
}
.config-status.ok { background: #ecfdf5; color: #059669; }
.config-status.warn { background: #fef3c7; color: #d97706; }
.toggle-icon {
  width: 20px; height: 20px; color: #9ca3af;
  transition: transform 0.2s;
}
.toggle-icon.open { transform: rotate(180deg); }
.config-body { margin-top: 20px; border-top: 1px solid #f3f4f6; padding-top: 20px; }
.config-form { display: flex; flex-direction: column; gap: 14px; max-width: 500px; }

.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-row label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}
.form-row input[type="text"],
.form-row input[type="password"] {
  padding: 10px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}
.form-row input:focus { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }
.form-row textarea {
  padding: 12px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  outline: none;
  resize: vertical;
  min-height: 200px;
  transition: border-color 0.2s;
}
.form-row textarea:focus { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-primary { background: #6366f1; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #4f46e5; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline { background: #fff; color: #374151; border: 1px solid #d1d5db; }
.btn-outline:hover:not(:disabled) { background: #f9fafb; border-color: #9ca3af; }
.btn-warning { background: #f59e0b; color: #fff; }
.btn-warning:hover:not(:disabled) { background: #d97706; }
.btn-warning:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-sm { padding: 8px 16px; font-size: 13px; }

.config-msg, .send-msg {
  font-size: 13px;
  margin-left: 12px;
}
.config-msg.success, .send-msg.success { color: #059669; }
.config-msg.error, .send-msg.error { color: #dc2626; }

.recipients-area, .cc-area {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px;
  transition: border-color 0.2s;
}
.recipients-area:focus-within, .cc-area:focus-within { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }
.recipient-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 4px;
}
.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #eef2ff;
  color: #4338ca;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
}
.tag-cc {
  background: #fef3c7;
  color: #92400e;
}
.tag-remove {
  background: none;
  border: none;
  color: #6366f1;
  font-size: 16px;
  cursor: pointer;
  padding: 0 2px;
  line-height: 1;
}
.tag-remove:hover { color: #dc2626; }
.recipient-input-wrap { position: relative; }
.recipient-input-wrap input {
  width: 100%;
  border: none;
  outline: none;
  padding: 6px 4px;
  font-size: 14px;
  background: transparent;
}
.suggestion-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  max-height: 260px;
  overflow-y: auto;
  z-index: 100;
}
.suggestion-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  cursor: pointer;
  transition: background 0.15s;
  gap: 8px;
}
.suggestion-item:hover { background: #f3f4f6; }
.emp-name { font-size: 14px; font-weight: 500; color: #1f2937; min-width: 60px; }
.emp-email { font-size: 12px; color: #6366f1; flex: 1; }
.emp-dept { font-size: 12px; color: #9ca3af; }

.compose-section .section-title { margin-bottom: 20px; }
.compose-form { display: flex; flex-direction: column; gap: 18px; }
.form-actions {
  display: flex;
  align-items: center;
  padding-top: 8px;
}
.btn-send { padding: 12px 28px; font-size: 15px; }
.btn-icon { width: 18px; height: 18px; }

/* 考勤提醒区 */
.reminder-section .section-title { margin-bottom: 4px; }
.reminder-config { display: flex; flex-direction: column; gap: 14px; margin-bottom: 16px; }
.reminder-row { display: flex; flex-direction: column; gap: 6px; }
.reminder-row label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  display: flex;
  align-items: center;
  gap: 6px;
}
.reminder-row input[type="checkbox"] { accent-color: #6366f1; }
.reminder-row .checkbox-label { font-weight: 500; cursor: pointer; }
.reminder-row .text-input-full {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
}
.reminder-row .text-input-full:focus { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }
.month-picker { display: flex; gap: 8px; }
.select-input {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  background: #fff;
  cursor: pointer;
}
.select-input:focus { border-color: #6366f1; }
.reminder-actions { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }

/* 预览卡片 */
.preview-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 20px;
  margin-top: 8px;
}
.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 8px;
}
.preview-header h4 { margin: 0; font-size: 15px; color: #1f2937; }
.preview-stats { display: flex; gap: 6px; flex-wrap: wrap; }
.stat-badge {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 99px;
  background: #eef2ff;
  color: #4338ca;
  font-weight: 500;
}
.stat-badge.ok { background: #ecfdf5; color: #059669; }
.stat-badge.warn { background: #fef3c7; color: #d97706; }
.preview-field {
  margin-bottom: 12px;
  font-size: 14px;
  color: #374151;
}
.preview-field strong { color: #1f2937; }
.preview-body {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  font-family: inherit;
  color: #374151;
}
.warn-box {
  background: #fef3c7;
  border: 1px solid #fcd34d;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 13px;
  color: #92400e;
}
.recipients-list {
  margin-top: 6px;
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}
.recipient-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 14px;
  border-bottom: 1px solid #f3f4f6;
  font-size: 13px;
}
.recipient-item:last-child { border-bottom: none; }
.r-name { font-weight: 500; color: #1f2937; min-width: 60px; }
.r-days { color: #dc2626; font-weight: 600; min-width: 50px; }
.r-email { color: #6366f1; flex: 1; }
.r-email.missing { color: #dc2626; font-style: italic; }

/* 附件 */
.attachment-area { display: flex; flex-direction: column; gap: 8px; }
.attachment-list { display: flex; flex-direction: column; gap: 4px; }
.attachment-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 13px;
}
.att-icon { width: 16px; height: 16px; color: #6366f1; flex-shrink: 0; }
.att-name { font-weight: 500; color: #1f2937; flex: 1; }
.att-size { color: #9ca3af; font-size: 12px; }
.attachment-btn { cursor: pointer; align-self: flex-start; }

@media (max-width: 640px) {
  .container { padding: 0 12px; }
  .card { padding: 16px; }
}
</style>
