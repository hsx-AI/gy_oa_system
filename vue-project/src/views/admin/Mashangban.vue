<template>
  <div class="msb-page">
    <div class="container">
      <header class="page-header">
        <div>
          <h1>工艺码上办月报</h1>
          <p>支持单月 / 区间 / 全年统计（admin1、经理层、各科室主任/副主任/班组长）</p>
        </div>
        <div class="header-actions">
          <button
            type="button"
            class="btn btn-export"
            :disabled="loading || exportLoading || !activeMonths.length"
            @click="handleExportExcel"
          >
            {{ exportLoading ? '导出中…' : '导出报表' }}
          </button>
          <button type="button" class="btn" :disabled="loading" @click="reloadAll">
            {{ loading ? '加载中…' : '刷新' }}
          </button>
        </div>
      </header>

      <div v-if="!canAccess" class="card tip">
        <p>您暂无权限访问此页面。仅系统管理员（admin1）、经理/副经理/经理助理，以及各科室主任/副主任/班组长可见。</p>
        <router-link to="/" class="btn">返回首页</router-link>
      </div>

      <template v-else>
        <div class="card toolbar top-bar">
          <label>
            统计方式
            <select v-model="rangeMode" @change="onRangeModeChange">
              <option value="month">单月</option>
              <option value="range">区间</option>
              <option value="year">全年</option>
            </select>
          </label>

          <template v-if="rangeMode === 'month'">
            <label>
              月份
              <select v-model="monthStart" @change="onRangeChange">
                <option v-if="!monthOptions.length" value="">暂无入库月份</option>
                <option v-for="m in monthOptions" :key="m" :value="m">{{ m }}</option>
              </select>
            </label>
          </template>

          <template v-else-if="rangeMode === 'range'">
            <label>
              起始月
              <select v-model="monthStart" @change="onRangeChange">
                <option v-for="m in monthOptions" :key="'s-' + m" :value="m">{{ m }}</option>
              </select>
            </label>
            <span class="range-sep">至</span>
            <label>
              结束月
              <select v-model="monthEnd" @change="onRangeChange">
                <option v-for="m in monthOptions" :key="'e-' + m" :value="m">{{ m }}</option>
              </select>
            </label>
          </template>

          <template v-else>
            <label>
              年份
              <select v-model="selectedYear" @change="onYearChange">
                <option v-for="y in yearOptions" :key="y" :value="y">{{ y }} 全年</option>
              </select>
            </label>
          </template>

          <span v-if="activeMonths.length" class="meta">
            {{ rangeLabel }} · 覆盖 {{ activeMonths.length }} 个月 ·
            科室 {{ deptAll.length }} · 人员 {{ personAll.length }} · 工单 {{ orderAll.length }}
          </span>
        </div>

        <section v-if="rangeMode === 'year' && activeMonths.length" class="chart-dashboard">
          <div class="kpi-grid">
            <div v-for="card in summaryKpiCards" :key="card.key" class="kpi-card" :class="`kpi-${card.key}`">
              <span class="kpi-label">{{ card.label }}</span>
              <strong class="kpi-value">{{ card.value }}</strong>
              <span class="kpi-hint">{{ card.hint }}</span>
            </div>
          </div>
          <div class="chart-grid chart-grid-2">
            <div class="chart-card">
              <v-chart class="chart-box" :option="yearOrderTrendOption" autoresize />
            </div>
            <div class="chart-card">
              <v-chart class="chart-box" :option="yearHoursTrendOption" autoresize />
            </div>
            <div class="chart-card">
              <v-chart class="chart-box" :option="yearAvgServiceTrendOption" autoresize />
            </div>
            <div class="chart-card">
              <v-chart class="chart-box" :option="yearStatusTrendOption" autoresize />
            </div>
          </div>
        </section>

        <div class="tabs">
          <button type="button" :class="{ active: activeTab === 'dept' }" @click="activeTab = 'dept'">
            科室统计
          </button>
          <button type="button" :class="{ active: activeTab === 'person' }" @click="activeTab = 'person'">
            人员服务绩效
          </button>
          <button type="button" :class="{ active: activeTab === 'order' }" @click="activeTab = 'order'">
            工单明细
          </button>
        </div>

        <!-- 科室统计 -->
        <section v-show="activeTab === 'dept'" class="card">
          <div class="filters">
            <label>
              科室
              <select v-model="deptFilter.dept">
                <option value="">全部</option>
                <option v-for="d in allDeptNames" :key="d" :value="d">{{ d }}</option>
              </select>
            </label>
            <label>
              工单数 ≥
              <input v-model.number="deptFilter.minOrders" type="number" min="0" placeholder="0" />
            </label>
            <label>
              总服务时长 ≥
              <input v-model.number="deptFilter.minHours" type="number" min="0" step="0.1" placeholder="0" />
            </label>
            <label>
              关键词
              <input v-model.trim="deptFilter.keyword" type="search" placeholder="科室名" />
            </label>
            <button type="button" class="btn btn-ghost" @click="resetDeptFilter">重置</button>
            <span class="meta">显示 {{ filteredDeptRows.length }} / {{ deptAll.length }}</span>
          </div>

          <div v-if="!deptFilter.dept && deptChartRows.length" class="dept-chart-panel">
            <div class="chart-grid chart-grid-2">
              <div class="chart-card chart-card-inner">
                <v-chart class="chart-box chart-box-md" :option="deptOrderBarOption" autoresize />
              </div>
              <div class="chart-card chart-card-inner">
                <v-chart class="chart-box chart-box-md" :option="deptHoursBarOption" autoresize />
              </div>
            </div>
          </div>

          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th v-for="col in deptColumns" :key="col.key" class="sortable" @click="toggleSort('dept', col.key)">
                    {{ col.label }}
                    <span class="sort-mark">{{ sortMark('dept', col.key) }}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!filteredDeptRows.length">
                  <td :colspan="deptColumns.length" class="empty">暂无匹配数据</td>
                </tr>
                <tr v-for="row in filteredDeptRows" :key="row.deptName">
                  <td>{{ row.deptName }}</td>
                  <td>{{ row.orderCount ?? '-' }}</td>
                  <td>{{ fmtNum(row.totalServiceHours) }}</td>
                  <td>{{ fmtNum(row.avgServiceHours) }}</td>
                  <td>{{ fmtNum(row.avgAcceptHours) }}</td>
                  <td>{{ fmtNum(row.avgArriveHours) }}</td>
                  <td>{{ row.pendingAccept ?? '-' }}</td>
                  <td>{{ row.pendingArrive ?? '-' }}</td>
                  <td>{{ row.processing ?? '-' }}</td>
                  <td>{{ row.pendingConfirm ?? '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- 人员绩效 -->
        <section v-show="activeTab === 'person'" class="card">
          <div class="filters">
            <label>
              科室
              <select v-model="personFilter.dept">
                <option value="">全部</option>
                <option v-for="d in allDeptNames" :key="d" :value="d">{{ d }}</option>
              </select>
            </label>
            <label>
              姓名
              <input v-model.trim="personFilter.name" type="search" placeholder="姓名关键词" />
            </label>
            <label>
              服务频次 ≥
              <input v-model.number="personFilter.minService" type="number" min="0" placeholder="0" />
            </label>
            <label>
              总服务时长 ≥
              <input v-model.number="personFilter.minHours" type="number" min="0" step="0.1" placeholder="0" />
            </label>
            <label>
              有评价
              <select v-model="personFilter.hasRate">
                <option value="">全部</option>
                <option value="1">有评价</option>
                <option value="0">无评价</option>
              </select>
            </label>
            <button type="button" class="btn btn-ghost" @click="resetPersonFilter">重置</button>
            <span class="meta">显示 {{ filteredPersonRows.length }} / {{ personAll.length }}</span>
          </div>

          <div v-if="personPodiumRows.length" class="person-visual-panel">
            <div class="podium-grid">
              <div
                v-for="(row, idx) in personPodiumRows"
                :key="`${row.deptName}-${row.employeeName}`"
                class="podium-card"
                :class="`podium-${idx + 1}`"
              >
                <div class="podium-rank">{{ podiumMedal(idx) }}</div>
                <div class="podium-name">{{ row.employeeName }}</div>
                <div class="podium-dept">{{ row.deptName }}</div>
                <div class="podium-metrics">
                  <span>服务 {{ row.serviceCount ?? 0 }} 次</span>
                  <span>{{ fmtNum(row.totalServiceHours) }} 小时</span>
                </div>
              </div>
            </div>
            <div class="chart-card chart-card-inner">
              <v-chart class="chart-box chart-box-lg" :option="personTopBarOption" autoresize />
            </div>
          </div>

          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th class="rank-col">排名</th>
                  <th v-for="col in personColumns" :key="col.key" class="sortable" @click="toggleSort('person', col.key)">
                    {{ col.label }}
                    <span class="sort-mark">{{ sortMark('person', col.key) }}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!filteredPersonRows.length">
                  <td :colspan="personColumns.length + 1" class="empty">暂无匹配数据</td>
                </tr>
                <tr
                  v-for="row in filteredPersonRows"
                  :key="`${row.deptName}-${row.employeeName}`"
                  :class="personRowClassByRow(row)"
                >
                  <td class="rank-cell">
                    <span class="rank-badge" :class="rankBadgeClassByRow(row)">{{ personRankLabelByRow(row) }}</span>
                  </td>
                  <td>{{ row.deptName }}</td>
                  <td>
                    <span class="name-with-badge">{{ row.employeeName }}</span>
                  </td>
                  <td>
                    <div class="metric-cell">
                      <span>{{ row.serviceCount ?? '-' }}</span>
                      <div class="metric-bar-track">
                        <div class="metric-bar-fill" :style="{ width: personMetricWidth(row, 'serviceCount') }"></div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div class="metric-cell">
                      <span>{{ fmtNum(row.totalServiceHours) }}</span>
                      <div class="metric-bar-track metric-bar-hours">
                        <div class="metric-bar-fill" :style="{ width: personMetricWidth(row, 'totalServiceHours') }"></div>
                      </div>
                    </div>
                  </td>
                  <td>{{ typeCountsText(row) }}</td>
                  <td>{{ fmtNum(row.avgServiceHours) }}</td>
                  <td>{{ fmtNum(row.avgAcceptHours) }}</td>
                  <td>{{ fmtNum(row.avgArriveHours) }}</td>
                  <td>{{ row.patrolCount ?? '-' }}</td>
                  <td>{{ rateCountsText(row) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- 工单明细 -->
        <section v-show="activeTab === 'order'" class="card">
          <div class="filters">
            <label>
              科室
              <select v-model="orderFilter.dept" @change="orderPage = 1">
                <option value="">全部</option>
                <option v-for="d in allDeptNames" :key="d" :value="d">{{ d }}</option>
              </select>
            </label>
            <label>
              类型
              <select v-model="orderFilter.orderType" @change="orderPage = 1">
                <option value="">全部</option>
                <option v-for="t in orderTypeOptions" :key="t" :value="t">{{ t }}</option>
              </select>
            </label>
            <label>
              状态
              <select v-model="orderFilter.status" @change="orderPage = 1">
                <option value="">全部</option>
                <option v-for="s in orderStatusOptions" :key="s" :value="s">{{ s }}</option>
              </select>
            </label>
            <label>
              工艺员
              <select v-model="orderFilter.engineer" @change="orderPage = 1">
                <option value="">全部</option>
                <option v-for="n in engineerOptions" :key="n" :value="n">{{ n }}</option>
              </select>
            </label>
            <label>
              操作员
              <select v-model="orderFilter.operator" @change="orderPage = 1">
                <option value="">全部</option>
                <option v-for="n in operatorOptions" :key="n" :value="n">{{ n }}</option>
              </select>
            </label>
            <label>
              评价
              <select v-model="orderFilter.rating" @change="orderPage = 1">
                <option value="">全部</option>
                <option v-for="r in ratingOptions" :key="r" :value="r">{{ r }}</option>
              </select>
            </label>
            <label class="grow">
              关键词
              <input
                v-model.trim="orderFilter.keyword"
                type="search"
                placeholder="工单号 / 工件 / 工作号 / 说明"
                @input="orderPage = 1"
              />
            </label>
            <button type="button" class="btn btn-ghost" @click="resetOrderFilter">重置</button>
            <span class="meta">显示 {{ filteredOrderRows.length }} / {{ orderAll.length }}</span>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th v-for="col in orderColumns" :key="col.key" class="sortable" @click="toggleSort('order', col.key)">
                    {{ col.label }}
                    <span class="sort-mark">{{ sortMark('order', col.key) }}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="ordersLoading">
                  <td :colspan="orderColumns.length" class="empty">加载中…</td>
                </tr>
                <tr v-else-if="!pagedOrderRows.length">
                  <td :colspan="orderColumns.length" class="empty">暂无匹配数据</td>
                </tr>
                <tr v-for="row in pagedOrderRows" :key="row.orderNo">
                  <td>{{ row.orderNo }}</td>
                  <td>{{ row.deptName || '-' }}</td>
                  <td>{{ row.orderType || '-' }}</td>
                  <td>{{ row.orderStatus || '-' }}</td>
                  <td>{{ row.processEngineerName || '-' }}</td>
                  <td>{{ row.operatorName || '-' }}</td>
                  <td class="clip" :title="row.workpieceName || ''">{{ row.workpieceName || '-' }}</td>
                  <td>{{ row.workNo || '-' }}</td>
                  <td>{{ fmtTime(row.createdAt) }}</td>
                  <td>{{ row.ratingLabel || row.ratingScore || '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="pager">
            <button type="button" class="btn" :disabled="orderPage <= 1" @click="orderPage -= 1">上一页</button>
            <span>第 {{ orderPage }} / {{ orderTotalPages }} 页（筛选后 {{ filteredOrderRows.length }} 条）</span>
            <button type="button" class="btn" :disabled="orderPage >= orderTotalPages" @click="orderPage += 1">下一页</button>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import * as XLSX from 'xlsx'
import VChart from 'vue-echarts'
import { getUploadConfig } from '@/api/attendance'
import { canAccessMashangban } from '@/utils/roleMatch'
import {
  getColorBarChartOption,
  getHorizontalBarChartOption,
  getLineChartOption,
  getMultiLineChartOption,
} from '@/utils/chartConfig'
import {
  getMashangbanDept,
  getMashangbanMonths,
  getMashangbanOrders,
  getMashangbanPerson
} from '@/api/mashangban'

const canAccess = ref(false)
const loading = ref(false)
const exportLoading = ref(false)
const ordersLoading = ref(false)
const months = ref([])
const rangeMode = ref('month') // month | range | year
const monthStart = ref('')
const monthEnd = ref('')
const selectedYear = ref('')
const activeTab = ref('dept')

const deptAll = ref([])
const personAll = ref([])
const orderAll = ref([])
const monthlySnapshots = ref([])

const monthOptions = computed(() =>
  (months.value || []).map(m => m.yearMonth).filter(Boolean).sort().reverse()
)

const yearOptions = computed(() => {
  const years = new Set(monthOptions.value.map(m => m.slice(0, 4)))
  return Array.from(years).sort().reverse()
})

const activeMonths = computed(() => {
  if (!monthOptions.value.length) return []
  let start = monthStart.value
  let end = monthEnd.value
  if (rangeMode.value === 'month') {
    end = start
  } else if (rangeMode.value === 'year') {
    const year = selectedYear.value || (monthOptions.value[0] || '').slice(0, 4)
    const inYear = monthOptions.value.filter(m => m.startsWith(`${year}-`)).sort()
    return inYear
  }
  if (!start || !end) return []
  if (start > end) [start, end] = [end, start]
  return monthOptions.value.filter(m => m >= start && m <= end).sort()
})

const rangeLabel = computed(() => {
  const list = activeMonths.value
  if (!list.length) return '未选择'
  if (list.length === 1) return list[0]
  return `${list[0]} ~ ${list[list.length - 1]}`
})

const deptFilter = reactive({
  dept: '',
  minOrders: null,
  minHours: null,
  keyword: ''
})
const personFilter = reactive({
  dept: '',
  name: '',
  minService: null,
  minHours: null,
  hasRate: ''
})
const orderFilter = reactive({
  dept: '',
  orderType: '',
  status: '',
  engineer: '',
  operator: '',
  rating: '',
  keyword: ''
})

const sorts = reactive({
  dept: { key: 'orderCount', order: 'desc' },
  person: { key: 'serviceCount', order: 'desc' },
  order: { key: 'createdAt', order: 'desc' }
})

const orderPage = ref(1)
const orderPageSize = 40

const deptColumns = [
  { key: 'deptName', label: '科室' },
  { key: 'orderCount', label: '工单总数' },
  { key: 'totalServiceHours', label: '总服务时长' },
  { key: 'avgServiceHours', label: '平均服务' },
  { key: 'avgAcceptHours', label: '平均接单' },
  { key: 'avgArriveHours', label: '平均到场' },
  { key: 'pendingAccept', label: '未接单' },
  { key: 'pendingArrive', label: '待到场' },
  { key: 'processing', label: '处理中' },
  { key: 'pendingConfirm', label: '待确认' }
]

const personColumns = [
  { key: 'deptName', label: '科室' },
  { key: 'employeeName', label: '姓名' },
  { key: 'serviceCount', label: '服务频次' },
  { key: 'totalServiceHours', label: '总服务时长' },
  { key: 'typeCounts', label: '工单类型次数' },
  { key: 'avgServiceHours', label: '平均服务' },
  { key: 'avgAcceptHours', label: '平均接单' },
  { key: 'avgArriveHours', label: '平均到场' },
  { key: 'patrolCount', label: '巡视次数' },
  { key: 'rateCounts', label: '评价(很好/较好/一般/较差/很差)' }
]

const orderColumns = [
  { key: 'orderNo', label: '工单号' },
  { key: 'deptName', label: '科室' },
  { key: 'orderType', label: '类型' },
  { key: 'orderStatus', label: '状态' },
  { key: 'processEngineerName', label: '工艺员' },
  { key: 'operatorName', label: '操作员' },
  { key: 'workpieceName', label: '工件' },
  { key: 'workNo', label: '工作号' },
  { key: 'createdAt', label: '创建时间' },
  { key: 'ratingLabel', label: '评价' }
]

const collator = new Intl.Collator('zh-Hans-CN', { numeric: true, sensitivity: 'base' })

const allDeptNames = computed(() => {
  const set = new Set([
    ...deptAll.value.map(r => r.deptName),
    ...personAll.value.map(r => r.deptName),
    ...orderAll.value.map(r => r.deptName)
  ].filter(Boolean))
  return Array.from(set).sort(collator.compare)
})

const orderTypeOptions = computed(() => uniqueSorted(orderAll.value.map(r => r.orderType)))
const orderStatusOptions = computed(() => uniqueSorted(orderAll.value.map(r => r.orderStatus)))
const engineerOptions = computed(() => uniqueSorted(orderAll.value.map(r => r.processEngineerName)))
const operatorOptions = computed(() => uniqueSorted(orderAll.value.map(r => r.operatorName)))
const ratingOptions = computed(() => uniqueSorted(orderAll.value.map(r => r.ratingLabel || r.ratingScore)))

const filteredDeptRows = computed(() => {
  const rows = deptAll.value.filter(row => {
    if (deptFilter.dept && row.deptName !== deptFilter.dept) return false
    if (deptFilter.keyword && !String(row.deptName || '').includes(deptFilter.keyword)) return false
    if (isFilledNumber(deptFilter.minOrders) && Number(row.orderCount || 0) < Number(deptFilter.minOrders)) return false
    if (isFilledNumber(deptFilter.minHours) && Number(row.totalServiceHours || 0) < Number(deptFilter.minHours)) return false
    return true
  })
  return sortRows(rows, sorts.dept.key, sorts.dept.order, 'dept')
})

const filteredPersonRows = computed(() => {
  const rows = personAll.value.filter(row => {
    if (personFilter.dept && row.deptName !== personFilter.dept) return false
    if (personFilter.name && !String(row.employeeName || '').includes(personFilter.name)) return false
    if (isFilledNumber(personFilter.minService) && Number(row.serviceCount || 0) < Number(personFilter.minService)) return false
    if (isFilledNumber(personFilter.minHours) && Number(row.totalServiceHours || 0) < Number(personFilter.minHours)) return false
    const rateSum = Number(row.rateExcellent || 0) + Number(row.rateGood || 0) + Number(row.rateNormal || 0)
      + Number(row.ratePoor || 0) + Number(row.rateBad || 0)
    if (personFilter.hasRate === '1' && rateSum <= 0) return false
    if (personFilter.hasRate === '0' && rateSum > 0) return false
    return true
  })
  return sortRows(rows, sorts.person.key, sorts.person.order, 'person')
})

const filteredOrderRows = computed(() => {
  const kw = (orderFilter.keyword || '').toLowerCase()
  const rows = orderAll.value.filter(row => {
    if (orderFilter.dept && row.deptName !== orderFilter.dept) return false
    if (orderFilter.orderType && row.orderType !== orderFilter.orderType) return false
    if (orderFilter.status && row.orderStatus !== orderFilter.status) return false
    if (orderFilter.engineer && row.processEngineerName !== orderFilter.engineer) return false
    if (orderFilter.operator && row.operatorName !== orderFilter.operator) return false
    if (orderFilter.rating) {
      const rating = row.ratingLabel || row.ratingScore || ''
      if (rating !== orderFilter.rating) return false
    }
    if (kw) {
      const blob = [
        row.orderNo, row.workpieceName, row.workNo, row.orderDesc,
        row.processEngineerName, row.operatorName, row.machineName
      ].map(v => String(v || '').toLowerCase()).join(' ')
      if (!blob.includes(kw)) return false
    }
    return true
  })
  return sortRows(rows, sorts.order.key, sorts.order.order, 'order')
})

const orderTotalPages = computed(() => Math.max(1, Math.ceil(filteredOrderRows.value.length / orderPageSize)))

const pagedOrderRows = computed(() => {
  const start = (orderPage.value - 1) * orderPageSize
  return filteredOrderRows.value.slice(start, start + orderPageSize)
})

const yearMonthAxis = computed(() =>
  activeMonths.value.map((ym) => `${Number(ym.slice(5, 7))}月`)
)

function sumDeptField(snapshot, field) {
  return (snapshot?.dept || []).reduce((sum, row) => sum + (Number(row[field]) || 0), 0)
}

function avgDeptField(snapshot, field, weightField = 'orderCount') {
  const pairs = (snapshot?.dept || []).map((row) => [row[field], row[weightField] || 1])
  return weightedAvg(pairs)
}

const summaryKpiCards = computed(() => {
  const totalOrders = deptAll.value.reduce((sum, row) => sum + (Number(row.orderCount) || 0), 0)
  const totalHours = deptAll.value.reduce((sum, row) => sum + (Number(row.totalServiceHours) || 0), 0)
  const avgAccept = weightedAvg(deptAll.value.map((row) => [row.avgAcceptHours, row.orderCount || 1]))
  return [
    { key: 'orders', label: '年度工单总数', value: totalOrders, hint: `${activeMonths.value.length} 个月累计` },
    { key: 'hours', label: '总服务时长(h)', value: fmtNum(totalHours), hint: '各科室合计' },
    { key: 'depts', label: '涉及科室', value: deptAll.value.length, hint: '参与服务科室数' },
    { key: 'people', label: '服务人员', value: personAll.value.length, hint: avgAccept == null ? '—' : `平均接单 ${fmtNum(avgAccept)} h` },
  ]
})

const yearOrderTrendOption = computed(() => getLineChartOption({
  title: '月度工单总量趋势',
  xAxisData: yearMonthAxis.value,
  seriesData: activeMonths.value.map((ym) => {
    const snap = monthlySnapshots.value.find((item) => item.yearMonth === ym)
    return sumDeptField(snap, 'orderCount')
  }),
  yAxisName: '工单数',
}))

const yearHoursTrendOption = computed(() => getLineChartOption({
  title: '月度总服务时长趋势',
  xAxisData: yearMonthAxis.value,
  seriesData: activeMonths.value.map((ym) => {
    const snap = monthlySnapshots.value.find((item) => item.yearMonth === ym)
    return Number(sumDeptField(snap, 'totalServiceHours').toFixed(2))
  }),
  yAxisName: '小时',
}))

const yearAvgServiceTrendOption = computed(() => getMultiLineChartOption({
  title: '月度响应效率趋势',
  xAxisData: yearMonthAxis.value,
  series: [
    {
      name: '平均服务(h)',
      data: activeMonths.value.map((ym) => {
        const snap = monthlySnapshots.value.find((item) => item.yearMonth === ym)
        const v = avgDeptField(snap, 'avgServiceHours')
        return v == null ? 0 : Number(v.toFixed(3))
      }),
    },
    {
      name: '平均接单(h)',
      data: activeMonths.value.map((ym) => {
        const snap = monthlySnapshots.value.find((item) => item.yearMonth === ym)
        const v = avgDeptField(snap, 'avgAcceptHours')
        return v == null ? 0 : Number(v.toFixed(3))
      }),
    },
    {
      name: '平均到场(h)',
      data: activeMonths.value.map((ym) => {
        const snap = monthlySnapshots.value.find((item) => item.yearMonth === ym)
        const v = avgDeptField(snap, 'avgArriveHours')
        return v == null ? 0 : Number(v.toFixed(3))
      }),
    },
  ],
}))

const yearStatusTrendOption = computed(() => getMultiLineChartOption({
  title: '月度工单状态趋势',
  xAxisData: yearMonthAxis.value,
  series: [
    {
      name: '未接单',
      data: activeMonths.value.map((ym) => sumDeptField(monthlySnapshots.value.find((item) => item.yearMonth === ym), 'pendingAccept')),
    },
    {
      name: '待到场',
      data: activeMonths.value.map((ym) => sumDeptField(monthlySnapshots.value.find((item) => item.yearMonth === ym), 'pendingArrive')),
    },
    {
      name: '处理中',
      data: activeMonths.value.map((ym) => sumDeptField(monthlySnapshots.value.find((item) => item.yearMonth === ym), 'processing')),
    },
    {
      name: '待确认',
      data: activeMonths.value.map((ym) => sumDeptField(monthlySnapshots.value.find((item) => item.yearMonth === ym), 'pendingConfirm')),
    },
  ],
}))

const deptChartRows = computed(() =>
  sortRows([...filteredDeptRows.value], 'orderCount', 'desc', 'dept').slice(0, 16)
)

const deptOrderBarOption = computed(() => getColorBarChartOption({
  title: '各科室工单总数对比',
  xAxisData: deptChartRows.value.map((row) => row.deptName),
  seriesData: deptChartRows.value.map((row) => Number(row.orderCount) || 0),
  yAxisName: '工单数',
}))

const deptHoursBarOption = computed(() => getColorBarChartOption({
  title: '各科室总服务时长对比',
  xAxisData: deptChartRows.value.map((row) => row.deptName),
  seriesData: deptChartRows.value.map((row) => Number(row.totalServiceHours) || 0),
  yAxisName: '小时',
}))

const personTopRows = computed(() =>
  sortRows([...filteredPersonRows.value], 'serviceCount', 'desc', 'person').slice(0, 10)
)

const personPodiumRows = computed(() => personTopRows.value.slice(0, 3))

const personTopBarOption = computed(() => getHorizontalBarChartOption({
  title: '服务人员绩效 TOP10',
  labels: personTopRows.value.map((row) => `${row.employeeName}（${row.deptName}）`),
  values: personTopRows.value.map((row) => Number(row.serviceCount) || 0),
  yAxisName: '服务频次',
}))

const personMaxServiceCount = computed(() =>
  Math.max(...filteredPersonRows.value.map((row) => Number(row.serviceCount) || 0), 1)
)

const personMaxHours = computed(() =>
  Math.max(...filteredPersonRows.value.map((row) => Number(row.totalServiceHours) || 0), 1)
)

function personMetricWidth(row, field) {
  const value = Number(row[field]) || 0
  const max = field === 'serviceCount' ? personMaxServiceCount.value : personMaxHours.value
  return `${Math.max(8, (value / max) * 100)}%`
}

const personServiceRankMap = computed(() => {
  const sorted = sortRows([...filteredPersonRows.value], 'serviceCount', 'desc', 'person')
  const map = new Map()
  sorted.forEach((row, idx) => {
    map.set(`${row.deptName}::${row.employeeName}`, idx)
  })
  return map
})

function personServiceRank(row) {
  return personServiceRankMap.value.get(`${row.deptName}::${row.employeeName}`) ?? 999
}

function personRankLabelByRow(row) {
  const idx = personServiceRank(row)
  if (idx === 0) return '🥇'
  if (idx === 1) return '🥈'
  if (idx === 2) return '🥉'
  if (idx < 5) return `#${idx + 1}`
  return `#${idx + 1}`
}

function rankBadgeClassByRow(row) {
  const idx = personServiceRank(row)
  if (idx === 0) return 'rank-badge-gold'
  if (idx === 1) return 'rank-badge-silver'
  if (idx === 2) return 'rank-badge-bronze'
  if (idx < 5) return 'rank-badge-top'
  return ''
}

function personRowClassByRow(row) {
  const idx = personServiceRank(row)
  if (idx === 0) return 'row-rank-gold'
  if (idx === 1) return 'row-rank-silver'
  if (idx === 2) return 'row-rank-bronze'
  if (idx < 5) return 'row-rank-top'
  return ''
}

function podiumMedal(idx) {
  return ['🥇 TOP1', '🥈 TOP2', '🥉 TOP3'][idx] || `#${idx + 1}`
}

watch(filteredOrderRows, () => {
  if (orderPage.value > orderTotalPages.value) orderPage.value = orderTotalPages.value
})

function uniqueSorted(values) {
  return Array.from(new Set(values.filter(Boolean))).sort(collator.compare)
}

function isFilledNumber(v) {
  return v !== null && v !== undefined && v !== '' && !Number.isNaN(Number(v))
}

function typeCountsText(row) {
  return [row.typeSimple, row.typeNormal, row.typeComplex, row.typeHard, row.typeImprove]
    .map(v => v ?? 0).join('/')
}

function rateCountsText(row) {
  return [row.rateExcellent, row.rateGood, row.rateNormal, row.ratePoor, row.rateBad]
    .map(v => v ?? 0).join('/')
}

function sortValue(row, key, scope) {
  if (scope === 'person' && key === 'typeCounts') {
    return Number(row.serviceCount || 0)
  }
  if (scope === 'person' && key === 'rateCounts') {
    return Number(row.rateExcellent || 0) + Number(row.rateGood || 0) + Number(row.rateNormal || 0)
      + Number(row.ratePoor || 0) + Number(row.rateBad || 0)
  }
  if (scope === 'order' && key === 'ratingLabel') {
    return row.ratingLabel || row.ratingScore || ''
  }
  return row[key]
}

function sortRows(rows, key, order, scope) {
  const dir = order === 'asc' ? 1 : -1
  return [...rows].sort((a, b) => {
    const va = sortValue(a, key, scope)
    const vb = sortValue(b, key, scope)
    const na = va == null || va === '' ? null : Number(va)
    const nb = vb == null || vb === '' ? null : Number(vb)
    const bothNumber = na != null && nb != null && !Number.isNaN(na) && !Number.isNaN(nb)
      && String(va).trim() !== '' && String(vb).trim() !== ''
      && !/^\d{4}-\d{2}-\d{2}/.test(String(va)) && !/^\d{4}-\d{2}-\d{2}/.test(String(vb))
    let cmp
    if (bothNumber) {
      cmp = na - nb
    } else {
      cmp = collator.compare(String(va ?? ''), String(vb ?? ''))
    }
    if (cmp === 0) {
      if (scope === 'person') return collator.compare(String(a.employeeName || ''), String(b.employeeName || ''))
      if (scope === 'order') return collator.compare(String(a.orderNo || ''), String(b.orderNo || ''))
      return collator.compare(String(a.deptName || ''), String(b.deptName || ''))
    }
    return cmp * dir
  })
}

function toggleSort(scope, key) {
  if (sorts[scope].key === key) {
    sorts[scope].order = sorts[scope].order === 'asc' ? 'desc' : 'asc'
  } else {
    sorts[scope].key = key
    sorts[scope].order = 'desc'
  }
  if (scope === 'order') orderPage.value = 1
}

function sortMark(scope, key) {
  if (sorts[scope].key !== key) return '↕'
  return sorts[scope].order === 'asc' ? '↑' : '↓'
}

function fmtNum(v) {
  if (v == null || v === '') return '-'
  const n = Number(v)
  if (Number.isNaN(n)) return String(v)
  return Number.isInteger(n) ? String(n) : n.toFixed(3)
}

function fmtTime(v) {
  if (!v) return '-'
  return String(v).replace('T', ' ').slice(0, 19)
}

function resetDeptFilter() {
  deptFilter.dept = ''
  deptFilter.minOrders = null
  deptFilter.minHours = null
  deptFilter.keyword = ''
}

function resetPersonFilter() {
  personFilter.dept = ''
  personFilter.name = ''
  personFilter.minService = null
  personFilter.minHours = null
  personFilter.hasRate = ''
}

function resetOrderFilter() {
  orderFilter.dept = ''
  orderFilter.orderType = ''
  orderFilter.status = ''
  orderFilter.engineer = ''
  orderFilter.operator = ''
  orderFilter.rating = ''
  orderFilter.keyword = ''
  orderPage.value = 1
}

async function checkPermission() {
  try {
    const raw = localStorage.getItem('userInfo')
    const user = raw ? JSON.parse(raw) : null
    const name = (user?.name || user?.userName || '').trim()
    const jb = (user?.jb || '').trim()
    const lsys = (user?.dept || user?.lsys || '').trim()
    if (!name) {
      canAccess.value = false
      return
    }
    let admin1Name = ''
    try {
      const cfg = await getUploadConfig()
      admin1Name = (cfg?.admin1 || '').trim()
    } catch { /* ignore */ }
    canAccess.value = canAccessMashangban({ name, jb, lsys, admin1: admin1Name })
  } catch {
    canAccess.value = false
  }
}

async function loadMonths() {
  const res = await getMashangbanMonths()
  months.value = res?.items || []
  if (!monthOptions.value.length) {
    monthStart.value = ''
    monthEnd.value = ''
    selectedYear.value = ''
    return
  }
  if (!monthStart.value || !monthOptions.value.includes(monthStart.value)) {
    monthStart.value = monthOptions.value[0]
  }
  if (!monthEnd.value || !monthOptions.value.includes(monthEnd.value)) {
    monthEnd.value = monthStart.value
  }
  if (!selectedYear.value || !yearOptions.value.includes(selectedYear.value)) {
    selectedYear.value = monthStart.value.slice(0, 4)
  }
}

function weightedAvg(pairs) {
  let weightSum = 0
  let valueSum = 0
  for (const [value, weight] of pairs) {
    const w = Number(weight) || 0
    if (w <= 0) continue
    const n = Number(value)
    if (Number.isNaN(n)) continue
    weightSum += w
    valueSum += n * w
  }
  if (weightSum <= 0) return null
  return valueSum / weightSum
}

function aggregateDeptRows(rows) {
  const map = new Map()
  for (const row of rows) {
    const key = row.deptName || ''
    if (!key) continue
    if (!map.has(key)) {
      map.set(key, {
        deptName: key,
        orderCount: 0,
        totalServiceHours: 0,
        pendingAccept: 0,
        pendingArrive: 0,
        processing: 0,
        pendingConfirm: 0,
        _acceptPairs: [],
        _arrivePairs: []
      })
    }
    const cur = map.get(key)
    const orders = Number(row.orderCount) || 0
    cur.orderCount += orders
    cur.totalServiceHours += Number(row.totalServiceHours) || 0
    cur.pendingAccept += Number(row.pendingAccept) || 0
    cur.pendingArrive += Number(row.pendingArrive) || 0
    cur.processing += Number(row.processing) || 0
    cur.pendingConfirm += Number(row.pendingConfirm) || 0
    cur._acceptPairs.push([row.avgAcceptHours, orders || 1])
    cur._arrivePairs.push([row.avgArriveHours, orders || 1])
  }
  return Array.from(map.values()).map(row => {
    const avgService = row.orderCount > 0 ? row.totalServiceHours / row.orderCount : null
    return {
      deptName: row.deptName,
      orderCount: row.orderCount,
      totalServiceHours: Number(row.totalServiceHours.toFixed(3)),
      avgServiceHours: avgService == null ? null : Number(avgService.toFixed(3)),
      avgAcceptHours: (() => {
        const v = weightedAvg(row._acceptPairs)
        return v == null ? null : Number(v.toFixed(3))
      })(),
      avgArriveHours: (() => {
        const v = weightedAvg(row._arrivePairs)
        return v == null ? null : Number(v.toFixed(3))
      })(),
      pendingAccept: row.pendingAccept,
      pendingArrive: row.pendingArrive,
      processing: row.processing,
      pendingConfirm: row.pendingConfirm
    }
  })
}

function aggregatePersonRows(rows) {
  const map = new Map()
  for (const row of rows) {
    const key = `${row.deptName || ''}::${row.employeeName || ''}`
    if (!row.employeeName) continue
    if (!map.has(key)) {
      map.set(key, {
        deptName: row.deptName,
        employeeName: row.employeeName,
        serviceCount: 0,
        totalServiceHours: 0,
        typeSimple: 0,
        typeNormal: 0,
        typeComplex: 0,
        typeHard: 0,
        typeImprove: 0,
        patrolCount: 0,
        patrolFactory: 0,
        patrolNewtech: 0,
        patrolFollow: 0,
        rateExcellent: 0,
        rateGood: 0,
        rateNormal: 0,
        ratePoor: 0,
        rateBad: 0,
        _acceptPairs: [],
        _arrivePairs: []
      })
    }
    const cur = map.get(key)
    const services = Number(row.serviceCount) || 0
    cur.serviceCount += services
    cur.totalServiceHours += Number(row.totalServiceHours) || 0
    cur.typeSimple += Number(row.typeSimple) || 0
    cur.typeNormal += Number(row.typeNormal) || 0
    cur.typeComplex += Number(row.typeComplex) || 0
    cur.typeHard += Number(row.typeHard) || 0
    cur.typeImprove += Number(row.typeImprove) || 0
    cur.patrolCount += Number(row.patrolCount) || 0
    cur.patrolFactory += Number(row.patrolFactory) || 0
    cur.patrolNewtech += Number(row.patrolNewtech) || 0
    cur.patrolFollow += Number(row.patrolFollow) || 0
    cur.rateExcellent += Number(row.rateExcellent) || 0
    cur.rateGood += Number(row.rateGood) || 0
    cur.rateNormal += Number(row.rateNormal) || 0
    cur.ratePoor += Number(row.ratePoor) || 0
    cur.rateBad += Number(row.rateBad) || 0
    cur._acceptPairs.push([row.avgAcceptHours, services || 1])
    cur._arrivePairs.push([row.avgArriveHours, services || 1])
  }
  return Array.from(map.values()).map(row => {
    const avgService = row.serviceCount > 0 ? row.totalServiceHours / row.serviceCount : null
    return {
      ...row,
      totalServiceHours: Number(row.totalServiceHours.toFixed(3)),
      avgServiceHours: avgService == null ? null : Number(avgService.toFixed(3)),
      avgAcceptHours: (() => {
        const v = weightedAvg(row._acceptPairs)
        return v == null ? null : Number(v.toFixed(3))
      })(),
      avgArriveHours: (() => {
        const v = weightedAvg(row._arrivePairs)
        return v == null ? null : Number(v.toFixed(3))
      })(),
      _acceptPairs: undefined,
      _arrivePairs: undefined
    }
  })
}

function mergeOrderRows(rows) {
  const map = new Map()
  for (const row of rows) {
    const key = row.orderNo || `${row.deptName}-${row.createdAt}-${Math.random()}`
    const prev = map.get(key)
    if (!prev) {
      map.set(key, row)
      continue
    }
    // 同工单号跨月时保留创建时间更晚的一条。
    const ta = String(prev.createdAt || '')
    const tb = String(row.createdAt || '')
    if (tb >= ta) map.set(key, row)
  }
  return Array.from(map.values())
}

async function loadRangeData() {
  const list = activeMonths.value
  if (!list.length) {
    deptAll.value = []
    personAll.value = []
    orderAll.value = []
    monthlySnapshots.value = []
    return
  }
  ordersLoading.value = true
  try {
    const results = await Promise.all(
      list.map(async ym => {
        const [deptRes, personRes, orderRes] = await Promise.all([
          getMashangbanDept(ym),
          getMashangbanPerson(ym),
          getMashangbanOrders({ yearMonth: ym, page: 1, pageSize: 2000 })
        ])
        return {
          dept: deptRes?.items || [],
          person: personRes?.items || [],
          order: orderRes?.items || []
        }
      })
    )
    const deptRows = results.flatMap(r => r.dept)
    const personRows = results.flatMap(r => r.person)
    const orderRows = results.flatMap(r => r.order)
    monthlySnapshots.value = list.map((ym, idx) => ({
      yearMonth: ym,
      dept: results[idx]?.dept || [],
      person: results[idx]?.person || [],
      orders: results[idx]?.order || [],
    }))
    deptAll.value = list.length === 1 ? deptRows : aggregateDeptRows(deptRows)
    personAll.value = list.length === 1 ? personRows : aggregatePersonRows(personRows)
    orderAll.value = list.length === 1 ? orderRows : mergeOrderRows(orderRows)
    orderPage.value = 1
  } finally {
    ordersLoading.value = false
  }
}

async function reloadAll() {
  if (!canAccess.value) return
  loading.value = true
  try {
    await loadMonths()
    await loadRangeData()
  } finally {
    loading.value = false
  }
}

async function onRangeModeChange() {
  if (rangeMode.value === 'month') {
    monthEnd.value = monthStart.value
  } else if (rangeMode.value === 'range') {
    if (!monthEnd.value) monthEnd.value = monthStart.value
    if (monthStart.value > monthEnd.value) {
      const tmp = monthStart.value
      monthStart.value = monthEnd.value
      monthEnd.value = tmp
    }
  } else if (rangeMode.value === 'year') {
    selectedYear.value = (monthStart.value || monthOptions.value[0] || '').slice(0, 4)
  }
  resetDeptFilter()
  resetPersonFilter()
  resetOrderFilter()
  await loadRangeData()
}

async function onRangeChange() {
  if (rangeMode.value === 'month') {
    monthEnd.value = monthStart.value
  } else if (monthStart.value && monthEnd.value && monthStart.value > monthEnd.value) {
    const tmp = monthStart.value
    monthStart.value = monthEnd.value
    monthEnd.value = tmp
  }
  resetDeptFilter()
  resetPersonFilter()
  resetOrderFilter()
  await loadRangeData()
}

async function onYearChange() {
  resetDeptFilter()
  resetPersonFilter()
  resetOrderFilter()
  await loadRangeData()
}

function exportCellValue(row, key, scope) {
  if (scope === 'person' && key === 'typeCounts') return typeCountsText(row)
  if (scope === 'person' && key === 'rateCounts') return rateCountsText(row)
  if (scope === 'order' && key === 'createdAt') return fmtTime(row.createdAt)
  if (scope === 'order' && key === 'ratingLabel') return row.ratingLabel || row.ratingScore || ''
  const v = row[key]
  if (v == null || v === '') return ''
  return v
}

function buildDeptSheet(rows) {
  const header = deptColumns.map(col => col.label)
  const body = rows.map(row => deptColumns.map(col => exportCellValue(row, col.key, 'dept')))
  return XLSX.utils.aoa_to_sheet([header, ...body])
}

function buildPersonSheet(rows) {
  const header = ['排名', ...personColumns.map(col => col.label)]
  const body = rows.map(row => [
    personServiceRank(row) + 1,
    ...personColumns.map(col => exportCellValue(row, col.key, 'person')),
  ])
  return XLSX.utils.aoa_to_sheet([header, ...body])
}

function buildOrderSheet(rows) {
  const header = orderColumns.map(col => col.label)
  const body = rows.map(row => orderColumns.map(col => exportCellValue(row, col.key, 'order')))
  return XLSX.utils.aoa_to_sheet([header, ...body])
}

function exportFileName() {
  const label = rangeLabel.value.replace(/[<>:"/\\|?*\s]+/g, '_')
  return `工艺码上办月报_${label}.xlsx`
}

function handleExportExcel() {
  if (!activeMonths.value.length) {
    alert('请先选择统计月份')
    return
  }
  exportLoading.value = true
  try {
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, buildDeptSheet(filteredDeptRows.value), '科室统计')
    XLSX.utils.book_append_sheet(wb, buildPersonSheet(filteredPersonRows.value), '人员服务绩效')
    XLSX.utils.book_append_sheet(wb, buildOrderSheet(filteredOrderRows.value), '工单明细')
    XLSX.writeFile(wb, exportFileName())
  } catch (e) {
    console.error(e)
    alert(e?.message || '导出失败，请稍后重试')
  } finally {
    exportLoading.value = false
  }
}

onMounted(async () => {
  await checkPermission()
  if (canAccess.value) await reloadAll()
})
</script>

<style scoped>
.msb-page {
  padding: 24px;
  background: #f5f7fb;
  min-height: 100%;
}
.container {
  max-width: 1480px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.btn-export {
  background: #059669;
  color: #fff;
  border-color: #059669;
}
.btn-export:hover:not(:disabled) {
  filter: brightness(1.06);
}
.page-header h1 {
  margin: 0 0 6px;
  font-size: 24px;
  color: #1f2937;
}
.page-header p,
.meta {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
}
.range-sep {
  color: #64748b;
  font-weight: 600;
}
.card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.06);
  padding: 18px;
  margin-bottom: 14px;
}
.tip {
  text-align: center;
  padding: 40px 20px;
}
.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.tabs button {
  border: 0;
  background: #eaf0f7;
  padding: 9px 18px;
  border-radius: 7px;
  cursor: pointer;
  color: #334155;
  font-weight: 600;
}
.tabs button.active {
  background: #1677ff;
  color: #fff;
}
.top-bar,
.filters,
.pager {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.filters {
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid #eef2f7;
}
.top-bar label,
.filters label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #374151;
  font-size: 13px;
}
.filters label.grow {
  flex: 1;
  min-width: 220px;
}
select,
input {
  height: 34px;
  border: 1px solid #d7dce5;
  border-radius: 6px;
  padding: 0 10px;
  background: #fff;
  font-weight: 400;
  min-width: 110px;
}
label.grow input {
  width: 100%;
  min-width: 180px;
}
.btn {
  height: 34px;
  border: 0;
  border-radius: 6px;
  padding: 0 14px;
  background: #1677ff;
  color: #fff;
  cursor: pointer;
}
.btn-ghost {
  background: #e8eef6;
  color: #334155;
}
.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.table-wrap {
  overflow: auto;
  max-height: calc(100vh - 320px);
}
table {
  width: 100%;
  border-collapse: collapse;
  min-width: 980px;
  font-size: 13px;
}
th,
td {
  border-bottom: 1px solid #eef2f7;
  padding: 9px 10px;
  text-align: left;
  vertical-align: top;
}
th {
  background: #f4f7fb;
  color: #4b5563;
  font-weight: 600;
  white-space: nowrap;
  position: sticky;
  top: 0;
  z-index: 1;
}
th.sortable {
  cursor: pointer;
  user-select: none;
}
th.sortable:hover {
  color: #1677ff;
}
.sort-mark {
  margin-left: 4px;
  color: #94a3b8;
  font-size: 12px;
}
.empty {
  text-align: center;
  color: #9ca3af;
  padding: 24px 10px;
}
.clip {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pager {
  margin-top: 12px;
  justify-content: flex-end;
  color: #6b7280;
  font-size: 13px;
}

.chart-dashboard {
  margin-bottom: 14px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.kpi-card {
  background: linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid #e5edf7;
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
}

.kpi-label {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
}

.kpi-value {
  display: block;
  font-size: 24px;
  line-height: 1.2;
  color: #0f172a;
  margin-bottom: 4px;
}

.kpi-hint {
  font-size: 11px;
  color: #94a3b8;
}

.kpi-orders { border-top: 3px solid #1677ff; }
.kpi-hours { border-top: 3px solid #13c2c2; }
.kpi-depts { border-top: 3px solid #722ed1; }
.kpi-people { border-top: 3px solid #fa8c16; }

.chart-grid {
  display: grid;
  gap: 12px;
}

.chart-grid-2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.chart-card,
.chart-card-inner {
  background: #fff;
  border: 1px solid #e8eef5;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
  overflow: hidden;
}

.chart-card-inner {
  padding: 8px 8px 0;
}

.chart-box {
  width: 100%;
  height: 280px;
}

.chart-box-md {
  height: 320px;
}

.chart-box-lg {
  height: 360px;
}

.dept-chart-panel,
.person-visual-panel {
  margin-bottom: 14px;
}

.podium-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.podium-card {
  border-radius: 12px;
  padding: 16px;
  color: #1f2937;
  border: 1px solid #e5edf7;
  background: #fff;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
}

.podium-1 {
  background: linear-gradient(180deg, #fff9e6 0%, #ffffff 100%);
  border-color: #f6d365;
  transform: translateY(-4px);
}

.podium-2 {
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
  border-color: #cbd5e1;
}

.podium-3 {
  background: linear-gradient(180deg, #fff4eb 0%, #ffffff 100%);
  border-color: #fdba74;
}

.podium-rank {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 8px;
}

.podium-name {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 4px;
}

.podium-dept {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 10px;
}

.podium-metrics {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #334155;
}

.rank-col,
.rank-cell {
  width: 56px;
  text-align: center;
}

.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 34px;
  height: 24px;
  padding: 0 6px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  background: #eef2f7;
  color: #64748b;
}

.rank-badge-gold { background: #fff1b8; color: #ad6800; }
.rank-badge-silver { background: #f1f5f9; color: #475569; }
.rank-badge-bronze { background: #ffe7ba; color: #d46b08; }
.rank-badge-top { background: #e6f4ff; color: #0958d9; }

.row-rank-gold td { background: #fffbe6; }
.row-rank-silver td { background: #f8fafc; }
.row-rank-bronze td { background: #fff7e6; }
.row-rank-top td { background: #f0f7ff; }

.metric-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 88px;
}

.metric-bar-track {
  height: 6px;
  border-radius: 999px;
  background: #edf2f7;
  overflow: hidden;
}

.metric-bar-hours .metric-bar-fill {
  background: linear-gradient(90deg, #13c2c2, #87e8de);
}

.metric-bar-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #1677ff, #69c0ff);
}

.name-with-badge {
  font-weight: 600;
}

@media (max-width: 1100px) {
  .kpi-grid,
  .chart-grid-2,
  .podium-grid {
    grid-template-columns: 1fr;
  }
  .podium-1 { transform: none; }
}

@media (max-width: 800px) {
  .msb-page { padding: 14px; }
  .page-header { flex-direction: column; }
}
</style>
