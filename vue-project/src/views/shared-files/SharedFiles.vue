<template>
  <div class="shared-page">
    <header class="page-header">
      <div class="header-left">
        <div class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 48 40" width="40" height="34">
            <path d="M4 10h14l4 4h22a4 4 0 0 1 4 4v16a4 4 0 0 1-4 4H4a4 4 0 0 1-4-4V14a4 4 0 0 1 4-4z" fill="#F6B73C"/>
            <path d="M0 16h48v18a4 4 0 0 1-4 4H4a4 4 0 0 1-4-4V16z" fill="#E8A017"/>
            <path d="M0 16h48v3H0z" fill="#F9D27A" opacity=".55"/>
          </svg>
        </div>
        <div>
          <h1>协同办公</h1>
          <p>部门协同 Office 文档 · 文件夹可见性 · 在线编辑</p>
        </div>
      </div>
      <div class="header-actions">
        <button type="button" class="btn" @click="refresh" title="刷新">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-2.6-6.3"/><polyline points="21 3 21 9 15 9"/></svg>
          刷新
        </button>
        <button v-if="perms.can_create_folder" type="button" class="btn" @click="openCreateFolder">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7h6l2 2h10v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z"/><path d="M12 12v6M9 15h6"/></svg>
          新建文件夹
        </button>
        <div v-if="perms.can_create_blank" class="dropdown">
          <button type="button" class="btn" @click="showCreateMenu = !showCreateMenu">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M12 18v-6M9 15h6"/></svg>
            新建文档
          </button>
          <div v-if="showCreateMenu" class="dropdown-menu">
            <button type="button" @click="createBlank('docx')">
              <span class="mini-badge word">W</span> Word (.docx)
            </button>
            <button type="button" @click="createBlank('xlsx')">
              <span class="mini-badge excel">X</span> Excel (.xlsx)
            </button>
            <button type="button" @click="createBlank('pptx')">
              <span class="mini-badge ppt">P</span> PPT (.pptx)
            </button>
          </div>
        </div>
        <label v-if="perms.can_upload" class="btn btn-primary upload-btn">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          上传文件
          <input type="file" hidden accept=".doc,.docx,.xls,.xlsx,.ppt,.pptx" @change="onUploadChange">
        </label>
        <div class="view-toggle" role="group" aria-label="视图切换">
          <button type="button" :class="['vt-btn', { active: viewMode === 'grid' }]" @click="viewMode = 'grid'" title="网格">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
          </button>
          <button type="button" :class="['vt-btn', { active: viewMode === 'list' }]" @click="viewMode = 'list'" title="列表">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
          </button>
        </div>
      </div>
    </header>

    <nav class="breadcrumb">
      <button type="button" class="crumb root" @click="goParent(null)">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/></svg>
        协同办公
      </button>
      <template v-for="c in breadcrumb" :key="c.id">
        <span class="sep">/</span>
        <button type="button" class="crumb" @click="goParent(c.id)">{{ c.name }}</button>
      </template>
    </nav>

    <div v-if="errorMessage" class="banner error">{{ errorMessage }}</div>

    <div class="workspace">
      <div v-if="loading" class="empty-state">
        <div class="spinner"></div>
        <p>正在加载…</p>
      </div>
      <div v-else-if="items.length === 0" class="empty-state">
        <div class="empty-folder" aria-hidden="true">
          <svg viewBox="0 0 96 80" width="88" height="72">
            <path d="M8 18h28l8 8h44a6 6 0 0 1 6 6v36a6 6 0 0 1-6 6H8a6 6 0 0 1-6-6V24a6 6 0 0 1 6-6z" fill="#F6B73C"/>
            <path d="M2 30h92v38a6 6 0 0 1-6 6H8a6 6 0 0 1-6-6V30z" fill="#E8A017"/>
            <path d="M2 30h92v6H2z" fill="#F9D27A" opacity=".5"/>
          </svg>
        </div>
        <p class="empty-title">当前目录为空</p>
        <p class="empty-hint">可新建文件夹，或上传 / 新建 Word、Excel、PPT 文档</p>
      </div>

      <!-- 网格视图 -->
      <div v-else-if="viewMode === 'grid'" class="file-grid">
        <article
          v-for="row in items"
          :key="row.id"
          class="file-card"
          :class="row.is_folder ? 'is-folder' : fileKind(row.file_type)"
          @dblclick="openItem(row)"
        >
          <button type="button" class="card-main" @click="openItem(row)">
            <div class="card-icon" aria-hidden="true">
              <svg v-if="row.is_folder" class="folder-svg" viewBox="0 0 72 60" width="56" height="46">
                <path d="M6 12h20l6 6h34a5 5 0 0 1 5 5v27a5 5 0 0 1-5 5H6a5 5 0 0 1-5-5V17a5 5 0 0 1 5-5z" fill="#F6B73C"/>
                <path d="M1 22h70v28a5 5 0 0 1-5 5H6a5 5 0 0 1-5-5V22z" fill="#E8A017"/>
                <path d="M1 22h70v4H1z" fill="#FCE3A8" opacity=".7"/>
                <rect x="14" y="30" width="28" height="3" rx="1.5" fill="#fff" opacity=".35"/>
              </svg>
              <div v-else class="doc-tile" :class="fileKind(row.file_type)">
                <span class="doc-letter">{{ fileLetter(row.file_type) }}</span>
                <span class="doc-ext">{{ (row.file_type || 'file').toUpperCase() }}</span>
              </div>
            </div>
            <div class="card-name" :title="row.name">{{ row.name }}</div>
            <div class="card-meta">
              <span v-if="row.is_folder" class="vis-pill">{{ visibilityShort(row) }}</span>
              <span v-else>{{ formatSize(row.size) }}</span>
            </div>
          </button>
          <div class="card-actions" @click.stop>
            <button v-if="row.can_edit && !row.is_folder" type="button" class="act" @click="openEditor(row)">编辑</button>
            <a v-if="!row.is_folder" class="act" :href="downloadUrl(row.id)">下载</a>
            <button v-if="row.can_set_visibility" type="button" class="act" @click="openVisibility(row)">可见性</button>
            <button v-if="row.can_rename" type="button" class="act" @click="renameItem(row)">重命名</button>
            <button v-if="row.can_delete" type="button" class="act danger" @click="deleteItem(row)">删除</button>
          </div>
        </article>
      </div>

      <!-- 列表视图 -->
      <div v-else class="table-wrap">
        <table class="file-table">
          <thead>
            <tr>
              <th class="col-name">名称</th>
              <th>可见性 / 类型</th>
              <th>大小</th>
              <th>创建人</th>
              <th>修改人</th>
              <th>更新时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in items" :key="row.id" @dblclick="openItem(row)">
              <td>
                <button type="button" class="name-btn" @click="openItem(row)">
                  <span class="list-icon" aria-hidden="true">
                    <svg v-if="row.is_folder" viewBox="0 0 36 30" width="28" height="24">
                      <path d="M3 6h10l3 3h17a2.5 2.5 0 0 1 2.5 2.5V24a2.5 2.5 0 0 1-2.5 2.5H3A2.5 2.5 0 0 1 .5 24V8.5A2.5 2.5 0 0 1 3 6z" fill="#F6B73C"/>
                      <path d="M.5 11h35v13A2.5 2.5 0 0 1 33 26.5H3A2.5 2.5 0 0 1 .5 24V11z" fill="#E8A017"/>
                    </svg>
                    <span v-else class="list-doc" :class="fileKind(row.file_type)">{{ fileLetter(row.file_type) }}</span>
                  </span>
                  <span class="name-text">{{ row.name }}</span>
                </button>
              </td>
              <td>
                <span v-if="row.is_folder" class="vis-pill">{{ visibilityText(row) }}</span>
                <span v-else class="type-tag" :class="fileKind(row.file_type)">{{ (row.file_type || '-').toUpperCase() }}</span>
              </td>
              <td>{{ row.is_folder ? '—' : formatSize(row.size) }}</td>
              <td>{{ row.created_by || '—' }}</td>
              <td>{{ row.updated_by || '—' }}</td>
              <td class="muted">{{ row.updated_at || '—' }}</td>
              <td class="actions">
                <button v-if="row.can_edit" type="button" class="btn btn-small btn-primary" @click="openEditor(row)">在线编辑</button>
                <a v-if="!row.is_folder" class="btn btn-small" :href="downloadUrl(row.id)">下载</a>
                <button v-if="row.can_set_visibility" type="button" class="btn btn-small" @click="openVisibility(row)">可见性</button>
                <button v-if="row.can_rename" type="button" class="btn btn-small" @click="renameItem(row)">重命名</button>
                <button v-if="row.can_delete" type="button" class="btn btn-small danger" @click="deleteItem(row)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showVisModal" class="modal-overlay" @click.self="showVisModal=false">
      <div class="modal">
        <h3>设置文件夹可见性：{{ visForm.name }}</h3>
        <label class="field"><input type="radio" value="all" v-model="visForm.visibility_type"> 全员可见</label>
        <label class="field"><input type="radio" value="restricted" v-model="visForm.visibility_type"> 按科室/级别限制（可组合）</label>
        <div v-if="visForm.visibility_type==='restricted'" class="vis-box">
          <div class="field"><div class="label">可见科室（不选=不限制科室）</div>
            <div class="checks"><label v-for="d in departments" :key="d" class="check"><input type="checkbox" :value="d" v-model="visForm.visibility_depts"> {{ d }}</label></div>
          </div>
          <div class="field"><div class="label">可见级别（不选=不限制级别）</div>
            <div class="checks"><label v-for="lv in levels" :key="lv.key" class="check"><input type="checkbox" :value="lv.key" v-model="visForm.visibility_levels"> {{ lv.label }}</label></div>
          </div>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn" @click="showVisModal=false">取消</button>
          <button type="button" class="btn btn-primary" @click="saveVisibility">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  listSharedFiles, getSharedMetaOptions, createSharedFolder, updateFolderVisibility,
  uploadSharedFile, createBlankSharedFile, renameSharedFile, deleteSharedFile, downloadSharedFileUrl
} from '@/api/sharedFiles'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const errorMessage = ref('')
const items = ref([])
const breadcrumb = ref([])
const parentId = ref(null)
const showCreateMenu = ref(false)
const showVisModal = ref(false)
const viewMode = ref(localStorage.getItem('shared_files_view') || 'grid')
const departments = ref([])
const levels = ref([])
const perms = reactive({ is_admin: false, can_create_folder: false, can_upload: false, can_create_blank: false, can_delete_file: false })
const visForm = reactive({ id: null, name: '', visibility_type: 'all', visibility_depts: [], visibility_levels: [] })

watch(viewMode, (v) => { try { localStorage.setItem('shared_files_view', v) } catch (e) {} })

function currentParentFromQuery() {
  const raw = route.query.parent_id
  if (raw == null || raw === '' || raw === 'null') return null
  const n = Number(raw)
  return Number.isFinite(n) && n > 0 ? n : null
}
function formatSize(size) {
  const n = Number(size) || 0
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB'
  return (n / 1024 / 1024).toFixed(1) + ' MB'
}
function fileKind(type) {
  const t = (type || '').toLowerCase()
  if (t === 'xls' || t === 'xlsx') return 'excel'
  if (t === 'doc' || t === 'docx') return 'word'
  if (t === 'ppt' || t === 'pptx') return 'ppt'
  return 'file'
}
function fileLetter(type) {
  const k = fileKind(type)
  if (k === 'excel') return 'X'
  if (k === 'word') return 'W'
  if (k === 'ppt') return 'P'
  return 'F'
}
function visibilityText(row) {
  if (!row.is_folder) return '—'
  if ((row.visibility_type || 'all') === 'all') return '全员可见'
  const parts = []
  if (row.visibility_depts && row.visibility_depts.length) parts.push('科室:' + row.visibility_depts.join('/'))
  if (row.visibility_levels && row.visibility_levels.length) parts.push('级别:' + row.visibility_levels.join('/'))
  return parts.length ? parts.join(' · ') : '限制（未配置）'
}
function visibilityShort(row) {
  if ((row.visibility_type || 'all') === 'all') return '全员'
  return '受限'
}
function downloadUrl(id) { return downloadSharedFileUrl(id) }
function humanize(err) {
  const detail = err && err.response && err.response.data && err.response.data.detail
  return (typeof detail === 'string' && detail) || (err && err.message) || '操作失败'
}
async function loadOptions() {
  try {
    const res = await getSharedMetaOptions()
    departments.value = res.departments || []
    levels.value = res.levels || []
  } catch (e) {}
}
async function refresh() {
  loading.value = true
  errorMessage.value = ''
  showCreateMenu.value = false
  try {
    const res = await listSharedFiles({ parent_id: parentId.value })
    items.value = res.items || []
    breadcrumb.value = res.breadcrumb || []
    Object.assign(perms, res.permissions || {})
  } catch (e) {
    errorMessage.value = humanize(e)
    items.value = []
  } finally {
    loading.value = false
  }
}
function goParent(id) {
  if (id == null) router.push({ path: '/shared-files' })
  else router.push({ path: '/shared-files', query: { parent_id: id } })
}
function openItem(row) {
  if (row.is_folder) goParent(row.id)
  else if (row.can_edit) openEditor(row)
}
function openEditor(row) { router.push('/shared-files/edit/' + row.id) }
async function openCreateFolder() {
  const name = window.prompt('请输入文件夹名称')
  if (!name || !name.trim()) return
  try {
    const res = await createSharedFolder({ name: name.trim(), parent_id: parentId.value, visibility_type: 'all' })
    await refresh()
    if (res.data) openVisibility(res.data)
  } catch (e) { window.alert(humanize(e)) }
}
function openVisibility(row) {
  visForm.id = row.id
  visForm.name = row.name
  visForm.visibility_type = row.visibility_type || 'all'
  visForm.visibility_depts = [...(row.visibility_depts || [])]
  visForm.visibility_levels = [...(row.visibility_levels || [])]
  showVisModal.value = true
}
async function saveVisibility() {
  try {
    await updateFolderVisibility(visForm.id, {
      visibility_type: visForm.visibility_type,
      visibility_depts: visForm.visibility_depts,
      visibility_levels: visForm.visibility_levels
    })
    showVisModal.value = false
    await refresh()
  } catch (e) { window.alert(humanize(e)) }
}
async function onUploadChange(ev) {
  const input = ev.target
  const file = input.files && input.files[0]
  input.value = ''
  if (!file) return
  try {
    await uploadSharedFile({ file, parent_id: parentId.value })
    await refresh()
  } catch (e) { window.alert(humanize(e)) }
}
async function createBlank(ext) {
  showCreateMenu.value = false
  const name = window.prompt('请输入文件名', '新建文档')
  if (!name || !name.trim()) return
  try {
    const res = await createBlankSharedFile({ name: name.trim(), file_type: ext, parent_id: parentId.value })
    await refresh()
    if (res.data && res.data.id) openEditor(res.data)
  } catch (e) { window.alert(humanize(e)) }
}
async function renameItem(row) {
  const name = window.prompt('新名称', row.name)
  if (!name || !name.trim() || name.trim() === row.name) return
  try {
    await renameSharedFile(row.id, name.trim())
    await refresh()
  } catch (e) { window.alert(humanize(e)) }
}
async function deleteItem(row) {
  const tip = row.is_folder
    ? ('确认删除文件夹「' + row.name + '」及其全部内容？')
    : ('确认删除「' + row.name + '」？')
  if (!window.confirm(tip)) return
  try {
    await deleteSharedFile(row.id)
    await refresh()
  } catch (e) { window.alert(humanize(e)) }
}
watch(() => route.query.parent_id, () => {
  parentId.value = currentParentFromQuery()
  refresh()
})
onMounted(async () => {
  parentId.value = currentParentFromQuery()
  await loadOptions()
  await refresh()
})
</script>

<style scoped>
.shared-page {
  --sf-bg: #f3f6fb;
  --sf-surface: #ffffff;
  --sf-ink: #1e293b;
  --sf-muted: #64748b;
  --sf-line: #e2e8f0;
  --sf-accent: #1890ff;
  --sf-word: #2b579a;
  --sf-excel: #217346;
  --sf-ppt: #c43e1c;
  min-height: calc(100vh - 80px);
  padding: 20px 24px 40px;
  color: var(--sf-ink);
  background:
    radial-gradient(1200px 400px at 10% -10%, #dbeafe 0%, transparent 55%),
    radial-gradient(900px 320px at 95% 0%, #fef3c7 0%, transparent 50%),
    var(--sf-bg);
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 14px;
}
.header-left { display: flex; gap: 14px; align-items: center; }
.brand-mark {
  width: 52px; height: 52px; border-radius: 14px;
  background: linear-gradient(145deg, #fff 0%, #fff7e6 100%);
  border: 1px solid #fde68a;
  display: grid; place-items: center;
  box-shadow: 0 6px 16px rgba(232, 160, 23, .18);
}
.page-header h1 { margin: 0 0 4px; font-size: 22px; letter-spacing: .02em; }
.page-header p { margin: 0; color: var(--sf-muted); font-size: 13px; }

.header-actions { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.btn {
  border: 1px solid var(--sf-line);
  background: var(--sf-surface);
  border-radius: 8px;
  padding: 7px 12px;
  cursor: pointer;
  font-size: 13px;
  text-decoration: none;
  color: inherit;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: background .15s, border-color .15s, box-shadow .15s;
}
.btn:hover { border-color: #bfdbfe; background: #f8fbff; }
.btn-primary {
  background: linear-gradient(180deg, #3aa0ff, var(--sf-accent));
  border-color: var(--sf-accent);
  color: #fff;
  box-shadow: 0 4px 12px rgba(24, 144, 255, .28);
}
.btn-primary:hover { filter: brightness(1.04); background: linear-gradient(180deg, #3aa0ff, var(--sf-accent)); }
.btn-small { padding: 4px 8px; font-size: 12px; border-radius: 6px; }
.btn.danger, .act.danger { color: #b91c1c; border-color: #fecaca; }
.upload-btn { cursor: pointer; }

.dropdown { position: relative; }
.dropdown-menu {
  position: absolute; top: calc(100% + 6px); left: 0;
  background: #fff; border: 1px solid var(--sf-line); border-radius: 10px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, .12); z-index: 30; min-width: 168px; padding: 6px;
}
.dropdown-menu button {
  display: flex; width: 100%; align-items: center; gap: 8px;
  text-align: left; border: none; background: transparent;
  padding: 8px 10px; cursor: pointer; border-radius: 7px; font-size: 13px;
}
.dropdown-menu button:hover { background: #f1f5f9; }
.mini-badge {
  width: 22px; height: 22px; border-radius: 5px; color: #fff;
  display: inline-grid; place-items: center; font-size: 11px; font-weight: 700;
}
.mini-badge.word { background: var(--sf-word); }
.mini-badge.excel { background: var(--sf-excel); }
.mini-badge.ppt { background: var(--sf-ppt); }

.view-toggle {
  display: inline-flex; border: 1px solid var(--sf-line); border-radius: 8px;
  overflow: hidden; background: #fff; margin-left: 4px;
}
.vt-btn {
  border: none; background: transparent; width: 34px; height: 32px;
  display: grid; place-items: center; cursor: pointer; color: var(--sf-muted);
}
.vt-btn.active { background: #e6f4ff; color: var(--sf-accent); }

.breadcrumb {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
  margin-bottom: 14px; font-size: 13px;
  padding: 8px 12px; background: rgba(255,255,255,.7);
  border: 1px solid var(--sf-line); border-radius: 10px; backdrop-filter: blur(6px);
}
.crumb {
  border: none; background: transparent; color: var(--sf-accent);
  cursor: pointer; padding: 2px 4px; border-radius: 4px;
  display: inline-flex; align-items: center; gap: 4px;
}
.crumb:hover { background: #e6f4ff; }
.crumb.root { font-weight: 600; color: var(--sf-ink); }
.sep { color: #94a3b8; }

.banner.error {
  background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca;
  border-radius: 10px; padding: 10px 12px; margin-bottom: 12px;
}

.workspace {
  background: rgba(255,255,255,.72);
  border: 1px solid var(--sf-line);
  border-radius: 16px;
  padding: 16px;
  min-height: 360px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, .04);
}

.empty-state {
  padding: 56px 16px; text-align: center; color: var(--sf-muted);
  display: flex; flex-direction: column; align-items: center; gap: 8px;
}
.empty-folder { filter: drop-shadow(0 8px 14px rgba(232, 160, 23, .25)); margin-bottom: 6px; }
.empty-title { margin: 0; color: var(--sf-ink); font-size: 16px; font-weight: 600; }
.empty-hint { margin: 0; font-size: 13px; }
.spinner {
  width: 28px; height: 28px; border-radius: 50%;
  border: 3px solid #dbeafe; border-top-color: var(--sf-accent);
  animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.file-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(148px, 1fr));
  gap: 12px;
}
.file-card {
  position: relative;
  background: #fff;
  border: 1px solid var(--sf-line);
  border-radius: 14px;
  padding: 12px 10px 10px;
  transition: transform .15s, box-shadow .15s, border-color .15s;
}
.file-card:hover {
  transform: translateY(-2px);
  border-color: #bfdbfe;
  box-shadow: 0 12px 24px rgba(15, 23, 42, .08);
}
.file-card.is-folder:hover { border-color: #fcd34d; box-shadow: 0 12px 24px rgba(232, 160, 23, .16); }
.card-main {
  width: 100%; border: none; background: transparent; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 0;
  color: inherit;
}
.card-icon {
  height: 64px; display: grid; place-items: center;
  filter: drop-shadow(0 6px 10px rgba(15, 23, 42, .1));
}
.folder-svg { display: block; }

.doc-tile {
  width: 46px; height: 56px; border-radius: 8px 10px 8px 8px;
  position: relative; color: #fff;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.25);
}
.doc-tile::before {
  content: '';
  position: absolute; top: 0; right: 0;
  border-style: solid; border-width: 0 14px 14px 0;
  border-color: transparent rgba(255,255,255,.35) transparent transparent;
}
.doc-tile.word { background: linear-gradient(160deg, #3b6fb6, var(--sf-word)); }
.doc-tile.excel { background: linear-gradient(160deg, #2f9a5f, var(--sf-excel)); }
.doc-tile.ppt { background: linear-gradient(160deg, #e15a3a, var(--sf-ppt)); }
.doc-tile.file { background: linear-gradient(160deg, #64748b, #475569); }
.doc-letter { font-size: 20px; font-weight: 800; line-height: 1; letter-spacing: -.02em; }
.doc-ext { font-size: 9px; opacity: .85; margin-top: 2px; font-weight: 600; }

.card-name {
  width: 100%;
  font-size: 13px; font-weight: 600; text-align: center;
  line-height: 1.35;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden; word-break: break-all;
}
.card-meta {
  font-size: 11px; color: var(--sf-muted); min-height: 18px;
}
.vis-pill {
  display: inline-flex; align-items: center;
  padding: 1px 8px; border-radius: 999px;
  background: #fff7ed; color: #b45309; border: 1px solid #fed7aa;
  font-size: 11px; font-weight: 600;
}

.card-actions {
  display: flex; flex-wrap: wrap; justify-content: center; gap: 4px;
  margin-top: 8px; padding-top: 8px; border-top: 1px dashed #eef2f7;
  opacity: 0; max-height: 0; overflow: hidden;
  transition: opacity .15s, max-height .15s;
}
.file-card:hover .card-actions,
.file-card:focus-within .card-actions {
  opacity: 1; max-height: 80px;
}
.act {
  border: 1px solid var(--sf-line); background: #f8fafc;
  border-radius: 6px; padding: 2px 7px; font-size: 11px;
  cursor: pointer; color: #334155; text-decoration: none;
}
.act:hover { background: #e6f4ff; border-color: #91caff; color: var(--sf-accent); }

.table-wrap { overflow: auto; border-radius: 12px; border: 1px solid var(--sf-line); background: #fff; }
.file-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.file-table th, .file-table td {
  padding: 11px 12px; border-bottom: 1px solid #f1f5f9;
  text-align: left; vertical-align: middle;
}
.file-table th {
  background: #f8fafc; color: #475569; font-weight: 600;
  position: sticky; top: 0; z-index: 1;
}
.file-table tbody tr:hover { background: #f8fbff; }
.col-name { min-width: 220px; }
.name-btn {
  border: none; background: transparent; cursor: pointer;
  display: inline-flex; align-items: center; gap: 10px;
  padding: 0; color: #0f172a; font-size: 13px; font-weight: 600;
}
.list-icon { display: inline-grid; place-items: center; width: 30px; }
.list-doc {
  width: 24px; height: 28px; border-radius: 4px; color: #fff;
  display: grid; place-items: center; font-size: 12px; font-weight: 800;
}
.list-doc.word { background: var(--sf-word); }
.list-doc.excel { background: var(--sf-excel); }
.list-doc.ppt { background: var(--sf-ppt); }
.list-doc.file { background: #64748b; }
.type-tag {
  display: inline-block; padding: 2px 8px; border-radius: 6px;
  font-size: 11px; font-weight: 700; color: #fff;
}
.type-tag.word { background: var(--sf-word); }
.type-tag.excel { background: var(--sf-excel); }
.type-tag.ppt { background: var(--sf-ppt); }
.type-tag.file { background: #64748b; }
.muted { color: var(--sf-muted); font-size: 12px; }
.actions { display: flex; flex-wrap: wrap; gap: 6px; }

.modal-overlay {
  position: fixed; inset: 0; background: rgba(15, 23, 42, .4);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000; padding: 16px; backdrop-filter: blur(2px);
}
.modal {
  width: min(640px, 100%); background: #fff; border-radius: 14px;
  padding: 20px; max-height: 80vh; overflow: auto;
  box-shadow: 0 24px 48px rgba(15, 23, 42, .2);
}
.modal h3 { margin: 0 0 12px; font-size: 16px; }
.field { display: block; margin-bottom: 10px; }
.vis-box { border: 1px solid var(--sf-line); border-radius: 10px; padding: 12px; margin-top: 8px; background: #f8fafc; }
.label { font-size: 13px; color: #475569; margin-bottom: 6px; }
.checks { display: flex; flex-wrap: wrap; gap: 8px 14px; max-height: 180px; overflow: auto; }
.check { font-size: 13px; display: inline-flex; align-items: center; gap: 4px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }

@media (max-width: 720px) {
  .shared-page { padding: 14px; }
  .page-header { flex-direction: column; }
  .file-grid { grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); }
}
</style>
