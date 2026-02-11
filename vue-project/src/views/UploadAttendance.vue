<template>
  <div class="upload-page">
    <!-- 页面头部 -->
    <div class="page-header-bar">
      <div class="container">
        <div class="header-bar-content">
          <div>
            <h1 class="page-title">打卡数据上传</h1>
            <p class="page-subtitle">批量导入考勤打卡数据，支持 Excel 和 CSV 格式</p>
          </div>
        </div>
      </div>
    </div>

    <div class="container">
      <!-- 上传区域 -->
      <div class="upload-section card mt-xl">
        <div class="upload-header">
          <h3 class="section-title">文件上传</h3>
          <button class="btn-text" @click="downloadTemplate">
            <svg class="icon-sm mr-xs" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
            </svg>
            下载模板
          </button>
        </div>

        <div class="upload-area" :class="{ 'drag-over': isDragOver }" 
             @dragover.prevent="handleDragOver" 
             @dragleave="handleDragLeave" 
             @drop.prevent="handleDrop">
          <input
            ref="fileInput"
            type="file"
            accept=".xlsx,.xls,.csv"
            @change="handleFileSelect"
            style="display: none"
          />
          
          <div v-if="!selectedFile" class="upload-placeholder" @click="$refs.fileInput.click()">
            <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <div class="upload-text">
              <div class="upload-main-text">点击或拖拽文件到此区域上传</div>
              <div class="upload-sub-text">支持 .xlsx、.xls、.csv 格式，单个文件不超过 10MB</div>
            </div>
          </div>

          <div v-else class="file-info">
            <div class="file-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
                <polyline points="13 2 13 9 20 9" />
              </svg>
            </div>
            <div class="file-details">
              <div class="file-name">{{ selectedFile.name }}</div>
              <div class="file-meta">
                <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
                <span class="file-status" :class="`status-${uploadStatus}`">
                  {{ uploadStatusText }}
                </span>
              </div>
              <div v-if="uploadError" class="file-error">
                {{ uploadError }}
              </div>
              <div v-if="uploadProgress > 0 && uploadProgress < 100" class="file-progress">
                <div class="progress-bar">
                  <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
                </div>
                <span class="progress-text">{{ uploadProgress }}%</span>
              </div>
            </div>
            <button class="btn-text" @click="removeFile">
              <svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        <div v-if="selectedFile && uploadStatus === 'ready'" class="upload-actions">
          <button class="btn btn-primary" @click="handleUpload" :disabled="uploading">
            <svg class="icon-sm mr-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            {{ uploading ? '上传中...' : '开始上传' }}
          </button>
          <button class="btn btn-default" @click="removeFile">取消</button>
        </div>
      </div>

      <!-- 上传说明 -->
      <div class="instructions-section mt-xl">
        <h3 class="section-title mb-lg">上传说明</h3>
        <div class="instructions-grid grid-2">
          <div class="instruction-card card">
            <div class="instruction-icon" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10 9 9 9 8 9" />
              </svg>
            </div>
            <div class="instruction-content">
              <h4 class="instruction-title">文件格式要求</h4>
              <ul class="instruction-list">
                <li>支持 Excel 格式（.xlsx、.xls）</li>
                <li>支持 CSV 格式（.csv）</li>
                <li>文件大小不超过 10MB</li>
                <li>建议使用提供的模板文件</li>
              </ul>
            </div>
          </div>

          <div class="instruction-card card">
            <div class="instruction-icon" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="9 11 12 14 22 4" />
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
              </svg>
            </div>
            <div class="instruction-content">
              <h4 class="instruction-title">数据字段说明</h4>
              <ul class="instruction-list">
                <li>必填：日期、工号、姓名</li>
                <li>可选：部门、上班时间、下班时间</li>
                <li>日期格式：YYYY-MM-DD</li>
                <li>时间格式：HH:MM:SS</li>
              </ul>
            </div>
          </div>

          <div class="instruction-card card">
            <div class="instruction-icon" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            </div>
            <div class="instruction-content">
              <h4 class="instruction-title">注意事项</h4>
              <ul class="instruction-list">
                <li>请确保数据格式正确</li>
                <li>避免空白行和无效数据</li>
                <li>重复数据将被自动过滤</li>
                <li>上传后可在记录页面查看</li>
              </ul>
            </div>
          </div>

          <div class="instruction-card card">
            <div class="instruction-icon" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            </div>
            <div class="instruction-content">
              <h4 class="instruction-title">常见问题</h4>
              <ul class="instruction-list">
                <li>上传失败？检查文件格式和大小</li>
                <li>数据未显示？刷新页面重试</li>
                <li>格式错误？下载模板参考</li>
                <li>其他问题？联系技术支持</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- 上传历史 -->
      <div class="history-section mt-xl">
        <h3 class="section-title mb-lg">上传历史</h3>
        <div class="history-list card">
          <div v-if="uploadHistory.length === 0" class="empty-state">
            <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div class="empty-text">暂无上传记录</div>
          </div>
          <div v-else class="history-items">
            <div v-for="item in uploadHistory" :key="item.id" class="history-item">
              <div class="history-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
                  <polyline points="13 2 13 9 20 9" />
                </svg>
              </div>
              <div class="history-info">
                <div class="history-name">{{ item.filename }}</div>
                <div class="history-meta">
                  <span>{{ item.date }}</span>
                  <span class="meta-divider">·</span>
                  <span>{{ item.records }} 条记录</span>
                  <span class="meta-divider">·</span>
                  <span :class="`text-${item.statusType}`">{{ item.status }}</span>
                </div>
              </div>
              <button class="btn-text btn-sm">查看详情</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { uploadAttendanceExcel } from '@/api/attendance'

const fileInput = ref(null)
const selectedFile = ref(null)
const isDragOver = ref(false)
const uploading = ref(false)
const uploadStatus = ref('ready') // ready, uploading, success, error
const uploadProgress = ref(0)
const uploadError = ref('') // 存储上传错误信息

const uploadHistory = ref([])

const uploadStatusText = computed(() => {
  const statusMap = {
    ready: '准备上传',
    uploading: '上传中',
    success: '上传成功',
    error: '上传失败'
  }
  return statusMap[uploadStatus.value]
})

const handleDragOver = () => {
  isDragOver.value = true
}

const handleDragLeave = () => {
  isDragOver.value = false
}

const handleDrop = (e) => {
  isDragOver.value = false
  const files = e.dataTransfer.files
  if (files.length > 0) {
    selectedFile.value = files[0]
    uploadStatus.value = 'ready'
    uploadError.value = ''
  }
}

const handleFileSelect = (e) => {
  const files = e.target.files
  if (files.length > 0) {
    selectedFile.value = files[0]
    uploadStatus.value = 'ready'
    uploadError.value = ''
  }
}

const removeFile = () => {
  selectedFile.value = null
  uploadStatus.value = 'ready'
  uploadProgress.value = 0
  uploadError.value = ''
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const handleUpload = async () => {
  if (!selectedFile.value) return
  
  uploading.value = true
  uploadStatus.value = 'uploading'
  uploadProgress.value = 0
  uploadError.value = ''
  
  // 模拟进度（因为实际上传可能没有进度事件）
  const progressInterval = setInterval(() => {
    if (uploadProgress.value < 90) {
      uploadProgress.value += 10
    }
  }, 200)
  
  try {
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
    const uploader = (userInfo.name || userInfo.userName || '').trim()
    const response = await uploadAttendanceExcel(selectedFile.value, uploader)
    
    clearInterval(progressInterval)
    uploadProgress.value = 100
    uploadStatus.value = 'success'
    
    // 添加到历史记录（使用真实返回数据）
    uploadHistory.value.unshift({
      id: Date.now(),
      filename: selectedFile.value.name,
      date: new Date().toLocaleString('zh-CN'),
      records: response.records_count || 0,
      successCount: response.success_count || 0,
      failCount: response.fail_count || 0,
      status: `成功导入 ${response.success_count || 0} 条`,
      statusType: 'success'
    })
    
    // 显示成功提示
    console.log('上传成功:', response.message)
    alert(`上传成功！\n${response.message}\n成功: ${response.success_count} 条\n失败: ${response.fail_count} 条`)
    
  } catch (error) {
    clearInterval(progressInterval)
    uploadStatus.value = 'error'
    uploadProgress.value = 0
    const msg = error.response?.data?.detail || error.message || '上传失败，请检查文件格式'
    uploadError.value = msg
    
    // 添加失败记录
    uploadHistory.value.unshift({
      id: Date.now(),
      filename: selectedFile.value.name,
      date: new Date().toLocaleString('zh-CN'),
      records: 0,
      status: '上传失败',
      statusType: 'error'
    })
    
    console.error('上传失败:', error)
    alert(`上传失败: ${error.message || '请检查文件格式和网络连接'}`)
    
  } finally {
    uploading.value = false
  }
}

const downloadTemplate = () => {
  // TODO: 实现下载模板功能
  console.log('下载模板')
  alert('模板下载功能暂未实现')
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}
</script>

<style scoped>
.upload-page {
  min-height: 100vh;
  background: var(--color-bg-layout);
  padding-bottom: var(--spacing-xxl);
}

.header-bar-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 上传区域 */
.upload-section {
  padding: var(--spacing-xl);
  border: 1px solid var(--color-border-lighter);
}

.upload-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
}

.upload-area {
  border: 2px dashed var(--color-border-base);
  border-radius: var(--radius-md);
  padding: var(--spacing-xxl);
  transition: all var(--transition-base) var(--transition-ease);
  background: var(--color-bg-spotlight);
}

.upload-area.drag-over {
  border-color: var(--color-primary);
  background: var(--color-primary-lightest);
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-lg);
  cursor: pointer;
}

.upload-icon {
  width: 64px;
  height: 64px;
  color: var(--color-text-tertiary);
}

.upload-text {
  text-align: center;
}

.upload-main-text {
  font-size: var(--font-size-md);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
  margin-bottom: var(--spacing-xs);
}

.upload-sub-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.file-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-base);
  padding: var(--spacing-lg);
  background: var(--color-bg-container);
  border-radius: var(--radius-base);
}

.file-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-base);
  background: var(--color-primary-lightest);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.file-icon svg {
  width: 24px;
  height: 24px;
}

.file-details {
  flex: 1;
}

.file-name {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
}

.file-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.file-status {
  font-weight: var(--font-weight-medium);
}

.status-ready { color: var(--color-text-secondary); }
.status-uploading { color: var(--color-info); }
.status-success { color: var(--color-success); }
.status-error { color: var(--color-error); }

.file-error {
  color: var(--color-error);
  font-size: var(--font-size-sm);
  margin-top: var(--spacing-xs);
}

.file-progress {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: var(--color-border-lighter);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  transition: width var(--transition-base) var(--transition-ease);
}

.progress-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-family-code);
  min-width: 40px;
  text-align: right;
}

.upload-actions {
  display: flex;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-lg);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-border-lighter);
}

/* 说明卡片 */
.instructions-grid {
  margin-top: var(--spacing-lg);
}

.instruction-card {
  padding: var(--spacing-xl);
  border: 1px solid var(--color-border-lighter);
  display: flex;
  gap: var(--spacing-base);
}

.instruction-icon {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.instruction-icon svg {
  width: 28px;
  height: 28px;
  color: white;
}

.instruction-content {
  flex: 1;
}

.instruction-title {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-base);
}

.instruction-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.instruction-list li {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  padding-left: var(--spacing-base);
  position: relative;
}

.instruction-list li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: var(--color-primary);
}

/* 上传历史 */
.history-list {
  padding: 0;
  border: 1px solid var(--color-border-lighter);
  overflow: hidden;
}

.empty-state {
  padding: var(--spacing-xxxl);
  text-align: center;
}

.empty-icon {
  width: 64px;
  height: 64px;
  color: var(--color-text-quaternary);
  margin: 0 auto var(--spacing-base);
}

.empty-text {
  font-size: var(--font-size-base);
  color: var(--color-text-tertiary);
}

.history-items {
  display: flex;
  flex-direction: column;
}

.history-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-base);
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
  transition: background-color var(--transition-base) var(--transition-ease);
}

.history-item:last-child {
  border-bottom: none;
}

.history-item:hover {
  background: var(--color-bg-spotlight);
}

.history-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-base);
  background: var(--color-bg-spotlight);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.history-icon svg {
  width: 20px;
  height: 20px;
}

.history-info {
  flex: 1;
}

.history-name {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
}

.history-meta {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.meta-divider {
  margin: 0 var(--spacing-xs);
}

/* 响应式 */
@media (max-width: 768px) {
  .upload-section {
    padding: var(--spacing-base);
  }
  
  .upload-area {
    padding: var(--spacing-lg);
  }
  
  .upload-icon {
    width: 48px;
    height: 48px;
  }
  
  .instructions-grid {
    grid-template-columns: 1fr;
  }
  
  .history-item {
    flex-wrap: wrap;
  }
}
</style>
