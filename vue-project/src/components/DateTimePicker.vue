<template>
  <div class="dtp">
    <div class="dtp__row">
      <input
        type="date"
        class="dtp__date"
        :value="innerDate"
        @input="onDateInput"
        :disabled="disabled"
      >
      <div class="dtp__time">
        <select class="dtp__hour" :value="innerHour" @change="onHourChange" :disabled="disabled">
          <option v-for="h in hourOptions" :key="h.value" :value="h.value">{{ h.label }}</option>
        </select>
        <span class="dtp__sep">:</span>
        <select class="dtp__minute" :value="innerMinute" @change="onMinuteChange" :disabled="disabled || innerHour === 24">
          <option v-for="m in minuteOptions" :key="m" :value="m">{{ String(m).padStart(2, '0') }}</option>
        </select>
        <span class="dtp__sep">:</span>
        <select class="dtp__second" :value="innerSecond" @change="onSecondChange" :disabled="disabled || innerHour === 24">
          <option v-for="sec in secondOptions" :key="sec" :value="sec">{{ String(sec).padStart(2, '0') }}</option>
        </select>
      </div>
    </div>
    <div class="dtp__presets" v-if="!disabled">
      <button
        v-for="p in presets"
        :key="p.h + '-' + p.m"
        type="button"
        class="dtp__preset-btn"
        :class="{ 'dtp__preset-btn--active': innerHour === p.h && innerMinute === p.m && innerSecond === 0 }"
        @click="applyPreset(p)"
      >{{ p.label }}</button>
    </div>
    <p v-if="timeHint" class="dtp__hint">{{ timeHint }}</p>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  minuteStep: { type: Number, default: 1 }
})

const emit = defineEmits(['update:modelValue'])

const innerDate = ref('')
const innerHour = ref(8)
const innerMinute = ref(0)
const innerSecond = ref(0)

const hourOptions = computed(() => {
  const opts = []
  for (let h = 0; h <= 24; h++) {
    let label = String(h).padStart(2, '0')
    if (h === 0) label += ' (当天开始)'
    else if (h === 24) label += ' (当天结束)'
    opts.push({ value: h, label })
  }
  return opts
})

const minuteOptions = computed(() => {
  const step = props.minuteStep || 1
  const opts = []
  for (let m = 0; m < 60; m += step) opts.push(m)
  return opts
})

const secondOptions = computed(() => {
  const opts = []
  for (let s = 0; s < 60; s++) opts.push(s)
  return opts
})

const presets = [
  { h: 0, m: 0, label: '00:00 当天开始' },
  { h: 8, m: 0, label: '08:00' },
  { h: 12, m: 0, label: '12:00' },
  { h: 13, m: 0, label: '13:00' },
  { h: 17, m: 0, label: '17:00' },
  { h: 24, m: 0, label: '24:00 当天结束' }
]

const timeHint = computed(() => {
  if (innerHour.value === 0 && innerMinute.value === 0) {
    const dateLabel = innerDate.value || '所选日期'
    return `即 ${dateLabel} 零点，这一天的最开始`
  }
  if (innerHour.value === 24) {
    const dateLabel = innerDate.value || '所选日期'
    return `即 ${dateLabel} 的结束（次日零点），通常用于结束时间`
  }
  return ''
})

function parseModelValue(val) {
  if (!val || typeof val !== 'string') return { date: '', hour: 8, minute: 0, second: 0 }
  const s = val.trim().replace(' ', 'T')
  const match = s.match(/^(\d{4}-\d{2}-\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2}))?)?/)
  if (!match) return { date: '', hour: 8, minute: 0, second: 0 }
  return {
    date: match[1],
    hour: match[2] != null ? parseInt(match[2], 10) : 8,
    minute: match[3] != null ? parseInt(match[3], 10) : 0,
    second: match[4] != null ? parseInt(match[4], 10) : 0
  }
}

function emitValue() {
  if (!innerDate.value) {
    emit('update:modelValue', '')
    return
  }
  let d = innerDate.value
  let h = innerHour.value
  let m = innerMinute.value
  let sec = innerSecond.value
  if (h === 24) {
    const dt = new Date(d + 'T00:00:00')
    dt.setDate(dt.getDate() + 1)
    const y = dt.getFullYear()
    const mo = String(dt.getMonth() + 1).padStart(2, '0')
    const da = String(dt.getDate()).padStart(2, '0')
    d = `${y}-${mo}-${da}`
    h = 0
    m = 0
    sec = 0
  }
  const hh = String(h).padStart(2, '0')
  const mm = String(m).padStart(2, '0')
  const ss = String(sec).padStart(2, '0')
  emit('update:modelValue', `${d}T${hh}:${mm}:${ss}`)
}

let skipSync = false

watch(() => props.modelValue, (val) => {
  if (skipSync) { skipSync = false; return }
  const parsed = parseModelValue(val)
  innerDate.value = parsed.date
  innerHour.value = parsed.hour
  innerMinute.value = parsed.minute
  innerSecond.value = Math.min(59, Math.max(0, parsed.second || 0))
}, { immediate: true })

function onDateInput(e) {
  innerDate.value = e.target.value
  skipSync = true
  emitValue()
}

function onHourChange(e) {
  innerHour.value = parseInt(e.target.value, 10)
  if (innerHour.value === 24) {
    innerMinute.value = 0
    innerSecond.value = 0
  }
  skipSync = true
  emitValue()
}

function onMinuteChange(e) {
  innerMinute.value = parseInt(e.target.value, 10)
  skipSync = true
  emitValue()
}

function onSecondChange(e) {
  innerSecond.value = parseInt(e.target.value, 10)
  skipSync = true
  emitValue()
}

function applyPreset(p) {
  innerHour.value = p.h
  innerMinute.value = p.m
  innerSecond.value = 0
  skipSync = true
  emitValue()
}
</script>

<style scoped>
.dtp__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.dtp__date {
  flex: 1 1 auto;
  min-width: 130px;
  padding: 8px 12px;
  border: 1px solid var(--color-border-base, #d9d9d9);
  border-radius: var(--radius-sm, 4px);
  font-size: var(--font-size-base, 14px);
  transition: border-color 0.2s;
}

.dtp__date:focus {
  border-color: var(--color-primary, #1677ff);
  outline: none;
}

.dtp__time {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}

.dtp__hour,
.dtp__minute,
.dtp__second {
  padding: 8px 4px;
  border: 1px solid var(--color-border-base, #d9d9d9);
  border-radius: var(--radius-sm, 4px);
  font-size: var(--font-size-base, 14px);
  background: white;
  transition: border-color 0.2s;
  cursor: pointer;
}

.dtp__hour {
  min-width: 148px;
  width: 168px;
  max-width: 100%;
}

.dtp__minute,
.dtp__second {
  width: 56px;
}

.dtp__hour:focus,
.dtp__minute:focus,
.dtp__second:focus {
  border-color: var(--color-primary, #1677ff);
  outline: none;
}

.dtp__hour:disabled,
.dtp__minute:disabled,
.dtp__second:disabled {
  background: var(--color-bg-layout, #f5f5f5);
  cursor: not-allowed;
}

.dtp__sep {
  font-weight: 600;
  font-size: 16px;
  color: var(--color-text-secondary, #666);
  user-select: none;
}

.dtp__presets {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.dtp__preset-btn {
  padding: 2px 8px;
  font-size: 12px;
  border: 1px solid var(--color-border-lighter, #e8e8e8);
  border-radius: 12px;
  background: var(--color-bg-spotlight, #fafafa);
  color: var(--color-text-secondary, #666);
  cursor: pointer;
  transition: all 0.15s;
  line-height: 1.6;
}

.dtp__preset-btn:hover {
  border-color: var(--color-primary, #1677ff);
  color: var(--color-primary, #1677ff);
  background: white;
}

.dtp__preset-btn--active {
  border-color: var(--color-primary, #1677ff);
  color: white;
  background: var(--color-primary, #1677ff);
}

.dtp__preset-btn--active:hover {
  color: white;
  background: var(--color-primary-light, #4096ff);
}

.dtp__hint {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-primary, #1677ff);
  line-height: 1.4;
}
</style>
