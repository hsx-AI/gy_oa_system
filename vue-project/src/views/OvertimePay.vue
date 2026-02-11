<template>
  <div class="overtime-pay-page">
    <div class="page-header">
      <div class="header-content">
        <h1 class="header-title">加班费统计</h1>
        <p class="header-subtitle">按科室、年份、月份查询</p>
      </div>
    </div>

    <div class="container">
      <div v-if="!canView" class="no-permission card">
        <div class="no-permission-content">
          <p>您暂无权限查看加班费统计，仅部长/副部长或人事管理员可访问。</p>
          <router-link to="/" class="btn btn-primary">返回首页</router-link>
        </div>
      </div>

      <template v-else>
        <div class="filter-section card">
          <div class="filter-form">
            <div class="form-item">
              <label class="form-label">科室</label>
              <select v-model="selectedLsys" class="form-select" :disabled="!lsysList.length">
                <option value="">全员</option>
                <option v-for="d in lsysList" :key="d" :value="d">{{ d }}</option>
              </select>
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
              <button
                type="button"
                class="btn btn-outline"
                :disabled="!filterMonth || exportLoading"
                @click="downloadExcel"
              >
                <span v-if="exportLoading">生成中...</span>
                <span v-else>下载 Excel 工资报表</span>
              </button>
            </div>
          </div>
          <p v-if="canView" class="filter-hint">下载报表请先选择「月份」，将生成多 sheet：首 sheet 全员，其余为各科室。</p>
        </div>

        <div v-if="hasFetched" class="section card overtime-pay-section">
          <h2 class="section-title">
            <svg class="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="1" x2="12" y2="23"/>
              <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
            统计结果
          </h2>
          <p class="section-desc">{{ selectedLsys || '全员' }} {{ filterYear }}年{{ filterMonth ? filterMonth + '月' : '全年' }}（单价 {{ overtimePayZhibanfei }} 元/小时）</p>
          <div v-if="overtimePayByMonth.length > 0" class="table-wrap">
            <h3 class="subsection-title">按月份</h3>
            <table class="data-table">
              <thead>
                <tr>
                  <th>月份</th>
                  <th>加班小时</th>
                  <th>加班费（元）</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in overtimePayByMonth" :key="row.month">
                  <td>{{ row.monthLabel }}</td>
                  <td>{{ row.hours }}</td>
                  <td class="pay-cell">{{ row.pay }}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr>
                  <td>合计</td>
                  <td>{{ overtimePayByMonth.reduce((s, r) => s + (r.hours || 0), 0).toFixed(2) }}</td>
                  <td class="pay-cell">{{ overtimePayByMonth.reduce((s, r) => s + (r.pay || 0), 0).toFixed(2) }}</td>
                </tr>
              </tfoot>
            </table>
          </div>
          <div v-if="overtimePayByEmployee.length > 0" class="table-wrap">
            <h3 class="subsection-title">科室员工加班费明细</h3>
            <table class="data-table">
              <thead>
                <tr>
                  <th>姓名</th>
                  <th>加班小时</th>
                  <th>加班费（元）</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in overtimePayByEmployee" :key="row.name">
                  <td>{{ row.name }}</td>
                  <td>{{ row.hours }}</td>
                  <td class="pay-cell">{{ row.pay }}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr>
                  <td>合计</td>
                  <td>{{ overtimePayByEmployee.reduce((s, r) => s + (r.hours || 0), 0).toFixed(2) }}</td>
                  <td class="pay-cell">{{ overtimePayByEmployee.reduce((s, r) => s + (r.pay || 0), 0).toFixed(2) }}</td>
                </tr>
              </tfoot>
            </table>
          </div>
          <div v-if="hasFetched && !overtimePayByMonth.length && !overtimePayByEmployee.length" class="empty-state">暂无加班费数据</div>
        </div>

        <div v-if="!hasFetched && !loading" class="init-hint card">
          <p>选择科室、年份与月份后点击「查询」查看加班费统计。</p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as XLSX from 'xlsx'
import { getOvertimePayPermission, getDeptLsysList, getDeptOvertimePayByMonth, getDeptOvertimePayByEmployee, getOvertimePayExport } from '@/api/attendance'

const router = useRouter()
const canView = ref(false)
const lsysList = ref([])
const selectedLsys = ref('')
const filterYear = ref(new Date().getFullYear())
const filterMonth = ref('')
const loading = ref(false)
const exportLoading = ref(false)
const hasFetched = ref(false)
const overtimePayByMonth = ref([])
const overtimePayByEmployee = ref([])
const overtimePayZhibanfei = ref(15)

const yearOptions = computed(() => {
  const y = new Date().getFullYear()
  return [y, y - 1, y - 2, y - 3, y - 4, y - 5]
})

const fetchData = async () => {
  loading.value = true
  hasFetched.value = true
  const payParams = { year: filterYear.value }
  if (selectedLsys.value) payParams.lsys = selectedLsys.value
  if (filterMonth.value) payParams.month = Number(filterMonth.value)
  try {
    const [resMonth, resEmp] = await Promise.all([
      getDeptOvertimePayByMonth(payParams),
      getDeptOvertimePayByEmployee(payParams)
    ])
    overtimePayByMonth.value = (resMonth?.success && resMonth?.list) ? resMonth.list : []
    overtimePayByEmployee.value = (resEmp?.success && resEmp?.list) ? resEmp.list : []
    overtimePayZhibanfei.value = resMonth?.zhibanfei ?? resEmp?.zhibanfei ?? 15
  } catch (e) {
    overtimePayByMonth.value = []
    overtimePayByEmployee.value = []
  } finally {
    loading.value = false
  }
}

function sheetFromList(list) {
  const header = ['姓名', '本月加班费（元）']
  const rows = list.map((item) => [item.name || '', item.pay ?? 0])
  return XLSX.utils.aoa_to_sheet([header, ...rows])
}

async function downloadExcel() {
  if (!filterMonth.value) {
    alert('请先选择月份后再下载报表')
    return
  }
  exportLoading.value = true
  try {
    const res = await getOvertimePayExport({
      year: filterYear.value,
      month: Number(filterMonth.value)
    })
    if (!res?.success || res.all === undefined) {
      alert('获取报表数据失败')
      return
    }
    const wb = XLSX.utils.book_new()
    const allSheet = sheetFromList(res.all || [])
    XLSX.utils.book_append_sheet(wb, allSheet, '全员')
    const byDept = res.byDept || []
    for (const dept of byDept) {
      const sheetName = (dept.lsys || '科室').slice(0, 31)
      const sheet = sheetFromList(dept.list || [])
      XLSX.utils.book_append_sheet(wb, sheet, sheetName)
    }
    const fileName = `加班费工资报表_${filterYear.value}年${filterMonth.value}月.xlsx`
    XLSX.writeFile(wb, fileName)
  } catch (e) {
    console.error(e)
    alert('下载失败，请稍后重试')
  } finally {
    exportLoading.value = false
  }
}

onMounted(async () => {
  const user = JSON.parse(localStorage.getItem('userInfo') || '{}')
  const name = (user.name || user.userName || '').trim()
  if (!name) {
    router.replace('/login')
    return
  }
  try {
    const permRes = await getOvertimePayPermission({ name })
    canView.value = !!(permRes?.canView)
    if (!canView.value) return
    const listRes = await getDeptLsysList()
    lsysList.value = (listRes?.list || []).filter(Boolean)
    if (lsysList.value.length) selectedLsys.value = ''
  } catch (e) {
    canView.value = false
  }
})
</script>

<style scoped>
.overtime-pay-page {
  min-height: 100vh;
  background: var(--color-bg-layout);
}
.overtime-pay-page .container {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0 0 var(--spacing-xxl);
}
.card {
  background: var(--color-bg-container);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
  box-shadow: var(--shadow-card);
}
.no-permission-content {
  text-align: center;
  padding: var(--spacing-xxl);
}
.no-permission-content p {
  margin-bottom: var(--spacing-lg);
  color: var(--color-text-secondary);
}
.filter-form {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: var(--spacing-lg);
}
.form-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}
.form-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
.form-select {
  min-width: 120px;
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
}
.btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  cursor: pointer;
  border: none;
}
.btn-primary {
  background: var(--color-primary);
  color: white;
}
.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.btn-outline {
  background: transparent;
  border: 1px solid var(--color-primary);
  color: var(--color-primary);
}
.btn-outline:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.filter-hint {
  margin-top: var(--spacing-sm);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}
.loading-icon {
  width: 18px;
  height: 18px;
  vertical-align: middle;
  margin-right: var(--spacing-xs);
}
.section-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--spacing-md);
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}
.section-icon {
  width: 24px;
  height: 24px;
  color: var(--color-primary);
}
.section-desc {
  margin-bottom: var(--spacing-lg);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
.subsection-title {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  margin: var(--spacing-lg) 0 var(--spacing-sm);
}
.subsection-title:first-of-type {
  margin-top: 0;
}
.table-wrap {
  margin-bottom: var(--spacing-lg);
}
.data-table {
  width: 100%;
  border-collapse: collapse;
}
.data-table th,
.data-table td {
  padding: var(--spacing-md);
  text-align: left;
  border-bottom: 1px solid var(--color-border-lighter);
}
.data-table th {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  background: var(--color-bg-spotlight);
}
.data-table td {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}
.pay-cell {
  font-weight: var(--font-weight-medium);
  color: var(--color-primary);
}
.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-secondary);
}
.init-hint {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-secondary);
}
</style>
