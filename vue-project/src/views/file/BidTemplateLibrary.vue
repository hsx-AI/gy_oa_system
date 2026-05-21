<template>
  <div class="bid-template-page">
    <header class="page-header">
      <div>
        <h1>工艺投标文件管理</h1>
        <p>集中维护投标模板的最新版本，支持标签筛选、版本更新要点和历史版本下载。</p>
      </div>
      <button type="button" class="btn btn-primary" @click="openCreateUpload">上传新模板</button>
    </header>

    <section class="filter-panel">
      <div class="filter-row filter-row-main">
        <input
          v-model="filters.keyword"
          class="input keyword-input"
          type="search"
          placeholder="搜索模板名称、更新要点、转速、容量、参考项目或自定义标签"
          @keyup.enter="loadList"
        >
        <button type="button" class="btn btn-primary" @click="loadList">查询</button>
        <button type="button" class="btn" @click="resetFilters">重置</button>
      </div>
      <div class="filter-row">
        <label>
          <span>机组类型</span>
          <select v-model="filters.machine_type" class="input">
            <option value="">全部</option>
            <option v-for="item in options.machine_types" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
        <label>
          <span>文件属性</span>
          <select v-model="filters.file_scope" class="input">
            <option value="">全部</option>
            <option v-for="item in options.file_scopes" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
        <label>
          <span>轴系形式</span>
          <select v-model="filters.shaft_type" class="input">
            <option value="">全部</option>
            <option v-for="item in options.shaft_types" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
        <label>
          <span>支架支臂数量</span>
          <select v-model="filters.support_arm_count" class="input">
            <option value="">全部</option>
            <option v-for="item in options.support_arm_counts" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
      </div>
      <div class="filter-row">
        <label>
          <span>参考项目</span>
          <input v-model="filters.reference_project" class="input" type="text" placeholder="项目名称模糊搜索">
        </label>
        <label>
          <span>自定义标签</span>
          <input v-model="filters.custom_tag" class="input" type="text" placeholder="如：调速器、特殊工况">
        </label>
      </div>
    </section>

    <section class="table-panel">
      <div class="table-header">
        <h2>最新模板</h2>
        <span>共 {{ total }} 条</span>
      </div>
      <div v-if="loading" class="empty-state">正在加载...</div>
      <div v-else-if="list.length === 0" class="empty-state">暂无模板记录</div>
      <div v-else class="table-wrap">
        <table class="template-table">
          <thead>
            <tr>
              <th>模板名称</th>
              <th>最新版本</th>
              <th>标签</th>
              <th>关键参数</th>
              <th>更新要点</th>
              <th>上传信息</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in list" :key="row.id">
              <td>
                <strong class="template-title">{{ row.title }}</strong>
                <small v-if="row.description">{{ row.description }}</small>
                <small>{{ row.latest.file_name }}</small>
              </td>
              <td>
                <span class="version-pill">v{{ row.latest.version_no }}</span>
                <span class="muted">{{ row.version_count }} 个版本</span>
              </td>
              <td class="tag-cell">
                <span v-if="row.latest.machine_type" class="tag">{{ row.latest.machine_type }}</span>
                <span v-if="row.latest.file_scope" class="tag tag-blue">{{ row.latest.file_scope }}</span>
                <span v-if="row.latest.shaft_type" class="tag tag-green">{{ row.latest.shaft_type }}</span>
                <span v-for="tag in row.latest.custom_tags" :key="tag" class="tag tag-gray">{{ tag }}</span>
              </td>
              <td>
                <div class="meta-grid">
                  <span>转速：{{ row.latest.speed || '-' }}</span>
                  <span>容量：{{ row.latest.capacity || '-' }}</span>
                  <span>支臂：{{ row.latest.support_arm_count || '-' }}</span>
                  <span>参考：{{ row.latest.reference_project || '-' }}</span>
                </div>
              </td>
              <td class="note-cell" :title="row.latest.change_note">{{ row.latest.change_note || '-' }}</td>
              <td>
                <span>{{ row.latest.uploader || '-' }}</span>
                <small>{{ row.latest.upload_time || '-' }}</small>
                <small>{{ formatSize(row.latest.file_size) }}</small>
              </td>
              <td class="actions-cell">
                <button type="button" class="btn btn-small btn-primary" @click="downloadLatest(row)">下载最新</button>
                <button type="button" class="btn btn-small" @click="openUpdateUpload(row)">更新</button>
                <button type="button" class="btn btn-small" @click="openHistory(row)">历史版本</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="total > pageSize" class="pager">
        <button type="button" class="btn btn-small" :disabled="page <= 1" @click="changePage(page - 1)">上一页</button>
        <span>第 {{ page }} / {{ totalPages }} 页</span>
        <button type="button" class="btn btn-small" :disabled="page >= totalPages" @click="changePage(page + 1)">下一页</button>
      </div>
    </section>

    <div v-if="showUploadModal" class="modal-overlay" @click.self="closeUploadModal">
      <div class="upload-modal">
        <div class="modal-header">
          <h2>{{ uploadMode === 'create' ? '上传新模板' : '更新模板版本' }}</h2>
          <button type="button" class="icon-close" @click="closeUploadModal">&times;</button>
        </div>
        <form class="upload-form" @submit.prevent="submitUpload">
          <div class="form-grid">
            <label class="field field-full">
              <span>模板名称 <b>*</b></span>
              <input v-model="uploadForm.title" class="input" type="text" required>
            </label>
            <label class="field field-full">
              <span>说明</span>
              <input v-model="uploadForm.description" class="input" type="text" placeholder="可填写适用范围或注意事项">
            </label>
            <label class="field">
              <span>机组类型</span>
              <select v-model="uploadForm.machine_type" class="input">
                <option value="">请选择</option>
                <option v-for="item in options.machine_types" :key="item" :value="item">{{ item }}</option>
              </select>
            </label>
            <label class="field">
              <span>文件属性</span>
              <select v-model="uploadForm.file_scope" class="input">
                <option value="">请选择</option>
                <option v-for="item in options.file_scopes" :key="item" :value="item">{{ item }}</option>
              </select>
            </label>
            <label class="field">
              <span>轴系形式</span>
              <select v-model="uploadForm.shaft_type" class="input">
                <option value="">请选择</option>
                <option v-for="item in options.shaft_types" :key="item" :value="item">{{ item }}</option>
              </select>
            </label>
            <label class="field">
              <span>支架支臂数量</span>
              <select v-model="uploadForm.support_arm_count" class="input">
                <option value="">请选择</option>
                <option v-for="item in options.support_arm_counts" :key="item" :value="item">{{ item }}</option>
              </select>
            </label>
            <label class="field">
              <span>转速</span>
              <input v-model="uploadForm.speed" class="input" type="text" placeholder="如：150r/min">
            </label>
            <label class="field">
              <span>容量</span>
              <input v-model="uploadForm.capacity" class="input" type="text" placeholder="如：300MW">
            </label>
            <label class="field field-full">
              <span>参考项目</span>
              <input v-model="uploadForm.reference_project" class="input" type="text" placeholder="可填写一个或多个参考项目">
            </label>
            <label class="field field-full">
              <span>自定义标签</span>
              <input v-model="uploadForm.custom_tags" class="input" type="text" placeholder="多个标签用逗号分隔">
            </label>
            <label class="field field-full">
              <span>本次更新要点 <b>*</b></span>
              <textarea v-model="uploadForm.change_note" class="input textarea" required placeholder="请记录本次模板新增、修订或替换的关键内容"></textarea>
            </label>
            <label class="field field-full">
              <span>模板文件 <b>*</b></span>
              <input ref="fileInputRef" class="input" type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.rar,.7z" @change="onFileChange">
              <small>支持 PDF、Word、Excel、PPT 和压缩包。</small>
            </label>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn" @click="closeUploadModal">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="uploading">{{ uploading ? '上传中...' : '提交' }}</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="showHistoryModal" class="modal-overlay" @click.self="closeHistoryModal">
      <div class="history-modal">
        <div class="modal-header">
          <div>
            <h2>{{ historyTemplate?.title || '历史版本' }}</h2>
            <p>可下载任意历史版本，用于比对或回溯。</p>
          </div>
          <button type="button" class="icon-close" @click="closeHistoryModal">&times;</button>
        </div>
        <div v-if="historyLoading" class="empty-state">正在加载...</div>
        <div v-else class="history-list">
          <article v-for="item in historyList" :key="item.id" class="history-item">
            <div class="history-main">
              <div>
                <span class="version-pill">v{{ item.version_no }}</span>
                <strong>{{ item.file_name }}</strong>
                <span v-if="item.id === historyTemplate?.current_version_id" class="tag tag-green">最新</span>
              </div>
              <p>{{ item.change_note || '未填写更新要点' }}</p>
              <div class="history-meta">
                <span>{{ item.uploader || '-' }}</span>
                <span>{{ item.upload_time || '-' }}</span>
                <span>{{ formatSize(item.file_size) }}</span>
                <span>{{ [item.machine_type, item.file_scope, item.shaft_type].filter(Boolean).join(' / ') || '-' }}</span>
              </div>
            </div>
            <button type="button" class="btn btn-small btn-primary" @click="downloadVersion(item)">下载</button>
          </article>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  getBidTemplateFileUrl,
  getBidTemplateHistory,
  getBidTemplateList,
  getBidTemplateOptions,
  uploadBidTemplate
} from '@/api/bidTemplate'

const options = ref({
  machine_types: [],
  file_scopes: [],
  shaft_types: [],
  support_arm_counts: [],
  reference_projects: []
})
const filters = ref(defaultFilters())
const list = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 20

const showUploadModal = ref(false)
const uploadMode = ref('create')
const uploading = ref(false)
const selectedFile = ref(null)
const fileInputRef = ref(null)
const uploadForm = ref(defaultUploadForm())

const showHistoryModal = ref(false)
const historyTemplate = ref(null)
const historyList = ref([])
const historyLoading = ref(false)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

function defaultFilters() {
  return {
    keyword: '',
    machine_type: '',
    file_scope: '',
    shaft_type: '',
    support_arm_count: '',
    reference_project: '',
    custom_tag: ''
  }
}

function defaultUploadForm() {
  return {
    template_id: '',
    title: '',
    description: '',
    change_note: '',
    machine_type: '',
    file_scope: '',
    speed: '',
    capacity: '',
    shaft_type: '',
    support_arm_count: '',
    reference_project: '',
    custom_tags: ''
  }
}

function getCurrentUser() {
  try {
    const raw = localStorage.getItem('userInfo')
    if (!raw) return ''
    const u = JSON.parse(raw)
    return (u.name || u.userName || '').trim()
  } catch {
    return ''
  }
}

async function loadOptions() {
  try {
    const res = await getBidTemplateOptions()
    options.value = {
      machine_types: res.machine_types || [],
      file_scopes: res.file_scopes || [],
      shaft_types: res.shaft_types || [],
      support_arm_counts: res.support_arm_counts || [],
      reference_projects: res.reference_projects || []
    }
  } catch {
    options.value = {
      machine_types: ['抽蓄', '混流', '轴流', '贯流', '通用'],
      file_scopes: ['专用文件', '通用文件', '专用及通用文件'],
      shaft_types: ['立式', '卧式', '斜式', '通用'],
      support_arm_counts: ['2', '3', '4', '5', '6', '8', '通用'],
      reference_projects: []
    }
  }
}

async function loadList() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    for (const [key, value] of Object.entries(filters.value)) {
      const text = String(value || '').trim()
      if (text) params[key] = text
    }
    const res = await getBidTemplateList(params)
    list.value = res.list || []
    total.value = res.total || 0
  } catch (err) {
    list.value = []
    total.value = 0
    alert(err.response?.data?.detail || err.message || '加载模板列表失败')
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.value = defaultFilters()
  page.value = 1
  loadList()
}

function changePage(next) {
  page.value = next
  loadList()
}

function openCreateUpload() {
  uploadMode.value = 'create'
  uploadForm.value = defaultUploadForm()
  selectedFile.value = null
  showUploadModal.value = true
}

function openUpdateUpload(row) {
  const latest = row.latest || {}
  uploadMode.value = 'update'
  uploadForm.value = {
    template_id: row.id,
    title: row.title || '',
    description: row.description || '',
    change_note: '',
    machine_type: latest.machine_type || '',
    file_scope: latest.file_scope || '',
    speed: latest.speed || '',
    capacity: latest.capacity || '',
    shaft_type: latest.shaft_type || '',
    support_arm_count: latest.support_arm_count || '',
    reference_project: latest.reference_project || '',
    custom_tags: (latest.custom_tags || []).join(', ')
  }
  selectedFile.value = null
  showUploadModal.value = true
}

function closeUploadModal() {
  showUploadModal.value = false
  selectedFile.value = null
  uploadForm.value = defaultUploadForm()
  if (fileInputRef.value) fileInputRef.value.value = ''
}

function onFileChange(e) {
  const file = e.target.files?.[0] || null
  selectedFile.value = file
  if (file && uploadMode.value === 'create' && !uploadForm.value.title.trim()) {
    uploadForm.value.title = file.name.replace(/\.[^/.]+$/, '')
  }
}

async function submitUpload() {
  if (!selectedFile.value) {
    alert('请选择模板文件')
    return
  }
  if (!uploadForm.value.title.trim()) {
    alert('请填写模板名称')
    return
  }
  if (!uploadForm.value.change_note.trim()) {
    alert('请填写本次更新要点')
    return
  }
  uploading.value = true
  try {
    await uploadBidTemplate({
      ...uploadForm.value,
      uploader: getCurrentUser(),
      file: selectedFile.value
    })
    alert(uploadMode.value === 'create' ? '模板上传成功' : '模板版本更新成功')
    closeUploadModal()
    await loadOptions()
    await loadList()
  } catch (err) {
    alert(err.response?.data?.detail || err.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

async function openHistory(row) {
  showHistoryModal.value = true
  historyTemplate.value = { id: row.id, title: row.title, current_version_id: row.current_version_id }
  historyList.value = []
  historyLoading.value = true
  try {
    const res = await getBidTemplateHistory(row.id)
    historyTemplate.value = res.template || historyTemplate.value
    historyList.value = res.versions || []
  } catch (err) {
    alert(err.response?.data?.detail || err.message || '加载历史版本失败')
  } finally {
    historyLoading.value = false
  }
}

function closeHistoryModal() {
  showHistoryModal.value = false
  historyTemplate.value = null
  historyList.value = []
}

function downloadLatest(row) {
  window.open(getBidTemplateFileUrl({ templateId: row.id }), '_blank', 'noopener')
}

function downloadVersion(version) {
  window.open(getBidTemplateFileUrl({ versionId: version.id }), '_blank', 'noopener')
}

function formatSize(size) {
  const n = Number(size || 0)
  if (!n) return '-'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

onMounted(async () => {
  await loadOptions()
  await loadList()
})
</script>

<style scoped>
.bid-template-page {
  width: 100%;
  padding: 0 20px 32px 0;
  color: var(--color-text-primary, #1f2937);
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
  padding: 18px 20px;
  background: #fff;
  border: 1px solid var(--color-border-lighter, #e5e7eb);
  border-radius: 8px;
}

.page-header h1 {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 700;
}

.page-header p {
  margin: 0;
  color: var(--color-text-secondary, #6b7280);
  font-size: 14px;
}

.filter-panel,
.table-panel {
  margin-bottom: 18px;
  padding: 16px;
  background: #fff;
  border: 1px solid var(--color-border-lighter, #e5e7eb);
  border-radius: 8px;
}

.filter-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.filter-row:last-child {
  margin-bottom: 0;
}

.filter-row-main {
  display: flex;
}

.keyword-input {
  flex: 1;
}

.filter-row label,
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--color-text-secondary, #6b7280);
}

.field b {
  color: #dc2626;
}

.field small {
  color: var(--color-text-tertiary, #9ca3af);
}

.input {
  min-height: 36px;
  padding: 7px 10px;
  border: 1px solid var(--color-border-base, #d1d5db);
  border-radius: 6px;
  background: #fff;
  color: var(--color-text-primary, #1f2937);
  font-size: 14px;
  box-sizing: border-box;
}

.textarea {
  min-height: 90px;
  resize: vertical;
  line-height: 1.5;
}

.btn {
  min-height: 34px;
  padding: 7px 14px;
  border: 1px solid var(--color-border-base, #d1d5db);
  border-radius: 6px;
  background: #fff;
  color: var(--color-text-primary, #1f2937);
  font-size: 14px;
  cursor: pointer;
}

.btn:hover {
  background: #f9fafb;
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn-primary {
  border-color: var(--color-primary, #2563eb);
  background: var(--color-primary, #2563eb);
  color: #fff;
}

.btn-primary:hover {
  background: #1d4ed8;
}

.btn-small {
  min-height: 28px;
  padding: 4px 9px;
  font-size: 12px;
}

.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.table-header h2 {
  margin: 0;
  font-size: 17px;
}

.table-header span {
  color: var(--color-text-secondary, #6b7280);
  font-size: 13px;
}

.table-wrap {
  overflow-x: auto;
}

.template-table {
  width: 100%;
  min-width: 1100px;
  border-collapse: collapse;
  font-size: 13px;
}

.template-table th,
.template-table td {
  padding: 10px 12px;
  border: 1px solid var(--color-border-lighter, #e5e7eb);
  text-align: left;
  vertical-align: top;
}

.template-table th {
  background: #f8fafc;
  font-weight: 600;
}

.template-table td small,
.muted {
  display: block;
  margin-top: 4px;
  color: var(--color-text-tertiary, #9ca3af);
  font-size: 12px;
}

.template-title {
  display: block;
  max-width: 240px;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.version-pill {
  display: inline-flex;
  align-items: center;
  min-width: 40px;
  justify-content: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4338ca;
  font-weight: 700;
  font-size: 12px;
}

.tag-cell {
  max-width: 220px;
}

.tag {
  display: inline-flex;
  align-items: center;
  margin: 0 4px 4px 0;
  padding: 2px 8px;
  border-radius: 999px;
  background: #fef3c7;
  color: #92400e;
  font-size: 12px;
  white-space: nowrap;
}

.tag-blue {
  background: #dbeafe;
  color: #1d4ed8;
}

.tag-green {
  background: #dcfce7;
  color: #15803d;
}

.tag-gray {
  background: #f3f4f6;
  color: #4b5563;
}

.meta-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 4px;
  min-width: 150px;
  color: var(--color-text-secondary, #6b7280);
}

.note-cell {
  max-width: 220px;
  line-height: 1.45;
}

.actions-cell {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  min-width: 190px;
}

.empty-state {
  padding: 42px 16px;
  text-align: center;
  color: var(--color-text-secondary, #6b7280);
}

.pager {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 12px;
  color: var(--color-text-secondary, #6b7280);
  font-size: 13px;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(0, 0, 0, 0.48);
}

.upload-modal,
.history-modal {
  width: min(860px, 96vw);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.24);
  overflow: hidden;
}

.history-modal {
  width: min(920px, 96vw);
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border-lighter, #e5e7eb);
}

.modal-header h2 {
  margin: 0;
  font-size: 18px;
}

.modal-header p {
  margin: 4px 0 0;
  color: var(--color-text-secondary, #6b7280);
  font-size: 13px;
}

.icon-close {
  border: 0;
  background: transparent;
  color: var(--color-text-tertiary, #9ca3af);
  font-size: 28px;
  line-height: 1;
  cursor: pointer;
}

.upload-form,
.history-list {
  overflow: auto;
}

.upload-form {
  padding: 18px 20px 20px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.field-full {
  grid-column: 1 / -1;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

.history-list {
  padding: 8px 20px 20px;
}

.history-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 0;
  border-bottom: 1px solid var(--color-border-lighter, #e5e7eb);
}

.history-item:last-child {
  border-bottom: 0;
}

.history-main {
  min-width: 0;
}

.history-main > div:first-child {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.history-main p {
  margin: 8px 0;
  color: var(--color-text-primary, #1f2937);
  line-height: 1.5;
}

.history-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  color: var(--color-text-secondary, #6b7280);
  font-size: 12px;
}

@media (max-width: 900px) {
  .bid-template-page {
    padding-right: 0;
  }

  .page-header {
    flex-direction: column;
  }

  .filter-row,
  .filter-row-main,
  .form-grid {
    display: flex;
    flex-direction: column;
  }

  .template-table {
    min-width: 980px;
  }
}
</style>
