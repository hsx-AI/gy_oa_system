<template>
  <div ref="rootRef" class="searchable-select" :class="{ 'is-open': open }">
    <div class="searchable-select-field">
      <input
        ref="inputRef"
        type="text"
        class="searchable-select-input"
        :value="inputText"
        :placeholder="placeholder"
        autocomplete="off"
        @input="onInput"
        @focus="onFocus"
        @keydown.down.prevent="moveHighlight(1)"
        @keydown.up.prevent="moveHighlight(-1)"
        @keydown.enter.prevent="confirmHighlight"
        @keydown.escape.prevent="closeDropdown"
      />
      <button
        v-if="modelValue"
        type="button"
        class="searchable-select-clear"
        tabindex="-1"
        aria-label="清空"
        @mousedown.prevent
        @click="clearSelection"
      >
        ×
      </button>
    </div>
    <ul
      v-if="open && filteredOptions.length"
      class="searchable-select-dropdown"
      role="listbox"
    >
      <li
        v-for="(opt, idx) in filteredOptions"
        :key="optionKey(opt, idx)"
        role="option"
        :class="{ active: idx === highlightIndex }"
        @mousedown.prevent="selectOption(opt)"
      >
        {{ displayLabel(opt) }}
      </li>
    </ul>
    <p v-else-if="open && showTypeHint" class="searchable-select-hint">
      {{ typeHintText }}
    </p>
    <p v-else-if="open && keyword.trim() && !filteredOptions.length" class="searchable-select-hint">
      无匹配项目
    </p>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  options: { type: Array, default: () => [] },
  /** 选项取值字段，默认 gzhname */
  valueKey: { type: String, default: 'gzhname' },
  /** 自定义展示文案，如 项目名（工作号） */
  formatLabel: { type: Function, default: null },
  placeholder: { type: String, default: '输入关键字搜索' },
  /** 超过该数量时须输入关键字后才展示列表 */
  typeToFilterMin: { type: Number, default: 12 },
  typeHint: { type: String, default: '选项较多，请输入项目名称或工作号关键字筛选' },
})

const emit = defineEmits(['update:modelValue'])

const rootRef = ref(null)
const inputRef = ref(null)
const open = ref(false)
const keyword = ref('')
const highlightIndex = ref(0)

function optionValue(opt) {
  if (!opt) return ''
  if (typeof opt === 'string') return opt
  return String(opt[props.valueKey] ?? opt.value ?? opt.label ?? '').trim()
}

function displayLabel(opt) {
  if (props.formatLabel) return props.formatLabel(opt)
  return optionValue(opt) || '—'
}

function optionKey(opt, idx) {
  const v = optionValue(opt)
  return v ? `${v}-${idx}` : `opt-${idx}`
}

const selectedLabel = computed(() => {
  if (!props.modelValue) return ''
  const hit = (props.options || []).find((o) => optionValue(o) === props.modelValue)
  return hit ? displayLabel(hit) : props.modelValue
})

const inputText = computed(() => (open.value ? keyword.value : selectedLabel.value))

const showTypeHint = computed(
  () => (props.options?.length || 0) > props.typeToFilterMin && !keyword.value.trim(),
)

const typeHintText = computed(() => props.typeHint)

const filteredOptions = computed(() => {
  const list = props.options || []
  const q = keyword.value.trim().toLowerCase()
  if (list.length > props.typeToFilterMin && !q) return []
  if (!q) return list
  return list.filter((item) => {
    const label = displayLabel(item).toLowerCase()
    const gzh = String(item?.gzh ?? '').toLowerCase()
    const name = String(item?.gzhname ?? item?.label ?? '').toLowerCase()
    const val = optionValue(item).toLowerCase()
    return label.includes(q) || gzh.includes(q) || name.includes(q) || val.includes(q)
  })
})

watch(filteredOptions, () => {
  highlightIndex.value = 0
})

watch(
  () => props.modelValue,
  () => {
    if (!open.value) keyword.value = ''
  },
)

function onInput(e) {
  keyword.value = e.target.value
  open.value = true
  if (!keyword.value.trim()) {
    emit('update:modelValue', '')
  }
}

function onFocus() {
  open.value = true
  keyword.value = selectedLabel.value
  if (inputRef.value) {
    inputRef.value.select()
  }
}

function closeDropdown() {
  open.value = false
  keyword.value = ''
  highlightIndex.value = 0
}

function selectOption(opt) {
  emit('update:modelValue', optionValue(opt))
  closeDropdown()
}

function clearSelection() {
  emit('update:modelValue', '')
  keyword.value = ''
  open.value = false
  inputRef.value?.focus()
}

function moveHighlight(delta) {
  if (!open.value) {
    open.value = true
    return
  }
  const len = filteredOptions.value.length
  if (!len) return
  highlightIndex.value = (highlightIndex.value + delta + len) % len
}

function confirmHighlight() {
  const opt = filteredOptions.value[highlightIndex.value]
  if (opt) selectOption(opt)
}

function onDocumentClick(e) {
  if (!rootRef.value?.contains(e.target)) closeDropdown()
}

onMounted(() => document.addEventListener('mousedown', onDocumentClick))
onBeforeUnmount(() => document.removeEventListener('mousedown', onDocumentClick))
</script>

<style scoped>
.searchable-select {
  position: relative;
  width: 100%;
}

.searchable-select-field {
  position: relative;
  display: flex;
  align-items: center;
}

.searchable-select-input {
  width: 100%;
  padding: 8px 28px 8px 8px;
  border: 1px solid var(--color-border-base, #d9d9d9);
  border-radius: var(--radius-sm, 4px);
  font-size: inherit;
  line-height: 1.4;
  background: var(--color-bg-container, #fff);
}

.searchable-select-input:focus {
  outline: none;
  border-color: var(--color-primary, #3b82f6);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.12);
}

.searchable-select-clear {
  position: absolute;
  right: 6px;
  width: 22px;
  height: 22px;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: #94a3b8;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
}

.searchable-select-clear:hover {
  color: #64748b;
  background: #f1f5f9;
}

.searchable-select-dropdown {
  position: absolute;
  z-index: 120;
  left: 0;
  right: 0;
  top: calc(100% + 4px);
  max-height: 220px;
  margin: 0;
  padding: 4px 0;
  list-style: none;
  overflow-y: auto;
  border: 1px solid var(--color-border-base, #d9d9d9);
  border-radius: var(--radius-sm, 4px);
  background: #fff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
}

.searchable-select-dropdown li {
  padding: 8px 10px;
  font-size: 0.9rem;
  line-height: 1.35;
  cursor: pointer;
  word-break: break-all;
}

.searchable-select-dropdown li:hover,
.searchable-select-dropdown li.active {
  background: #eff6ff;
  color: #1d4ed8;
}

.searchable-select-hint {
  position: absolute;
  z-index: 120;
  left: 0;
  right: 0;
  top: calc(100% + 4px);
  margin: 0;
  padding: 10px;
  font-size: 0.85rem;
  color: #64748b;
  border: 1px dashed #cbd5e1;
  border-radius: var(--radius-sm, 4px);
  background: #f8fafc;
}
</style>
