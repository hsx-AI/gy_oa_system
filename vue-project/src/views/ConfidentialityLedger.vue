<template>
  <div class="ledger-page">
    <header class="ledger-header">
      <div>
        <p class="eyebrow">保密审批台账</p>
        <h1>智能制造工艺部论文保密审批台账</h1>
      </div>
      <div class="header-actions">
        <input v-model.trim="keyword" class="search-input" type="search" placeholder="搜索申请人、论文名称、发布途径" @keyup.enter="loadRecords(1)" />
        <button type="button" class="ghost-btn" @click="loadRecords(1)" :disabled="loading">查询</button>
        <button type="button" class="primary-btn" @click="addDraft">新增一行</button>
        <button type="button" class="primary-btn export" @click="exportLedger" :disabled="exporting">
          {{ exporting ? '导出中...' : '导出台账' }}
        </button>
      </div>
    </header>

    <section class="ledger-card">
      <div class="table-wrap">
        <table class="ledger-table">
          <thead>
            <tr>
              <th class="col-index">序号</th>
              <th>申请人</th>
              <th class="col-title">论文名称</th>
              <th>申请时间</th>
              <th>资料形式</th>
              <th>发布途径</th>
              <th>是否涉密</th>
              <th>是否涉及军工及科研生产</th>
              <th class="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="draft" class="draft-row">
              <td class="col-index">新增</td>
              <td><input v-model.trim="draft.applicant" /></td>
              <td><textarea v-model.trim="draft.paper_title" rows="2"></textarea></td>
              <td><input v-model="draft.apply_time" type="date" /></td>
              <td><input v-model.trim="draft.material_form" placeholder="文字" /></td>
              <td><input v-model.trim="draft.publish_channel" placeholder="著作、论文" /></td>
              <td>
                <select v-model="draft.is_confidential">
                  <option value=""></option>
                  <option value="否">否</option>
                  <option value="是">是</option>
                </select>
              </td>
              <td>
                <select v-model="draft.military_research">
                  <option value=""></option>
                  <option value="否">否</option>
                  <option value="是">是</option>
                </select>
              </td>
              <td class="row-actions">
                <button type="button" class="save-btn" @click="saveDraft" :disabled="saving">保存</button>
                <button type="button" class="plain-btn" @click="draft = null">取消</button>
              </td>
            </tr>
            <tr v-for="(row, idx) in rows" :key="row.id">
              <td class="col-index">{{ (page - 1) * pageSize + idx + 1 }}</td>
              <template v-if="editingId === row.id">
                <td><input v-model.trim="editForm.applicant" /></td>
                <td><textarea v-model.trim="editForm.paper_title" rows="2"></textarea></td>
                <td><input v-model="editForm.apply_time" type="date" /></td>
                <td><input v-model.trim="editForm.material_form" /></td>
                <td><input v-model.trim="editForm.publish_channel" /></td>
                <td>
                  <select v-model="editForm.is_confidential">
                    <option value=""></option>
                    <option value="否">否</option>
                    <option value="是">是</option>
                  </select>
                </td>
                <td>
                  <select v-model="editForm.military_research">
                    <option value=""></option>
                    <option value="否">否</option>
                    <option value="是">是</option>
                  </select>
                </td>
                <td class="row-actions">
                  <button type="button" class="save-btn" @click="saveEdit(row.id)" :disabled="saving">保存</button>
                  <button type="button" class="plain-btn" @click="cancelEdit">取消</button>
                </td>
              </template>
              <template v-else>
                <td>{{ row.applicant || '-' }}</td>
                <td class="title-cell" :title="row.paper_title">{{ row.paper_title || '-' }}</td>
                <td>{{ displayDate(row.apply_time) || '-' }}</td>
                <td>{{ row.material_form || '-' }}</td>
                <td>{{ row.publish_channel || '-' }}</td>
                <td>{{ row.is_confidential || '-' }}</td>
                <td>{{ row.military_research || '-' }}</td>
                <td class="row-actions">
                  <button type="button" class="plain-btn" @click="startEdit(row)">编辑</button>
                  <button type="button" class="danger-btn" @click="removeRow(row)">删除</button>
                </td>
              </template>
            </tr>
            <tr v-if="!loading && !draft && rows.length === 0">
              <td colspan="9" class="empty-cell">暂无台账记录</td>
            </tr>
            <tr v-if="loading">
              <td colspan="9" class="empty-cell">加载中...</td>
            </tr>
          </tbody>
        </table>
      </div>
      <footer class="pagination" v-if="total > pageSize">
        <button type="button" :disabled="page <= 1" @click="loadRecords(page - 1)">上一页</button>
        <span>第 {{ page }} / {{ totalPages }} 页，共 {{ total }} 条</span>
        <button type="button" :disabled="page >= totalPages" @click="loadRecords(page + 1)">下一页</button>
      </footer>
    </section>

    <div v-if="toast.text" class="toast" :class="toast.type">{{ toast.text }}</div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import {
  createConfidentialityLedgerRecord,
  deleteConfidentialityLedgerRecord,
  exportConfidentialityLedger,
  getConfidentialityLedgerRecords,
  updateConfidentialityLedgerRecord,
} from '@/api/confidentialityLedger'

const rows = ref([])
const page = ref(1)
const pageSize = 50
const total = ref(0)
const keyword = ref('')
const loading = ref(false)
const saving = ref(false)
const exporting = ref(false)
const draft = ref(null)
const editingId = ref(null)
const editForm = ref({})
const toast = reactive({ text: '', type: 'success' })

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

function currentUser() {
  try {
    const user = JSON.parse(localStorage.getItem('userInfo') || '{}')
    return {
      name: (user.name || user.userName || '').trim(),
    }
  } catch {
    return { name: '' }
  }
}

function blankRow() {
  return {
    applicant: currentUser().name,
    paper_title: '',
    apply_time: '',
    material_form: '',
    publish_channel: '',
    is_confidential: '',
    military_research: '',
    current_user: currentUser().name,
  }
}

function normalizePayload(row) {
  return {
    applicant: row.applicant || '',
    paper_title: row.paper_title || '',
    apply_time: row.apply_time || '',
    material_form: row.material_form || '',
    publish_channel: row.publish_channel || '',
    is_confidential: row.is_confidential || '',
    military_research: row.military_research || '',
    current_user: currentUser().name,
  }
}

function showToast(text, type = 'success') {
  toast.text = text
  toast.type = type
  clearTimeout(showToast.timer)
  showToast.timer = setTimeout(() => { toast.text = '' }, 2600)
}

function errorMessage(e, fallback = '操作失败') {
  return e?.response?.data?.detail || e?.message || fallback
}

async function loadRecords(nextPage = 1) {
  loading.value = true
  page.value = nextPage
  try {
    const res = await getConfidentialityLedgerRecords({
      page: page.value,
      page_size: pageSize,
      keyword: keyword.value,
    })
    rows.value = res?.data || []
    total.value = Number(res?.total || 0)
  } catch (e) {
    rows.value = []
    total.value = 0
    showToast(errorMessage(e, '加载失败'), 'error')
  } finally {
    loading.value = false
  }
}

function addDraft() {
  if (!draft.value) draft.value = blankRow()
}

async function saveDraft() {
  if (!draft.value) return
  saving.value = true
  try {
    await createConfidentialityLedgerRecord(normalizePayload(draft.value))
    draft.value = null
    showToast('已新增台账记录')
    await loadRecords(1)
  } catch (e) {
    showToast(errorMessage(e, '新增失败'), 'error')
  } finally {
    saving.value = false
  }
}

function startEdit(row) {
  editingId.value = row.id
  editForm.value = { ...row }
}

function cancelEdit() {
  editingId.value = null
  editForm.value = {}
}

async function saveEdit(id) {
  saving.value = true
  try {
    await updateConfidentialityLedgerRecord(id, normalizePayload(editForm.value))
    cancelEdit()
    showToast('已保存修改')
    await loadRecords(page.value)
  } catch (e) {
    showToast(errorMessage(e, '保存失败'), 'error')
  } finally {
    saving.value = false
  }
}

async function removeRow(row) {
  if (!window.confirm(`确认删除第 ${row.id} 条台账记录？`)) return
  try {
    await deleteConfidentialityLedgerRecord(row.id)
    showToast('已删除')
    await loadRecords(rows.value.length === 1 && page.value > 1 ? page.value - 1 : page.value)
  } catch (e) {
    showToast(errorMessage(e, '删除失败'), 'error')
  }
}

function displayDate(value) {
  const s = String(value || '').trim()
  if (!s) return ''
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (m) return `${m[1]}.${Number(m[2])}.${Number(m[3])}`
  return s
}

function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob instanceof Blob ? blob : new Blob([blob]))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

async function exportLedger() {
  exporting.value = true
  try {
    const blob = await exportConfidentialityLedger({ keyword: keyword.value })
    saveBlob(blob, '智能制造工艺部论文保密审批台账.xlsx')
    showToast('导出已开始')
  } catch (e) {
    showToast(errorMessage(e, '导出失败'), 'error')
  } finally {
    exporting.value = false
  }
}

onMounted(() => loadRecords(1))
</script>

<style scoped>
.ledger-page {
  min-height: 100vh;
  padding: 0 18px 28px 0;
  color: #1f2937;
}

.ledger-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  padding: 20px 22px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.eyebrow {
  margin: 0 0 6px;
  color: #0f766e;
  font-size: 12px;
  font-weight: 800;
}

.ledger-header h1 {
  margin: 0;
  font-size: 24px;
  line-height: 1.25;
}

.header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.search-input {
  width: min(320px, 42vw);
  height: 36px;
  border: 1px solid #cbd5e1;
  border-radius: 7px;
  padding: 0 11px;
  outline: none;
}

.ghost-btn,
.primary-btn,
.plain-btn,
.danger-btn,
.save-btn,
.pagination button {
  min-height: 34px;
  border-radius: 7px;
  border: 1px solid #cbd5e1;
  padding: 0 12px;
  background: #fff;
  color: #334155;
  font-weight: 700;
  cursor: pointer;
}

.primary-btn,
.save-btn {
  border-color: #0f766e;
  background: #0f766e;
  color: #fff;
}

.primary-btn.export {
  border-color: #2563eb;
  background: #2563eb;
}

.danger-btn {
  border-color: #fecaca;
  color: #b91c1c;
  background: #fff5f5;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.ledger-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.table-wrap {
  overflow: auto;
}

.ledger-table {
  width: 100%;
  min-width: 1220px;
  border-collapse: collapse;
  font-size: 13px;
}

.ledger-table th,
.ledger-table td {
  border: 1px solid #d1d5db;
  padding: 8px 10px;
  vertical-align: middle;
}

.ledger-table th {
  background: #d9eaf7;
  color: #111827;
  text-align: center;
  font-weight: 800;
  white-space: nowrap;
}

.ledger-table td {
  background: #fff;
  text-align: center;
}

.ledger-table tbody tr:hover td {
  background: #f8fafc;
}

.draft-row td {
  background: #f0fdfa;
}

.col-index {
  width: 64px;
}

.col-title {
  width: 420px;
}

.col-actions {
  width: 138px;
}

.title-cell {
  max-width: 430px;
  text-align: left;
  line-height: 1.55;
  word-break: break-word;
}

.ledger-table input,
.ledger-table select,
.ledger-table textarea {
  width: 100%;
  min-width: 0;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 7px 8px;
  color: #172033;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
}

.ledger-table textarea {
  resize: vertical;
  min-height: 42px;
  line-height: 1.45;
}

.row-actions {
  white-space: nowrap;
}

.row-actions button + button {
  margin-left: 6px;
}

.empty-cell {
  height: 120px;
  color: #64748b;
  font-size: 14px;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 13px;
  border-top: 1px solid #e5e7eb;
  color: #64748b;
  font-size: 13px;
}

.toast {
  position: fixed;
  right: 22px;
  bottom: 22px;
  z-index: 50;
  max-width: min(420px, calc(100vw - 44px));
  padding: 11px 14px;
  border-radius: 8px;
  background: #047857;
  color: #fff;
  font-size: 14px;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.25);
}

.toast.error {
  background: #b91c1c;
}

@media (max-width: 760px) {
  .ledger-page {
    padding: 0 0 24px;
  }

  .ledger-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .search-input {
    width: 100%;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
