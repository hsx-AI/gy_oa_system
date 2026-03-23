<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <button type="button" class="btn-back" @click="goBack">← 返回</button>
          <h1 class="header-title">全部请假记录</h1>
          <p class="header-subtitle">{{ scopeHint }}</p>
        </div>
      </div>
    </div>

    <div class="content mt-xl">
      <div class="card record-card">
        <div class="card-header record-card__header">
          <div>
            <h3>请假记录</h3>
            <p class="record-card__desc">{{ recordFilterLabel }}</p>
          </div>
          <div class="record-card__filters">
            <label class="filter-label">年份：</label>
            <select v-model.number="recordYear" class="filter-select" @change="onYearChange">
              <option :value="null">全部</option>
              <option v-for="y in recordYearOptions" :key="y" :value="y">{{ y }}年</option>
            </select>
            <label class="filter-label">月份：</label>
            <select
              v-model.number="recordMonth"
              class="filter-select"
              :disabled="!recordYear"
              @change="fetchList"
            >
              <option :value="null">全年</option>
              <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
            </select>
          </div>
        </div>
        <div class="card-body record-card__body">
          <div v-if="loading" class="loading-wrap">加载中…</div>
          <div class="table-wrap" v-else-if="displayList.length">
            <table class="record-table">
              <thead>
                <tr>
                  <th>科室</th>
                  <th>姓名</th>
                  <th>请假类型</th>
                  <th>开始时间</th>
                  <th>结束时间</th>
                  <th>天数</th>
                  <th>申请时间</th>
                  <th>事由</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(r, idx) in displayList" :key="r.id != null && r.id !== '' ? String(r.id) : `row-${idx}`">
                  <td>{{ r.department }}</td>
                  <td>{{ r.name }}</td>
                  <td>{{ r.type }}</td>
                  <td>{{ r.startTime }}</td>
                  <td>{{ r.endTime }}</td>
                  <td>{{ r.duration }}</td>
                  <td>{{ r.applyTime }}</td>
                  <td class="reason-cell">{{ r.reason || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
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
              <button type="button" class="record-pagination__btn" :disabled="page <= 1" @click="page = Math.max(1, page - 1)">上一页</button>
              <span class="record-pagination__num">第 {{ page }} / {{ totalPages || 1 }} 页</span>
              <button type="button" class="record-pagination__btn" :disabled="page >= totalPages" @click="page = Math.min(totalPages, page + 1)">下一页</button>
            </div>
          </div>
          <p class="empty-text" v-else-if="!loading">暂无请假记录</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getLeaveAllRecords } from '@/api/attendance'

const router = useRouter()
const route = useRoute()
const list = ref([])
const loading = ref(false)
const scope = ref('')
const recordYear = ref(null)
const recordMonth = ref(null)
const page = ref(1)
const pageSize = ref(20)

const recordYearOptions = computed(() => {
  const y = new Date().getFullYear()
  return Array.from({ length: 6 }, (_, i) => y - i)
})

const scopeHint = computed(() => {
  if (scope.value === 'all') return '部长/副部长：查看全员已通过请假记录'
  if (scope.value === 'dept') return '当前为本科室已通过请假记录'
  return '暂无可见记录'
})

const recordFilterLabel = computed(() => {
  if (!recordYear.value) return '展示全部年份已通过请假记录'
  if (recordMonth.value) return `展示 ${recordYear.value}年${recordMonth.value}月 已通过请假记录`
  return `展示 ${recordYear.value}年 已通过请假记录`
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
    const params = { name }
    if (recordYear.value) {
      params.year = recordYear.value
      if (recordMonth.value) params.month = recordMonth.value
    }
    const res = await getLeaveAllRecords(params)
    if (res.success) {
      list.value = res.data || []
      scope.value = res.scope || 'none'
    } else {
      list.value = []
    }
    page.value = 1
  } catch (err) {
    console.error('获取全部请假记录失败:', err)
    list.value = []
  } finally {
    loading.value = false
  }
}

function onYearChange() {
  if (!recordYear.value) recordMonth.value = null
  fetchList()
}

function goBack() {
  if (route.query.from === 'leader') {
    router.push('/leader-dashboard')
  } else {
    router.back()
  }
}

onMounted(() => {
  const qYear = parseInt(route.query.year, 10)
  if (qYear > 2000) recordYear.value = qYear
  const qMonth = parseInt(route.query.month, 10)
  if (qMonth >= 1 && qMonth <= 12 && recordYear.value) recordMonth.value = qMonth
  fetchList()
})
</script>

<style scoped>
.btn-back { margin-right: 12px; padding: 6px 12px; border: 1px solid var(--border-color, #ddd); border-radius: 6px; background: #fff; cursor: pointer; font-size: 14px; }
.btn-back:hover { background: #f5f5f5; }
.header-content { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; }
.header-info { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.header-title { margin: 0; font-size: 1.5rem; }
.header-subtitle { margin: 4px 0 0 0; color: #666; font-size: 0.9rem; width: 100%; }
.mt-xl { margin-top: 24px; }
.record-card { border: 1px solid #eee; border-radius: 8px; overflow: hidden; background: #fff; }
.record-card__header { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; padding: 16px 20px; border-bottom: 1px solid #eee; }
.record-card__desc { margin: 4px 0 0 0; color: #666; font-size: 0.875rem; }
.record-card__filters { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.filter-label { font-size: 14px; color: #666; }
.filter-select { padding: 6px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
.record-card__body { padding: 16px 20px; }
.table-wrap { overflow-x: auto; }
.record-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.record-table th, .record-table td { padding: 10px 12px; border-bottom: 1px solid #eee; text-align: left; }
.record-table th { background: #f8f9fa; font-weight: 600; color: #333; }
.reason-cell { max-width: 200px; word-break: break-all; }
.record-pagination { margin-top: 16px; display: flex; align-items: center; flex-wrap: wrap; gap: 16px; }
.record-pagination__total { color: #666; font-size: 14px; }
.record-pagination__select { padding: 4px 8px; margin: 0 4px; border: 1px solid #ddd; border-radius: 4px; }
.record-pagination__pages { display: flex; align-items: center; gap: 8px; }
.record-pagination__btn { padding: 6px 12px; border: 1px solid #ddd; border-radius: 6px; background: #fff; cursor: pointer; font-size: 14px; }
.record-pagination__btn:hover:not(:disabled) { background: #f5f5f5; }
.record-pagination__btn:disabled { opacity: 0.6; cursor: not-allowed; }
.loading-wrap { padding: 24px; text-align: center; color: #666; }
.empty-text { padding: 24px; text-align: center; color: #999; }
</style>
