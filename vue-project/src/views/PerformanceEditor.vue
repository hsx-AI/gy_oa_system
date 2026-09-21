<template>
  <div class="oo-editor-page">
    <div class="oo-editor-toolbar">
      <button type="button" class="oo-back-btn" @click="goBack">返回绩效统计</button>
      <div class="oo-editor-title">
        <strong>{{ fileName || '绩效统计' }}</strong>
        <span class="oo-meta">{{ hint }}</span>
      </div>
    </div>
    <div v-if="errorMessage" class="oo-error">
      <p>{{ errorMessage }}</p>
      <button type="button" class="oo-retry-btn" @click="bootstrap">重试</button>
    </div>
    <div v-else-if="loading" class="oo-loading">正在加载…</div>
    <div id="performance-onlyoffice" class="oo-editor-host"></div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getPerformanceOnlineEditorConfig } from '@/api/performance'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const errorMessage = ref('')
const fileName = ref('')
let editorInstance = null
let loadedScriptUrl = ''

const currentUser = computed(() => {
  try {
    const user = JSON.parse(localStorage.getItem('userInfo') || '{}')
    return (user.name || user.userName || '').trim()
  } catch (e) {
    return ''
  }
})

const hint = computed(() => route.query.scope === 'summary' ? '汇总表可以看全员。只有你自己的行和会议纪实可以编辑，排名按合计自动计算。' : '这里只有你自己的绩效行和会议纪实。公式列不能改。')

function goBack() { router.push('/performance') }

function destroyEditor() {
  try {
    if (editorInstance && typeof editorInstance.destroyEditor === 'function') editorInstance.destroyEditor()
  } catch (e) { /* ignore */ }
  editorInstance = null
  const host = document.getElementById('performance-onlyoffice')
  if (host) host.innerHTML = ''
}

function loadOnlyOfficeApi(documentServerUrl) {
  const base = String(documentServerUrl || '').replace(/\/$/, '')
  const src = base + '/web-apps/apps/api/documents/api.js'
  if (window.DocsAPI && window.DocsAPI.DocEditor && loadedScriptUrl === src) return Promise.resolve()
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
      else reject(new Error('ONLYOFFICE DocsAPI missing'))
    }
    script.onerror = () => reject(new Error('ONLYOFFICE API failed'))
    document.head.appendChild(script)
  })
}

function detailOf(err) {
  const detail = err && err.response && err.response.data && err.response.data.detail
  return (typeof detail === 'string' && detail) || (err && err.message) || '操作失败'
}

async function bootstrap() {
  destroyEditor()
  loading.value = true
  errorMessage.value = ''
  const docId = Number(route.query.docId)
  if (!Number.isFinite(docId) || docId <= 0) {
    loading.value = false
    errorMessage.value = '缺少绩效文档'
    return
  }
  try {
    const res = await getPerformanceOnlineEditorConfig(docId, { current_user: currentUser.value })
    fileName.value = (res.file && res.file.name) || ''
    await loadOnlyOfficeApi(res.documentServerUrl)
    editorInstance = new window.DocsAPI.DocEditor('performance-onlyoffice', res.config)
    loading.value = false
  } catch (err) {
    loading.value = false
    errorMessage.value = detailOf(err)
  }
}

onMounted(bootstrap)
onBeforeUnmount(destroyEditor)
</script>

<style scoped>
.oo-editor-page { display: flex; flex-direction: column; height: calc(100vh - 56px); min-height: 480px; background: #f5f7fa; }
.oo-editor-toolbar { display: flex; align-items: center; gap: 12px; padding: 10px 16px; background: #fff; border-bottom: 1px solid #e5e7eb; }
.oo-back-btn, .oo-retry-btn { border: 1px solid #d1d5db; background: #fff; border-radius: 6px; padding: 6px 12px; cursor: pointer; }
.oo-editor-title { display: flex; flex-wrap: wrap; gap: 10px; align-items: baseline; }
.oo-meta { color: #2563eb; font-size: 12px; }
.oo-loading, .oo-error { padding: 24px 16px; }
.oo-error { color: #b91c1c; }
.oo-editor-host { flex: 1; min-height: 0; }
</style>
