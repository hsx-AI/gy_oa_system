<template>
  <div class="yggl-fill-page">
    <div class="container">
      <header class="page-header">
        <div class="header-content">
          <div class="header-info">
            <h1 class="header-title">主表批量填充</h1>
            <p class="header-subtitle">按 Excel 上传：A 列为身份证号（用于匹配），B 列为要填充的值。仅系统管理员（webconfig.admin1）可操作。</p>
          </div>
        </div>
      </header>

      <div v-if="!canAccess" class="card no-permission">
        <p>您暂无权限访问此页面，仅系统管理员（webconfig.admin1 对应用户）可操作。</p>
        <router-link to="/" class="btn btn-primary">返回首页</router-link>
      </div>

      <template v-else>
        <div class="card form-section">
          <form @submit.prevent="submit" class="fill-form">
            <div class="form-row">
              <label class="form-label">选择要填充的字段</label>
              <select v-model="selectedField" class="form-select" required>
                <option value="">-- 请选择 --</option>
                <option v-for="opt in fieldOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>
            <div class="form-row">
              <label class="form-label">选择 Excel 文件</label>
              <input
                ref="fileInputRef"
                type="file"
                accept=".xlsx,.xls"
                class="form-file"
                @change="onFileChange"
              />
              <span v-if="fileName" class="file-name">{{ fileName }}</span>
            </div>
            <div class="form-actions">
              <button type="submit" class="btn btn-primary" :disabled="uploading || !selectedField || !file">
                {{ uploading ? '上传中…' : '上传并填充' }}
              </button>
              <button type="button" class="btn btn-outline" @click="reset">重置</button>
            </div>
          </form>
        </div>

        <div v-if="result" class="card result-section" :class="result.success ? 'result-success' : 'result-error'">
          <h3 class="result-title">{{ result.success ? '执行结果' : '执行失败' }}</h3>
          <p class="result-message">{{ result.message }}</p>
          <p v-if="result.updated != null" class="result-detail">已更新：{{ result.updated }} 条</p>
          <div v-if="result.unmapped && result.unmapped.length" class="unmapped-box">
            <p class="unmapped-title">未在 yggl 中匹配到的身份证号（{{ result.unmapped.length }} 个）：</p>
            <p class="unmapped-list">{{ result.unmapped.slice(0, 20).join('、') }}{{ result.unmapped.length > 20 ? ' …' : '' }}</p>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getDbManagerPermission, getYgglFillFields, ygglFillByExcel } from '@/api/dbManager'

const canAccess = ref(false)
const fieldOptions = ref([])
const selectedField = ref('')
const file = ref(null)
const fileName = ref('')
const fileInputRef = ref(null)
const uploading = ref(false)
const result = ref(null)

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

function onFileChange(e) {
  const f = e.target.files?.[0]
  file.value = f || null
  fileName.value = f ? f.name : ''
}

function reset() {
  selectedField.value = ''
  file.value = null
  fileName.value = ''
  result.value = null
  if (fileInputRef.value) fileInputRef.value.value = ''
}

async function submit() {
  if (!selectedField.value || !file.value) return
  const name = getCurrentUser()
  if (!name) return
  uploading.value = true
  result.value = null
  try {
    const formData = new FormData()
    formData.append('field', selectedField.value)
    formData.append('file', file.value)
    const res = await ygglFillByExcel({ current_user: name }, formData)
    result.value = res?.success
      ? { success: true, message: res.message ?? '', updated: res.updated ?? 0, unmapped: res.unmapped ?? [] }
      : { success: false, message: res?.message || res?.detail || '请求失败' }
  } catch (e) {
    const msg = e.response?.data?.detail ?? e.message ?? '网络错误'
    result.value = { success: false, message: String(msg) }
  } finally {
    uploading.value = false
  }
}

onMounted(async () => {
  const name = getCurrentUser()
  if (!name) return
  try {
    const permRes = await getDbManagerPermission({ current_user: name })
    canAccess.value = !!(permRes && permRes.canAccess)
    if (!canAccess.value) return
    const listRes = await getYgglFillFields({ current_user: name })
    fieldOptions.value = listRes?.list ?? []
  } catch {
    canAccess.value = false
  }
})
</script>

<style scoped>
.yggl-fill-page { min-height: 100vh; background: var(--color-bg-layout); padding-bottom: var(--spacing-xxl); }
.card { background: var(--color-bg-container); border-radius: var(--radius-base); padding: var(--spacing-xl); margin-bottom: var(--spacing-lg); }
.no-permission { text-align: center; }
.no-permission p { margin-bottom: var(--spacing-base); }
.form-section { margin-top: 0; }
.fill-form .form-row { display: flex; align-items: center; gap: var(--spacing-base); margin-bottom: var(--spacing-lg); flex-wrap: wrap; }
.form-label { min-width: 140px; white-space: nowrap; }
.form-select { min-width: 200px; padding: var(--spacing-sm) var(--spacing-base); border: 1px solid var(--color-border-lighter); border-radius: var(--radius-base); }
.form-file { padding: var(--spacing-sm) 0; }
.file-name { margin-left: var(--spacing-sm); font-size: var(--font-size-sm); color: var(--color-text-secondary); }
.form-actions { display: flex; gap: var(--spacing-base); margin-top: var(--spacing-xl); }
.result-section { margin-top: var(--spacing-lg); }
.result-title { margin: 0 0 var(--spacing-sm); font-size: var(--font-size-lg); }
.result-message { margin: 0 0 var(--spacing-xs); }
.result-detail { margin: 0; font-size: var(--font-size-sm); color: var(--color-text-secondary); }
.result-success .result-title { color: var(--color-success, #2e7d32); }
.result-error .result-title { color: var(--color-danger, #e53935); }
.unmapped-box { margin-top: var(--spacing-base); padding: var(--spacing-base); background: var(--color-bg-spotlight); border-radius: var(--radius-base); }
.unmapped-title { margin: 0 0 var(--spacing-xs); font-size: var(--font-size-sm); }
.unmapped-list { margin: 0; font-size: var(--font-size-sm); color: var(--color-text-secondary); word-break: break-all; }
</style>
