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
import { getEmailConfig, updateEmailConfig, sendEmail } from '@/api/email'

const canAccess = ref(false)
const configured = ref(false)
const showConfig = ref(false)

const employees = ref([])
const recipients = ref([])
const recipientInput = ref('')
const showSuggestions = ref(false)

const emailForm = ref({ subject: '', content: '' })
const configForm = ref({ email_address: '', email_auth_code: '' })

const configSaving = ref(false)
const configMsg = ref('')
const configMsgType = ref('')
const sending = ref(false)
const sendMsg = ref('')
const sendMsgType = ref('')

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

function onSearchInput() {
  showSuggestions.value = true
}

function selectEmployee(emp) {
  const addr = emp.name
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
    const res = await sendEmail({
      current_user: getCurrentUser(),
      to: recipients.value,
      subject: emailForm.value.subject,
      content: emailForm.value.content,
      content_type: 'plain',
    })
    if (res && res.success) {
      sendMsg.value = res.message || '发送成功'
      sendMsgType.value = 'success'
      recipients.value = []
      emailForm.value.subject = ''
      emailForm.value.content = ''
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

onMounted(loadConfig)
</script>

<style scoped>
.email-sender-page {
  padding: 24px 0;
  min-height: 100vh;
  background: var(--color-bg-layout, #f0f2f5);
}
.container {
  max-width: 860px;
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

/* 配置区 */
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

/* 表单 */
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
.btn-sm { padding: 8px 16px; font-size: 13px; }

.config-msg, .send-msg {
  font-size: 13px;
  margin-left: 12px;
}
.config-msg.success, .send-msg.success { color: #059669; }
.config-msg.error, .send-msg.error { color: #dc2626; }

/* 收件人 */
.recipients-area {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px;
  transition: border-color 0.2s;
}
.recipients-area:focus-within { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }
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
  padding: 10px 14px;
  cursor: pointer;
  transition: background 0.15s;
}
.suggestion-item:hover { background: #f3f4f6; }
.emp-name { font-size: 14px; font-weight: 500; color: #1f2937; }
.emp-dept { font-size: 12px; color: #9ca3af; }

/* 发送 */
.compose-section .section-title { margin-bottom: 20px; }
.compose-form { display: flex; flex-direction: column; gap: 18px; }
.form-actions {
  display: flex;
  align-items: center;
  padding-top: 8px;
}
.btn-send { padding: 12px 28px; font-size: 15px; }
.btn-icon { width: 18px; height: 18px; }

@media (max-width: 640px) {
  .container { padding: 0 12px; }
  .card { padding: 16px; }
}
</style>
