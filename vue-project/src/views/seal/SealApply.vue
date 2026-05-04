<template>
  <div class="seal-page">
    <header class="seal-header">
      <h1 class="seal-title">
        <svg class="seal-title-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <path d="M8 12h8M12 8v8"/>
        </svg>
        部门用印申请
      </h1>
      <div class="seal-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="seal-tab"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
          <span v-if="tab.key === 'pending' && pendingCount > 0" class="tab-badge">{{ pendingCount }}</span>
        </button>
      </div>
    </header>

    <!-- 发起申请 -->
    <section v-if="activeTab === 'apply'" class="seal-section">
      <div class="form-card">
        <h2 class="form-card__title">填写用印申请</h2>
        <form class="seal-form" @submit.prevent="handleSubmit">
          <div class="form-row">
            <label class="form-label required">申请人</label>
            <input class="form-input" :value="userName" disabled />
          </div>
          <div class="form-row">
            <label class="form-label">所属科室</label>
            <input class="form-input" :value="userDept" disabled />
          </div>
          <div class="form-row">
            <label class="form-label">用印类型</label>
            <select class="form-input" v-model="form.seal_type" disabled>
              <option value="部门公章">部门公章</option>
            </select>
          </div>
          <div class="form-row">
            <label class="form-label required">用印事由</label>
            <textarea class="form-textarea" v-model="form.reason" placeholder="请详细描述用印事由" rows="4"></textarea>
          </div>
          <div class="form-row">
            <label class="form-label required">审批人</label>
            <select class="form-input" v-model="form.approver" :disabled="approverLoading">
              <option value="">{{ approverLoading ? '加载中...' : '请选择审批人' }}</option>
              <option v-for="a in approverList" :key="a.name" :value="a.name">{{ a.label }}</option>
            </select>
          </div>
          <div class="form-row">
            <label class="form-label required">用印附件</label>
            <div class="file-upload-area" :class="{ 'has-file': selectedFile }">
              <input
                ref="fileInput"
                type="file"
                class="file-input-hidden"
                :accept="acceptExts"
                @change="onFileChange"
              />
              <div v-if="!selectedFile" class="file-upload-placeholder" @click="$refs.fileInput.click()">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
                </svg>
                <span>点击选择文件</span>
                <small>支持 Word、Excel、PPT、PDF、图片、压缩包等</small>
              </div>
              <div v-else class="file-upload-selected">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                </svg>
                <span class="file-name">{{ selectedFile.name }}</span>
                <small class="file-size">{{ formatFileSize(selectedFile.size) }}</small>
                <button type="button" class="file-remove-btn" @click="removeFile" title="移除文件">&times;</button>
              </div>
            </div>
          </div>
          <div class="form-row">
            <label class="form-label">备注</label>
            <input class="form-input" v-model="form.remark" placeholder="选填" />
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-submit" :disabled="submitting">
              {{ submitting ? '提交中...' : '提交申请' }}
            </button>
          </div>
        </form>
      </div>
    </section>

    <!-- 审批待办 -->
    <section v-if="activeTab === 'pending'" class="seal-section">
      <div class="table-card">
        <div class="table-card__header">
          <h2 class="table-card__title">待我审批 ({{ pendingList.length }})</h2>
          <button type="button" class="btn-refresh" @click="loadPending">刷新</button>
        </div>
        <div v-if="pendingLoading" class="empty-state">加载中...</div>
        <div v-else-if="!pendingList.length" class="empty-state">暂无待审批的用印申请</div>
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>申请人</th>
                <th>科室</th>
                <th>用印类型</th>
                <th>用印事由</th>
                <th>附件</th>
                <th>申请时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in pendingList" :key="item.id">
                <td>{{ item.applicant }}</td>
                <td>{{ item.department }}</td>
                <td>{{ item.seal_type || '-' }}</td>
                <td class="reason-cell" :title="item.reason">{{ item.reason }}</td>
                <td>
                  <a :href="attachmentUrl(item.attachment)" target="_blank" class="link-file">
                    {{ item.attachment_original || '下载' }}
                  </a>
                </td>
                <td class="time-cell">{{ item.apply_time }}</td>
                <td class="action-cell">
                  <button type="button" class="btn-approve" @click="doApprove(item, 'approve')">通过</button>
                  <button type="button" class="btn-reject" @click="openRejectDialog(item)">驳回</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- 我的申请 -->
    <section v-if="activeTab === 'mine'" class="seal-section">
      <div class="table-card">
        <div class="table-card__header">
          <h2 class="table-card__title">我的用印申请</h2>
          <button type="button" class="btn-refresh" @click="loadMyApplications">刷新</button>
        </div>
        <div v-if="myLoading" class="empty-state">加载中...</div>
        <div v-else-if="!myList.length" class="empty-state">暂无用印申请记录</div>
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>用印类型</th>
                <th>用印事由</th>
                <th>附件</th>
                <th>审批人</th>
                <th>审批状态</th>
                <th>用印状态</th>
                <th>申请时间</th>
                <th>审批时间</th>
                <th>驳回原因</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in myList" :key="item.id">
                <td>{{ item.seal_type || '-' }}</td>
                <td class="reason-cell" :title="item.reason">{{ item.reason }}</td>
                <td>
                  <a :href="attachmentUrl(item.attachment)" target="_blank" class="link-file">
                    {{ item.attachment_original || '下载' }}
                  </a>
                </td>
                <td>{{ item.approver }}</td>
                <td>
                  <span class="status-tag" :class="statusClass(item.status)">{{ item.approval_status_text || item.status_text }}</span>
                </td>
                <td>
                  <span class="status-tag" :class="sealUsedClass(item)">{{ item.seal_used_text || '—' }}</span>
                </td>
                <td class="time-cell">{{ item.apply_time }}</td>
                <td class="time-cell">{{ item.approve_time || '-' }}</td>
                <td>{{ item.reject_reason || '-' }}</td>
                <td class="action-cell">
                  <button
                    v-if="item.status === 1 && Number(item.used_stamp) !== 1"
                    type="button"
                    class="btn-mark-used"
                    :disabled="markingId === item.id"
                    @click="markUsed(item)"
                  >
                    {{ markingId === item.id ? '提交中…' : '已用印' }}
                  </button>
                  <span v-else class="cell-dash">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- 全部记录 -->
    <section v-if="activeTab === 'records'" class="seal-section">
      <div class="table-card">
        <div class="table-card__header">
          <h2 class="table-card__title">全部用印记录</h2>
          <div class="filter-bar">
            <input class="filter-input" v-model="filterKeyword" placeholder="搜索申请人/事由/类型" @keyup.enter="loadRecords(1)" />
            <select class="filter-select" v-model="filterStatus" @change="loadRecords(1)">
              <option value="">全部审批状态</option>
              <option value="pending">待审批</option>
              <option value="approved">已通过</option>
              <option value="rejected">已驳回</option>
            </select>
            <select class="filter-select" v-model="filterSealUsed" @change="loadRecords(1)">
              <option value="">全部用印状态</option>
              <option value="unused">未用印</option>
              <option value="used">已用印</option>
            </select>
            <button type="button" class="btn-refresh" @click="loadRecords(1)">查询</button>
          </div>
        </div>
        <div v-if="recordsLoading" class="empty-state">加载中...</div>
        <div v-else-if="!recordsList.length" class="empty-state">暂无记录</div>
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>申请人</th>
                <th>科室</th>
                <th>用印类型</th>
                <th>用印事由</th>
                <th>附件</th>
                <th>审批人</th>
                <th>审批状态</th>
                <th>用印状态</th>
                <th>申请时间</th>
                <th>审批时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recordsList" :key="item.id">
                <td>{{ item.applicant }}</td>
                <td>{{ item.department }}</td>
                <td>{{ item.seal_type || '-' }}</td>
                <td class="reason-cell" :title="item.reason">{{ item.reason }}</td>
                <td>
                  <a :href="attachmentUrl(item.attachment)" target="_blank" class="link-file">
                    {{ item.attachment_original || '下载' }}
                  </a>
                </td>
                <td>{{ item.approver }}</td>
                <td>
                  <span class="status-tag" :class="statusClass(item.status)">{{ item.approval_status_text || item.status_text }}</span>
                </td>
                <td>
                  <span class="status-tag" :class="sealUsedClass(item)">{{ item.seal_used_text || '—' }}</span>
                </td>
                <td class="time-cell">{{ item.apply_time }}</td>
                <td class="time-cell">{{ item.approve_time || '-' }}</td>
              </tr>
            </tbody>
          </table>
          <div class="pagination" v-if="recordsTotal > recordsPageSize">
            <button type="button" :disabled="recordsPage <= 1" @click="loadRecords(recordsPage - 1)">上一页</button>
            <span class="page-info">第 {{ recordsPage }} / {{ Math.ceil(recordsTotal / recordsPageSize) }} 页（共 {{ recordsTotal }} 条）</span>
            <button type="button" :disabled="recordsPage >= Math.ceil(recordsTotal / recordsPageSize)" @click="loadRecords(recordsPage + 1)">下一页</button>
          </div>
        </div>
      </div>
    </section>

    <!-- 驳回原因弹窗 -->
    <div v-if="rejectDialogVisible" class="modal-overlay" @click.self="rejectDialogVisible = false">
      <div class="reject-modal">
        <div class="reject-modal__header">
          <h3>驳回用印申请</h3>
          <button type="button" class="reject-modal__close" @click="rejectDialogVisible = false">&times;</button>
        </div>
        <div class="reject-modal__body">
          <p>申请人：{{ rejectTarget?.applicant }}，事由：{{ rejectTarget?.reason?.slice(0, 50) }}</p>
          <textarea class="form-textarea" v-model="rejectReason" placeholder="请输入驳回原因（选填）" rows="3"></textarea>
        </div>
        <div class="reject-modal__footer">
          <button type="button" class="btn-cancel" @click="rejectDialogVisible = false">取消</button>
          <button type="button" class="btn-reject" @click="doReject" :disabled="approving">确认驳回</button>
        </div>
      </div>
    </div>

    <!-- 提示信息 -->
    <div v-if="toastMsg" class="toast-msg" :class="toastType">{{ toastMsg }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { refreshWorkplaceTodos } from '@/composables/useWorkplaceTodos'
import {
  getSealApprovers,
  submitSealApply,
  getPendingSeal,
  approveSeal,
  getSealRecords,
  sealAttachmentUrl,
  getMySealApplications,
  markSealUsed,
} from '@/api/seal'

const route = useRoute()

const tabs = [
  { key: 'apply', label: '发起申请' },
  { key: 'pending', label: '审批待办' },
  { key: 'mine', label: '我的申请' },
  { key: 'records', label: '全部记录' },
]

const activeTab = ref('apply')

function getUserInfo() {
  try {
    const s = localStorage.getItem('userInfo')
    return s ? JSON.parse(s) : {}
  } catch { return {} }
}

const userInfo = getUserInfo()
const userName = ref((userInfo.name || userInfo.userName || '').trim())
const userDept = ref((userInfo.dept || userInfo.lsys || '').trim())

const form = ref({
  seal_type: '部门公章',
  reason: '',
  approver: '',
  remark: '',
})
const selectedFile = ref(null)
const fileInput = ref(null)
const submitting = ref(false)

const approverList = ref([])
const approverLoading = ref(false)

const pendingList = ref([])
const pendingLoading = ref(false)
const pendingCount = computed(() => pendingList.value.length)

const myList = ref([])
const myLoading = ref(false)

const recordsList = ref([])
const recordsLoading = ref(false)
const recordsTotal = ref(0)
const recordsPage = ref(1)
const recordsPageSize = 20
const filterKeyword = ref('')
const filterStatus = ref('')
const filterSealUsed = ref('')
const markingId = ref(null)

const rejectDialogVisible = ref(false)
const rejectTarget = ref(null)
const rejectReason = ref('')
const approving = ref(false)

const toastMsg = ref('')
const toastType = ref('success')
let toastTimer = null

const acceptExts = '.doc,.docx,.xls,.xlsx,.ppt,.pptx,.pdf,.txt,.csv,.jpg,.jpeg,.png,.gif,.bmp,.webp,.zip,.rar,.7z,.odt,.ods,.odp,.wps,.et'

function showToast(msg, type = 'success') {
  toastMsg.value = msg
  toastType.value = type
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastMsg.value = '' }, 4000)
}

function formatFileSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

function onFileChange(e) {
  const file = e.target.files?.[0]
  if (file) selectedFile.value = file
}

function removeFile() {
  selectedFile.value = null
  if (fileInput.value) fileInput.value.value = ''
}

function attachmentUrl(filename) {
  return sealAttachmentUrl(filename)
}

function statusClass(status) {
  if (status === 0) return 'status-pending'
  if (status === 1) return 'status-approved'
  if (status === 2) return 'status-rejected'
  return ''
}

function sealUsedClass(item) {
  if (item?.status !== 1) return ''
  return Number(item.used_stamp) === 1 ? 'status-used-done' : 'status-unused'
}

async function markUsed(item) {
  if (!item?.id || !userName.value) return
  markingId.value = item.id
  try {
    await markSealUsed({ id: item.id, applicant: userName.value })
    showToast('已标记为已用印')
    await loadMyApplications()
    try {
      await refreshWorkplaceTodos()
    } catch { /* ignore */ }
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '操作失败'
    showToast(typeof msg === 'string' ? msg : '操作失败', 'error')
  }
  markingId.value = null
}

async function loadApprovers() {
  approverLoading.value = true
  try {
    const res = await getSealApprovers()
    approverList.value = res?.data || []
  } catch { approverList.value = [] }
  approverLoading.value = false
}

async function handleSubmit() {
  if (!form.value.reason.trim()) { showToast('请填写用印事由', 'error'); return }
  if (!form.value.approver) { showToast('请选择审批人', 'error'); return }
  if (!selectedFile.value) { showToast('请上传用印附件', 'error'); return }

  submitting.value = true
  try {
    await submitSealApply({
      applicant: userName.value,
      department: userDept.value,
      seal_type: form.value.seal_type,
      reason: form.value.reason,
      approver: form.value.approver,
      remark: form.value.remark,
      attachment: selectedFile.value,
    })
    showToast('用印申请已提交，等待审批')
    form.value = { seal_type: '部门公章', reason: '', approver: '', remark: '' }
    removeFile()
    loadMyApplications()
  } catch (e) {
    showToast(e?.message || '提交失败，请重试', 'error')
  }
  submitting.value = false
}

async function loadPending() {
  if (!userName.value) return
  pendingLoading.value = true
  try {
    const res = await getPendingSeal({ approver: userName.value })
    pendingList.value = res?.data || []
  } catch { pendingList.value = [] }
  pendingLoading.value = false
}

async function doApprove(item, action) {
  approving.value = true
  try {
    await approveSeal({ id: item.id, approver: userName.value, action })
    showToast('已通过用印申请')
    loadPending()
  } catch (e) {
    showToast(e?.message || '操作失败', 'error')
  }
  approving.value = false
}

function openRejectDialog(item) {
  rejectTarget.value = item
  rejectReason.value = ''
  rejectDialogVisible.value = true
}

async function doReject() {
  if (!rejectTarget.value) return
  approving.value = true
  try {
    await approveSeal({
      id: rejectTarget.value.id,
      approver: userName.value,
      action: 'reject',
      reject_reason: rejectReason.value,
    })
    showToast('已驳回用印申请')
    rejectDialogVisible.value = false
    loadPending()
  } catch (e) {
    showToast(e?.message || '操作失败', 'error')
  }
  approving.value = false
}

async function loadMyApplications() {
  if (!userName.value) return
  myLoading.value = true
  try {
    const res = await getMySealApplications({ name: userName.value })
    myList.value = res?.data || []
  } catch { myList.value = [] }
  myLoading.value = false
}

async function loadRecords(page = 1) {
  recordsLoading.value = true
  recordsPage.value = page
  try {
    const res = await getSealRecords({
      page,
      page_size: recordsPageSize,
      keyword: filterKeyword.value,
      status: filterStatus.value,
      seal_used: filterSealUsed.value,
    })
    recordsList.value = res?.data || []
    recordsTotal.value = res?.total || 0
  } catch {
    recordsList.value = []
    recordsTotal.value = 0
  }
  recordsLoading.value = false
}

watch(activeTab, (tab) => {
  if (tab === 'pending') loadPending()
  else if (tab === 'mine') loadMyApplications()
  else if (tab === 'records') loadRecords(1)
})

onMounted(() => {
  loadApprovers()
  loadPending()
  loadMyApplications()
  const tab = route.query.tab
  if (tab && tabs.some(t => t.key === tab)) activeTab.value = tab
})
</script>

<style scoped>
.seal-page {
  min-height: 100vh;
  background: var(--color-bg-layout, #f0f2f5);
}

.seal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.seal-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary, #1e293b);
}

.seal-title-icon {
  width: 28px;
  height: 28px;
  color: #dc2626;
}

.seal-tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.seal-tab {
  position: relative;
  padding: 8px 20px;
  border: 1px solid var(--color-border-base, #d1d5db);
  border-radius: 999px;
  background: #fff;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary, #64748b);
  cursor: pointer;
  transition: all 0.15s;
}

.seal-tab:hover {
  border-color: var(--color-primary, #3b82f6);
  color: var(--color-primary, #3b82f6);
}

.seal-tab.active {
  background: var(--color-primary, #3b82f6);
  border-color: var(--color-primary, #3b82f6);
  color: #fff;
}

.tab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  margin-left: 4px;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  background: #ef4444;
  border-radius: 999px;
}

.seal-tab.active .tab-badge {
  background: rgba(255,255,255,0.3);
  color: #fff;
}

.seal-section {
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 表单卡片 */
.form-card {
  background: #fff;
  border: 1px solid var(--color-border-lighter, #e5e7eb);
  border-radius: 12px;
  padding: 28px 32px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  max-width: 720px;
}

.form-card__title {
  margin: 0 0 24px;
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary, #1e293b);
}

.seal-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary, #475569);
}

.form-label.required::after {
  content: '*';
  color: #ef4444;
  margin-left: 3px;
}

.form-input,
.form-textarea {
  padding: 10px 14px;
  border: 1px solid var(--color-border-base, #d1d5db);
  border-radius: 8px;
  font-size: 14px;
  color: var(--color-text-primary, #1e293b);
  background: #fff;
  transition: border-color 0.15s;
  outline: none;
}

.form-input:focus,
.form-textarea:focus {
  border-color: var(--color-primary, #3b82f6);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-input:disabled {
  background: #f8fafc;
  color: var(--color-text-tertiary, #94a3b8);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

/* 文件上传 */
.file-upload-area {
  border: 2px dashed var(--color-border-base, #d1d5db);
  border-radius: 10px;
  transition: all 0.15s;
  overflow: hidden;
}

.file-upload-area.has-file {
  border-style: solid;
  border-color: var(--color-primary-light, #93c5fd);
  background: #eff6ff;
}

.file-input-hidden {
  display: none;
}

.file-upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 28px;
  cursor: pointer;
  color: var(--color-text-tertiary, #94a3b8);
  transition: all 0.15s;
}

.file-upload-placeholder:hover {
  color: var(--color-primary, #3b82f6);
  border-color: var(--color-primary, #3b82f6);
  background: #f8fafc;
}

.file-upload-placeholder svg {
  width: 32px;
  height: 32px;
}

.file-upload-placeholder span {
  font-size: 14px;
  font-weight: 500;
}

.file-upload-placeholder small {
  font-size: 12px;
  color: var(--color-text-tertiary, #94a3b8);
}

.file-upload-selected {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
}

.file-upload-selected svg {
  width: 24px;
  height: 24px;
  color: var(--color-primary, #3b82f6);
  flex-shrink: 0;
}

.file-name {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary, #1e293b);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--color-text-tertiary, #94a3b8);
}

.file-remove-btn {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 50%;
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.file-remove-btn:hover {
  background: #ef4444;
  color: #fff;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 8px;
}

.btn-submit {
  padding: 10px 32px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 表格卡片 */
.table-card {
  background: #fff;
  border: 1px solid var(--color-border-lighter, #e5e7eb);
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  overflow: hidden;
}

.table-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 24px;
  border-bottom: 1px solid var(--color-border-lighter, #e5e7eb);
  flex-wrap: wrap;
}

.table-card__title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary, #1e293b);
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.filter-input {
  padding: 6px 12px;
  border: 1px solid var(--color-border-base, #d1d5db);
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  width: 200px;
}

.filter-input:focus {
  border-color: var(--color-primary, #3b82f6);
}

.filter-select {
  padding: 6px 12px;
  border: 1px solid var(--color-border-base, #d1d5db);
  border-radius: 6px;
  font-size: 13px;
  background: #fff;
}

.btn-refresh {
  padding: 6px 16px;
  border: 1px solid var(--color-primary, #3b82f6);
  border-radius: 6px;
  background: #fff;
  color: var(--color-primary, #3b82f6);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.btn-refresh:hover {
  background: var(--color-primary, #3b82f6);
  color: #fff;
}

.table-wrap {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th {
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  color: var(--color-text-secondary, #64748b);
  background: #f8fafc;
  border-bottom: 1px solid var(--color-border-lighter, #e5e7eb);
  white-space: nowrap;
}

.data-table td {
  padding: 12px 16px;
  color: var(--color-text-primary, #1e293b);
  border-bottom: 1px solid var(--color-border-lighter, #f1f5f9);
  vertical-align: middle;
}

.data-table tbody tr:hover {
  background: #f8fafc;
}

.reason-cell {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.time-cell {
  white-space: nowrap;
  font-size: 12px;
  color: var(--color-text-tertiary, #94a3b8);
}

.link-file {
  color: var(--color-primary, #3b82f6);
  text-decoration: none;
  font-size: 12px;
  max-width: 160px;
  display: inline-block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.link-file:hover {
  text-decoration: underline;
}

.action-cell {
  white-space: nowrap;
  display: flex;
  gap: 6px;
}

.btn-approve {
  padding: 4px 14px;
  border: 1px solid #10b981;
  border-radius: 6px;
  background: #ecfdf5;
  color: #059669;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.btn-approve:hover {
  background: #059669;
  color: #fff;
}

.btn-reject {
  padding: 4px 14px;
  border: 1px solid #ef4444;
  border-radius: 6px;
  background: #fef2f2;
  color: #dc2626;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.btn-reject:hover {
  background: #dc2626;
  color: #fff;
}

.status-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.status-pending {
  background: #fef3c7;
  color: #d97706;
}

.status-approved {
  background: #dcfce7;
  color: #16a34a;
}

.status-rejected {
  background: #fee2e2;
  color: #dc2626;
}

.status-unused {
  background: #fef3c7;
  color: #b45309;
}

.status-used-done {
  background: #dbeafe;
  color: #1d4ed8;
}

.btn-mark-used {
  padding: 4px 12px;
  border: 1px solid #2563eb;
  border-radius: 6px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.btn-mark-used:hover:not(:disabled) {
  background: #2563eb;
  color: #fff;
}

.btn-mark-used:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.cell-dash {
  color: var(--color-text-tertiary, #94a3b8);
  font-size: 13px;
}

.empty-state {
  padding: 48px;
  text-align: center;
  font-size: 14px;
  color: var(--color-text-tertiary, #94a3b8);
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 16px;
  border-top: 1px solid var(--color-border-lighter, #f1f5f9);
}

.pagination button {
  padding: 6px 16px;
  border: 1px solid var(--color-border-base, #d1d5db);
  border-radius: 6px;
  background: #fff;
  font-size: 13px;
  cursor: pointer;
}

.pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pagination button:not(:disabled):hover {
  background: var(--color-primary, #3b82f6);
  color: #fff;
  border-color: var(--color-primary, #3b82f6);
}

.page-info {
  font-size: 13px;
  color: var(--color-text-tertiary, #94a3b8);
}

/* 驳回弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.reject-modal {
  background: #fff;
  border-radius: 12px;
  width: 440px;
  max-width: 92vw;
  box-shadow: 0 20px 50px rgba(0,0,0,0.2);
}

.reject-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.reject-modal__header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.reject-modal__close {
  border: none;
  background: none;
  font-size: 22px;
  color: #94a3b8;
  cursor: pointer;
}

.reject-modal__close:hover {
  color: #ef4444;
}

.reject-modal__body {
  padding: 18px 24px;
}

.reject-modal__body p {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--color-text-secondary, #64748b);
}

.reject-modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 24px;
  border-top: 1px solid #e5e7eb;
}

.btn-cancel {
  padding: 8px 20px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  font-size: 13px;
  cursor: pointer;
}

.btn-cancel:hover {
  background: #f1f5f9;
}

/* 提示条 */
.toast-msg {
  position: fixed;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  padding: 10px 28px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  z-index: 200;
  animation: toastIn 0.3s ease;
  box-shadow: 0 4px 20px rgba(0,0,0,0.12);
}

.toast-msg.success {
  background: #dcfce7;
  color: #166534;
  border: 1px solid #bbf7d0;
}

.toast-msg.error {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

@keyframes toastIn {
  from { opacity: 0; transform: translateX(-50%) translateY(-10px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

@media (max-width: 768px) {
  .seal-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .form-card {
    padding: 20px 16px;
  }
  .filter-bar {
    width: 100%;
  }
  .filter-input {
    flex: 1;
    width: auto;
  }
}
</style>
