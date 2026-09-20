<template>
  <div class="oo-editor-page">
    <div class="oo-editor-toolbar">
      <button type="button" class="oo-back-btn" @click="goBack">返回</button>
      <div class="oo-editor-title">
        <strong>{{ fileName || '共享文档编辑' }}</strong>
        <span v-if="documentKey" class="oo-meta">key: {{ documentKey }}</span>
        <span v-if="version != null" class="oo-meta">v{{ version }}</span>
      </div>
    </div>

    <div v-if="errorMessage" class="oo-error">
      <p>{{ errorMessage }}</p>
      <button type="button" class="oo-retry-btn" @click="bootstrap">重试</button>
    </div>
    <div v-else-if="loading" class="oo-loading">正在加载 ONLYOFFICE 编辑器…</div>
    <div id="onlyoffice-editor" class="oo-editor-host"></div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getEditorConfig } from '@/api/sharedFiles'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const errorMessage = ref('')
const fileName = ref('')
const documentKey = ref('')
const version = ref(null)

let editorInstance = null
let loadedScriptUrl = ''

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/')
}

function destroyEditor() {
  try {
    if (editorInstance && typeof editorInstance.destroyEditor === 'function') {
      editorInstance.destroyEditor()
    }
  } catch (e) {
    console.warn('destroy ONLYOFFICE editor failed', e)
  }
  editorInstance = null
  const host = document.getElementById('onlyoffice-editor')
  if (host) host.innerHTML = ''
}

function loadOnlyOfficeApi(documentServerUrl) {
  const base = String(documentServerUrl || '').replace(/\/$/, '')
  if (!base) {
    return Promise.reject(new Error('未返回 Document Server 地址'))
  }
  const src = `${base}/web-apps/apps/api/documents/api.js`
  if (window.DocsAPI && window.DocsAPI.DocEditor && loadedScriptUrl === src) {
    return Promise.resolve()
  }
  return new Promise((resolve, reject) => {
    const existing = document.querySelector('script[data-onlyoffice-api="1"]')
    if (existing && window.DocsAPI && window.DocsAPI.DocEditor) {
      loadedScriptUrl = existing.src
      resolve()
      return
    }
    if (existing) existing.remove()
    const script = document.createElement('script')
    script.src = src
    script.async = true
    script.dataset.onlyofficeApi = '1'
    script.onload = () => {
      loadedScriptUrl = src
      if (window.DocsAPI && window.DocsAPI.DocEditor) resolve()
      else reject(new Error('ONLYOFFICE DocsAPI 加载失败'))
    }
    script.onerror = () => reject(new Error(`无法加载 ONLYOFFICE API：${src}`))
    document.head.appendChild(script)
  })
}

function humanizeError(err) {
  const detail = err && err.response && err.response.data && err.response.data.detail
  const msg = (typeof detail === 'string' && detail)
    || (err && (err.message || err.detail || err.toString()))
    || '未知错误'
  if (/未配置|ONLYOFFICE_URL|PUBLIC_API|JWT_SECRET/i.test(msg)) {
    return `ONLYOFFICE 配置不完整：${msg}`
  }
  if (/403|没有权限|外部门/i.test(msg)) {
    return '没有权限访问共享文档'
  }
  if (/404|不存在/i.test(msg)) {
    return '文件不存在或已删除'
  }
  if (/Network|network|Failed to fetch|timeout|Request failed/i.test(msg)) {
    return detail || '网络异常，无法连接后端或 ONLYOFFICE 服务'
  }
  return msg
}

async function bootstrap() {
  destroyEditor()
  loading.value = true
  errorMessage.value = ''
  const fileId = Number(route.params.id)
  if (!Number.isFinite(fileId) || fileId <= 0) {
    loading.value = false
    errorMessage.value = '无效的文件 ID'
    return
  }
  try {
    const res = await getEditorConfig(fileId)
    const documentServerUrl = res.documentServerUrl
    const config = res.config
    fileName.value = (res.file && res.file.name) || (config && config.document && config.document.title) || ''
    documentKey.value = (res.file && res.file.document_key) || (config && config.document && config.document.key) || ''
    version.value = res.file && res.file.version != null ? res.file.version : null

    await loadOnlyOfficeApi(documentServerUrl)
    if (!window.DocsAPI || !window.DocsAPI.DocEditor) {
      throw new Error('ONLYOFFICE DocsAPI 不可用，请检查 Document Server 是否启动')
    }
    editorInstance = new window.DocsAPI.DocEditor('onlyoffice-editor', config)
    loading.value = false
  } catch (err) {
    console.error(err)
    loading.value = false
    errorMessage.value = humanizeError(err)
  }
}

onMounted(() => {
  bootstrap()
})

onBeforeUnmount(() => {
  destroyEditor()
})
</script>

<style scoped>
.oo-editor-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px);
  min-height: 480px;
  background: #f5f7fa;
}
.oo-editor-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}
.oo-back-btn,
.oo-retry-btn {
  border: 1px solid #d1d5db;
  background: #fff;
  border-radius: 6px;
  padding: 6px 12px;
  cursor: pointer;
}
.oo-editor-title {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 10px;
  font-size: 14px;
  color: #111827;
}
.oo-meta {
  color: #6b7280;
  font-size: 12px;
}
.oo-loading,
.oo-error {
  padding: 24px 16px;
  color: #374151;
}
.oo-error {
  color: #b91c1c;
}
.oo-editor-host {
  flex: 1;
  min-height: 0;
  width: 100%;
}
</style>
