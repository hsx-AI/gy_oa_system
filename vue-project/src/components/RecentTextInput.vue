<template>
  <div class="recent-text-input-wrap" ref="wrapRef">
    <textarea
      v-if="tag === 'textarea'"
      :value="modelValue"
      :name="name"
      :placeholder="placeholder"
      :rows="rows"
      autocomplete="off"
      class="recent-text-input"
      @input="onInput"
      @focus="onFocus"
      @blur="onBlur"
    />
    <input
      v-else
      type="text"
      :value="modelValue"
      :name="name"
      :placeholder="placeholder"
      autocomplete="off"
      class="recent-text-input"
      @input="onInput"
      @focus="onFocus"
      @blur="onBlur"
    />
    <div v-if="showDropdown && recentList.length > 0" class="recent-dropdown" ref="dropdownRef">
      <div class="recent-dropdown-title">最近使用</div>
      <ul class="recent-dropdown-list">
        <li
          v-for="(item, index) in recentList"
          :key="index"
          class="recent-dropdown-item"
          @mousedown.prevent="selectItem(item)"
        >
          {{ item }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  storageKey: { type: String, required: true },
  placeholder: { type: String, default: '' },
  name: { type: String, default: '' },
  tag: { type: String, default: 'input' },
  rows: { type: [Number, String], default: 3 },
  maxItems: { type: Number, default: 10 }
})

const emit = defineEmits(['update:modelValue'])

const wrapRef = ref(null)
const dropdownRef = ref(null)
const showDropdown = ref(false)
const recentList = ref([])
let blurTimer = null

function loadRecent() {
  try {
    const raw = localStorage.getItem(props.storageKey)
    const list = raw ? JSON.parse(raw) : []
    recentList.value = Array.isArray(list) ? list.filter(Boolean) : []
  } catch {
    recentList.value = []
  }
}

function saveRecent(value) {
  const v = (value || '').trim()
  if (!v) return
  try {
    let list = recentList.value.filter(item => item !== v)
    list.unshift(v)
    list = list.slice(0, props.maxItems)
    recentList.value = list
    localStorage.setItem(props.storageKey, JSON.stringify(list))
  } catch (e) {
    console.warn('saveRecent failed', e)
  }
}

function onInput(e) {
  emit('update:modelValue', e.target.value)
}

function onFocus() {
  if (blurTimer) {
    clearTimeout(blurTimer)
    blurTimer = null
  }
  loadRecent()
  showDropdown.value = true
}

function onBlur() {
  blurTimer = setTimeout(() => {
    showDropdown.value = false
    const v = (props.modelValue || '').trim()
    if (v) saveRecent(v)
    blurTimer = null
  }, 200)
}

function selectItem(item) {
  emit('update:modelValue', item)
  showDropdown.value = false
}

function onClickOutside(e) {
  if (showDropdown.value && wrapRef.value && !wrapRef.value.contains(e.target)) {
    showDropdown.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', onClickOutside)
})
onUnmounted(() => {
  document.removeEventListener('click', onClickOutside)
  if (blurTimer) clearTimeout(blurTimer)
})
</script>

<style scoped>
.recent-text-input-wrap {
  position: relative;
  width: 100%;
}
.recent-text-input {
  width: 100%;
  padding: 8px 12px;
  font-size: 1rem;
  line-height: 1.5;
  color: var(--input-color, #333);
  background: var(--input-bg, #fff);
  border: 1px solid var(--input-border, #ccc);
  border-radius: 6px;
  font-family: inherit;
  box-sizing: border-box;
}
.recent-text-input:focus {
  outline: none;
  border-color: var(--primary, #667eea);
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}
.recent-text-input::placeholder {
  color: #999;
}
.recent-dropdown {
  position: absolute;
  z-index: 1000;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 4px;
  background: #fff;
  border: 1px solid var(--input-border, #ccc);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  max-height: 220px;
  overflow: hidden;
}
.recent-dropdown-title {
  padding: 6px 12px;
  font-size: 0.8rem;
  color: #888;
  border-bottom: 1px solid #eee;
}
.recent-dropdown-list {
  list-style: none;
  margin: 0;
  padding: 4px 0;
  max-height: 180px;
  overflow-y: auto;
}
.recent-dropdown-item {
  padding: 8px 12px;
  font-size: 0.95rem;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.recent-dropdown-item:hover {
  background: #f0f0f0;
}
</style>
