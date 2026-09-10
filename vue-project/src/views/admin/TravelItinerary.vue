<template>
  <div class="travel-page">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">{{ t.title }}</h1>
          <p class="header-subtitle">{{ t.subtitle }}</p>
        </div>
        <div class="header-actions">
          <button type="button" class="btn" :disabled="loading" @click="reloadAll">
            {{ loading ? t.loading : t.refresh }}
          </button>
          <router-link to="/admin/health-monitor" class="btn btn-secondary">{{ t.backAdmin }}</router-link>
        </div>
      </div>
    </div>

    <div class="container">
      <div v-if="!canAccess" class="card tip">
        <p>{{ t.noPermission }}</p>
        <router-link to="/" class="btn btn-primary">{{ t.backHome }}</router-link>
      </div>

      <template v-else>
        <section class="summary-grid">
          <article v-for="item in summaryItems" :key="item.key" class="summary-card card">
            <h3>{{ item.label }}</h3>
            <div class="summary-metrics">
              <div><b>{{ item.total }}</b><span>{{ t.total }}</span></div>
              <div><b>{{ item.completed }}</b><span>{{ t.completed }}</span></div>
              <div><b>{{ item.processing }}</b><span>{{ t.processing }}</span></div>
            </div>
            <p class="summary-meta">{{ t.latestUpdate }}{{ item.latestUpdate || t.none }}</p>
          </article>
        </section>

        <section class="card toolbar-card">
          <div class="tabs">
            <button
              type="button"
              :class="{ on: direction === 'departure' }"
              @click="switchDirection('departure')"
            >{{ t.tabDeparture }}</button>
            <button
              type="button"
              :class="{ on: direction === 'arrival' }"
              @click="switchDirection('arrival')"
            >{{ t.tabArrival }}</button>
          </div>
          <div class="filters">
            <input
              v-model.trim="keyword"
              type="search"
              class="filter-input"
              :placeholder="t.keywordPlaceholder"
              @keyup.enter="search"
            >
            <select v-model="billStatus" class="filter-input">
              <option value="">{{ t.allStatus }}</option>
              <option :value="t.statusDone">{{ t.statusDone }}</option>
              <option :value="t.statusProcessing">{{ t.statusProcessing }}</option>
            </select>
            <input v-model="dateFrom" type="date" class="filter-input" :title="t.dateFrom">
            <input v-model="dateTo" type="date" class="filter-input" :title="t.dateTo">
            <button type="button" class="btn btn-primary" :disabled="loading" @click="search">{{ t.search }}</button>
            <button type="button" class="btn" :disabled="loading" @click="resetFilters">{{ t.reset }}</button>
          </div>
        </section>

        <section class="card table-card">
          <div class="table-head">
            <h3>{{ currentLabel }}</h3>
            <span>{{ pageInfoText }}</span>
          </div>
          <div v-if="loading" class="empty">{{ t.loading }}</div>
          <div v-else-if="!rows.length" class="empty">{{ t.empty }}</div>
          <div v-else class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th v-for="col in t.columns" :key="col">{{ col }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in rows" :key="row.billNo">
                  <td class="mono">{{ row.billNo }}</td>
                  <td>{{ row.reimbursedBy || dash }}</td>
                  <td>{{ row.departCity || dash }}</td>
                  <td>{{ row.arriveCity || dash }}</td>
                  <td>{{ row.departDate || dash }}</td>
                  <td>{{ row.arriveDate || dash }}</td>
                  <td>{{ row.leaveDate || dash }}</td>
                  <td>{{ row.tripDays ?? dash }}</td>
                  <td>{{ row.transport || dash }}</td>
                  <td>{{ row.seatClass || dash }}</td>
                  <td class="num">{{ formatMoney(row.transportFee) }}</td>
                  <td class="num">{{ formatMoney(row.hotelFee) }}</td>
                  <td class="num">{{ formatMoney(row.taxiFee) }}</td>
                  <td class="num">{{ formatMoney(row.prepaidTransport) }}</td>
                  <td>{{ row.fillDate || dash }}</td>
                  <td>
                    <span class="status-pill" :class="row.billStatus === t.statusDone ? 'done' : 'pending'">
                      {{ row.billStatus || dash }}
                    </span>
                  </td>
                  <td class="remark" :title="row.remark || ''">{{ row.remark || dash }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="totalPages > 1" class="pager">
            <button type="button" class="btn" :disabled="page <= 1 || loading" @click="goPage(page - 1)">{{ t.prev }}</button>
            <button type="button" class="btn" :disabled="page >= totalPages || loading" @click="goPage(page + 1)">{{ t.next }}</button>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getUploadConfig } from '@/api/attendance'
import { getTravelItineraryList, getTravelItinerarySummary } from '@/api/travelItinerary'

const dash = '-'

const t = {
  title: '\u5dee\u65c5\u884c\u7a0b\u660e\u7ec6\u67e5\u8be2',
  subtitle: '\u516c\u7f51 pusher \u63a8\u9001\u7684\u300c\u79bb\u5f00\u54c8\u5c14\u6ee8 / \u5230\u8fbe\u54c8\u5c14\u6ee8\u300d\u62a5\u8868\uff1b\u5355\u636e\u7f16\u53f7\u552f\u4e00\uff0c\u72b6\u6001\u4e3a\u300c\u5b8c\u6210\u300d\u7684\u5355\u636e\u5165\u5e93\u540e\u4e0d\u518d\u66f4\u65b0',
  loading: '\u52a0\u8f7d\u4e2d...',
  refresh: '\u5237\u65b0',
  backAdmin: '\u8fd4\u56de\u7cfb\u7edf\u7ba1\u7406\u5458',
  noPermission: '\u60a8\u6682\u65e0\u6743\u9650\u8bbf\u95ee\u6b64\u9875\u9762\uff0c\u4ec5\u7cfb\u7edf\u7ba1\u7406\u5458\uff08webconfig.admin1\uff09\u53ef\u67e5\u770b\u3002',
  backHome: '\u8fd4\u56de\u9996\u9875',
  total: '\u5408\u8ba1',
  completed: '\u5df2\u5b8c\u6210',
  processing: '\u5904\u7406\u4e2d\u7b49',
  latestUpdate: '\u6700\u8fd1\u66f4\u65b0\uff1a',
  none: '\u6682\u65e0',
  tabDeparture: '\u79bb\u5f00\u54c8\u5c14\u6ee8',
  tabArrival: '\u5230\u8fbe\u54c8\u5c14\u6ee8',
  keywordPlaceholder: '\u5355\u636e\u7f16\u53f7 / \u62a5\u9500\u4eba / \u57ce\u5e02 / \u8bf4\u660e',
  allStatus: '\u5168\u90e8\u72b6\u6001',
  statusDone: '\u5b8c\u6210',
  statusProcessing: '\u5904\u7406\u4e2d',
  dateFrom: '\u51fa\u53d1\u65e5\u8d77',
  dateTo: '\u51fa\u53d1\u65e5\u6b62',
  search: '\u67e5\u8be2',
  reset: '\u91cd\u7f6e',
  empty: '\u6682\u65e0\u6570\u636e\uff08\u7b49\u5f85 pusher \u63a8\u9001\u540e\u81ea\u52a8\u5165\u5e93\uff09',
  prev: '\u4e0a\u4e00\u9875',
  next: '\u4e0b\u4e00\u9875',
  labelDeparture: '\u79bb\u5f00\u54c8\u5c14\u6ee8\uff08\u51fa\u53d1\u57ce\u5e02=\u54c8\u5c14\u6ee8\uff09',
  labelArrival: '\u5230\u8fbe\u54c8\u5c14\u6ee8\uff08\u5230\u8fbe\u57ce\u5e02=\u54c8\u5c14\u6ee8\uff09',
  queryFailed: '\u67e5\u8be2\u5931\u8d25',
  columns: [
    '\u5355\u636e\u7f16\u53f7',
    '\u62a5\u9500\u4eba',
    '\u51fa\u53d1\u57ce\u5e02',
    '\u5230\u8fbe\u57ce\u5e02',
    '\u51fa\u53d1\u65e5\u671f',
    '\u5230\u8fbe\u65e5\u671f',
    '\u79bb\u5f00\u65e5\u671f',
    '\u5929\u6570',
    '\u4ea4\u901a\u5de5\u5177',
    '\u5750\u5e2d',
    '\u4ea4\u901a\u8d39',
    '\u4f4f\u5bbf\u8d39',
    '\u6253\u8f66\u8d39',
    '\u4ee3\u57ab\u4ea4\u901a',
    '\u586b\u62a5\u65e5\u671f',
    '\u72b6\u6001',
    '\u62a5\u9500\u8bf4\u660e',
  ],
}

const userName = (() => {
  try {
    return JSON.parse(localStorage.getItem('userInfo') || '{}').name || ''
  } catch {
    return ''
  }
})()

const canAccess = ref(false)
const loading = ref(false)
const summaryItems = ref([])
const direction = ref('departure')
const keyword = ref('')
const billStatus = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 50

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const currentLabel = computed(() => (
  direction.value === 'arrival' ? t.labelArrival : t.labelDeparture
))
const pageInfoText = computed(() => (
  `\u5171 ${total.value} \u6761 \u00b7 \u7b2c ${page.value} / ${totalPages.value} \u9875`
))

function formatMoney(value) {
  if (value === null || value === undefined || value === '') return dash
  const num = Number(value)
  if (Number.isNaN(num)) return value
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function checkPermission() {
  try {
    const cfg = await getUploadConfig()
    const admin1 = (cfg?.admin1 || '').trim()
    canAccess.value = !!(admin1 && userName === admin1)
  } catch {
    canAccess.value = false
  }
}

async function loadSummary() {
  const res = await getTravelItinerarySummary({ current_user: userName })
  summaryItems.value = res?.items || []
}

async function loadList() {
  loading.value = true
  try {
    const res = await getTravelItineraryList({
      current_user: userName,
      direction: direction.value,
      keyword: keyword.value,
      bill_status: billStatus.value,
      date_from: dateFrom.value,
      date_to: dateTo.value,
      page: page.value,
      page_size: pageSize,
    })
    rows.value = res?.items || []
    total.value = Number(res?.total || 0)
  } catch (e) {
    rows.value = []
    total.value = 0
    alert(e.response?.data?.detail || e.message || t.queryFailed)
  } finally {
    loading.value = false
  }
}

async function reloadAll() {
  if (!canAccess.value) return
  loading.value = true
  try {
    await loadSummary()
    await loadList()
  } finally {
    loading.value = false
  }
}

function switchDirection(next) {
  if (direction.value === next) return
  direction.value = next
  page.value = 1
  loadList()
}

function search() {
  page.value = 1
  loadList()
}

function resetFilters() {
  keyword.value = ''
  billStatus.value = ''
  dateFrom.value = ''
  dateTo.value = ''
  page.value = 1
  loadList()
}

function goPage(next) {
  page.value = next
  loadList()
}

onMounted(async () => {
  await checkPermission()
  if (canAccess.value) await reloadAll()
})
</script>

<style scoped>
.travel-page { max-width: 1600px; margin: 0 auto; padding: 0 16px 40px; }
.header-content { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }
.header-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.container { margin-top: 16px; }
.tip { padding: 28px; }
.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 14px;
}
.summary-card { padding: 18px 20px; }
.summary-card h3 { margin: 0 0 12px; font-size: 16px; }
.summary-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.summary-metrics div { background: #f8fafc; border-radius: 8px; padding: 10px; text-align: center; }
.summary-metrics b { display: block; font-size: 22px; color: #0f172a; }
.summary-metrics span { color: #64748b; font-size: 12px; }
.summary-meta { margin: 12px 0 0; color: #64748b; font-size: 13px; }
.toolbar-card { padding: 16px 18px; margin-bottom: 14px; }
.tabs { display: flex; gap: 8px; margin-bottom: 12px; }
.tabs button {
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 8px;
  padding: 8px 14px;
  cursor: pointer;
}
.tabs button.on { background: #0f766e; border-color: #0f766e; color: #fff; font-weight: 600; }
.filters { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.filter-input {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 8px 10px;
  min-width: 140px;
}
.table-card { padding: 0; overflow: hidden; }
.table-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid #e2e8f0;
}
.table-head h3 { margin: 0; font-size: 16px; }
.table-wrap { overflow: auto; max-height: 70vh; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th,
.data-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #edf2f7;
  white-space: nowrap;
  text-align: left;
}
.data-table th {
  position: sticky;
  top: 0;
  background: #0f766e;
  color: #fff;
  z-index: 1;
}
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.remark {
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.status-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
}
.status-pill.done { background: #dcfce7; color: #166534; }
.status-pill.pending { background: #fef3c7; color: #92400e; }
.empty { padding: 48px 16px; text-align: center; color: #94a3b8; }
.pager { display: flex; justify-content: flex-end; gap: 8px; padding: 12px 16px; }
@media (max-width: 900px) {
  .summary-grid { grid-template-columns: 1fr; }
  .header-content { flex-direction: column; }
}
</style>
