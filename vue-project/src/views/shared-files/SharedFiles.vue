<template>
  <div class="shared-page">
    <header class="page-header">
      <div>
        <h1>共享文档</h1>
        <p>部门共享 Office 文档，支持多人在线协同编辑。</p>
      </div>
      <div class="header-actions">
        <button type="button" class="btn" @click="refresh">刷新</button>
        <button type="button" class="btn" @click="openCreateFolder">新建文件夹</button>
        <label class="btn btn-primary upload-btn">
          上传文件
          <input type="file" hidden accept=".doc,.docx,.xls,.xlsx,.ppt,.pptx" @change="onUploadChange">
        </label>
      </div>
    </header>

    <nav class="breadcrumb">
      <button type="button" class="crumb" @click="goParent(null)">共享文档</button>
      <template v-for="c in breadcrumb" :key="c.id">
        <span class="sep">/</span>
        <button type="button" class="crumb" @click="goParent(c.id)">{{ c.name }}</button>
      </template>
    </nav>

    <div v-if="errorMessage" class="banner error">{{ errorMessage }}</div>
    <div v-if="loading" class="empty-state">正在加载...</div>
    <div v-else-if="items.length === 0" class="empty-state">当前目录为空，可新建文件夹或上传 Office 文件。</div>
    <div v-else class="table-wrap">
      <table class="file-table">
        <thead>
          <tr>
            <th>名称</th>
            <th>类型</th>
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
              <button
                type="button"
                class="name-btn"
                @click="openItem(row)"
              >
                <span class="icon">{{ row.is_folder ? '?' : fileIcon(row.file_type) }}</span>
                <span>{{ row.name }}</span>
              </button>
            </td>
            <td>{{ row.is_folder ? '文件夹' : (row.file_type || '-').toUpperCase() }}</td>
            <td>{{ row.is_folder ? '-' : formatSize(row.size) }}</td>
            <td>{{ row.created_by || '-' }}</td>
            <td>{{ row.updated_by || '-' }}</td>
            <td>{{ row.updated_at || '-' }}</td>
            <td class="actions">
              <button v-if="row.can_edit" type="button" class="btn btn-small btn-primary" @click="openEditor(row)">在线编辑</button>
              <a v-if="!row.is_folder" class="btn btn-small" :href="downloadUrl(row.id)">下载</a>
              <button v-if="row.can_rename" type="button" class="btn btn-small" @click="renameItem(row)">重命名</button>
              <button v-if="row.can_delete" type="button" class="btn btn-small danger" @click="deleteItem(row)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  listSharedFiles,
  createSharedFolder,
  uploadSharedFile,
  renameSharedFile,
  deleteSharedFile,
  downloadSharedFileUrl
} from '@/api/sharedFiles'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const errorMessage = ref('')
const items = ref([])
const breadcrumb = ref([])
const parentId = ref(null)

function currentParentFromQuery() {
  const raw = route.query.parent_id
  if (raw == null || raw === '' || raw === 'null') return null
  const n = Number(raw)
  return Number.isFinite(n) && n > 0 ? n : null
}

function formatSize(size) {
  const n = Number(size) || 0
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

function fileIcon(type) {
  const t = (type || '').toLowerCase()
  if (t === 'xls' || t === 'xlsx') return '?'
  if (t === 'doc' || t === 'docx') return '?'
  if (t === 'ppt' || t === 'pptx') return '?'
  return '?'
}

function downloadUrl(id) {
  return downloadSharedFileUrl(id)
}

function humanize(err) {
  const detail = err && err.response && err.response.data && err.response.data.detail
  return (typeof detail === 'string' && detail) || (err && err.message) || '操作失败'
}

async function refresh() {
  loading.value = true
  errorMessage.value = ''
  try {
    const res = await listSharedFiles({ parent_id: parentId.value })
    items.value = res.items || []
    breadcrumb.value = res.breadcrumb || []
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
  if (row.is_folder) {
    goParent(row.id)
    return
  }
  if (row.can_edit) openEditor(row)
}

function openEditor(row) {
  router.push(`/shared-files/edit/${row.id}`)
}

async function openCreateFolder() {
  const name = window.prompt('请输入文件夹名称')
  if (!name || !name.trim()) return
  try {
    await createSharedFolder({ name: name.trim(), parent_id: parentId.value })
    await refresh()
  } catch (e) {
    window.alert(humanize(e))
  }
}

async function onUploadChange(ev) {
  const input = ev.target
  const file = input.files && input.files[0]
  input.value = ''
  if (!file) return
  try {
    await uploadSharedFile({ file, parent_id: parentId.value })
    await refresh()
  } catch (e) {
    window.alert(humanize(e))
  }
}

async function renameItem(row) {
  const name = window.prompt('新名称', row.name)
  if (!name || !name.trim() || name.trim() === row.name) return
  try {
    await renameSharedFile(row.id, name.trim())
    await refresh()
  } catch (e) {
    window.alert(humanize(e))
  }
}

async function deleteItem(row) {
  const tip = row.is_folder
    ? `确认删除文件夹「${row.name}」及其全部内容？`
    : `确认删除「${row.name}」？`
  if (!window.confirm(tip)) return
  try {
    await deleteSharedFile(row.id)
    await refresh()
  } catch (e) {
    window.alert(humanize(e))
  }
}

watch(
  () => route.query.parent_id,
  () => {
    parentId.value = currentParentFromQuery()
    refresh()
  }
)

onMounted(() => {
  parentId.value = currentParentFromQuery()
  refresh()
})
</script>

<style scoped>
.shared-page {
  padding: 20px 24px 32px;
  color: #1f2937;
}
.page-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 16px;
}
.page-header h1 {
  margin: 0 0 6px;
  font-size: 22px;
}
.page-header p {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
}
.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.btn {
  border: 1px solid #d1d5db;
  background: #fff;
  border-radius: 6px;
  padding: 7px 12px;
  cursor: pointer;
  font-size: 13px;
  text-decoration: none;
  color: inherit;
  display: inline-flex;
  align-items: center;
}
.btn-primary {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}
.btn-small {
  padding: 4px 8px;
  font-size: 12px;
}
.btn.danger {
  color: #b91c1c;
  border-color: #fecaca;
}
.upload-btn {
  cursor: pointer;
}
.breadcrumb {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 14px;
  font-size: 13px;
}
.crumb {
  border: none;
  background: transparent;
  color: #2563eb;
  cursor: pointer;
  padding: 0;
}
.sep {
  color: #9ca3af;
}
.banner.error {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 12px;
}
.empty-state {
  padding: 36px 12px;
  text-align: center;
  color: #6b7280;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}
.table-wrap {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: auto;
}
.file-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.file-table th,
.file-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #f3f4f6;
  text-align: left;
  vertical-align: middle;
}
.file-table th {
  background: #f9fafb;
  color: #4b5563;
  font-weight: 600;
}
.name-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0;
  color: #111827;
  font-size: 13px;
}
.name-btn:hover span:last-child {
  color: #2563eb;
  text-decoration: underline;
}
.icon {
  font-size: 16px;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
