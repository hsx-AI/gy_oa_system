<template>
  <div class="tp">
    <div class="tp__row">
      <select class="tp__hour" :value="innerHour" @change="onHourChange" :disabled="disabled">
        <option v-for="h in hourOptions" :key="h.value" :value="h.value">{{ h.label }}</option>
      </select>
      <span class="tp__sep">:</span>
      <select class="tp__minute" :value="innerMinute" @change="onMinuteChange" :disabled="disabled || innerHour === 24">
        <option v-for="m in minuteOptions" :key="m" :value="m">{{ String(m).padStart(2, '0') }}</option>
      </select>
    </div>
    <div class="tp__presets" v-if="!disabled">
      <button
        v-for="p in presets"
        :key="p.h + '-' + p.m"
        type="button"
        class="tp__preset-btn"
        :class="{ 'tp__preset-btn--active': innerHour === p.h && innerMinute === p.m }"
        @click="applyPreset(p)"
      >{{ p.label }}</button>
    </div>
    <p v-if="timeHint" class="tp__hint">{{ timeHint }}</p>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  withSeconds: { type: Boolean, default: true }
})

const emit = defineEmits(['update:modelValue'])

const innerHour = ref(8)
const innerMinute = ref(0)

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
  const opts = []
  for (let m = 0; m < 60; m++) opts.push(m)
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
    return '即当天零点（一天的最开始）'
  }
  if (innerHour.value === 24) {
    return '即当天结束（次日零点），通常用于结束时间'
  }
  return ''
})

function parseModelValue(val) {
  if (!val || typeof val !== 'string') return { hour: 8, minute: 0 }
  const s = val.trim()
  const parts = s.split(':')
  if (parts.length < 2) return { hour: 8, minute: 0 }
  const h = parseInt(parts[0], 10)
  const m = parseInt(parts[1], 10)
  if (isNaN(h) || isNaN(m)) return { hour: 8, minute: 0 }
  return { hour: Math.min(24, Math.max(0, h)), minute: Math.min(59, Math.max(0, m)) }
}

function emitValue() {
  const hh = String(innerHour.value).padStart(2, '0')
  const mm = String(innerMinute.value).padStart(2, '0')
  const base = `${hh}:${mm}`
  emit('update:modelValue', props.withSeconds ? base + ':00' : base)
}

let skipSync = false

watch(() => props.modelValue, (val) => {
  if (skipSync) { skipSync = false; return }
  const parsed = parseModelValue(val)
  innerHour.value = parsed.hour
  innerMinute.value = parsed.minute
}, { immediate: true })

function onHourChange(e) {
  innerHour.value = parseInt(e.target.value, 10)
  if (innerHour.value === 24) innerMinute.value = 0
  skipSync = true
  emitValue()
}

function onMinuteChange(e) {
  innerMinute.value = parseInt(e.target.value, 10)
  skipSync = true
  emitValue()
}

function applyPreset(p) {
  innerHour.value = p.h
  innerMinute.value = p.m
  skipSync = true
  emitValue()
}
</script>

<style scoped>
.tp__row {
  display: flex;
  align-items: center;
  gap: 2px;
}

.tp__hour,
.tp__minute {
  padding: 8px 4px;
  border: 1px solid var(--color-border-base, #d9d9d9);
  border-radius: var(--radius-sm, 4px);
  font-size: var(--font-size-base, 14px);
  background: white;
  transition: border-color 0.2s;
  cursor: pointer;
}

.tp__hour {
  flex: 1;
  min-width: 0;
}

.tp__minute {
  width: 60px;
  flex-shrink: 0;
}

.tp__hour:focus,
.tp__minute:focus {
  border-color: var(--color-primary, #1677ff);
  outline: none;
}

.tp__hour:disabled,
.tp__minute:disabled {
  background: var(--color-bg-layout, #f5f5f5);
  cursor: not-allowed;
}

.tp__sep {
  font-weight: 600;
  font-size: 16px;
  color: var(--color-text-secondary, #666);
  user-select: none;
}

.tp__presets {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.tp__preset-btn {
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

.tp__preset-btn:hover {
  border-color: var(--color-primary, #1677ff);
  color: var(--color-primary, #1677ff);
  background: white;
}

.tp__preset-btn--active {
  border-color: var(--color-primary, #1677ff);
  color: white;
  background: var(--color-primary, #1677ff);
}

.tp__preset-btn--active:hover {
  color: white;
  background: var(--color-primary-light, #4096ff);
}

.tp__hint {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-primary, #1677ff);
  line-height: 1.4;
}
</style>
