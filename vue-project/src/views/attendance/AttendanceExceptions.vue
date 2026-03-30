<template>
  <div class="attendance-page">
    <div class="page-header-bar">
      <div class="header-bar-content">
        <div>
          <h1 class="page-title">考勤异常管理</h1>
          <p class="page-subtitle">仅展示智能建议需请假/缺勤且未完成请假或公出的异常日打卡记录</p>
        </div>
        <div class="header-actions">
          <div class="month-selector">
            <label class="month-label">选择月份</label>
            <input
              v-model="monthStr"
              type="month"
              class="month-input"
              @change="loadExceptions"
            />
          </div>
          <button class="btn btn-outline" type="button" @click="handleExport" :disabled="exporting || loading">
            {{ exporting ? '导出中…' : '导出考勤异常表' }}
          </button>
          <button class="btn btn-outline" type="button" @click="handleLeaveHandlerExport" :disabled="exportingLeaveHandler || loading">
            {{ exportingLeaveHandler ? '导出中…' : '导出异常处理表（上传公司系统）' }}
          </button>
        </div>
      </div>
    </div>

    <div class="container">
      <div class="table-container card mt-xl">
        <div class="table-header">
          <h3 class="table-title">考勤异常列表</h3>
          <span class="remind-tip">请提醒这些同事处理考勤</span>
          <div class="table-toolbar">
            <div class="dept-filter">
              <label class="dept-filter-label">所在单位</label>
              <select v-model="selectedDept" class="dept-filter-select">
                <option value="">全部</option>
                <option v-for="d in departmentOptions" :key="d" :value="d">{{ d }}</option>
              </select>
            </div>
            <span class="table-info text-tertiary text-sm">
              共 {{ filteredRecords.length }} 条记录
            </span>
          </div>
        </div>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th
                  scope="col"
                  class="th-sortable"
                  :class="{ 'th-sortable--active': sortBy === 'date' }"
                  title="点击切换升序/降序"
                  @click="toggleSort('date')"
                >
                  日期<span v-if="sortBy === 'date'" class="sort-ind">{{ sortDir === 'asc' ? ' ↑' : ' ↓' }}</span>
                </th>
                <th
                  scope="col"
                  class="th-sortable"
                  :class="{ 'th-sortable--active': sortBy === 'name' }"
                  title="点击切换升序/降序"
                  @click="toggleSort('name')"
                >
                  姓名<span v-if="sortBy === 'name'" class="sort-ind">{{ sortDir === 'asc' ? ' ↑' : ' ↓' }}</span>
                </th>
                <th>所在单位</th>
                <th v-for="n in timeSlots" :key="'th' + n">考勤时间{{ n }}</th>
                <th v-if="isDakaman">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td :colspan="3 + timeSlots.length + (isDakaman ? 1 : 0)" class="text-center text-tertiary">
                  加载中…
                </td>
              </tr>
              <tr v-else-if="filteredRecords.length === 0">
                <td :colspan="3 + timeSlots.length + (isDakaman ? 1 : 0)" class="text-center text-tertiary">
                  {{ loadError ? loadError : (selectedDept ? '该科室暂无考勤异常记录' : '暂无考勤异常记录') }}
                </td>
              </tr>
              <tr v-for="record in displayRecords" :key="record.id || `${record.employee_name}-${record.attendance_date}`">
                <td>
                  <span class="table-date">{{ record.attendance_date }}</span>
                </td>
                <td>
                  <div class="employee-cell">
                    <div class="employee-avatar">
                      {{ record.employee_name ? record.employee_name.charAt(0) : '' }}
                    </div>
                    <span class="employee-name">{{ record.employee_name }}</span>
                  </div>
                </td>
                <td>
                  <span class="text-secondary">{{ record.department }}</span>
                </td>
                <td v-if="isFullDayAbsence(record)" :colspan="timeSlots.length" class="full-day-absence-cell">
                  <span class="full-day-absence-badge">全天缺勤</span>
                </td>
                <template v-else>
                  <td v-for="n in timeSlots" :key="'t' + n" class="time-slot-cell">
                    <div class="time-slot-inner">
                      <span
                        v-if="hasAttendanceTimeMark(record, n)"
                        class="inout-chip"
                        :class="isOutAttendanceMark(record, n) ? 'inout-chip-out' : 'inout-chip-in'"
                      >{{ isOutAttendanceMark(record, n) ? '出' : '进' }}</span>
                      <span class="time-badge">{{ record['time_' + n] || '-' }}</span>
                    </div>
                  </td>
                </template>
                <td v-if="isDakaman">
                  <button class="btn-process" @click="openProcessModal(record)" :disabled="processingId === recordKey(record)">
                    {{ processingId === recordKey(record) ? '处理中…' : '代处理' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 打卡管理员代处理弹窗 -->
    <div v-if="processModal.show" class="modal-overlay" @click.self="closeProcessModal">
      <div class="modal-content">
        <h3 class="modal-title">代处理考勤异常</h3>
        <div class="modal-body">
          <p class="modal-info">
            <strong>{{ processModal.record?.employee_name }}</strong>
            <span class="text-secondary"> · {{ processModal.record?.department }}</span>
            <span class="text-secondary"> · {{ processModal.record?.attendance_date }}</span>
          </p>
          <div class="modal-field">
            <label>处理类型</label>
            <div class="action-toggle">
              <button type="button" class="toggle-btn" :class="{ active: processModal.processType === 'leave' }" @click="processModal.processType = 'leave'">请假</button>
              <button type="button" class="toggle-btn" :class="{ active: processModal.processType === 'business_trip' }" @click="processModal.processType = 'business_trip'">公出</button>
            </div>
          </div>
          <div v-if="processModal.processType === 'leave'" class="modal-field">
            <label>请假类型</label>
            <select v-model="processModal.leaveType" class="modal-select">
              <option v-for="lt in leaveTypeOptions" :key="lt" :value="lt">{{ lt }}</option>
            </select>
          </div>
          <div class="modal-field">
            <label>备注</label>
            <input type="text" v-model="processModal.reason" class="modal-input" placeholder="选填" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="closeProcessModal">取消</button>
          <button class="btn btn-primary" @click="confirmProcess" :disabled="processingId !== null">
            {{ processingId !== null ? '处理中…' : '确认提交' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { getAttendanceExceptions, exportAttendanceExceptions, exportLeaveHandlerTable, dakamanProcessException } from '@/api/attendance'
import { hasAttendanceTimeMark, isOutAttendanceMark } from '@/utils/attendanceTimeMark'

const timeSlots = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

const loading = ref(false)
const loadError = ref('')
const records = ref([])
const selectedDept = ref('')
const exporting = ref(false)
const exportingLeaveHandler = ref(false)
const isDakaman = ref(false)
const processingId = ref(null)

/** 表格排序：'' 表示保持接口顺序 */
const sortBy = ref('')
const sortDir = ref('asc')

function toggleSort(field) {
  if (sortBy.value === field) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortBy.value = field
    sortDir.value = 'asc'
  }
}

const leaveTypeOptions = ['换休', '带薪年休假', '事假', '病假', '婚假', '丧假', '哺乳假', '产假', '产前检查', '护理假', '探亲假']

const processModal = reactive({
  show: false,
  record: null,
  processType: 'leave',
  leaveType: '事假',
  reason: '打卡管理员代处理',
})

const now = new Date()
const monthStr = ref(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`)

const departmentOptions = computed(() => {
  const set = new Set()
  records.value.forEach(r => {
    const d = (r.department || '').trim()
    if (d) set.add(d)
  })
  return Array.from(set).sort((a, b) => a.localeCompare(b, 'zh-CN'))
})

const filteredRecords = computed(() => {
  if (!selectedDept.value) return records.value
  return records.value.filter(r => (r.department || '').trim() === selectedDept.value)
})

const displayRecords = computed(() => {
  const list = filteredRecords.value.slice()
  if (sortBy.value === 'date') {
    list.sort((a, b) => {
      const da = String(a.attendance_date || '')
      const db = String(b.attendance_date || '')
      const cmp = da.localeCompare(db, undefined, { numeric: true })
      return sortDir.value === 'asc' ? cmp : -cmp
    })
  } else if (sortBy.value === 'name') {
    list.sort((a, b) => {
      const na = String(a.employee_name || '')
      const nb = String(b.employee_name || '')
      const cmp = na.localeCompare(nb, 'zh-CN')
      return sortDir.value === 'asc' ? cmp : -cmp
    })
  }
  return list
})

function getCurrentUserName() {
  try {
    const raw = localStorage.getItem('userInfo')
    if (!raw) return ''
    const user = JSON.parse(raw)
    return (user.name || user.userName || '').trim()
  } catch {
    return ''
  }
}

function isFullDayAbsence(record) {
  if (record.full_day_absence === true) return true
  const t = [record.time_1, record.time_2, record.time_3, record.time_4, record.time_5, record.time_6, record.time_7, record.time_8, record.time_9, record.time_10]
  return t.every(v => !v || String(v).trim() === '')
}

function formatExportFilename() {
  const match = (monthStr.value || '').match(/^(\d{4})-(\d{2})$/)
  const ym = match ? `${match[1]}${match[2]}` : ''
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  const h = String(now.getHours()).padStart(2, '0')
  const min = String(now.getMinutes()).padStart(2, '0')
  const s = String(now.getSeconds()).padStart(2, '0')
  return `考勤异常_${ym || `${y}${m}`}_${y}${m}${d}_${h}${min}${s}.xlsx`
}

function loadExceptions() {
  const match = (monthStr.value || '').match(/^(\d{4})-(\d{2})$/)
  if (!match) return
  const year = parseInt(match[1], 10)
  const month = parseInt(match[2], 10)
  loading.value = true
  loadError.value = ''
  getAttendanceExceptions({
    year,
    month,
    current_user: getCurrentUserName()
  })
    .then((res) => {
      if (res && res.success && Array.isArray(res.data)) {
        records.value = res.data
        selectedDept.value = ''
        if (res.is_dakaman !== undefined) isDakaman.value = !!res.is_dakaman
      } else {
        records.value = []
        loadError.value = (res && res.message) || '加载失败'
      }
    })
    .catch((err) => {
      records.value = []
      loadError.value = err?.response?.data?.detail || err?.message || '请求失败'
    })
    .finally(() => {
      loading.value = false
    })
}

async function handleExport() {
  const match = (monthStr.value || '').match(/^(\d{4})-(\d{2})$/)
  if (!match) {
    alert('请先选择导出的年月')
    return
  }
  const name = getCurrentUserName()
  if (!name) {
    alert('请先登录')
    return
  }
  exporting.value = true
  try {
    const year = parseInt(match[1], 10)
    const month = parseInt(match[2], 10)
    const blob = await exportAttendanceExceptions({ year, month, current_user: name })
    const isExcel = blob.type && blob.type.includes('spreadsheet')
    if (isExcel) {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = formatExportFilename()
      a.click()
      URL.revokeObjectURL(url)
    } else {
      const text = await blob.text()
      try {
        const j = JSON.parse(text)
        alert(j.detail || j.message || '导出失败')
      } catch {
        alert('导出失败')
      }
    }
  } catch (e) {
    alert(e?.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

async function handleLeaveHandlerExport() {
  const match = (monthStr.value || '').match(/^(\d{4})-(\d{2})$/)
  if (!match) {
    alert('请先选择导出的年月')
    return
  }
  const name = getCurrentUserName()
  if (!name) {
    alert('请先登录')
    return
  }
  exportingLeaveHandler.value = true
  try {
    const year = parseInt(match[1], 10)
    const month = parseInt(match[2], 10)
    const blob = await exportLeaveHandlerTable({ year, month, current_user: name })
    const isExcel = blob.type && (blob.type.includes('spreadsheet') || blob.type.includes('ms-excel'))
    if (isExcel) {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `异常处理表_${match[1]}${match[2]}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
    } else {
      const text = await blob.text()
      try {
        const j = JSON.parse(text)
        alert(j.detail || j.message || '导出失败')
      } catch {
        alert('导出失败')
      }
    }
  } catch (e) {
    alert(e?.message || '导出失败')
  } finally {
    exportingLeaveHandler.value = false
  }
}

function recordKey(record) {
  return `${record.employee_name}-${record.attendance_date}`
}

function openProcessModal(record) {
  processModal.record = record
  processModal.processType = 'leave'
  processModal.leaveType = '事假'
  processModal.reason = '打卡管理员代处理'
  processModal.show = true
}

function closeProcessModal() {
  processModal.show = false
  processModal.record = null
}

async function confirmProcess() {
  const rec = processModal.record
  if (!rec) return
  const key = recordKey(rec)
  processingId.value = key
  try {
    const res = await dakamanProcessException({
      current_user: getCurrentUserName(),
      employee_name: rec.employee_name,
      department: rec.department,
      attendance_date: rec.attendance_date,
      process_type: processModal.processType,
      leave_type: processModal.leaveType,
      reason: processModal.reason || '打卡管理员代处理',
    })
    if (res && res.success) {
      records.value = records.value.filter(r => recordKey(r) !== key)
      closeProcessModal()
      alert(res.message || '处理成功')
    } else {
      alert(res?.message || '处理失败')
    }
  } catch (e) {
    alert(e?.response?.data?.detail || e?.message || '处理失败')
  } finally {
    processingId.value = null
  }
}

onMounted(() => {
  loadExceptions()
})
</script>

<style scoped>
.attendance-page {
  min-height: 100vh;
  background: var(--color-bg-layout);
  padding-bottom: var(--spacing-xxl);
}

.header-bar-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-base);
}

.month-selector {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.month-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
}

.month-input {
  min-width: 150px;
  padding: var(--spacing-sm) var(--spacing-base);
  cursor: pointer;
}

.container {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0;
}

.mt-xl {
  margin-top: var(--spacing-xl);
}

.table-container {
  padding: 0;
  border: 1px solid var(--color-border-lighter);
  overflow: hidden;
  border-radius: var(--radius-md);
  background: var(--color-bg-container);
}

.table-header {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
  background: var(--color-bg-spotlight);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.table-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.remind-tip {
  color: #e53e3e;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  margin-left: 12px;
  animation: remind-blink 1.2s ease-in-out infinite;
}

@keyframes remind-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.table-toolbar {
  display: flex;
  align-items: center;
  gap: var(--spacing-xl);
}

.dept-filter {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.dept-filter-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.dept-filter-select {
  min-width: 140px;
  padding: var(--spacing-sm) var(--spacing-base);
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  background: var(--color-bg-container);
  cursor: pointer;
}

.table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}

.data-table thead {
  background: var(--color-bg-spotlight);
}

.data-table th {
  padding: var(--spacing-base) var(--spacing-base);
  text-align: left;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border-lighter);
  white-space: nowrap;
}

.th-sortable {
  cursor: pointer;
  user-select: none;
  transition: color 0.15s;
}
.th-sortable:hover {
  color: var(--color-text-primary);
}
.th-sortable--active {
  color: var(--color-text-primary);
}
.sort-ind {
  font-weight: var(--font-weight-regular, 400);
  opacity: 0.9;
}

.data-table td {
  padding: var(--spacing-base);
  border-bottom: 1px solid var(--color-border-lighter);
  color: var(--color-text-primary);
}

.data-table tbody tr:hover {
  background-color: var(--color-bg-spotlight);
}

.table-date {
  font-family: var(--font-family-code);
  color: var(--color-text-secondary);
}

.employee-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.employee-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-base);
  background: var(--color-primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: var(--font-weight-semibold);
  flex-shrink: 0;
}

.employee-name {
  font-weight: var(--font-weight-medium);
}

.time-slot-cell {
  white-space: nowrap;
  vertical-align: middle;
}

.time-slot-inner {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
}

.inout-chip {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.25rem;
  padding: 2px 5px;
  font-size: 10px;
  font-weight: var(--font-weight-semibold);
  line-height: 1.2;
  border-radius: 3px;
  letter-spacing: 0.02em;
}

.inout-chip-in {
  background: rgba(82, 196, 26, 0.15);
  color: #389e0d;
  border: 1px solid rgba(82, 196, 26, 0.35);
}

.inout-chip-out {
  background: rgba(24, 144, 255, 0.12);
  color: #096dd9;
  border: 1px solid rgba(24, 144, 255, 0.35);
}

.time-badge {
  font-family: var(--font-family-code);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.full-day-absence-cell {
  color: var(--color-text-secondary);
}

.full-day-absence-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  background: var(--color-warning-bg, #fff3e0);
  color: var(--color-warning, #e65100);
}

.text-center {
  text-align: center;
}

.text-tertiary {
  color: var(--color-text-tertiary);
}

.text-secondary {
  color: var(--color-text-secondary);
}

.text-sm {
  font-size: var(--font-size-sm);
}

.btn-process {
  padding: 4px 12px;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-base);
  background: var(--color-bg-container);
  color: var(--color-primary);
  font-size: var(--font-size-xs);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}
.btn-process:hover:not(:disabled) {
  background: var(--color-primary);
  color: #fff;
}
.btn-process:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9000;
}
.modal-content {
  background: var(--color-bg-container);
  border-radius: var(--radius-lg);
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
  width: 440px;
  max-width: 90vw;
  overflow: hidden;
}
.modal-title {
  padding: 20px 24px 0;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
}
.modal-body {
  padding: 16px 24px 8px;
}
.modal-info {
  margin-bottom: 16px;
  font-size: var(--font-size-base);
}
.modal-field {
  margin-bottom: 14px;
}
.modal-field label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}
.modal-select, .modal-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  background: var(--color-bg-container);
  box-sizing: border-box;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 24px 20px;
}
.action-toggle {
  display: inline-flex;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  overflow: hidden;
}
.toggle-btn {
  padding: 6px 18px;
  border: none;
  background: var(--color-bg-container);
  color: var(--color-text-secondary);
  cursor: pointer;
  font-size: var(--font-size-sm);
  transition: all 0.2s;
}
.toggle-btn + .toggle-btn {
  border-left: 1px solid var(--color-border-base);
}
.toggle-btn.active {
  background: var(--color-primary);
  color: #fff;
  font-weight: var(--font-weight-medium);
}
</style>
