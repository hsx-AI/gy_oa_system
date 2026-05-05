<template>
  <div class="discipline-page">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">考勤纪律审查</h1>
          <p class="header-subtitle">打卡纪律大数据检测与假期值班出勤核查</p>
        </div>
        <router-link to="/leader-dashboard" class="btn btn-back">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          返回看板
        </router-link>
      </div>
    </div>

    <div class="container">
      <!-- ====== 打卡纪律大数据检测 ====== -->
      <div class="section card">
        <h2 class="section-title">
          <svg class="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
          打卡纪律大数据检测
        </h2>
        <p class="section-desc">
          基于打卡数据，自动检测踩点上班（8:00 前 N 分钟内打卡）和踩点下班（17:00 后 N 分钟内打卡）的情况。阈值可选 2～5 分钟及 10 / 20 / 30 分钟、1 小时。
        </p>

        <div class="filter-bar">
          <div class="form-item">
            <label class="form-label">科室</label>
            <select v-model="filterLsys" class="form-select">
              <option value="">全员</option>
              <option v-for="d in lsysList" :key="d" :value="d">{{ d }}</option>
            </select>
          </div>
          <div class="form-item">
            <label class="form-label">年份</label>
            <select v-model="filterYear" class="form-select">
              <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option>
            </select>
          </div>
          <div class="form-item">
            <label class="form-label">月份</label>
            <select v-model="filterMonth" class="form-select">
              <option :value="0">全年</option>
              <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
            </select>
          </div>
          <div class="form-item">
            <label class="form-label">踩点上班阈值</label>
            <select v-model="clockInMinutes" class="form-select form-select-sm">
              <option v-for="n in DISCIPLINE_MINUTE_OPTIONS" :key="'ci'+n" :value="n">
                {{ disciplineMinuteOptionText('8:00 前', n) }}
              </option>
            </select>
          </div>
          <div class="form-item">
            <label class="form-label">踩点下班阈值</label>
            <select v-model="clockOutMinutes" class="form-select form-select-sm">
              <option v-for="n in DISCIPLINE_MINUTE_OPTIONS" :key="'co'+n" :value="n">
                {{ disciplineMinuteOptionText('17:00 后', n) }}
              </option>
            </select>
          </div>
          <div class="form-item">
            <label class="form-label">聚合维度</label>
            <div class="tab-group">
              <button
                v-for="dim in dimensions"
                :key="dim.value"
                :class="['tab-btn', { active: filterDimension === dim.value }]"
                @click="filterDimension = dim.value"
              >{{ dim.label }}</button>
            </div>
          </div>
          <div class="form-item form-item-check">
            <label class="check-label">
              <input type="checkbox" v-model="excludeHolidays" class="check-input" />
              <span>过滤节假日</span>
            </label>
            <span class="check-hint">排除周末及法定假日</span>
          </div>
          <div class="form-item form-actions">
            <button class="btn btn-primary" @click="fetchStats" :disabled="loading">
              <svg v-if="loading" class="loading-icon" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="31.4" stroke-linecap="round">
                  <animateTransform attributeName="transform" type="rotate" dur="1s" from="0 12 12" to="360 12 12" repeatCount="indefinite"/>
                </circle>
              </svg>
              {{ loading ? '检测中...' : '查询' }}
            </button>
            <button class="btn btn-outline-scatter" type="button" @click="openCustomScatter">
              <svg class="btn-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="7.5" cy="7.5" r="2" /><circle cx="16" cy="16" r="2" /><circle cx="17" cy="8" r="2" /><circle cx="8" cy="17" r="2" />
                <rect x="2" y="2" width="20" height="20" rx="3" />
              </svg>
              查看任意员工散点
            </button>
          </div>
        </div>

        <template v-if="hasFetched">
          <!-- 汇总卡片 -->
          <div class="summary-cards">
            <div class="summary-card card-clockin">
              <div class="summary-card-header">
                <svg class="summary-card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4"/>
                  <polyline points="10 17 15 12 10 7"/>
                  <line x1="15" y1="12" x2="3" y2="12"/>
                </svg>
                <h3>踩点上班</h3>
                <span class="summary-range">{{ clockInRangeLabel }}</span>
              </div>
              <div class="summary-card-body">
                <div class="summary-total">
                  <span class="total-value">{{ clockInTotal }}</span>
                  <span class="total-unit">次</span>
                </div>
              </div>
            </div>
            <div class="summary-card card-clockout">
              <div class="summary-card-header">
                <svg class="summary-card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
                  <polyline points="16 17 21 12 16 7"/>
                  <line x1="21" y1="12" x2="9" y2="12"/>
                </svg>
                <h3>踩点下班</h3>
                <span class="summary-range">{{ clockOutRangeLabel }}</span>
              </div>
              <div class="summary-card-body">
                <div class="summary-total">
                  <span class="total-value">{{ clockOutTotal }}</span>
                  <span class="total-unit">次</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 柱状图对比 -->
          <div class="chart-section">
            <div class="chart-column">
              <h3 class="chart-title">踩点上班排行（{{ clockInRangeLabel }}）</h3>
              <div v-if="clockInList.length" class="bar-chart-wrap">
                <div class="rank-list">
                  <div
                    v-for="(item, idx) in clockInList"
                    :key="'ci-' + item.key"
                    class="rank-item"
                    @click="onRankClick('clockIn', idx, item)"
                  >
                    <div class="rank-bar-row">
                      <span class="rank-num">{{ idx + 1 }}</span>
                      <span class="rank-name" :title="item.dept ? item.key + '（' + item.dept + '）' : item.key">{{ item.key }}</span>
                      <span v-if="item.dept && filterDimension === 'person'" class="rank-dept">{{ item.dept }}</span>
                      <div class="rank-bar-wrap">
                        <div
                          class="rank-bar bar-clockin"
                          :style="{ width: getBarWidth(item.count, clockInMax) }"
                        ></div>
                      </div>
                      <span class="rank-count">{{ item.count }}次</span>
                      <svg v-if="item.dates?.length" class="expand-icon" :class="{ expanded: expandedClockIn === idx }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" @click.stop="toggleExpand('clockIn', idx)"><polyline points="6 9 12 15 18 9"/></svg>
                    </div>
                    <transition name="slide">
                      <div v-if="expandedClockIn === idx && item.dates?.length" class="rank-detail" @click.stop>
                        <table class="detail-table">
                          <thead><tr><th>日期</th><th v-if="filterDimension !== 'person'">姓名</th><th>打卡时间</th></tr></thead>
                          <tbody>
                            <tr v-for="d in item.dates" :key="d.date + d.name">
                              <td>{{ d.date }}</td>
                              <td v-if="filterDimension !== 'person'">{{ d.name }}</td>
                              <td>{{ d.time }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </transition>
                  </div>
                </div>
              </div>
              <div v-else class="empty-state">暂无踩点上班记录</div>
            </div>

            <div class="chart-column">
              <h3 class="chart-title">踩点下班排行（{{ clockOutRangeLabel }}）</h3>
              <div v-if="clockOutList.length" class="bar-chart-wrap">
                <div class="rank-list">
                  <div
                    v-for="(item, idx) in clockOutList"
                    :key="'co-' + item.key"
                    class="rank-item"
                    @click="onRankClick('clockOut', idx, item)"
                  >
                    <div class="rank-bar-row">
                      <span class="rank-num">{{ idx + 1 }}</span>
                      <span class="rank-name" :title="item.dept ? item.key + '（' + item.dept + '）' : item.key">{{ item.key }}</span>
                      <span v-if="item.dept && filterDimension === 'person'" class="rank-dept">{{ item.dept }}</span>
                      <div class="rank-bar-wrap">
                        <div
                          class="rank-bar bar-clockout"
                          :style="{ width: getBarWidth(item.count, clockOutMax) }"
                        ></div>
                      </div>
                      <span class="rank-count">{{ item.count }}次</span>
                      <svg v-if="item.dates?.length" class="expand-icon" :class="{ expanded: expandedClockOut === idx }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" @click.stop="toggleExpand('clockOut', idx)"><polyline points="6 9 12 15 18 9"/></svg>
                    </div>
                    <transition name="slide">
                      <div v-if="expandedClockOut === idx && item.dates?.length" class="rank-detail" @click.stop>
                        <table class="detail-table">
                          <thead><tr><th>日期</th><th v-if="filterDimension !== 'person'">姓名</th><th>打卡时间</th></tr></thead>
                          <tbody>
                            <tr v-for="d in item.dates" :key="d.date + d.name">
                              <td>{{ d.date }}</td>
                              <td v-if="filterDimension !== 'person'">{{ d.name }}</td>
                              <td>{{ d.time }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </transition>
                  </div>
                </div>
              </div>
              <div v-else class="empty-state">暂无踩点下班记录</div>
            </div>
          </div>
        </template>

        <div v-if="!hasFetched && !loading" class="init-hint">
          <p>选择筛选条件后点击「查询」开始检测。</p>
        </div>
      </div>

      <!-- ====== 假期值班出勤核查 ====== -->
      <div class="section card duty-section">
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
            <button class="btn btn-primary" @click="fetchDutyAttendance" :disabled="dutyLoading">
              <svg v-if="dutyLoading" class="loading-icon" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="31.4" stroke-linecap="round">
                  <animateTransform attributeName="transform" type="rotate" dur="1s" from="0 12 12" to="360 12 12" repeatCount="indefinite"/>
                </circle>
              </svg>
              {{ dutyLoading ? '核查中...' : '核查' }}
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
                      <td>{{ d.late }}</td>
                      <td>{{ d.earlyLeave }}</td>
                      <td>{{ d.absent }}</td>
                    </tr>
                    <tr v-if="!dutyByDate.length">
                      <td colspan="7" class="table-empty-cell">所选范围暂无值班排班</td>
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
    </div>

    <!-- ====== 个人打卡散点图弹窗 ====== -->
    <teleport to="body">
      <transition name="modal-fade">
        <div v-if="scatterVisible" class="scatter-overlay" @click.self="scatterVisible = false">
          <div class="scatter-modal">
            <div class="scatter-header">
              <h3>{{ scatterName }} · 打卡时间分布</h3>
              <div class="scatter-controls">
                <button
                  v-for="r in scatterRanges"
                  :key="r.value"
                  :class="['tab-btn', { active: scatterRange === r.value }]"
                  @click="changeScatterRange(r.value)"
                >{{ r.label }}</button>
              </div>
              <button class="scatter-close" @click="scatterVisible = false">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
            <div class="scatter-body">
              <div v-if="scatterLoading" class="scatter-loading">加载中...</div>
              <v-chart v-else-if="scatterOption" class="scatter-chart" :option="scatterOption" :autoresize="true" />
              <div v-else class="scatter-empty">暂无打卡数据</div>
            </div>
          </div>
        </div>
      </transition>
    </teleport>

    <!-- ====== 自定义员工散点图弹窗 ====== -->
    <teleport to="body">
      <transition name="modal-fade">
        <div v-if="customScatterVisible" class="scatter-overlay" @click.self="customScatterVisible = false">
          <div class="scatter-modal">
            <div class="scatter-header">
              <div class="custom-scatter-picker">
                <input
                  ref="customNameInputRef"
                  v-model.trim="customScatterInput"
                  type="text"
                  class="custom-scatter-input"
                  placeholder="输入姓名搜索…"
                  @input="onCustomNameInput"
                  @keydown.enter.prevent="confirmCustomName"
                  @focus="customDropdownOpen = customNameMatches.length > 0"
                />
                <div v-if="customDropdownOpen && customNameMatches.length" class="custom-scatter-dropdown">
                  <div
                    v-for="m in customNameMatches"
                    :key="m.name"
                    class="custom-scatter-dropdown-item"
                    @mousedown.prevent="selectCustomName(m)"
                  >
                    <span class="dropdown-name">{{ m.name }}</span>
                    <span class="dropdown-dept">{{ m.lsys }}</span>
                  </div>
                </div>
              </div>
              <div class="scatter-controls">
                <button
                  v-for="r in scatterRanges"
                  :key="'cs-' + r.value"
                  :class="['tab-btn', { active: customScatterRange === r.value }]"
                  @click="changeCustomScatterRange(r.value)"
                >{{ r.label }}</button>
              </div>
              <button class="scatter-close" @click="customScatterVisible = false">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
            <div class="scatter-body">
              <div v-if="customScatterLoading" class="scatter-loading">加载中...</div>
              <v-chart v-else-if="customScatterOption" class="scatter-chart" :option="customScatterOption" :autoresize="true" />
              <div v-else class="scatter-empty">{{ customScatterName ? '暂无打卡数据' : '请输入姓名查询' }}</div>
            </div>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import {
  getStatisticsPermission,
  getDeptLsysList,
  getClockInDisciplineStats,
  getHolidayDutyAttendanceCheck,
  getPersonScatterData,
  getStatisticsEmployees,
} from '@/api/attendance'

/** 与后端 `/discipline/clock-in-stats` 白名单一致 */
const DISCIPLINE_MINUTE_OPTIONS = Object.freeze([2, 3, 4, 5, 10, 20, 30, 60])

function disciplineMinuteOptionText(prefix, n) {
  return n === 60 ? `${prefix} 1 小时` : `${prefix} ${n} 分钟`
}

const filterYear = ref(new Date().getFullYear())
const filterMonth = ref(0)
const filterLsys = ref('')
const filterDimension = ref('person')
const clockInMinutes = ref(2)
const clockOutMinutes = ref(2)
const excludeHolidays = ref(true)
const loading = ref(false)
const hasFetched = ref(false)
const lsysList = ref([])

const dimensions = [
  { value: 'person', label: '按人' },
  { value: 'month', label: '按月' },
  { value: 'dept', label: '按科室' },
]

const clockInTotal = ref(0)
const clockOutTotal = ref(0)
const clockInList = ref([])
const clockOutList = ref([])
const expandedClockIn = ref(-1)
const expandedClockOut = ref(-1)
const clockInRangeLabel = ref('7:58-8:00')
const clockOutRangeLabel = ref('17:00-17:02')

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
const dutyFetched = ref(false)
const dutySummary = ref({})
const dutyByDate = ref([])
const dutyDetails = ref([])

const dutyExceptionDetails = computed(() => dutyDetails.value.filter(r => r.status !== 'normal'))

const yearOptions = computed(() => {
  const cur = new Date().getFullYear()
  return Array.from({ length: 6 }, (_, i) => cur - i)
})

const clockInMax = computed(() => Math.max(...clockInList.value.map(i => i.count), 1))
const clockOutMax = computed(() => Math.max(...clockOutList.value.map(i => i.count), 1))

function getBarWidth(count, max) {
  if (!max) return '0%'
  return `${Math.max((count / max) * 100, 3)}%`
}

function percentText(rate) {
  const n = Number(rate || 0)
  return `${(n * 100).toFixed(1)}%`
}

function toggleExpand(type, idx) {
  if (type === 'clockIn') {
    expandedClockIn.value = expandedClockIn.value === idx ? -1 : idx
  } else {
    expandedClockOut.value = expandedClockOut.value === idx ? -1 : idx
  }
}

async function fetchStats() {
  loading.value = true
  hasFetched.value = true
  expandedClockIn.value = -1
  expandedClockOut.value = -1
  try {
    const params = {
      year: filterYear.value,
      dimension: filterDimension.value,
      clock_in_minutes: clockInMinutes.value,
      clock_out_minutes: clockOutMinutes.value,
      exclude_holidays: excludeHolidays.value,
    }
    if (filterMonth.value) params.month = filterMonth.value
    if (filterLsys.value) params.lsys = filterLsys.value
    const res = await getClockInDisciplineStats(params)
    if (res.success) {
      clockInTotal.value = res.clockInTotal || 0
      clockOutTotal.value = res.clockOutTotal || 0
      clockInList.value = res.clockIn || []
      clockOutList.value = res.clockOut || []
      if (res.clockInRange) clockInRangeLabel.value = res.clockInRange
      if (res.clockOutRange) clockOutRangeLabel.value = res.clockOutRange
    }
  } catch (e) {
    console.error('打卡纪律统计失败:', e)
  } finally {
    loading.value = false
  }
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

onMounted(async () => {
  try {
    const saved = localStorage.getItem('userInfo')
    if (!saved) return
    const user = JSON.parse(saved)
    const name = user.name || user.userName
    if (!name) return
    const res = await getStatisticsPermission({ name })
    if (res.success && res.level === 3) {
      const listRes = await getDeptLsysList()
      if (listRes.success && listRes.list?.length) {
        lsysList.value = listRes.list.filter(v => v && !['其他部门员工','其他部门成员'].includes(v.trim()))
      }
    }
  } catch { /* ignore */ }
})

// ====== 个人散点图弹窗 ======
const scatterVisible = ref(false)
const scatterName = ref('')
const scatterRange = ref('month')
const scatterLoading = ref(false)
const scatterOption = ref(null)

const scatterRanges = [
  { value: 'week', label: '近1周' },
  { value: 'month', label: '近1月' },
  { value: 'year', label: '近1年' },
]

function getDateRange(range) {
  const end = new Date()
  const start = new Date()
  if (range === 'week') start.setDate(end.getDate() - 7)
  else if (range === 'month') start.setMonth(end.getMonth() - 1)
  else start.setFullYear(end.getFullYear() - 1)
  const fmt = d => d.toISOString().slice(0, 10)
  return { start_date: fmt(start), end_date: fmt(end) }
}

function formatHour(h) {
  const hh = Math.floor(h)
  const mm = Math.round((h - hh) * 60)
  return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`
}

function formatHourWithSecond(h) {
  const totalSeconds = Math.max(0, Math.round(h * 3600))
  const hh = Math.floor(totalSeconds / 3600)
  const mm = Math.floor((totalSeconds % 3600) / 60)
  const ss = totalSeconds % 60
  return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`
}

function buildScatterOption(data, range) {
  const dates = data.map(d => d.date)
  const ciData = data.filter(d => d.clockIn != null).map(d => [d.date, d.clockIn])
  const coData = data.filter(d => d.clockOut != null).map(d => [d.date, d.clockOut])

  const zoomStart = range === 'year' ? 75 : 0

  function autoRange(values, anchor, fallbackLo, fallbackHi) {
    if (!values.length) return { min: fallbackLo, max: fallbackHi }
    const lo = Math.min(...values, anchor)
    const hi = Math.max(...values, anchor)
    const pad = Math.max((hi - lo) * 0.25, 0.25)
    return {
      min: Math.max(0, Math.floor((lo - pad) * 4) / 4),
      max: Math.min(24, Math.ceil((hi + pad) * 4) / 4),
    }
  }

  const ciValues = ciData.map(d => d[1])
  const coValues = coData.map(d => d[1])
  const ciRange = autoRange(ciValues, 8, 7, 9)
  const coRange = autoRange(coValues, 17, 16, 18)

  const hasSlider = range === 'year'
  const bottomPad = hasSlider ? 70 : 36

  const axisLabelFmt = v => {
    const h = Math.floor(v)
    const m = Math.round((v - h) * 60)
    return `${h}:${String(m).padStart(2, '0')}`
  }

  return {
    tooltip: {
      trigger: 'item',
      formatter(p) {
        return `${p.seriesName}<br/>${p.data[0]}<br/>${formatHourWithSecond(p.data[1])}`
      }
    },
    legend: {
      data: ['上班打卡', '下班打卡'],
      top: 0,
      textStyle: { fontSize: 12 }
    },
    grid: [
      { left: 60, right: 24, top: 36, bottom: '54%' },
      { left: 60, right: 24, top: '54%', bottom: bottomPad },
    ],
    xAxis: [
      {
        type: 'category',
        gridIndex: 0,
        data: dates,
        axisLabel: { show: false },
        axisTick: { alignWithLabel: true },
      },
      {
        type: 'category',
        gridIndex: 1,
        data: dates,
        axisLabel: {
          fontSize: 11,
          rotate: dates.length > 15 ? 45 : 0,
          formatter: v => v.slice(5),
        },
        axisTick: { alignWithLabel: true },
      },
    ],
    yAxis: [
      {
        type: 'value',
        gridIndex: 0,
        min: ciRange.min,
        max: ciRange.max,
        inverse: true,
        axisLabel: { formatter: axisLabelFmt, fontSize: 11 },
        name: '上班',
        nameTextStyle: { fontSize: 11, padding: [0, 40, 0, 0] },
        splitLine: { lineStyle: { type: 'dotted', color: '#e5e7eb' } },
      },
      {
        type: 'value',
        gridIndex: 1,
        min: coRange.min,
        max: coRange.max,
        inverse: true,
        axisLabel: { formatter: axisLabelFmt, fontSize: 11 },
        name: '下班',
        nameTextStyle: { fontSize: 11, padding: [0, 40, 0, 0] },
        splitLine: { lineStyle: { type: 'dotted', color: '#e5e7eb' } },
      },
    ],
    dataZoom: hasSlider ? [
      { type: 'slider', xAxisIndex: [0, 1], start: zoomStart, end: 100, bottom: 6, height: 22 },
      { type: 'inside', xAxisIndex: [0, 1], start: zoomStart, end: 100 },
    ] : [
      { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
    ],
    series: [
      {
        name: '上班打卡',
        type: 'scatter',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: ciData,
        symbolSize: 10,
        symbol: 'path://M-1,-1L1,-1L1,1L-1,1Z M-0.6,-0.6L0.6,-0.6L0.6,0.6L-0.6,0.6Z',
        itemStyle: { color: '#f59e0b' },
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { type: 'dashed', width: 2, color: '#ef4444' },
          label: { formatter: '8:00', fontSize: 11, position: 'insideEndTop', color: '#ef4444' },
          data: [{ yAxis: 8 }],
        },
      },
      {
        name: '下班打卡',
        type: 'scatter',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: coData,
        symbolSize: 10,
        symbol: 'path://M-1,-1L1,-1L1,1L-1,1Z M-0.6,-0.6L0.6,-0.6L0.6,0.6L-0.6,0.6Z',
        itemStyle: { color: '#7c3aed' },
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { type: 'dashed', width: 2, color: '#3b82f6' },
          label: { formatter: '17:00', fontSize: 11, position: 'insideEndTop', color: '#3b82f6' },
          data: [{ yAxis: 17 }],
        },
      },
    ],
  }
}

async function openScatter(personName) {
  scatterName.value = personName
  scatterVisible.value = true
  scatterRange.value = 'month'
  await loadScatterData()
}

async function changeScatterRange(range) {
  scatterRange.value = range
  await loadScatterData()
}

async function loadScatterData() {
  scatterLoading.value = true
  scatterOption.value = null
  try {
    const { start_date, end_date } = getDateRange(scatterRange.value)
    const res = await getPersonScatterData({ name: scatterName.value, start_date, end_date, exclude_holidays: excludeHolidays.value })
    if (res.success && res.data?.length) {
      scatterOption.value = buildScatterOption(res.data, scatterRange.value)
    }
  } catch (e) {
    console.error('散点图数据加载失败:', e)
  } finally {
    scatterLoading.value = false
  }
}

function onRankClick(type, idx, item) {
  if (filterDimension.value === 'person' && item.key) {
    openScatter(item.key)
  } else {
    toggleExpand(type, idx)
  }
}

// ====== 自定义员工散点图 ======
const customScatterVisible = ref(false)
const customScatterName = ref('')
const customScatterInput = ref('')
const customScatterRange = ref('month')
const customScatterLoading = ref(false)
const customScatterOption = ref(null)
const customNameInputRef = ref(null)
const customDropdownOpen = ref(false)
const customNameMatches = ref([])
const allEmployees = ref([])

async function loadAllEmployees() {
  if (allEmployees.value.length) return
  try {
    const rows = []
    for (const dept of lsysList.value) {
      const res = await getStatisticsEmployees({ current_user: '_admin_', lsys: dept, limit: 500 })
      if (res.success && res.list) {
        for (const n of res.list) rows.push({ name: n, lsys: dept })
      }
    }
    allEmployees.value = rows
  } catch { /* ignore */ }
}

function onCustomNameInput() {
  const q = customScatterInput.value.trim().toLowerCase()
  if (!q) {
    customNameMatches.value = []
    customDropdownOpen.value = false
    return
  }
  customNameMatches.value = allEmployees.value
    .filter(e => e.name.toLowerCase().includes(q))
    .slice(0, 15)
  customDropdownOpen.value = customNameMatches.value.length > 0
}

function selectCustomName(emp) {
  customScatterInput.value = emp.name
  customScatterName.value = emp.name
  customDropdownOpen.value = false
  loadCustomScatterData()
}

function confirmCustomName() {
  const name = customScatterInput.value.trim()
  if (!name) return
  customScatterName.value = name
  customDropdownOpen.value = false
  loadCustomScatterData()
}

function openCustomScatter() {
  customScatterVisible.value = true
  customScatterOption.value = null
  customScatterRange.value = 'month'
  loadAllEmployees()
  setTimeout(() => customNameInputRef.value?.focus(), 100)
}

async function changeCustomScatterRange(range) {
  customScatterRange.value = range
  if (customScatterName.value) await loadCustomScatterData()
}

async function loadCustomScatterData() {
  if (!customScatterName.value) return
  customScatterLoading.value = true
  customScatterOption.value = null
  try {
    const { start_date, end_date } = getDateRange(customScatterRange.value)
    const res = await getPersonScatterData({ name: customScatterName.value, start_date, end_date, exclude_holidays: excludeHolidays.value })
    if (res.success && res.data?.length) {
      customScatterOption.value = buildScatterOption(res.data, customScatterRange.value)
    }
  } catch (e) {
    console.error('散点图数据加载失败:', e)
  } finally {
    customScatterLoading.value = false
  }
}
</script>

<style scoped>
.discipline-page {
  min-height: 100vh;
  background: var(--color-bg-layout);
}

.page-header {
  padding: var(--spacing-md) var(--spacing-xl);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--spacing-lg);
}

.header-info { flex: 1; min-width: 200px; }

.header-title {
  font-size: var(--font-size-xxl, 24px);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin: 0 0 4px;
}

.header-subtitle {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0;
}

.btn-back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  background: var(--color-bg-container);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  text-decoration: none;
  transition: all 0.15s;
}
.btn-back:hover { border-color: var(--color-primary); color: var(--color-primary); }
.btn-back .btn-icon { width: 16px; height: 16px; }

.container {
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

.section {
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
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

/* 筛选栏 */
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

.form-select-sm { min-width: 150px; }

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

.form-item-check {
  justify-content: center;
  gap: 2px;
}

.check-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  cursor: pointer;
  user-select: none;
}

.check-input {
  width: 16px;
  height: 16px;
  accent-color: var(--color-primary);
  cursor: pointer;
}

.check-hint {
  font-size: var(--font-size-xs, 11px);
  color: var(--color-text-tertiary);
}

.tab-group { display: flex; gap: 4px; }

.tab-btn {
  padding: 6px 14px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  background: var(--color-bg-container);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all 0.15s;
}
.tab-btn:hover { border-color: var(--color-primary); color: var(--color-primary); }
.tab-btn.active { background: var(--color-primary); color: white; border-color: var(--color-primary); }

.form-actions { margin-left: auto; }

.btn {
  height: 36px;
  padding: 0 var(--spacing-xl);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  border: none;
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.btn-primary { background: var(--color-primary); color: white; }
.btn-primary:hover:not(:disabled) { filter: brightness(1.05); }
.btn-primary:disabled { opacity: 0.7; cursor: not-allowed; }

.loading-icon { width: 16px; height: 16px; }

/* 汇总卡片 */
.summary-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.summary-card {
  border-radius: var(--radius-base);
  border: 1px solid var(--color-border-lighter);
  overflow: hidden;
}

.summary-card-header {
  padding: var(--spacing-md) var(--spacing-lg);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  color: white;
}

.card-clockin .summary-card-header { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
.card-clockout .summary-card-header { background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%); }

.summary-card-icon { width: 22px; height: 22px; flex-shrink: 0; }

.summary-card-header h3 {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  margin: 0;
  color: white;
}

.summary-range {
  margin-left: auto;
  font-size: var(--font-size-xs);
  background: rgba(255,255,255,0.2);
  padding: 2px 8px;
  border-radius: 10px;
}

.summary-card-body { padding: var(--spacing-lg) var(--spacing-xl); }

.summary-total {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-xs);
}

.total-value { font-size: var(--font-size-huge, 36px); font-weight: var(--font-weight-bold); color: var(--color-text-primary); }
.total-unit { font-size: var(--font-size-md); color: var(--color-text-secondary); }

/* 排行榜 */
.chart-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-xl);
}

.chart-title {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-md);
}

.rank-list { display: flex; flex-direction: column; gap: 2px; }

.rank-item {
  cursor: pointer;
  border-radius: var(--radius-sm, 4px);
  transition: background 0.15s;
}
.rank-item:hover { background: var(--color-bg-hover, rgba(0,0,0,0.02)); }

.rank-bar-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 8px 10px;
}

.rank-num {
  width: 24px;
  text-align: right;
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}

.rank-name {
  min-width: 60px;
  max-width: 100px;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 0;
}

.rank-dept {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  white-space: nowrap;
  flex-shrink: 0;
}

.rank-bar-wrap {
  flex: 1;
  height: 20px;
  background: var(--color-bg-spotlight, #f3f4f6);
  border-radius: 4px;
  overflow: hidden;
  min-width: 60px;
}

.rank-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.bar-clockin { background: linear-gradient(90deg, #fbbf24, #f59e0b); }
.bar-clockout { background: linear-gradient(90deg, #a78bfa, #7c3aed); }

.rank-count {
  min-width: 48px;
  text-align: right;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}

.expand-icon {
  width: 16px;
  height: 16px;
  color: var(--color-text-tertiary);
  transition: transform 0.2s;
  flex-shrink: 0;
}
.expand-icon.expanded { transform: rotate(180deg); }

.rank-detail {
  padding: 0 10px 10px 44px;
  overflow: hidden;
}

.slide-enter-active, .slide-leave-active { transition: all 0.2s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; max-height: 0; }
.slide-enter-to, .slide-leave-from { opacity: 1; max-height: 500px; }

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

.empty-state {
  padding: var(--spacing-xl);
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

.init-hint {
  padding: var(--spacing-xl);
  text-align: center;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

/* 假期值班出勤核查 */
.duty-section {
  border: 1px solid var(--color-border-lighter);
}

.duty-filter-bar {
  align-items: flex-end;
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

/* 散点图弹窗 */
.scatter-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.scatter-modal {
  background: var(--color-bg-container, #fff);
  border-radius: var(--radius-lg, 12px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2);
  width: 100%;
  max-width: 960px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.scatter-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md, 12px);
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border-lighter, #eee);
  flex-shrink: 0;
}

.scatter-header h3 {
  font-size: var(--font-size-lg, 16px);
  font-weight: var(--font-weight-semibold, 600);
  color: var(--color-text-primary);
  margin: 0;
  white-space: nowrap;
}

.scatter-controls {
  display: flex;
  gap: 4px;
  margin-left: auto;
}

.scatter-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--color-text-tertiary);
  border-radius: 6px;
  transition: background 0.15s;
  flex-shrink: 0;
}
.scatter-close:hover { background: var(--color-bg-hover, rgba(0,0,0,.06)); }
.scatter-close svg { width: 18px; height: 18px; }

.scatter-body {
  flex: 1;
  min-height: 480px;
  padding: 12px 16px 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.scatter-chart {
  width: 100%;
  height: 500px;
}

.scatter-loading,
.scatter-empty {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

/* 自定义散点图 - 按钮 & 搜索 */
.btn-outline-scatter {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-primary);
  background: #fff;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-base, 6px);
  cursor: pointer;
  transition: all .15s ease;
  white-space: nowrap;
}
.btn-outline-scatter:hover {
  background: var(--color-primary-lightest, #eef2ff);
}
.btn-icon-sm {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}
.custom-scatter-picker {
  position: relative;
  min-width: 200px;
}
.custom-scatter-input {
  width: 100%;
  padding: 6px 12px;
  font-size: 14px;
  border: 1px solid var(--color-border-base, #d1d5db);
  border-radius: var(--radius-base, 6px);
  outline: none;
  transition: border-color .15s;
}
.custom-scatter-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(99, 102, 241, .15);
}
.custom-scatter-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  max-height: 240px;
  overflow-y: auto;
  background: #fff;
  border: 1px solid var(--color-border-lighter, #e5e7eb);
  border-radius: var(--radius-base, 6px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  z-index: 10;
}
.custom-scatter-dropdown-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
  transition: background .1s;
}
.custom-scatter-dropdown-item:hover {
  background: var(--color-bg-hover, #f3f4f6);
}
.dropdown-name {
  font-weight: 500;
  color: var(--color-text-primary);
}
.dropdown-dept {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.modal-fade-enter-active,
.modal-fade-leave-active { transition: opacity 0.2s ease; }
.modal-fade-enter-from,
.modal-fade-leave-to { opacity: 0; }

@media (max-width: 960px) {
  .chart-section { grid-template-columns: 1fr; }
  .summary-cards { grid-template-columns: 1fr; }
  .duty-summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .duty-content-grid { grid-template-columns: 1fr; }
  .scatter-modal { max-width: 100%; }
}

@media (max-width: 768px) {
  .filter-bar { flex-direction: column; align-items: stretch; }
  .form-actions { margin-left: 0; }
  .duty-summary-grid { grid-template-columns: 1fr; }
  .scatter-header { flex-wrap: wrap; }
  .scatter-chart { height: 320px; }
}
</style>
