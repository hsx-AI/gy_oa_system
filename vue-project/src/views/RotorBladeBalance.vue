<template>
  <div class="blade-page">
    <section class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">转轮叶片配重工艺程序</h1>
          <p class="header-subtitle">复刻原230系统功能，按叶片重量优化排列，计算综合偏心矩 IZ。</p>
        </div>
        <div class="header-actions no-print">
          <button type="button" class="btn" @click="resetForm">重置</button>
          <button type="button" class="btn" :disabled="!result" @click="printPage">打印</button>
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
          <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
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

      <div class="result-summary">
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
          <table class="result-table">
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
        </div>

        <div class="diagram-panel">
          <div class="diagram-title">程序优化排列示意图</div>
          <svg class="blade-diagram" viewBox="0 0 520 520" role="img" aria-label="叶片优化排列示意图">
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
        </div>
      </div>

      <div class="report-footer">
        <label>编制：<input v-model.trim="meta.compiler" type="text" class="plain-input"></label>
        <label>校核：<input v-model.trim="meta.checker" type="text" class="plain-input"></label>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'

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
const reportRef = ref(null)

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
  result.value = null
}

function resetForm() {
  form.mode = 'V1'
  form.bladeCount = 4
  singleBlades.value = createRows(4)
  longBlades.value = createRows(4)
  shortBlades.value = createRows(4)
  result.value = null
  errorMessage.value = ''
}

function printPage() {
  window.print()
}

function calculate() {
  errorMessage.value = ''
  try {
    result.value = form.mode === 'V1' ? calculateSingle() : calculateDual()
  } catch (error) {
    result.value = null
    errorMessage.value = error.message || '计算失败，请检查输入。'
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
}

@media print {
  .no-print,
  .page-header,
  .app-sidebar,
  .app-header,
  .app-footer {
    display: none !important;
  }

  .blade-page {
    padding: 0;
  }

  .report-card {
    margin: 0;
    border: none;
    box-shadow: none;
  }

  .result-layout {
    grid-template-columns: 1fr;
  }

  .diagram-panel {
    page-break-inside: avoid;
  }
}
</style>
