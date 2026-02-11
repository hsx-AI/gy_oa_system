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
            {{ exporting ? '导出中…' : '导出报表' }}
          </button>
        </div>
      </div>
    </div>

    <div class="container">
      <div class="table-container card mt-xl">
        <div class="table-header">
          <h3 class="table-title">考勤异常列表</h3>
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
                <th>日期</th>
                <th>姓名</th>
                <th>所在单位</th>
                <th>考勤时间1</th>
                <th>考勤时间2</th>
                <th>考勤时间3</th>
                <th>考勤时间4</th>
                <th>考勤时间5</th>
                <th>考勤时间6</th>
                <th>考勤时间7</th>
                <th>考勤时间8</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="11" class="text-center text-tertiary">
                  加载中…
                </td>
              </tr>
              <tr v-else-if="filteredRecords.length === 0">
                <td colspan="11" class="text-center text-tertiary">
                  {{ loadError ? loadError : (selectedDept ? '该科室暂无考勤异常记录' : '暂无考勤异常记录') }}
                </td>
              </tr>
              <tr v-for="record in filteredRecords" :key="record.id || `${record.employee_name}-${record.attendance_date}`">
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
                <td v-if="isFullDayAbsence(record)" colspan="8" class="full-day-absence-cell">
                  <span class="full-day-absence-badge">全天缺勤</span>
                </td>
                <template v-else>
                  <td><span class="time-badge">{{ record.time_1 || '-' }}</span></td>
                  <td><span class="time-badge">{{ record.time_2 || '-' }}</span></td>
                  <td><span class="time-badge">{{ record.time_3 || '-' }}</span></td>
                  <td><span class="time-badge">{{ record.time_4 || '-' }}</span></td>
                  <td><span class="time-badge">{{ record.time_5 || '-' }}</span></td>
                  <td><span class="time-badge">{{ record.time_6 || '-' }}</span></td>
                  <td><span class="time-badge">{{ record.time_7 || '-' }}</span></td>
                  <td><span class="time-badge">{{ record.time_8 || '-' }}</span></td>
                </template>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getAttendanceExceptions, exportAttendanceExceptions } from '@/api/attendance'

const loading = ref(false)
const loadError = ref('')
const records = ref([])
const selectedDept = ref('')
const exporting = ref(false)

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
  const t = [record.time_1, record.time_2, record.time_3, record.time_4, record.time_5, record.time_6, record.time_7, record.time_8]
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
</style>
