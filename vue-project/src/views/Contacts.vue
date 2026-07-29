<template>
  <div class="contacts-page">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">{{ directoryLabel }}</h1>
          <p class="header-subtitle">按单位查看联系方式，支持搜索、筛选和快速拨号</p>
        </div>
      </div>
    </div>

    <div class="toolbar card">
      <div class="toolbar-left">
        <div class="directory-tabs" role="tablist" aria-label="通讯录类型">
          <button type="button" class="directory-tab" :class="{ active: directorySource === 'department' }" @click="switchDirectory('department')">部门通讯录</button>
          <button type="button" class="directory-tab" :class="{ active: directorySource === 'company' }" @click="switchDirectory('company')">公司通讯录</button>
        </div>
        <label class="toolbar-label">{{ directorySource === 'company' ? '单位' : '科室' }}</label>
        <select v-model="selectedDept" class="toolbar-select" @change="loadContacts">
          <option value="">{{ directorySource === 'company' ? '全部单位' : '全部科室' }}</option>
          <option v-for="d in deptOptions" :key="d" :value="d">{{ d }}</option>
        </select>
        <span class="toolbar-total" v-if="!loading">共 {{ totalCount }} 人</span>
      </div>
      <div class="toolbar-right">
        <div class="search-box">
          <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            v-model="searchKeyword"
            type="text"
            class="search-input"
            placeholder="搜索姓名、工号、手机、座机…"
            @input="onSearchInput"
          />
          <button v-if="searchKeyword" type="button" class="search-clear" @click="clearSearch">&times;</button>
        </div>
        <button type="button" class="btn btn-outline btn-sm" @click="toggleExpandAll">
          {{ allExpanded ? '全部收起' : '全部展开' }}
        </button>
        <label v-if="canManageCompany" class="btn btn-primary btn-sm upload-directory-btn" :class="{ disabled: importing }">
          <input ref="companyFileInput" type="file" accept=".xlsx" @change="onCompanyFileSelected" />
          {{ importing ? '更新中…' : '更新公司通讯录' }}
        </label>
      </div>
    </div>

    <div v-if="loading" class="loading-state card">
      <div class="loading-spinner"></div>
      <p>加载中…</p>
    </div>

    <div v-else-if="departments.length === 0" class="empty-state card">
      <p>{{ searchKeyword ? '未找到匹配的联系人' : '暂无通讯录数据' }}</p>
    </div>

    <div v-else class="dept-list">
      <div
        v-for="dept in departments"
        :key="dept.name"
        class="dept-group card"
      >
        <div class="dept-header" @click="toggleDept(dept.name)">
          <div class="dept-header-left">
            <span class="dept-arrow" :class="{ expanded: expandedDepts[dept.name] }">▸</span>
            <h2 class="dept-name">{{ dept.name }}</h2>
            <span class="dept-count">{{ dept.count }} 人</span>
          </div>
        </div>
        <Transition name="dept-fold">
          <div v-if="expandedDepts[dept.name]" class="dept-body">
            <div class="contact-grid">
              <div
                v-for="p in dept.members"
                :key="p.gh || p.name"
                class="contact-card"
                :class="{ 'contact-card-leader': isLeaderJb(p.jb) }"
              >
                <div class="contact-card-top">
                  <span class="contact-name">{{ p.name }}</span>
                  <span v-if="p.jb" class="jb-badge" :class="jbBadgeClass(p.jb)">{{ p.jb }}</span>
                </div>
                <div v-if="p.group" class="contact-group">{{ p.group }}</div>
                <div class="contact-card-phones">
                  <div v-if="p.mobile" class="contact-phone-row">
                    <svg class="contact-phone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="2" width="14" height="20" rx="2" /><line x1="12" y1="18" x2="12.01" y2="18" /></svg>
                    <a :href="'tel:' + p.mobile" class="phone-link">{{ p.mobile }}</a>
                  </div>
                  <div v-if="p.telephone" class="contact-phone-row">
                    <svg class="contact-phone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" /></svg>
                    <span class="tel-text">{{ p.telephone }}</span>
                  </div>
                  <div v-if="!p.mobile && !p.telephone" class="contact-phone-row contact-no-phone">
                    <span class="no-data">暂无联系方式</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { canManageCompanyContacts, getContacts, importCompanyContacts } from '@/api/contacts'

const departments = ref([])
const loading = ref(false)
const searchKeyword = ref('')
const selectedDept = ref('')
const totalCount = ref(0)
const expandedDepts = reactive({})
const deptOptions = ref([])
const directorySource = ref('department')
const canManageCompany = ref(false)
const importing = ref(false)
const companyFileInput = ref(null)

let searchTimer = null

const directoryLabel = computed(() => directorySource.value === 'company' ? '公司通讯录' : '部门通讯录')

const allExpanded = computed(() => {
  const keys = Object.keys(expandedDepts)
  return keys.length > 0 && keys.every(k => expandedDepts[k])
})

function toggleDept(name) {
  expandedDepts[name] = !expandedDepts[name]
}

function toggleExpandAll() {
  const expand = !allExpanded.value
  for (const dept of departments.value) {
    expandedDepts[dept.name] = expand
  }
}

function isLeaderJb(jb) {
  if (!jb) return false
  return /经理|主任|组长/.test(jb)
}

function jbBadgeClass(jb) {
  if (!jb) return ''
  if (/经理/.test(jb)) return 'jb-manager'
  if (/主任/.test(jb)) return 'jb-director'
  if (/组长/.test(jb)) return 'jb-leader'
  return 'jb-default'
}

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => loadContacts(), 300)
}

function clearSearch() {
  searchKeyword.value = ''
  loadContacts()
}

function currentUserName() {
  try {
    const user = JSON.parse(localStorage.getItem('userInfo') || '{}')
    return (user.name || user.userName || user.username || '').trim()
  } catch (_) {
    return ''
  }
}

function switchDirectory(source) {
  if (directorySource.value === source) return
  directorySource.value = source
  selectedDept.value = ''
  searchKeyword.value = ''
  deptOptions.value = []
  Object.keys(expandedDepts).forEach(key => delete expandedDepts[key])
  loadContacts()
}

async function onCompanyFileSelected(event) {
  const file = event.target.files?.[0]
  if (!file || importing.value) return
  if (!/\.xlsx$/i.test(file.name)) {
    window.alert('请上传 .xlsx 格式的公司电话号码表')
    event.target.value = ''
    return
  }
  importing.value = true
  try {
    const res = await importCompanyContacts(file, currentUserName())
    window.alert(res?.message || '公司通讯录已更新')
    if (directorySource.value === 'company') {
      selectedDept.value = ''
      searchKeyword.value = ''
      await loadContacts()
    }
  } catch (error) {
    window.alert(error?.response?.data?.detail || error?.message || '公司通讯录更新失败')
  } finally {
    importing.value = false
    if (companyFileInput.value) companyFileInput.value.value = ''
  }
}

async function loadContacts() {
  loading.value = true
  try {
    const params = {}
    if (selectedDept.value) params.department = selectedDept.value
    if (searchKeyword.value.trim()) params.keyword = searchKeyword.value.trim()
    params.source = directorySource.value
    const res = await getContacts(params)
    if (res?.success) {
      departments.value = res.departments || []
      totalCount.value = res.total || 0
      if (!selectedDept.value) {
        deptOptions.value = departments.value.map(dept => dept.name)
      }
      for (const dept of departments.value) {
        if (!(dept.name in expandedDepts)) {
          expandedDepts[dept.name] = true
        }
      }
    }
  } catch (e) {
    console.error('加载通讯录失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadContacts()
  canManageCompanyContacts(currentUserName())
    .then(res => { canManageCompany.value = Boolean(res?.canManage) })
    .catch(() => { canManageCompany.value = false })
})
</script>

<style scoped>
.contacts-page {
  width: 100%;
  max-width: none;
  padding: 0 0 var(--spacing-xl);
}
.page-header { margin-bottom: var(--spacing-lg); text-align: left; }
.header-content { display: flex; flex-direction: column; gap: 4px; }
.header-title { font-size: var(--font-size-xl); font-weight: var(--font-weight-bold); margin: 0; }
.header-subtitle { font-size: var(--font-size-sm); color: var(--color-text-tertiary); margin: 4px 0 0; }

.card {
  background: white;
  border-radius: var(--radius-md, 8px);
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.06));
  border: 1px solid var(--color-border-lighter, #e5e7eb);
  padding: var(--spacing-md, 16px) var(--spacing-lg, 20px);
  margin-bottom: var(--spacing-md, 16px);
}

.toolbar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
.toolbar-left, .toolbar-right { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.toolbar-label { font-size: 13px; color: var(--color-text-secondary); font-weight: 500; }
.directory-tabs { display: inline-flex; padding: 3px; border: 1px solid #dbe3ef; border-radius: 7px; background: #f8fafc; }
.directory-tab { border: 0; border-radius: 5px; padding: 5px 10px; color: #64748b; background: transparent; font-size: 13px; cursor: pointer; }
.directory-tab.active { color: #1d4ed8; background: #fff; box-shadow: 0 1px 3px rgba(15, 23, 42, .12); font-weight: 600; }
.toolbar-select {
  padding: 6px 10px;
  border: 1px solid var(--color-border-base, #d1d5db);
  border-radius: 6px;
  font-size: 13px;
  background: #fff;
  min-width: 140px;
}
.toolbar-total { font-size: 12px; color: #94a3b8; font-weight: 500; }

.search-box {
  position: relative;
  display: flex;
  align-items: center;
}
.search-icon {
  position: absolute;
  left: 10px;
  width: 15px;
  height: 15px;
  color: #94a3b8;
  pointer-events: none;
}
.search-input {
  padding: 6px 30px 6px 32px;
  border: 1px solid var(--color-border-base, #d1d5db);
  border-radius: 6px;
  font-size: 13px;
  width: 260px;
  outline: none;
  transition: border-color 0.15s;
}
.search-input:focus { border-color: var(--color-primary, #3b82f6); box-shadow: 0 0 0 2px rgba(59,130,246,.12); }
.search-clear {
  position: absolute;
  right: 6px;
  background: none;
  border: none;
  font-size: 16px;
  color: #94a3b8;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}
.search-clear:hover { color: #475569; }

.btn { cursor: pointer; border: 1px solid var(--color-border-base); background: white; border-radius: 6px; padding: 6px 14px; font-size: 13px; transition: all .15s; }
.btn:hover { background: #f8fafc; }
.btn-outline { border-color: var(--color-primary, #3b82f6); color: var(--color-primary, #3b82f6); }
.btn-outline:hover { background: #eff6ff; }
.btn-primary { border-color: var(--color-primary, #3b82f6); background: var(--color-primary, #3b82f6); color: #fff; }
.btn-primary:hover { background: #2563eb; }
.upload-directory-btn { display: inline-flex; align-items: center; }
.upload-directory-btn input { display: none; }
.upload-directory-btn.disabled { cursor: wait; opacity: .7; pointer-events: none; }

.loading-state { text-align: center; padding: 48px; color: #94a3b8; }
.loading-spinner {
  width: 28px; height: 28px;
  border: 3px solid #e5e7eb;
  border-top-color: var(--color-primary, #3b82f6);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  margin: 0 auto 12px;
}
@keyframes spin { to { transform: rotate(360deg); } }
.empty-state { text-align: center; padding: 48px; color: #94a3b8; font-size: 14px; }

.dept-list { display: flex; flex-direction: column; gap: 0; }
.dept-group { padding: 0; overflow: hidden; }
.dept-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}
.dept-header:hover { background: #f8fafc; }
.dept-header-left { display: flex; align-items: center; gap: 10px; }
.dept-arrow {
  display: inline-block;
  font-size: 13px;
  color: var(--color-primary, #3b82f6);
  transition: transform 0.2s;
  width: 14px;
}
.dept-arrow.expanded { transform: rotate(90deg); }
.dept-name { margin: 0; font-size: 15px; font-weight: 700; color: #1e293b; }
.dept-count {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #e0e7ff;
  color: #4338ca;
  font-weight: 600;
}

.dept-body { padding: 0 12px 14px; }
.dept-fold-enter-active, .dept-fold-leave-active { transition: all 0.2s ease; overflow: hidden; }
.dept-fold-enter-from, .dept-fold-leave-to { opacity: 0; max-height: 0; }
.dept-fold-enter-to, .dept-fold-leave-from { opacity: 1; max-height: 6000px; }

.contact-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.contact-card {
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px 14px;
  transition: box-shadow 0.15s, border-color 0.15s;
}
.contact-card:hover {
  border-color: #bfdbfe;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.08);
}
.contact-card-leader {
  background: #fffbeb;
  border-color: #fde68a;
}
.contact-card-leader:hover {
  border-color: #fbbf24;
  box-shadow: 0 2px 8px rgba(251, 191, 36, 0.12);
}

.contact-card-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.contact-group { margin: -3px 0 6px; color: #64748b; font-size: 12px; }
.contact-name {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
}

.jb-badge {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}
.jb-manager { background: #fef3c7; color: #92400e; }
.jb-director { background: #dbeafe; color: #1e40af; }
.jb-leader { background: #dcfce7; color: #166534; }
.jb-default { background: #f1f5f9; color: #475569; }

.contact-card-phones {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.contact-phone-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  line-height: 1.4;
}
.contact-phone-icon {
  width: 13px;
  height: 13px;
  flex-shrink: 0;
  color: #94a3b8;
}
.phone-link {
  color: var(--color-primary, #3b82f6);
  text-decoration: none;
  font-weight: 500;
  font-size: 12px;
}
.phone-link:hover { text-decoration: underline; }
.tel-text { color: #475569; font-size: 12px; }
.contact-no-phone { min-height: 18px; }
.no-data { color: #cbd5e1; font-size: 12px; }

@media (max-width: 1000px) {
  .contact-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 640px) {
  .toolbar { flex-direction: column; align-items: stretch; }
  .search-input { width: 100%; }
  .contact-grid { grid-template-columns: 1fr; }
}
</style>
