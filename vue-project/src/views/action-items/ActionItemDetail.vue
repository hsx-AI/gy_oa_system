<template>
  <div class="detail-page">
    <button class="back" @click="$router.back()">← 返回</button>
    <header class="detail-head">
      <div>
        <div class="badges"><span class="status" :data-status="item.current_status">{{ item.current_status }}</span><span class="priority" :data-priority="item.priority || '中'">{{ item.priority || '中' }}优先级</span><span v-for="tag in item.risk_tags" :key="tag" class="risk">{{ tag }}</span></div>
        <h1>{{ item.title || '行动项详情' }}</h1>
        <p>{{ item.action_number || '未编号' }} · 来源：{{ item.meeting?.meeting_name || item.minutes_number || '人工新增' }}</p>
      </div>
      <div class="actions">
        <div v-if="canReceive || canAssign" class="receive-choice">
          <span>请选择一种办理方式</span>
          <div>
            <button v-if="canReceive" class="btn function-self-receive" @click="confirmReceive">由本人接收</button>
            <button v-if="canAssign" class="btn function-assign" @click="openAssign">分配科室成员完成</button>
          </div>
        </div>
        <button v-if="canAdminAdjust" class="btn function-edit" @click="openAdjust">调整</button>
        <button v-if="canAdminCancel" class="btn danger" @click="cancelPublished">删除</button>
        <button v-if="canExecute" class="btn function-progress" @click="openProgress">填报进展</button>
        <button v-if="canExecute" class="btn function-complete" @click="openCompletion">申请完工</button>
        <button v-if="canChange" class="btn function-change" @click="requestChange">申请变更</button>
        <button v-if="permissions.supervise" class="btn warning" @click="remind">催办</button>
      </div>
    </header>

    <section class="overview-grid">
      <article class="panel summary">
        <h2>基本信息</h2>
        <dl>
          <div><dt>责任科室</dt><dd>{{ item.responsible_department_ids?.join('、') || '待确认' }}</dd></div>
          <div><dt>责任人</dt><dd>{{ item.responsible_person_ids?.join('、') || '待确认' }}</dd></div>
          <div><dt>主管领导</dt><dd>{{ item.supervisor_id || '待确认' }}</dd></div>
          <div><dt>要求完成</dt><dd>{{ item.required_completion_date || '待确认' }}</dd></div>
          <div><dt>当前进度</dt><dd>{{ item.current_progress || 0 }}%</dd></div>
          <div><dt>发布时间</dt><dd>{{ item.published_at || '未发布' }}</dd></div>
        </dl>
        <div class="progress"><i :style="{ width: (item.current_progress || 0) + '%' }"></i></div>
        <h3>行动项内容</h3><p class="content">{{ item.content }}</p>
        <h3>纪要原文依据</h3><blockquote>{{ item.source_quote || '—' }}</blockquote>
        <div v-if="item.collaborating_departments?.length"><h3>协同科室</h3><p>{{ item.collaborating_departments.join('、') }}</p></div>
        <div v-if="item.collaborating_people?.length"><h3>协同责任人</h3><p>{{ item.collaborating_people.join('、') }}</p></div>
      </article>
      <article class="panel pending-panel">
        <h2>待处理事项</h2>
        <div v-for="app in pendingCompletions" :key="'c'+app.id" class="pending-card">
          <strong>{{ app.responsible_department || '责任科室' }}完工申请</strong><span>{{ app.applicant }} · {{ app.applied_at }}</span><p>{{ app.completion_description }}</p>
          <div v-if="canApprove" class="approval-actions"><button @click="approveCompletion(app, '通过')">通过</button><button class="danger" @click="approveCompletion(app, '退回整改')">退回整改</button><button @click="approveCompletion(app, '要求补充材料')">补充材料</button></div>
        </div>
        <div v-for="change in pendingChanges" :key="'g'+change.id" class="pending-card">
          <strong>{{ change.change_type }}申请</strong><span>{{ change.applicant }} · {{ change.applied_at }}</span><p>{{ change.change_reason }}</p>
          <div v-if="canApprove" class="approval-actions"><button @click="approveChange(change, '通过')">通过</button><button class="danger" @click="approveChange(change, '退回整改')">退回</button></div>
        </div>
        <div v-if="!pendingCompletions.length && !pendingChanges.length" class="empty small">暂无待处理申请</div>
      </article>
    </section>

    <section class="panel department-execution-panel">
      <div class="section-head">
        <h2>各责任科室执行情况</h2>
        <span>总进度按责任科室等权平均计算</span>
      </div>
      <div class="department-execution-grid">
        <article
          v-for="execution in departmentExecutions"
          :key="execution.department"
          class="department-execution-card"
          :data-status="execution.execution_status"
        >
          <div class="department-execution-head">
            <strong>{{ execution.department }}</strong>
            <span class="status" :data-status="execution.execution_status">{{ execution.execution_status }}</span>
          </div>
          <p>负责人：{{ execution.responsible_person || '待分配' }}</p>
          <div class="department-progress"><i :style="{ width: `${execution.progress_percent || 0}%` }"></i></div>
          <div class="department-execution-meta">
            <span>科室进度 {{ execution.progress_percent || 0 }}%</span>
            <span v-if="execution.completed_at">完成于 {{ execution.completed_at }}</span>
            <span v-else-if="execution.received_at">接收于 {{ execution.received_at }}</span>
          </div>
        </article>
        <div v-if="!departmentExecutions.length" class="empty small">暂无科室执行数据</div>
      </div>
    </section>

    <section class="panel timeline-panel">
      <div class="section-head"><h2>全过程时间轴</h2><span>发布、接收、进展、催办、变更、完工与审批均保留历史</span></div>
      <div class="timeline">
        <article v-for="event in events" :key="event.id" class="event">
          <i></i><div class="event-head"><strong>{{ event.event_type }}</strong><span>{{ event.operator }} · {{ event.created_at }}</span></div>
          <p>{{ event.event_content }}</p>
        </article>
        <div v-if="!events.length" class="empty">暂无历史记录</div>
      </div>
    </section>

    <section v-if="attachments.length" class="panel">
      <h2>佐证与附件</h2>
      <div class="attachments"><a v-for="file in attachments" :key="file.id" :href="attachmentUrl(file.id)" target="_blank">{{ file.original_name }} <small>{{ file.uploader }} · {{ file.uploaded_at }}</small></a></div>
    </section>

    <div v-if="modal === 'progress'" class="modal-mask" @click.self="modal = ''">
      <form class="modal" @submit.prevent="submitProgress">
        <div class="modal-head"><h2>进展填报</h2><button type="button" @click="modal=''">×</button></div>
        <label>进度百分比<input v-model.number="progressForm.progress_percent" type="number" min="0" max="100" required></label>
        <label>本期进展<textarea v-model.trim="progressForm.current_progress" rows="4" required></textarea></label>
        <label>已完成工作<textarea v-model.trim="progressForm.completed_work" rows="2"></textarea></label>
        <label>存在问题<textarea v-model.trim="progressForm.existing_problems" rows="2"></textarea></label>
        <label>下一步计划<textarea v-model.trim="progressForm.next_plan" rows="2"></textarea></label>
        <div class="form-row"><label>预计完成时间<input v-model="progressForm.expected_completion_date" type="date"></label><label class="check"><input v-model="progressForm.delay_risk" type="checkbox"> 存在延期风险</label></div>
        <label>附件<input type="file" multiple @change="progressFiles = [...$event.target.files]"></label>
        <div class="modal-actions"><button type="button" class="btn" @click="modal=''">取消</button><button class="btn primary" :disabled="saving">{{ saving ? '提交中…' : '提交进展' }}</button></div>
      </form>
    </div>

    <div v-if="modal === 'completion'" class="modal-mask" @click.self="modal = ''">
      <form class="modal" @submit.prevent="submitCompletion">
        <div class="modal-head"><h2>完工申请</h2><button type="button" @click="modal=''">×</button></div>
        <label>完成情况<textarea v-model.trim="completionForm.completion_description" rows="4" required></textarea></label>
        <label>实际完成时间<input v-model="completionForm.actual_completion_date" type="date" required></label>
        <label>完成成果<textarea v-model.trim="completionForm.completion_results" rows="3"></textarea></label>
        <label>遗留问题<textarea v-model.trim="completionForm.remaining_issues" rows="2"></textarea></label>
        <label>佐证材料<input type="file" multiple @change="completionFiles = [...$event.target.files]"></label>
        <div class="modal-actions"><button type="button" class="btn" @click="modal=''">取消</button><button class="btn primary" :disabled="saving">{{ saving ? '提交中…' : '提交完工申请' }}</button></div>
      </form>
    </div>

    <div v-if="modal === 'assign'" class="modal-mask" @click.self="modal = ''">
      <form class="modal compact" @submit.prevent="submitAssign">
        <div class="modal-head"><h2>分配科室成员完成</h2><button type="button" @click="modal=''">×</button></div>
        <label>
          可分配科室
          <input :value="assignmentScope.departments?.join('、') || '无可分配科室'" disabled>
          <small v-if="assignmentScope.departments?.length === 1" class="field-hint">
            科室主任、副主任仅可分配本科室在职人员
          </small>
        </label>
        <label>责任人
          <select v-model="assignmentPerson" required>
            <option value="">请选择</option>
            <option v-for="person in departmentPeople" :key="person.name" :value="person.name">
              {{ person.department }} · {{ person.name }}（{{ person.job || '员工' }}）
            </option>
          </select>
          <small v-if="user.department_leader" class="field-hint">
            部门领导可选择各责任科室的主任、主任责或副主任承接任务
          </small>
        </label>
        <div class="modal-actions"><button type="button" class="btn" @click="modal=''">取消</button><button class="btn primary" :disabled="saving">{{ saving ? '保存中…' : '确认分配给该成员' }}</button></div>
      </form>
    </div>

    <div v-if="modal === 'adjust'" class="modal-mask" @click.self="modal = ''">
      <form class="modal" @submit.prevent="submitAdjust">
        <div class="modal-head"><h2>调整行动项</h2><button type="button" @click="modal=''">×</button></div>
        <label>标题<input v-model.trim="adjustForm.title" required></label>
        <label>内容<textarea v-model.trim="adjustForm.content" rows="4" required></textarea></label>
        <label>责任科室
          <select v-model="adjustForm.responsible_department_id" required>
            <option value="">请选择</option>
            <option v-for="dept in directory.departments || []" :key="dept" :value="dept">{{ dept }}</option>
          </select>
        </label>
        <label>责任人
          <select v-model="adjustForm.responsible_person_id" required>
            <option value="">请选择</option>
            <option v-for="person in adjustPeople" :key="person.name" :value="person.name">{{ person.name }}（{{ person.job || '员工' }}）</option>
          </select>
        </label>
        <label>主管领导
          <select v-model="adjustForm.supervisor_id">
            <option value="">请选择</option>
            <option v-for="person in directory.supervisors || []" :key="person.name || person" :value="person.name || person">{{ person.name || person }}</option>
          </select>
        </label>
        <div class="form-row">
          <label>要求完成时间<input v-model="adjustForm.required_completion_date" type="date"></label>
          <label>优先级
            <select v-model="adjustForm.priority">
              <option>高</option><option>中</option><option>低</option>
            </select>
          </label>
        </div>
        <div class="modal-actions"><button type="button" class="btn" @click="modal=''">取消</button><button class="btn primary" :disabled="saving">{{ saving ? '保存中…' : '保存调整' }}</button></div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  actionAttachmentUrl, addActionProgress, applyActionChange, applyActionCompletion,
  approveActionChange, approveActionCompletion, assignActionResponsible, cancelPublishedAction,
  getActionDetail, getActionDirectory, receiveAction, remindAction, updateAction,
} from '@/api/actionItems'

const route = useRoute(); const router = useRouter(); const actionId = Number(route.params.id)
const currentUser = (() => { try { const u = JSON.parse(localStorage.getItem('userInfo') || '{}'); return (u.name || u.userName || '').trim() } catch { return '' } })()
const item = reactive({ risk_tags: [], responsible_department_ids: [], responsible_person_ids: [], collaborating_departments: [] })
const permissions = reactive({}); const user = reactive({})
const directory = reactive({ people: [], departments: [], supervisors: [] })
const assignmentScope = reactive({ departments: [], people: [] })
const events = ref([]); const completions = ref([]); const changes = ref([]); const attachments = ref([])
const departmentExecutions = ref([])
const modal = ref(''); const saving = ref(false); const progressFiles = ref([]); const completionFiles = ref([])
const assignmentPerson = ref('')
const adjustForm = reactive({
  title: '', content: '', responsible_department_id: '', responsible_person_id: '',
  supervisor_id: '', required_completion_date: '', priority: '中',
})
const progressForm = reactive({ progress_percent: 0, current_progress: '', completed_work: '', existing_problems: '', next_plan: '', expected_completion_date: '', delay_risk: false })
const completionForm = reactive({ completion_description: '', actual_completion_date: new Date().toISOString().slice(0, 10), completion_results: '', remaining_issues: '' })

function isDirectorJob(jb) {
  const j = (jb || '').trim()
  if (!j) return false
  if (j.includes('副主任') || j.startsWith('副主任')) return true
  if (j.includes('主任责')) return true
  return j === '主任' || j.startsWith('主任')
}

const myDepartmentExecution = computed(() => departmentExecutions.value.find(
  execution => execution.department === user.dept,
))
const canReceive = computed(() => {
  if (myDepartmentExecution.value?.execution_status !== '待接收') return false
  if (myDepartmentExecution.value?.responsible_person === currentUser) return true
  return !!(user.dept && item.responsible_department_ids?.includes(user.dept) && isDirectorJob(user.jb))
})
const canAssign = computed(() => item.current_status === '待接收'
  && assignmentScope.departments?.length
  && assignmentScope.people?.length)
const canAdminAdjust = computed(() => user.minutes_admin && !['草稿', '待发布', '已取消'].includes(item.current_status))
const canAdminCancel = computed(() => user.minutes_admin && !['草稿', '待发布', '已取消'].includes(item.current_status))
const departmentPeople = computed(() => assignmentScope.people || [])
const adjustPeople = computed(() => directory.people.filter(p => !adjustForm.responsible_department_id || p.department === adjustForm.responsible_department_id))
const canExecute = computed(() => (
  ['进行中', '退回整改'].includes(myDepartmentExecution.value?.execution_status)
  && myDepartmentExecution.value?.responsible_person === currentUser
))
const canChange = computed(() => !['草稿', '待发布', '已完成', '已取消'].includes(item.current_status) && (item.responsible_person_ids?.includes(currentUser) || user.minutes_admin || user.dept_manager || user.department_leader))
const canApprove = computed(() => item.supervisor_id === currentUser || user.admin || user.department_leader)
const pendingCompletions = computed(() => completions.value.filter(x => x.approval_status === '待审批'))
const pendingChanges = computed(() => changes.value.filter(x => x.approval_status === '待审批'))
watch(() => adjustForm.responsible_department_id, (dept) => {
  if (!dept) return
  const person = directory.people.find(p => p.name === adjustForm.responsible_person_id)
  if (person && person.department !== dept) adjustForm.responsible_person_id = ''
})
async function load() {
  const res = await getActionDetail(actionId, currentUser)
  Object.assign(item, res?.item || {}); Object.assign(permissions, res?.permissions || {}); Object.assign(user, res?.user || {})
  Object.assign(assignmentScope, res?.assignmentScope || { departments: [], people: [] })
  departmentExecutions.value = res?.departmentExecutions || []
  events.value = res?.events || []; completions.value = res?.completions || []; changes.value = res?.changes || []; attachments.value = res?.attachments || []
  progressForm.progress_percent = myDepartmentExecution.value?.progress_percent || 0
}
async function bootstrap() {
  const [detail, people] = await Promise.all([
    getActionDetail(actionId, currentUser), getActionDirectory(currentUser),
  ])
  Object.assign(item, detail?.item || {}); Object.assign(permissions, detail?.permissions || {}); Object.assign(user, detail?.user || {})
  Object.assign(assignmentScope, detail?.assignmentScope || { departments: [], people: [] })
  departmentExecutions.value = detail?.departmentExecutions || []
  events.value = detail?.events || []; completions.value = detail?.completions || []; changes.value = detail?.changes || []; attachments.value = detail?.attachments || []
  Object.assign(directory, people || {})
  progressForm.progress_percent = myDepartmentExecution.value?.progress_percent || 0
  if (route.query.edit === '1' && user.minutes_admin) openAdjust()
}
async function confirmReceive() {
  if (!confirm('确认由本人代表本科室接收并负责完成该行动项？\n接收后本科室进入“进行中”，本科室不能再使用初次分配功能。')) return
  try { await receiveAction(actionId, { current_user: currentUser }); await load() } catch (e) { fail(e) }
}
function openAssign() {
  const current = item.responsible_person_id || ''
  assignmentPerson.value = departmentPeople.value.some(person => person.name === current) ? current : ''
  modal.value = 'assign'
}
function openAdjust() {
  adjustForm.title = item.title || ''
  adjustForm.content = item.content || ''
  adjustForm.responsible_department_id = item.responsible_department_ids?.[0] || item.responsible_department_id || ''
  adjustForm.responsible_person_id = item.responsible_person_ids?.[0] || item.responsible_person_id || ''
  adjustForm.supervisor_id = item.supervisor_id || ''
  adjustForm.required_completion_date = item.required_completion_date || ''
  adjustForm.priority = item.priority || '中'
  modal.value = 'adjust'
}
async function submitAdjust() {
  saving.value = true
  try {
    await updateAction(actionId, {
      current_user: currentUser,
      title: adjustForm.title,
      content: adjustForm.content,
      responsible_department_id: adjustForm.responsible_department_id,
      responsible_person_id: adjustForm.responsible_person_id,
      responsible_department_ids: [adjustForm.responsible_department_id].filter(Boolean),
      responsible_person_ids: [adjustForm.responsible_person_id].filter(Boolean),
      supervisor_id: adjustForm.supervisor_id || null,
      required_completion_date: adjustForm.required_completion_date || null,
      priority: adjustForm.priority,
    })
    modal.value = ''
    await load()
  } catch (e) { fail(e) } finally { saving.value = false }
}
async function cancelPublished() {
  const reason = prompt(`删除「${item.title}」并保留历史记录。\n可填写删除原因：`, '台账管理删除')
  if (reason === null) return
  try {
    await cancelPublishedAction(actionId, { current_user: currentUser, reason })
    alert('已删除（取消）')
    router.push('/action-items/ledger')
  } catch (e) { fail(e) }
}
async function submitAssign() {
  saving.value = true
  try {
    await assignActionResponsible(actionId, { current_user: currentUser, responsible_person_id: assignmentPerson.value })
    modal.value = ''; await load()
  } catch (e) { fail(e) } finally { saving.value = false }
}
function openProgress() { modal.value = 'progress' }
function openCompletion() { modal.value = 'completion' }
function toFormData(data, files) { const fd = new FormData(); Object.entries(data).forEach(([k,v]) => fd.append(k, typeof v === 'boolean' ? String(v) : (v ?? ''))); files.forEach(f => fd.append('files', f)); return fd }
async function submitProgress() {
  saving.value = true
  try { await addActionProgress(actionId, toFormData({ current_user: currentUser, ...progressForm }, progressFiles.value)); modal.value=''; progressFiles.value=[]; await load() } catch (e) { fail(e) } finally { saving.value=false }
}
async function submitCompletion() {
  saving.value = true
  try { await applyActionCompletion(actionId, toFormData({ current_user: currentUser, ...completionForm }, completionFiles.value)); modal.value=''; completionFiles.value=[]; await load() } catch (e) { fail(e) } finally { saving.value=false }
}
async function approveCompletion(app, result) {
  const opinion = prompt(`请输入“${result}”审批意见`, result === '通过' ? '同意完工' : '')
  if (opinion === null) return
  try { await approveActionCompletion(app.id, { current_user: currentUser, result, opinion }); await load() } catch (e) { fail(e) }
}
async function approveChange(change, result) {
  const opinion = prompt(`请输入“${result}”审批意见`, result === '通过' ? '同意' : '')
  if (opinion === null) return
  try { await approveActionChange(change.id, { current_user: currentUser, result, opinion }); await load() } catch (e) { fail(e) }
}
async function requestChange() {
  const type = prompt('变更类型：延期 / 负责人变更 / 责任科室变更 / 内容调整 / 取消', '延期')
  if (!type) return
  const reason = prompt('请输入变更原因', '')
  if (!reason) return
  const after = {}
  if (type === '延期') after.required_completion_date = prompt('新的完成日期（YYYY-MM-DD）', item.required_completion_date || '')
  if (type === '负责人变更') after.responsible_person_id = prompt('新的责任人姓名', item.responsible_person_id || '')
  if (type === '责任科室变更') after.responsible_department_id = prompt('新的责任科室', item.responsible_department_id || '')
  if (type === '内容调整') { after.title = prompt('新标题', item.title) || item.title; after.content = prompt('新内容', item.content) || item.content }
  try { await applyActionChange(actionId, { current_user: currentUser, change_type: type, after_content: after, reason }); await load() } catch (e) { fail(e) }
}
async function remind() {
  const note = prompt('请输入催办说明', '请及时更新行动项进展')
  if (!note) return
  try {
    const result = await remindAction(actionId, currentUser, note)
    alert(result?.message || (result?.sent === false ? '未识别到有效提醒对象，本次催办已跳过' : '催办已发送'))
    await load()
  } catch (e) { fail(e) }
}
function attachmentUrl(id) { return actionAttachmentUrl(id, currentUser) }
function fail(e) { alert(e?.response?.data?.detail || e?.message || '操作失败') }
onMounted(bootstrap)
</script>

<style scoped>
.detail-page{padding-bottom:32px}.back{border:0;background:none;color:#2563eb;padding:0;cursor:pointer}.detail-head{display:flex;justify-content:space-between;gap:20px;margin:12px 0 16px}.detail-head h1{margin:8px 0 5px;font-size:23px}.detail-head p{margin:0;color:#64748b;font-size:12px}.badges{display:flex;gap:6px}.status,.priority,.risk{padding:3px 8px;border-radius:99px;font-size:11px;background:#eff6ff;color:#1d4ed8}.priority{background:#fffbeb;color:#b45309}.priority[data-priority="高"]{background:#fef2f2;color:#dc2626}.priority[data-priority="低"]{background:#ecfdf5;color:#047857}.status[data-status="草稿"]{background:#f1f5f9;color:#475569}.status[data-status="待发布"]{background:#f5f3ff;color:#7c3aed}.status[data-status="待接收"]{background:#eff6ff;color:#1d4ed8}.status[data-status="进行中"]{background:#ecfeff;color:#0e7490}.status[data-status="待完工审批"]{background:#fffbeb;color:#b45309}.status[data-status="退回整改"]{background:#fef2f2;color:#dc2626}.status[data-status="已完成"]{background:#ecfdf5;color:#047857}.status[data-status="已取消"]{background:#f1f5f9;color:#64748b}.risk{background:#fff7ed;color:#c2410c}.actions{display:flex;gap:8px;align-items:flex-start;flex-wrap:wrap}.receive-choice{display:flex;flex-direction:column;gap:5px;padding:8px;border:1px solid #bfdbfe;border-radius:8px;background:#f8fbff}.receive-choice>span{font-size:11px;color:#64748b}.receive-choice>div{display:flex;gap:7px;flex-wrap:wrap}.btn{border:1px solid #cbd5e1;background:#fff;border-radius:6px;padding:7px 11px;cursor:pointer}.btn.primary{background:#2563eb;border-color:#2563eb;color:#fff}.btn.warning{border-color:#f59e0b;color:#b45309;background:#fffbeb}.btn.danger{border-color:#ef4444;color:#dc2626;background:#fef2f2}.function-self-receive{border-color:#2563eb;color:#1d4ed8;background:#eff6ff}.function-assign{border-color:#0891b2;color:#fff;background:#0891b2}.function-edit{border-color:#3b82f6;color:#1d4ed8;background:#eff6ff}.function-progress{border-color:#0ea5e9;color:#0369a1;background:#f0f9ff}.function-complete{border-color:#16a34a;color:#047857;background:#ecfdf5}.function-change{border-color:#8b5cf6;color:#6d28d9;background:#f5f3ff}.overview-grid{display:grid;grid-template-columns:minmax(0,2fr) minmax(300px,1fr);gap:14px}.panel{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:17px;margin-bottom:14px}.panel h2{margin:0 0 14px;font-size:16px}.panel h3{font-size:13px;margin:16px 0 6px}.summary dl{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:0}.summary dl div{background:#f8fafc;border-radius:7px;padding:9px}.summary dt{font-size:11px;color:#94a3b8}.summary dd{margin:4px 0 0;font-size:13px}.progress{height:7px;background:#e2e8f0;border-radius:99px;overflow:hidden;margin:14px 0}.progress i{display:block;height:100%;background:#3b82f6}.content{white-space:pre-wrap;color:#334155;line-height:1.7}.summary blockquote{margin:0;padding:10px;background:#f8fafc;border-left:3px solid #93c5fd;color:#64748b;font-size:12px}.pending-card{border:1px solid #e2e8f0;border-radius:8px;padding:11px;margin-bottom:9px}.pending-card>span{display:block;color:#94a3b8;font-size:11px;margin-top:3px}.pending-card p{font-size:12px;color:#475569}.approval-actions{display:flex;gap:7px}.approval-actions button{border:0;background:#eff6ff;color:#1d4ed8;border-radius:5px;padding:5px 8px;cursor:pointer}.approval-actions .danger{background:#fef2f2;color:#dc2626}.section-head{display:flex;justify-content:space-between}.section-head span{font-size:11px;color:#94a3b8}.timeline{margin-left:7px}.event{position:relative;padding:0 0 17px 22px;border-left:2px solid #dbeafe}.event>i{position:absolute;width:10px;height:10px;border-radius:50%;background:#3b82f6;left:-6px;top:3px}.event-head{display:flex;justify-content:space-between}.event-head span{font-size:11px;color:#94a3b8}.event p{margin:5px 0 0;font-size:12px;color:#475569;white-space:pre-wrap}.attachments{display:flex;gap:8px;flex-wrap:wrap}.attachments a{padding:8px 10px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;color:#2563eb;text-decoration:none;font-size:12px}.attachments small{display:block;color:#94a3b8;margin-top:3px}.empty{text-align:center;padding:30px;color:#94a3b8}.empty.small{padding:20px}.modal-mask{position:fixed;inset:0;background:rgba(15,23,42,.45);z-index:1000;display:flex;align-items:center;justify-content:center}.modal{width:min(620px,94vw);max-height:92vh;overflow:auto;background:#fff;border-radius:12px;padding:20px}.modal.compact{width:min(460px,94vw)}.modal-head{display:flex;justify-content:space-between}.modal-head h2{margin:0 0 15px;font-size:18px}.modal-head button{border:0;background:none;font-size:24px}.modal label{display:flex;flex-direction:column;gap:5px;margin-bottom:10px;font-size:12px}.modal input,.modal textarea,.modal select{border:1px solid #cbd5e1;border-radius:6px;padding:8px;font:inherit}.field-hint{color:#64748b;font-size:11px;line-height:1.5}.form-row{display:grid;grid-template-columns:1fr 1fr;gap:10px}.form-row .check{flex-direction:row;align-items:center;margin-top:22px}.modal-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:15px}@media(max-width:900px){.overview-grid{grid-template-columns:1fr}.detail-head{flex-direction:column}.summary dl{grid-template-columns:1fr 1fr}}@media(max-width:560px){.summary dl,.form-row{grid-template-columns:1fr}.event-head{flex-direction:column;gap:3px}}
.department-execution-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}.department-execution-card{border:1px solid #dbe3ef;border-left:4px solid #3b82f6;border-radius:8px;padding:12px;background:#fff}.department-execution-card[data-status="已完成"]{border-left-color:#10b981;background:#f6fffa}.department-execution-card[data-status="待完工审批"]{border-left-color:#f59e0b;background:#fffbeb}.department-execution-card[data-status="退回整改"]{border-left-color:#ef4444;background:#fff7f7}.department-execution-head,.department-execution-meta{display:flex;align-items:center;justify-content:space-between;gap:8px}.department-execution-card p{margin:9px 0;color:#475569;font-size:12px}.department-progress{height:7px;background:#e2e8f0;border-radius:99px;overflow:hidden}.department-progress i{display:block;height:100%;background:#3b82f6;border-radius:inherit}.department-execution-meta{margin-top:7px;color:#64748b;font-size:10px;flex-wrap:wrap}
</style>
