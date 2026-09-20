<template>
  <div class="shared-page">
    <header class="page-header">
      <div>
        <h1>协同办公</h1>
        <p>部门协同 Office 文档：支持文件夹可见性、在线协同编辑。</p>
      </div>
      <div class="header-actions">
        <button type="button" class="btn" @click="refresh">刷新</button>
        <button v-if="perms.can_create_folder" type="button" class="btn" @click="openCreateFolder">新建文件夹</button>
        <div v-if="perms.can_create_blank" class="dropdown">
          <button type="button" class="btn" @click="showCreateMenu = !showCreateMenu">新建文档</button>
          <div v-if="showCreateMenu" class="dropdown-menu">
            <button type="button" @click="createBlank('docx')">Word (.docx)</button>
            <button type="button" @click="createBlank('xlsx')">Excel (.xlsx)</button>
            <button type="button" @click="createBlank('pptx')">PPT (.pptx)</button>
          </div>
        </div>
        <label v-if="perms.can_upload" class="btn btn-primary upload-btn">
          上传文件
          <input type="file" hidden accept=".doc,.docx,.xls,.xlsx,.ppt,.pptx" @change="onUploadChange">
        </label>
      </div>
    </header>

    <nav class="breadcrumb">
      <button type="button" class="crumb" @click="goParent(null)">协同办公</button>
      <template v-for="c in breadcrumb" :key="c.id">
        <span class="sep">/</span>
        <button type="button" class="crumb" @click="goParent(c.id)">{{ c.name }}</button>
      </template>
    </nav>

    <div v-if="errorMessage" class="banner error">{{ errorMessage }}</div>
    <div v-if="loading" class="empty-state">正在加载...</div>
    <div v-else-if="items.length === 0" class="empty-state">当前目录为空。</div>
    <div v-else class="table-wrap">
      <table class="file-table">
        <thead>
          <tr>
            <th>名称</th>
            <th>类型</th>
            <th>可见性</th>
            <th>大小</th>
            <th>创建人</th>
            <th>修改人</th>
            <th>更新时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in items" :key="row.id">
            <td>
              <button type="button" class="name-btn" @click="openItem(row)">
                <span class="icon">{{ row.is_folder ? '?' : fileIcon(row.file_type) }}</span>
                <span>{{ row.name }}</span>
              </button>
            </td>
            <td>{{ row.is_folder ? '文件夹' : (row.file_type || '-').toUpperCase() }}</td>
            <td>{{ visibilityText(row) }}</td>
            <td>{{ row.is_folder ? '-' : formatSize(row.size) }}</td>
            <td>{{ row.created_by || '-' }}</td>
            <td>{{ row.updated_by || '-' }}</td>
            <td>{{ row.updated_at || '-' }}</td>
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
const departments = ref([])
const levels = ref([])
const perms = reactive({ is_admin: false, can_create_folder: false, can_upload: false, can_create_blank: false, can_delete_file: false })
const visForm = reactive({ id: null, name: '', visibility_type: 'all', visibility_depts: [], visibility_levels: [] })

function currentParentFromQuery() {
  const raw = route.query.parent_id
  if (raw == null || raw === '' || raw === 'null') return null
  const n = Number(raw)
  return Number.isFinite(n) && n > 0 ? n : null
}
function formatSize(size) { const n = Number(size) || 0; if (n < 1024) return n + " B"; if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB"; return (n / 1024 / 1024).toFixed(1) + " MB" }
function fileIcon(type) { const t = (type || '').toLowerCase(); if (t === 'xls' || t === 'xlsx') return '?'; if (t === 'doc' || t === 'docx') return '?'; if (t === 'ppt' || t === 'pptx') return '?'; return '?' }
function visibilityText(row) {
  if (!row.is_folder) return "-"
  if ((row.visibility_type || 'all') === 'all') return '全员可见'
  const parts = []
  if (row.visibility_depts && row.visibility_depts.length) parts.push('科室:' + row.visibility_depts.join('/'))
  if (row.visibility_levels && row.visibility_levels.length) parts.push('级别:' + row.visibility_levels.join('/'))
  return parts.length ? parts.join(' ; ') : '限制（未配置）'
}
function downloadUrl(id) { return downloadSharedFileUrl(id) }
function humanize(err) { const detail = err && err.response && err.response.data && err.response.data.detail; return (typeof detail === 'string' && detail) || (err && err.message) || '操作失败' }
async function loadOptions() { try { const res = await getSharedMetaOptions(); departments.value = res.departments || []; levels.value = res.levels || [] } catch (e) {} }
async function refresh() { loading.value = true; errorMessage.value = ""; showCreateMenu.value = false; try { const res = await listSharedFiles({ parent_id: parentId.value }); items.value = res.items || []; breadcrumb.value = res.breadcrumb || []; Object.assign(perms, res.permissions || {}) } catch (e) { errorMessage.value = humanize(e); items.value = [] } finally { loading.value = false } }
function goParent(id) { if (id == null) router.push({ path: '/shared-files' }); else router.push({ path: '/shared-files', query: { parent_id: id } }) }
function openItem(row) { if (row.is_folder) goParent(row.id); else if (row.can_edit) openEditor(row) }
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
function openVisibility(row) { visForm.id = row.id; visForm.name = row.name; visForm.visibility_type = row.visibility_type || 'all'; visForm.visibility_depts = [...(row.visibility_depts || [])]; visForm.visibility_levels = [...(row.visibility_levels || [])]; showVisModal.value = true }
async function saveVisibility() { try { await updateFolderVisibility(visForm.id, { visibility_type: visForm.visibility_type, visibility_depts: visForm.visibility_depts, visibility_levels: visForm.visibility_levels }); showVisModal.value = false; await refresh() } catch (e) { window.alert(humanize(e)) } }
async function onUploadChange(ev) { const input = ev.target; const file = input.files && input.files[0]; input.value = ""; if (!file) return; try { await uploadSharedFile({ file, parent_id: parentId.value }); await refresh() } catch (e) { window.alert(humanize(e)) } }
async function createBlank(ext) {
  showCreateMenu.value = false
  const name = window.prompt('请输入文件名', '新建文档')
  if (!name || !name.trim()) return
  try { const res = await createBlankSharedFile({ name: name.trim(), file_type: ext, parent_id: parentId.value }); await refresh(); if (res.data && res.data.id) openEditor(res.data) } catch (e) { window.alert(humanize(e)) }
}
async function renameItem(row) { const name = window.prompt('新名称', row.name); if (!name || !name.trim() || name.trim() === row.name) return; try { await renameSharedFile(row.id, name.trim()); await refresh() } catch (e) { window.alert(humanize(e)) } }
async function deleteItem(row) {
  const tip = row.is_folder ? ('确认删除文件夹「' + row.name + '」及其全部内容？') : ('确认删除「' + row.name + '」？')
  if (!window.confirm(tip)) return
  try { await deleteSharedFile(row.id); await refresh() } catch (e) { window.alert(humanize(e)) }
}
watch(() => route.query.parent_id, () => { parentId.value = currentParentFromQuery(); refresh() })
onMounted(async () => { parentId.value = currentParentFromQuery(); await loadOptions(); await refresh() })
</script>

<style scoped>
.shared-page { padding: 20px 24px 32px; color: #1f2937; }
.page-header { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 16px; }
.page-header h1 { margin: 0 0 6px; font-size: 22px; }
.page-header p { margin: 0; color: #6b7280; font-size: 13px; }
.header-actions { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.btn { border: 1px solid #d1d5db; background: #fff; border-radius: 6px; padding: 7px 12px; cursor: pointer; font-size: 13px; text-decoration: none; color: inherit; display: inline-flex; align-items: center; }
.btn-primary { background: #2563eb; border-color: #2563eb; color: #fff; }
.btn-small { padding: 4px 8px; font-size: 12px; }
.btn.danger { color: #b91c1c; border-color: #fecaca; }
.upload-btn { cursor: pointer; }
.dropdown { position: relative; }
.dropdown-menu { position: absolute; top: 110%; left: 0; background: #fff; border: 1px solid #e5e7eb; border-radius: 6px; box-shadow: 0 8px 20px rgba(0,0,0,.08); z-index: 20; min-width: 140px; }
.dropdown-menu button { display: block; width: 100%; text-align: left; border: none; background: transparent; padding: 8px 12px; cursor: pointer; }
.dropdown-menu button:hover { background: #f3f4f6; }
.breadcrumb { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-bottom: 14px; font-size: 13px; }
.crumb { border: none; background: transparent; color: #2563eb; cursor: pointer; padding: 0; }
.sep { color: #9ca3af; }
.banner.error { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px; }
.empty-state { padding: 36px 12px; text-align: center; color: #6b7280; background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; }
.table-wrap { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; overflow: auto; }
.file-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.file-table th, .file-table td { padding: 10px 12px; border-bottom: 1px solid #f3f4f6; text-align: left; vertical-align: middle; }
.file-table th { background: #f9fafb; color: #4b5563; font-weight: 600; }
.name-btn { border: none; background: transparent; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; padding: 0; color: #111827; font-size: 13px; }
.actions { display: flex; flex-wrap: wrap; gap: 6px; }
.modal-overlay { position: fixed; inset: 0; background: rgba(15,23,42,.35); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 16px; }
.modal { width: min(640px, 100%); background: #fff; border-radius: 10px; padding: 18px; max-height: 80vh; overflow: auto; }
.modal h3 { margin: 0 0 12px; font-size: 16px; }
.field { display: block; margin-bottom: 10px; }
.vis-box { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; margin-top: 8px; }
.label { font-size: 13px; color: #4b5563; margin-bottom: 6px; }
.checks { display: flex; flex-wrap: wrap; gap: 8px 14px; max-height: 180px; overflow: auto; }
.check { font-size: 13px; display: inline-flex; align-items: center; gap: 4px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
</style>
