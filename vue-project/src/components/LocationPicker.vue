<template>
  <div class="location-picker">
    <!-- 境外模式：国家选择 + 补充输入 -->
    <template v-if="mode === 'abroad'">
      <div class="lp-row">
        <select v-model="abroad.country" class="lp-select lp-select--country" @change="emitValue">
          <option value="">请选择国家/地区</option>
          <option v-for="c in countries" :key="c.alpha2" :value="c.cnname">
            {{ c.cnname }}（{{ c.name }}）
          </option>
        </select>
        <input
          v-model="abroad.detail"
          class="lp-input"
          placeholder="补充具体地点（选填）"
          @input="emitValue"
        >
      </div>
    </template>

    <!-- 境内模式：省 → 市 + 补充输入 -->
    <template v-else>
      <div class="lp-row">
        <select v-model="china.province" class="lp-select" @change="onProvinceChange">
          <option value="">省/直辖市</option>
          <option v-for="p in provinces" :key="p.code" :value="p.code">{{ p.name }}</option>
        </select>
        <select v-model="china.city" class="lp-select" @change="emitValue">
          <option value="">市/州</option>
          <option v-for="c in cityOptions" :key="c.code" :value="c.code">{{ c.name }}</option>
        </select>
        <input
          v-model="china.detail"
          class="lp-input lp-input--inline"
          placeholder="补充详细地点（选填）"
          @input="emitValue"
        >
      </div>
    </template>
  </div>
</template>

<script setup>
import { reactive, computed, watch } from 'vue'
import provinceData from 'province-city-china/dist/province.json'
import cityData from 'province-city-china/dist/city.json'
import countryData from 'province-city-china/dist/country.json'

const props = defineProps({
  modelValue: { type: String, default: '' },
  mode: { type: String, default: 'domestic' } // 'domestic' | 'abroad'
})
const emit = defineEmits(['update:modelValue'])

const provinces = provinceData
const countries = countryData.sort((a, b) => a.cnname.localeCompare(b.cnname, 'zh'))

const china = reactive({ province: '', city: '', detail: '' })
const abroad = reactive({ country: '', detail: '' })

const cityOptions = computed(() => {
  if (!china.province) return []
  const pCode = china.province.substring(0, 2)
  return cityData.filter(c => c.province === pCode)
})

function onProvinceChange() {
  china.city = ''
  china.detail = ''
  emitValue()
}

function getProvinceName(code) {
  return provinces.find(p => p.code === code)?.name || ''
}
function getCityName(code) {
  return cityOptions.value.find(c => c.code === code)?.name || ''
}

function emitValue() {
  let val = ''
  if (props.mode === 'abroad') {
    val = [abroad.country, abroad.detail].filter(Boolean).join('')
  } else {
    const pName = getProvinceName(china.province)
    const cName = getCityName(china.city)
    val = [pName, cName, china.detail].filter(Boolean).join('')
  }
  emit('update:modelValue', val)
}

watch(() => props.mode, () => {
  china.province = ''
  china.city = ''
  china.detail = ''
  abroad.country = ''
  abroad.detail = ''
})
</script>

<style scoped>
.location-picker {
  width: 100%;
}
.lp-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.lp-select {
  flex: 1 1 0;
  min-width: 100px;
  padding: 6px 8px;
  border: 1px solid #d0d5dd;
  border-radius: 6px;
  font-size: 13px;
  background: #fff;
  color: #1d2939;
  outline: none;
  transition: border-color .2s;
}
.lp-select:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59,130,246,.12);
}
.lp-select--country {
  flex: 2 1 0;
  min-width: 200px;
}
.lp-input {
  flex: 1 1 0;
  min-width: 120px;
  padding: 6px 10px;
  border: 1px solid #d0d5dd;
  border-radius: 6px;
  font-size: 13px;
  color: #1d2939;
  outline: none;
  transition: border-color .2s;
}
.lp-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59,130,246,.12);
}
</style>
