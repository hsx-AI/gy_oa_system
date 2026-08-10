<template>
  <div class="personal-inbox-page">
    <div class="container">
      <header class="page-head">
        <div>
          <h1>AI 红旗邮箱看板</h1>
          <p>仅整理您个人企业邮箱中标记为红旗（FLAGGED）的邮件</p>
        </div>
        <div class="actions">
          <button class="btn secondary" :disabled="loading" @click="load">刷新</button>
          <button class="btn secondary" :disabled="analyzing || !configured" @click="analyze">
            {{ analyzing ? '分析中…' : '立即分析' }}
          </button>
          <button class="btn primary" :disabled="syncing || !configured" @click="sync">
            {{ syncing ? '同步中…' : '同步红旗邮件' }}
          </button>
          <template v-if="selectionMode">
            <button class="btn secondary" :disabled="batchCompleting" @click="selectAll">全选</button>
            <button class="btn secondary" :disabled="batchCompleting || !selectedIds.length" @click="selectedIds = []">清空</button>
            <button class="btn danger" :disabled="batchCompleting || !selectedIds.length" @click="batchComplete">
              {{ batchCompleting ? '批量处理中…' : `批量完成 (${selectedIds.length})` }}
            </button>
            <button class="btn secondary" :disabled="batchCompleting" @click="exitSelection">取消多选</button>
          </template>
          <button v-else class="btn secondary" :disabled="!tasks.length" @click="selectionMode = true">多选完成</button>
        </div>
      </header>

      <div v-if="message" class="notice">{{ message }}</div>
      <section class="card config-card">
        <button type="button" class="config-head" @click="configOpen = !configOpen">
          <span>
            <strong>个人红旗邮箱配置</strong>
            <small>配置您自己的企业邮箱账号和 IMAP 授权码，仅用于本人的红旗邮件待办</small>
          </span>
          <span class="config-head-right">
            <em :class="configured ? 'configured' : 'unconfigured'">{{ configured ? '已配置' : '未配置' }}</em>
            <b>{{ configOpen ? '收起' : '展开' }}</b>
          </span>
        </button>
        <div v-if="configOpen" class="config-body">
          <div class="config-hint">IMAP：{{ imapServer }}:{{ imapPort }}（SSL）；只同步本人邮箱中已标红旗的邮件。授权码不是邮箱登录密码。</div>
          <label class="config-field">
            <span>企业邮箱地址</span>
            <input v-model.trim="configForm.email_address" type="email" autocomplete="email" placeholder="例如 name@hec-china.com">
          </label>
          <label class="config-field">
            <span>IMAP 授权码</span>
            <input v-model.trim="configForm.email_auth_code" type="password" autocomplete="new-password" :placeholder="configured ? `已配置 ${authCodeMasked}；不修改可留空` : '请输入 IMAP 授权码'">
          </label>
          <div class="config-buttons">
            <button class="btn primary" :disabled="configSaving" @click="saveConfig">{{ configSaving ? '保存中…' : '保存个人邮箱配置' }}</button>
          </div>
        </div>
      </section>
      <section v-if="!configured && !loading" class="empty card">
        <h2>个人邮箱尚未配置</h2>
        <p>请先配置个人企业邮箱地址和 IMAP 授权码。</p>
      </section>
      <section v-else class="card board">
        <div class="board-head">
          <div class="title-wrap">
            <span class="ai-icon flag-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M5 21V4"/><path d="M5 4h11l-2 4 2 4H5"/>
              </svg>
            </span>
            <h2>AI 红旗邮箱看板</h2>
            <span class="count">{{ tasks.length }}</span>
          </div>
        </div>
        <div v-if="loading" class="empty">加载中…</div>
        <div v-else-if="!tasks.length" class="empty">暂无红旗邮件待办任务</div>
        <div v-else class="task-grid">
          <article v-for="task in tasks" :key="task.id" class="task-card" :class="{ selected: selectedIds.includes(task.id) }" @click="selectionMode ? toggleSelected(task.id) : openDetail(task.id)">
            <label v-if="selectionMode" class="task-check" @click.stop>
              <input type="checkbox" :checked="selectedIds.includes(task.id)" :disabled="batchCompleting" @change="toggleSelected(task.id)">
              <span>选择</span>
            </label>
            <div class="task-top">
              <span v-if="editingId !== task.id" class="deadline">
                {{ task.taskDeadline || '未指定完成时间' }}
                <button class="deadline-edit" title="指定完成时间" @click.stop="startEdit(task)">编辑</button>
              </span>
              <span v-else class="deadline-editor" @click.stop>
                <input v-model="deadlineDraft" type="datetime-local" @keydown.enter.prevent="saveDeadline(task.id)" @keydown.esc.prevent="cancelEdit">
                <button :disabled="deadlineSavingId === task.id" @click="saveDeadline(task.id)">保存</button>
                <button @click="cancelEdit">取消</button>
              </span>
              <span class="from">{{ shortFrom(task.from) }}</span>
            </div>
            <h3>{{ task.taskSummary }}</h3>
            <p>{{ task.subject || '（无主题）' }}</p>
            <footer>
              <span>{{ task.emailDate || task.receivedAt }}</span>
              <button :disabled="selectionMode || completingId === task.id" @click.stop="complete(task.id)">
                {{ completingId === task.id ? '处理中…' : '标记完成' }}
              </button>
            </footer>
          </article>
        </div>
      </section>
      <div v-if="detailOpen" class="modal-overlay" @click.self="closeDetail">
        <div class="detail-modal">
          <header><h2>邮件详情</h2><button aria-label="关闭" @click="closeDetail">×</button></header>
          <div v-if="detailItem" class="detail-content">
            <div class="detail-meta">
              <p><strong>主题</strong><span>{{ detailItem.subject || '（无主题）' }}</span></p>
              <p><strong>发件人</strong><span>{{ detailItem.from || '—' }}</span></p>
              <p><strong>收件人</strong><span>{{ detailItem.to || '—' }}</span></p>
              <p><strong>抄送</strong><span>{{ detailItem.cc || '—' }}</span></p>
              <p><strong>发件时间</strong><span>{{ detailItem.emailDate || '—' }}</span></p>
            </div>
            <div class="body-tabs">
              <button :class="{ active: bodyMode === 'html' }" :disabled="!detailItem.bodyHtml" @click="bodyMode = 'html'">HTML</button>
              <button :class="{ active: bodyMode === 'text' }" @click="bodyMode = 'text'">纯文本</button>
            </div>
            <iframe v-if="bodyMode === 'html' && detailItem.bodyHtml" class="mail-frame" :srcdoc="detailItem.bodyHtml" sandbox=""></iframe>
            <pre v-else class="mail-text">{{ detailItem.bodyText || '（无正文）' }}</pre>
          </div>
          <div v-else class="empty">邮件详情加载中…</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getPersonalInboxConfig, updatePersonalInboxConfig, listPersonalInboxTasks, syncPersonalInbox, analyzePersonalInbox, completePersonalInboxTask, updatePersonalInboxTaskDeadline, getPersonalInboxEmailDetail } from '@/api/inboxEmail'

const router = useRouter()
const name = ref('')
const tasks = ref([])
const configured = ref(true)
const loading = ref(false)
const syncing = ref(false)
const analyzing = ref(false)
const completingId = ref(null)
const message = ref('')
const selectionMode = ref(false)
const selectedIds = ref([])
const batchCompleting = ref(false)
const editingId = ref(null)
const deadlineDraft = ref('')
const deadlineSavingId = ref(null)
const detailOpen = ref(false)
const detailItem = ref(null)
const bodyMode = ref('html')
const configOpen = ref(false)
const configSaving = ref(false)
const authCodeMasked = ref('')
const imapServer = ref('imap.qiye.163.com')
const imapPort = ref(993)
const configForm = ref({ email_address: '', email_auth_code: '' })

function shortFrom(value) {
  const text = (value || '').trim()
  return text.length > 28 ? `${text.slice(0, 28)}…` : (text || '未知发件人')
}

async function load() {
  loading.value = true
  try {
    const [cfg, result] = await Promise.all([
      getPersonalInboxConfig(name.value),
      listPersonalInboxTasks({ current_user: name.value, limit: 200 }),
    ])
    configured.value = !!cfg?.configured
    configForm.value.email_address = cfg?.emailAddress || ''
    configForm.value.email_auth_code = ''
    authCodeMasked.value = cfg?.authCodeMasked || ''
    imapServer.value = cfg?.imapServer || 'imap.qiye.163.com'
    imapPort.value = cfg?.imapPort || 993
    if (!configured.value) configOpen.value = true
    tasks.value = result?.items || []
  } catch (e) {
    message.value = e?.response?.data?.detail || e?.message || '加载失败'
  } finally { loading.value = false }
}

async function saveConfig() {
  if (!configForm.value.email_address) {
    message.value = '请填写个人企业邮箱地址'
    return
  }
  if (!configured.value && !configForm.value.email_auth_code) {
    message.value = '请填写 IMAP 授权码'
    return
  }
  configSaving.value = true
  try {
    const res = await updatePersonalInboxConfig({
      current_user: name.value,
      email_address: configForm.value.email_address,
      email_auth_code: configForm.value.email_auth_code,
    })
    message.value = res?.message || '个人邮箱配置已保存'
    configured.value = true
    await load()
  } catch (e) {
    message.value = e?.response?.data?.detail || e?.message || '个人邮箱配置保存失败'
  } finally { configSaving.value = false }
}

async function sync() {
  syncing.value = true
  try { const r = await syncPersonalInbox(name.value); message.value = r?.message || '同步完成'; await load() }
  catch (e) { message.value = e?.response?.data?.detail || e?.message || '同步失败' }
  finally { syncing.value = false }
}

async function analyze() {
  analyzing.value = true
  try { const r = await analyzePersonalInbox({ current_user: name.value, limit: 50 }); message.value = r?.message || '分析完成'; await load() }
  catch (e) { message.value = e?.response?.data?.detail || e?.message || '分析失败' }
  finally { analyzing.value = false }
}

async function complete(id) {
  completingId.value = id
  try { await completePersonalInboxTask({ current_user: name.value, id }); await load() }
  finally { completingId.value = null }
}

function toggleSelected(id) {
  selectedIds.value = selectedIds.value.includes(id)
    ? selectedIds.value.filter(item => item !== id)
    : [...selectedIds.value, id]
}
function selectAll() { selectedIds.value = tasks.value.map(task => task.id) }
function exitSelection() { selectionMode.value = false; selectedIds.value = [] }

async function batchComplete() {
  if (!selectedIds.value.length || batchCompleting.value) return
  batchCompleting.value = true
  const ids = [...selectedIds.value]
  let completed = 0
  try {
    for (const id of ids) {
      try {
        await completePersonalInboxTask({ current_user: name.value, id })
        completed += 1
      } catch (e) {
        message.value = `已完成 ${completed} 项；任务 ${id} 处理失败：${e?.response?.data?.detail || e?.message || '未知错误'}`
        break
      }
    }
    if (completed === ids.length) message.value = `已批量完成 ${completed} 项待办`
    exitSelection()
    await load()
  } finally { batchCompleting.value = false }
}

function toInput(value) { return (value || '').replace(' ', 'T').slice(0, 16) }
function startEdit(task) { editingId.value = task.id; deadlineDraft.value = toInput(task.taskDeadline) }
function cancelEdit() { editingId.value = null; deadlineDraft.value = '' }
async function saveDeadline(id) {
  deadlineSavingId.value = id
  try {
    await updatePersonalInboxTaskDeadline({ current_user: name.value, id, task_deadline: deadlineDraft.value.replace('T', ' ') })
    message.value = '完成时间已更新'
    cancelEdit()
    await load()
  } catch (e) { message.value = e?.response?.data?.detail || e?.message || '完成时间更新失败' }
  finally { deadlineSavingId.value = null }
}

async function openDetail(id) {
  detailOpen.value = true
  detailItem.value = null
  bodyMode.value = 'html'
  try {
    const res = await getPersonalInboxEmailDetail({ current_user: name.value, id })
    detailItem.value = res?.item || null
    bodyMode.value = detailItem.value?.bodyHtml ? 'html' : 'text'
  } catch (e) {
    message.value = e?.response?.data?.detail || e?.message || '邮件详情加载失败'
    closeDetail()
  }
}
function closeDetail() { detailOpen.value = false; detailItem.value = null }

onMounted(() => {
  try {
    const user = JSON.parse(localStorage.getItem('userInfo') || '{}')
    name.value = (user.name || user.userName || '').trim()
  } catch {}
  if (!name.value) router.replace('/login')
  else load()
})
</script>

<style scoped>
.personal-inbox-page{min-height:100vh;background:var(--color-bg-layout,#f5f7fb);padding:24px}.container{max-width:1200px;margin:auto}.page-head,.board-head,.title-wrap,.actions,.task-top,footer{display:flex;align-items:center}.page-head{justify-content:space-between;gap:20px;margin-bottom:20px}.page-head h1{margin:0;font-size:24px}.page-head p{margin:6px 0 0;color:#64748b}.actions{gap:10px}.btn{border:1px solid #dbe3ef;border-radius:8px;padding:9px 15px;cursor:pointer}.btn.primary{background:#2563eb;color:#fff;border-color:#2563eb}.btn.secondary{background:#fff;color:#334155}.btn:disabled{opacity:.55;cursor:not-allowed}.card{background:#fff;border:1px solid #e5eaf2;border-radius:14px;box-shadow:0 8px 24px rgba(15,23,42,.06)}.board{padding:20px}.board-head{justify-content:space-between;padding-bottom:16px;border-bottom:1px solid #eef2f7}.title-wrap{gap:10px}.title-wrap h2{margin:0;font-size:18px}.ai-icon{display:grid;place-items:center;width:34px;height:34px;border-radius:10px;color:#fff;background:linear-gradient(135deg,#6366f1,#06b6d4)}.ai-icon svg{width:20px}.count{min-width:24px;padding:2px 7px;border-radius:999px;background:#eef2ff;color:#4338ca;text-align:center;font-weight:700}.task-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px;margin-top:18px}.task-card{border:1px solid #e4e9f2;border-radius:12px;padding:15px;background:linear-gradient(145deg,#fff,#f8fafc);transition:.18s}.task-card:hover{transform:translateY(-2px);box-shadow:0 10px 22px rgba(15,23,42,.08);border-color:#c7d2fe}.task-top,footer{justify-content:space-between;gap:12px}.deadline{color:#b45309;font-size:13px;font-weight:600}.from,footer{color:#64748b;font-size:12px}.task-card h3{margin:15px 0 8px;font-size:16px;color:#172033}.task-card p{margin:0 0 16px;color:#64748b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.task-card footer button{border:0;border-radius:999px;padding:6px 12px;background:#eef2ff;color:#4338ca;cursor:pointer}.empty{text-align:center;padding:55px;color:#64748b}.notice{margin-bottom:14px;padding:10px 14px;border-radius:8px;background:#eff6ff;color:#1d4ed8}@media(max-width:700px){.personal-inbox-page{padding:12px}.page-head{align-items:flex-start;flex-direction:column}.actions{flex-wrap:wrap}.task-grid{grid-template-columns:1fr}}
.btn.danger{background:#dc2626;color:#fff;border-color:#dc2626}.actions{flex-wrap:wrap}.flag-icon{background:linear-gradient(135deg,#f97316,#dc2626)}.task-card{position:relative;cursor:pointer}.task-card.selected{border-color:#6366f1;background:#eef2ff}.task-check{display:flex;align-items:center;gap:6px;margin-bottom:10px;color:#4338ca;font-size:13px;font-weight:600;cursor:pointer}.deadline-edit{margin-left:6px;border:0;background:transparent;color:#2563eb;cursor:pointer}.deadline-editor{display:flex;align-items:center;gap:5px}.deadline-editor input{max-width:165px;border:1px solid #dbe3ef;border-radius:6px;padding:5px}.deadline-editor button{border:0;border-radius:5px;padding:5px 7px;cursor:pointer}.modal-overlay{position:fixed;inset:0;z-index:1000;display:grid;place-items:center;padding:24px;background:rgba(15,23,42,.58)}.detail-modal{width:min(1000px,96vw);height:min(760px,92vh);display:flex;flex-direction:column;background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 24px 70px rgba(0,0,0,.3)}.detail-modal>header{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid #e5e7eb}.detail-modal>header h2{margin:0;font-size:18px}.detail-modal>header button{border:0;background:transparent;font-size:28px;cursor:pointer}.detail-content{min-height:0;display:flex;flex:1;flex-direction:column;padding:16px 20px}.detail-meta{display:grid;grid-template-columns:1fr 1fr;gap:6px 20px}.detail-meta p{display:flex;gap:10px;margin:2px 0;font-size:13px}.detail-meta strong{min-width:58px;color:#64748b}.detail-meta span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.body-tabs{display:flex;gap:8px;margin:14px 0 8px}.body-tabs button{border:1px solid #dbe3ef;border-radius:6px;padding:6px 12px;background:#fff;cursor:pointer}.body-tabs button.active{background:#2563eb;color:#fff;border-color:#2563eb}.mail-frame,.mail-text{flex:1;min-height:0;width:100%;border:1px solid #e5e7eb;border-radius:8px;background:#fff}.mail-text{box-sizing:border-box;margin:0;padding:16px;overflow:auto;white-space:pre-wrap;font:14px/1.7 system-ui;color:#334155}@media(max-width:700px){.detail-meta{grid-template-columns:1fr}.modal-overlay{padding:8px}}
.config-card{margin-bottom:16px;overflow:hidden}.config-head{width:100%;display:flex;align-items:center;justify-content:space-between;gap:20px;padding:16px 20px;border:0;background:#fff;text-align:left;cursor:pointer}.config-head>span:first-child{display:flex;flex-direction:column;gap:4px}.config-head strong{font-size:16px;color:#172033}.config-head small{font-size:13px;color:#64748b}.config-head-right{display:flex;align-items:center;gap:12px;white-space:nowrap}.config-head em{padding:3px 9px;border-radius:999px;font-size:12px;font-style:normal}.config-head em.configured{background:#dcfce7;color:#166534}.config-head em.unconfigured{background:#fef3c7;color:#92400e}.config-head b{font-size:12px;color:#2563eb}.config-body{padding:0 20px 18px;border-top:1px solid #eef2f7}.config-hint{margin:14px 0;padding:10px 12px;border-radius:8px;background:#f8fafc;color:#64748b;font-size:13px}.config-field{display:flex;align-items:center;gap:14px;margin:12px 0}.config-field>span{width:110px;flex-shrink:0;color:#475569;font-size:14px}.config-field input{width:min(520px,100%);padding:9px 11px;border:1px solid #dbe3ef;border-radius:8px;font-size:14px}.config-buttons{padding-left:124px;margin-top:14px}@media(max-width:700px){.config-head{align-items:flex-start}.config-head small{display:none}.config-field{align-items:stretch;flex-direction:column;gap:5px}.config-field>span{width:auto}.config-buttons{padding-left:0}}
</style>
