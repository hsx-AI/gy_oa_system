<template>
  <div class="statistics-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">统计汇总</h1>
          <p class="header-subtitle">按员工查看年度加班、请假、公出数据汇总，支持月度趋势与明细筛选</p>
        </div>
      </div>
    </div>

    <div class="container">
      <!-- 查询条件 -->
      <div class="query-section card">
        <div class="query-form">
          <div class="form-item">
            <label class="form-label">员工姓名</label>
            <!-- 1级：仅自己，固定 -->
            <input
              v-if="permLevel === 1"
              :value="queryParams.name"
              type="text"
              class="form-input"
              readonly
              placeholder="仅可查看本人"
            />
            <!-- 2级：科室下属，下拉选择（含全员） -->
            <select
              v-else-if="permLevel === 2"
              v-model="queryParams.name"
              name="statisticsNameSelect"
              autocomplete="on"
              class="form-select"
              :disabled="!deptEmployeeList.length"
            >
              <option value="">全员</option>
              <option v-for="n in deptEmployeeList" :key="n" :value="n">{{ n }}</option>
            </select>
            <!-- 3级：全部，输入查询 -->
            <input
              v-else
              v-model="queryParams.name"
              type="text"
              name="statisticsName"
              autocomplete="name"
              class="form-input"
              placeholder="输入姓名查询"
            />
          </div>
          <div class="form-item">
            <label class="form-label">查询年份</label>
            <select v-model="queryParams.year" name="statisticsYear" autocomplete="on" class="form-select">
              <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option>
            </select>
          </div>
          <div class="form-item form-actions">
            <button class="btn btn-primary" @click="fetchData" :disabled="loading">
              <svg v-if="loading" class="loading-icon" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="31.4" stroke-linecap="round">
                  <animateTransform attributeName="transform" type="rotate" dur="1s" from="0 12 12" to="360 12 12" repeatCount="indefinite"/>
                </circle>
              </svg>
              <span>{{ loading ? '查询中...' : '查询统计' }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- 年度汇总卡片 -->
      <div v-if="yearTotal" class="summary-section">
        <h2 class="section-title">
          <svg class="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 3v18h18M7 16l4-4 4 4 6-6"/>
          </svg>
          {{ queryParams.year }}年度汇总{{ isAllStaffQuery ? '（全员）' : '' }}
        </h2>
        <p class="section-hint">切换年份可对比历年数据；下方表格支持按月份筛选明细。</p>
        <div class="summary-cards">
          <div class="summary-card overtime-card">
            <div class="summary-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
            </div>
            <div class="summary-content">
              <div class="summary-label">加班统计</div>
              <div class="summary-main">
                <span class="summary-value">{{ yearTotal.overtime.hours }}</span>
                <span class="summary-unit">小时</span>
              </div>
              <div class="summary-sub">共 {{ yearTotal.overtime.count }} 次加班</div>
            </div>
          </div>
          
          <div class="summary-card leave-card">
            <div class="summary-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                <line x1="16" y1="2" x2="16" y2="6"/>
                <line x1="8" y1="2" x2="8" y2="6"/>
                <line x1="3" y1="10" x2="21" y2="10"/>
                <path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01"/>
              </svg>
            </div>
            <div class="summary-content">
              <div class="summary-label">请假统计</div>
              <div class="summary-main">
                <span class="summary-value">{{ yearTotal.leave.days }}</span>
                <span class="summary-unit">天</span>
              </div>
              <div class="summary-sub">共 {{ yearTotal.leave.count }} 次请假，{{ yearTotal.leave.hours }} 小时</div>
            </div>
          </div>

          <div class="summary-card business-trip-card">
            <div class="summary-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/>
                <circle cx="12" cy="10" r="3"/>
              </svg>
            </div>
            <div class="summary-content">
              <div class="summary-label">公出统计</div>
              <div class="summary-main">
                <span class="summary-value">{{ yearTotal.business_trip?.days ?? 0 }}</span>
                <span class="summary-unit">天</span>
              </div>
              <div class="summary-sub">共 {{ yearTotal.business_trip?.count ?? 0 }} 次公出</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 月度趋势图表：与领导人看板科室横向对比同形式，按类型筛选展示 -->
      <div v-if="monthlyData.length > 0" class="chart-section card">
        <h2 class="section-title">
          <svg class="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 20V10M12 20V4M6 20v-6"/>
          </svg>
          月度统计趋势
        </h2>
        <div class="chart-filter-row">
          <label class="chart-filter-label">展示</label>
          <div class="chart-type-tabs">
            <button
              v-for="t in trendChartTypes"
              :key="t.type"
              :class="['tab-btn', 'tab-btn-sm', { active: trendChartType === t.type }]"
              @click="trendChartType = t.type"
            >
              {{ t.label }}{{ t.unit }}
            </button>
          </div>
        </div>
        <div class="chart-container">
          <div class="bar-chart bar-chart-single">
            <div v-for="month in monthlyData" :key="month.month" class="bar-group">
              <div class="bar-col">
                <div
                  class="bar bar-has-value"
                  :class="trendChartBarClass"
                  :style="{ height: getBarHeight(trendChartValue(month), trendChartMax) }"
                  :title="trendChartTitle(month)"
                >
                  <span class="bar-value">{{ trendChartValue(month) }}</span>
                </div>
              </div>
              <div class="bar-label">{{ getMonthLabel(month.month) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 科室成员横向对比：仅班组长/主任/副主任可见，参考领导人看板科室横向对比 -->
      <div v-if="permLevel === 2 && permLsys && memberComparisonList.length > 0 && yearTotal" class="chart-section card">
        <h2 class="section-title">
          <svg class="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
          </svg>
          科室成员横向对比
        </h2>
        <p class="section-hint">{{ permLsys }} 各成员加班、请假、公出（{{ queryParams.year }}年全年）</p>
        <div class="chart-filter-row">
          <label class="chart-filter-label">展示</label>
          <div class="chart-type-tabs">
            <button
              v-for="t in memberCompareChartTypes"
              :key="t.type"
              :class="['tab-btn', 'tab-btn-sm', { active: memberCompareChartType === t.type }]"
              @click="memberCompareChartType = t.type"
            >
              {{ t.label }}{{ t.unit }}
            </button>
          </div>
        </div>
        <div class="chart-container">
          <div class="bar-chart bar-chart-single">
            <div v-for="row in memberCompareSorted" :key="row.name" class="bar-group">
              <div class="bar-col">
                <div
                  class="bar bar-has-value"
                  :class="memberCompareBarClass"
                  :style="{ height: getBarHeight(memberCompareValue(row), memberCompareMax) }"
                  :title="memberCompareTitle(row)"
                >
                  <span class="bar-value">{{ memberCompareValue(row) }}</span>
                </div>
              </div>
              <div class="bar-label">{{ row.name }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 详细数据表格：有汇总结果后才显示；全员时只显示提示，单人时显示三张明细表 -->
      <div v-if="yearTotal" class="tables-section">
        <!-- 全员汇总时：不拉取个人明细，提示选择具体员工 -->
        <div v-if="isAllStaffQuery" class="table-card table-card--wide card tables-hint-card">
          <div class="empty-state tables-hint">
            <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
            <p class="hint-title">当前为科室全员汇总</p>
            <p class="hint-desc">请在上方选择具体员工姓名后，再点击「查询统计」，即可查看该员工的加班、请假、公出明细。</p>
          </div>
        </div>

        <!-- 单人查询时：显示加班/请假/公出三张明细表 -->
        <template v-else>
          <!-- 加班记录表格 -->
          <div class="table-card card">
            <div class="table-header">
              <h3 class="table-title">
                <svg class="table-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
                加班明细
              </h3>
              <div class="table-filter">
                <select v-model="selectedOvertimeMonth" class="filter-select">
                  <option value="">全年</option>
                  <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
                </select>
              </div>
            </div>
            <div class="table-content">
              <table v-if="filteredOvertimeRecords.length > 0" class="data-table">
                <thead>
                  <tr>
                    <th>日期</th>
                    <th>类型</th>
                    <th>时间段</th>
                    <th>时长</th>
                    <th>说明</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="record in filteredOvertimeRecords" :key="record.id">
                    <td>{{ formatDate(record.timedate) }}</td>
                    <td>
                      <span class="type-tag overtime-type">{{ record.jiabanfs || '加班' }}</span>
                    </td>
                    <td>{{ formatTimeRange(record.timefrom, record.timeto) }}</td>
                    <td class="hours-cell">{{ record.jbf || record.tian1 || '-' }} 小时</td>
                    <td class="content-cell">{{ record.content || '-' }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="empty-state">
                <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M9 12h6M12 9v6M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <p>暂无加班记录</p>
              </div>
            </div>
          </div>

          <!-- 请假记录表格 -->
          <div class="table-card card">
            <div class="table-header">
              <h3 class="table-title">
                <svg class="table-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                  <line x1="16" y1="2" x2="16" y2="6"/>
                  <line x1="8" y1="2" x2="8" y2="6"/>
                  <line x1="3" y1="10" x2="21" y2="10"/>
                </svg>
                请假明细
              </h3>
              <div class="table-filter">
                <select v-model="selectedLeaveMonth" class="filter-select">
                  <option value="">全年</option>
                  <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
                </select>
              </div>
            </div>
            <div class="table-content">
              <table v-if="filteredLeaveRecords.length > 0" class="data-table">
                <thead>
                  <tr>
                    <th>日期</th>
                    <th>类型</th>
                    <th>时间段</th>
                    <th>时长</th>
                    <th>说明</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="record in filteredLeaveRecords" :key="record.id">
                    <td>{{ formatDate(record.timefrom) }}</td>
                    <td>
                      <span class="type-tag leave-type" :class="getLeaveTypeClass(record.qjfs)">
                        {{ record.qjfs || '请假' }}
                      </span>
                    </td>
                    <td>{{ formatDateTimeRange(record.timefrom, record.timeto) }}</td>
                    <td class="hours-cell">
                      <span v-if="record.tian && parseFloat(record.tian) > 0">{{ record.tian }} 天</span>
                      <span v-else-if="record.xiaoshi && parseFloat(record.xiaoshi) > 0">{{ record.xiaoshi }} 小时</span>
                      <span v-else>-</span>
                    </td>
                    <td class="content-cell">{{ record.content || '-' }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="empty-state">
                <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M9 12h6M12 9v6M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <p>暂无请假记录</p>
              </div>
            </div>
          </div>

          <!-- 公出记录表格（加宽，与加班、请假横向对齐） -->
          <div class="table-card table-card--wide card">
            <div class="table-header">
              <h3 class="table-title">
                <svg class="table-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/>
                  <circle cx="12" cy="10" r="3"/>
                </svg>
                公出明细
              </h3>
              <div class="table-filter">
                <select v-model="selectedBusinessTripMonth" class="filter-select">
                  <option value="">全年</option>
                  <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
                </select>
              </div>
            </div>
            <div class="table-content">
              <table v-if="filteredBusinessTripRecords.length > 0" class="data-table data-table--wide">
                <thead>
                  <tr>
                    <th>委派单位</th>
                    <th>公出地点</th>
                    <th>出发时间</th>
                    <th>实际返回时间</th>
                    <th>天数</th>
                    <th>任务</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="record in filteredBusinessTripRecords" :key="record.id">
                    <td>{{ record.wpdw || '-' }}</td>
                    <td>{{ record.gcdd || '-' }}</td>
                    <td>{{ record.gcsj || '-' }}</td>
                    <td>{{ record.sjfhtime || record.yjfhsj || '-' }}</td>
                    <td class="hours-cell">{{ record.days ?? '-' }} 天</td>
                    <td class="content-cell">{{ record.gcrw || '-' }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="empty-state">
                <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M9 12h6M12 9v6M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <p>暂无公出记录</p>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- 初始提示状态 -->
      <div v-if="!yearTotal && !loading" class="init-state card">
        <div class="init-content">
          <svg class="init-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          <h3>查看统计汇总</h3>
          <p>请输入您的姓名并选择年份，点击"查询统计"查看加班、请假、公出数据</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getMonthlySummary, getOvertimeRecords, getBusinessTripRecords, getLeaveRecords, getStatisticsPermission, getStatisticsEmployees, getDeptLeaveStats, getDeptOvertimeStats, getDeptBusinessTripStats } from '@/api/attendance'

// 权限：1=仅自己 2=科室下拉 3=全部输入
const permLevel = ref(1)
const permLsys = ref('')
const deptEmployeeList = ref([])

// 查询参数
const queryParams = ref({
  name: '',
  year: new Date().getFullYear()
})

// 状态
const loading = ref(false)
const monthlyData = ref([])
const yearTotal = ref(null)
const overtimeRecords = ref([])
const leaveRecords = ref([])
const businessTripRecords = ref([])
const selectedOvertimeMonth = ref('')
const selectedLeaveMonth = ref('')
const selectedBusinessTripMonth = ref('')
// 科室成员横向对比（班组长/主任/副主任可见）：按人合并加班/请假/公出
const deptMemberLeave = ref([])
const deptMemberOvertime = ref([])
const deptMemberTrip = ref([])

// 年份选项
const yearOptions = computed(() => {
  const currentYear = new Date().getFullYear()
  const years = []
  for (let y = currentYear; y >= currentYear - 5; y--) {
    years.push(y)
  }
  return years
})

// 计算最大值用于图表
const maxOvertimeHours = computed(() => {
  if (monthlyData.value.length === 0) return 1
  const max = Math.max(...monthlyData.value.map(m => m.overtime.hours))
  return max || 1
})

const maxLeaveDays = computed(() => {
  if (monthlyData.value.length === 0) return 1
  const max = Math.max(...monthlyData.value.map(m => m.leave.days))
  return max || 1
})

const maxBusinessTripDays = computed(() => {
  if (monthlyData.value.length === 0) return 1
  const max = Math.max(...monthlyData.value.map(m => (m.business_trip?.days ?? 0)))
  return max || 1
})

// 月度趋势图：筛选展示加班/请假/公出其一（与领导人看板科室横向对比同形式）
const trendChartType = ref('overtime')
const trendChartTypes = [
  { type: 'overtime', label: '加班', unit: '(小时)' },
  { type: 'leave', label: '请假', unit: '(天)' },
  { type: 'trip', label: '公出', unit: '(天)' }
]
const trendChartBarClass = computed(() => {
  if (trendChartType.value === 'overtime') return 'bar-ot'
  if (trendChartType.value === 'leave') return 'bar-lv'
  return 'bar-tr'
})
const trendChartMax = computed(() => {
  if (trendChartType.value === 'overtime') return maxOvertimeHours.value
  if (trendChartType.value === 'leave') return maxLeaveDays.value
  return maxBusinessTripDays.value
})
function trendChartValue(month) {
  if (trendChartType.value === 'overtime') return month.overtime.hours
  if (trendChartType.value === 'leave') return month.leave.days
  return month.business_trip?.days ?? 0
}
function trendChartTitle(month) {
  const v = trendChartValue(month)
  if (trendChartType.value === 'overtime') return `加班 ${v} 小时`
  return `${trendChartTypes.find(t => t.type === trendChartType.value)?.label || ''} ${v} 天`
}

// 过滤后的加班记录
const filteredOvertimeRecords = computed(() => {
  if (!selectedOvertimeMonth.value) return overtimeRecords.value
  return overtimeRecords.value.filter(r => {
    if (!r.timedate) return false
    const month = parseInt(r.timedate.split('-')[1])
    return month === parseInt(selectedOvertimeMonth.value)
  })
})

// 过滤后的请假记录
const filteredLeaveRecords = computed(() => {
  if (!selectedLeaveMonth.value) return leaveRecords.value
  return leaveRecords.value.filter(r => {
    if (!r.timefrom) return false
    const month = parseInt(r.timefrom.split('-')[1])
    return month === parseInt(selectedLeaveMonth.value)
  })
})

// 过滤后的公出记录
const filteredBusinessTripRecords = computed(() => {
  if (!selectedBusinessTripMonth.value) return businessTripRecords.value
  return businessTripRecords.value.filter(r => {
    if (!r.gcsj) return false
    const month = parseInt(String(r.gcsj).split('-')[1])
    return month === parseInt(selectedBusinessTripMonth.value)
  })
})

// 获取柱状图高度
const getBarHeight = (value, max) => {
  if (!value || !max) return '0%'
  const percentage = (value / max) * 100
  return `${Math.max(percentage, 5)}%`
}

// 科室成员横向对比：合并加班/请假/公出为 { name, overtimeHours, leaveDays, tripDays }
const memberComparisonList = computed(() => {
  const byName = new Map()
  for (const r of (deptMemberOvertime.value || [])) {
    const n = (r.name || '').trim()
    if (n) byName.set(n, { name: n, overtimeHours: r.hours || 0, leaveDays: 0, tripDays: 0 })
  }
  for (const r of (deptMemberLeave.value || [])) {
    const n = (r.name || '').trim()
    if (n) {
      if (!byName.has(n)) byName.set(n, { name: n, overtimeHours: 0, leaveDays: 0, tripDays: 0 })
      byName.get(n).leaveDays = r.days || 0
    }
  }
  for (const r of (deptMemberTrip.value || [])) {
    const n = (r.name || '').trim()
    if (n) {
      if (!byName.has(n)) byName.set(n, { name: n, overtimeHours: 0, leaveDays: 0, tripDays: 0 })
      byName.get(n).tripDays = r.days || 0
    }
  }
  return Array.from(byName.values())
})

const memberCompareChartType = ref('overtime')
const memberCompareChartTypes = [
  { type: 'overtime', label: '加班', unit: '(小时)' },
  { type: 'leave', label: '请假', unit: '(天)' },
  { type: 'trip', label: '公出', unit: '(天)' }
]
const memberCompareBarClass = computed(() => {
  if (memberCompareChartType.value === 'overtime') return 'bar-ot'
  if (memberCompareChartType.value === 'leave') return 'bar-lv'
  return 'bar-tr'
})
function memberCompareValue(row) {
  if (memberCompareChartType.value === 'overtime') return row.overtimeHours
  if (memberCompareChartType.value === 'leave') return row.leaveDays
  return row.tripDays
}
const memberCompareSorted = computed(() => {
  const list = memberComparisonList.value
  if (!list.length) return []
  return [...list].sort((a, b) => memberCompareValue(b) - memberCompareValue(a))
})
const memberCompareMax = computed(() => {
  const list = memberCompareSorted.value
  if (!list.length) return 1
  const max = Math.max(...list.map(memberCompareValue))
  return max || 1
})
function memberCompareTitle(row) {
  const v = memberCompareValue(row)
  if (memberCompareChartType.value === 'overtime') return `加班 ${v} 小时`
  return `${memberCompareChartTypes.find(t => t.type === memberCompareChartType.value)?.label || ''} ${v} 天`
}

// 获取月份标签
const getMonthLabel = (monthStr) => {
  if (!monthStr) return ''
  const parts = monthStr.split('-')
  return `${parseInt(parts[1])}月`
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  // 处理不同格式的日期
  const date = dateStr.split(' ')[0]
  return date
}

// 格式化时间范围
const formatTimeRange = (from, to) => {
  if (!from && !to) return '-'
  const fromTime = from ? from.split(' ')[1] || from : ''
  const toTime = to ? to.split(' ')[1] || to : ''
  // 处理 1899-12-30 这种特殊格式
  const cleanFrom = fromTime.replace('1899-12-30 ', '')
  const cleanTo = toTime.replace('1899-12-30 ', '')
  return `${cleanFrom} - ${cleanTo}`
}

// 格式化日期时间范围
const formatDateTimeRange = (from, to) => {
  if (!from && !to) return '-'
  const fromDate = from ? from.split(' ')[0] : ''
  const toDate = to ? to.split(' ')[0] : ''
  if (fromDate === toDate) {
    return fromDate
  }
  return `${fromDate} 至 ${toDate}`
}

// 获取请假类型样式
const getLeaveTypeClass = (type) => {
  if (!type) return ''
  if (type.includes('病')) return 'sick-leave'
  if (type.includes('事')) return 'personal-leave'
  if (type.includes('年')) return 'annual-leave'
  if (type.includes('婚')) return 'marriage-leave'
  if (type.includes('产')) return 'maternity-leave'
  return ''
}

// 加载权限并初始化姓名
const loadPermission = async () => {
  const savedUser = localStorage.getItem('userInfo')
  if (!savedUser) return
  try {
    const user = JSON.parse(savedUser)
    const name = user.name || user.userName
    if (!name) return
    const res = await getStatisticsPermission({ name })
    if (res.success) {
      permLevel.value = res.level ?? 1
      permLsys.value = res.lsys || ''
      if (permLevel.value === 1) {
        queryParams.value.name = name
      } else if (permLevel.value === 2 && permLsys.value) {
        const empRes = await getStatisticsEmployees({ current_user: name, lsys: permLsys.value })
        deptEmployeeList.value = (empRes.list || []).filter(Boolean)
        if (deptEmployeeList.value.length && !queryParams.value.name) {
          queryParams.value.name = deptEmployeeList.value.includes(name) ? name : deptEmployeeList.value[0]
        }
      } else {
        queryParams.value.name = ''
      }
    }
  } catch (e) {
    // 降级为1级
    const user = JSON.parse(localStorage.getItem('userInfo') || '{}')
    queryParams.value.name = user.name || user.userName || ''
  }
}

onMounted(() => {
  loadPermission()
})

// 是否当前为「全员」汇总（2级且未选具体员工）
const isAllStaffQuery = computed(() => permLevel.value === 2 && !(queryParams.value.name || '').trim())

// 获取数据
const fetchData = async () => {
  const name = (queryParams.value.name || '').trim()
  if (!name && !isAllStaffQuery.value) {
    alert(permLevel.value === 2 ? '请选择员工或「全员」' : '请输入员工姓名')
    return
  }
  if (isAllStaffQuery.value && !permLsys.value) {
    alert('科室信息缺失')
    return
  }

  loading.value = true
  try {
    const params = { year: queryParams.value.year }
    if (name) params.name = name
    else params.lsys = permLsys.value

    const summaryRes = await getMonthlySummary(params)
    if (summaryRes.success) {
      monthlyData.value = summaryRes.monthly || []
      yearTotal.value = summaryRes.year_total
    }

    if (name) {
      const [overtimeRes, leaveRes, businessTripRes] = await Promise.all([
        getOvertimeRecords({ name, year: queryParams.value.year }),
        getLeaveRecords({ name, year: queryParams.value.year }),
        getBusinessTripRecords({ name, year: queryParams.value.year })
      ])
      if (overtimeRes.success) overtimeRecords.value = overtimeRes.records || []
      if (leaveRes.success) leaveRecords.value = leaveRes.records || []
      if (businessTripRes.success) businessTripRecords.value = businessTripRes.records || []
    } else {
      overtimeRecords.value = []
      leaveRecords.value = []
      businessTripRecords.value = []
    }

    // 班组长/主任/副主任：拉取科室成员横向对比数据（按人加班/请假/公出）
    if (permLevel.value === 2 && permLsys.value) {
      try {
        const deptParams = { lsys: permLsys.value, year: queryParams.value.year }
        const [leaveDept, overtimeDept, tripDept] = await Promise.all([
          getDeptLeaveStats(deptParams),
          getDeptOvertimeStats(deptParams),
          getDeptBusinessTripStats(deptParams)
        ])
        deptMemberLeave.value = (leaveDept.success && leaveDept.list) ? leaveDept.list : []
        deptMemberOvertime.value = (overtimeDept.success && overtimeDept.list) ? overtimeDept.list : []
        deptMemberTrip.value = (tripDept.success && tripDept.list) ? tripDept.list : []
      } catch (e) {
        deptMemberLeave.value = []
        deptMemberOvertime.value = []
        deptMemberTrip.value = []
      }
    } else {
      deptMemberLeave.value = []
      deptMemberOvertime.value = []
      deptMemberTrip.value = []
    }
  } catch (error) {
    console.error('获取数据失败:', error)
    alert('获取数据失败，请检查网络或后端服务')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.statistics-page {
  min-height: 100vh;
  background: var(--color-bg-layout);
}

.statistics-page .page-header {
  padding: var(--spacing-md) var(--spacing-xl);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--spacing-lg);
}

.header-info {
  flex: 1;
  min-width: 200px;
}

/* 容器 */
.statistics-page .container {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0 0 var(--spacing-xxl);
}

.card {
  background: var(--color-bg-container);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
}

/* 查询区域：冻结在页面顶端，滚动时始终可见 */
.query-section {
  position: sticky;
  top: 0;
  z-index: 10;
  padding: var(--spacing-xl);
  margin-bottom: 0;
  background: var(--color-bg-container);
  box-shadow: var(--shadow-card);
}

.query-form {
  display: flex;
  gap: var(--spacing-xl);
  align-items: flex-end;
  flex-wrap: wrap;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.form-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.form-input,
.form-select {
  height: 40px;
  padding: 0 var(--spacing-md);
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  background: var(--color-bg-container);
  min-width: 200px;
  transition: all var(--transition-base);
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-lightest);
}

.form-input[readonly] {
  background: var(--color-bg-spotlight);
  cursor: default;
}

.form-actions {
  margin-left: auto;
}

.btn {
  height: 40px;
  padding: 0 var(--spacing-xl);
  border-radius: var(--radius-base);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  border: none;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  transition: all var(--transition-base);
}

.btn-primary {
  background: var(--color-primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.loading-icon {
  width: 18px;
  height: 18px;
}

/* 汇总区域 */
.summary-section {
  margin-top: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
}

.section-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-sm);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.section-hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-lg);
}

.section-icon {
  width: 24px;
  height: 24px;
  color: var(--color-primary);
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: var(--spacing-xl);
}

.summary-card {
  padding: var(--spacing-xl);
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  transition: transform var(--transition-base), box-shadow var(--transition-base);
}

.summary-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-elevated);
}

.overtime-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.leave-card {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
}

.business-trip-card {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  color: white;
}

.summary-icon {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.summary-icon svg {
  width: 32px;
  height: 32px;
}

.summary-label {
  font-size: var(--font-size-sm);
  opacity: 0.9;
  margin-bottom: var(--spacing-xs);
}

.summary-main {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-xs);
}

.summary-value {
  font-size: var(--font-size-huge);
  font-weight: var(--font-weight-bold);
  line-height: 1;
}

.summary-unit {
  font-size: var(--font-size-md);
  opacity: 0.9;
}

.summary-sub {
  font-size: var(--font-size-sm);
  opacity: 0.8;
  margin-top: var(--spacing-sm);
}

/* 图表区域 */
.chart-section {
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
}

.chart-container {
  margin-top: var(--spacing-lg);
}

.chart-filter-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
  flex-wrap: wrap;
}
.chart-filter-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
.chart-type-tabs {
  display: flex;
  gap: var(--spacing-sm);
}
.tab-btn-sm {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm);
}
.tab-btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  background: var(--color-bg-container);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all var(--transition-base);
}
.tab-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.tab-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.bar-chart {
  display: flex;
  gap: var(--spacing-sm);
  height: 200px;
  min-height: 200px;
  align-items: stretch;
  padding-top: 28px;
  padding-bottom: var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
  overflow-x: auto;
  overflow-y: visible;
  box-sizing: content-box;
}
.bar-chart-single .bar-group .bar-col {
  min-width: 28px;
}
.bar-group {
  flex: 1;
  min-width: 44px;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  min-height: 0;
}
.bar-group .bar-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  flex: 1;
  min-width: 20px;
  min-height: 0;
}
.bar-group .bar {
  width: 28px;
  min-height: 4px;
  border-radius: 4px 4px 0 0;
  transition: height var(--transition-slow);
}
.bar-group .bar-has-value {
  position: relative;
}
.bar-group .bar-has-value .bar-value {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translate(-50%, calc(-100% - 4px));
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  white-space: nowrap;
  pointer-events: none;
}
.bar-group .bar-ot {
  background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
}
.bar-group .bar-lv {
  background: linear-gradient(180deg, #f093fb 0%, #f5576c 100%);
}
.bar-group .bar-tr {
  background: linear-gradient(180deg, #4facfe 0%, #00f2fe 100%);
}
.bar-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-top: var(--spacing-sm);
}

/* 表格区域 */
.tables-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-xl);
}

.table-card {
  overflow: hidden;
}

/* 公出明细横跨两列，与加班、请假对齐且更宽 */
.table-card--wide {
  grid-column: 1 / -1;
}

.table-header {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.table-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.table-icon {
  width: 20px;
  height: 20px;
  color: var(--color-primary);
}

.filter-select {
  height: 32px;
  padding: 0 var(--spacing-md);
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  background: var(--color-bg-container);
}

.table-content {
  padding: var(--spacing-lg);
  max-height: 400px;
  overflow-y: auto;
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

.data-table tbody tr:hover {
  background: var(--color-bg-spotlight);
}

.overtime-pay-table .pay-cell {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.overtime-pay-table tfoot td {
  font-weight: var(--font-weight-semibold);
  border-top: 2px solid var(--color-border-base);
}

.type-tag {
  display: inline-block;
  padding: 2px var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
}

.overtime-type {
  background: var(--color-primary-lightest);
  color: var(--color-primary-dark);
}

.leave-type {
  background: #fff1f0;
  color: #cf1322;
}

.leave-type.sick-leave {
  background: #fff7e6;
  color: #d46b08;
}

.leave-type.personal-leave {
  background: #f6ffed;
  color: #389e0d;
}

.leave-type.annual-leave {
  background: #e6f7ff;
  color: #096dd9;
}

.leave-type.marriage-leave {
  background: #fff0f6;
  color: #c41d7f;
}

.leave-type.maternity-leave {
  background: #f9f0ff;
  color: #722ed1;
}

.hours-cell {
  font-weight: var(--font-weight-medium);
  color: var(--color-primary);
}

.content-cell {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 公出明细表加宽，任务等列可展示更多文字 */
.data-table--wide .content-cell {
  max-width: 360px;
}

.empty-state {
  text-align: center;
  padding: var(--spacing-xxl);
  color: var(--color-text-tertiary);
}

.empty-icon {
  width: 48px;
  height: 48px;
  margin-bottom: var(--spacing-md);
  opacity: 0.5;
}

.tables-hint-card {
  grid-column: 1 / -1;
}
.tables-hint {
  padding: var(--spacing-xxl);
}
.tables-hint .hint-title {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-sm);
}
.tables-hint .hint-desc {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  max-width: 480px;
  margin: 0 auto;
}

/* 初始状态 */
.init-state {
  padding: var(--spacing-xxxl);
  text-align: center;
}

.init-content {
  max-width: 400px;
  margin: 0 auto;
}

.init-icon {
  width: 64px;
  height: 64px;
  color: var(--color-primary);
  margin-bottom: var(--spacing-lg);
  opacity: 0.6;
}

.init-content h3 {
  font-size: var(--font-size-xl);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-md);
}

.init-content p {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
}

/* 响应式 */
@media (max-width: 768px) {
  .query-form {
    flex-direction: column;
    align-items: stretch;
  }
  
  .form-input,
  .form-select {
    width: 100%;
  }
  
  .form-actions {
    margin-left: 0;
    margin-top: var(--spacing-md);
  }
  
  .btn {
    width: 100%;
    justify-content: center;
  }
  
  .summary-cards {
    grid-template-columns: 1fr;
  }
  
  .tables-section {
    grid-template-columns: 1fr;
  }
  
  .bar-chart {
    overflow-x: auto;
    padding-bottom: var(--spacing-lg);
  }
  
  .bar-group {
    min-width: 50px;
  }
}
</style>
