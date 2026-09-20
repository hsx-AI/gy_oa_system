<template>
  <aside class="att-side-panel">
    <div class="att-side-panel__head">
      <div>
        <h3 class="att-side-panel__title">我的打卡记录</h3>
        <p class="att-side-panel__sub">单击填开始，Shift+单击填结束</p>
      </div>
      <input
        v-model="selectedMonth"
        type="month"
        class="att-side-panel__month"
        aria-label="选择月份"
        @change="loadRecords"
      >
    </div>
    <div class="att-side-panel__meta">
      <span>共 {{ records.length }} 条</span>
      <span v-if="hintText" class="att-side-panel__hint">{{ hintText }}</span>
      <button type="button" class="att-side-panel__refresh" :disabled="loading" @click="loadRecords">
        {{ loading ? '加载中…' : '刷新' }}
      </button>
    </div>
    <div class="att-side-panel__body">
      <div v-if="loading && !records.length" class="att-side-panel__empty">加载中...</div>
      <div v-else-if="!records.length" class="att-side-panel__empty">该月暂无打卡记录</div>
      <div v-else class="att-side-panel__list">
        <article v-for="record in records" :key="record.id" class="att-day-card">
          <div class="att-day-card__top">
            <div class="att-day-card__date">{{ record.attendance_date }}</div>
            <button
              v-if="filledSlots(record).length >= 1"
              type="button"
              class="att-day-card__range"
              title="首条打卡填开始，末条打卡填结束"
              @click="fillDayRange(record)"
            >整段填入</button>
          </div>
          <div class="att-day-card__times">
            <template v-if="filledSlots(record).length">
              <button
                v-for="slot in filledSlots(record)"
                :key="`${record.id}-${slot}`"
                type="button"
                class="att-time-chip"
                :title="chipTitle(record, slot)"
                @click="onChipClick($event, record, slot)"
              >
                <span
                  v-if="hasAttendanceTimeMark(record, slot)"
                  class="att-time-chip__mark"
                  :class="isOutAttendanceMark(record, slot) ? 'is-out' : 'is-in'"
                >{{ isOutAttendanceMark(record, slot) ? '出' : '进' }}</span>
                <span class="att-time-chip__time">{{ record['time_' + slot] }}</span>
              </button>
            </template>
            <span v-else class="att-day-card__none">无打卡</span>
          </div>
        </article>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, watch } from 'vue'
import { queryAttendance } from '@/api/attendance'
import { hasAttendanceTimeMark, isOutAttendanceMark } from '@/utils/attendanceTimeMark'

const props = defineProps({
  /** 弹窗打开时为 true，触发加载 */
  active: { type: Boolean, default: false },
  /** 员工姓名；为空时从 localStorage 读取 */
  employeeName: { type: String, default: '' },
})

const emit = defineEmits(['fill-time'])

const TIME_SLOTS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

function defaultMonth() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

const selectedMonth = ref(defaultMonth())
const records = ref([])
const loading = ref(false)
const hintText = ref('')
let hintTimer = null

function resolveName() {
  const fromProp = (props.employeeName || '').trim()
  if (fromProp) return fromProp
  try {
    const info = JSON.parse(localStorage.getItem('userInfo') || '{}')
    return (info.name || info.userName || '').trim()
  } catch {
    return ''
  }
}

function filledSlots(record) {
  return TIME_SLOTS.filter((n) => {
    const t = record?.[`time_${n}`]
    return t != null && String(t).trim() !== '' && t !== '-'
  })
}

function normalizeTime(raw) {
  const s = String(raw || '').trim()
  if (!s) return ''
  const parts = s.split(':')
  if (parts.length < 2) return ''
  const h = String(Math.min(23, Math.max(0, parseInt(parts[0], 10) || 0))).padStart(2, '0')
  const m = String(Math.min(59, Math.max(0, parseInt(parts[1], 10) || 0))).padStart(2, '0')
  const sec = parts.length >= 3
    ? String(Math.min(59, Math.max(0, parseInt(parts[2], 10) || 0))).padStart(2, '0')
    : '00'
  return `${h}:${m}:${sec}`
}

function normalizeDate(raw) {
  const s = String(raw || '').trim().slice(0, 10)
  const parts = s.split('-')
  if (parts.length < 3) return s
  return `${parts[0]}-${parts[1].padStart(2, '0')}-${parts[2].padStart(2, '0')}`
}

function buildPayload(field, dateRaw, timeRaw) {
  const date = normalizeDate(dateRaw)
  const time = normalizeTime(timeRaw)
  if (!date || !time) return null
  return {
    field,
    date,
    time,
    datetime: `${date}T${time}`,
  }
}

function showHint(text) {
  hintText.value = text
  if (hintTimer) clearTimeout(hintTimer)
  hintTimer = setTimeout(() => { hintText.value = '' }, 1800)
}

function emitFill(field, dateRaw, timeRaw) {
  const payload = buildPayload(field, dateRaw, timeRaw)
  if (!payload) return
  emit('fill-time', payload)
  showHint(field === 'start' ? `已填开始 ${payload.time}` : `已填结束 ${payload.time}`)
}

function chipTitle(record, slot) {
  const mark = hasAttendanceTimeMark(record, slot)
    ? (isOutAttendanceMark(record, slot) ? '出' : '进')
    : '打卡'
  return `${mark} ${record['time_' + slot]}｜单击填开始，Shift+单击填结束`
}

function onChipClick(event, record, slot) {
  const field = event.shiftKey ? 'end' : 'start'
  emitFill(field, record.attendance_date, record[`time_${slot}`])
}

function fillDayRange(record) {
  const slots = filledSlots(record)
  if (!slots.length) return
  const first = slots[0]
  const last = slots[slots.length - 1]
  emitFill('start', record.attendance_date, record[`time_${first}`])
  emitFill('end', record.attendance_date, record[`time_${last}`])
  showHint('已填入首末打卡时段')
}

async function loadRecords() {
  const name = resolveName()
  if (!name || !selectedMonth.value?.includes('-')) {
    records.value = []
    return
  }
  loading.value = true
  try {
    const [year, month] = selectedMonth.value.split('-')
    const startDate = `${year}-${month}-01`
    const lastDay = new Date(parseInt(year, 10), parseInt(month, 10), 0).getDate()
    const endDate = `${year}-${month}-${String(lastDay).padStart(2, '0')}`
    const response = await queryAttendance({
      name,
      start_date: startDate,
      end_date: endDate,
    })
    if (response?.success && Array.isArray(response.data)) {
      records.value = response.data.map((row, index) => ({ id: index + 1, ...row }))
    } else {
      records.value = []
    }
  } catch {
    records.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.active, props.employeeName],
  ([active]) => {
    if (active) {
      if (!selectedMonth.value) selectedMonth.value = defaultMonth()
      loadRecords()
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.att-side-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
  background: #f8fafc;
  border: 1px solid var(--color-border-lighter, #e5e7eb);
  border-radius: var(--radius-md, 8px);
  overflow: hidden;
}

.att-side-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px 8px;
  border-bottom: 1px solid var(--color-border-lighter, #e5e7eb);
  background: #fff;
}

.att-side-panel__title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary, #0f172a);
}

.att-side-panel__sub {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-text-tertiary, #94a3b8);
}

.att-side-panel__month {
  flex-shrink: 0;
  padding: 4px 8px;
  border: 1px solid var(--color-border-base, #cbd5e1);
  border-radius: 6px;
  font-size: 13px;
  background: #fff;
  color: var(--color-text-primary, #0f172a);
}

.att-side-panel__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 14px;
  font-size: 12px;
  color: var(--color-text-secondary, #64748b);
  background: #fff;
  border-bottom: 1px solid var(--color-border-lighter, #e5e7eb);
}

.att-side-panel__hint {
  flex: 1;
  text-align: center;
  color: var(--color-primary, #1890ff);
  font-weight: 500;
}

.att-side-panel__refresh {
  border: none;
  background: none;
  color: var(--color-primary, #1890ff);
  font-size: 12px;
  cursor: pointer;
  padding: 0;
}

.att-side-panel__refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.att-side-panel__body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px 12px 12px;
}

.att-side-panel__empty {
  padding: 32px 12px;
  text-align: center;
  font-size: 13px;
  color: var(--color-text-tertiary, #94a3b8);
}

.att-side-panel__list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.att-day-card {
  background: #fff;
  border: 1px solid var(--color-border-lighter, #e5e7eb);
  border-radius: 8px;
  padding: 8px 10px;
}

.att-day-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.att-day-card__date {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary, #0f172a);
}

.att-day-card__range {
  border: 1px solid rgba(24, 144, 255, 0.35);
  background: #e6f4ff;
  color: #1677ff;
  border-radius: 999px;
  font-size: 11px;
  padding: 2px 8px;
  cursor: pointer;
  line-height: 1.4;
}

.att-day-card__range:hover {
  background: #bae0ff;
}

.att-day-card__times {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.att-day-card__none {
  font-size: 12px;
  color: var(--color-text-tertiary, #94a3b8);
}

.att-time-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border-radius: 999px;
  background: #f1f5f9;
  border: 1px solid transparent;
  font-size: 12px;
  color: var(--color-text-primary, #0f172a);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, box-shadow 0.15s;
}

.att-time-chip:hover {
  background: #e6f4ff;
  border-color: rgba(24, 144, 255, 0.35);
  box-shadow: 0 1px 4px rgba(24, 144, 255, 0.18);
}

.att-time-chip__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
  color: #fff;
}

.att-time-chip__mark.is-in {
  background: #16a34a;
}

.att-time-chip__mark.is-out {
  background: #ea580c;
}

.att-time-chip__time {
  font-variant-numeric: tabular-nums;
}
</style>
