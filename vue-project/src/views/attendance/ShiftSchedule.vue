<template>
  <div class="shift-page">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">排班管理</h1>
          <p class="header-subtitle">以班次为维度，按月为科室人员排班</p>
        </div>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar card">
      <div class="toolbar-left">
        <label class="toolbar-label">科室</label>
        <select v-model="selectedDept" class="toolbar-select" @change="loadSchedule">
          <option value="">请选择科室</option>
          <option v-for="d in departments" :key="d" :value="d">{{ d }}</option>
        </select>
        <button type="button" class="btn btn-sm" @click="prevMonth">&lt;</button>
        <span class="toolbar-month">{{ year }}年{{ month }}月</span>
        <button type="button" class="btn btn-sm" @click="nextMonth">&gt;</button>
      </div>
      <div class="toolbar-right">
        <button type="button" class="btn btn-outline btn-sm" @click="showConfigPanel = !showConfigPanel" title="排班规则配置">
          ⚙ 配置
        </button>
        <button type="button" class="btn btn-outline btn-sm" @click="handleCopyLastMonth" :disabled="saving">复制上月</button>
        <button type="button" class="btn btn-primary btn-sm" @click="handleAutoSchedule" :disabled="saving">自动排班</button>
        <button type="button" class="btn btn-primary btn-sm" @click="handleSave" :disabled="saving || !dirty">
          {{ saving ? '保存中…' : '保存排班' }}
        </button>
      </div>
    </div>

    <!-- 配置面板 -->
    <div v-if="showConfigPanel" class="config-panel card">
      <h3>排班规则配置 <span class="config-dept">{{ selectedDept || '—' }}</span></h3>
      <div class="config-form">
        <div class="config-item">
          <label>工作日夜班人数</label>
          <input type="number" v-model.number="config.workday_night" min="0" max="50">
        </div>
        <div class="config-item">
          <label>周末白班人数</label>
          <input type="number" v-model.number="config.weekend_day" min="0" max="50">
        </div>
        <div class="config-item">
          <label>周末夜班人数</label>
          <input type="number" v-model.number="config.weekend_night" min="0" max="50">
        </div>
        <button type="button" class="btn btn-primary btn-sm" @click="handleSaveConfig">保存配置</button>
      </div>
    </div>

    <!-- 图例 -->
    <div class="legend">
      <span class="legend-item"><span class="legend-dot legend-day"></span>白班 8:00-17:00</span>
      <span class="legend-item"><span class="legend-dot legend-night"></span>夜班 17:00-22:00</span>
      <span class="legend-item"><span class="legend-dot legend-rest"></span>休息</span>
      <span class="legend-sep">|</span>
      <span class="legend-hint">点击单元格切换班次</span>
    </div>

    <!-- 排班网格 -->
    <div class="schedule-wrap card" v-if="employees.length">
      <div class="schedule-scroll">
        <table class="schedule-table">
          <thead>
            <tr>
              <th class="col-name sticky-col">姓名</th>
              <th class="col-total sticky-col2">
                <div>统计</div>
                <div class="th-sub">白/夜</div>
              </th>
              <th
                v-for="d in dates"
                :key="d.date"
                class="col-day"
                :class="{ 'col-weekend': !d.isWorkday, 'col-today': d.date === todayStr }"
              >
                <div class="th-day">{{ d.date.slice(8) }}</div>
                <div class="th-weekday">{{ d.label }}</div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="emp in employees" :key="emp">
              <td class="col-name sticky-col">{{ emp }}</td>
              <td class="col-total sticky-col2">
                <span class="stat-day">{{ empStats[emp]?.day || 0 }}</span>/<span class="stat-night">{{ empStats[emp]?.night || 0 }}</span>
              </td>
              <td
                v-for="d in dates"
                :key="d.date"
                class="col-day cell"
                :class="cellClass(emp, d)"
                @click="cycleShift(emp, d.date)"
              >
                <span class="cell-text">{{ cellLabel(emp, d.date) }}</span>
              </td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="summary-row">
              <td class="col-name sticky-col"><strong>当日合计</strong></td>
              <td class="col-total sticky-col2">—</td>
              <td v-for="d in dates" :key="d.date" class="col-day">
                <div class="summary-cell">
                  <span class="stat-day" title="白班人数">{{ daySummary[d.date]?.day || 0 }}</span>
                  <span class="stat-night" title="夜班人数">{{ daySummary[d.date]?.night || 0 }}</span>
                </div>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
    <div v-else-if="selectedDept && !loading" class="empty-state card">
      <p>该科室暂无在职员工数据</p>
    </div>
    <div v-else-if="loading" class="empty-state card"><p>加载中…</p></div>
    <div v-else class="empty-state card"><p>请先选择科室</p></div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { getDepartments, getShiftConfig, saveShiftConfig, getSchedule, saveSchedule, autoSchedule, copyLastMonth } from '@/api/shift'

const now = new Date()
const year = ref(now.getFullYear())
const month = ref(now.getMonth() + 1)
const todayStr = now.toISOString().slice(0, 10)

const departments = ref([])
const selectedDept = ref('')
const employees = ref([])
const dates = ref([])
const scheduleData = reactive({})
const loading = ref(false)
const saving = ref(false)
const dirty = ref(false)
const showConfigPanel = ref(false)
const config = reactive({ workday_night: 2, weekend_day: 2, weekend_night: 2 })

function getCurrentUser() {
  try { return (JSON.parse(localStorage.getItem('userInfo') || '{}').name || '').trim() }
  catch { return '' }
}

onMounted(async () => {
  try {
    const res = await getDepartments()
    departments.value = res?.departments || []
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
    const dept = (userInfo.dept || userInfo.department || '').trim()
    if (dept && departments.value.includes(dept)) {
      selectedDept.value = dept
      await loadSchedule()
    }
  } catch (e) {
    console.error('加载科室列表失败:', e)
  }
})

async function loadSchedule() {
  if (!selectedDept.value) { employees.value = []; dates.value = []; return }
  loading.value = true
  dirty.value = false
  try {
    const [schRes, cfgRes] = await Promise.all([
      getSchedule({ department: selectedDept.value, year: year.value, month: month.value }),
      getShiftConfig({ department: selectedDept.value }),
    ])
    employees.value = schRes?.employees || []
    dates.value = schRes?.dates || []
    Object.keys(scheduleData).forEach(k => delete scheduleData[k])
    const sch = schRes?.schedule || {}
    for (const [emp, dayMap] of Object.entries(sch)) {
      scheduleData[emp] = { ...dayMap }
    }
    const c = cfgRes?.data || {}
    config.workday_night = c.workday_night ?? 2
    config.weekend_day = c.weekend_day ?? 2
    config.weekend_night = c.weekend_night ?? 2
  } catch (e) {
    console.error('加载排班失败:', e)
  } finally {
    loading.value = false
  }
}

function prevMonth() {
  if (month.value === 1) { year.value--; month.value = 12 }
  else month.value--
  loadSchedule()
}
function nextMonth() {
  if (month.value === 12) { year.value++; month.value = 1 }
  else month.value++
  loadSchedule()
}

const SHIFT_CYCLE = ['白班', '夜班', '休息', '']
function cycleShift(emp, dateStr) {
  if (!scheduleData[emp]) scheduleData[emp] = {}
  const cur = scheduleData[emp][dateStr] || ''
  const idx = SHIFT_CYCLE.indexOf(cur)
  const next = SHIFT_CYCLE[(idx + 1) % SHIFT_CYCLE.length]
  scheduleData[emp][dateStr] = next
  dirty.value = true
}

function cellLabel(emp, dateStr) {
  const v = scheduleData[emp]?.[dateStr] || ''
  if (v === '白班') return '白'
  if (v === '夜班') return '夜'
  if (v === '休息') return '休'
  return ''
}

function cellClass(emp, d) {
  const v = scheduleData[emp]?.[d.date] || ''
  return {
    'cell-day': v === '白班',
    'cell-night': v === '夜班',
    'cell-rest': v === '休息',
    'cell-empty': !v,
    'col-weekend': !d.isWorkday,
    'col-today': d.date === todayStr,
  }
}

const empStats = computed(() => {
  const stats = {}
  for (const emp of employees.value) {
    let day = 0, night = 0
    const dayMap = scheduleData[emp] || {}
    for (const v of Object.values(dayMap)) {
      if (v === '白班') day++
      else if (v === '夜班') night++
    }
    stats[emp] = { day, night }
  }
  return stats
})

const daySummary = computed(() => {
  const summary = {}
  for (const d of dates.value) {
    let day = 0, night = 0
    for (const emp of employees.value) {
      const v = scheduleData[emp]?.[d.date] || ''
      if (v === '白班') day++
      else if (v === '夜班') night++
    }
    summary[d.date] = { day, night }
  }
  return summary
})

async function handleSave() {
  if (!selectedDept.value) return
  saving.value = true
  try {
    await saveSchedule({
      department: selectedDept.value,
      year: year.value,
      month: month.value,
      schedule: { ...scheduleData },
      current_user: getCurrentUser(),
    })
    dirty.value = false
    alert('排班已保存')
  } catch (e) {
    alert(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleAutoSchedule() {
  if (!selectedDept.value) return
  if (!confirm('自动排班将覆盖当前月排班数据，确认？')) return
  saving.value = true
  try {
    const res = await autoSchedule({
      department: selectedDept.value,
      year: year.value,
      month: month.value,
      current_user: getCurrentUser(),
    })
    if (res?.success) {
      await loadSchedule()
      alert(res.message || '自动排班完成')
    } else {
      alert(res?.message || '自动排班失败')
    }
  } catch (e) {
    alert(e?.response?.data?.detail || '自动排班失败')
  } finally {
    saving.value = false
  }
}

async function handleCopyLastMonth() {
  if (!selectedDept.value) return
  if (!confirm('复制上月排班将覆盖当月已有数据，确认？')) return
  saving.value = true
  try {
    const res = await copyLastMonth({
      department: selectedDept.value,
      year: year.value,
      month: month.value,
      current_user: getCurrentUser(),
    })
    if (res?.success) {
      await loadSchedule()
      alert(res.message || '已复制')
    } else {
      alert(res?.message || '复制失败')
    }
  } catch (e) {
    alert(e?.response?.data?.detail || '复制失败')
  } finally {
    saving.value = false
  }
}

async function handleSaveConfig() {
  if (!selectedDept.value) return
  try {
    await saveShiftConfig({
      department: selectedDept.value,
      workday_night: config.workday_night,
      weekend_day: config.weekend_day,
      weekend_night: config.weekend_night,
      current_user: getCurrentUser(),
    })
    alert('配置已保存')
  } catch (e) {
    alert('保存配置失败')
  }
}
</script>

<style scoped>
.shift-page {
  width: 100%;
  max-width: none;
  padding: 0 0 var(--spacing-xl);
}
.page-header { margin-bottom: var(--spacing-lg); }
.header-title { font-size: var(--font-size-xl); font-weight: var(--font-weight-bold); margin: 0; }
.header-subtitle { font-size: var(--font-size-sm); color: var(--color-text-tertiary); margin: 4px 0 0; }

.card {
  background: white;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-lighter);
  padding: var(--spacing-md) var(--spacing-lg);
  margin-bottom: var(--spacing-md);
}

/* 工具栏 */
.toolbar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.toolbar-left, .toolbar-right { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.toolbar-label { font-size: var(--font-size-sm); color: var(--color-text-secondary); }
.toolbar-select { padding: 4px 8px; border: 1px solid var(--color-border-base); border-radius: var(--radius-sm); font-size: var(--font-size-sm); }
.toolbar-month { font-weight: var(--font-weight-bold); font-size: var(--font-size-base); min-width: 100px; text-align: center; }
.btn { cursor: pointer; border: 1px solid var(--color-border-base); background: white; border-radius: var(--radius-sm); padding: 4px 12px; font-size: var(--font-size-sm); transition: all .15s; }
.btn:hover { background: var(--color-primary-lightest, #eff6ff); }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn-primary { background: var(--color-primary); color: white; border-color: var(--color-primary); }
.btn-primary:hover { opacity: .9; }
.btn-outline { background: white; border-color: var(--color-primary); color: var(--color-primary); }
.btn-sm { padding: 4px 10px; font-size: 13px; }

/* 配置面板 */
.config-panel h3 { margin: 0 0 12px; font-size: var(--font-size-base); }
.config-dept { color: var(--color-primary); margin-left: 8px; }
.config-form { display: flex; align-items: flex-end; gap: 16px; flex-wrap: wrap; }
.config-item { display: flex; flex-direction: column; gap: 4px; }
.config-item label { font-size: 12px; color: var(--color-text-secondary); }
.config-item input { width: 80px; padding: 4px 8px; border: 1px solid var(--color-border-base); border-radius: var(--radius-sm); text-align: center; }

/* 图例 */
.legend { display: flex; align-items: center; gap: 16px; margin-bottom: var(--spacing-sm); font-size: 13px; color: var(--color-text-secondary); flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 4px; }
.legend-dot { width: 14px; height: 14px; border-radius: 3px; display: inline-block; }
.legend-day { background: #dbeafe; border: 1px solid #93c5fd; }
.legend-night { background: #fef3c7; border: 1px solid #fbbf24; }
.legend-rest { background: #f3f4f6; border: 1px solid #d1d5db; }
.legend-sep { color: #d1d5db; }
.legend-hint { font-style: italic; color: #9ca3af; }

/* 排班网格 */
.schedule-wrap { padding: 0; overflow: hidden; }
.schedule-scroll { overflow-x: auto; overflow-y: auto; max-height: calc(100vh - 300px); }
.schedule-table { border-collapse: collapse; width: max-content; min-width: 100%; font-size: 13px; }
.schedule-table th,
.schedule-table td { border: 1px solid #e5e7eb; text-align: center; white-space: nowrap; }
.schedule-table thead th {
  background: #f8fafc;
  position: sticky;
  top: 0;
  z-index: 3;
  padding: 4px 2px;
  font-weight: 500;
}
.th-day { font-size: 14px; font-weight: 600; line-height: 1.2; }
.th-weekday { font-size: 11px; color: #9ca3af; }
.th-sub { font-size: 11px; color: #9ca3af; font-weight: normal; }

.col-name { min-width: 72px; max-width: 90px; padding: 6px 8px; font-weight: 500; text-align: left; }
.col-total { min-width: 50px; padding: 4px 6px; font-size: 12px; }
.col-day { width: 36px; min-width: 36px; max-width: 36px; padding: 0; }
.col-weekend { background: #fafaf9; }
.col-today { box-shadow: inset 0 0 0 2px var(--color-primary); }

.sticky-col {
  position: sticky;
  left: 0;
  z-index: 4;
  background: white;
}
.sticky-col2 {
  position: sticky;
  left: 90px;
  z-index: 4;
  background: white;
}
thead .sticky-col,
thead .sticky-col2 {
  z-index: 5;
  background: #f8fafc;
}

/* 单元格 */
.cell { cursor: pointer; height: 34px; transition: background .1s; user-select: none; }
.cell:hover { filter: brightness(.95); }
.cell-text { display: inline-block; width: 100%; line-height: 34px; font-weight: 600; font-size: 12px; }
.cell-day { background: #dbeafe; color: #1d4ed8; }
.cell-night { background: #fef3c7; color: #92400e; }
.cell-rest { background: #f3f4f6; color: #9ca3af; }
.cell-empty { background: white; color: transparent; }

.stat-day { color: #2563eb; font-weight: 600; }
.stat-night { color: #d97706; font-weight: 600; }

/* 合计行 */
.summary-row td { background: #f8fafc; font-size: 12px; padding: 4px 2px; }
.summary-cell { display: flex; flex-direction: column; align-items: center; line-height: 1.2; gap: 1px; }

.empty-state { text-align: center; padding: var(--spacing-xxl); color: var(--color-text-tertiary); }

@media (max-width: 768px) {
  .toolbar { flex-direction: column; align-items: flex-start; }
  .schedule-scroll { max-height: calc(100vh - 360px); }
}
</style>
