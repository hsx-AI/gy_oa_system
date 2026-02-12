<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <button type="button" class="btn-back" @click="goBack">← 返回</button>
          <h1 class="header-title">全部公出记录</h1>
          <p class="header-subtitle">{{ scopeHint }}</p>
        </div>
      </div>
    </div>

    <div class="content mt-xl">
      <div class="card record-card">
        <div class="card-header record-card__header">
          <div>
            <h3>公出记录</h3>
            <p class="record-card__desc">{{ recordFilterLabel }}</p>
          </div>
          <div class="record-card__filters">
            <label class="filter-label">年份：</label>
            <select v-model.number="recordYear" class="filter-select" @change="fetchList">
              <option :value="null">全部</option>
              <option v-for="y in recordYearOptions" :key="y" :value="y">{{ y }}年</option>
            </select>
          </div>
        </div>
        <div class="card-body record-card__body">
          <div v-if="loading" class="loading-wrap">加载中…</div>
          <div class="table-wrap" v-else-if="displayList.length">
            <table class="record-table">
              <thead>
                <tr>
                  <th>委派单位</th>
                  <th>公出人</th>
                  <th>委派时间</th>
                  <th>项目名称</th>
                  <th>公出地点</th>
                  <th>出发时间</th>
                  <th>实际返回时间</th>
                  <th>审批状态</th>
                  <th>当前审批人</th>
                  <th>驳回原因</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in displayList" :key="r.id">
                  <td>{{ r.targetUnit }}</td>
                  <td>{{ r.person }}</td>
                  <td>{{ r.assignTime }}</td>
                  <td>{{ r.projectName }}</td>
                  <td>{{ r.location }}</td>
                  <td>{{ r.startTime || '—' }}</td>
                  <td>{{ r.actualReturnTime ? r.actualReturnTime.replace('T', ' ').slice(0, 16) : '—' }}</td>
                  <td><span class="status-tag" :class="r.statusClass || 'status-processing'">{{ r.status || '审批中' }}</span></td>
                  <td>{{ r.status === '审批中' && r.currentApprover ? r.currentApprover : '—' }}</td>
                  <td class="reject-reason-cell">{{ r.status === '已驳回' && r.rejectReason ? r.rejectReason : '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <!-- 分页 -->
          <div class="record-pagination" v-if="!loading && list.length">
            <span class="record-pagination__total">共 {{ list.length }} 条</span>
            <span class="record-pagination__size">
              每页
              <select v-model.number="pageSize" class="record-pagination__select">
                <option :value="10">10</option>
                <option :value="20">20</option>
                <option :value="50">50</option>
              </select>
              条
            </span>
            <div class="record-pagination__pages">
              <button
                type="button"
                class="record-pagination__btn"
                :disabled="page <= 1"
                @click="page = Math.max(1, page - 1)"
              >
                上一页
              </button>
              <span class="record-pagination__num">
                第 {{ page }} / {{ totalPages || 1 }} 页
              </span>
              <button
                type="button"
                class="record-pagination__btn"
                :disabled="page >= totalPages"
                @click="page = Math.min(totalPages, page + 1)"
              >
                下一页
              </button>
            </div>
          </div>
          <p class="empty-text" v-else-if="!loading">暂无公出记录</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getBusinessTripAllRecords } from '@/api/attendance'

const router = useRouter()
const list = ref([])
const loading = ref(false)
const scope = ref('') // all | dept | none
const recordYear = ref(null) // null = 全部年份
const page = ref(1)
const pageSize = ref(20)

const recordYearOptions = computed(() => {
  const y = new Date().getFullYear()
  return Array.from({ length: 6 }, (_, i) => y - i)
})

const scopeHint = computed(() => {
  if (scope.value === 'all') return '部长/副部长：按时间顺序查看全员公出记录'
  if (scope.value === 'dept') return '当前为本科室公出记录（按时间顺序）'
  return '暂无可见记录'
})

const recordFilterLabel = computed(() => {
  if (recordYear.value) return `展示 ${recordYear.value}年 公出记录`
  return '展示全部年份公出记录'
})

const totalPages = computed(() => Math.max(1, Math.ceil(list.value.length / pageSize.value)))
const displayList = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return list.value.slice(start, start + pageSize.value)
})

function getCurrentUserName() {
  const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
  return (userInfo.name || userInfo.userName || '').trim()
}

async function fetchList() {
  const name = getCurrentUserName()
  if (!name) {
    list.value = []
    scope.value = 'none'
    return
  }
  loading.value = true
  try {
    const res = await getBusinessTripAllRecords({
      name,
      year: recordYear.value ?? undefined
    })
    if (res.success) {
      list.value = res.data || []
      scope.value = res.scope || 'none'
    } else {
      list.value = []
    }
    page.value = 1
  } catch (err) {
    console.error('获取全部公出记录失败:', err)
    list.value = []
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push('/attendance/business-trip')
}

onMounted(() => fetchList())
</script>

<style scoped>
.btn-back {
  margin-right: 12px;
  padding: 6px 12px;
  border: 1px solid var(--border-color, #ddd);
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
}
.btn-back:hover {
  background: #f5f5f5;
}
.header-content {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.header-info {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.header-title {
  margin: 0;
  font-size: 1.5rem;
}
.header-subtitle {
  margin: 4px 0 0 0;
  color: #666;
  font-size: 0.9rem;
  width: 100%;
}
.mt-xl {
  margin-top: 24px;
}
.record-card {
  border: 1px solid #eee;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}
.record-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
}
.record-card__desc {
  margin: 4px 0 0 0;
  color: #666;
  font-size: 0.875rem;
}
.record-card__filters {
  display: flex;
  align-items: center;
  gap: 8px;
}
.filter-label {
  font-size: 14px;
  color: #666;
}
.filter-select {
  padding: 6px 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}
.record-card__body {
  padding: 16px 20px;
}
.table-wrap {
  overflow-x: auto;
}
.record-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.record-table th,
.record-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #eee;
  text-align: left;
}
.record-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #333;
}
.reject-reason-cell {
  max-width: 180px;
  word-break: break-all;
}
.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}
.status-approved {
  background: #e8f5e9;
  color: #2e7d32;
}
.status-rejected {
  background: #ffebee;
  color: #c62828;
}
.status-processing {
  background: #fff3e0;
  color: #e65100;
}
.record-pagination {
  margin-top: 16px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}
.record-pagination__total {
  color: #666;
  font-size: 14px;
}
.record-pagination__select {
  padding: 4px 8px;
  margin: 0 4px;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.record-pagination__pages {
  display: flex;
  align-items: center;
  gap: 8px;
}
.record-pagination__btn {
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
}
.record-pagination__btn:hover:not(:disabled) {
  background: #f5f5f5;
}
.record-pagination__btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.loading-wrap {
  padding: 24px;
  text-align: center;
  color: #666;
}
.empty-text {
  padding: 24px;
  text-align: center;
  color: #999;
}
</style>
