<template>
  <div class="travel-gap-block section card duty-section">
    <h2 class="section-title">
      <svg class="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M3 12h18M12 3l9 9-9 9"/>
        <circle cx="6" cy="12" r="2"/>
      </svg>
      {{ t.title }}
    </h2>
    <p class="section-desc">{{ t.desc }}</p>

    <div class="filter-bar duty-filter-bar">
      <div class="form-item">
        <label class="form-label">{{ t.dept }}</label>
        <select v-model="filterLsys" class="form-select">
          <option value="">{{ t.allDept }}</option>
          <option v-for="d in lsysList" :key="'tg-' + d" :value="d">{{ d }}</option>
        </select>
      </div>
      <div class="form-item">
        <label class="form-label">{{ t.startDate }}</label>
        <input v-model="startDate" type="date" class="form-input" />
      </div>
      <div class="form-item">
        <label class="form-label">{{ t.endDate }}</label>
        <input v-model="endDate" type="date" class="form-input" />
      </div>
      <div class="form-item">
        <label class="form-label">{{ t.checkType }}</label>
        <select v-model="checkType" class="form-select">
          <option value="all">{{ t.typeAll }}</option>
          <option value="departure">{{ t.typeDeparture }}</option>
          <option value="arrival">{{ t.typeArrival }}</option>
        </select>
      </div>
      <div class="form-item">
        <label class="form-label">{{ t.minHours }}</label>
        <select v-model.number="minHours" class="form-select">
          <option :value="0">{{ t.min0 }}</option>
          <option :value="1">{{ t.min1 }}</option>
          <option :value="4">{{ t.min4 }}</option>
          <option :value="8">{{ t.min8 }}</option>
          <option :value="16">{{ t.min16 }}</option>
          <option :value="24">{{ t.min24 }}</option>
        </select>
      </div>
      <div class="form-item form-actions">
        <button class="btn btn-primary" type="button" @click="fetchCheck" :disabled="loading">
          <svg v-if="loading" class="loading-icon" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="31.4" stroke-linecap="round">
              <animateTransform attributeName="transform" type="rotate" dur="1s" from="0 12 12" to="360 12 12" repeatCount="indefinite"/>
            </circle>
          </svg>
          {{ loading ? t.checking : t.check }}
        </button>
        <button class="btn btn-outline-duty" type="button" @click="exportCheck" :disabled="exporting || loading">
          {{ exporting ? t.exporting : t.exportExcel }}
        </button>
      </div>
    </div>

    <template v-if="fetched">
      <div class="duty-summary-grid">
        <div class="duty-metric">
          <span class="metric-label">{{ t.mDepTrips }}</span>
          <strong>{{ summary.departureTrips || 0 }}</strong>
          <span class="metric-sub">{{ t.unitRow }}</span>
        </div>
        <div class="duty-metric metric-warn">
          <span class="metric-label">{{ t.mDepGap }}</span>
          <strong>{{ summary.departureSuspicious || 0 }}</strong>
          <span class="metric-sub">{{ t.uncoveredHint }}</span>
        </div>
        <div class="duty-metric">
          <span class="metric-label">{{ t.mArrTrips }}</span>
          <strong>{{ summary.arrivalTrips || 0 }}</strong>
          <span class="metric-sub">{{ t.unitRow }}</span>
        </div>
        <div class="duty-metric metric-warn">
          <span class="metric-label">{{ t.mArrGap }}</span>
          <strong>{{ summary.arrivalSuspicious || 0 }}</strong>
          <span class="metric-sub">{{ t.uncoveredHint }}</span>
        </div>
        <div class="duty-metric metric-danger">
          <span class="metric-label">{{ t.mTotal }}</span>
          <strong>{{ summary.totalSuspicious || 0 }}</strong>
          <span class="metric-sub">{{ coverSummaryText }}</span>
        </div>
      </div>

      <div class="table-toolbar">
        <span class="table-count">{{ t.totalPrefix }}{{ displayRows.length }}{{ t.totalSuffix }}</span>
        <input
          v-model.trim="keyword"
          type="search"
          class="form-input search-input"
          :placeholder="t.searchPlaceholder"
        />
      </div>

      <div class="table-wrap detail-table-wrap">
        <table class="detail-table duty-table travel-gap-table">
          <thead>
            <tr>
              <th v-for="col in t.columns" :key="col">{{ col }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="r in displayRows"
              :key="r.checkType + '-' + r.billNo"
              :class="{
                'row-warn': (r.uncoveredHours || 0) > 0,
                'row-danger': (r.uncoveredHours || 0) >= 16,
                'row-ok': r.coverStatus === 'full',
              }"
            >
              <td>
                <span :class="['status-pill', r.checkType === 'departure' ? 'status-dep' : 'status-arr']">
                  {{ r.checkTypeText }}
                </span>
              </td>
              <td>{{ r.name }}</td>
              <td>{{ r.dept || dash }}</td>
              <td>{{ r.billNo }}</td>
              <td>{{ r.departCity || dash }}</td>
              <td>{{ r.arriveCity || dash }}</td>
              <td>{{ r.eventDate || dash }}</td>
              <td>{{ r.eventNode || dash }}</td>
              <td>{{ r.anchorPunch || dash }}</td>
              <td>
                <strong v-if="r.gapHours != null" :class="gapClass(r.gapHours)">{{ r.gapHours }}</strong>
                <span v-else>{{ dash }}</span>
              </td>
              <td>{{ r.gapWorkDays != null ? r.gapWorkDays : dash }}</td>
              <td>
                <span :class="['status-pill', coverPillClass(r.coverStatus)]">
                  {{ r.coverStatusText || dash }}
                </span>
              </td>
              <td>{{ r.coveredHours != null ? r.coveredHours : dash }}</td>
              <td>
                <strong v-if="r.uncoveredHours != null" :class="gapClass(r.uncoveredHours)">{{ r.uncoveredHours }}</strong>
                <span v-else>{{ dash }}</span>
              </td>
              <td class="remark-cell" :title="r.coverDetail || ''">{{ r.coverDetail || dash }}</td>
              <td>{{ r.billStatus || dash }}</td>
              <td class="remark-cell">{{ r.remark || '' }}</td>
            </tr>
            <tr v-if="!displayRows.length">
              <td colspan="17" class="table-empty-cell">{{ t.empty }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import {
  getDeptLsysList,
  getTravelGapCheck,
  exportTravelGapCheck,
} from '@/api/attendance'

const props = defineProps({
  externalLsysList: { type: Array, default: null },
})

const dash = '-'

const t = {
  title: '\u5dee\u65c5\u884c\u7a0b\u7a7a\u7f3a\u6838\u67e5',
  desc: '\u6309\u5dee\u65c5\u884c\u7a0b\u660e\u7ec6\uff0c\u6838\u67e5\u79bb\u54c8\u524d\u6700\u8fd1\u4e00\u6b21\u6253\u5361\u3001\u8fd4\u54c8\u540e\u7b2c\u4e00\u6b21\u6253\u5361\uff0c\u6309\u6807\u51c6\u5de5\u4f5c\u65f6\u6bb5\u7d2f\u8ba1\u4e2d\u95f4\u7a7a\u7f3a\u5c0f\u65f6\uff08\u4e0a\u5348 08:00\u201312:00\u3001\u4e0b\u5348 13:00\u201317:00\uff1b\u5468\u672b\u4e0e\u6cd5\u5b9a\u5047\u65e5\u4e0d\u8ba1\uff09\u3002\u5e76\u6838\u5bf9\u7a7a\u7f3a\u5de5\u65f6\u662f\u5426\u88ab\u5df2\u901a\u8fc7\u8bf7\u5047\u6216\u5e02\u5185\u516c\u51fa\u8986\u76d6\u3002',
  dept: '\u79d1\u5ba4',
  allDept: '\u5168\u90e8\u79d1\u5ba4',
  startDate: '\u5f00\u59cb\u65e5\u671f',
  endDate: '\u7ed3\u675f\u65e5\u671f',
  checkType: '\u6838\u67e5\u7c7b\u578b',
  typeAll: '\u5168\u90e8',
  typeDeparture: '\u4ec5\u79bb\u54c8\u524d',
  typeArrival: '\u4ec5\u8fd4\u54c8\u540e',
  minHours: '\u6700\u5c11\u7a7a\u7f3a\u5c0f\u65f6',
  min0: '\u5168\u90e8\uff08\u542b 0\uff09',
  min1: '\u2265 1 \u5c0f\u65f6',
  min4: '\u2265 4 \u5c0f\u65f6',
  min8: '\u2265 8 \u5c0f\u65f6\uff08\u7ea6 1 \u5929\uff09',
  min16: '\u2265 16 \u5c0f\u65f6\uff08\u7ea6 2 \u5929\uff09',
  min24: '\u2265 24 \u5c0f\u65f6\uff08\u7ea6 3 \u5929\uff09',
  check: '\u6838\u67e5',
  checking: '\u6838\u67e5\u4e2d...',
  exportExcel: '\u5bfc\u51fa Excel',
  exporting: '\u5bfc\u51fa\u4e2d...',
  mDepTrips: '\u79bb\u54c8\u884c\u7a0b',
  mDepGap: '\u79bb\u54c8\u672a\u8986\u76d6',
  mArrTrips: '\u8fd4\u54c8\u884c\u7a0b',
  mArrGap: '\u8fd4\u54c8\u672a\u8986\u76d6',
  mTotal: '\u672a\u8986\u76d6\u5408\u8ba1',
  unitRow: '\u6761',
  uncoveredHint: '\u4ecd\u6709\u7a7a\u7f3a\u5de5\u65f6',
  totalPrefix: '\u5171 ',
  totalSuffix: ' \u6761',
  searchPlaceholder: '\u7b5b\u9009\u59d3\u540d / \u5355\u636e\u53f7 / \u57ce\u5e02',
  empty: '\u6240\u9009\u8303\u56f4\u6682\u65e0\u5339\u914d\u884c\u7a0b\uff08\u8fd4\u54c8\u8868\u82e5\u4e3a\u7a7a\uff0c\u8bf7\u5148\u5bfc\u5165/\u63a8\u9001\u5230\u8fbe\u54c8\u5c14\u6ee8\u6570\u636e\uff09',
  columns: [
    '\u6838\u67e5\u7c7b\u578b',
    '\u59d3\u540d',
    '\u79d1\u5ba4',
    '\u5355\u636e\u7f16\u53f7',
    '\u51fa\u53d1\u57ce\u5e02',
    '\u5230\u8fbe\u57ce\u5e02',
    '\u4e8b\u4ef6\u65e5\u671f',
    '\u4e8b\u4ef6\u8282\u70b9',
    '\u5bf9\u7167\u6253\u5361',
    '\u7a7a\u7f3a\u5c0f\u65f6',
    '\u6298\u5408\u5de5\u4f5c\u65e5',
    '\u8bf7\u5047/\u5e02\u5185\u516c\u51fa',
    '\u5df2\u8986\u76d6\u5c0f\u65f6',
    '\u672a\u8986\u76d6\u5c0f\u65f6',
    '\u8986\u76d6\u660e\u7ec6',
    '\u72b6\u6001',
    '\u5907\u6ce8',
  ],
  exportName: '\u5dee\u65c5\u884c\u7a0b\u7a7a\u7f3a\u6838\u67e5',
  allDeptFile: '\u5168\u90e8\u79d1\u5ba4',
}

function defaultRange() {
  const now = new Date()
  const y = now.getFullYear()
  return { start: `${y}-01-01`, end: `${y}-12-31` }
}

const range = defaultRange()
const filterLsys = ref('')
const startDate = ref(range.start)
const endDate = ref(range.end)
const checkType = ref('all')
const minHours = ref(4)
const keyword = ref('')
const loading = ref(false)
const exporting = ref(false)
const fetched = ref(false)
const summary = ref({})
const rows = ref([])
const lsysList = ref([])

const typedRows = computed(() => {
  if (checkType.value === 'departure') return rows.value.filter(r => r.checkType === 'departure')
  if (checkType.value === 'arrival') return rows.value.filter(r => r.checkType === 'arrival')
  return rows.value
})

const displayRows = computed(() => {
  const kw = keyword.value.toLowerCase()
  if (!kw) return typedRows.value
  return typedRows.value.filter(r => {
    const blob = [r.name, r.billNo, r.departCity, r.arriveCity, r.dept, r.accountDept, r.coverDetail, r.coverStatusText]
      .map(v => String(v || '').toLowerCase())
      .join('|')
    return blob.includes(kw)
  })
})

const coverSummaryText = computed(() => {
  const s = summary.value || {}
  return `\u5df2\u8986\u76d6 ${s.fullyCovered || 0} / \u90e8\u5206 ${s.partialCovered || 0} / \u672a\u8986\u76d6 ${s.uncovered || 0}`
})

function gapClass(n) {
  if (n >= 16) return 'gap-danger'
  if (n > 0) return 'gap-warn'
  return ''
}

function coverPillClass(status) {
  if (status === 'full') return 'status-cover-full'
  if (status === 'partial') return 'status-cover-partial'
  if (status === 'none') return 'status-cover-none'
  return 'status-cover-na'
}

async function fetchCheck() {
  if (!startDate.value || !endDate.value) return
  loading.value = true
  fetched.value = true
  try {
    const params = {
      start_date: startDate.value,
      end_date: endDate.value,
      min_hours: minHours.value,
    }
    if (filterLsys.value) params.lsys = filterLsys.value
    const res = await getTravelGapCheck(params)
    if (res.success) {
      summary.value = res.summary || {}
      rows.value = res.rows || []
    } else {
      summary.value = {}
      rows.value = []
    }
  } catch (e) {
    console.error(e)
    summary.value = {}
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function exportCheck() {
  if (!startDate.value || !endDate.value) return
  exporting.value = true
  try {
    const params = {
      start_date: startDate.value,
      end_date: endDate.value,
      min_hours: minHours.value,
    }
    if (filterLsys.value) params.lsys = filterLsys.value
    const blob = await exportTravelGapCheck(params)
    if (blob instanceof Blob) {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const scope = filterLsys.value || t.allDeptFile
      a.download = `${scope}_${startDate.value}_${endDate.value}_${t.exportName}.xlsx`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
  } catch (e) {
    console.error(e)
  } finally {
    exporting.value = false
  }
}

async function loadLsysList() {
  const excl = ['\u5176\u4ed6\u90e8\u95e8\u5458\u5de5', '\u5176\u4ed6\u90e8\u95e8\u6210\u5458']
  if (props.externalLsysList?.length) {
    lsysList.value = props.externalLsysList.filter(v => v && !excl.includes(String(v).trim()))
    return
  }
  try {
    const listRes = await getDeptLsysList()
    if (listRes.success && listRes.list?.length) {
      lsysList.value = listRes.list.filter(v => v && !excl.includes(v.trim()))
    }
  } catch { /* ignore */ }
}

watch(
  () => props.externalLsysList,
  (v) => {
    const excl = ['\u5176\u4ed6\u90e8\u95e8\u5458\u5de5', '\u5176\u4ed6\u90e8\u95e8\u6210\u5458']
    if (v?.length) {
      lsysList.value = v.filter(x => x && !excl.includes(String(x).trim()))
    }
  },
  { deep: true },
)

onMounted(() => {
  loadLsysList()
})
</script>

<style scoped>
.travel-gap-block.section {
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
  line-height: 1.55;
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

.metric-warn strong { color: #d97706; }
.metric-danger strong { color: #dc2626; }

.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
  flex-wrap: wrap;
}

.table-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.search-input {
  min-width: 220px;
}

.table-wrap {
  width: 100%;
  overflow: auto;
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--radius-base);
}

.detail-table-wrap {
  max-height: 560px;
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

.travel-gap-table {
  min-width: 1400px;
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

.status-dep {
  color: #0e7490;
  background: #cffafe;
}

.status-arr {
  color: #047857;
  background: #d1fae5;
}

.status-cover-full {
  color: #047857;
  background: #d1fae5;
}

.status-cover-partial {
  color: #92400e;
  background: #fef3c7;
}

.status-cover-none {
  color: #991b1b;
  background: #fee2e2;
}

.status-cover-na {
  color: #6b7280;
  background: #f3f4f6;
}

.row-warn {
  background: #fffbeb;
}

.row-danger {
  background: #fef2f2;
}

.row-ok {
  background: #f0fdf4;
}

.gap-warn { color: #d97706; }
.gap-danger { color: #dc2626; }

.remark-cell {
  color: #b45309;
  max-width: 200px;
  white-space: normal;
}

@media (max-width: 960px) {
  .duty-summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 768px) {
  .filter-bar { flex-direction: column; align-items: stretch; }
  .duty-summary-grid { grid-template-columns: 1fr; }
}
</style>
