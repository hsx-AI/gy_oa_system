<template>
  <div class="page-container file-page-counter">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">文件页数统计</h1>
          <p class="header-subtitle">
            支持 PDF、Word、PPT、Excel 批量统计页数，可拖拽上传或选择文件/文件夹
          </p>
        </div>
      </div>
    </div>

    <div class="container">
      <section
        class="drop-zone card"
        :class="{ 'drop-zone--active': dragOver }"
        @dragenter.prevent="dragOver = true"
        @dragover.prevent="dragOver = true"
        @dragleave.prevent="dragOver = false"
        @drop.prevent="onDrop"
      >
        <p class="drop-zone__title">拖拽文件或文件夹到这里</p>
        <p class="drop-zone__hint">支持 .pdf .doc .docx .ppt .pptx .xls .xlsx</p>
      </section>

      <div class="toolbar">
        <input
          ref="fileInputRef"
          type="file"
          multiple
          accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx"
          class="hidden-input"
          @change="onFileInput"
        >
        <input
          ref="folderInputRef"
          type="file"
          webkitdirectory
          directory
          multiple
          class="hidden-input"
          @change="onFolderInput"
        >
        <button type="button" class="btn" @click="fileInputRef?.click()">选择文件</button>
        <button type="button" class="btn" @click="folderInputRef?.click()">选择文件夹</button>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="!pendingFiles.length || counting"
          @click="startCounting"
        >
          {{ counting ? '统计中…' : '开始统计' }}
        </button>
        <button type="button" class="btn" :disabled="!results.length" @click="exportTable">导出表格</button>
        <button type="button" class="btn" :disabled="!pendingFiles.length && !results.length" @click="clearAll">
          清空列表
        </button>
      </div>

      <section class="card table-card">
        <div class="summary-bar">
          <span v-if="counting">正在统计，请稍候…</span>
          <span v-else-if="results.length">{{ summaryText }}</span>
          <span v-else>总页数：0</span>
          <span v-if="pendingFiles.length" class="summary-bar__pending">
            待统计 {{ pendingFiles.length }} 个文件
          </span>
        </div>

        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th class="col-index">序号</th>
                <th class="sortable-th" @click="toggleSort('filename')">
                  文件名 <span class="sort-icon">{{ sortIcon('filename') }}</span>
                </th>
                <th class="sortable-th col-pages" @click="toggleSort('page_count')">
                  页数 <span class="sort-icon">{{ sortIcon('page_count') }}</span>
                </th>
                <th class="sortable-th col-type" @click="toggleSort('file_type')">
                  类型 <span class="sort-icon">{{ sortIcon('file_type') }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in displayRows" :key="row.key">
                <td class="col-index">{{ index + 1 }}</td>
                <td class="col-name" :title="row.filename">{{ row.filename }}</td>
                <td class="col-pages">{{ formatPageCount(row.page_count) }}</td>
                <td class="col-type">{{ row.file_type }}</td>
              </tr>
              <tr v-if="!displayRows.length">
                <td colspan="4" class="empty-text">请上传文件后点击「开始统计」</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import * as XLSX from 'xlsx'
import { countFilePages } from '@/api/filePageCounter'

const SUPPORTED = new Set(['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'])

const fileInputRef = ref(null)
const folderInputRef = ref(null)
const dragOver = ref(false)
const counting = ref(false)
const pendingFiles = ref([])
const results = ref([])
const sortKey = ref('')
const sortAsc = ref(true)

const displayRows = computed(() => {
  if (results.value.length) {
    return sortRows(results.value.map((row, index) => ({ ...row, key: `r-${index}` })))
  }
  return pendingFiles.value.map((file, index) => ({
    key: `p-${index}-${file.name}`,
    filename: file.name,
    page_count: '待统计',
    file_type: getFileType(file.name),
  }))
})

const summaryText = computed(() => {
  const s = summarize(results.value)
  return `总页数：${s.total} | PPT: ${s.ppt} | Word: ${s.word} | PDF: ${s.pdf} | Excel: ${s.excel}`
})

function getFileType(name) {
  const ext = (name.split('.').pop() || '').toUpperCase()
  return ext || '未知'
}

function isSupportedFile(file) {
  const ext = (file.name.split('.').pop() || '').toLowerCase()
  return SUPPORTED.has(ext)
}

function addFiles(fileList) {
  const next = [...pendingFiles.value]
  for (const file of fileList) {
    if (!isSupportedFile(file)) continue
    if (next.some((item) => item.name === file.name && item.size === file.size && item.lastModified === file.lastModified)) {
      continue
    }
    next.push(file)
  }
  pendingFiles.value = next
  results.value = []
}

function onDrop(event) {
  dragOver.value = false
  const items = event.dataTransfer?.items
  if (!items?.length) {
    addFiles(event.dataTransfer?.files || [])
    return
  }
  const collected = []
  const walkers = []
  for (const item of items) {
    const entry = item.webkitGetAsEntry?.()
    if (entry) {
      walkers.push(walkEntry(entry, collected))
    } else if (item.kind === 'file') {
      const file = item.getAsFile()
      if (file) collected.push(file)
    }
  }
  Promise.all(walkers).then(() => addFiles(collected))
}

function walkEntry(entry, bucket) {
  return new Promise((resolve) => {
    if (entry.isFile) {
      entry.file((file) => {
        bucket.push(file)
        resolve()
      }, resolve)
      return
    }
    if (!entry.isDirectory) {
      resolve()
      return
    }
    const reader = entry.createReader()
    const readBatch = () => {
      reader.readEntries(async (entries) => {
        if (!entries.length) {
          resolve()
          return
        }
        await Promise.all(entries.map((child) => walkEntry(child, bucket)))
        readBatch()
      }, resolve)
    }
    readBatch()
  })
}

function onFileInput(event) {
  addFiles(event.target.files || [])
  event.target.value = ''
}

function onFolderInput(event) {
  addFiles(event.target.files || [])
  event.target.value = ''
}

async function startCounting() {
  if (!pendingFiles.value.length || counting.value) return
  counting.value = true
  try {
    const res = await countFilePages(pendingFiles.value)
    results.value = (res.data?.items || []).map((item) => ({
      filename: item.filename,
      page_count: item.page_count,
      file_type: item.file_type,
    }))
  } catch (error) {
    alert(error.response?.data?.detail || error.message || '统计失败，请稍后重试')
  } finally {
    counting.value = false
  }
}

function clearAll() {
  pendingFiles.value = []
  results.value = []
  sortKey.value = ''
  sortAsc.value = true
}

function formatPageCount(value) {
  if (typeof value === 'number') return value
  return value ?? 'N/A'
}

function summarize(items) {
  const summary = { total: 0, pdf: 0, word: 0, ppt: 0, excel: 0 }
  for (const item of items) {
    const value = item.page_count
    if (typeof value !== 'number') continue
    summary.total += value
    const type = (item.file_type || '').toUpperCase()
    if (type === 'PDF') summary.pdf += value
    else if (type === 'DOC' || type === 'DOCX') summary.word += value
    else if (type === 'PPT' || type === 'PPTX') summary.ppt += value
    else if (type === 'XLS' || type === 'XLSX') summary.excel += value
  }
  return summary
}

function toggleSort(key) {
  if (sortKey.value === key) {
    sortAsc.value = !sortAsc.value
  } else {
    sortKey.value = key
    sortAsc.value = key !== 'page_count'
  }
}

function sortIcon(key) {
  if (sortKey.value !== key) return '↕'
  return sortAsc.value ? '↑' : '↓'
}

function sortRows(rows) {
  if (!sortKey.value) return rows
  const key = sortKey.value
  const asc = sortAsc.value
  return [...rows].sort((a, b) => {
    let va = a[key]
    let vb = b[key]
    if (key === 'page_count') {
      va = typeof va === 'number' ? va : -1
      vb = typeof vb === 'number' ? vb : -1
      return asc ? va - vb : vb - va
    }
    va = String(va || '').toLowerCase()
    vb = String(vb || '').toLowerCase()
    if (va === vb) return 0
    return asc ? (va > vb ? 1 : -1) : (va > vb ? -1 : 1)
  })
}

function exportTable() {
  if (!results.value.length) return
  const rows = sortRows(results.value.map((row, index) => ({ ...row, key: index })))
  const sheetData = [
    ['序号', '文件名', '页数', '类型'],
    ...rows.map((row, index) => [
      index + 1,
      row.filename,
      formatPageCount(row.page_count),
      row.file_type,
    ]),
  ]
  const sheet = XLSX.utils.aoa_to_sheet(sheetData)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, sheet, '页数统计')
  XLSX.writeFile(wb, `文件页数统计_${new Date().toISOString().slice(0, 10)}.xlsx`)
}
</script>

<style scoped>
.file-page-counter .container {
  max-width: 1200px;
  margin: 0 auto;
}

.drop-zone {
  margin-bottom: 16px;
  padding: 48px 24px;
  text-align: center;
  border: 2px dashed #cbd5e1;
  background: #f8fafc;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.drop-zone--active,
.drop-zone:hover {
  border-color: #2563eb;
  background: #eff6ff;
}

.drop-zone__title {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}

.drop-zone__hint {
  margin: 0;
  color: #64748b;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

.hidden-input {
  display: none;
}

.table-card {
  padding: 0;
  overflow: hidden;
}

.summary-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.summary-bar__pending {
  font-size: 14px;
  font-weight: 500;
  color: #64748b;
}

.table-wrap {
  overflow: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #edf2f7;
  text-align: center;
}

.data-table th {
  background: #2563eb;
  color: #fff;
  font-weight: 600;
}

.sortable-th {
  cursor: pointer;
  user-select: none;
}

.sort-icon {
  margin-left: 4px;
  font-size: 12px;
  opacity: 0.85;
}

.col-index {
  width: 72px;
}

.col-pages {
  width: 120px;
}

.col-type {
  width: 120px;
}

.col-name {
  text-align: left;
  max-width: 520px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-text {
  padding: 40px 16px;
  color: #94a3b8;
}

@media (max-width: 768px) {
  .drop-zone {
    padding: 32px 16px;
  }

  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
