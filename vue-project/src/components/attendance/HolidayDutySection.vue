<template>
  <div class="holiday-duty-block section card duty-section">
    <h2 class="section-title">
      <svg class="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="4" width="18" height="17" rx="2"/>
        <path d="M16 2v4M8 2v4M3 10h18M9 15l2 2 4-4"/>
      </svg>
      假期值班出勤核查
    </h2>
    <p class="section-desc">
      按排班表中的白班、夜班核对打卡记录。白班 08:00-17:00，夜班 17:00-22:00；夜班当日缺少离开记录时按 24:00 离开校验。
    </p>

    <div class="filter-bar duty-filter-bar">
      <div class="form-item">
        <label class="form-label">科室</label>
        <select v-model="dutyLsys" class="form-select">
          <option value="">全部科室</option>
          <option v-for="d in lsysList" :key="'duty-' + d" :value="d">{{ d }}</option>
        </select>
      </div>
      <div class="form-item">
        <label class="form-label">开始日期</label>
        <input v-model="dutyStartDate" type="date" class="form-input" />
      </div>
      <div class="form-item">
        <label class="form-label">结束日期</label>
        <input v-model="dutyEndDate" type="date" class="form-input" />
      </div>
      <div class="form-item form-actions">
        <button class="btn btn-primary" type="button" @click="fetchDutyAttendance" :disabled="dutyLoading">
          <svg v-if="dutyLoading" class="loading-icon" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="31.4" stroke-linecap="round">
              <animateTransform attributeName="transform" type="rotate" dur="1s" from="0 12 12" to="360 12 12" repeatCount="indefinite"/>
            </circle>
          </svg>
          {{ dutyLoading ? '核查中...' : '核查' }}
        </button>
        <button class="btn btn-outline-duty" type="button" @click="exportDutyAttendance" :disabled="dutyExporting || dutyLoading">
          {{ dutyExporting ? '导出中...' : '导出 Excel' }}
        </button>
      </div>
    </div>

    <template v-if="dutyFetched">
      <div class="duty-summary-grid">
        <div class="duty-metric">
          <span class="metric-label">应出勤</span>
          <strong>{{ dutySummary.scheduled || 0 }}</strong>
          <span class="metric-sub">人次</span>
        </div>
        <div class="duty-metric metric-ok">
          <span class="metric-label">已出勤</span>
          <strong>{{ dutySummary.attended || 0 }}</strong>
          <span class="metric-sub">{{ percentText(dutySummary.attendanceRate) }}</span>
        </div>
        <div class="duty-metric metric-warn">
          <span class="metric-label">迟到</span>
          <strong>{{ dutySummary.late || 0 }}</strong>
          <span class="metric-sub">{{ percentText(dutySummary.lateRate) }}</span>
        </div>
        <div class="duty-metric metric-warn">
          <span class="metric-label">早退</span>
          <strong>{{ dutySummary.earlyLeave || 0 }}</strong>
          <span class="metric-sub">{{ percentText(dutySummary.earlyLeaveRate) }}</span>
        </div>
        <div class="duty-metric metric-danger">
          <span class="metric-label">缺勤</span>
          <strong>{{ dutySummary.absent || 0 }}</strong>
          <span class="metric-sub">{{ percentText(dutySummary.absentRate) }}</span>
        </div>
      </div>

      <div class="duty-content-grid">
        <div class="duty-panel">
          <h3 class="chart-title">按日期汇总</h3>
          <div class="table-wrap compact-table-wrap">
            <table class="detail-table duty-table">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>应出勤</th>
                  <th>已出勤</th>
                  <th>出勤率</th>
                  <th>出勤人员占比</th>
                  <th>出勤人员占比（含境内公出）</th>
                  <th>迟到</th>
                  <th>早退</th>
                  <th>缺勤</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="d in dutyByDate" :key="d.date">
                  <td>{{ d.date }}</td>
                  <td>{{ d.scheduled }}</td>
                  <td>{{ d.attended }}</td>
                  <td>{{ percentText(d.attendanceRate) }}</td>
                  <td>{{ d.attendedPeople || 0 }} / {{ d.memberTotal || 0 }}（{{ percentText(d.memberAttendanceRate) }}）</td>
                  <td>{{ d.attendedPeopleWithTrip || 0 }} / {{ d.memberTotal || 0 }}（{{ percentText(d.memberAttendanceRateWithTrip) }}）</td>
                  <td>{{ d.late }}</td>
                  <td>{{ d.earlyLeave }}</td>
                  <td>{{ d.absent }}</td>
                </tr>
                <tr v-if="!dutyByDate.length">
                  <td colspan="9" class="table-empty-cell">所选范围暂无值班排班</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="duty-panel">
          <h3 class="chart-title">异常明细</h3>
          <div class="table-wrap detail-table-wrap">
            <table class="detail-table duty-table">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>科室</th>
                  <th>姓名</th>
                  <th>班次</th>
                  <th>首入</th>
                  <th>末出</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in dutyExceptionDetails" :key="r.date + r.dept + r.name + r.shiftType">
                  <td>{{ r.date }}</td>
                  <td>{{ r.dept }}</td>
                  <td>{{ r.name }}</td>
                  <td>{{ r.shiftType }} {{ r.expectedStart }}-{{ r.expectedEnd }}</td>
                  <td>{{ r.firstIn || '-' }}</td>
                  <td>{{ r.lastOut || '-' }}</td>
                  <td><span :class="['status-pill', 'status-' + r.status]">{{ r.statusText }}</span></td>
                </tr>
                <tr v-if="!dutyExceptionDetails.length">
                  <td colspan="7" class="table-empty-cell">暂无迟到、早退或缺勤</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import {
  getDeptLsysList,
  getHolidayDutyAttendanceCheck,
  exportHolidayDutyAttendanceCheck,
} from '@/api/attendance'

const props = defineProps({
  /** 父页已加载的科室列表（如考勤纪律页），传入则不再请求 */
  externalLsysList: { type: Array, default: null },
})

function getDefaultDutyRange() {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth() + 1
  if (month >= 10) {
    return { start: `${year}-10-01`, end: `${year}-10-07` }
  }
  return { start: `${year}-05-01`, end: `${year}-05-05` }
}

const defaultDutyRange = getDefaultDutyRange()
const dutyLsys = ref('')
const dutyStartDate = ref(defaultDutyRange.start)
const dutyEndDate = ref(defaultDutyRange.end)
const dutyLoading = ref(false)
const dutyExporting = ref(false)
const dutyFetched = ref(false)
const dutySummary = ref({})
const dutyByDate = ref([])
const dutyDetails = ref([])
const lsysList = ref([])

const dutyExceptionDetails = computed(() => dutyDetails.value.filter(r => r.status !== 'normal'))

function percentText(rate) {
  const n = Number(rate || 0)
  return `${(n * 100).toFixed(1)}%`
}

async function fetchDutyAttendance() {
  if (!dutyStartDate.value || !dutyEndDate.value) return
  dutyLoading.value = true
  dutyFetched.value = true
  try {
    const params = {
      start_date: dutyStartDate.value,
      end_date: dutyEndDate.value,
    }
    if (dutyLsys.value) params.lsys = dutyLsys.value
    const res = await getHolidayDutyAttendanceCheck(params)
    if (res.success) {
      dutySummary.value = res.summary || {}
      dutyByDate.value = res.byDate || []
      dutyDetails.value = res.details || []
    }
  } catch (e) {
    console.error('假期值班出勤核查失败:', e)
    dutySummary.value = {}
    dutyByDate.value = []
    dutyDetails.value = []
  } finally {
    dutyLoading.value = false
  }
}

async function exportDutyAttendance() {
  if (!dutyStartDate.value || !dutyEndDate.value) return
  dutyExporting.value = true
  try {
    const params = {
      start_date: dutyStartDate.value,
      end_date: dutyEndDate.value,
    }
    if (dutyLsys.value) params.lsys = dutyLsys.value
    const blob = await exportHolidayDutyAttendanceCheck(params)
    if (blob instanceof Blob) {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const scope = dutyLsys.value || '全部科室'
      a.download = `${scope}_${dutyStartDate.value}_${dutyEndDate.value}_假期值班出勤核查.xlsx`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
  } catch (e) {
    console.error('假期值班出勤核查导出失败:', e)
  } finally {
    dutyExporting.value = false
  }
}

async function loadLsysList() {
  if (props.externalLsysList?.length) {
    lsysList.value = props.externalLsysList.filter(v => v && !['其他部门员工', '其他部门成员'].includes(String(v).trim()))
    return
  }
  try {
    const listRes = await getDeptLsysList()
    if (listRes.success && listRes.list?.length) {
      lsysList.value = listRes.list.filter(v => v && !['其他部门员工', '其他部门成员'].includes(v.trim()))
    }
  } catch { /* ignore */ }
}

watch(
  () => props.externalLsysList,
  (v) => {
    if (v?.length) {
      lsysList.value = v.filter(x => x && !['其他部门员工', '其他部门成员'].includes(String(x).trim()))
    }
  },
  { deep: true },
)

onMounted(() => {
  loadLsysList()
})
</script>

<style scoped>
.holiday-duty-block.section {
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
}

.card {
  background: var(--color-bg-container);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
}

.section-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-sm);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.section-icon { width: 24px; height: 24px; color: var(--color-primary); flex-shrink: 0; }

.section-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0 0 var(--spacing-lg);
}

.filter-bar {
  display: flex;
  gap: var(--spacing-lg);
  align-items: flex-end;
  flex-wrap: wrap;
  margin-bottom: var(--spacing-xl);
  padding: var(--spacing-lg);
  background: var(--color-bg-spotlight, #f9fafb);
  border-radius: var(--radius-base);
}

.duty-filter-bar {
  align-items: flex-end;
}

.form-item { display: flex; flex-direction: column; gap: var(--spacing-xs); }

.form-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.form-select {
  height: 36px;
  padding: 0 var(--spacing-md);
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  background: var(--color-bg-container);
  min-width: 120px;
}

.form-input {
  height: 36px;
  padding: 0 var(--spacing-md);
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  background: var(--color-bg-container);
  min-width: 150px;
}

.form-actions {
  flex-direction: row;
  align-items: flex-end;
  gap: var(--spacing-sm);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  padding: 8px 16px;
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  border: none;
}

.btn-primary { background: var(--color-primary); color: white; }
.btn-primary:hover:not(:disabled) { filter: brightness(1.05); }
.btn-primary:disabled { opacity: 0.7; cursor: not-allowed; }

.btn-outline-duty {
  color: var(--color-primary);
  background: var(--color-bg-container);
  border: 1px solid var(--color-primary);
}
.btn-outline-duty:hover:not(:disabled) {
  background: var(--color-primary-lightest, #eef2ff);
}
.btn-outline-duty:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.loading-icon { width: 16px; height: 16px; }

.chart-title {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  margin: 0 0 var(--spacing-md);
  color: var(--color-text-primary);
}

.duty-section {
  border: 1px solid var(--color-border-lighter);
}

.duty-summary-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(140px, 1fr));
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);
}

.duty-metric {
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--radius-base);
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-container);
  min-height: 96px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
}

.duty-metric strong {
  font-size: 30px;
  line-height: 1;
  color: var(--color-text-primary);
}

.metric-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.metric-sub {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.metric-ok strong { color: #059669; }
.metric-warn strong { color: #d97706; }
.metric-danger strong { color: #dc2626; }

.duty-content-grid {
  display: grid;
  grid-template-columns: minmax(360px, 0.9fr) minmax(520px, 1.4fr);
  gap: var(--spacing-xl);
  align-items: start;
}

.duty-panel {
  min-width: 0;
}

.table-wrap {
  width: 100%;
  overflow: auto;
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--radius-base);
}

.compact-table-wrap {
  max-height: 420px;
}

.detail-table-wrap {
  max-height: 520px;
}

.detail-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-xs);
}

.detail-table th {
  text-align: left;
  padding: 4px 8px;
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border-lighter);
}

.detail-table td {
  padding: 4px 8px;
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-border-lighter);
}

.duty-table {
  min-width: 100%;
  background: var(--color-bg-container);
}

.duty-table th {
  position: sticky;
  top: 0;
  background: var(--color-bg-spotlight, #f9fafb);
  z-index: 1;
}

.table-empty-cell {
  text-align: center;
  color: var(--color-text-tertiary);
  padding: var(--spacing-lg) !important;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: var(--font-size-xs);
  font-weight: 600;
  white-space: nowrap;
}

.status-normal {
  color: #047857;
  background: #d1fae5;
}

.status-late,
.status-early_leave,
.status-late_early {
  color: #92400e;
  background: #fef3c7;
}

.status-absent {
  color: #991b1b;
  background: #fee2e2;
}

@media (max-width: 960px) {
  .duty-summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .duty-content-grid { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .filter-bar { flex-direction: column; align-items: stretch; }
  .duty-summary-grid { grid-template-columns: 1fr; }
}
</style>
