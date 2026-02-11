<template>
  <div class="page-container">
    <div class="page-header">
      <h1>我的申请流程</h1>
      <button class="btn btn-outline" @click="router.push('/')">返回首页</button>
    </div>

    <div class="card">
      <div class="card-header">
        <h3>申请记录（不含已通过）</h3>
        <div class="filter-row">
          <label>年份：</label>
          <select v-model="filterYear" class="filter-select">
            <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option>
          </select>
        </div>
      </div>
      <div class="card-body">
        <div class="table-wrap" v-if="listData.length">
          <table class="data-table">
            <thead>
              <tr>
                <th>类型</th>
                <th>标题</th>
                <th>状态</th>
                <th>日期</th>
                <th>单号</th>
                <th>驳回原因</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="req in listData" :key="req.uniqueId">
                <td>
                  <span class="type-tag" :class="req.sourceClass">{{ req.sourceLabel }}</span>
                </td>
                <td class="title-cell">{{ req.title }}</td>
                <td>
                  <span class="status-tag" :class="req.statusClass">{{ req.status }}</span>
                </td>
                <td>{{ req.time }}</td>
                <td>{{ req.id }}</td>
                <td class="reject-reason-cell">{{ req.status === '已驳回' && req.rejectReason ? req.rejectReason : '—' }}</td>
                <td>
                  <button type="button" class="btn btn-primary btn-sm" @click="goDetail(req)">查看</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="empty-state" v-else-if="!loading">
          <p>暂无申请记录</p>
        </div>
        <div class="empty-state" v-else>
          <p>加载中...</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getLeaveList, getOvertimeList, getBusinessTripList } from '@/api/attendance'

const router = useRouter()
const listData = ref([])
const loading = ref(false)
const filterYear = ref(new Date().getFullYear())

const userInfo = (() => {
  try {
    const s = localStorage.getItem('userInfo')
    return s ? JSON.parse(s) : {}
  } catch {
    return {}
  }
})()

const userName = userInfo.name || userInfo.userName || ''

const yearOptions = (() => {
  const y = new Date().getFullYear()
  return Array.from({ length: 6 }, (_, i) => y - i)
})()

function goDetail(req) {
  const path = req.source === 'leave' ? '/attendance/leave'
    : req.source === 'overtime' ? '/attendance/overtime'
    : '/attendance/business-trip'
  router.push(path)
}

async function fetchList() {
  if (!userName) return
  loading.value = true
  try {
    const [leaveRes, overtimeRes, btRes] = await Promise.all([
      getLeaveList({ name: userName, year: filterYear.value, status: 'all' }),
      getOvertimeList({ name: userName, year: filterYear.value, status: 'all' }),
      getBusinessTripList({ name: userName, year: filterYear.value, status: 'all' })
    ])
    const items = []
    ;(leaveRes.data || []).forEach(r => {
      if (r.status === '已通过') return
      items.push({
        uniqueId: 'leave-' + r.id,
        id: 'QJ' + r.id,
        title: (r.type || '请假') + '申请',
        status: r.status,
        statusClass: r.statusClass || 'status-processing',
        time: (r.applyTime || '').slice(0, 10),
        source: 'leave',
        sourceLabel: '请假',
        sourceClass: 'source-leave',
        rejectReason: r.rejectReason || ''
      })
    })
    ;(overtimeRes.data || []).forEach(r => {
      if (r.status === '已通过') return
      items.push({
        uniqueId: 'overtime-' + r.id,
        id: 'JB' + r.id,
        title: ((r.date || '').slice(0, 10)) + '加班登记',
        status: r.status,
        statusClass: r.statusClass || 'status-processing',
        time: (r.applyTime || r.date || '').slice(0, 10),
        source: 'overtime',
        sourceLabel: '加班',
        sourceClass: 'source-overtime',
        rejectReason: r.rejectReason || ''
      })
    })
    ;(btRes.data || []).forEach(r => {
      if (r.status === '已通过') return
      const loc = r.location ? '去' + r.location + '的' : ''
      items.push({
        uniqueId: 'bt-' + r.id,
        id: 'GC' + r.id,
        title: loc + '公出登记',
        status: r.status || '—',
        statusClass: r.statusClass || 'status-processing',
        time: (r.startTime || r.assignTime || '').slice(0, 10),
        source: 'business-trip',
        sourceLabel: '公出',
        sourceClass: 'source-trip',
        rejectReason: r.rejectReason || ''
      })
    })
    items.sort((a, b) => (b.time || '').localeCompare(a.time || ''))
    listData.value = items
  } catch (e) {
    listData.value = []
  } finally {
    loading.value = false
  }
}

watch(filterYear, fetchList)
onMounted(fetchList)
</script>

<style scoped>
.page-container { width: 100%; max-width: none; margin: 0; padding: 0 0 var(--spacing-xl); }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--spacing-xl); }
.card { background: white; border-radius: var(--radius-md); box-shadow: var(--shadow-sm); border: 1px solid var(--color-border-lighter); }
.card-header { padding: var(--spacing-lg); border-bottom: 1px solid var(--color-border-lighter); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: var(--spacing-md); }
.card-body { padding: var(--spacing-lg); }
.filter-row { display: flex; align-items: center; gap: var(--spacing-sm); }
.filter-select { padding: 6px 12px; border: 1px solid var(--color-border-base); border-radius: var(--radius-sm); font-size: 14px; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--color-border-lighter); }
.data-table th { font-weight: 600; background: var(--color-bg-lighter, #f8f9fa); }
.title-cell { max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.type-tag { display: inline-block; padding: 2px 8px; font-size: 12px; border-radius: var(--radius-sm); }
.source-leave { background: #fff1f0; color: #cf1322; }
.source-overtime { background: var(--color-primary-lightest, #e6f7ff); color: var(--color-primary); }
.source-trip { background: #e6fffb; color: #08979c; }
.status-tag { display: inline-block; padding: 2px 8px; font-size: 12px; border-radius: var(--radius-sm); }
.status-processing { color: #d97706; background: #fef3c7; }
.status-approved { color: #059669; background: #d1fae5; }
.status-rejected { color: #dc2626; background: #fee2e2; }
.empty-state { text-align: center; padding: var(--spacing-xxl); color: var(--color-text-tertiary); }
.btn { padding: 8px 16px; border-radius: var(--radius-sm); border: 1px solid; cursor: pointer; font-size: 14px; }
.btn-outline { background: white; border-color: var(--color-primary); color: var(--color-primary); }
.btn-primary { background: var(--color-primary); color: white; border-color: var(--color-primary); }
.btn-sm { padding: 4px 12px; font-size: 13px; }
</style>
