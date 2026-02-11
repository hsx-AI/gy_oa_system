<template>
  <div class="admin-employee-page">
    <div class="container">
      <!-- 页面头部：标题 + 操作按钮 -->
      <header class="page-header">
        <div class="header-content">
          <div class="header-info">
            <h1 class="header-title">员工在职管理</h1>
            <p class="header-subtitle">设置员工在职/离职状态，离职人员将不参与统计且无法登录系统</p>
          </div>
          <div class="header-actions">
            <button type="button" class="btn btn-secondary" @click="openAddModal">
              添丁
            </button>
            <button
              type="button"
              class="btn btn-primary"
              @click="handleExport"
              :disabled="exporting"
            >
              <span v-if="exporting" class="loading-spinner"></span>
              <span v-else>{{ isDeptOnly ? '导出本室在职员工' : '导出在职员工表' }}</span>
            </button>
          </div>
        </div>
      </header>

      <!-- 筛选区 -->
      <section class="query-section card">
        <div class="query-form">
          <div class="form-item">
            <label class="form-label">在职状态</label>
            <select v-model="filters.zaizhi" class="form-select">
              <option value="0">在职</option>
              <option value="1">离职</option>
              <option value="all">全部</option>
            </select>
          </div>
          <div class="form-item">
            <label class="form-label">科室</label>
            <select
              v-model="filters.lsys"
              class="form-select"
              :disabled="isDeptOnly"
            >
              <option value="">全部科室</option>
              <option v-for="d in deptList" :key="d" :value="d">{{ d }}</option>
            </select>
          </div>
          <div class="form-item">
            <label class="form-label">姓名</label>
            <input
              v-model="filters.q"
              type="text"
              class="form-input"
              placeholder="输入姓名模糊搜索"
            />
          </div>
          <div class="form-item form-actions">
            <button class="btn btn-primary" @click="loadList" :disabled="loading">
              <span v-if="loading" class="loading-spinner"></span>
              <span>{{ loading ? '查询中...' : '查询' }}</span>
            </button>
          </div>
        </div>
      </section>

      <!-- 表格区 -->
      <section class="table-section card">
        <div class="table-header">
          <h2 class="table-title">员工列表</h2>
          <span class="table-meta">共 {{ total }} 人</span>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>姓名</th>
                <th>工号</th>
                <th>科室</th>
                <th>级别</th>
                <th>在职状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in list" :key="row.name">
                <td>{{ row.name }}</td>
                <td>{{ row.gh }}</td>
                <td>
                  <template v-if="isDeptOnly">{{ row.lsys }}</template>
                  <select
                    v-else
                    v-model="row.lsys"
                    class="form-select inline-select"
                    :disabled="updateDeptLevelLoading === row.name"
                    @change="onDeptLevelChange(row, 'lsys')"
                  >
                    <option v-for="d in deptList" :key="d" :value="d">{{ d }}</option>
                    <option v-if="row.lsys && !deptList.includes(row.lsys)" :value="row.lsys">{{ row.lsys }}</option>
                  </select>
                </td>
                <td>
                  <template v-if="isDeptOnly">{{ row.jb }}</template>
                  <select
                    v-else
                    v-model="row.jb"
                    class="form-select inline-select"
                    :disabled="updateDeptLevelLoading === row.name"
                    @change="onDeptLevelChange(row, 'jb')"
                  >
                    <option value="">请选择</option>
                    <option v-for="jb in jbOptions" :key="jb" :value="jb">{{ jb }}</option>
                    <option v-if="row.jb && !jbOptions.includes(row.jb)" :value="row.jb">{{ row.jb }}</option>
                  </select>
                </td>
                <td>
                  <span :class="['status-tag', row.zaizhi === 1 ? 'status-left' : 'status-active']">
                    {{ row.zaizhiText }}
                  </span>
                </td>
                <td>
                  <button
                    v-if="row.zaizhi === 0"
                    type="button"
                    class="btn btn-sm btn-danger-outline"
                    @click="setStatus(row.name, 1)"
                    :disabled="actionLoading === row.name"
                  >
                    {{ actionLoading === row.name ? '处理中...' : '设为离职' }}
                  </button>
                  <button
                    v-else
                    type="button"
                    class="btn btn-sm btn-primary-outline"
                    @click="setStatus(row.name, 0)"
                    :disabled="actionLoading === row.name"
                  >
                    {{ actionLoading === row.name ? '处理中...' : '设为在职' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!list.length && !loading" class="empty-tip">暂无数据，请调整筛选条件后查询</div>
        <div v-if="total > pageSize" class="pagination-wrap">
          <button
            class="btn btn-sm"
            :disabled="page <= 1"
            @click="page = Math.max(1, page - 1); loadList()"
          >
            上一页
          </button>
          <span class="page-info">第 {{ page }} 页 / 共 {{ Math.ceil(total / pageSize) }} 页</span>
          <button
            class="btn btn-sm"
            :disabled="page * pageSize >= total"
            @click="page++; loadList()"
          >
            下一页
          </button>
        </div>
      </section>
    </div>

    <!-- 添丁弹窗（与 container 平级，避免被裁剪） -->
    <Teleport to="body">
      <div v-if="showAddModal" class="modal-overlay" @click.self="closeAddModal">
        <div class="modal-card">
          <div class="modal-header">
            <h3 class="modal-title">添丁（新增员工）</h3>
            <button type="button" class="modal-close" @click="closeAddModal" aria-label="关闭">&times;</button>
          </div>
          <form class="modal-body" @submit.prevent="submitAdd">
            <div class="form-row">
              <div class="form-item">
                <label class="form-label">姓名 <span class="required">*</span></label>
                <input v-model="addForm.name" type="text" class="form-input" placeholder="登录用户名" required />
              </div>
              <div class="form-item">
                <label class="form-label">工号</label>
                <input v-model="addForm.gh" type="text" class="form-input" placeholder="选填" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-item">
                <label class="form-label">科室 <span class="required">*</span></label>
                <input
                  v-if="isDeptOnly"
                  :value="addForm.lsys"
                  type="text"
                  class="form-input"
                  readonly
                />
                <select v-else v-model="addForm.lsys" class="form-select" required>
                  <option value="">请选择科室</option>
                  <option v-for="d in deptList" :key="d" :value="d">{{ d }}</option>
                </select>
              </div>
              <div class="form-item">
                <label class="form-label">级别</label>
                <select v-model="addForm.jb" class="form-select">
                  <option value="">请选择</option>
                  <option value="员工">员工</option>
                  <option value="组长">组长</option>
                  <option value="主任">主任</option>
                  <option value="副主任">副主任</option>
                  <option value="副部长">副部长</option>
                  <option value="部长">部长</option>
                </select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-item">
                <label class="form-label">性别</label>
                <select v-model="addForm.xbie" class="form-select">
                  <option value="">请选择</option>
                  <option value="男">男</option>
                  <option value="女">女</option>
                </select>
              </div>
              <div class="form-item">
                <label class="form-label">初始密码 <span class="required">*</span></label>
                <input
                  v-model="addForm.password"
                  type="password"
                  class="form-input"
                  placeholder="至少4位，用于登录"
                  minlength="4"
                  required
                />
              </div>
            </div>
            <p class="modal-hint">新员工将写入 YGGL 主表，可凭姓名与初始密码登录系统。</p>
          </form>
          <div class="modal-footer">
            <button type="button" class="btn btn-default" @click="closeAddModal">取消</button>
            <button type="button" class="btn btn-primary" @click="submitAdd" :disabled="addSubmitting">
              <span v-if="addSubmitting" class="loading-spinner"></span>
              <span>{{ addSubmitting ? '提交中...' : '确定添加' }}</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getAdminEmployees, setEmployeeStatus, getAdminDeptList, exportEmployeesExcel, addEmployee, updateEmployeeDeptLevel } from '@/api/attendance'

const currentUserName = ref('')
const deptList = ref([])
const list = ref([])
const total = ref(0)
const loading = ref(false)
const actionLoading = ref('')
const exporting = ref(false)
const isDeptOnly = ref(false)
const showAddModal = ref(false)
const addSubmitting = ref(false)
const addForm = reactive({
  name: '',
  gh: '',
  lsys: '',
  jb: '',
  xbie: '',
  password: ''
})

const filters = reactive({
  zaizhi: '0',
  lsys: '',
  q: ''
})
const page = ref(1)
const pageSize = 50

/** 级别下拉选项（与添丁弹窗一致） */
const jbOptions = ['员工', '组长', '主任', '副部长', '部长']
const updateDeptLevelLoading = ref('') // 正在保存的员工 name

function getCurrentUser() {
  try {
    const raw = localStorage.getItem('userInfo')
    if (raw) {
      const u = JSON.parse(raw)
      return (u.name || u.username || '').trim()
    }
  } catch (e) {}
  return ''
}

async function loadDeptList() {
  const name = getCurrentUser()
  if (!name) return
  try {
    const res = await getAdminDeptList({ current_user: name })
    if (res?.success && Array.isArray(res.list)) {
      deptList.value = res.list
      if (res.scope?.role === 'dept' && res.list.length === 1) {
        isDeptOnly.value = true
        filters.lsys = res.list[0]
      } else {
        isDeptOnly.value = false
      }
    }
  } catch (e) {
    console.error('科室列表加载失败', e)
  }
}

async function loadList() {
  const name = getCurrentUser()
  if (!name) {
    list.value = []
    total.value = 0
    return
  }
  loading.value = true
  try {
    const res = await getAdminEmployees({
      current_user: name,
      zaizhi: filters.zaizhi,
      lsys: filters.lsys || undefined,
      q: filters.q?.trim() || undefined,
      page: page.value,
      page_size: pageSize
    })
    if (res?.success) {
      list.value = res.list || []
      total.value = res.total ?? 0
    } else {
      list.value = []
      total.value = 0
    }
  } catch (e) {
    list.value = []
    total.value = 0
    if (e?.response?.status === 403) {
      alert('仅部长/副部长/科室主任可访问员工在职管理')
    } else {
      console.error('员工列表加载失败', e)
    }
  } finally {
    loading.value = false
  }
}

async function setStatus(empName, zaizhi) {
  const name = getCurrentUser()
  if (!name) return
  const action = zaizhi === 1 ? '设为离职' : '设为在职'
  if (!confirm(`确定将「${empName}」${action}？`)) return
  actionLoading.value = empName
  try {
    const res = await setEmployeeStatus({
      current_user: name,
      name: empName,
      zaizhi
    })
    if (res?.success) {
      await loadList()
    } else {
      alert(res?.message || '操作失败')
    }
  } catch (e) {
    alert(e?.message || '操作失败')
  } finally {
    actionLoading.value = ''
  }
}

async function onDeptLevelChange(row, field) {
  const name = getCurrentUser()
  if (!name) return
  updateDeptLevelLoading.value = row.name
  try {
    const res = await updateEmployeeDeptLevel({
      current_user: name,
      name: row.name,
      lsys: row.lsys,
      jb: row.jb || ''
    })
    if (res?.success) {
      row.lsys = res.lsys ?? row.lsys
      row.jb = res.jb ?? row.jb
    } else {
      alert(res?.message || '保存失败')
      await loadList()
    }
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '保存失败'
    alert(msg)
    await loadList()
  } finally {
    updateDeptLevelLoading.value = ''
  }
}

function formatExportFilename() {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  const h = String(now.getHours()).padStart(2, '0')
  const min = String(now.getMinutes()).padStart(2, '0')
  const s = String(now.getSeconds()).padStart(2, '0')
  return `在职员工按科室_${y}${m}${d}_${h}${min}${s}.xlsx`
}

async function handleExport() {
  const name = getCurrentUser()
  if (!name) {
    alert('请先登录')
    return
  }
  exporting.value = true
  try {
    const blob = await exportEmployeesExcel({ current_user: name })
    const isExcel = blob.type && blob.type.includes('spreadsheet')
    if (isExcel) {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = formatExportFilename()
      a.click()
      URL.revokeObjectURL(url)
    } else {
      const text = await blob.text()
      try {
        const j = JSON.parse(text)
        alert(j.detail || j.message || '导出失败')
      } catch {
        alert('导出失败')
      }
    }
  } catch (e) {
    alert(e?.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

function openAddModal() {
  addForm.name = ''
  addForm.gh = ''
  addForm.lsys = isDeptOnly.value && deptList.value.length === 1 ? deptList.value[0] : ''
  addForm.jb = ''
  addForm.xbie = ''
  addForm.password = ''
  showAddModal.value = true
}

function closeAddModal() {
  showAddModal.value = false
}

async function submitAdd() {
  const name = getCurrentUser()
  if (!name) return
  if (!(addForm.name || '').trim()) {
    alert('请填写姓名')
    return
  }
  if (!(addForm.password || '').trim()) {
    alert('请填写初始密码')
    return
  }
  if ((addForm.password || '').trim().length < 4) {
    alert('初始密码至少4位')
    return
  }
  if (!isDeptOnly.value && !(addForm.lsys || '').trim()) {
    alert('请选择科室')
    return
  }
  addSubmitting.value = true
  try {
    const res = await addEmployee({
      current_user: name,
      name: (addForm.name || '').trim(),
      gh: (addForm.gh || '').trim(),
      lsys: (addForm.lsys || '').trim(),
      jb: (addForm.jb || '').trim(),
      xbie: (addForm.xbie || '').trim(),
      password: (addForm.password || '').trim()
    })
    if (res?.success) {
      alert(res.message || '添加成功')
      closeAddModal()
      loadList()
    } else {
      alert(res?.message || '添加失败')
    }
  } catch (e) {
    alert(e?.response?.data?.detail || e?.message || '添加失败')
  } finally {
    addSubmitting.value = false
  }
}

onMounted(async () => {
  currentUserName.value = getCurrentUser()
  await loadDeptList()
  loadList()
})
</script>

<style scoped>
.admin-employee-page {
  padding: var(--spacing-xl, 24px) 0;
  min-height: 100%;
}

.admin-employee-page .container {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0;
}

/* ---------- 页面头部 ---------- */
.page-header {
  margin-bottom: var(--spacing-xl, 24px);
}

.header-content {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-lg, 16px);
  flex-wrap: wrap;
}

.header-info {
  flex: 1;
  min-width: 0;
}

.header-title {
  font-size: var(--font-size-xxl, 1.5rem);
  font-weight: 600;
  margin: 0 0 var(--spacing-xs, 4px) 0;
  line-height: 1.3;
}

.header-subtitle {
  color: var(--color-text-secondary);
  margin: 0;
  font-size: var(--font-size-sm, 0.875rem);
  line-height: 1.5;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-md, 12px);
  flex-shrink: 0;
}

.header-actions .btn {
  white-space: nowrap;
}

/* ---------- 筛选区 ---------- */
.query-section {
  margin-bottom: var(--spacing-xl, 24px);
  padding: var(--spacing-lg, 16px) var(--spacing-xl, 24px);
}

.query-form {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr auto;
  gap: var(--spacing-lg, 16px) var(--spacing-xl, 24px);
  align-items: end;
}

.query-form .form-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .query-form {
    grid-template-columns: 1fr 1fr;
  }
  .query-form .form-actions {
    grid-column: span 2;
  }
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs, 4px);
}

.form-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
}

.form-select,
.form-input {
  width: 100%;
  padding: var(--spacing-sm, 8px) var(--spacing-md, 12px);
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm, 4px);
  font-size: var(--font-size-base);
  background: var(--color-bg-container);
  min-height: 36px;
}

.form-select:focus,
.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.form-hint {
  font-size: var(--font-size-xs, 0.75rem);
  color: var(--color-text-tertiary);
  margin-top: var(--spacing-xs, 2px);
}

/* ---------- 表格区 ---------- */
.table-section {
  overflow: hidden;
  padding: 0;
}

.table-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-bg-spotlight);
}

.table-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  margin: 0;
}

.table-meta {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
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
  padding: var(--spacing-md) var(--spacing-xl);
  text-align: left;
  border-bottom: 1px solid var(--color-border-lighter);
}

.data-table th {
  background: var(--color-bg-spotlight);
  font-weight: 600;
  color: var(--color-text-secondary);
}

.data-table tbody tr:hover {
  background: var(--color-bg-spotlight);
}

.data-table .inline-select {
  min-width: 100px;
  max-width: 100%;
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: var(--font-size-sm);
}

.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 500;
}

.status-active {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.status-left {
  background: var(--color-error-bg);
  color: var(--color-error);
}

.btn-sm {
  padding: 4px 12px;
  font-size: var(--font-size-sm);
}

.btn-danger-outline {
  border: 1px solid var(--color-error);
  color: var(--color-error);
  background: transparent;
  border-radius: var(--radius-sm);
}

.btn-danger-outline:hover:not(:disabled) {
  background: var(--color-error-bg);
}

.btn-primary-outline {
  border: 1px solid var(--color-primary);
  color: var(--color-primary);
  background: transparent;
  border-radius: var(--radius-sm);
}

.btn-primary-outline:hover:not(:disabled) {
  background: var(--color-primary-lightest);
}

.empty-tip {
  padding: var(--spacing-xxl, 48px) var(--spacing-xl);
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

.pagination-wrap {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-xl);
  border-top: 1px solid var(--color-border-light);
  background: var(--color-bg-spotlight);
}

.page-info {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* 加载动画（与按钮内文字并列时留间距） */
.loading-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  margin-right: 6px;
  vertical-align: -2px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.btn-secondary {
  background: var(--color-bg-spotlight);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-base);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-border-lighter);
  border-color: var(--color-text-quaternary);
}

/* ---------- 添丁弹窗 ---------- */
.required {
  color: var(--color-error);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--color-bg-mask);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--spacing-lg);
}

.modal-card {
  background: var(--color-bg-container);
  border-radius: var(--radius-md);
  min-width: 420px;
  max-width: 520px;
  max-height: 90vh;
  overflow: auto;
  box-shadow: var(--shadow-elevated);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-light);
}

.modal-title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.modal-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  line-height: 1;
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 0 4px;
}

.modal-close:hover {
  color: var(--color-text-primary);
}

.modal-body {
  padding: var(--spacing-xl);
}

.form-row {
  display: flex;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.form-row .form-item {
  flex: 1;
  min-width: 0;
}

.modal-body .form-input,
.modal-body .form-select {
  width: 100%;
}

.modal-hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: var(--spacing-sm) 0 0;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
  padding: var(--spacing-lg) var(--spacing-xl);
  border-top: 1px solid var(--color-border-light);
}
</style>
