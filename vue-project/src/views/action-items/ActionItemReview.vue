<template>
  <div class="review-page">
    <header class="review-head">
      <div><button class="back" @click="$router.push('/action-items/minutes')">← 返回纪要列表</button><h1>{{ minute.meeting_name || 'AI 提取确认' }}</h1><p>{{ minute.minutes_number }} · {{ minute.meeting_date }} · {{ minute.status }}</p></div>
      <div class="head-actions">
        <a
          v-for="file in minute.attachments"
          :key="file.id"
          class="btn file-link"
          :href="attachmentUrl(file.id)"
          :title="file.name"
          target="_blank"
        >下载 {{ file.name }}</a>
        <button v-if="permissions.extract" class="btn function-ai" :disabled="extracting" @click="reExtract">{{ extracting ? '提取中…' : '重新提取' }}</button>
        <button v-if="permissions.publish" class="btn function-publish" :disabled="!selectedPublishIds.length || publishing" @click="publishSelected">{{ publishing ? '发布中…' : `发布选中（${selectedPublishIds.length}）` }}</button>
      </div>
    </header>

    <section v-if="permissions.minutesManage" class="batch-bar">
      <label><input v-model="selectAll" type="checkbox" @change="toggleAll"> 全选未发布项</label>
      <select v-model="batchDepartment"><option value="">批量设置责任科室</option><option v-for="d in directory.departments" :key="d">{{ d }}</option></select>
      <button class="btn function-assign" :disabled="!batchDepartment || !checkedIds.length" @click="applyBatch('department')">应用</button>
      <input v-model="batchDeadline" type="date">
      <button class="btn function-deadline" :disabled="!batchDeadline || !checkedIds.length" @click="applyBatch('deadline')">批量截止日期</button>
      <button class="btn function-merge" :disabled="checkedIds.length !== 2" @click="mergeChecked">合并两项</button>
      <button class="btn function-add" @click="addDraft">新增行动项</button>
    </section>

    <main class="review-layout">
      <section ref="textPanel" class="minutes-panel">
        <div class="panel-head"><strong>会议纪要正文</strong><span>点击右侧行动项可定位原文依据</span></div>
        <div class="minutes-text" v-html="highlightedText"></div>
      </section>
      <section class="cards-panel">
        <div class="panel-head"><strong>行动项草稿（{{ activeActions.length }}）</strong><span>AI 结果必须人工确认</span></div>
        <div v-if="loading" class="empty">加载中…</div>
        <article
          v-for="action in activeActions"
          :key="action.id"
          class="action-card"
          :class="{ active: activeId === action.id, cancelled: action.current_status === '已取消' }"
          :data-status="action.current_status"
          :data-priority="action.priority || '中'"
          @click="focusAction(action)"
        >
          <div class="card-top">
            <input v-if="isEditable(action)" v-model="checkedIds" type="checkbox" :value="action.id" @click.stop>
            <span class="status" :data-status="action.current_status">{{ action.current_status }}</span>
            <label v-if="isEditable(action)" class="priority-editor" :data-priority="action.priority || '中'" @click.stop>
              <span>{{ prioritySavingIds.includes(action.id) ? '保存中' : '优先级' }}</span>
              <select
                :value="action.priority || '中'"
                :disabled="prioritySavingIds.includes(action.id)"
                @change.stop="updatePriority(action, $event.target.value)"
              >
                <option>高</option><option>中</option><option>低</option>
              </select>
            </label>
            <span v-else class="priority-badge" :data-priority="action.priority || '中'">{{ action.priority || '中' }}优先级</span>
            <span v-if="action.uncertain_fields?.length" class="uncertain">待确认 {{ action.uncertain_fields.length }} 项</span>
            <div class="card-tools">
              <button v-if="isEditable(action)" class="tool-edit" @click.stop="edit(action)">编辑</button>
              <button v-if="isEditable(action)" class="tool-split" @click.stop="split(action)">拆分</button>
              <button v-if="isEditable(action)" class="danger" @click.stop="cancelDraft(action)">删除</button>
              <router-link v-else :to="`/action-items/${action.id}`">详情</router-link>
            </div>
          </div>
          <h3>{{ action.title }}</h3>
          <p>{{ action.content }}</p>
          <blockquote>{{ action.source_quote || '未提供原文依据' }}</blockquote>
          <dl>
            <div><dt>责任科室</dt><dd :class="{ pending: !action.responsible_department_ids?.length }">{{ action.responsible_department_ids?.join('、') || '待确认' }}</dd></div>
            <div><dt>责任人</dt><dd :class="{ pending: !action.responsible_person_ids?.length }">{{ action.responsible_person_ids?.join('、') || '待确认' }}</dd></div>
            <div v-if="action.collaborating_people?.length"><dt>协同负责人</dt><dd>{{ action.collaborating_people.join('、') }}</dd></div>
            <div><dt>主管领导</dt><dd :class="{ pending: !action.supervisor_id }">{{ action.supervisor_id || '待确认' }}</dd></div>
            <div><dt>完成时间</dt><dd :class="{ pending: !action.required_completion_date }">{{ action.required_completion_date || '待确认' }}</dd></div>
          </dl>
        </article>
        <div v-if="!loading && !activeActions.length" class="empty">暂无行动项，请重新提取或人工新增</div>
      </section>
    </main>

    <div v-if="showEdit" class="modal-mask" @click.self="showEdit = false">
      <form class="modal" @submit.prevent="saveEdit">
        <div class="modal-head"><h2>{{ editForm.id ? '编辑行动项' : '新增行动项' }}</h2><button type="button" @click="showEdit = false">×</button></div>
        <label>标题<input v-model.trim="editForm.title" required></label>
        <label>行动项内容<textarea v-model.trim="editForm.content" rows="4" required></textarea></label>
        <label>纪要原文依据<textarea v-model.trim="editForm.source_quote" rows="3"></textarea></label>
        <div class="grid">
          <label>责任科室<select v-model="editForm.responsible_department_ids" multiple @change="syncPeopleFromDepartments"><option v-for="d in directory.departments" :key="d">{{ d }}</option></select><small class="field-hint">可多选；行动项仍只保留一条</small></label>
          <label>责任人<select v-model="editForm.responsible_person_ids" multiple @change="syncDepartmentsFromPeople"><option v-for="p in directory.people" :key="`${p.name}-${p.department}`" :value="p.name">{{ p.name }}（{{ p.department }} · {{ p.job || '职务未维护' }}）</option></select><small class="field-hint">可多选；选择人员后自动补充其所属科室</small></label>
          <label>主管领导<select v-model="editForm.supervisor_id"><option value="">待确认</option><option v-for="p in directory.supervisors" :key="p.name">{{ p.name }}</option></select></label>
          <label>要求完成时间<input v-model="editForm.required_completion_date" type="date"></label>
          <label>优先级<select v-model="editForm.priority"><option>高</option><option>中</option><option>低</option></select></label>
          <label>协同科室<select v-model="editForm.collaborating_departments" multiple><option v-for="d in directory.departments" :key="d">{{ d }}</option></select></label>
          <label>协同责任人<select v-model="editForm.collaborating_people" multiple><option v-for="p in directory.people" :key="p.name">{{ p.name }}（{{ p.department }}）</option></select></label>
        </div>
        <div class="modal-actions"><button type="button" class="btn" @click="showEdit = false">取消</button><button class="btn primary" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button></div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  actionAttachmentUrl, cancelActionDraft, createActionDraft, extractMeetingActions,
  getActionDirectory, getActionPermissions, getMeetingMinute, mergeActions, publishActions,
  splitAction, updateAction,
} from '@/api/actionItems'

const route = useRoute(); const router = useRouter()
const meetingId = Number(route.params.meetingId)
const currentUser = (() => { try { const u = JSON.parse(localStorage.getItem('userInfo') || '{}'); return (u.name || u.userName || '').trim() } catch { return '' } })()
const minute = reactive({ actions: [], minutes_text: '' })
const directory = reactive({ departments: [], people: [], supervisors: [], defaultResponsibles: {} })
const permissions = reactive({})
const loading = ref(false); const extracting = ref(false); const publishing = ref(false); const saving = ref(false)
const prioritySavingIds = ref([])
const checkedIds = ref([]); const activeId = ref(0); const selectAll = ref(false)
const batchDepartment = ref(''); const batchDeadline = ref('')
const showEdit = ref(false)
const editForm = reactive(emptyForm())
function emptyForm() { return { id: 0, title: '', content: '', source_quote: '', responsible_department_id: '', responsible_person_id: '', responsible_department_ids: [], responsible_person_ids: [], collaborating_departments: [], collaborating_people: [], supervisor_id: '', required_completion_date: '', priority: '中' } }
const activeActions = computed(() => (minute.actions || []).filter(a => a.current_status !== '已取消'))
const selectedPublishIds = computed(() => activeActions.value.filter(a => checkedIds.value.includes(a.id) && isEditable(a)).map(a => a.id))
function escapeHtml(s = '') { return s.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])) }
const highlightedText = computed(() => {
  let text = escapeHtml(minute.minutes_text || '').replace(/\n/g, '<br>')
  const action = activeActions.value.find(a => a.id === activeId.value)
  const quote = action?.source_quote?.trim()
  if (quote) {
    const escaped = escapeHtml(quote).replace(/\n/g, '<br>')
    const index = text.indexOf(escaped)
    if (index >= 0) text = text.slice(0, index) + `<mark id="source-highlight">${escaped}</mark>` + text.slice(index + escaped.length)
  }
  return text
})
function isEditable(a) { return !!permissions.minutesManage && ['草稿', '待发布'].includes(a.current_status) }
function personRecord(name) { return directory.people.find(p => p.name === name) }
function syncDepartmentsFromPeople() {
  const selected = editForm.responsible_person_ids.map(personRecord).filter(Boolean)
  editForm.responsible_department_ids = [...new Set([
    ...editForm.responsible_department_ids,
    ...selected.map(record => record.department).filter(Boolean),
  ])]
  const leader = selected.find(record => ['经理', '副经理'].includes(record.job))
  if (leader) editForm.supervisor_id = leader.name
}
function syncPeopleFromDepartments() {
  const selectedDepartments = new Set(editForm.responsible_department_ids)
  const retained = editForm.responsible_person_ids.filter(name => {
    const record = personRecord(name)
    return record && selectedDepartments.has(record.department)
  })
  const defaults = editForm.responsible_department_ids
    .map(department => directory.defaultResponsibles?.[department])
    .filter(Boolean)
  editForm.responsible_person_ids = [...new Set([...retained, ...defaults])]
}
function attachmentUrl(id) { return actionAttachmentUrl(id, currentUser) }
async function load() {
  loading.value = true
  try {
    const [m, d, p] = await Promise.all([
      getMeetingMinute(meetingId, currentUser), getActionDirectory(currentUser),
      getActionPermissions(currentUser),
    ])
    Object.assign(minute, m?.item || {}); Object.assign(directory, d || {})
    Object.assign(permissions, p?.permissions || {})
    checkedIds.value = activeActions.value.filter(isEditable).map(a => a.id)
  } finally { loading.value = false }
}
function focusAction(action) {
  activeId.value = action.id
  requestAnimationFrame(() => document.getElementById('source-highlight')?.scrollIntoView({ behavior: 'smooth', block: 'center' }))
}
function toggleAll() { checkedIds.value = selectAll.value ? activeActions.value.filter(isEditable).map(a => a.id) : [] }
function edit(action) { Object.assign(editForm, emptyForm(), JSON.parse(JSON.stringify(action))); showEdit.value = true }
function addDraft() { Object.assign(editForm, emptyForm()); showEdit.value = true }
async function saveEdit() {
  saving.value = true
  try {
    const payload = { current_user: currentUser, ...editForm }
    if (editForm.id) await updateAction(editForm.id, payload)
    else await createActionDraft({ ...payload, source_meeting_id: meetingId })
    showEdit.value = false; await load()
  } catch (e) { alert(e?.response?.data?.detail || e?.message || '保存失败') }
  finally { saving.value = false }
}
async function updatePriority(action, priority) {
  if (!isEditable(action) || prioritySavingIds.value.includes(action.id)) return
  const previous = action.priority || '中'
  action.priority = priority
  prioritySavingIds.value = [...prioritySavingIds.value, action.id]
  try {
    await updateAction(action.id, { current_user: currentUser, priority })
  } catch (e) {
    action.priority = previous
    alert(e?.response?.data?.detail || e?.message || '优先级保存失败')
  } finally {
    prioritySavingIds.value = prioritySavingIds.value.filter(id => id !== action.id)
  }
}
async function applyBatch(kind) {
  const value = kind === 'department' ? batchDepartment.value : batchDeadline.value
  for (const id of checkedIds.value) {
    const patch = kind === 'department' ? { responsible_department_ids: [value] } : { required_completion_date: value }
    await updateAction(id, { current_user: currentUser, ...patch })
  }
  await load()
}
async function mergeChecked() {
  if (checkedIds.value.length !== 2) return
  if (!confirm('确认合并选中的两条行动项？被合并项将保留历史并标记取消。')) return
  try { await mergeActions({ current_user: currentUser, ids: checkedIds.value }); await load() }
  catch (e) { alert(e?.response?.data?.detail || '合并失败') }
}
async function split(action) {
  const first = prompt('请输入拆分后的第1项标题', action.title)
  if (!first) return
  const second = prompt('请输入拆分后的第2项标题', '')
  if (!second) return
  try {
    await splitAction(action.id, { current_user: currentUser, parts: [
      { title: first, content: action.content, source_quote: action.source_quote || '' },
      { title: second, content: action.content, source_quote: action.source_quote || '' },
    ] }); await load()
  } catch (e) { alert(e?.response?.data?.detail || '拆分失败') }
}
async function cancelDraft(action) {
  try { await cancelActionDraft(action.id, { current_user: currentUser }); checkedIds.value = checkedIds.value.filter(id => id !== action.id); await load() }
  catch (e) { alert(e?.response?.data?.detail || '操作失败') }
}
async function publishSelected() {
  if (!confirm(`确认发布选中的 ${selectedPublishIds.value.length} 条行动项？发布后将通知责任人。`)) return
  publishing.value = true
  try { const res = await publishActions({ current_user: currentUser, ids: selectedPublishIds.value }); alert(res?.message || '发布成功'); await load() }
  catch (e) { alert(e?.response?.data?.detail || e?.message || '发布失败') }
  finally { publishing.value = false }
}
async function reExtract() {
  if (activeActions.value.some(a => !isEditable(a)) && !confirm('该纪要已有已发布行动项。重新提取只会取消旧草稿，不影响已发布事项，是否继续？')) return
  extracting.value = true
  try { const res = await extractMeetingActions(meetingId, currentUser); alert(res?.message || '提取完成'); await load() }
  catch (e) { alert(e?.response?.data?.detail || e?.message || '提取失败') }
  finally { extracting.value = false }
}
onMounted(load)
</script>

<style scoped>
.review-page{padding-bottom:30px}.review-head{display:flex;justify-content:space-between;gap:20px;align-items:flex-end;margin-bottom:14px}.review-head h1{margin:8px 0 3px;font-size:22px}.review-head p{margin:0;color:#64748b;font-size:12px}.back{border:0;background:none;color:#2563eb;padding:0;cursor:pointer}.head-actions,.batch-bar{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.head-actions{justify-content:flex-end;max-width:min(620px,65vw)}.btn{border:1px solid #cbd5e1;background:#fff;border-radius:6px;padding:7px 11px;cursor:pointer}.file-link{text-decoration:none;color:#2563eb;max-width:420px;white-space:normal;overflow-wrap:anywhere;line-height:1.45;text-align:left;height:auto}.btn.primary{background:#2563eb;border-color:#2563eb;color:#fff}.btn:disabled{opacity:.5}.function-ai{border-color:#a78bfa;color:#6d28d9;background:#f5f3ff}.function-publish{border-color:#16a34a;color:#fff;background:#16a34a}.function-assign{border-color:#0891b2;color:#0e7490;background:#ecfeff}.function-deadline{border-color:#f59e0b;color:#b45309;background:#fffbeb}.function-merge{border-color:#8b5cf6;color:#6d28d9;background:#f5f3ff}.function-add{border-color:#10b981;color:#047857;background:#ecfdf5}.batch-bar{background:#fff;border:1px solid #e2e8f0;border-radius:9px;padding:10px;margin-bottom:12px;font-size:12px}.batch-bar select,.batch-bar input[type=date]{border:1px solid #cbd5e1;border-radius:5px;padding:6px}.review-layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(420px,.9fr);gap:12px;height:calc(100vh - 245px);min-height:560px}.minutes-panel,.cards-panel{background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow:auto}.panel-head{position:sticky;top:0;z-index:2;display:flex;justify-content:space-between;padding:12px 15px;border-bottom:1px solid #e2e8f0;background:#fff}.panel-head span{color:#94a3b8;font-size:11px}.minutes-text{padding:20px;white-space:normal;line-height:1.9;font-size:14px}.minutes-text :deep(mark){background:#fde68a;padding:2px;border-radius:2px}.action-card{margin:12px;border:1px solid #dbe3ef;border-left:4px solid #f59e0b;border-radius:9px;padding:13px;cursor:pointer;transition:.15s;background:#fff}.action-card[data-priority="高"]{border-left-color:#ef4444;background:linear-gradient(90deg,#fff7f7 0,#fff 18%)}.action-card[data-priority="中"]{border-left-color:#f59e0b}.action-card[data-priority="低"]{border-left-color:#22c55e;background:linear-gradient(90deg,#f5fff8 0,#fff 18%)}.action-card.active{border-color:#3b82f6;box-shadow:0 0 0 2px #dbeafe}.card-top{display:flex;align-items:center;gap:7px;flex-wrap:wrap}.card-tools{margin-left:auto;display:flex;gap:5px}.card-tools button,.card-tools a{border:0;border-radius:5px;padding:4px 7px;background:#eff6ff;color:#2563eb;font-size:12px;text-decoration:none;cursor:pointer}.card-tools .tool-split{background:#f5f3ff;color:#7c3aed}.card-tools .danger{background:#fef2f2;color:#dc2626}.status,.uncertain,.priority-badge{font-size:10px;padding:3px 8px;border-radius:99px;background:#eff6ff;color:#1d4ed8}.status[data-status="草稿"]{background:#f1f5f9;color:#475569}.status[data-status="待发布"]{background:#f5f3ff;color:#7c3aed}.status[data-status="待接收"]{background:#eff6ff;color:#1d4ed8}.status[data-status="进行中"]{background:#ecfeff;color:#0e7490}.status[data-status="待完工审批"]{background:#fffbeb;color:#b45309}.status[data-status="退回整改"]{background:#fef2f2;color:#dc2626}.status[data-status="已完成"]{background:#ecfdf5;color:#047857}.status[data-status="已取消"]{background:#f1f5f9;color:#64748b}.uncertain{background:#fff7ed;color:#c2410c}.priority-editor{display:flex;align-items:center;gap:4px;border-radius:99px;padding:2px 5px 2px 8px;font-size:10px;background:#fffbeb;color:#b45309}.priority-editor select{border:0;background:transparent;color:inherit;font-size:10px;font-weight:700;outline:none}.priority-editor[data-priority="高"],.priority-badge[data-priority="高"]{background:#fef2f2;color:#dc2626}.priority-editor[data-priority="低"],.priority-badge[data-priority="低"]{background:#ecfdf5;color:#047857}.action-card h3{font-size:15px;margin:11px 0 6px}.action-card>p{margin:0;color:#475569;font-size:13px;line-height:1.6}.action-card blockquote{margin:10px 0;padding:8px 10px;background:#f8fafc;border-left:3px solid #93c5fd;color:#64748b;font-size:12px}.action-card dl{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin:0}.action-card dl div{display:flex;font-size:11px}.action-card dt{color:#94a3b8;width:62px}.action-card dd{margin:0;color:#334155}.action-card dd.pending{color:#dc2626}.empty{text-align:center;padding:40px;color:#94a3b8}.modal-mask{position:fixed;inset:0;background:rgba(15,23,42,.45);z-index:1000;display:flex;align-items:center;justify-content:center}.modal{width:min(680px,94vw);max-height:92vh;overflow:auto;background:#fff;border-radius:12px;padding:20px}.modal-head{display:flex;justify-content:space-between;align-items:center}.modal-head h2{font-size:18px}.modal-head button{border:0;background:none;font-size:24px}.modal>label,.grid label{display:flex;flex-direction:column;gap:5px;margin-bottom:11px;font-size:12px}.modal input,.modal textarea,.modal select{border:1px solid #cbd5e1;border-radius:6px;padding:8px;font:inherit}.field-hint{color:#64748b;font-size:10px;line-height:1.3}.grid{display:grid;grid-template-columns:1fr 1fr;gap:0 12px}.grid select[multiple]{min-height:72px}.modal-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:15px}@media(max-width:1000px){.review-layout{grid-template-columns:1fr;height:auto}.minutes-panel,.cards-panel{max-height:70vh}}@media(max-width:600px){.review-head{align-items:flex-start;flex-direction:column}.head-actions{max-width:100%;justify-content:flex-start}.file-link{max-width:100%}.grid{grid-template-columns:1fr}.action-card dl{grid-template-columns:1fr}}
</style>
