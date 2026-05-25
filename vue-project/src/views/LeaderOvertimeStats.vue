<template>
  <div class="leader-ot-page">
    <div class="page-header">
      <div>
        <h1>部办加班统计</h1>
        <p>按部办打卡识别加班：工作日 7:30 前 + 17:30 后（不足 1 小时也计），与驾驶舱自动计算一致；领导岗位已高亮</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-secondary" type="button" @click="openBaselineModal">录入排名基准</button>
        <router-link to="/leader-dashboard" class="btn btn-secondary">返回驾驶舱</router-link>
      </div>
    </div>

    <section class="filter-card">
      <div :class="['form-item', { 'form-item--disabled': isDateRangeMode }]">
        <label>年份</label>
        <select v-model="filterYear" :disabled="isDateRangeMode">
          <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option>
        </select>
      </div>
      <div :class="['form-item', { 'form-item--disabled': isDateRangeMode }]">
        <label>月份</label>
        <select v-model="filterMonth" :disabled="isDateRangeMode">
          <option value="">全年</option>
          <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
        </select>
      </div>
      <div class="form-item">
        <label>开始日期</label>
        <input v-model="dateFrom" type="date" />
      </div>
      <div class="form-item">
        <label>结束日期</label>
        <input v-model="dateTo" type="date" />
      </div>
      <button class="btn btn-primary" :disabled="loading" @click="fetchData">
        {{ loading ? '查询中...' : '查询' }}
      </button>
    </section>

    <section class="summary-grid">
      <div class="summary-card">
        <span class="summary-label">统计区间</span>
        <strong>{{ rangeText }}</strong>
      </div>
      <div class="summary-card accent">
        <span class="summary-label">总加班</span>
        <strong>{{ stats.totalHours ?? 0 }}<small>小时</small></strong>
      </div>
      <div class="summary-card">
        <span class="summary-label">涉及人员</span>
        <strong>{{ stats.personCount ?? 0 }}<small>人</small></strong>
      </div>
    </section>

    <section class="content-grid">
      <article class="panel">
        <div class="panel-header">
          <h2>按人汇总</h2>
        </div>
        <div v-if="loading" class="empty">加载中...</div>
        <div v-else-if="!people.length" class="empty">暂无加班数据</div>
        <div v-else class="people-list">
          <div
            v-for="(item, idx) in people"
            :key="item.name"
            :class="['person-row', { 'person-row--leader': item.isLeader }]"
          >
            <span class="rank">{{ idx + 1 }}</span>
            <div class="person-main">
              <strong>
                {{ item.name }}
              </strong>
              <span>
                {{ item.jb || '部办人员' }} · {{ calcDaysByHours(item.hours) }} 天 · 月均 {{ formatMonthlyAvgDays(item) }} 天
              </span>
              <p v-if="item.isLeader && item.estimatedRank" class="rank-note">
                预计排名{{ item.estimatedRank }}/{{ item.rankTotal || stats.rankTotal || 126 }}
              </p>
            </div>
            <span class="hours">{{ item.hours }} 小时</span>
          </div>
        </div>
      </article>

      <article class="panel details-panel">
        <div class="panel-header">
          <h2>每日明细</h2>
          <div v-if="details.length" class="detail-filters">
            <input
              v-model.trim="detailKeyword"
              type="text"
              class="detail-filter-input"
              placeholder="筛选姓名"
            />
            <select v-model="detailType" class="detail-filter-select">
              <option value="">全部类型</option>
              <option v-for="type in detailTypeOptions" :key="type" :value="type">{{ type }}</option>
            </select>
            <label class="detail-filter-check">
              <input v-model="detailLeaderOnly" type="checkbox" />
              仅看领导
            </label>
            <button type="button" class="btn btn-secondary detail-filter-reset" @click="resetDetailFilters">
              重置
            </button>
          </div>
        </div>
        <div v-if="loading" class="empty">加载中...</div>
        <div v-else-if="!details.length" class="empty">暂无明细</div>
        <div v-else-if="!filteredDetails.length" class="empty">筛选后暂无数据</div>
        <div v-else class="detail-table-wrap">
          <table class="detail-table">
            <thead>
              <tr>
                <th class="th-sortable" @click="toggleDetailSort('date')">
                  日期 <span class="sort-ind">{{ detailSortIndicator('date') }}</span>
                </th>
                <th class="th-sortable" @click="toggleDetailSort('name')">
                  姓名 <span class="sort-ind">{{ detailSortIndicator('name') }}</span>
                </th>
                <th class="th-sortable" @click="toggleDetailSort('dayType')">
                  类型 <span class="sort-ind">{{ detailSortIndicator('dayType') }}</span>
                </th>
                <th class="th-sortable" @click="toggleDetailSort('segments')">
                  时段 <span class="sort-ind">{{ detailSortIndicator('segments') }}</span>
                </th>
                <th class="th-sortable" @click="toggleDetailSort('hours')">
                  小时 <span class="sort-ind">{{ detailSortIndicator('hours') }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in sortedFilteredDetails"
                :key="`${row.name}-${row.date}`"
                :class="{ 'detail-row--leader': row.isLeader }"
              >
                <td>{{ row.date }}</td>
                <td>{{ row.name }}</td>
                <td>{{ row.dayType }}</td>
                <td>
                  <span v-for="(seg, i) in row.segments || []" :key="i" class="segment-chip">
                    {{ seg.type }} {{ seg.start }}-{{ seg.end }}
                  </span>
                </td>
                <td class="td-hours">{{ row.hours }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>
    </section>

    <div v-if="baselineModalVisible" class="modal-overlay" @click.self="closeBaselineModal">
      <div class="modal-content">
        <div class="modal-header">
          <div>
            <h2>录入排名基准</h2>
            <p>中层领导干部月均加班天数</p>
          </div>
          <button class="icon-btn" type="button" @click="closeBaselineModal">×</button>
        </div>
        <div class="baseline-toolbar">
          <div class="form-item">
            <label>基准年份</label>
            <input v-model.number="baselineYear" type="number" min="2000" max="2100" />
          </div>
          <button class="btn btn-secondary" type="button" :disabled="baselineLoading" @click="loadBaselineData">
            {{ baselineLoading ? '读取中...' : '读取已有' }}
          </button>
          <span class="baseline-count">当前 {{ baselineCount }} 条</span>
        </div>
        <textarea
          v-model="baselineText"
          class="baseline-textarea"
          placeholder="一行一个月均天数，也支持空格、逗号分隔"
        ></textarea>
        <div class="modal-footer">
          <button class="btn btn-secondary" type="button" @click="closeBaselineModal">取消</button>
          <button class="btn btn-primary" type="button" :disabled="baselineSaving" @click="saveBaselineData">
            {{ baselineSaving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  getLeaderOvertimeBaseline,
  getLeaderOvertimeStats,
  saveLeaderOvertimeBaseline
} from '@/api/attendance'

const now = new Date()
const filterYear = ref(now.getFullYear())
const filterMonth = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const loading = ref(false)
const stats = ref({ totalHours: 0, personCount: 0, list: [], details: [] })
const baselineModalVisible = ref(false)
const baselineYear = ref(now.getFullYear() - 1)
const baselineText = ref('')
const baselineLoading = ref(false)
const baselineSaving = ref(false)
const detailKeyword = ref('')
const detailType = ref('')
const detailLeaderOnly = ref(false)
const detailSortKey = ref('date')
const detailSortOrder = ref('desc')

const yearOptions = computed(() => {
  const y = now.getFullYear()
  return Array.from({ length: 6 }, (_, i) => y - i)
})
const people = computed(() => stats.value.list || [])
const details = computed(() => stats.value.details || [])
const detailTypeOptions = computed(() => {
  const set = new Set()
  details.value.forEach((row) => {
    if (row?.dayType) set.add(row.dayType)
  })
  return Array.from(set)
})
const filteredDetails = computed(() => {
  const keyword = detailKeyword.value.trim().toLowerCase()
  return details.value.filter((row) => {
    if (detailType.value && row.dayType !== detailType.value) return false
    if (detailLeaderOnly.value && !row.isLeader) return false
    if (keyword && !String(row.name || '').toLowerCase().includes(keyword)) return false
    return true
  })
})
const sortedFilteredDetails = computed(() => {
  const rows = [...filteredDetails.value]
  const key = detailSortKey.value
  const order = detailSortOrder.value === 'asc' ? 1 : -1

  return rows.sort((a, b) => {
    const aValue = getDetailSortValue(a, key)
    const bValue = getDetailSortValue(b, key)
    if (aValue === bValue) return 0
    return aValue > bValue ? order : -order
  })
})
const isDateRangeMode = computed(() => Boolean(dateFrom.value && dateTo.value))
const rankBaselineShort = computed(() => String(stats.value.rankBaselineYear || 2025).slice(-2))
const baselineCount = computed(() => {
  try {
    return parseBaselineValues().length
  } catch {
    return 0
  }
})
const periodMonths = computed(() => {
  const start = parseDate(stats.value.range?.start || (isDateRangeMode.value ? dateFrom.value : ''))
  const end = parseDate(stats.value.range?.end || (isDateRangeMode.value ? dateTo.value : ''))
  if (start && end) {
    const diffMs = end.getTime() - start.getTime()
    const days = Math.floor(diffMs / 86400000) + 1
    if (days > 0) return days / 30
  }
  return filterMonth.value ? 1 : 12
})
const rangeText = computed(() => {
  if (stats.value.range?.start && stats.value.range?.end) {
    return `${stats.value.range.start} 至 ${stats.value.range.end}`
  }
  if (dateFrom.value && dateTo.value) {
    return `${dateFrom.value} 至 ${dateTo.value}`
  }
  return filterMonth.value ? `${filterYear.value}年${filterMonth.value}月` : `${filterYear.value}年`
})

function currentUserName() {
  try {
    const u = JSON.parse(localStorage.getItem('userInfo') || '{}')
    return (u.name || u.userName || '').trim()
  } catch {
    return ''
  }
}

function calcDaysByHours(hours) {
  const numericHours = Number(hours)
  if (!Number.isFinite(numericHours) || numericHours <= 0) return '0.0'
  return (numericHours / 8).toFixed(1)
}

function formatMonthlyAvgDays(item) {
  const apiValue = Number(item?.monthlyAvgDays)
  if (Number.isFinite(apiValue)) return apiValue.toFixed(2)
  const numericHours = Number(item?.hours)
  if (!Number.isFinite(numericHours) || numericHours <= 0) return '0.00'
  const months = Number(periodMonths.value)
  if (!Number.isFinite(months) || months <= 0) return '0.00'
  return (numericHours / 8 / months).toFixed(2)
}

function parseDate(value) {
  if (!value) return null
  const d = new Date(`${value}T00:00:00`)
  return Number.isNaN(d.getTime()) ? null : d
}

function parseBaselineValues() {
  const text = (baselineText.value || '').trim()
  if (!text) return []
  return text.split(/[\s,，;；]+/).filter(Boolean).map(token => {
    const value = Number(token)
    if (!Number.isFinite(value) || value < 0) {
      throw new Error(`存在无效数字：${token}`)
    }
    return value
  })
}

function resetDetailFilters() {
  detailKeyword.value = ''
  detailType.value = ''
  detailLeaderOnly.value = false
}

function toggleDetailSort(key) {
  if (detailSortKey.value === key) {
    detailSortOrder.value = detailSortOrder.value === 'asc' ? 'desc' : 'asc'
    return
  }
  detailSortKey.value = key
  detailSortOrder.value = key === 'date' ? 'desc' : 'asc'
}

function detailSortIndicator(key) {
  if (detailSortKey.value !== key) return '↕'
  return detailSortOrder.value === 'asc' ? '↑' : '↓'
}

function getDetailSortValue(row, key) {
  if (key === 'hours') return Number(row?.hours) || 0
  if (key === 'date') return String(row?.date || '')
  if (key === 'segments') return Array.isArray(row?.segments) ? row.segments.length : 0
  return String(row?.[key] || '').toLowerCase()
}

async function openBaselineModal() {
  baselineYear.value = Number(stats.value.rankBaselineYear || filterYear.value - 1 || now.getFullYear() - 1)
  baselineModalVisible.value = true
  await loadBaselineData()
}

function closeBaselineModal() {
  baselineModalVisible.value = false
}

async function loadBaselineData() {
  baselineLoading.value = true
  try {
    const res = await getLeaderOvertimeBaseline({
      year: baselineYear.value,
      current_user: currentUserName()
    })
    baselineText.value = (res?.values || []).map(v => Number(v).toFixed(2)).join('\n')
  } catch (e) {
    alert(e.response?.data?.detail || '排名基准读取失败')
  } finally {
    baselineLoading.value = false
  }
}

async function saveBaselineData() {
  let values = []
  try {
    values = parseBaselineValues()
  } catch (e) {
    alert(e.message || '存在无效数字')
    return
  }
  if (!baselineYear.value || values.length === 0) {
    alert('请填写年份和月均天数')
    return
  }
  baselineSaving.value = true
  try {
    const res = await saveLeaderOvertimeBaseline({
      year: Number(baselineYear.value),
      values,
      current_user: currentUserName()
    })
    baselineText.value = (res?.values || []).map(v => Number(v).toFixed(2)).join('\n')
    alert(`已保存 ${res?.count || values.length} 条`)
    closeBaselineModal()
    await fetchData()
  } catch (e) {
    alert(e.response?.data?.detail || '排名基准保存失败')
  } finally {
    baselineSaving.value = false
  }
}

async function fetchData() {
  loading.value = true
  try {
    const params = { year: filterYear.value, current_user: currentUserName() }
    if ((dateFrom.value && !dateTo.value) || (!dateFrom.value && dateTo.value)) {
      alert('开始日期和结束日期需要同时选择')
      return
    }
    if (dateFrom.value && dateTo.value) {
      params.date_from = dateFrom.value
      params.date_to = dateTo.value
    } else if (filterMonth.value) {
      params.month = Number(filterMonth.value)
    }
    const res = await getLeaderOvertimeStats(params)
    stats.value = res?.success ? res : { totalHours: 0, personCount: 0, list: [], details: [] }
  } catch (e) {
    stats.value = { totalHours: 0, personCount: 0, list: [], details: [] }
    alert(e.response?.data?.detail || '领导加班统计加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.leader-ot-page {
  min-height: 100%;
  background: #f3f4f6;
  padding: 24px 28px;
  color: #1f2937;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: #fff;
  border-radius: 14px;
  padding: 22px 24px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.page-header h1 { margin: 0; font-size: 22px; }
.page-header p { margin: 6px 0 0; color: #6b7280; font-size: 14px; }
.page-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.filter-card {
  margin-top: 16px;
  display: flex;
  align-items: end;
  gap: 14px;
  background: #fff;
  border-radius: 14px;
  padding: 18px 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.form-item { display: flex; flex-direction: column; gap: 6px; }
.form-item label { font-size: 13px; color: #4b5563; font-weight: 600; }
.form-item--disabled label { color: #9ca3af; }
.form-item select {
  min-width: 140px;
  height: 36px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 0 10px;
  background: #fff;
}
.form-item--disabled select {
  background: #f3f4f6;
  color: #9ca3af;
  cursor: not-allowed;
}
.form-item input {
  min-width: 160px;
  height: 36px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 0 10px;
  background: #fff;
}
.btn {
  height: 36px;
  padding: 0 16px;
  border-radius: 8px;
  border: 1px solid #d1d5db;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  text-decoration: none;
  font-size: 14px;
}
.btn-primary { border: none; background: #2563eb; color: #fff; }
.btn-primary:disabled { opacity: .6; cursor: not-allowed; }
.btn-secondary { color: #374151; background: #fff; }
.summary-grid {
  display: grid;
  grid-template-columns: 1.3fr 1fr 1fr;
  gap: 14px;
  margin-top: 16px;
}
.summary-card {
  background: #fff;
  border-radius: 14px;
  padding: 18px 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.summary-card.accent { background: linear-gradient(135deg, #1d4ed8, #0f766e); color: #fff; }
.summary-label { display: block; font-size: 13px; color: #6b7280; margin-bottom: 8px; }
.accent .summary-label { color: rgba(255,255,255,.78); }
.summary-card strong { font-size: 24px; }
.summary-card small { font-size: 13px; margin-left: 4px; font-weight: 500; }
.content-grid {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 16px;
  margin-top: 16px;
}
.panel {
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
  overflow: hidden;
}
.panel-header { padding: 16px 18px; border-bottom: 1px solid #eef0f3; }
.details-panel .panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.panel-header h2 { margin: 0; font-size: 16px; }
.detail-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.detail-filter-input,
.detail-filter-select {
  height: 32px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 0 10px;
  font-size: 12px;
  background: #fff;
}
.detail-filter-input {
  width: 120px;
}
.detail-filter-check {
  height: 32px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #4b5563;
  font-size: 12px;
}
.detail-filter-reset {
  height: 32px;
  padding: 0 10px;
  font-size: 12px;
}
.empty { color: #9ca3af; text-align: center; padding: 34px 0; }
.people-list { padding: 8px 12px 12px; }
.person-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 8px;
  border-bottom: 1px solid #f3f4f6;
  border-radius: 10px;
  margin-bottom: 4px;
}
.person-row--leader {
  background: linear-gradient(135deg, #fff7ed, #e0f2fe);
  border: 1px solid #f59e0b;
  box-shadow: 0 6px 16px rgba(245, 158, 11, .16);
}
.rank {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #eff6ff;
  color: #2563eb;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}
.person-row--leader .rank {
  background: #f59e0b;
  color: #fff;
}
.person-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.person-main strong { font-size: 14px; }
.person-main span { font-size: 12px; color: #6b7280; }
.rank-note {
  margin: 2px 0 0;
  font-size: 12px;
  line-height: 1.4;
  color: #92400e;
  font-weight: 600;
}
.hours { font-weight: 700; color: #0f766e; }
.person-row--leader .hours { color: #b45309; }
.details-panel {
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.details-panel .empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.detail-table-wrap {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
.detail-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.detail-table th, .detail-table td { padding: 10px 12px; border-bottom: 1px solid #eef0f3; text-align: left; vertical-align: top; }
.detail-table th { background: #f9fafb; color: #4b5563; font-weight: 700; position: sticky; top: 0; }
.detail-table .th-sortable {
  cursor: pointer;
  user-select: none;
}
.detail-table .th-sortable:hover {
  background: #f3f4f6;
}
.sort-ind {
  margin-left: 4px;
  font-size: 11px;
  color: #9ca3af;
}
.detail-row--leader td { background: #fff7ed; }
.segment-chip {
  display: inline-flex;
  margin: 0 6px 4px 0;
  padding: 3px 8px;
  border-radius: 999px;
  background: #ecfdf5;
  color: #047857;
  white-space: nowrap;
}
.td-hours { font-weight: 700; color: #0f766e; }
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(17, 24, 39, .45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.modal-content {
  width: min(620px, 100%);
  max-height: calc(100vh - 40px);
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, .28);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border-bottom: 1px solid #eef0f3;
}
.modal-header h2 { margin: 0; font-size: 18px; }
.modal-header p { margin: 5px 0 0; color: #6b7280; font-size: 13px; }
.icon-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  color: #374151;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
}
.baseline-toolbar {
  display: flex;
  align-items: end;
  gap: 12px;
  padding: 16px 20px 10px;
  flex-wrap: wrap;
}
.baseline-count {
  height: 36px;
  display: inline-flex;
  align-items: center;
  color: #6b7280;
  font-size: 13px;
}
.baseline-textarea {
  margin: 0 20px 16px;
  min-height: 300px;
  resize: vertical;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  padding: 12px;
  font-size: 13px;
  line-height: 1.5;
  font-family: Consolas, Monaco, monospace;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 20px;
  border-top: 1px solid #eef0f3;
}
@media (max-width: 900px) {
  .summary-grid, .content-grid { grid-template-columns: 1fr; }
  .filter-card, .page-header { align-items: stretch; flex-direction: column; }
  .page-actions { align-items: stretch; flex-direction: column; }
  .page-actions .btn { justify-content: center; }
}
</style>
