<template>
  <div class="overtime-pay-page">
    <div class="page-header">
      <div class="header-content">
        <h1 class="header-title">其他绩效激励统计</h1>
        <p class="header-subtitle">按科室、年月或自定义时间段查询与导出</p>
      </div>
    </div>

    <div class="container">
      <div v-if="!canView" class="no-permission card">
        <div class="no-permission-content">
          <p>您暂无权限查看其他绩效激励统计。</p>
          <router-link to="/" class="btn btn-primary">返回首页</router-link>
        </div>
      </div>

      <template v-else>
        <div class="filter-section card">
          <div class="filter-form">
            <div class="filter-fields">
              <div class="form-item" v-if="scope !== 'self'">
                <label class="form-label">科室</label>
                <select v-model="selectedLsys" class="form-select" :disabled="!lsysList.length || scope === 'lsys'">
                  <option value="">全员</option>
                  <option v-for="d in lsysList" :key="d" :value="d">{{ d }}</option>
                </select>
              </div>
              <div class="form-item" v-if="scope === 'self'">
                <label class="form-label">范围</label>
                <span class="scope-self-label">本人</span>
              </div>
              <div :class="['form-item', { 'form-item--disabled': isDateRangeMode }]">
                <label class="form-label">年份</label>
                <select v-model="filterYear" class="form-select" :disabled="isDateRangeMode">
                  <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option>
                </select>
              </div>
              <div :class="['form-item', { 'form-item--disabled': isDateRangeMode }]">
                <label class="form-label">月份</label>
                <select v-model="filterMonth" class="form-select" :disabled="isDateRangeMode">
                  <option value="">全年</option>
                  <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
                </select>
              </div>
              <div class="form-item">
                <label class="form-label">开始日期</label>
                <input v-model="dateFrom" type="date" class="form-date" />
              </div>
              <div class="form-item">
                <label class="form-label">结束日期</label>
                <input v-model="dateTo" type="date" class="form-date" />
              </div>
            </div>
            <div class="filter-toolbar">
              <button class="btn btn-primary" @click="fetchData" :disabled="loading">
                <svg v-if="loading" class="loading-icon" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="31.4" stroke-linecap="round">
                    <animateTransform attributeName="transform" type="rotate" dur="1s" from="0 12 12" to="360 12 12" repeatCount="indefinite"/>
                  </circle>
                </svg>
                <span>{{ loading ? '加载中...' : '查询' }}</span>
              </button>
              <div class="filter-toolbar-exports">
                <span class="toolbar-exports-label">导出</span>
                <button
                  type="button"
                  class="btn btn-outline"
                  :disabled="(!filterMonth && !isDateRangeMode) || exportLoading"
                  @click="downloadExcel"
                >
                  <span v-if="exportLoading">生成中...</span>
                  <span v-else>工资报表</span>
                </button>
                <button
                  type="button"
                  class="btn btn-outline"
                  :disabled="overtimeHoursExportLoading"
                  @click="downloadOvertimeHoursExcel"
                >
                  <span v-if="overtimeHoursExportLoading">生成中...</span>
                  <span v-else>全部加班时长</span>
                </button>
                <button
                  type="button"
                  class="btn btn-outline"
                  :disabled="isDateRangeMode || fullAttendanceExportLoading"
                  :title="isDateRangeMode ? '满勤名单请使用年份/月份筛选' : ''"
                  @click="downloadFullAttendanceExcel"
                >
                  <span v-if="fullAttendanceExportLoading">生成中...</span>
                  <span v-else>满勤名单</span>
                </button>
                <button
                  type="button"
                  class="btn btn-outline"
                  :disabled="isDateRangeMode || !filterMonth || attendanceReportLoading"
                  :title="isDateRangeMode ? '考勤表请使用年份/月份筛选' : ''"
                  @click="downloadAttendanceReportWord"
                >
                  <span v-if="attendanceReportLoading">生成中...</span>
                  <span v-else>考勤表 Word</span>
                </button>
              </div>
            </div>
          </div>
          <p v-if="canView" class="filter-hint">筛选方式二选一：① 年份+月份（或全年）；② 同时填写开始、结束日期（自定义时间段，此时年月选择失效）。查询与「下载 Excel 工资报表」「导出全部加班时长」均支持时间段；工资报表需选定单月或自定义区间。满勤名单、考勤表(Word) 仅支持按年月，自定义时间段时请改回年月筛选。科室选「全员」时，考勤表按科室分别生成 Word 并打包为 zip。</p>
        </div>

        <div v-if="hasFetched" class="section card overtime-pay-section">
          <h2 class="section-title">
            <svg class="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="1" x2="12" y2="23"/>
              <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
            统计结果
          </h2>
          <p class="section-desc">
            {{ scope === 'self' ? '本人' : (selectedLsys || '全员') }} {{ periodLabel }}
            （单价 {{ overtimePayZhibanfei }} 元/小时，十一、高温假、春节三个假期单日值班满8小时固定奖励200元/天，超出8小时不额外奖励）
          </p>
          <div v-if="overtimePayByMonth.length > 0" class="table-wrap">
            <h3 class="subsection-title">按月份</h3>
            <table class="data-table">
              <thead>
                <tr>
                  <th>月份</th>
                  <th>加班小时</th>
                  <th>其他绩效激励（元）</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in overtimePayByMonth" :key="row.month">
                  <td>{{ row.monthLabel }}</td>
                  <td>{{ row.hours }}</td>
                  <td class="pay-cell">{{ row.pay }}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr>
                  <td>合计</td>
                  <td>{{ overtimePayByMonth.reduce((s, r) => s + (r.hours || 0), 0).toFixed(2) }}</td>
                  <td class="pay-cell">{{ overtimePayByMonth.reduce((s, r) => s + (r.pay || 0), 0).toFixed(2) }}</td>
                </tr>
              </tfoot>
            </table>
          </div>
          <div v-if="overtimePayByEmployee.length > 0" class="table-wrap">
            <h3 class="subsection-title">科室员工其他绩效激励明细</h3>
            <table class="data-table">
              <thead>
                <tr>
                  <th>姓名</th>
                  <th>加班小时</th>
                  <th>其他绩效激励（元）</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in overtimePayByEmployee" :key="row.name">
                  <td>{{ row.name }}</td>
                  <td>{{ row.hours }}</td>
                  <td class="pay-cell">{{ row.pay }}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr>
                  <td>合计</td>
                  <td>{{ overtimePayByEmployee.reduce((s, r) => s + (r.hours || 0), 0).toFixed(2) }}</td>
                  <td class="pay-cell">{{ overtimePayByEmployee.reduce((s, r) => s + (r.pay || 0), 0).toFixed(2) }}</td>
                </tr>
              </tfoot>
            </table>
          </div>
          <div v-if="hasFetched && !overtimePayByMonth.length && !overtimePayByEmployee.length" class="empty-state">暂无其他绩效激励数据</div>
        </div>

        <div v-if="!hasFetched && !loading" class="init-hint card">
          <p>选择科室、年份与月份，或填写开始/结束日期后点击「查询」查看其他绩效激励统计。</p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as XLSX from 'xlsx'
import { getOvertimePayPermission, getDeptLsysList, getDeptOvertimePayByMonth, getDeptOvertimePayByEmployee, getOvertimePayExport, getOvertimeHoursExport, getFullAttendanceExport, downloadAttendanceReport } from '@/api/attendance'

const router = useRouter()
const canView = ref(false)
const scope = ref('self')  // self | lsys | all
const scopeLsys = ref('')   // scope=lsys 时本室名称
const currentUserName = ref('')
const lsysList = ref([])
const selectedLsys = ref('')
const filterYear = ref(new Date().getFullYear())
const filterMonth = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const loading = ref(false)
const exportLoading = ref(false)
const overtimeHoursExportLoading = ref(false)
const fullAttendanceExportLoading = ref(false)
const attendanceReportLoading = ref(false)
const hasFetched = ref(false)
const overtimePayByMonth = ref([])
const overtimePayByEmployee = ref([])
const overtimePayZhibanfei = ref(15)

const yearOptions = computed(() => {
  const y = new Date().getFullYear()
  return [y, y - 1, y - 2, y - 3, y - 4, y - 5]
})

const isDateRangeMode = computed(() => Boolean(dateFrom.value && dateTo.value))

const periodLabel = computed(() => {
  if (isDateRangeMode.value) return `${dateFrom.value} 至 ${dateTo.value}`
  return `${filterYear.value}年${filterMonth.value ? filterMonth.value + '月' : '全年'}`
})

function exportPeriodLabel() {
  if (isDateRangeMode.value) return `${dateFrom.value}_${dateTo.value}`
  if (filterMonth.value) return `${filterYear.value}年${filterMonth.value}月`
  return `${filterYear.value}年全年`
}

function buildPeriodParams(extra = {}) {
  const params = {
    current_user: currentUserName.value,
    scope: scope.value,
    ...extra
  }
  if (scope.value === 'lsys' && scopeLsys.value) params.scope_lsys = scopeLsys.value
  if ((dateFrom.value && !dateTo.value) || (!dateFrom.value && dateTo.value)) {
    throw new Error('开始日期和结束日期需要同时选择')
  }
  if (isDateRangeMode.value) {
    params.date_from = dateFrom.value
    params.date_to = dateTo.value
  } else {
    params.year = filterYear.value
    if (filterMonth.value) params.month = Number(filterMonth.value)
  }
  return params
}

const fetchData = async () => {
  loading.value = true
  hasFetched.value = true
  let payParams
  try {
    payParams = buildPeriodParams()
  } catch (e) {
    alert(e.message || '日期筛选无效')
    loading.value = false
    return
  }
  if (scope.value === 'self') payParams.name = currentUserName.value
  else if (selectedLsys.value) payParams.lsys = selectedLsys.value
  try {
    const [resMonth, resEmp] = await Promise.all([
      getDeptOvertimePayByMonth(payParams),
      getDeptOvertimePayByEmployee(payParams)
    ])
    overtimePayByMonth.value = (resMonth?.success && resMonth?.list) ? resMonth.list : []
    overtimePayByEmployee.value = (resEmp?.success && resEmp?.list) ? resEmp.list : []
    overtimePayZhibanfei.value = resMonth?.zhibanfei ?? resEmp?.zhibanfei ?? 15
  } catch (e) {
    overtimePayByMonth.value = []
    overtimePayByEmployee.value = []
    alert(e.response?.data?.detail || e.message || '查询失败')
  } finally {
    loading.value = false
  }
}

function sheetFromList(list) {
  const header = ['姓名', '本月其他绩效激励（元）']
  const rows = list.map((item) => [item.name || '', item.pay ?? 0])
  return XLSX.utils.aoa_to_sheet([header, ...rows])
}

function overtimeHoursSheetFromList(list) {
  const header = ['姓名', '加班总时长(小时)', '其他绩效激励时长(小时)', '换休票时长(小时)', '加班次数']
  const rows = (list || []).map((item) => [
    item.name || '',
    item.totalHours ?? 0,
    item.payHours ?? 0,
    item.hxHours ?? 0,
    item.times ?? 0
  ])
  return XLSX.utils.aoa_to_sheet([header, ...rows])
}

async function downloadOvertimeHoursExcel() {
  overtimeHoursExportLoading.value = true
  try {
    const params = buildPeriodParams()
    const res = await getOvertimeHoursExport(params)
    if (!res?.success || res.all === undefined) {
      alert('获取加班时长数据失败')
      return
    }
    const wb = XLSX.utils.book_new()
    const allSheet = overtimeHoursSheetFromList(res.all || [])
    XLSX.utils.book_append_sheet(wb, allSheet, scope.value === 'self' ? '本人' : '全员')
    for (const dept of res.byDept || []) {
      const sheetName = (dept.lsys || '科室').slice(0, 31)
      const sheet = overtimeHoursSheetFromList(dept.list || [])
      XLSX.utils.book_append_sheet(wb, sheet, sheetName)
    }
    const fileName = `全部加班时长_${exportPeriodLabel()}.xlsx`
    XLSX.writeFile(wb, fileName)
  } catch (e) {
    console.error(e)
    alert(e.message || e.response?.data?.detail || '导出失败，请稍后重试')
  } finally {
    overtimeHoursExportLoading.value = false
  }
}

async function downloadExcel() {
  if (!filterMonth.value && !isDateRangeMode.value) {
    alert('请先选择月份，或填写开始/结束日期后再下载报表')
    return
  }
  exportLoading.value = true
  try {
    const res = await getOvertimePayExport(buildPeriodParams())
    if (!res?.success || res.all === undefined) {
      alert('获取报表数据失败')
      return
    }
    const wb = XLSX.utils.book_new()
    const allSheet = sheetFromList(res.all || [])
    XLSX.utils.book_append_sheet(wb, allSheet, scope.value === 'self' ? '本人' : '全员')
    const byDept = res.byDept || []
    for (const dept of byDept) {
      const sheetName = (dept.lsys || '科室').slice(0, 31)
      const sheet = sheetFromList(dept.list || [])
      XLSX.utils.book_append_sheet(wb, sheet, sheetName)
    }
    const fileName = `其他绩效激励工资报表_${exportPeriodLabel()}.xlsx`
    XLSX.writeFile(wb, fileName)
  } catch (e) {
    console.error(e)
    alert(e.message || e.response?.data?.detail || '下载失败，请稍后重试')
  } finally {
    exportLoading.value = false
  }
}

async function downloadAttendanceReportWord() {
  if (!filterMonth.value) {
    alert('请先选择月份后再下载考勤表')
    return
  }
  attendanceReportLoading.value = true
  try {
    const params = { year: filterYear.value, month: Number(filterMonth.value) }
    if (scope.value !== 'self' && selectedLsys.value) params.lsys = selectedLsys.value
    const blob = await downloadAttendanceReport(params)
    const url = window.URL.createObjectURL(blob instanceof Blob ? blob : new Blob([blob]))
    const a = document.createElement('a')
    a.href = url
    const isAllDepts = scope.value !== 'self' && !selectedLsys.value
    const lsysLabel = selectedLsys.value ? `_${selectedLsys.value}` : ''
    a.download = isAllDepts
      ? `考勤表_${filterYear.value}年${filterMonth.value}月_各科室.zip`
      : `考勤表_${filterYear.value}年${filterMonth.value}月${lsysLabel}.docx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  } catch (e) {
    console.error(e)
    alert('下载考勤表失败，请稍后重试')
  } finally {
    attendanceReportLoading.value = false
  }
}

async function downloadFullAttendanceExcel() {
  fullAttendanceExportLoading.value = true
  try {
    const params = { year: filterYear.value }
    if (filterMonth.value) params.month = Number(filterMonth.value)
    if (scope.value !== 'self' && selectedLsys.value) params.lsys = selectedLsys.value
    const res = await getFullAttendanceExport(params)
    if (!res?.success || !res.byDept) {
      alert('获取满勤名单失败')
      return
    }
    const wb = XLSX.utils.book_new()
    const allDetails = []
    for (const d of res.byDept || []) {
      for (const p of d.fullDetails || []) {
        const n = (p.name || '').trim()
        if (n) allDetails.push(p)
      }
    }
    allDetails.sort((a, b) => (a.name || '').localeCompare(b.name || '', 'zh-Hans-CN'))
    const seen = new Set()
    const uniqueDetails = allDetails.filter((p) => {
      if (seen.has(p.name)) return false
      seen.add(p.name)
      return true
    })
    const firstHeader = ['序号', '姓名', '出勤天数', '公出天数']
    const firstRows = uniqueDetails.map((p, i) => [i + 1, p.name, p.attendDays ?? '', p.businessDays ?? ''])
    const firstSheet = XLSX.utils.aoa_to_sheet([firstHeader, ...firstRows])
    XLSX.utils.book_append_sheet(wb, firstSheet, '全员满勤名单')
    for (const dept of res.byDept || []) {
      const details = dept.fullDetails || []
      const nameHeader = ['序号', '姓名', '出勤天数', '公出天数']
      const nameRows = details.map((p, i) => [i + 1, p.name, p.attendDays ?? '', p.businessDays ?? ''])
      const sheet = XLSX.utils.aoa_to_sheet([nameHeader, ...nameRows])
      const sheetName = (dept.lsys || '科室').slice(0, 31)
      XLSX.utils.book_append_sheet(wb, sheet, sheetName)
    }
    const monthLabel = filterMonth.value ? `${filterMonth.value}月` : '全年'
    const fileName = `满勤名单_${filterYear.value}年${monthLabel}.xlsx`
    XLSX.writeFile(wb, fileName)
  } catch (e) {
    console.error(e)
    alert('导出失败，请稍后重试')
  } finally {
    fullAttendanceExportLoading.value = false
  }
}

onMounted(async () => {
  const user = JSON.parse(localStorage.getItem('userInfo') || '{}')
  const name = (user.name || user.userName || '').trim()
  if (!name) {
    router.replace('/login')
    return
  }
  currentUserName.value = name
  try {
    const permRes = await getOvertimePayPermission({ name })
    canView.value = !!(permRes?.canView)
    scope.value = permRes?.scope || 'self'
    scopeLsys.value = (permRes?.lsys || '').trim()
    if (!canView.value) return
    if (scope.value === 'all') {
      const listRes = await getDeptLsysList()
      lsysList.value = (listRes?.list || []).filter(Boolean)
      selectedLsys.value = ''
    } else if (scope.value === 'lsys' && scopeLsys.value) {
      lsysList.value = [scopeLsys.value]
      selectedLsys.value = scopeLsys.value
    } else {
      lsysList.value = []
      selectedLsys.value = ''
    }
  } catch (e) {
    canView.value = false
  }
})
</script>

<style scoped>
.overtime-pay-page {
  min-height: 100vh;
  background: var(--color-bg-layout);
}
.overtime-pay-page .container {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0 0 var(--spacing-xxl);
}
.card {
  background: var(--color-bg-container);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
  box-shadow: var(--shadow-card);
}
.no-permission-content {
  text-align: center;
  padding: var(--spacing-xxl);
}
.no-permission-content p {
  margin-bottom: var(--spacing-lg);
  color: var(--color-text-secondary);
}
.filter-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}
.filter-fields {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: var(--spacing-lg);
}
.filter-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--spacing-md);
  width: 100%;
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-border-lighter);
}
.filter-toolbar-exports {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--spacing-sm);
  margin-left: auto;
}
.toolbar-exports-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  margin-right: var(--spacing-xs);
  white-space: nowrap;
}
.form-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}
.form-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
.form-select,
.form-date {
  min-width: 120px;
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
}
.form-date {
  min-width: 140px;
}
.form-item--disabled .form-label {
  opacity: 0.6;
}
.form-item--disabled .form-select {
  opacity: 0.55;
  cursor: not-allowed;
}
.scope-self-label {
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
.btn {
  height: 40px;
  padding: 0 var(--spacing-lg);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  border: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  white-space: nowrap;
}
.btn-primary {
  background: var(--color-primary);
  color: white;
}
.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.btn-outline {
  background: transparent;
  border: 1px solid var(--color-primary);
  color: var(--color-primary);
}
.btn-outline:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.filter-hint {
  margin-top: var(--spacing-sm);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}
.loading-icon {
  width: 18px;
  height: 18px;
  vertical-align: middle;
  margin-right: var(--spacing-xs);
}
.section-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--spacing-md);
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}
.section-icon {
  width: 24px;
  height: 24px;
  color: var(--color-primary);
}
.section-desc {
  margin-bottom: var(--spacing-lg);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
.subsection-title {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  margin: var(--spacing-lg) 0 var(--spacing-sm);
}
.subsection-title:first-of-type {
  margin-top: 0;
}
.table-wrap {
  margin-bottom: var(--spacing-lg);
}
.data-table {
  width: 100%;
  border-collapse: collapse;
}
.data-table th,
.data-table td {
  padding: var(--spacing-md);
  text-align: left;
  border-bottom: 1px solid var(--color-border-lighter);
}
.data-table th {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  background: var(--color-bg-spotlight);
}
.data-table td {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}
.pay-cell {
  font-weight: var(--font-weight-medium);
  color: var(--color-primary);
}
.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-secondary);
}
.init-hint {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-secondary);
}

@media (max-width: 768px) {
  .filter-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  .filter-toolbar-exports {
    margin-left: 0;
    width: 100%;
  }
  .filter-toolbar .btn-primary {
    width: 100%;
  }
  .filter-toolbar-exports .btn-outline {
    flex: 1 1 calc(50% - var(--spacing-xs));
    min-width: 0;
  }
}
</style>
