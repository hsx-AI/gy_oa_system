<template>
  <div class="attendance-page">
    <div class="page-header-bar">
      <div class="header-bar-content">
        <div>
          <h1 class="page-title">假期调休设置</h1>
          <p class="page-subtitle">配置每年的法定节假日与调休上班日，影响智能建议与考勤异常判断。</p>
        </div>
        <div class="header-actions">
          <div class="month-selector">
            <label class="month-label">选择年份</label>
            <select v-model="year" class="year-select" @change="loadHolidays">
              <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}</option>
            </select>
          </div>
          <button type="button" class="btn btn-outline" @click="addRow">
            新增日期
          </button>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="saving"
            @click="handleSave"
          >
            {{ saving ? '保存中…' : '保存本年设置' }}
          </button>
        </div>
      </div>
    </div>

    <div class="container">
      <div class="card mt-xl llm-card">
        <h3 class="llm-title">使用本地大模型自动解析假期通知</h3>
        <p class="llm-desc">
          将全年放假通知原文粘贴在下面，本地大模型会流式解析出放假日和调休上班日，并写入 {{ year }} 年的假期设置。
        </p>
        <textarea
          v-model="llmText"
          class="llm-textarea"
          rows="6"
          placeholder="例如：&#10;1.元旦：1 月 1 日（周四）至 3 日（周六）放假调休，共 3 天。1 月 4 日（周日）上班。&#10;2.春节：……"
        ></textarea>
        <div class="llm-actions">
          <button
            v-if="llmParsing"
            type="button"
            class="btn btn-outline"
            @click="cancelParse"
          >取消</button>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="llmParsing || !llmText.trim()"
            @click="handleParseByLLM"
          >
            {{ llmParsing ? '解析中…' : '一键解析并填充' }}
          </button>
        </div>

        <div v-if="llmParsing || llmStreamText || llmStatusMsg" class="llm-stream">
          <div class="llm-stream-head">
            <span class="llm-stream-title">
              解析过程
              <span v-if="llmModelInfo" class="llm-stream-model">{{ llmModelInfo }}</span>
            </span>
            <span class="llm-stream-status" :class="llmStatusType">
              <span v-if="llmParsing" class="llm-dot"></span>
              {{ llmStatusMsg || (llmParsing ? '正在调用本地大模型…' : '已完成') }}
            </span>
          </div>
          <pre ref="llmStreamBoxRef" class="llm-stream-body">{{ llmStreamText || '（等待模型输出…）' }}</pre>
        </div>
      </div>

      <div class="card mt-xl">
        <div class="table-header">
          <h3 class="table-title">假期与调休列表（{{ year }} 年）</h3>
        </div>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 160px;">日期</th>
                <th>类型 / 说明</th>
                <th style="width: 200px;">节日</th>
                <th style="width: 80px;">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="4" class="text-center text-tertiary">加载中…</td>
              </tr>
              <tr v-else-if="rows.length === 0">
                <td colspan="4" class="text-center text-tertiary">当前年份暂无配置，请点击「新增日期」添加。</td>
              </tr>
              <tr v-for="(row, idx) in rows" :key="row.id">
                <td>
                  <input
                    type="date"
                    v-model="row.date"
                    class="input"
                  />
                </td>
                <td>
                  <select v-model="row.type" class="input">
                    <option value="放假">放假</option>
                    <option value="上班">上班</option>
                  </select>
                  <p class="field-hint">
                    放假：休息日；上班：调休工作日。
                  </p>
                </td>
                <td>
                  <select v-model="row.festival" class="input">
                    <option value="">（无）</option>
                    <option v-for="f in festivalOptions" :key="f" :value="f">
                      {{ f }}
                    </option>
                  </select>
                  <p class="field-hint">
                    用于标识节假日名称，便于其他绩效激励统计。
                  </p>
                </td>
                <td>
                  <button type="button" class="link-btn danger" @click="removeRow(idx)">
                    删除
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getHolidays, saveHolidays } from '@/api/attendance'

const loading = ref(false)
const saving = ref(false)
const uploading = ref(false) // 兼容旧逻辑，暂未使用
const year = ref(new Date().getFullYear().toString())
const rows = ref([])
const fileInput = ref(null)
const llmText = ref('')
const llmParsing = ref(false)
const llmStreamText = ref('')
const llmStatusMsg = ref('')
const llmStatusType = ref('') // '', 'success', 'error'
const llmModelInfo = ref('')
const llmStreamBoxRef = ref(null)
let llmAbortController = null

const festivalOptions = [
  '元旦',
  '春节',
  '清明',
  '劳动节',
  '端午节',
  '中秋节',
  '国庆节',
  '高温防暑休假'
]

const yearOptions = (() => {
  const cur = new Date().getFullYear()
  const list = []
  for (let y = cur - 1; y <= cur + 2; y++) list.push(String(y))
  return list
})()

function getCurrentUserName () {
  try {
    const raw = localStorage.getItem('userInfo')
    if (!raw) return ''
    const user = JSON.parse(raw)
    return (user.name || user.userName || '').trim()
  } catch {
    return ''
  }
}

function normalizeDateToYear (d) {
  if (!d) return ''
  const y = year.value
  const m = String(new Date(d).getMonth() + 1).padStart(2, '0')
  const day = String(new Date(d).getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function loadHolidays () {
  loading.value = true
  rows.value = []
  getHolidays(year.value)
    .then(res => {
      if (res && res.success && Array.isArray(res.holidays)) {
        rows.value = res.holidays.map((h, idx) => ({
          id: `${h.date}-${idx}`,
          date: h.date,
          type: h.type || '',
          festival: h.festival || ''
        }))
      } else {
        rows.value = []
      }
    })
    .catch(() => {
      rows.value = []
    })
    .finally(() => {
      loading.value = false
    })
}

function addRow () {
  const today = new Date()
  const m = String(today.getMonth() + 1).padStart(2, '0')
  const d = String(today.getDate()).padStart(2, '0')
  rows.value.push({
    id: `new-${Date.now()}-${rows.value.length}`,
    date: `${year.value}-${m}-${d}`,
    type: '放假',
    festival: ''
  })
}

function removeRow (idx) {
  rows.value.splice(idx, 1)
}

async function handleSave () {
  const name = getCurrentUserName()
  if (!name) {
    alert('请先登录')
    return
  }
  // 简单校验：过滤空日期
  const holidays = rows.value
    .map(r => ({
      date: normalizeDateToYear(r.date),
      type: (r.type || '').trim() || '放假',
      festival: (r.festival || '').trim()
    }))
    .filter(r => r.date)

  if (!holidays.length && !confirm('当前年份没有任何假期配置，确定要清空该年的假期数据吗？')) {
    return
  }

  saving.value = true
  try {
    const res = await saveHolidays({
      year: year.value,
      current_user: name,
      holidays
    })
    if (res && res.success) {
      alert('保存成功')
      // 以返回数据为准刷新
      if (Array.isArray(res.holidays)) {
        rows.value = res.holidays.map((h, idx) => ({
          id: `${h.date}-${idx}`,
          date: h.date,
          type: h.type || ''
        }))
      }
    } else {
      alert(res?.detail || res?.message || '保存失败')
    }
  } catch (e) {
    alert(e?.response?.data?.detail || e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

function cancelParse () {
  if (llmAbortController) {
    try { llmAbortController.abort() } catch { /* ignore */ }
  }
}

function scrollStreamBoxToBottom () {
  const box = llmStreamBoxRef.value
  if (!box) return
  // 等待 DOM 更新后滚动到底部
  requestAnimationFrame(() => {
    try { box.scrollTop = box.scrollHeight } catch { /* ignore */ }
  })
}

function handleStreamEvent (evt) {
  if (!evt || typeof evt !== 'object') return
  if (evt.type === 'meta') {
    if (evt.model) {
      llmModelInfo.value = evt.model + (evt.base_url ? `  ·  ${evt.base_url}` : '')
    }
    llmStatusMsg.value = '正在调用本地大模型…'
    llmStatusType.value = ''
  } else if (evt.type === 'chunk') {
    llmStreamText.value += (evt.text || '')
    scrollStreamBoxToBottom()
  } else if (evt.type === 'done') {
    if (Array.isArray(evt.holidays)) {
      rows.value = evt.holidays.map((h, idx) => ({
        id: `${h.date}-${idx}`,
        date: h.date,
        type: h.type || '',
        festival: h.festival || ''
      }))
    }
    llmStatusMsg.value = `解析完成，已写入 ${evt.holidays ? evt.holidays.length : 0} 条记录`
    llmStatusType.value = 'success'
  } else if (evt.type === 'error') {
    llmStatusMsg.value = evt.message || '解析失败'
    llmStatusType.value = 'error'
  }
}

async function handleParseByLLM () {
  const name = getCurrentUserName()
  if (!name) {
    alert('请先登录')
    return
  }
  const text = llmText.value.trim()
  if (!text) {
    alert('请先粘贴放假通知内容')
    return
  }

  llmParsing.value = true
  llmStreamText.value = ''
  llmStatusMsg.value = '正在连接本地大模型…'
  llmStatusType.value = ''
  llmModelInfo.value = ''
  llmAbortController = new AbortController()

  try {
    const res = await fetch('/api/holiday/parse-text-stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream'
      },
      body: JSON.stringify({
        year: year.value,
        current_user: name,
        text
      }),
      signal: llmAbortController.signal
    })
    if (!res.ok || !res.body) {
      let errMsg = '解析失败'
      try {
        const err = await res.json()
        errMsg = err.detail || err.message || errMsg
      } catch { /* ignore */ }
      throw new Error(errMsg)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    // SSE 按 \n\n 分隔事件；每条事件里 data: 之后是 JSON
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let sepIdx
      while ((sepIdx = buffer.indexOf('\n\n')) !== -1) {
        const rawEvent = buffer.slice(0, sepIdx)
        buffer = buffer.slice(sepIdx + 2)
        const lines = rawEvent.split('\n')
        const dataLines = []
        for (const line of lines) {
          if (line.startsWith('data:')) {
            dataLines.push(line.slice(5).trimStart())
          }
        }
        if (!dataLines.length) continue
        try {
          const evt = JSON.parse(dataLines.join('\n'))
          handleStreamEvent(evt)
        } catch (e) {
          // 忽略解析失败的单条事件
        }
      }
    }
  } catch (e) {
    if (e && e.name === 'AbortError') {
      llmStatusMsg.value = '已取消'
      llmStatusType.value = 'error'
    } else {
      llmStatusMsg.value = e?.message || '解析失败'
      llmStatusType.value = 'error'
    }
  } finally {
    llmParsing.value = false
    llmAbortController = null
  }
}

onMounted(() => {
  loadHolidays()
})
</script>

<style scoped>
.attendance-page {
  min-height: 100vh;
  background: var(--color-bg-layout);
  padding-bottom: var(--spacing-xxl);
}

.header-bar-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-base);
}

.month-selector {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.month-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
}

.year-select {
  min-width: 120px;
  padding: var(--spacing-sm) var(--spacing-base);
}

.container {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0;
}

.mt-xl {
  margin-top: var(--spacing-xl);
}

.table-header {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
  background: var(--color-bg-spotlight);
}

.table-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}

.data-table thead {
  background: var(--color-bg-spotlight);
}

.data-table th,
.data-table td {
  padding: var(--spacing-base);
  border-bottom: 1px solid var(--color-border-lighter);
  text-align: left;
}

.text-center {
  text-align: center;
}

.text-tertiary {
  color: var(--color-text-tertiary);
}

.input {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-base);
  border-radius: var(--radius-base);
  border: 1px solid var(--color-border-lighter);
  font-size: var(--font-size-sm);
}

.field-hint {
  margin-top: 4px;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.link-btn {
  background: none;
  border: none;
  color: var(--color-primary);
  cursor: pointer;
  font-size: var(--font-size-sm);
  padding: 0;
}

.link-btn.danger {
  color: var(--color-danger, #e53935);
}

.llm-card {
  border: 1px solid var(--color-border-lighter);
  padding: var(--spacing-lg) var(--spacing-xl);
}

.llm-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--spacing-xs);
}

.llm-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-base);
}

.llm-textarea {
  width: 100%;
  min-height: 140px;
  padding: var(--spacing-sm) var(--spacing-base);
  border-radius: var(--radius-base);
  border: 1px solid var(--color-border-lighter);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  resize: vertical;
}

.llm-actions {
  margin-top: var(--spacing-sm);
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
}

.llm-stream {
  margin-top: var(--spacing-base);
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--radius-base);
  background: #0f172a;
  color: #e2e8f0;
  overflow: hidden;
}
.llm-stream-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-sm);
  padding: 8px 14px;
  background: rgba(255, 255, 255, 0.06);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  font-size: var(--font-size-sm);
}
.llm-stream-title {
  font-weight: var(--font-weight-semibold);
  color: #f1f5f9;
}
.llm-stream-model {
  margin-left: 8px;
  padding: 1px 8px;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.18);
  color: #93c5fd;
  font-size: 0.75rem;
  font-weight: 400;
}
.llm-stream-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  color: #cbd5e1;
}
.llm-stream-status.success { color: #4ade80; }
.llm-stream-status.error { color: #f87171; }
.llm-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #3b82f6;
  animation: llm-dot-pulse 1.1s infinite ease-in-out;
}
@keyframes llm-dot-pulse {
  0%, 100% { transform: scale(0.85); opacity: 0.7; }
  50% { transform: scale(1.15); opacity: 1; }
}
.llm-stream-body {
  margin: 0;
  padding: 12px 14px;
  max-height: 260px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.82rem;
  line-height: 1.55;
  color: #e2e8f0;
  background: transparent;
}
</style>

