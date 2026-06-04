<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">工作号录入</h1>
          <p class="header-subtitle">为本专业维护工作号及项目名称，供技术文件与技术管理编号使用</p>
        </div>
        <div class="header-actions">
          <button class="btn" @click="goBack">返回文件编号</button>
        </div>
      </div>
    </div>

    <div class="container">
      <div class="card">
        <div class="card-header">
          <h3>新增工作号</h3>
        </div>
        <div class="card-body">
          <form class="form-grid" @submit.prevent="handleSubmit">
            <div class="form-group">
              <label>添加人</label>
              <input v-model="form.tjr" type="text" class="readonly" readonly>
            </div>
            <div class="form-group">
              <label>所属科室</label>
              <input v-model="form.ssks" type="text" class="readonly" readonly>
            </div>
            <div class="form-group">
              <label>截止年份（基准年）</label>
              <input v-model.number="form.jznf" type="number" min="2000" :max="maxYear" required>
            </div>
            <div class="form-group">
              <label>工作号</label>
              <input v-model="form.gzh" type="text" placeholder="例如：001289" required>
            </div>
            <div class="form-group">
              <label>工作号名称</label>
              <input v-model="form.gzhname" type="text" placeholder="例如：云浮水源山抽水蓄能" required>
            </div>
            <div class="form-actions">
              <button type="button" @click="resetForm">重置</button>
              <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? '保存中…' : '保存工作号' }}</button>
            </div>
          </form>
        </div>
      </div>

      <div class="card record-card mt-xl">
        <div class="card-header record-card__header">
          <div>
            <h3>本专业工作号列表</h3>
            <p class="record-card__desc">{{ listFilterLabel }}</p>
          </div>
          <div class="record-card__filters">
            <label class="filter-label">范围</label>
            <select v-model="listDataRange" class="filter-select filter-select--scope" @change="onListRangeChange">
              <option value="self">本人</option>
              <option value="major">本专业</option>
              <template v-if="canViewAllDepts">
                <option value="all">全部科室</option>
                <option v-for="d in deptLsysOptions" :key="'lsys-' + d" :value="'lsys:' + d">{{ d }}</option>
              </template>
            </select>
            <label class="filter-label">截止年份</label>
            <select v-model="listYearFilter" class="filter-select">
              <option value="">全部</option>
              <option v-for="y in listYearOptions" :key="y" :value="String(y)">{{ y }}年</option>
            </select>
            <input
              v-model.trim="listKeyword"
              type="search"
              class="filter-input filter-input--search"
              placeholder="工作号/名称/添加人"
              aria-label="关键词筛选"
            >
            <select v-model="listSort" class="filter-select" aria-label="排序">
              <option value="year0_desc">截止年份 ↓</option>
              <option value="year0_asc">截止年份 ↑</option>
              <option value="gzh_asc">工作号 A→Z</option>
              <option value="gzh_desc">工作号 Z→A</option>
              <option value="gzhname_asc">名称 A→Z</option>
              <option value="gzhname_desc">名称 Z→A</option>
            </select>
            <button type="button" class="btn btn-sm" @click="resetListFilters">重置</button>
          </div>
        </div>
        <div class="card-body record-card__body">
          <div v-if="loading" class="empty-text">加载中…</div>
          <div v-else-if="filteredList.length" class="table-wrap">
            <table class="data-table record-table">
              <thead>
                <tr>
                  <th>工作号</th>
                  <th>工作号名称</th>
                  <th>截止年份</th>
                  <th>所属科室</th>
                  <th>添加人</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in displayList" :key="row.id">
                  <td>{{ row.gzh }}</td>
                  <td>{{ row.gzhname }}</td>
                  <td>{{ row.year0 }}</td>
                  <td>{{ row.ssks }}</td>
                  <td>{{ row.tjr }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="!loading && filteredList.length" class="record-pagination">
            <span class="record-pagination__total">共 {{ filteredList.length }} 条</span>
            <span class="record-pagination__size">
              每页
              <select v-model.number="listPageSize" class="record-pagination__select">
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
                :disabled="listPage <= 1"
                @click="listPage = Math.max(1, listPage - 1)"
              >
                上一页
              </button>
              <span class="record-pagination__num">第 {{ listPage }} / {{ listTotalPages }} 页</span>
              <button
                type="button"
                class="record-pagination__btn"
                :disabled="listPage >= listTotalPages"
                @click="listPage = Math.min(listTotalPages, listPage + 1)"
              >
                下一页
              </button>
            </div>
          </div>
          <p v-else-if="!loading" class="empty-text">
            {{ list.length ? '当前筛选条件下暂无记录' : '当前范围暂无工作号记录' }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getGzhList, addGzh } from '@/api/fileNumbering'
import { getStatisticsPermission, getDeptLsysList } from '@/api/attendance'
import { keywordMatches, sortRecordRows } from '@/utils/recordTableHelpers'

const router = useRouter()

const currentYear = new Date().getFullYear()
const maxYear = computed(() => currentYear + 10)

const form = ref({
  tjr: '',
  ssks: '',
  jznf: currentYear,
  gzh: '',
  gzhname: '',
})

const list = ref([])
const loading = ref(false)
const saving = ref(false)
const permissionLevel = ref(1)
const userLsys = ref('')

const listDataRange = ref('major')
const listYearFilter = ref('')
const listKeyword = ref('')
const listSort = ref('year0_desc')
const listPage = ref(1)
const listPageSize = ref(20)
const deptLsysOptions = ref([])

const canViewAllDepts = computed(() => permissionLevel.value === 3)

const listYearOptions = computed(() => {
  const years = new Set()
  for (const row of list.value) {
    const y = Number(row?.year0)
    if (Number.isFinite(y)) years.add(y)
  }
  years.add(currentYear)
  return [...years].sort((a, b) => b - a)
})

const GZH_SORT_FIELDS = [
  { field: 'year0', type: 'number', get: (r) => r.year0 },
  { field: 'gzh', type: 'string', get: (r) => r.gzh },
  { field: 'gzhname', type: 'string', get: (r) => r.gzhname },
]

const filteredList = computed(() => {
  let rows = list.value
  if (listDataRange.value === 'self') {
    const name = (form.value.tjr || '').trim()
    rows = rows.filter((r) => (r.tjr || '').trim() === name)
  }
  if (listYearFilter.value) {
    const y = Number(listYearFilter.value)
    rows = rows.filter((r) => Number(r.year0) === y)
  }
  const kw = listKeyword.value
  if (kw) {
    rows = rows.filter((r) =>
      keywordMatches(kw, [r.gzh, r.gzhname, r.tjr, r.ssks, r.year0]),
    )
  }
  return sortRecordRows(rows, listSort.value, GZH_SORT_FIELDS)
})

const listTotalPages = computed(() =>
  Math.max(1, Math.ceil(filteredList.value.length / listPageSize.value)),
)

const displayList = computed(() => {
  const start = (listPage.value - 1) * listPageSize.value
  return filteredList.value.slice(start, start + listPageSize.value)
})

const listFilterLabel = computed(() => {
  const dr = listDataRange.value
  let who = '本人'
  if (dr === 'major') {
    who = userLsys.value ? `本专业（${userLsys.value}）` : '本专业'
  } else if (dr === 'all') {
    who = '全部科室'
  } else if (dr.startsWith('lsys:')) {
    who = dr.slice(5) || '科室'
  }
  const yearPart = listYearFilter.value ? `${listYearFilter.value}年` : '全部年份'
  const kw = listKeyword.value.trim()
  return `${yearPart}，${who}${kw ? `，关键词「${kw}」` : ''}`
})

watch([listKeyword, listSort, listYearFilter, listDataRange], () => {
  listPage.value = 1
})
watch(listPageSize, () => {
  listPage.value = 1
})
watch(filteredList, () => {
  if (listPage.value > listTotalPages.value) listPage.value = listTotalPages.value
})

function getCurrentUser() {
  try {
    const raw = localStorage.getItem('userInfo')
    if (!raw) return null
    const u = JSON.parse(raw)
    return { name: (u.name || u.userName || '').trim() }
  } catch {
    return null
  }
}

function normalizeLsysList(raw) {
  if (!Array.isArray(raw)) return []
  return raw.map((x) => (typeof x === 'string' ? x : x?.lsys || x?.name || '').trim()).filter(Boolean)
}

async function loadDeptOptions() {
  if (!canViewAllDepts.value) {
    deptLsysOptions.value = []
    return
  }
  try {
    const res = await getDeptLsysList()
    deptLsysOptions.value = normalizeLsysList(res?.list || res?.data)
  } catch {
    deptLsysOptions.value = []
  }
}

async function loadUserDept() {
  const user = getCurrentUser()
  if (!user?.name) return
  form.value.tjr = user.name
  try {
    const res = await getStatisticsPermission({ name: user.name })
    if (res && res.success !== false) {
      form.value.ssks = (res.lsys || '').trim()
      userLsys.value = form.value.ssks
      permissionLevel.value = res.level ?? 1
    }
  } catch {
    // ignore
  }
}

function resolveFetchDepartments() {
  const dr = listDataRange.value
  if (dr === 'all' && canViewAllDepts.value) {
    const depts = deptLsysOptions.value.length
      ? [...deptLsysOptions.value]
      : form.value.ssks
        ? [form.value.ssks]
        : []
    return [...new Set(depts)]
  }
  if (dr.startsWith('lsys:')) {
    const d = dr.slice(5).trim()
    return d ? [d] : []
  }
  return form.value.ssks ? [form.value.ssks] : []
}

async function loadList() {
  const departments = resolveFetchDepartments()
  if (!departments.length) {
    list.value = []
    return
  }
  loading.value = true
  try {
    const results = await Promise.all(
      departments.map((ssks) => getGzhList({ ssks }).catch(() => ({ list: [] }))),
    )
    const merged = []
    const seen = new Set()
    for (const res of results) {
      for (const row of res.list || []) {
        if (!row) continue
        const key = row.id != null ? `id:${row.id}` : `${row.ssks}|${row.gzh}|${row.gzhname}`
        if (seen.has(key)) continue
        seen.add(key)
        merged.push(row)
      }
    }
    list.value = merged
  } catch {
    list.value = []
  } finally {
    loading.value = false
  }
}

function onListRangeChange() {
  if (!canViewAllDepts.value && (listDataRange.value === 'all' || listDataRange.value.startsWith('lsys:'))) {
    listDataRange.value = 'major'
  }
  loadList()
}

function resetListFilters() {
  listDataRange.value = 'major'
  listYearFilter.value = ''
  listKeyword.value = ''
  listSort.value = 'year0_desc'
  listPage.value = 1
  loadList()
}

function resetForm() {
  form.value.gzh = ''
  form.value.gzhname = ''
  form.value.jznf = currentYear
}

async function handleSubmit() {
  if (!form.value.gzh.trim() || !form.value.gzhname.trim()) return
  if (!form.value.tjr || !form.value.ssks) {
    await loadUserDept()
    if (!form.value.tjr || !form.value.ssks) {
      alert('无法获取当前用户或科室信息，请重新登录后重试')
      return
    }
  }
  saving.value = true
  try {
    await addGzh({
      tjr: form.value.tjr,
      gzh: form.value.gzh.trim(),
      xmm: form.value.gzhname.trim(),
      jznf: form.value.jznf,
      ssks: form.value.ssks,
    })
    alert('保存成功')
    resetForm()
    await loadList()
  } catch (e) {
    alert(e?.response?.data?.detail || e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

function goBack() {
  router.push('/file/numbering')
}

onMounted(async () => {
  await loadUserDept()
  await loadDeptOptions()
  await loadList()
})
</script>

<style scoped>
.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--spacing-lg);
}

.card-header {
  padding: var(--spacing-md) var(--spacing-xl);
}

.card-body {
  padding: var(--spacing-lg) var(--spacing-xl);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.form-group label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.form-group input,
.form-group select {
  padding: 6px 10px;
  border-radius: var(--radius-base);
  border: 1px solid var(--color-border-lighter);
  font-size: var(--font-size-sm);
}

.readonly {
  background-color: var(--color-bg-layout);
}

.form-actions {
  grid-column: 1 / -1;
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-md);
}

.form-actions button {
  min-width: 80px;
  padding: 6px 16px;
  font-size: var(--font-size-sm);
  border-radius: var(--radius-base);
}

.record-card {
  background: white;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-lighter);
  overflow: hidden;
}

.record-card__header {
  padding: var(--spacing-lg) var(--spacing-xl);
  background: white;
  border-bottom: 1px solid var(--color-border-lighter);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: var(--spacing-md);
}

.record-card__header h3 {
  margin: 0 0 var(--spacing-xs);
}

.record-card__desc {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: normal;
}

.record-card__filters {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
  flex-shrink: 0;
}

.record-card__filters .filter-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.record-card__filters .filter-select--scope {
  min-width: 10rem;
  max-width: 20rem;
}

.record-card__filters .filter-select,
.record-card__filters .filter-input {
  padding: 6px 10px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
}

.record-card__filters .filter-input--search {
  min-width: 8rem;
  flex: 1;
  max-width: 14rem;
}

.record-card__body {
  padding: var(--spacing-lg) var(--spacing-xl);
}

.table-wrap {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}

.data-table th,
.data-table td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--color-border-lighter);
  text-align: left;
}

.data-table th {
  background: var(--color-bg-lighter, #f5f5f5);
  font-weight: 600;
}

.record-pagination {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px 16px;
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-border-lighter);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.record-pagination__select {
  padding: 4px 8px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  margin: 0 4px;
}

.record-pagination__pages {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.record-pagination__btn {
  padding: 4px 12px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  background: white;
  cursor: pointer;
  font-size: var(--font-size-sm);
}

.record-pagination__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty-text {
  padding: var(--spacing-xl);
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}
</style>
