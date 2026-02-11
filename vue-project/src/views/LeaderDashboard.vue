<template>
  <div class="leader-dashboard-page">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">领导人看板</h1>
          <p class="header-subtitle">本科室请假、加班、公出汇总，按人查看</p>
        </div>
      </div>
    </div>

    <div class="container">
      <!-- 无科室权限提示 -->
      <div v-if="!canViewDept" class="no-permission card">
        <div class="no-permission-content">
          <svg class="no-permission-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <h3>暂无科室数据权限</h3>
          <p>您当前仅可查看个人统计。科室维度汇总需组长/主任/部长等权限。</p>
          <router-link to="/statistics" class="btn btn-primary">前往统计汇总</router-link>
        </div>
      </div>

      <template v-else>
        <!-- 筛选 -->
        <div class="filter-section card">
          <div class="filter-form">
            <div class="form-item">
              <label class="form-label">隶属科室</label>
              <!-- 部长/副部长：下拉选择全员或任意科室 -->
              <select
                v-if="permLevel === 3"
                v-model="selectedLsys"
                class="form-select"
                :disabled="!lsysList.length"
              >
                <option value="">全员</option>
                <option v-for="d in lsysList" :key="d" :value="d">{{ d }}</option>
              </select>
              <!-- 组长/主任等：仅显示本科室 -->
              <input
                v-else
                :value="lsys"
                type="text"
                class="form-input"
                readonly
              />
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
                <option value="">全年</option>
                <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
              </select>
            </div>
            <div class="form-item form-actions">
              <button class="btn btn-primary" @click="fetchData" :disabled="loading">
                <svg v-if="loading" class="loading-icon" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="31.4" stroke-linecap="round">
                    <animateTransform attributeName="transform" type="rotate" dur="1s" from="0 12 12" to="360 12 12" repeatCount="indefinite"/>
                  </circle>
                </svg>
                <span>{{ loading ? '加载中...' : '查询' }}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- 汇总卡片 -->
        <div class="dashboard-cards">
          <div class="dashboard-card leave-card card">
            <div class="dashboard-card-header">
              <svg class="dashboard-card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                <line x1="16" y1="2" x2="16" y2="6"/>
                <line x1="8" y1="2" x2="8" y2="6"/>
                <line x1="3" y1="10" x2="21" y2="10"/>
              </svg>
              <h3>请假汇总</h3>
            </div>
            <div class="dashboard-card-body">
              <div class="dashboard-total">
                <span class="total-value">{{ leaveStats.totalDays ?? '-' }}</span>
                <span class="total-unit">天</span>
              </div>
              <div class="dashboard-meta">共 {{ leaveStats.personCount ?? 0 }} 人</div>
              <div v-if="leaveStats.list?.length" class="dashboard-list">
                <div class="list-title">按人明细</div>
                <ul class="person-list">
                  <li v-for="item in leaveStats.list" :key="item.name" class="person-item">
                    <span class="person-name">{{ item.name }}</span>
                    <span class="person-value">{{ item.days }} 天</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          <div class="dashboard-card overtime-card card">
            <div class="dashboard-card-header">
              <svg class="dashboard-card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
              <h3>加班汇总</h3>
            </div>
            <div class="dashboard-card-body">
              <div class="dashboard-total">
                <span class="total-value">{{ overtimeStats.totalHours ?? '-' }}</span>
                <span class="total-unit">小时</span>
              </div>
              <div class="dashboard-meta">共 {{ overtimeStats.personCount ?? 0 }} 人</div>
              <div v-if="overtimeStats.list?.length" class="dashboard-list">
                <div class="list-title">按人明细</div>
                <ul class="person-list">
                  <li v-for="item in overtimeStats.list" :key="item.name" class="person-item">
                    <span class="person-name">{{ item.name }}</span>
                    <span class="person-value">{{ item.hours }} 小时</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          <div class="dashboard-card trip-card card">
            <div class="dashboard-card-header">
              <svg class="dashboard-card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/>
                <circle cx="12" cy="10" r="3"/>
              </svg>
              <h3>公出汇总</h3>
            </div>
            <div class="dashboard-card-body">
              <div class="dashboard-total">
                <span class="total-value">{{ tripStats.totalDays ?? '-' }}</span>
                <span class="total-unit">天</span>
              </div>
              <div class="dashboard-meta">共 {{ tripStats.personCount ?? 0 }} 人</div>
              <div v-if="tripStats.list?.length" class="dashboard-list">
                <div class="list-title">按人明细</div>
                <ul class="person-list">
                  <li v-for="item in tripStats.list" :key="item.name" class="person-item">
                    <span class="person-name">{{ item.name }}</span>
                    <span class="person-value">{{ item.days }} 天</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <!-- 满勤率：支持单月与全年，无请假即视为满勤 -->
        <div v-if="hasFetched && (filterMonth || (fullAttendance.totalPeople != null && fullAttendance.totalPeople > 0))" class="section card full-attendance-section">
          <h2 class="section-title">
            <span>满勤率</span>
            <span class="section-sub">{{ filterYear }}年{{ filterMonth ? filterMonth + '月' : '全年' }}</span>
          </h2>
          <p class="section-desc">{{ filterMonth ? '当月没有请假即视为满勤' : '全年没有请假即视为满勤' }}（仅统计已通过请假记录）。</p>
          <div v-if="fullAttendance.totalPeople != null" class="full-attendance-content">
            <div class="full-attendance-summary">
              <div v-if="fullAttendance.workdays != null" class="fa-item">
                <span class="fa-label">应出勤工作日</span>
                <span class="fa-value">{{ fullAttendance.workdays }} 天</span>
              </div>
              <div class="fa-item">
                <span class="fa-label">全员满勤率</span>
                <span class="fa-value">{{ ((fullAttendance.rate ?? 0) * 100).toFixed(1) }}%</span>
                <span class="fa-meta">满勤 {{ fullAttendance.fullCount ?? 0 }} / {{ fullAttendance.totalPeople ?? 0 }} 人</span>
              </div>
            </div>
            <div v-if="fullAttendance.byDept?.length" class="full-attendance-depts">
              <div class="fa-dept-title">各科室满勤率</div>
              <div class="fa-dept-grid">
                <div v-for="d in fullAttendance.byDept" :key="d.lsys" class="fa-dept-card">
                  <span class="fa-dept-name">{{ d.lsys }}</span>
                  <span class="fa-dept-rate">{{ (d.rate * 100).toFixed(1) }}%</span>
                  <span class="fa-dept-meta">{{ d.fullCount }}/{{ d.totalPeople }} 人</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 满勤人数柱状图：横轴月，纵轴满勤人数，可筛科室 -->
        <div v-if="hasFetched" class="section card full-count-chart-section">
          <h2 class="section-title">满勤人数柱状图</h2>
          <div class="chart-filter-row">
            <label class="chart-filter-label">科室</label>
            <select v-model="chartLsys" class="form-select chart-filter-select" @change="fetchFullAttendanceChart">
              <option value="">全部</option>
              <option v-for="d in chartDeptOptions" :key="d" :value="d">{{ d }}</option>
            </select>
            <span class="chart-filter-hint">{{ filterYear }}年 · 横轴月，纵轴满勤人数</span>
          </div>
          <div class="bar-chart-wrap full-count-chart">
            <div class="bar-chart-months">
              <div v-for="item in fullAttendanceByMonth" :key="item.month" class="bar-month-group">
                <div class="bar-month-area">
                  <div
                    class="bar-month-bar"
                    :style="{ height: getFullCountBarHeightPx(item.fullCount, maxFullCountChart) }"
                    :title="`${item.monthLabel} 满勤 ${item.fullCount} 人`"
                  >
                    <span v-if="item.fullCount > 0" class="bar-month-value">{{ item.fullCount }}</span>
                  </div>
                </div>
                <div class="bar-month-label">{{ item.monthLabel }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 科室横向对比柱状图：筛选展示加班/请假/公出其一 -->
        <div v-if="hasFetched && deptComparison.list?.length" class="section card chart-section">
          <h2 class="section-title">科室横向对比</h2>
          <p class="section-desc">各科室加班、请假、公出（可选月份为当月，未选为全年）</p>
          <div class="chart-filter-row">
            <label class="chart-filter-label">展示</label>
            <div class="chart-type-tabs">
              <button
                v-for="t in compareChartTypes"
                :key="t.type"
                :class="['tab-btn', 'tab-btn-sm', { active: compareChartType === t.type }]"
                @click="compareChartType = t.type"
              >
                {{ t.label }}{{ t.unit }}
              </button>
            </div>
          </div>
          <div class="bar-chart-wrap">
            <div class="bar-chart-total bar-chart-single">
              <div v-for="row in deptComparisonSorted" :key="row.lsys" class="bar-group">
                <div class="bar-col">
                  <div
                    class="bar bar-has-value"
                    :class="compareChartBarClass"
                    :style="{ height: getCompareBarHeight(compareChartTotalValue(row), compareChartMaxTotal) }"
                    :title="compareChartTotalTitle(row)"
                  >
                    <span class="bar-value">{{ compareChartTotalValue(row) }}</span>
                  </div>
                </div>
                <div class="bar-label">{{ row.lsys }}</div>
              </div>
            </div>
          </div>
          <h3 class="chart-subtitle">人均</h3>
          <div class="bar-chart-wrap">
            <div class="bar-chart-total bar-chart-single">
              <div v-for="row in deptComparisonSorted" :key="'pc-' + row.lsys" class="bar-group">
                <div class="bar-col">
                  <div
                    class="bar bar-has-value"
                    :class="compareChartBarClass"
                    :style="{ height: getCompareBarHeight(compareChartPerCapitaValue(row), compareChartMaxPc) }"
                    :title="compareChartPerCapitaTitle(row)"
                  >
                    <span class="bar-value">{{ compareChartPerCapitaValue(row) }}</span>
                  </div>
                </div>
                <div class="bar-label">{{ row.lsys }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 全体员工排序 -->
        <div v-if="hasFetched" class="section card rankings-section">
          <h2 class="section-title">全体员工排序</h2>
          <div class="rankings-tabs">
            <button v-for="t in rankingTypes" :key="t.type" :class="['tab-btn', { active: rankingType === t.type }]" @click="rankingType = t.type">
              {{ t.label }}
            </button>
          </div>
          <div class="rankings-table-wrap">
            <table class="rankings-table">
              <thead>
                <tr>
                  <th>排名</th>
                  <th>姓名</th>
                  <th>科室</th>
                  <th>{{ currentRankingUnit }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in currentRankingList" :key="r.name + r.lsys">
                  <td>{{ r.rank }}</td>
                  <td>{{ r.name }}</td>
                  <td>{{ r.lsys }}</td>
                  <td class="rank-value">{{ r.value }} {{ r.unit }}</td>
                </tr>
              </tbody>
            </table>
            <div v-if="!currentRankingList.length && !loading" class="empty-rankings">暂无数据</div>
          </div>
        </div>

        <!-- 未查询时的提示 -->
        <div v-if="!hasFetched && !loading" class="init-hint card">
          <p>选择年份（可选月份）后点击「查询」查看本科室汇总、满勤率、科室对比与全员排序。</p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import {
  getStatisticsPermission,
  getDeptLsysList,
  getDeptLeaveStats,
  getDeptOvertimeStats,
  getDeptBusinessTripStats,
  getLeaderFullAttendance,
  getLeaderFullAttendanceYear,
  getLeaderFullAttendanceByMonth,
  getLeaderDeptComparison,
  getLeaderRankings
} from '@/api/attendance'

const lsys = ref('')
const permLevel = ref(1)
/** 部长/副部长可选任意科室；组长/主任仅本科室，与 lsys 一致 */
const selectedLsys = ref('')
const lsysList = ref([])
const canViewDept = computed(() => (permLevel.value === 2 && !!lsys.value) || permLevel.value === 3)

const filterYear = ref(new Date().getFullYear())
const filterMonth = ref('')
const loading = ref(false)
const hasFetched = ref(false)

const leaveStats = ref({})
const overtimeStats = ref({})
const tripStats = ref({})

const fullAttendance = ref({})
const fullAttendanceByMonth = ref([])
const chartLsys = ref('')
const deptComparison = ref({ list: [] })
/** 科室横向对比图筛选：overtime | leave | trip */
const compareChartType = ref('overtime')
const compareChartTypes = [
  { type: 'overtime', label: '加班', unit: '(小时)' },
  { type: 'leave', label: '请假', unit: '(天)' },
  { type: 'trip', label: '公出', unit: '(天)' }
]
const rankingsOvertime = ref([])
const rankingsLeave = ref([])
const rankingsTrip = ref([])
const rankingType = ref('overtime')
const rankingTypes = [
  { type: 'overtime', label: '加班' },
  { type: 'leave', label: '请假' },
  { type: 'trip', label: '公出' }
]

const currentRankingList = computed(() => {
  if (rankingType.value === 'overtime') return rankingsOvertime.value
  if (rankingType.value === 'leave') return rankingsLeave.value
  return rankingsTrip.value
})
const currentRankingUnit = computed(() => {
  if (rankingType.value === 'overtime') return '小时'
  return '天'
})

const maxCompareOvertime = computed(() => {
  const list = deptComparison.value?.list || []
  if (!list.length) return 1
  return Math.max(...list.map(r => r.overtimeTotal), 1)
})
const maxCompareLeave = computed(() => {
  const list = deptComparison.value?.list || []
  if (!list.length) return 1
  return Math.max(...list.map(r => r.leaveTotal), 1)
})
const maxCompareTrip = computed(() => {
  const list = deptComparison.value?.list || []
  if (!list.length) return 1
  return Math.max(...list.map(r => r.tripTotal), 1)
})
const maxCompareOvertimePc = computed(() => {
  const list = deptComparison.value?.list || []
  if (!list.length) return 1
  return Math.max(...list.map(r => r.overtimePerCapita), 0.01)
})
const maxCompareLeavePc = computed(() => {
  const list = deptComparison.value?.list || []
  if (!list.length) return 1
  return Math.max(...list.map(r => r.leavePerCapita), 0.01)
})
const maxCompareTripPc = computed(() => {
  const list = deptComparison.value?.list || []
  if (!list.length) return 1
  return Math.max(...list.map(r => r.tripPerCapita), 0.01)
})

function getCompareBarHeight(value, max) {
  if (value == null || !max) return '0%'
  const pct = (value / max) * 100
  return `${Math.max(pct, 4)}%`
}

const compareChartBarClass = computed(() => {
  if (compareChartType.value === 'overtime') return 'bar-ot'
  if (compareChartType.value === 'leave') return 'bar-lv'
  return 'bar-tr'
})
/** 科室横向对比：按当前展示类型（加班/请假/公出）数值从高到低排序，柱状图从左到右由高到低 */
const deptComparisonSorted = computed(() => {
  const list = deptComparison.value?.list || []
  if (!list.length) return []
  return [...list].sort((a, b) => (compareChartTotalValue(b) - compareChartTotalValue(a)))
})
const compareChartMaxTotal = computed(() => {
  if (compareChartType.value === 'overtime') return maxCompareOvertime.value
  if (compareChartType.value === 'leave') return maxCompareLeave.value
  return maxCompareTrip.value
})
const compareChartMaxPc = computed(() => {
  if (compareChartType.value === 'overtime') return maxCompareOvertimePc.value
  if (compareChartType.value === 'leave') return maxCompareLeavePc.value
  return maxCompareTripPc.value
})
function compareChartTotalValue(row) {
  if (compareChartType.value === 'overtime') return row.overtimeTotal
  if (compareChartType.value === 'leave') return row.leaveTotal
  return row.tripTotal
}
function compareChartPerCapitaValue(row) {
  if (compareChartType.value === 'overtime') return row.overtimePerCapita
  if (compareChartType.value === 'leave') return row.leavePerCapita
  return row.tripPerCapita
}
function compareChartTotalTitle(row) {
  const v = compareChartTotalValue(row)
  if (compareChartType.value === 'overtime') return `加班 ${v} 小时`
  return `${compareChartTypes.find(t => t.type === compareChartType.value)?.label || ''} ${v} 天`
}
function compareChartPerCapitaTitle(row) {
  const v = compareChartPerCapitaValue(row)
  if (compareChartType.value === 'overtime') return `人均加班 ${v} 小时`
  return `人均${compareChartTypes.find(t => t.type === compareChartType.value)?.label || ''} ${v} 天`
}

const yearOptions = computed(() => {
  const currentYear = new Date().getFullYear()
  const years = []
  for (let y = currentYear; y >= currentYear - 5; y--) years.push(y)
  return years
})

const chartDeptOptions = computed(() => {
  if (permLevel.value === 3) return lsysList.value
  return lsys.value ? [lsys.value] : []
})

const maxFullCountChart = computed(() => {
  const list = fullAttendanceByMonth.value
  if (!list.length) return 1
  return Math.max(...list.map(i => i.fullCount), 1)
})

/** 满勤柱状图柱区固定高度(px)，所有柱子在此高度内按比例绘制，底部对齐 */
const FULL_COUNT_BAR_AREA_PX = 180

function getFullCountBarHeightPx(value, max) {
  if (value == null || !max) return '8px'
  const pct = value / max
  const px = Math.max(8, Math.round(pct * FULL_COUNT_BAR_AREA_PX))
  return `${px}px`
}

const fetchFullAttendanceChart = async () => {
  try {
    const res = await getLeaderFullAttendanceByMonth({
      year: filterYear.value,
      lsys: chartLsys.value || undefined
    })
    if (res.success && res.list) fullAttendanceByMonth.value = res.list
    else fullAttendanceByMonth.value = []
  } catch (e) {
    fullAttendanceByMonth.value = []
  }
}

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
      lsys.value = (res.lsys || '').trim()
      if (permLevel.value === 2) {
        selectedLsys.value = lsys.value
      } else if (permLevel.value === 3) {
        const listRes = await getDeptLsysList()
        if (listRes.success && listRes.list?.length) {
          lsysList.value = listRes.list
          selectedLsys.value = '' // 默认全员
        }
      }
    }
  } catch (e) {
    permLevel.value = 1
    lsys.value = ''
    selectedLsys.value = ''
    lsysList.value = []
  }
}

const fetchData = async () => {
  const lsysToUse = permLevel.value === 3 ? selectedLsys.value : lsys.value
  // 部长可选全员(空)；组长/主任必须有科室
  if (permLevel.value !== 3 && !lsysToUse) return
  loading.value = true
  hasFetched.value = true
  const params = { year: filterYear.value }
  if (lsysToUse) params.lsys = lsysToUse
  if (filterMonth.value) params.month = parseInt(filterMonth.value)
  const year = filterYear.value
  const month = filterMonth.value ? parseInt(filterMonth.value) : undefined
  const baseParams = { year, month }
  try {
    const [
      leaveRes,
      overtimeRes,
      tripRes,
      fullAttRes,
      deptCompRes,
      rankOtRes,
      rankLvRes,
      rankTrRes
    ] = await Promise.all([
      getDeptLeaveStats(params),
      getDeptOvertimeStats(params),
      getDeptBusinessTripStats(params),
      filterMonth.value ? getLeaderFullAttendance({ year, month, lsys: lsysToUse || undefined }) : getLeaderFullAttendanceYear({ year, lsys: lsysToUse || undefined }),
      getLeaderDeptComparison(month ? { year, month } : { year }),
      getLeaderRankings({ ...baseParams, type: 'overtime' }),
      getLeaderRankings({ ...baseParams, type: 'leave' }),
      getLeaderRankings({ ...baseParams, type: 'trip' })
    ])
    if (leaveRes.success) leaveStats.value = leaveRes
    if (overtimeRes.success) overtimeStats.value = overtimeRes
    if (tripRes.success) tripStats.value = tripRes
    if (fullAttRes?.success) fullAttendance.value = fullAttRes
    if (deptCompRes?.success) deptComparison.value = deptCompRes
    if (rankOtRes?.success) rankingsOvertime.value = rankOtRes.list || []
    if (rankLvRes?.success) rankingsLeave.value = rankLvRes.list || []
    if (rankTrRes?.success) rankingsTrip.value = rankTrRes.list || []
    await fetchFullAttendanceChart()
  } catch (error) {
    console.error('领导人看板数据加载失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadPermission()
  await nextTick()
  // 有科室权限时默认查询（部长默认全员全年，组长/主任为本科室）
  if (canViewDept.value && (permLevel.value === 3 ? true : !!lsys.value)) {
    fetchData()
  }
})
</script>

<style scoped>
.leader-dashboard-page {
  min-height: 100vh;
  background: var(--color-bg-layout);
}

.leader-dashboard-page .page-header {
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

.leader-dashboard-page .container {
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

/* 无权限 */
.no-permission {
  padding: var(--spacing-xxxl);
  text-align: center;
}

.no-permission-content { max-width: 420px; margin: 0 auto; }

.no-permission-icon {
  width: 56px;
  height: 56px;
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-lg);
}

.no-permission-content h3 {
  font-size: var(--font-size-xl);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-md);
}

.no-permission-content p {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-xl);
}

/* 筛选：滚动时固定在顶端 */
.filter-section {
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
  position: sticky;
  top: 0;
  z-index: 10;
}

.filter-form {
  display: flex;
  gap: var(--spacing-xl);
  align-items: flex-end;
  flex-wrap: wrap;
}

.form-item { display: flex; flex-direction: column; gap: var(--spacing-sm); }

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
  min-width: 160px;
}

.form-input[readonly] { background: var(--color-bg-spotlight); cursor: default; }

.form-actions { margin-left: auto; }

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
}

.btn-primary { background: var(--color-primary); color: white; }

.btn-primary:hover:not(:disabled) { filter: brightness(1.05); }

.btn-primary:disabled { opacity: 0.7; cursor: not-allowed; }

.loading-icon { width: 18px; height: 18px; }

/* 看板卡片 */
.dashboard-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--spacing-xl);
}

.dashboard-card {
  overflow: hidden;
}

.dashboard-card-header {
  padding: var(--spacing-lg) var(--spacing-xl);
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.dashboard-card-icon { width: 24px; height: 24px; flex-shrink: 0; }

.dashboard-card h3 {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.leave-card .dashboard-card-header { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; }
.leave-card .dashboard-card-header .dashboard-card-icon { color: white; }
.leave-card .dashboard-card-header h3 { color: white; }

.overtime-card .dashboard-card-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
.overtime-card .dashboard-card-header .dashboard-card-icon { color: white; }
.overtime-card .dashboard-card-header h3 { color: white; }

.trip-card .dashboard-card-header { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; }
.trip-card .dashboard-card-header .dashboard-card-icon { color: white; }
.trip-card .dashboard-card-header h3 { color: white; }

.dashboard-card-body { padding: var(--spacing-xl); }

.dashboard-total {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-sm);
}

.total-value { font-size: var(--font-size-huge); font-weight: var(--font-weight-bold); color: var(--color-text-primary); }

.total-unit { font-size: var(--font-size-md); color: var(--color-text-secondary); }

.dashboard-meta { font-size: var(--font-size-sm); color: var(--color-text-secondary); margin-bottom: var(--spacing-lg); }

.dashboard-list { margin-top: var(--spacing-md); padding-top: var(--spacing-md); border-top: 1px solid var(--color-border-lighter); }

.list-title { font-size: var(--font-size-sm); font-weight: var(--font-weight-medium); color: var(--color-text-secondary); margin-bottom: var(--spacing-sm); }

.person-list { list-style: none; padding: 0; margin: 0; max-height: 200px; overflow-y: auto; }

.person-item {
  display: flex;
  justify-content: space-between;
  padding: var(--spacing-xs) 0;
  font-size: var(--font-size-sm);
  border-bottom: 1px solid var(--color-border-lighter);
}

.person-item:last-child { border-bottom: none; }

.person-name { color: var(--color-text-primary); }

.person-value { color: var(--color-primary); font-weight: var(--font-weight-medium); }

.init-hint {
  padding: var(--spacing-xl);
  text-align: center;
  color: var(--color-text-secondary);
}

/* 区块标题 */
.section { padding: var(--spacing-xl); margin-bottom: var(--spacing-xl); }
.section-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-md);
  display: flex;
  align-items: baseline;
  gap: var(--spacing-md);
}
.section-sub { font-size: var(--font-size-sm); color: var(--color-text-secondary); font-weight: normal; }
.section-icon { width: 24px; height: 24px; color: var(--color-primary); flex-shrink: 0; }
.section-desc, .section-desc + .chart-legend { margin-bottom: var(--spacing-md); font-size: var(--font-size-sm); color: var(--color-text-secondary); }

/* 满勤率 */
.full-attendance-content { margin-top: var(--spacing-md); }
.full-attendance-summary {
  display: flex;
  gap: var(--spacing-xl);
  flex-wrap: wrap;
  margin-bottom: var(--spacing-lg);
}
.fa-item { display: flex; flex-direction: column; gap: var(--spacing-xs); }
.fa-label { font-size: var(--font-size-sm); color: var(--color-text-secondary); }
.fa-value { font-size: var(--font-size-xl); font-weight: var(--font-weight-bold); color: var(--color-primary); }
.fa-meta { font-size: var(--font-size-sm); color: var(--color-text-tertiary); }
.fa-dept-title { font-size: var(--font-size-sm); font-weight: var(--font-weight-medium); color: var(--color-text-secondary); margin-bottom: var(--spacing-sm); }
.fa-dept-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: var(--spacing-md); }
.fa-dept-card {
  padding: var(--spacing-md);
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--radius-base);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}
.fa-dept-name { font-weight: var(--font-weight-medium); color: var(--color-text-primary); }
.fa-dept-rate { font-size: var(--font-size-lg); color: var(--color-primary); }
.fa-dept-meta { font-size: var(--font-size-xs); color: var(--color-text-tertiary); }

/* 科室对比柱状图 */
.chart-filter-row { display: flex; align-items: center; gap: var(--spacing-md); margin-bottom: var(--spacing-lg); flex-wrap: wrap; }
.chart-filter-label { font-size: var(--font-size-sm); color: var(--color-text-secondary); }
.chart-type-tabs { display: flex; gap: var(--spacing-sm); }
.tab-btn-sm { padding: var(--spacing-xs) var(--spacing-md); font-size: var(--font-size-sm); }
.bar-chart-wrap { margin-bottom: var(--spacing-xl); }
.bar-chart-wrap:last-child { margin-bottom: 0; }
.chart-subtitle { font-size: var(--font-size-md); color: var(--color-text-secondary); margin: var(--spacing-lg) 0 var(--spacing-sm); }
.bar-chart-total {
  display: flex;
  gap: var(--spacing-sm);
  height: 200px;
  align-items: stretch;
  padding-top: 28px;
  padding-bottom: var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
  overflow-x: auto;
  overflow-y: visible;
  box-sizing: content-box;
}
.bar-chart-single .bar-group .bar-col { min-width: 28px; }
.bar-group { flex: 1; min-width: 60px; display: flex; flex-direction: column; align-items: center; height: 100%; min-height: 0; }
.bar-group .bars { flex: 1; display: flex; gap: 4px; align-items: flex-end; width: 100%; justify-content: center; min-height: 0; }
.bar-group .bar-col { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; flex: 1; min-width: 20px; min-height: 0; }
.bar-group .bar { width: 20px; min-height: 4px; border-radius: 4px 4px 0 0; transition: height 0.2s; }
.bar-group .bar-has-value { position: relative; }
/* 柱顶数值相对柱子顶部定位，始终在柱子上方，不与高柱重叠 */
.bar-group .bar-has-value .bar-value { position: absolute; top: 0; left: 50%; transform: translate(-50%, calc(-100% - 4px)); font-size: var(--font-size-xs); color: var(--color-text-secondary); white-space: nowrap; pointer-events: none; }
.bar-chart-single .bar-group .bar { width: 28px; }
.bar-group .bar-ot { background: linear-gradient(180deg, #667eea 0%, #764ba2 100%); }
.bar-group .bar-lv { background: linear-gradient(180deg, #f093fb 0%, #f5576c 100%); }
.bar-group .bar-tr { background: linear-gradient(180deg, #4facfe 0%, #00f2fe 100%); }
.bar-group .bar-label { font-size: var(--font-size-xs); color: var(--color-text-tertiary); margin-top: var(--spacing-sm); text-align: center; }

/* 全员排序 */
.rankings-tabs { display: flex; gap: var(--spacing-sm); margin-bottom: var(--spacing-lg); }
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
.tab-btn:hover { border-color: var(--color-primary); color: var(--color-primary); }
.tab-btn.active { background: var(--color-primary); color: white; border-color: var(--color-primary); }
.rankings-table-wrap { max-height: 400px; overflow-y: auto; }
.rankings-table { width: 100%; border-collapse: collapse; }
.rankings-table th, .rankings-table td { padding: var(--spacing-md); text-align: left; border-bottom: 1px solid var(--color-border-lighter); }
.rankings-table th { font-size: var(--font-size-sm); font-weight: var(--font-weight-medium); color: var(--color-text-secondary); background: var(--color-bg-spotlight); }
.rankings-table td { font-size: var(--font-size-sm); color: var(--color-text-primary); }
.rankings-table .rank-value { font-weight: var(--font-weight-medium); color: var(--color-primary); }
.empty-rankings { text-align: center; padding: var(--spacing-xxl); color: var(--color-text-tertiary); }

/* 满勤人数柱状图 */
.chart-filter-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
  flex-wrap: wrap;
}
.chart-filter-label { font-size: var(--font-size-sm); color: var(--color-text-secondary); font-weight: var(--font-weight-medium); }
.chart-filter-select { width: 160px; }
.chart-filter-hint { font-size: var(--font-size-sm); color: var(--color-text-tertiary); }
.full-count-chart .bar-chart-months {
  display: flex;
  gap: var(--spacing-sm);
  height: 240px;
  align-items: flex-end;
  padding-bottom: var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
}
.full-count-chart .bar-month-group {
  flex: 1;
  min-width: 36px;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}
/* 固定高度柱区：所有柱子在此高度内绘制，底部贴 X 轴，顶部随数值起伏 */
.full-count-chart .bar-month-area {
  width: 100%;
  max-width: 32px;
  height: 180px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
  flex-shrink: 0;
}
.full-count-chart .bar-month-bar {
  width: 100%;
  max-width: 32px;
  min-height: 8px;
  border-radius: 6px 6px 0 0;
  background: linear-gradient(180deg, #0d9488 0%, #0f766e 100%);
  transition: height 0.2s;
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 4px;
  flex-shrink: 0;
}
.full-count-chart .bar-month-value {
  font-size: var(--font-size-xs);
  color: white;
  font-weight: var(--font-weight-medium);
  text-shadow: 0 0 1px rgba(0,0,0,0.5);
}
.full-count-chart .bar-month-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-top: var(--spacing-sm);
  flex-shrink: 0;
}
@media (max-width: 768px) {
  .filter-form { flex-direction: column; align-items: stretch; }
  .form-actions { margin-left: 0; }
  .dashboard-cards { grid-template-columns: 1fr; }
  .bar-chart-total { min-width: 400px; }
  .fa-dept-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
