<template>
  <div class="travel-page">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">�����г���ϸ��ѯ</h1>
          <p class="header-subtitle">
            ���� pusher ���͵ġ��뿪������ / ��������������������ݱ��Ψһ��״̬Ϊ����ɡ��ĵ��������ٸ���
          </p>
        </div>
        <div class="header-actions">
          <button type="button" class="btn" :disabled="loading" @click="reloadAll">
            {{ loading ? '�����С�' : 'ˢ��' }}
          </button>
          <router-link to="/admin/health-monitor" class="btn btn-secondary">����ϵͳ����Ա</router-link>
        </div>
      </div>
    </div>

    <div class="container">
      <div v-if="!canAccess" class="card tip">
        <p>������Ȩ�޷��ʴ�ҳ�棬��ϵͳ����Ա��webconfig.admin1���ɲ鿴��</p>
        <router-link to="/" class="btn btn-primary">������ҳ</router-link>
      </div>

      <template v-else>
        <section class="summary-grid">
          <article v-for="item in summaryItems" :key="item.key" class="summary-card card">
            <h3>{{ item.label }}</h3>
            <div class="summary-metrics">
              <div><b>{{ item.total }}</b><span>�ϼ�</span></div>
              <div><b>{{ item.completed }}</b><span>�����</span></div>
              <div><b>{{ item.processing }}</b><span>�����е�</span></div>
            </div>
            <p class="summary-meta">������£�{{ item.latestUpdate || '����' }}</p>
          </article>
        </section>

        <section class="card toolbar-card">
          <div class="tabs">
            <button
              type="button"
              :class="{ on: direction === 'departure' }"
              @click="switchDirection('departure')"
            >�뿪������</button>
            <button
              type="button"
              :class="{ on: direction === 'arrival' }"
              @click="switchDirection('arrival')"
            >���������</button>
          </div>
          <div class="filters">
            <input
              v-model.trim="keyword"
              type="search"
              class="filter-input"
              placeholder="���ݱ�� / ������ / ���� / ˵��"
              @keyup.enter="search"
            >
            <select v-model="billStatus" class="filter-input">
              <option value="">ȫ��״̬</option>
              <option value="���">���</option>
              <option value="������">������</option>
            </select>
            <input v-model="dateFrom" type="date" class="filter-input" title="��������">
            <input v-model="dateTo" type="date" class="filter-input" title="������ֹ">
            <button type="button" class="btn btn-primary" :disabled="loading" @click="search">��ѯ</button>
            <button type="button" class="btn" :disabled="loading" @click="resetFilters">����</button>
          </div>
        </section>

        <section class="card table-card">
          <div class="table-head">
            <h3>{{ currentLabel }}</h3>
            <span>�� {{ total }} �� �� �� {{ page }} / {{ totalPages }} ҳ</span>
          </div>
          <div v-if="loading" class="empty">�����С�</div>
          <div v-else-if="!rows.length" class="empty">�������ݣ��ȴ� pusher ���ͺ��Զ���⣩</div>
          <div v-else class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>���ݱ��</th>
                  <th>������</th>
                  <th>��������</th>
                  <th>�������</th>
                  <th>��������</th>
                  <th>��������</th>
                  <th>�뿪����</th>
                  <th>����</th>
                  <th>��ͨ����</th>
                  <th>��ϯ</th>
                  <th>��ͨ��</th>
                  <th>ס�޷�</th>
                  <th>�򳵷�</th>
                  <th>���潻ͨ</th>
                  <th>�����</th>
                  <th>״̬</th>
                  <th>����˵��</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in rows" :key="row.billNo">
                  <td class="mono">{{ row.billNo }}</td>
                  <td>{{ row.reimbursedBy || '��' }}</td>
                  <td>{{ row.departCity || '��' }}</td>
                  <td>{{ row.arriveCity || '��' }}</td>
                  <td>{{ row.departDate || '��' }}</td>
                  <td>{{ row.arriveDate || '��' }}</td>
                  <td>{{ row.leaveDate || '��' }}</td>
                  <td>{{ row.tripDays ?? '��' }}</td>
                  <td>{{ row.transport || '��' }}</td>
                  <td>{{ row.seatClass || '��' }}</td>
                  <td class="num">{{ formatMoney(row.transportFee) }}</td>
                  <td class="num">{{ formatMoney(row.hotelFee) }}</td>
                  <td class="num">{{ formatMoney(row.taxiFee) }}</td>
                  <td class="num">{{ formatMoney(row.prepaidTransport) }}</td>
                  <td>{{ row.fillDate || '��' }}</td>
                  <td>
                    <span class="status-pill" :class="row.billStatus === '���' ? 'done' : 'pending'">
                      {{ row.billStatus || '��' }}
                    </span>
                  </td>
                  <td class="remark" :title="row.remark || ''">{{ row.remark || '��' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="totalPages > 1" class="pager">
            <button type="button" class="btn" :disabled="page <= 1 || loading" @click="goPage(page - 1)">��һҳ</button>
            <button type="button" class="btn" :disabled="page >= totalPages || loading" @click="goPage(page + 1)">��һҳ</button>
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
  direction.value === 'arrival' ? '������������������=��������' : '�뿪����������������=��������'
))

function formatMoney(value) {
  if (value === null || value === undefined || value === '') return '��'
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
    alert(e.response?.data?.detail || e.message || '��ѯʧ��')
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
