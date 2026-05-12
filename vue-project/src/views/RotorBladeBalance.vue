<template>
  <div class="blade-page">
    <section class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">转轮叶片配重工艺程序</h1>
          <p class="header-subtitle">复刻原230系统功能，按叶片重量优化排列，计算综合偏心矩 IZ。</p>
        </div>
        <div class="header-actions no-print">
          <button type="button" class="btn" @click="openHistory">历史记录</button>
          <button type="button" class="btn" @click="resetForm">重置</button>
          <button type="button" class="btn" :disabled="!result" @click="printPage">生成PDF</button>
          <button type="button" class="btn" :disabled="!result || saveLoading" @click="saveCurrentResult">
            {{ saveLoading ? '保存中...' : '保存计算结果' }}
          </button>
          <button type="button" class="btn btn-primary" @click="calculate">计算排列</button>
        </div>
      </div>
    </section>

    <section class="workbench no-print">
      <div class="card setup-card">
        <div class="card-section">
          <div class="section-title">基础信息</div>
          <div class="field-grid">
            <label class="field">
              <span>叶片形式</span>
              <select v-model="form.mode" class="input" @change="syncBladeRows">
                <option value="V1">单一型式</option>
                <option value="V2">长短叶片型式</option>
              </select>
            </label>
            <label class="field">
              <span>{{ form.mode === 'V1' ? '叶片数量' : '长/短叶片数量各' }}</span>
              <select v-model.number="form.bladeCount" class="input" @change="syncBladeRows">
                <option v-for="count in bladeCountOptions" :key="count" :value="count">{{ count }} 个</option>
              </select>
            </label>
            <label class="field">
              <span>电站</span>
              <input v-model.trim="meta.station" class="input" type="text" placeholder="请输入电站名称">
            </label>
            <label class="field">
              <span>水轮机号</span>
              <input v-model.trim="meta.turbineNo" class="input" type="text" placeholder="请输入机组号">
            </label>
            <label class="field">
              <span>工作号</span>
              <input v-model.trim="meta.workNo" class="input" type="text" placeholder="请输入工作号">
            </label>
            <label class="field">
              <span>日期</span>
              <input v-model="meta.date" class="input" type="date">
            </label>
          </div>
        </div>

        <div class="card-section">
          <div class="section-title">来料重量</div>
          <div @keydown="onInputTableEnterKey">
            <div v-if="form.mode === 'V1'" class="table-wrap">
              <table class="input-table">
              <thead>
                <tr>
                  <th>计算序号</th>
                  <th>来料代码</th>
                  <th>重量(Kg)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(blade, index) in singleBlades" :key="`single-${index}`">
                  <td>{{ index + 1 }}#</td>
                  <td><input v-model.trim="blade.code" class="cell-input" type="text" placeholder="代码"></td>
                  <td><input v-model.trim="blade.weight" class="cell-input" type="number" step="0.001" min="0" placeholder="重量"></td>
                </tr>
              </tbody>
            </table>
            </div>

            <div v-else class="table-wrap">
              <table class="input-table dual-table">
              <thead>
                <tr>
                  <th colspan="3">长叶片</th>
                  <th colspan="3">短叶片</th>
                </tr>
                <tr>
                  <th>计算序号</th>
                  <th>来料代码</th>
                  <th>重量(Kg)</th>
                  <th>计算序号</th>
                  <th>来料代码</th>
                  <th>重量(Kg)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(_, index) in longBlades" :key="`dual-${index}`">
                  <td>{{ index + 1 }}#</td>
                  <td><input v-model.trim="longBlades[index].code" class="cell-input" type="text" placeholder="长叶片代码"></td>
                  <td><input v-model.trim="longBlades[index].weight" class="cell-input" type="number" step="0.001" min="0" placeholder="重量"></td>
                  <td>{{ index + 1 }}#'</td>
                  <td><input v-model.trim="shortBlades[index].code" class="cell-input" type="text" placeholder="短叶片代码"></td>
                  <td><input v-model.trim="shortBlades[index].weight" class="cell-input" type="number" step="0.001" min="0" placeholder="重量"></td>
                </tr>
              </tbody>
            </table>
            </div>
          </div>
          <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
          <p v-if="saveMessage" class="save-message">{{ saveMessage }}</p>
        </div>
      </div>

      <aside class="card note-card">
        <div class="section-title">计算说明</div>
        <ul>
          <li>重量按原程序降序排序，再按预设分组穷举优化。</li>
          <li>单一型式支持 4-20 个叶片。</li>
          <li>长短叶片型式支持长、短叶片各 4-17 个。</li>
          <li>结果中的原序号和来料代码保持与输入行对应。</li>
        </ul>
      </aside>
    </section>

    <section v-if="result" class="report-card" ref="reportRef">
      <div class="report-header">
        <div class="report-logo">智能制造工艺部</div>
        <div class="report-title">
          <div>
            <span class="blank-text">{{ meta.station }}</span> 电站
            <span class="blank-text">{{ meta.turbineNo }}</span> 号水轮机转轮叶片优化排列
          </div>
        </div>
        <div class="report-meta">
          <div>工作号：<span>{{ meta.workNo || '-' }}</span></div>
          <div>日期：<span>{{ meta.date || '-' }}</span></div>
        </div>
      </div>

      <div ref="resultSummaryRef" class="result-summary">
        <div>
          <span class="summary-label">叶片形式</span>
          <strong>{{ result.mode === 'V1' ? '单一叶片型式' : '长短叶片型式' }}</strong>
        </div>
        <div>
          <span class="summary-label">叶片数量</span>
          <strong>{{ result.mode === 'V1' ? `${result.bladeCount} 个` : `各 ${result.bladeCount} 个` }}</strong>
        </div>
        <div>
          <span class="summary-label">综合偏心矩</span>
          <strong>IZ={{ formatNumber(result.iz, 4) }}</strong>
        </div>
      </div>

      <div class="result-layout">
        <div class="table-wrap result-table-wrap">
          <table ref="resultTableRef" class="result-table">
            <thead>
              <tr>
                <th>安放角度</th>
                <th>原序号</th>
                <th>叶片重量(Kg)</th>
                <th>来料代码</th>
                <th v-if="result.mode === 'V2'">叶片规格</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in result.rows" :key="row.key" :class="{ 'row-muted': row.spec === '长叶片' }">
                <td>{{ formatNumber(row.angle, 3) }}°</td>
                <td>{{ row.originalLabel }}</td>
                <td>{{ formatWeight(row.weight) }}</td>
                <td>{{ row.code || '-' }}</td>
                <td v-if="result.mode === 'V2'">{{ row.spec }}</td>
              </tr>
            </tbody>
          </table>
          <button
            type="button"
            class="copy-table-image-btn no-print"
            :disabled="copyTableImageLoading"
            @click="copyResultTableAsImage"
          >
            {{ copyTableImageLoading ? '生成中…' : '复制表格图片' }}
          </button>
        </div>

        <div class="diagram-panel">
          <div class="diagram-title">程序优化排列示意图</div>
          <div class="diagram-figure-wrap">
            <svg
              ref="bladeDiagramRef"
              class="blade-diagram"
              viewBox="0 0 520 520"
              role="img"
              aria-label="叶片优化排列示意图"
            >
            <circle class="diagram-ring" cx="260" cy="260" r="182" />
            <circle class="diagram-center" cx="260" cy="260" r="46" />
            <line
              v-for="tick in diagramTicks"
              :key="tick.key"
              class="diagram-spoke"
              x1="260"
              y1="260"
              :x2="tick.x"
              :y2="tick.y"
            />
            <g v-for="point in diagramPoints" :key="point.key" class="diagram-point">
              <circle :cx="point.x" :cy="point.y" :r="point.spec === '短叶片' ? 22 : 26" :class="point.spec === '短叶片' ? 'short-node' : 'long-node'" />
              <text :x="point.x" :y="point.y - 4" text-anchor="middle">{{ point.positionLabel }}</text>
              <text :x="point.x" :y="point.y + 13" text-anchor="middle" class="node-sub">{{ point.originalLabel }}</text>
            </g>
            </svg>
            <button
              type="button"
              class="copy-table-image-btn no-print"
              :disabled="copyDiagramImageLoading"
              @click="copyDiagramAsImage"
            >
              {{ copyDiagramImageLoading ? '生成中…' : '复制示意图' }}
            </button>
          </div>
        </div>
      </div>

      <div class="report-footer">
        <label>编制：<input v-model.trim="meta.compiler" type="text" class="plain-input"></label>
        <label>校核：<input v-model.trim="meta.checker" type="text" class="plain-input"></label>
      </div>
    </section>

    <div v-if="historyOpen" class="history-overlay no-print" @click.self="historyOpen = false">
      <div class="history-modal">
        <div class="history-header">
          <div>
            <h2>计算结果历史记录</h2>
            <p>保存后的配重计算结果可在此追溯查看。</p>
          </div>
          <button type="button" class="history-close" @click="historyOpen = false">×</button>
        </div>
        <div class="history-toolbar">
          <input
            v-model.trim="historyKeyword"
            class="input"
            type="search"
            placeholder="搜索电站、水轮机号、工作号、保存人"
            @keyup.enter="fetchHistory(1)"
          >
          <button type="button" class="btn btn-primary" @click="fetchHistory(1)">查询</button>
        </div>
        <div v-if="historyError" class="history-error">{{ historyError }}</div>
        <div class="history-body">
          <div v-if="historyLoading" class="history-empty">加载中...</div>
          <div v-else-if="!historyRecords.length" class="history-empty">暂无保存记录</div>
          <table v-else class="history-table">
            <thead>
              <tr>
                <th>标题</th>
                <th>形式</th>
                <th>数量</th>
                <th>IZ</th>
                <th>保存人</th>
                <th>保存时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in historyRecords" :key="record.id">
                <td>
                  <strong>{{ record.title || '-' }}</strong>
                  <small>{{ record.station || '-' }} / {{ record.turbineNo || '-' }} / {{ record.workNo || '-' }}</small>
                </td>
                <td>{{ record.mode === 'V1' ? '单一' : '长短' }}</td>
                <td>{{ record.mode === 'V1' ? `${record.bladeCount}个` : `各${record.bladeCount}个` }}</td>
                <td>{{ formatNumber(Number(record.iz), 4) }}</td>
                <td>{{ record.createdBy }}</td>
                <td>{{ record.createdAt }}</td>
                <td><button type="button" class="btn btn-sm" @click="loadHistoryRecord(record.id)">查看</button></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="history-footer">
          <span>共 {{ historyTotal }} 条，第 {{ historyPage }} / {{ historyTotalPages }} 页</span>
          <div>
            <button type="button" class="btn btn-sm" :disabled="historyPage <= 1" @click="fetchHistory(historyPage - 1)">上一页</button>
            <button type="button" class="btn btn-sm" :disabled="historyPage >= historyTotalPages" @click="fetchHistory(historyPage + 1)">下一页</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import {
  getRotorBladeBalanceRecord,
  listRotorBladeBalanceRecords,
  saveRotorBladeBalanceRecord
} from '@/api/rotorBladeBalance'

const alphabet = 'abcdefghijklmnopqrst'

const form = reactive({
  mode: 'V1',
  bladeCount: 4
})

const today = new Date().toISOString().slice(0, 10)
const userInfo = readCurrentUser()

const meta = reactive({
  station: '',
  turbineNo: '',
  workNo: '',
  date: today,
  compiler: userInfo.name || '',
  checker: ''
})

const singleBlades = ref(createRows(4))
const longBlades = ref(createRows(4))
const shortBlades = ref(createRows(4))
const result = ref(null)
const errorMessage = ref('')
const saveMessage = ref('')
const saveLoading = ref(false)
const reportRef = ref(null)
const resultSummaryRef = ref(null)
const resultTableRef = ref(null)
const bladeDiagramRef = ref(null)
const copyTableImageLoading = ref(false)
const copyDiagramImageLoading = ref(false)
const historyOpen = ref(false)
const historyLoading = ref(false)
const historyError = ref('')
const historyKeyword = ref('')
const historyRecords = ref([])
const historyTotal = ref(0)
const historyPage = ref(1)
const historyPageSize = 10

const historyTotalPages = computed(() => Math.max(1, Math.ceil(historyTotal.value / historyPageSize)))

const bladeCountOptions = computed(() => {
  const max = form.mode === 'V1' ? 20 : 17
  return Array.from({ length: max - 3 }, (_, index) => index + 4)
})

const diagramPoints = computed(() => {
  if (!result.value) return []
  const radius = 182
  return result.value.rows.map((row, index) => {
    const angle = (row.angle - 90) * Math.PI / 180
    return {
      ...row,
      key: `${row.key}-diagram`,
      positionLabel: result.value.mode === 'V2' ? String(index + 1) : String(row.positionIndex),
      x: 260 + radius * Math.cos(angle),
      y: 260 + radius * Math.sin(angle)
    }
  })
})

const diagramTicks = computed(() => {
  if (!result.value) return []
  const rows = result.value.mode === 'V2'
    ? result.value.rows.filter((row) => row.spec === '长叶片')
    : result.value.rows
  return rows.map((row) => {
    const angle = (row.angle - 90) * Math.PI / 180
    return {
      key: `tick-${row.key}`,
      x: 260 + 172 * Math.cos(angle),
      y: 260 + 172 * Math.sin(angle)
    }
  })
})

function readCurrentUser() {
  try {
    const raw = localStorage.getItem('userInfo')
    if (!raw) return {}
    return JSON.parse(raw) || {}
  } catch {
    return {}
  }
}

function currentUserName() {
  const info = readCurrentUser()
  return (info.name || info.userName || info.username || '').trim()
}

function createRows(count) {
  return Array.from({ length: count }, () => ({ code: '', weight: '' }))
}

function resizeRows(rows, count) {
  const next = rows.slice(0, count)
  while (next.length < count) next.push({ code: '', weight: '' })
  return next
}

function syncBladeRows() {
  if (form.mode === 'V2' && form.bladeCount > 17) form.bladeCount = 17
  singleBlades.value = resizeRows(singleBlades.value, form.bladeCount)
  longBlades.value = resizeRows(longBlades.value, form.bladeCount)
  shortBlades.value = resizeRows(shortBlades.value, form.bladeCount)
  errorMessage.value = ''
  saveMessage.value = ''
  result.value = null
}

/** Enter：焦点移到同一列下一行的输入框（来料重量表） */
function onInputTableEnterKey(ev) {
  if (ev.key !== 'Enter' || ev.shiftKey || ev.ctrlKey || ev.altKey || ev.metaKey) return
  const target = ev.target
  if (!(target instanceof HTMLInputElement) || !target.classList.contains('cell-input')) return
  const td = target.closest('td')
  const tr = td?.closest('tr')
  const tbody = tr?.closest('tbody')
  if (!td || !tr || !tbody) return
  const colIndex = td.cellIndex
  let next = tr.nextElementSibling
  while (next) {
    const cell = next.cells[colIndex]
    const input = cell?.querySelector('input.cell-input')
    if (input) {
      ev.preventDefault()
      input.focus()
      if (typeof input.select === 'function') input.select()
      return
    }
    next = next.nextElementSibling
  }
}

function resetForm() {
  form.mode = 'V1'
  form.bladeCount = 4
  singleBlades.value = createRows(4)
  longBlades.value = createRows(4)
  shortBlades.value = createRows(4)
  result.value = null
  errorMessage.value = ''
  saveMessage.value = ''
}

function printPage() {
  if (!result.value) return
  const originalTitle = document.title
  const parts = [meta.station, meta.turbineNo, meta.workNo].map((item) => (item || '').trim()).filter(Boolean)
  document.title = parts.length ? `转轮叶片配重-${parts.join('-')}` : '转轮叶片配重报告'
  document.body.classList.add('printing-report-only')

  const cleanup = () => {
    document.body.classList.remove('printing-report-only')
    document.title = originalTitle
    window.removeEventListener('afterprint', cleanup)
  }

  window.addEventListener('afterprint', cleanup, { once: true })
  setTimeout(() => {
    window.print()
    setTimeout(cleanup, 1000)
  }, 50)
}

function calculate() {
  errorMessage.value = ''
  saveMessage.value = ''
  try {
    result.value = form.mode === 'V1' ? calculateSingle() : calculateDual()
  } catch (error) {
    result.value = null
    errorMessage.value = error.message || '计算失败，请检查输入。'
  }
}

async function copyResultTableAsImage() {
  const summaryEl = resultSummaryRef.value
  const tableEl = resultTableRef.value
  if (!summaryEl || !tableEl || copyTableImageLoading.value) return
  copyTableImageLoading.value = true
  try {
    const html2canvas = (await import('html2canvas')).default
    const scale = Math.min(2, Math.max(1, window.devicePixelRatio || 1))
    const opts = {
      backgroundColor: '#ffffff',
      scale,
      useCORS: true,
      logging: false
    }
    const [canvasSummary, canvasTable] = await Promise.all([
      html2canvas(summaryEl, opts),
      html2canvas(tableEl, opts)
    ])
    const gap = Math.round(8 * scale)
    const width = Math.max(canvasSummary.width, canvasTable.width)
    const height = canvasSummary.height + gap + canvasTable.height
    const merged = document.createElement('canvas')
    merged.width = width
    merged.height = height
    const ctx = merged.getContext('2d')
    if (!ctx) throw new Error('无法创建画布')
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, width, height)
    ctx.drawImage(canvasSummary, 0, 0)
    ctx.drawImage(canvasTable, 0, canvasSummary.height + gap)
    const blob = await new Promise((resolve, reject) => {
      merged.toBlob((b) => (b ? resolve(b) : reject(new Error('无法生成图片'))), 'image/png')
    })
    if (!navigator.clipboard?.write || typeof ClipboardItem === 'undefined') {
      window.alert('当前环境不支持将图片写入剪贴板，请使用 Chrome / Edge 等现代浏览器，并尽量通过 HTTPS 或 localhost 访问。')
      return
    }
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
    window.alert('摘要与表格图片已复制到剪贴板，可在微信、Word、邮件等处粘贴。')
  } catch (error) {
    console.error(error)
    window.alert(error?.message || '复制失败，请重试或检查浏览器剪贴板权限。')
  } finally {
    copyTableImageLoading.value = false
  }
}

async function copyDiagramAsImage() {
  const el = bladeDiagramRef.value
  if (!el || copyDiagramImageLoading.value) return
  copyDiagramImageLoading.value = true
  try {
    const html2canvas = (await import('html2canvas')).default
    const scale = Math.min(2, Math.max(1, window.devicePixelRatio || 1))
    const canvas = await html2canvas(el, {
      backgroundColor: '#ffffff',
      scale,
      useCORS: true,
      logging: false
    })
    const blob = await new Promise((resolve, reject) => {
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('无法生成图片'))), 'image/png')
    })
    if (!navigator.clipboard?.write || typeof ClipboardItem === 'undefined') {
      window.alert('当前环境不支持将图片写入剪贴板，请使用 Chrome / Edge 等现代浏览器，并尽量通过 HTTPS 或 localhost 访问。')
      return
    }
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
    window.alert('示意图已复制到剪贴板，可在微信、Word、邮件等处粘贴。')
  } catch (error) {
    console.error(error)
    window.alert(error?.message || '复制失败，请重试或检查浏览器剪贴板权限。')
  } finally {
    copyDiagramImageLoading.value = false
  }
}

function inputSnapshot() {
  return {
    mode: form.mode,
    bladeCount: form.bladeCount,
    singleBlades: singleBlades.value.map((item) => ({ code: item.code || '', weight: item.weight })),
    longBlades: longBlades.value.map((item) => ({ code: item.code || '', weight: item.weight })),
    shortBlades: shortBlades.value.map((item) => ({ code: item.code || '', weight: item.weight }))
  }
}

function metaSnapshot() {
  return {
    station: meta.station || '',
    turbineNo: meta.turbineNo || '',
    workNo: meta.workNo || '',
    date: meta.date || '',
    compiler: meta.compiler || '',
    checker: meta.checker || ''
  }
}

function recordTitle() {
  const parts = [meta.station, meta.turbineNo, meta.workNo].map((item) => (item || '').trim()).filter(Boolean)
  return parts.join(' / ')
}

function errorText(error, fallback) {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail) return detail
  return error?.message || fallback
}

async function saveCurrentResult() {
  if (!result.value || saveLoading.value) return
  const name = currentUserName()
  if (!name) {
    saveMessage.value = '未获取到当前登录人，无法保存。'
    return
  }

  saveLoading.value = true
  saveMessage.value = ''
  try {
    const res = await saveRotorBladeBalanceRecord({
      current_user: name,
      title: recordTitle(),
      meta: metaSnapshot(),
      inputData: inputSnapshot(),
      result: result.value
    })
    saveMessage.value = res.message || '保存成功'
    if (historyOpen.value) fetchHistory(historyPage.value)
  } catch (error) {
    saveMessage.value = errorText(error, '保存失败')
  } finally {
    saveLoading.value = false
  }
}

function openHistory() {
  historyOpen.value = true
  fetchHistory(1)
}

async function fetchHistory(page = historyPage.value) {
  const name = currentUserName()
  if (!name) {
    historyError.value = '未获取到当前登录人，无法查询历史记录。'
    historyRecords.value = []
    historyTotal.value = 0
    return
  }

  historyLoading.value = true
  historyError.value = ''
  try {
    const res = await listRotorBladeBalanceRecords({
      current_user: name,
      keyword: historyKeyword.value || undefined,
      page,
      page_size: historyPageSize
    })
    historyRecords.value = Array.isArray(res.list) ? res.list : []
    historyTotal.value = Number(res.total || 0)
    historyPage.value = Number(res.page || page)
  } catch (error) {
    historyError.value = errorText(error, '历史记录加载失败')
    historyRecords.value = []
    historyTotal.value = 0
  } finally {
    historyLoading.value = false
  }
}

async function loadHistoryRecord(id) {
  const name = currentUserName()
  if (!name) {
    historyError.value = '未获取到当前登录人，无法查看历史记录。'
    return
  }

  historyLoading.value = true
  historyError.value = ''
  try {
    const res = await getRotorBladeBalanceRecord(id, { current_user: name })
    const record = res.record || {}
    const savedMeta = record.meta || {}
    const savedInput = record.inputData || {}
    Object.assign(meta, {
      station: savedMeta.station || record.station || '',
      turbineNo: savedMeta.turbineNo || record.turbineNo || '',
      workNo: savedMeta.workNo || record.workNo || '',
      date: savedMeta.date || today,
      compiler: savedMeta.compiler || record.compiler || '',
      checker: savedMeta.checker || record.checker || ''
    })
    form.mode = savedInput.mode || record.mode || 'V1'
    form.bladeCount = Number(savedInput.bladeCount || record.bladeCount || 4)
    singleBlades.value = resizeRows(Array.isArray(savedInput.singleBlades) ? savedInput.singleBlades : [], form.bladeCount)
    longBlades.value = resizeRows(Array.isArray(savedInput.longBlades) ? savedInput.longBlades : [], form.bladeCount)
    shortBlades.value = resizeRows(Array.isArray(savedInput.shortBlades) ? savedInput.shortBlades : [], form.bladeCount)
    result.value = record.result || null
    errorMessage.value = ''
    saveMessage.value = `已载入历史记录：${record.title || record.createdAt || ''}`
    historyOpen.value = false
  } catch (error) {
    historyError.value = errorText(error, '历史记录加载失败')
  } finally {
    historyLoading.value = false
  }
}

function calculateSingle() {
  const blades = normalizeRows(singleBlades.value, form.bladeCount, '叶片')
  const weights = blades.map((item) => item.weight)
  const sortedWeights = [...weights].sort((a, b) => b - a)
  const groups = getGroups(form.bladeCount)
  const angles = createAngles(form.bladeCount, 0)
  const arrangement = optimizeArrangement(groups, sortedWeights, angles)
  const indexResolver = createIndexResolver(blades)
  const rows = arrangement.split('').map((letter, index) => {
    const weight = sortedWeights[letter.charCodeAt(0) - 97]
    const originalIndex = indexResolver(weight)
    const original = blades[originalIndex - 1]
    return {
      key: `single-${index}`,
      angle: 360 * index / form.bladeCount,
      positionIndex: index + 1,
      originalIndex,
      originalLabel: `${originalIndex}#`,
      weight,
      code: original.code,
      spec: '叶片'
    }
  })

  return {
    mode: 'V1',
    bladeCount: form.bladeCount,
    rows,
    iz: arrangementIz(arrangement, sortedWeights, angles),
    arrangement
  }
}

function calculateDual() {
  const longRows = normalizeRows(longBlades.value, form.bladeCount, '长叶片')
  const shortRows = normalizeRows(shortBlades.value, form.bladeCount, '短叶片')
  const longWeights = longRows.map((item) => item.weight)
  const shortWeights = shortRows.map((item) => item.weight)
  const sortedLong = [...longWeights].sort((a, b) => b - a)
  const sortedShort = [...shortWeights].sort((a, b) => b - a)
  const groups = getGroups(form.bladeCount)
  const longAngles = createAngles(form.bladeCount, 0)
  const shortAnglesForSingle = createAngles(form.bladeCount, 0)
  const shortAngles = createAngles(form.bladeCount, Math.PI / form.bladeCount)
  const longArrangement = optimizeArrangement(groups, sortedLong, longAngles)
  const shortBaseArrangement = optimizeArrangement(groups, sortedShort, shortAnglesForSingle)
  const shortArrangement = bestRotatedShortArrangement(longArrangement, shortBaseArrangement, sortedLong, sortedShort, longAngles, shortAngles)
  const longResolver = createIndexResolver(longRows)
  const shortResolver = createIndexResolver(shortRows)
  const rows = []

  for (let index = 0; index < form.bladeCount; index += 1) {
    const longLetter = longArrangement[index]
    const longWeight = sortedLong[longLetter.charCodeAt(0) - 97]
    const longOriginalIndex = longResolver(longWeight)
    rows.push({
      key: `long-${index}`,
      angle: 360 * index / form.bladeCount,
      positionIndex: index + 1,
      originalIndex: longOriginalIndex,
      originalLabel: `${longOriginalIndex}#`,
      weight: longWeight,
      code: longRows[longOriginalIndex - 1].code,
      spec: '长叶片'
    })

    const shortLetter = shortArrangement[index]
    const shortWeight = sortedShort[shortLetter.charCodeAt(0) - 97]
    const shortOriginalIndex = shortResolver(shortWeight)
    rows.push({
      key: `short-${index}`,
      angle: 360 * index / form.bladeCount + 180 / form.bladeCount,
      positionIndex: index + 1,
      originalIndex: shortOriginalIndex,
      originalLabel: `${shortOriginalIndex}#'`,
      weight: shortWeight,
      code: shortRows[shortOriginalIndex - 1].code,
      spec: '短叶片'
    })
  }

  return {
    mode: 'V2',
    bladeCount: form.bladeCount,
    rows,
    iz: combinedIz(longArrangement, shortArrangement, sortedLong, sortedShort, longAngles, shortAngles),
    longArrangement,
    shortArrangement
  }
}

function normalizeRows(rows, count, label) {
  const source = rows.slice(0, count)
  return source.map((row, index) => {
    const weight = Number(row.weight)
    if (row.weight === '' || row.weight === null || Number.isNaN(weight)) {
      throw new Error(`${label}${index + 1}#重量不能为空。`)
    }
    if (weight < 0) {
      throw new Error(`${label}${index + 1}#重量不能小于 0。`)
    }
    return {
      code: row.code || '',
      weight
    }
  })
}

function getGroups(count) {
  const groups = ['a']
  if (count >= 4 && count <= 9) {
    return [groups[0], alphabet.slice(1, count)]
  }
  if (count >= 10 && count <= 13) {
    if (count === 10) return ['a', 'dehi', 'bcfgj']
    if (count === 11) return ['a', 'dehik', 'bcfgj']
    if (count === 12) return ['a', 'dehil', 'bcfgjk']
    return ['bghm', 'cfil', 'adejk']
  }
  if (count === 14) return ['afglm', 'behkn', 'cdij']
  if (count === 15) return ['afglm', 'behkn', 'cdijo']
  if (count === 16) return ['cfkn', 'bgjo', 'delm', 'ahip']
  if (count === 17) return ['a', 'chkp', 'dglo', 'bijq', 'efmn']
  if (count === 18) return ['bgjor', 'cfkn', 'ahipq', 'delm']
  if (count === 19) return ['bgjor', 'cfkns', 'ahipq', 'delm']
  if (count === 20) return ['bgjor', 'cfkns', 'ahipq', 'delmt']
  throw new Error('叶片数超出计算范围。')
}

function createAngles(count, offset) {
  return Array.from({ length: count }, (_, index) => 2 * Math.PI * index / count + offset)
}

function optimizeArrangement(groups, sortedWeights, angles) {
  const groupOptions = []
  let positionOffset = 0
  for (const group of groups) {
    groupOptions.push(createGroupOptions(group, positionOffset, sortedWeights, angles))
    positionOffset += group.length
  }

  const splitIndex = Math.max(1, Math.floor(groupOptions.length / 2))
  const leftOptions = combineOptionLists(groupOptions.slice(0, splitIndex))
  const rightOptions = combineOptionLists(groupOptions.slice(splitIndex))
  const best = closestVectorPair(leftOptions, rightOptions)
  return best.order
}

function createGroupOptions(group, positionOffset, sortedWeights, angles) {
  const chars = group.split('')
  const options = []
  permute(chars, 0, (orderChars) => {
    let x = 0
    let y = 0
    for (let index = 0; index < orderChars.length; index += 1) {
      const weight = sortedWeights[orderChars[index].charCodeAt(0) - 97]
      const angle = angles[positionOffset + index]
      x += weight * Math.cos(angle)
      y += weight * Math.sin(angle)
    }
    options.push({ order: orderChars.join(''), x, y })
  })
  return options
}

function permute(items, start, visit) {
  if (start === items.length - 1) {
    visit(items)
    return
  }
  for (let index = start; index < items.length; index += 1) {
    const tmp = items[start]
    items[start] = items[index]
    items[index] = tmp
    permute(items, start + 1, visit)
    items[index] = items[start]
    items[start] = tmp
  }
}

function combineOptionLists(optionLists) {
  if (!optionLists.length) return [{ order: '', x: 0, y: 0 }]
  let combined = [{ order: '', x: 0, y: 0 }]
  for (const options of optionLists) {
    const next = []
    for (const base of combined) {
      for (const option of options) {
        next.push({
          order: base.order + option.order,
          x: base.x + option.x,
          y: base.y + option.y
        })
      }
    }
    combined = next
  }
  return combined
}

function closestVectorPair(leftOptions, rightOptions) {
  const sortedRight = [...rightOptions].sort((a, b) => a.x - b.x)
  let best = null
  let bestSq = Number.POSITIVE_INFINITY

  for (const left of leftOptions) {
    const targetX = -left.x
    const pivot = lowerBoundByX(sortedRight, targetX)
    for (let index = pivot; index < sortedRight.length; index += 1) {
      const right = sortedRight[index]
      const dx = left.x + right.x
      if (dx * dx >= bestSq) break
      const dy = left.y + right.y
      const sq = dx * dx + dy * dy
      if (sq < bestSq) {
        bestSq = sq
        best = { order: left.order + right.order, x: left.x + right.x, y: left.y + right.y }
      }
    }
    for (let index = pivot - 1; index >= 0; index -= 1) {
      const right = sortedRight[index]
      const dx = left.x + right.x
      if (dx * dx >= bestSq) break
      const dy = left.y + right.y
      const sq = dx * dx + dy * dy
      if (sq < bestSq) {
        bestSq = sq
        best = { order: left.order + right.order, x: left.x + right.x, y: left.y + right.y }
      }
    }
  }

  return best || { order: leftOptions[0].order + rightOptions[0].order, x: 0, y: 0 }
}

function lowerBoundByX(items, target) {
  let low = 0
  let high = items.length
  while (low < high) {
    const mid = Math.floor((low + high) / 2)
    if (items[mid].x < target) low = mid + 1
    else high = mid
  }
  return low
}

function arrangementIz(arrangement, sortedWeights, angles) {
  let x = 0
  let y = 0
  for (let index = 0; index < arrangement.length; index += 1) {
    const weight = sortedWeights[arrangement[index].charCodeAt(0) - 97]
    x += weight * Math.cos(angles[index])
    y += weight * Math.sin(angles[index])
  }
  return Math.sqrt(x * x + y * y)
}

function combinedIz(longArrangement, shortArrangement, sortedLong, sortedShort, longAngles, shortAngles) {
  let x = 0
  let y = 0
  for (let index = 0; index < longArrangement.length; index += 1) {
    const longWeight = sortedLong[longArrangement[index].charCodeAt(0) - 97]
    const shortWeight = sortedShort[shortArrangement[index].charCodeAt(0) - 97]
    x += longWeight * Math.cos(longAngles[index]) + shortWeight * Math.cos(shortAngles[index])
    y += longWeight * Math.sin(longAngles[index]) + shortWeight * Math.sin(shortAngles[index])
  }
  return Math.sqrt(x * x + y * y)
}

function bestRotatedShortArrangement(longArrangement, shortBaseArrangement, sortedLong, sortedShort, longAngles, shortAngles) {
  let bestOrder = shortBaseArrangement
  let bestIz = Number.POSITIVE_INFINITY
  let current = shortBaseArrangement
  for (let index = 0; index < shortBaseArrangement.length; index += 1) {
    const iz = combinedIz(longArrangement, current, sortedLong, sortedShort, longAngles, shortAngles)
    if (iz < bestIz) {
      bestIz = iz
      bestOrder = current
    }
    current = current.slice(1) + current[0]
  }
  return bestOrder
}

function createIndexResolver(rows) {
  const used = new Set()
  return (weight) => {
    for (let index = 0; index < rows.length; index += 1) {
      if (!used.has(index) && rows[index].weight === weight) {
        used.add(index)
        return index + 1
      }
    }
    return rows.findIndex((row) => row.weight === weight) + 1
  }
}

function formatNumber(value, digits) {
  if (!Number.isFinite(value)) return '-'
  return Number(value.toFixed(digits)).toString()
}

function formatWeight(value) {
  return Number.isInteger(value) ? String(value) : String(value)
}
</script>

<style scoped>
.blade-page {
  width: 100%;
  padding-right: var(--page-content-gap, 20px);
}

.workbench {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: var(--spacing-base);
  align-items: start;
}

.setup-card,
.note-card,
.report-card {
  background: var(--color-bg-container);
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
}

.setup-card {
  overflow: hidden;
}

.card-section {
  padding: var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
}

.card-section:last-child {
  border-bottom: none;
}

.section-title {
  margin-bottom: var(--spacing-base);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(180px, 1fr));
  gap: var(--spacing-base);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.table-wrap {
  width: 100%;
  overflow-x: auto;
}

.result-table-wrap {
  position: relative;
  padding-bottom: 42px;
}

.copy-table-image-btn {
  position: absolute;
  right: 0;
  bottom: 0;
  z-index: 2;
  padding: 6px 12px;
  font-size: var(--font-size-xs);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-base);
  background: #fff;
  color: var(--color-text-primary);
  cursor: pointer;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.copy-table-image-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.copy-table-image-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.input-table,
.result-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.input-table th,
.input-table td,
.result-table th,
.result-table td {
  border: 1px solid var(--color-border-light);
  padding: 10px 12px;
  text-align: center;
  font-size: var(--font-size-sm);
}

.input-table th,
.result-table th {
  background: #f5f7fa;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.cell-input {
  width: 100%;
  height: 34px;
  border: 1px solid transparent;
  border-radius: var(--radius-base);
  padding: 0 10px;
  background: #fff;
  outline: none;
  text-align: center;
}

.cell-input:hover,
.cell-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-lightest);
}

.note-card {
  padding: var(--spacing-xl);
}

.note-card ul {
  margin: 0;
  padding-left: 18px;
  color: var(--color-text-secondary);
  line-height: 1.9;
}

.error-text {
  margin-top: var(--spacing-base);
  color: var(--color-error);
}

.save-message {
  margin-top: var(--spacing-base);
  color: var(--color-success, #16a34a);
}

.report-card {
  margin-top: var(--spacing-base);
  padding: 0;
  overflow: hidden;
}

.report-header {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr) 220px;
  min-height: 72px;
  border-bottom: 1px solid var(--color-border-light);
}

.report-logo,
.report-title,
.report-meta {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-right: 1px solid var(--color-border-light);
}

.report-logo {
  justify-content: center;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-dark);
  background: var(--color-primary-lightest);
}

.report-title {
  justify-content: center;
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  text-align: center;
}

.report-meta {
  flex-direction: column;
  align-items: stretch;
  justify-content: center;
  gap: 8px;
  border-right: none;
  color: var(--color-text-secondary);
}

.blank-text {
  display: inline-block;
  min-width: 72px;
  padding: 0 4px;
  border-bottom: 1px solid var(--color-text-primary);
}

.result-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  background: var(--color-border-lighter);
  border-bottom: 1px solid var(--color-border-light);
}

.result-summary > div {
  padding: 14px 18px;
  background: #fff;
}

.summary-label {
  display: block;
  margin-bottom: 4px;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-xs);
}

.result-layout {
  display: grid;
  grid-template-columns: minmax(520px, 1fr) 440px;
  gap: var(--spacing-xl);
  padding: var(--spacing-xl);
  align-items: start;
}

.row-muted {
  background: #f7f8fa;
}

.diagram-panel {
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: var(--spacing-base);
  background: #fbfcfe;
}

.diagram-title {
  margin-bottom: var(--spacing-sm);
  text-align: center;
  font-weight: var(--font-weight-semibold);
}

.diagram-figure-wrap {
  position: relative;
  padding-bottom: 42px;
}

.blade-diagram {
  width: 100%;
  height: auto;
  display: block;
}

.diagram-ring {
  fill: none;
  stroke: #a7b7cc;
  stroke-width: 2;
}

.diagram-center {
  fill: #eef6ff;
  stroke: #a7b7cc;
  stroke-width: 2;
}

.diagram-spoke {
  stroke: #dbe4ef;
  stroke-width: 1;
}

.long-node {
  fill: #e6f7ff;
  stroke: #1890ff;
  stroke-width: 2;
}

.short-node {
  fill: #fff7e6;
  stroke: #faad14;
  stroke-width: 2;
}

.diagram-point text {
  font-size: 14px;
  font-weight: 700;
  fill: #263445;
  dominant-baseline: middle;
}

.diagram-point .node-sub {
  font-size: 11px;
  font-weight: 500;
  fill: #5f6f83;
}

.report-footer {
  display: flex;
  gap: var(--spacing-xxl);
  padding: var(--spacing-lg) var(--spacing-xl);
  border-top: 1px solid var(--color-border-light);
  font-size: var(--font-size-md);
}

.plain-input {
  width: 160px;
  border: none;
  border-bottom: 1px solid var(--color-text-secondary);
  outline: none;
  font-size: inherit;
  text-align: center;
}

.history-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgb(15 23 42 / 42%);
}

.history-modal {
  width: min(1080px, 100%);
  max-height: min(760px, calc(100vh - 48px));
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: var(--radius-md);
  box-shadow: 0 18px 48px rgb(15 23 42 / 24%);
  overflow: hidden;
}

.history-header,
.history-toolbar,
.history-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-base);
  padding: var(--spacing-base) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
}

.history-header h2 {
  margin: 0 0 4px;
  font-size: var(--font-size-xl);
  color: var(--color-text-primary);
}

.history-header p {
  margin: 0;
  color: var(--color-text-secondary);
}

.history-close {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: var(--radius-base);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
}

.history-close:hover {
  background: #f5f7fa;
  color: var(--color-text-primary);
}

.history-toolbar .input {
  min-width: 0;
  flex: 1;
}

.history-error {
  padding: 10px var(--spacing-xl);
  color: var(--color-error);
  background: #fff2f0;
  border-bottom: 1px solid #ffccc7;
}

.history-body {
  min-height: 260px;
  overflow: auto;
}

.history-empty {
  padding: 64px var(--spacing-xl);
  text-align: center;
  color: var(--color-text-secondary);
}

.history-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.history-table th,
.history-table td {
  padding: 12px;
  border-bottom: 1px solid var(--color-border-lighter);
  text-align: left;
  font-size: var(--font-size-sm);
  vertical-align: middle;
}

.history-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f5f7fa;
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
}

.history-table small {
  display: block;
  margin-top: 4px;
  color: var(--color-text-tertiary);
  line-height: 1.4;
}

.history-footer {
  border-top: 1px solid var(--color-border-lighter);
  border-bottom: none;
  color: var(--color-text-secondary);
}

.history-footer > div {
  display: flex;
  gap: var(--spacing-sm);
}

@media (max-width: 1180px) {
  .workbench,
  .result-layout {
    grid-template-columns: 1fr;
  }

  .result-layout {
    gap: var(--spacing-base);
  }
}

@media (max-width: 768px) {
  .field-grid,
  .result-summary,
  .report-header {
    grid-template-columns: 1fr;
  }

  .report-logo,
  .report-title,
  .report-meta {
    border-right: none;
    border-bottom: 1px solid var(--color-border-light);
  }

  .report-meta {
    border-bottom: none;
  }

  .result-layout {
    padding: var(--spacing-base);
  }

  .report-footer {
    flex-direction: column;
    gap: var(--spacing-base);
  }

  .history-overlay {
    padding: 12px;
  }

  .history-header,
  .history-toolbar,
  .history-footer {
    align-items: stretch;
    flex-direction: column;
  }
}

@media print {
  @page {
    size: A4 portrait;
    margin: 8mm;
  }

  :global(body.printing-report-only) {
    margin: 0 !important;
    background: #fff !important;
  }

  :global(body.printing-report-only *) {
    visibility: hidden !important;
  }

  :global(body.printing-report-only .report-card),
  :global(body.printing-report-only .report-card *) {
    visibility: visible !important;
  }

  :global(body.printing-report-only .no-print),
  :global(body.printing-report-only .page-header),
  :global(body.printing-report-only .app-sidebar),
  :global(body.printing-report-only .app-header),
  :global(body.printing-report-only .app-footer) {
    display: none !important;
  }

  .report-card {
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    width: 194mm !important;
    max-width: 194mm !important;
    margin: 0 !important;
    border: none !important;
    box-shadow: none !important;
    overflow: visible !important;
    background: #fff !important;
    color: #000 !important;
    break-inside: avoid;
    page-break-inside: avoid;
    print-color-adjust: exact;
    -webkit-print-color-adjust: exact;
  }

  .report-header {
    grid-template-columns: 34mm minmax(0, 1fr) 42mm;
    min-height: 16mm;
  }

  .report-logo,
  .report-title,
  .report-meta {
    padding: 2.5mm 3mm;
  }

  .report-logo {
    font-size: 11pt;
  }

  .report-title {
    font-size: 12pt;
    line-height: 1.35;
  }

  .report-meta {
    gap: 1.5mm;
    font-size: 8.5pt;
  }

  .blank-text {
    min-width: 16mm;
  }

  .result-summary > div {
    padding: 2.5mm 3mm;
    font-size: 9pt;
  }

  .summary-label {
    margin-bottom: 1mm;
    font-size: 7.5pt;
  }

  .result-layout {
    grid-template-columns: minmax(0, 1fr) 72mm;
    gap: 4mm;
    padding: 4mm;
  }

  .input-table th,
  .input-table td,
  .result-table th,
  .result-table td {
    padding: 1.7mm 1.5mm;
    font-size: 8.5pt;
    line-height: 1.2;
  }

  .diagram-panel {
    padding: 2.5mm;
    page-break-inside: avoid;
    break-inside: avoid;
  }

  .diagram-figure-wrap {
    padding-bottom: 0;
  }

  .diagram-title {
    margin-bottom: 1.5mm;
    font-size: 9pt;
  }

  .blade-diagram {
    max-height: 70mm;
  }

  .diagram-point text {
    font-size: 12px;
  }

  .diagram-point .node-sub {
    font-size: 10px;
  }

  .report-footer {
    gap: 16mm;
    padding: 3mm 4mm;
    font-size: 10pt;
  }
}
</style>
