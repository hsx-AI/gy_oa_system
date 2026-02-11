<template>
  <div class="db-manager-page">
    <div class="container">
      <header class="page-header">
        <div class="header-content">
          <div class="header-info">
            <h1 class="header-title">数据库表管理</h1>
            <p class="header-subtitle">选择表后进行增、删、改、查（仅系统管理员 webconfig.admin1）</p>
          </div>
        </div>
      </header>

      <div v-if="!canAccess" class="card no-permission">
        <p>您暂无权限访问此页面，仅系统管理员（webconfig.admin1 对应用户）可操作。</p>
        <router-link to="/" class="btn btn-primary">返回首页</router-link>
      </div>

      <template v-else>
        <div class="card filter-section">
          <div class="filter-row">
            <label class="form-label">选择表</label>
            <select v-model="selectedTable" class="form-select" @change="onTableChange">
              <option value="">-- 请选择表 --</option>
              <option v-for="t in tableList" :key="t" :value="t">{{ t }}</option>
            </select>
            <button type="button" class="btn btn-primary" :disabled="!selectedTable || loading" @click="loadRows">
              {{ loading ? '加载中…' : '刷新数据' }}
            </button>
            <button v-if="selectedTable && columns.length" type="button" class="btn btn-secondary" @click="openAddModal">
              新增一行
            </button>
          </div>
          <div v-if="selectedTable && columns.length" class="filter-row search-row">
            <label class="form-label">搜索</label>
            <select v-model="searchColumn" class="form-select search-col">
              <option value="">选择列</option>
              <option v-for="col in columns" :key="col.name" :value="col.name">{{ col.name }}</option>
            </select>
            <input
              v-model="searchKeyword"
              type="text"
              class="form-input search-input"
              placeholder="输入关键词，模糊匹配"
              @keyup.enter="doSearch"
            />
            <button type="button" class="btn btn-primary" :disabled="rowsLoading" @click="doSearch">
              搜索
            </button>
            <button v-if="hasSearch" type="button" class="btn btn-outline" @click="clearSearch">
              清除
            </button>
            <span v-if="hasSearch" class="search-hint">按「{{ searchColumn }}」包含「{{ searchKeyword }}」筛选</span>
          </div>
        </div>

        <div v-if="selectedTable && columns.length" class="card table-section">
          <div class="table-header">
            <h2 class="table-title">{{ selectedTable }}</h2>
            <span class="table-meta">共 {{ total }} 条，第 {{ page }} 页</span>
          </div>
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th v-for="col in columns" :key="col.name">{{ col.name }}{{ col.isPk ? ' (主键)' : '' }}</th>
                  <th style="width: 120px;">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="rowsLoading">
                  <td :colspan="columns.length + 1" class="text-center">加载中…</td>
                </tr>
                <tr v-else-if="rows.length === 0">
                  <td :colspan="columns.length + 1" class="text-center text-tertiary">暂无数据</td>
                </tr>
                <tr v-for="(row, rIdx) in rows" :key="rIdx">
                  <td v-for="col in columns" :key="col.name">{{ formatCell(row[col.name]) }}</td>
                  <td>
                    <button type="button" class="link-btn" @click="openEditModal(row)">编辑</button>
                    <button type="button" class="link-btn danger" @click="confirmDelete(row)">删除</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="total > pageSize" class="pagination">
            <button type="button" class="btn btn-outline" :disabled="page <= 1" @click="page = 1; loadRows()">首页</button>
            <button type="button" class="btn btn-outline" :disabled="page <= 1" @click="page--; loadRows()">上一页</button>
            <span class="page-info">{{ page }} / {{ totalPages }}</span>
            <button type="button" class="btn btn-outline" :disabled="page >= totalPages" @click="page++; loadRows()">下一页</button>
            <button type="button" class="btn btn-outline" :disabled="page >= totalPages" @click="page = totalPages; loadRows()">末页</button>
          </div>
        </div>
      </template>

      <!-- 新增/编辑 弹窗 -->
      <div v-if="showRowModal" class="modal-overlay" @click.self="showRowModal = false">
        <div class="modal-card">
          <h3 class="modal-title">{{ isEdit ? '编辑行' : '新增一行' }}</h3>
          <form @submit.prevent="submitRow" class="modal-form">
            <div v-for="col in columns" :key="col.name" class="form-item">
              <label class="form-label">{{ col.name }}{{ col.isPk ? ' (主键)' : '' }}{{ col.nullable ? '' : ' *' }}</label>
              <input
                v-model="formRow[col.name]"
                type="text"
                class="form-input"
                :placeholder="col.nullable ? '可空' : '必填'"
              />
            </div>
            <div class="modal-actions">
              <button type="button" class="btn btn-outline" @click="showRowModal = false">取消</button>
              <button type="submit" class="btn btn-primary" :disabled="saving">{{ saving ? '提交中…' : '确定' }}</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  getDbManagerPermission,
  getDbManagerTables,
  getDbManagerColumns,
  getDbManagerRows,
  insertDbManagerRow,
  updateDbManagerRow,
  deleteDbManagerRow
} from '@/api/dbManager'

const router = useRouter()
const canAccess = ref(false)
const tableList = ref([])
const selectedTable = ref('')
const columns = ref([])
const primaryKey = ref([])
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const searchColumn = ref('')
const searchKeyword = ref('')
const loading = ref(false)
const rowsLoading = ref(false)

const hasSearch = computed(() => (searchColumn.value || '').trim() && (searchKeyword.value || '').trim())
const saving = ref(false)
const showRowModal = ref(false)
const isEdit = ref(false)
const formRow = ref({})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

function getCurrentUser() {
  try {
    const raw = localStorage.getItem('userInfo')
    if (!raw) return ''
    const u = JSON.parse(raw)
    return (u.name || u.userName || '').trim()
  } catch {
    return ''
  }
}

function formatCell(val) {
  if (val == null) return ''
  if (typeof val === 'object' && typeof val.toISOString === 'function') return val.toISOString()
  return String(val)
}

function onTableChange() {
  columns.value = []
  primaryKey.value = []
  rows.value = []
  total.value = 0
  page.value = 1
  searchColumn.value = ''
  searchKeyword.value = ''
  if (!selectedTable.value) return
  loadColumns()
  loadRows()
}

function loadColumns() {
  const name = getCurrentUser()
  if (!name || !selectedTable.value) return
  getDbManagerColumns(selectedTable.value, { current_user: name })
    .then(res => {
      if (res && res.success && Array.isArray(res.list)) {
        columns.value = res.list
        primaryKey.value = res.primaryKey || []
      }
    })
    .catch(() => { columns.value = [] })
}

function loadRows() {
  const name = getCurrentUser()
  if (!name || !selectedTable.value) return
  rowsLoading.value = true
  const params = {
    current_user: name,
    page: page.value,
    page_size: pageSize.value
  }
  if (hasSearch.value) {
    params.search_column = searchColumn.value
    params.search_keyword = searchKeyword.value
  }
  getDbManagerRows(selectedTable.value, params)
    .then(res => {
      if (res && res.success) {
        rows.value = res.list || []
        total.value = res.total ?? 0
      }
    })
    .finally(() => { rowsLoading.value = false })
}

function doSearch() {
  if (!(searchColumn.value || '').trim()) {
    alert('请先选择要搜索的列')
    return
  }
  page.value = 1
  loadRows()
}

function clearSearch() {
  searchColumn.value = ''
  searchKeyword.value = ''
  page.value = 1
  loadRows()
}

function openAddModal() {
  isEdit.value = false
  formRow.value = {}
  columns.value.forEach(c => { formRow.value[c.name] = '' })
  showRowModal.value = true
}

function openEditModal(row) {
  isEdit.value = true
  formRow.value = { ...row }
  showRowModal.value = true
}

function submitRow() {
  const name = getCurrentUser()
  if (!name || !selectedTable.value) return
  saving.value = true
  const payload = { current_user: name, row: {} }
  columns.value.forEach(c => {
    const v = formRow.value[c.name]
    payload.row[c.name] = v === '' || v == null ? null : v
  })
  const api = isEdit.value ? updateDbManagerRow : insertDbManagerRow
  api(selectedTable.value, payload)
    .then(res => {
      if (res && res.success) {
        alert(isEdit.value ? '更新成功' : '插入成功')
        showRowModal.value = false
        loadRows()
      } else {
        alert(res?.detail || res?.message || '操作失败')
      }
    })
    .catch(e => {
      alert(e?.response?.data?.detail || e?.message || '操作失败')
    })
    .finally(() => { saving.value = false })
}

function confirmDelete(row) {
  if (!primaryKey.value.length) {
    alert('该表无主键，无法在此删除')
    return
  }
  const pkOnly = {}
  primaryKey.value.forEach(k => { pkOnly[k] = row[k] })
  if (!confirm('确定删除该行吗？此操作不可恢复。')) return
  const name = getCurrentUser()
  deleteDbManagerRow(selectedTable.value, { current_user: name, row: pkOnly })
    .then(res => {
      if (res && res.success) {
        alert('删除成功')
        loadRows()
      } else {
        alert(res?.detail || res?.message || '删除失败')
      }
    })
    .catch(e => {
      alert(e?.response?.data?.detail || e?.message || '删除失败')
    })
}

onMounted(async () => {
  const name = getCurrentUser()
  if (!name) {
    router.replace('/login')
    return
  }
  try {
    const res = await getDbManagerPermission({ current_user: name })
    canAccess.value = !!(res && res.canAccess)
    if (!canAccess.value) return
    const listRes = await getDbManagerTables({ current_user: name })
    tableList.value = (listRes?.list || []).filter(Boolean)
  } catch {
    canAccess.value = false
  }
})
</script>

<style scoped>
.db-manager-page { min-height: 100vh; background: var(--color-bg-layout); padding-bottom: var(--spacing-xxl); }
.no-permission { padding: var(--spacing-xl); text-align: center; }
.no-permission p { margin-bottom: var(--spacing-base); }
.filter-section { margin-bottom: var(--spacing-lg); padding: var(--spacing-xl); }
.filter-row { display: flex; align-items: center; gap: var(--spacing-base); flex-wrap: wrap; }
.filter-row.search-row { margin-top: var(--spacing-base); padding-top: var(--spacing-base); border-top: 1px solid var(--color-border-lighter); }
.form-label { margin-right: var(--spacing-sm); white-space: nowrap; }
.form-select { min-width: 200px; padding: var(--spacing-sm) var(--spacing-base); }
.form-select.search-col { min-width: 160px; }
.form-input.search-input { min-width: 200px; padding: var(--spacing-sm) var(--spacing-base); border: 1px solid var(--color-border-lighter); border-radius: var(--radius-base); }
.search-hint { font-size: var(--font-size-sm); color: var(--color-text-tertiary); margin-left: var(--spacing-sm); }
.table-section { margin-top: var(--spacing-lg); padding: 0 0 var(--spacing-base); }
.table-header { padding: var(--spacing-xl); border-bottom: 1px solid var(--color-border-lighter); display: flex; justify-content: space-between; align-items: center; }
.table-title { margin: 0; font-size: var(--font-size-lg); }
.table-meta { color: var(--color-text-secondary); font-size: var(--font-size-sm); }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }
.data-table th, .data-table td { padding: var(--spacing-sm) var(--spacing-base); border-bottom: 1px solid var(--color-border-lighter); text-align: left; }
.data-table th { background: var(--color-bg-spotlight); }
.text-center { text-align: center; }
.text-tertiary { color: var(--color-text-tertiary); }
.link-btn { background: none; border: none; color: var(--color-primary); cursor: pointer; margin-right: 8px; font-size: var(--font-size-sm); }
.link-btn.danger { color: var(--color-danger, #e53935); }
.pagination { padding: var(--spacing-base); display: flex; align-items: center; gap: var(--spacing-sm); flex-wrap: wrap; }
.page-info { margin: 0 var(--spacing-sm); }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-card { background: var(--color-bg-container); border-radius: var(--radius-base); padding: var(--spacing-xl); max-width: 500px; width: 90%; max-height: 90vh; overflow-y: auto; }
.modal-title { margin: 0 0 var(--spacing-lg); font-size: var(--font-size-lg); }
.modal-form .form-item { margin-bottom: var(--spacing-base); }
.modal-form .form-input { width: 100%; padding: var(--spacing-sm) var(--spacing-base); border: 1px solid var(--color-border-lighter); border-radius: var(--radius-base); }
.modal-actions { margin-top: var(--spacing-xl); display: flex; justify-content: flex-end; gap: var(--spacing-base); }
</style>
