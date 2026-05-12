<template>
  <div class="kqyc-page">
    <div class="page-header-bar">
      <div class="header-content">
        <div>
          <h1 class="page-title">打卡异常申请记录</h1>
          <p class="page-subtitle">{{ scopeHint }}</p>
        </div>
        <div class="header-actions">
          <button class="btn btn-outline" @click="router.push('/attendance')">返回考勤页</button>
        </div>
      </div>
    </div>

    <div class="container">
      <div class="filter-bar card">
        <div class="filter-group">
          <label>年份</label>
          <select v-model="filter.year" class="form-input">
            <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option>
          </select>
        </div>
        <div class="filter-group">
          <label>月份</label>
          <select v-model="filter.month" class="form-input">
            <option :value="0">全部</option>
            <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
          </select>
        </div>
        <div class="filter-group">
          <label>状态</label>
          <select v-model="filter.status" class="form-input">
            <option value="all">全部</option>
            <option value="pending">审批中</option>
            <option value="approved">已通过</option>
            <option value="rejected">已驳回</option>
          </select>
        </div>
        <div class="filter-group flex-grow">
          <label>关键字</label>
          <input v-model="filter.keyword" class="form-input" placeholder="姓名 / 事由 / 说明" @keyup.enter="loadData()">
        </div>
        <div class="filter-actions">
          <button class="btn btn-primary" @click="loadData()" :disabled="loading">
            {{ loading ? '查询中...' : '查询' }}
          </button>
          <button class="btn btn-outline" @click="resetFilter">重置</button>
        </div>
      </div>

      <div class="table-card card">
        <div class="table-header">
          <h3 class="table-title">查询结果</h3>
          <span class="count-info">共 {{ total }} 条</span>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>申请人</th>
                <th>科室</th>
                <th>异常日期</th>
                <th>异常时段</th>
                <th>事由</th>
                <th>说明</th>
                <th>附件</th>
                <th>一级审批</th>
                <th>二级审批</th>
                <th>状态</th>
                <th>处理结果</th>
                <th>申请时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="12" class="text-center text-tertiary">加载中…</td>
              </tr>
              <tr v-else-if="!records.length">
                <td colspan="12" class="text-center text-tertiary">暂无打卡异常申请记录</td>
              </tr>
              <tr v-for="r in records" :key="r.id">
                <td>{{ r.applicant }}</td>
                <td>{{ r.department }}</td>
                <td>{{ r.attendance_date }}</td>
                <td>{{ r.time_from }} ~ {{ r.time_to }}</td>
                <td>{{ r.reason_type || '—' }}</td>
                <td class="desc-cell" :title="r.description">{{ r.description }}</td>
                <td>
                  <a v-if="r.attachment" :href="attachmentUrl(r.attachment)" target="_blank" class="link-file">
                    {{ r.attachment_original || '下载' }}
                  </a>
                  <span v-else>—</span>
                </td>
                <td>
                  <div class="appr-cell">
                    <span class="appr-name">{{ r.first_approver }}</span>
                    <span class="appr-status" :class="statusTagClass(r.first_status)">{{ approverStatusText(r.first_status) }}</span>
                  </div>
                </td>
                <td>
                  <div class="appr-cell">
                    <span class="appr-name">{{ r.second_approver }}</span>
                    <span class="appr-status" :class="statusTagClass(r.second_status)">{{ approverStatusText(r.second_status) }}</span>
                  </div>
                </td>
                <td>
                  <span class="status-tag" :class="r.status_class">{{ r.status_text }}</span>
                  <div v-if="r.reject_reason" class="reject-reason" :title="r.reject_reason">驳回: {{ r.reject_reason }}</div>
                </td>
                <td>
                  <span v-if="r.processed_to_trip" class="processed-tag">已处理为市内公出</span>
                  <span v-else class="text-tertiary">—</span>
                  <div v-if="r.dakaman_confirmed" class="dakaman-confirmed-tag">
                    打卡管理员已确认（{{ r.dakaman_confirmed_by || '—' }} · {{ r.dakaman_confirmed_at }}）
                  </div>
                </td>
                <td>{{ r.apply_time }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="pagination" v-if="total > pageSize">
          <button :disabled="filter.page <= 1" @click="goPage(filter.page - 1)">上一页</button>
          <span>第 {{ filter.page }} / {{ totalPages }} 页</span>
          <button :disabled="filter.page >= totalPages" @click="goPage(filter.page + 1)">下一页</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getKqycRecords, kqycAttachmentUrl } from '@/api/attendanceException'

const router = useRouter()

const records = ref([])
const total = ref(0)
const loading = ref(false)
const pageSize = 20
const scope = ref('self')

const now = new Date()
const filter = reactive({
  year: now.getFullYear(),
  month: 0,
  status: 'all',
  keyword: '',
  page: 1,
})

const yearOptions = computed(() => {
  const y = now.getFullYear()
  return Array.from({ length: 6 }, (_, i) => y - i)
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const scopeHint = computed(() => {
  if (scope.value === 'all') return '可查看：全部员工的记录'
  if (scope.value === 'lsys') return '可查看：本科室成员的记录'
  return '可查看：本人的记录'
})

function attachmentUrl(filename) {
  return kqycAttachmentUrl(filename)
}

function approverStatusText(s) {
  const n = Number(s || 0)
  if (n === 1) return '通过'
  if (n === 2) return '驳回'
  return '待审批'
}
function statusTagClass(s) {
  const n = Number(s || 0)
  if (n === 1) return 'status-approved'
  if (n === 2) return 'status-rejected'
  return 'status-processing'
}

function getCurrentUserName() {
  try {
    const u = JSON.parse(localStorage.getItem('userInfo') || '{}')
    return (u.name || u.userName || '').trim()
  } catch {
    return ''
  }
}

async function loadData() {
  const name = getCurrentUserName()
  if (!name) return
  loading.value = true
  try {
    const params = {
      current_user: name,
      year: filter.year,
      status: filter.status,
      keyword: filter.keyword,
      page: filter.page,
      page_size: pageSize,
    }
    if (filter.month) params.month = filter.month
    const res = await getKqycRecords(params)
    if (res?.success) {
      records.value = res.data || []
      total.value = res.total || 0
      scope.value = res.scope || 'self'
    } else {
      records.value = []
      total.value = 0
    }
  } catch (e) {
    records.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function resetFilter() {
  filter.year = now.getFullYear()
  filter.month = 0
  filter.status = 'all'
  filter.keyword = ''
  filter.page = 1
  loadData()
}

function goPage(p) {
  if (p < 1 || p > totalPages.value) return
  filter.page = p
  loadData()
}

onMounted(() => loadData())
</script>

<style scoped>
.kqyc-page {
  min-height: 100vh;
  background: var(--color-bg-layout, #f5f7fa);
  padding-bottom: 32px;
}
.page-header-bar { padding: 18px 0; background: #fff; border-bottom: 1px solid #ebeef5; }
.header-content { padding: 0 24px; display: flex; justify-content: space-between; align-items: center; }
.page-title { margin: 0; font-size: 22px; font-weight: 600; color: #303133; }
.page-subtitle { margin: 6px 0 0; color: #909399; font-size: 13px; }
.container { padding: 18px 24px 0; }
.card { background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
.filter-bar {
  display: flex;
  gap: 14px;
  padding: 14px 18px;
  align-items: flex-end;
  flex-wrap: wrap;
}
.filter-group { display: flex; flex-direction: column; gap: 4px; min-width: 120px; }
.filter-group.flex-grow { flex: 1 1 220px; }
.filter-group label { font-size: 12px; color: #909399; }
.form-input {
  padding: 6px 10px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
  background: #fff;
}
.filter-actions { display: flex; gap: 8px; }
.btn { padding: 6px 16px; border-radius: 4px; cursor: pointer; font-size: 14px; border: 1px solid; }
.btn-primary { background: #409eff; color: #fff; border-color: #409eff; }
.btn-primary:hover:not(:disabled) { background: #3a8ee6; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-outline { background: #fff; color: #606266; border-color: #dcdfe6; }
.btn-outline:hover { background: #f5f7fa; color: #409eff; border-color: #409eff; }

.table-card { margin-top: 16px; }
.table-header {
  padding: 14px 18px;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.table-title { margin: 0; font-size: 16px; font-weight: 600; color: #303133; }
.count-info { color: #909399; font-size: 13px; }

.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th, .data-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #ebeef5;
  vertical-align: top;
}
.data-table th { background: #fafafa; color: #606266; font-weight: 500; }
.data-table tbody tr:hover { background: #f5f7fa; }

.desc-cell { max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.link-file { color: #409eff; text-decoration: none; }
.link-file:hover { text-decoration: underline; }

.appr-cell { display: flex; flex-direction: column; gap: 2px; }
.appr-name { color: #303133; }
.appr-status {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 11px;
  width: fit-content;
}

.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}
.status-processing { background: #fff7e6; color: #d46b08; }
.status-approved { background: #e6ffed; color: #389e0d; }
.status-rejected { background: #ffece8; color: #cf1322; }

.reject-reason { margin-top: 4px; color: #cf1322; font-size: 11px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.processed-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background: #e6f7ff;
  color: #096dd9;
  font-size: 12px;
}
.dakaman-confirmed-tag {
  margin-top: 4px;
  color: #389e0d;
  font-size: 11px;
}

.text-center { text-align: center; }
.text-tertiary { color: #909399; }

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 14px;
  border-top: 1px solid #ebeef5;
}
.pagination button {
  padding: 4px 14px;
  border: 1px solid #dcdfe6;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
}
.pagination button:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
