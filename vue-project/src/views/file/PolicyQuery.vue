<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">部门制度查询</h1>
          <p class="header-subtitle">制度上传、制度查询、关键词搜索，支持 PDF、Word、Excel</p>
        </div>
        <div class="header-actions" v-if="canUpload">
          <button class="btn btn-primary" @click="showUploadModal = true">上传制度</button>
        </div>
      </div>
    </div>

    <div class="content mt-xl">
      <div class="search-bar card mb-lg">
        <input v-model="searchKeyword" type="text" placeholder="按标题模糊搜索，回车查询" class="search-input" @keyup.enter="loadList">
        <button type="button" class="btn btn-primary" @click="loadList">查询</button>
        <button type="button" class="btn btn-ai" @click="showDeepSearchModal = true">AI 深度搜索</button>
        <button type="button" class="btn" @click="searchKeyword = ''; loadList()">重置</button>
      </div>

      <div class="card">
        <div class="card-header">
          <h3>制度列表</h3>
        </div>
        <div class="card-body">
          <div v-if="loading" class="empty-text">加载中...</div>
          <div v-else-if="list.length === 0" class="empty-text">暂无制度记录</div>
          <div v-else class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>标题</th>
                  <th>发行时间</th>
                  <th>文件名</th>
                  <th>上传人</th>
                  <th>上传时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in list" :key="row.id">
                  <td>{{ row.title || '—' }}</td>
                  <td>{{ row.issue_time || '—' }}</td>
                  <td>{{ row.file_name || '—' }}</td>
                  <td>{{ row.uploader || '—' }}</td>
                  <td>{{ row.upload_time ? row.upload_time.slice(0, 16) : '—' }}</td>
                  <td class="file-actions">
                    <button type="button" class="btn-copy-small btn-preview" @click="openFile(row.id, 0)">预览</button>
                    <button type="button" class="btn-copy-small btn-download" @click="openFile(row.id, 1)">下载</button>
                    <button v-if="canUpload" type="button" class="btn-copy-small btn-delete" @click="doDelete(row.id)">删除</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="total > 0" class="table-footer">
            共 {{ total }} 条，当前页 {{ list.length }} 条
          </div>
        </div>
      </div>
    </div>

    <!-- 预览弹窗 -->
    <div v-if="showPreviewModal" class="modal-overlay preview-overlay" @click.self="closePreviewModal">
      <div class="preview-modal">
        <div class="preview-header">
          <span>文档预览</span>
          <button type="button" class="btn-close" @click="closePreviewModal">×</button>
        </div>
        <div class="preview-body">
          <div v-show="previewLoading" class="preview-loading">
            <div class="loading-spinner"></div>
            <p>正在加载中...</p>
          </div>
          <iframe
            v-show="!previewLoading"
            ref="previewIframeRef"
            class="preview-iframe"
            :src="previewUrl"
            @load="onPreviewLoad"
          ></iframe>
        </div>
      </div>
    </div>

    <!-- AI 深度搜索弹窗 -->
    <div v-if="showDeepSearchModal" class="modal-overlay preview-overlay" @click.self="closeDeepSearchModal">
      <div class="deep-search-modal">
        <div class="deep-search-header">
          <div class="deep-search-header-left">
            <span class="deep-search-title">AI 深度搜索</span>
            <span class="deep-search-badge">向量检索</span>
            <span class="deep-search-desc">根据语义相似度深度搜索文件内容</span>
          </div>
          <button type="button" class="btn-close" @click="closeDeepSearchModal">×</button>
        </div>
        <div class="deep-search-body">
          <div class="deep-search-input-wrap">
            <input
              v-model="deepSearchKeyword"
              type="text"
              placeholder="用自然语言描述您要查找的内容，如：员工请假相关规定..."
              class="deep-search-input"
              @keyup.enter="doDeepSearch"
            >
            <button type="button" class="btn btn-ai btn-search" @click="doDeepSearch" :disabled="deepSearchLoading || !deepSearchKeyword?.trim()">
              {{ deepSearchLoading ? '搜索中...' : '搜索' }}
            </button>
          </div>
          <div class="deep-search-results">
            <div v-if="!deepSearchDone" class="deep-search-empty">
              <p>输入问题后点击搜索，将基于文档内容的语义理解进行智能匹配</p>
            </div>
            <div v-else-if="deepSearchLoading" class="deep-search-loading">
              <div class="loading-spinner"></div>
              <p>正在智能检索...</p>
            </div>
            <div v-else-if="deepSearchList.length === 0" class="deep-search-empty">
              <p>未找到相关制度，可尝试换一种表述</p>
            </div>
            <div v-else class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>标题</th>
                    <th>匹配切片</th>
                    <th>发行时间</th>
                    <th>文件名</th>
                    <th>相关性</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in deepSearchList" :key="row.id">
                    <td>{{ row.title || '—' }}</td>
                    <td class="snippet-cell" :title="row.snippet">{{ row.snippet || '—' }}</td>
                    <td>{{ row.issue_time || '—' }}</td>
                    <td>{{ row.file_name || '—' }}</td>
                    <td>{{ row.score != null ? (Math.round(row.score * 100) + '%') : '—' }}</td>
                    <td class="file-actions">
                      <button type="button" class="btn-copy-small btn-preview" @click="openFile(row.id, 0)">预览</button>
                      <button type="button" class="btn-copy-small btn-download" @click="openFile(row.id, 1)">下载</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 上传弹窗 -->
    <div v-if="showUploadModal" class="modal-overlay" @click.self="closeUploadModal">
      <div class="modal-content">
        <h2>上传制度</h2>
        <form @submit.prevent="submitUpload">
          <div class="form-group">
            <label>制度标题 <span class="required">*</span></label>
            <input v-model="uploadForm.title" type="text" placeholder="请输入制度标题" required>
          </div>
          <div class="form-group">
            <label>发行时间 <span class="required">*</span></label>
            <input v-model="uploadForm.issue_time" type="date" required>
          </div>
          <div class="form-group">
            <label>备注</label>
            <input v-model="uploadForm.remark" type="text" placeholder="选填">
          </div>
          <div class="form-group">
            <label>选择文件 <span class="required">*</span></label>
            <input
              ref="fileInputRef"
              type="file"
              accept=".pdf,.doc,.docx,.xls,.xlsx"
              @change="onFileSelected"
            >
            <p class="form-hint">支持 PDF、Word(.doc/.docx)、Excel(.xls/.xlsx)</p>
            <p v-if="selectedFile" class="selected-file">{{ selectedFile.name }}</p>
          </div>
          <div class="form-actions">
            <button type="button" @click="closeUploadModal">取消</button>
            <button type="submit" class="btn-primary" :disabled="uploadLoading || !selectedFile">
              {{ uploadLoading ? '上传中...' : '上传' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getPolicyList, getPolicyUploadPermission, uploadPolicy, deletePolicy, getPolicyFileUrl, vectorSearchPolicy } from '@/api/departmentPolicy'

const list = ref([])
const canUpload = ref(false)
const loading = ref(false)
const total = ref(0)
const searchKeyword = ref('')
const showUploadModal = ref(false)
const uploadLoading = ref(false)
const selectedFile = ref(null)
const fileInputRef = ref(null)
const showPreviewModal = ref(false)
const previewLoading = ref(false)
const previewUrl = ref('')
const previewIframeRef = ref(null)
const showDeepSearchModal = ref(false)
const deepSearchKeyword = ref('')
const deepSearchLoading = ref(false)
const deepSearchDone = ref(false)
const deepSearchList = ref([])

const uploadForm = ref({
  title: '',
  issue_time: '',
  remark: ''
})

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

async function loadList() {
  loading.value = true
  try {
    const params = { page: 1, page_size: 100 }
    if ((searchKeyword.value || '').trim()) params.keyword = searchKeyword.value.trim()
    const res = await getPolicyList(params)
    list.value = (res.list || []).filter(Boolean)
    total.value = res.total ?? list.value.length
  } catch {
    list.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function onFileSelected(e) {
  const file = e.target.files?.[0]
  selectedFile.value = file || null
  if (file?.name) {
    const base = file.name.replace(/\.[^/.]+$/, '')
    uploadForm.value.title = base
  }
}

function closeUploadModal() {
  showUploadModal.value = false
  uploadForm.value = { title: '', issue_time: '', remark: '' }
  selectedFile.value = null
  fileInputRef.value && (fileInputRef.value.value = '')
}

async function submitUpload() {
  if (!uploadForm.value.title?.trim()) {
    alert('请输入制度标题')
    return
  }
  if (!selectedFile.value) {
    alert('请选择文件')
    return
  }
  const allowed = ['.pdf', '.doc', '.docx', '.xls', '.xlsx']
  const ok = allowed.some(e => (selectedFile.value.name || '').toLowerCase().endsWith(e))
  if (!ok) {
    alert('仅支持 PDF、Word、Excel 格式')
    return
  }
  uploadLoading.value = true
  try {
    if (!uploadForm.value.issue_time?.trim()) {
      alert('请选择发行时间')
      return
    }
    await uploadPolicy({
      title: uploadForm.value.title.trim(),
      issue_time: uploadForm.value.issue_time.trim(),
      remark: (uploadForm.value.remark || '').trim(),
      uploader: getCurrentUser(),
      file: selectedFile.value
    })
    alert('上传成功')
    closeUploadModal()
    await loadList()
  } catch (err) {
    alert(err.response?.data?.detail || err.message || '上传失败')
  } finally {
    uploadLoading.value = false
  }
}

function openFile(id, download) {
  const url = getPolicyFileUrl(id, download)
  if (download === 1) {
    window.open(url, '_blank', 'noopener')
    return
  }
  previewUrl.value = url
  previewLoading.value = true
  showPreviewModal.value = true
}

function closePreviewModal() {
  showPreviewModal.value = false
  previewUrl.value = ''
  previewLoading.value = false
  previewIframeRef.value = null
}

function closeDeepSearchModal() {
  showDeepSearchModal.value = false
  deepSearchKeyword.value = ''
  deepSearchDone.value = false
  deepSearchList.value = []
}

async function doDeepSearch() {
  const q = (deepSearchKeyword.value || '').trim()
  if (!q) return
  deepSearchLoading.value = true
  deepSearchDone.value = true
  try {
    const res = await vectorSearchPolicy({ query: q, top_k: 20 })
    deepSearchList.value = (res.list || []).filter(Boolean)
  } catch (err) {
    deepSearchList.value = []
    alert(err.response?.data?.detail || err.message || '深度搜索失败')
  } finally {
    deepSearchLoading.value = false
  }
}

function onPreviewLoad() {
  previewLoading.value = false
}

async function doDelete(id) {
  if (!confirm('确定删除该制度？')) return
  try {
    await deletePolicy(id, getCurrentUser())
    alert('已删除')
    await loadList()
  } catch (err) {
    alert(err.response?.data?.detail || err.message || '删除失败')
  }
}

async function loadUploadPermission() {
  const name = getCurrentUser()
  if (!name) return
  try {
    const res = await getPolicyUploadPermission({ name })
    canUpload.value = !!(res && res.canUpload)
  } catch {
    canUpload.value = false
  }
}

onMounted(() => {
  loadUploadPermission()
  loadList()
})
</script>

<style scoped>
.page-container {
  width: 100%;
  max-width: none;
  margin: 0;
  padding-top: 0;
  padding-bottom: var(--spacing-xl);
  padding-left: 0;
  padding-right: 0;
}

.search-bar {
  display: flex;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  border-radius: var(--radius-md);
}

.search-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
}

.card {
  background: white;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-lighter);
}

.card-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-lighter);
}

.card-body {
  padding: var(--spacing-lg);
}

.empty-text {
  text-align: center;
  color: var(--color-text-secondary);
  padding: var(--spacing-xxl) 0;
}

.table-wrap {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.data-table th,
.data-table td {
  padding: 10px 12px;
  border: 1px solid var(--color-border-lighter);
  text-align: left;
}

.data-table th {
  background: var(--color-bg-lighter, #f5f5f5);
  font-weight: 600;
}

.file-actions {
  white-space: nowrap;
}
.file-actions .btn-copy-small {
  margin-right: 4px;
}

.btn-preview {
  color: #1890ff;
  border-color: #1890ff;
  background: rgba(24, 144, 255, 0.06);
}
.btn-preview:hover {
  background: rgba(24, 144, 255, 0.15);
}

.btn-download {
  color: #52c41a;
  border-color: #52c41a;
  background: rgba(82, 196, 26, 0.06);
}
.btn-download:hover {
  background: rgba(82, 196, 26, 0.15);
}

.btn-delete {
  color: var(--color-danger, #c00);
  border-color: var(--color-danger, #c00);
  background: rgba(204, 0, 0, 0.06);
}
.btn-delete:hover {
  background: rgba(204, 0, 0, 0.15);
}

.btn-copy-small {
  padding: 2px 8px;
  font-size: 0.8rem;
  border-radius: 4px;
  border: 1px solid var(--color-border-base);
  background: #fff;
  cursor: pointer;
}

.table-footer {
  margin-top: var(--spacing-md);
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.mb-lg {
  margin-bottom: var(--spacing-lg);
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-content {
  background: white;
  padding: var(--spacing-xl);
  border-radius: var(--radius-md);
  width: 500px;
  max-width: 90%;
}

.form-group {
  margin-bottom: var(--spacing-lg);
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-xs);
  font-weight: 500;
}

.form-group input[type="text"],
.form-group input[type="date"],
.form-group input[type="file"] {
  width: 100%;
  padding: 8px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
}

.form-hint,
.selected-file {
  margin-top: var(--spacing-xs);
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.required {
  color: var(--color-danger, #c00);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
  margin-top: var(--spacing-xl);
}

button {
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-base);
  cursor: pointer;
  background: white;
}

.btn-primary {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

/* AI 深度搜索按钮 - 显眼渐变色 */
.btn-ai {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 40%, #f093fb 100%);
  color: white;
  border: none;
  font-weight: 600;
}
.btn-ai:hover {
  background: linear-gradient(135deg, #5568d3 0%, #6a4190 40%, #e07de8 100%);
  color: white;
}

/* 深度搜索弹窗 */
.deep-search-modal {
  width: 90%;
  max-width: 900px;
  height: 80vh;
  background: white;
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 12px 48px rgba(102, 126, 234, 0.25);
  border: 1px solid rgba(102, 126, 234, 0.2);
}
.deep-search-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  padding: var(--spacing-lg) var(--spacing-xl);
  background: linear-gradient(90deg, rgba(102, 126, 234, 0.08) 0%, rgba(240, 147, 251, 0.06) 100%);
  border-bottom: 1px solid var(--color-border-lighter);
}
.deep-search-header-left {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--spacing-sm);
}
.deep-search-desc {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}
.deep-search-title {
  font-size: 1.125rem;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea, #764ba2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.deep-search-badge {
  font-size: 0.75rem;
  padding: 2px 8px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border-radius: 999px;
}
.deep-search-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: var(--spacing-lg);
}
.deep-search-input-wrap {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}
.deep-search-input {
  flex: 1;
  padding: 10px 16px;
  border: 2px solid rgba(102, 126, 234, 0.3);
  border-radius: var(--radius-md);
  font-size: 0.95rem;
}
.deep-search-input:focus {
  outline: none;
  border-color: #667eea;
}
.btn-search {
  flex-shrink: 0;
}
.deep-search-results {
  flex: 1;
  overflow: auto;
  background: var(--color-bg-lighter, #f8f9fa);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
}
.snippet-cell {
  max-width: 320px;
  color: var(--color-text-secondary);
  font-size: 0.85rem;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.deep-search-empty,
.deep-search-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: var(--color-text-secondary);
  text-align: center;
}
.deep-search-loading {
  gap: var(--spacing-lg);
}

/* 预览弹窗 */
.preview-overlay {
  z-index: 200;
}
.preview-modal {
  width: 90%;
  max-width: 960px;
  height: 85vh;
  background: white;
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}
.preview-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-lighter);
  font-weight: 600;
}
.btn-close {
  width: 32px;
  height: 32px;
  padding: 0;
  font-size: 24px;
  line-height: 1;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
}
.btn-close:hover {
  color: var(--color-text-primary);
}
.preview-body {
  flex: 1;
  position: relative;
  min-height: 0;
}
.preview-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-lg);
  background: var(--color-bg-lighter, #f8f9fa);
}
.preview-loading p {
  margin: 0;
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
}
.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-border-lighter);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.preview-iframe {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
}
</style>
