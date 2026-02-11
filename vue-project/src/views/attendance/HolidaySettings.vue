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
        <h3 class="llm-title">使用大模型自动解析假期通知</h3>
        <p class="llm-desc">
          将全年放假通知原文粘贴在下面，大模型会自动解析出放假日和调休上班日，并写入 {{ year }} 年的假期设置。
        </p>
        <textarea
          v-model="llmText"
          class="llm-textarea"
          rows="6"
          placeholder="例如：&#10;1.元旦：1 月 1 日（周四）至 3 日（周六）放假调休，共 3 天。1 月 4 日（周日）上班。&#10;2.春节：……"
        ></textarea>
        <div class="llm-actions">
          <button
            type="button"
            class="btn btn-primary"
            :disabled="llmParsing || !llmText.trim()"
            @click="handleParseByLLM"
          >
            {{ llmParsing ? '解析中…' : '一键解析并填充' }}
          </button>
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
                    用于标识节假日名称，便于加班费激励统计。
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
  try {
    const res = await fetch('/api/holiday/parse-text', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        year: year.value,
        current_user: name,
        text
      })
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || err.message || '解析失败')
    }
    const data = await res.json()
    if (data && data.success && Array.isArray(data.holidays)) {
      rows.value = data.holidays.map((h, idx) => ({
        id: `${h.date}-${idx}`,
        date: h.date,
        type: h.type || '',
        festival: h.festival || ''
      }))
      alert('解析并保存成功')
    } else {
      throw new Error(data?.detail || data?.message || '解析失败')
    }
  } catch (e) {
    alert(e?.message || '解析失败')
  } finally {
    llmParsing.value = false
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
}
</style>

