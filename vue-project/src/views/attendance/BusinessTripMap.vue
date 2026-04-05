<template>
  <div class="trip-map-page">
    <canvas ref="canvasRef" class="map-canvas" @mousemove="onCanvasMouseMove"></canvas>

    <!-- 效果切换按钮组 -->
    <div class="map-btn-group">
      <div class="btn" :class="{ active: state.bar }" @click="setEffectToggle('bar')">柱状图</div>
      <div class="btn" :class="{ active: state.flyLine }" @click="setEffectToggle('flyLine')">飞线</div>
      <div class="btn" :class="{ active: state.particle }" @click="setEffectToggle('particle')">粒子特效</div>
      <div class="btn" :class="{ active: state.mirror }" @click="setEffectToggle('mirror')">倒影</div>
    </div>

    <div class="top-bar">
      <h1 class="top-bar__title">公出地图</h1>
      <div class="top-bar__stats">
        <div class="kpi">
          <span class="kpi__num">{{ chinaTotal + worldTotal }}</span>
          <span class="kpi__label">公出总人数</span>
        </div>
        <span class="kpi__sep"></span>
        <div class="kpi">
          <span class="kpi__num">{{ chinaTotal }}</span>
          <span class="kpi__label">境内</span>
        </div>
        <span class="kpi__sep"></span>
        <div class="kpi">
          <span class="kpi__num">{{ worldTotal }}</span>
          <span class="kpi__label">境外</span>
        </div>
        <span class="kpi__sep"></span>
        <div class="kpi">
          <span class="kpi__num kpi__num--warn">{{ returningCount }}</span>
          <span class="kpi__label">即将返程</span>
        </div>
      </div>
    </div>

    <aside class="detail-panel" v-if="chinaTree.length || worldTree.length">
      <div class="detail-panel__head">
        <span>公出明细</span>
        <span class="badge">{{ chinaTree.length + worldTree.length }} 地区</span>
      </div>
      <div class="detail-scroll">
        <template v-if="chinaTree.length">
          <div class="section-title">境内公出 · {{ chinaTotal }}人</div>
          <div v-for="prov in chinaTree" :key="'cn-'+prov.name" class="region-group">
            <div class="region-group__head">
              {{ displayChinaName(prov.name) }}
              <span class="region-group__num">{{ prov.count }}</span>
            </div>
            <template v-for="dept in prov.depts" :key="prov.name+dept.dept">
              <div class="dept-label">{{ dept.dept }}</div>
              <div v-for="p in dept.persons"
                :key="prov.name+dept.dept+p.name+p.location"
                class="person-row">
                <div class="person-row__main">
                  <span class="person-row__name">{{ p.name }}</span>
                  <span class="person-row__loc">{{ p.location }}</span>
                </div>
                <div class="person-row__meta">
                  <span>{{ p.project || '—' }}</span>
                  <span class="meta-sep">·</span>
                  <span>{{ p.period }}</span>
                </div>
                <div class="person-row__tags">
                  <span class="pill" :class="pillClass(p.passed, 'passed')">已{{ p.passed }}天</span>
                  <span class="pill" :class="pillClass(p.remain, 'remain')">剩{{ p.remain }}天</span>
                </div>
              </div>
            </template>
          </div>
        </template>
        <template v-if="worldTree.length">
          <div class="section-title" style="margin-top:12px">境外公出 · {{ worldTotal }}人</div>
          <div v-for="c in worldTree" :key="'wd-'+c.name" class="region-group">
            <div class="region-group__head">
              {{ displayWorldCountryTitle(c.name) }}
              <span class="region-group__num">{{ c.count }}</span>
            </div>
            <template v-for="dept in c.depts" :key="c.name+dept.dept">
              <div class="dept-label">{{ dept.dept }}</div>
              <div v-for="p in dept.persons"
                :key="c.name+dept.dept+p.name+p.location"
                class="person-row">
                <div class="person-row__main">
                  <span class="person-row__name">{{ p.name }}</span>
                  <span class="person-row__loc">{{ p.location }}</span>
                </div>
                <div class="person-row__meta">
                  <span>{{ p.project || '—' }}</span>
                  <span class="meta-sep">·</span>
                  <span>{{ p.period }}</span>
                </div>
                <div class="person-row__tags">
                  <span class="pill" :class="pillClass(p.passed, 'passed')">已{{ p.passed }}天</span>
                  <span class="pill" :class="pillClass(p.remain, 'remain')">剩{{ p.remain }}天</span>
                </div>
              </div>
            </template>
          </div>
        </template>
      </div>
    </aside>

    <!-- 光柱悬停弹窗 -->
    <div v-if="barTooltip.show" class="bar-tooltip" :style="barTooltipStyle">
      <div class="bar-tooltip__header">
        <span class="bar-tooltip__name">{{ barTooltip.name }}</span>
        <span class="bar-tooltip__count">{{ barTooltip.count }}人</span>
      </div>
      <div class="bar-tooltip__body">
        <div v-for="(p, i) in barTooltip.persons" :key="i" class="bar-tooltip__person">
          <div class="btp__row1">
            <span class="btp__name">{{ p.name }}</span>
            <span class="btp__dept">{{ p.dept }}</span>
          </div>
          <div class="btp__row2">
            <span class="btp__loc">{{ p.location }}</span>
            <span class="btp__proj" v-if="p.project">· {{ p.project }}</span>
          </div>
          <div class="btp__row3">
            <span class="btp__period">{{ p.period }}</span>
            <span class="btp__pill" :class="p.remain <= 3 ? 'btp__pill--warn' : ''">剩{{ p.remain }}天</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="state-box">
      <div class="spinner"></div>
      <span>数据加载中...</span>
    </div>
    <div v-if="errorMsg" class="state-box state-box--error">{{ errorMsg }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, reactive } from 'vue'
import { getBusinessTripMap } from '@/api/businessTripMap'
import { World } from './map3d/World'

const canvasRef = ref(null)
let worldApp = null

const loading = ref(false)
const errorMsg = ref('')

const chinaData = ref({ points: [], lines: [], tree: [], total: 0, cityPoints: {}, cityList: [] })
const worldData = ref({ points: [], lines: [], tree: [], total: 0 })

const chinaTree = computed(() => chinaData.value.tree || [])
const chinaCityList = computed(() => chinaData.value.cityList || [])
const worldTree = computed(() => worldData.value.tree || [])
const chinaTotal = computed(() => chinaData.value.total || 0)
const worldTotal = computed(() => worldData.value.total || 0)

const returningCount = computed(() => {
  let count = 0
  ;[...chinaTree.value, ...worldTree.value].forEach(region => {
    (region.depts || []).forEach(dept => {
      (dept.persons || []).forEach(p => {
        if (p.remain >= 0 && p.remain <= 3) count++
      })
    })
  })
  return count
})

// ===== 光柱悬停弹窗 =====
const barTooltip = reactive({ show: false, name: '', count: 0, persons: [], x: 0, y: 0 })
const barTooltipStyle = computed(() => ({
  left: barTooltip.x + 16 + 'px',
  top: barTooltip.y - 10 + 'px'
}))
function onBarHover({ name, count, persons, mouseX, mouseY }) {
  barTooltip.name = name
  barTooltip.count = count
  barTooltip.persons = persons || []
  barTooltip.x = mouseX
  barTooltip.y = mouseY
  barTooltip.show = true
}
function onBarLeave() {
  barTooltip.show = false
}
function onCanvasMouseMove(e) {
  if (barTooltip.show) {
    barTooltip.x = e.clientX
    barTooltip.y = e.clientY
  }
}

// ===== 效果开关状态 =====
const state = reactive({
  bar: true,
  flyLine: true,
  particle: true,
  mirror: true
})

const setEffectToggle = (type) => {
  state[type] = !state[type]

  if (!worldApp) return

  if (type === 'bar') {
    if (worldApp.barGroup) worldApp.barGroup.visible = state[type]
    worldApp.setLabelVisible('labelGroup', state[type])
  }
  if (type === 'particle') {
    worldApp.particles.enable = state[type]
    worldApp.particles.instance.visible = state[type]
  }
  if (type === 'flyLine') {
    if (worldApp.flyLineGroup) worldApp.flyLineGroup.visible = state[type]
    if (worldApp.flyLineFocusGroup) worldApp.flyLineFocusGroup.visible = state[type]
  }
  if (type === 'mirror' && worldApp.groundMirror) {
    worldApp.groundMirror.visible = state[type]
  }
}

function pillClass(val, type) {
  if (type === 'passed') return val < 0 ? 'pill--warn' : ''
  return val < 0 ? 'pill--alert' : val <= 3 ? 'pill--warn' : ''
}

function displayChinaName(name) {
  if (name === '香港特别行政区') return '香港'
  if (name === '澳门特别行政区') return '澳门'
  return name
}

const WORLD_NAME_ALIASES = {
  '美国': 'United States', '英国': 'United Kingdom', '阿联酋': 'United Arab Emirates',
  '日本': 'Japan', '韩国': 'South Korea', '俄罗斯': 'Russia', '德国': 'Germany',
  '法国': 'France', '意大利': 'Italy', '巴西': 'Brazil', '印度': 'India',
  '泰国': 'Thailand', '越南': 'Vietnam', '马来西亚': 'Malaysia', '新加坡': 'Singapore',
  '澳大利亚': 'Australia', '加拿大': 'Canada'
}
const EN_TO_ZH = { 'United States': '美国', 'United Kingdom': '英国', 'Japan': '日本',
  'South Korea': '韩国', 'Russia': '俄罗斯', 'Germany': '德国', 'France': '法国',
  'Italy': '意大利', 'Brazil': '巴西', 'India': '印度', 'Thailand': '泰国',
  'Vietnam': '越南', 'Malaysia': '马来西亚', 'Singapore': '新加坡',
  'Australia': '澳大利亚', 'Canada': '加拿大', 'United Arab Emirates': '阿联酋'
}

function displayWorldCountryTitle(rawName) {
  const alias = WORLD_NAME_ALIASES[rawName]
  return EN_TO_ZH[alias] || EN_TO_ZH[rawName] || rawName
}

async function loadData() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await getBusinessTripMap()
    chinaData.value = res?.china || { points: [], lines: [], tree: [], total: 0, cityPoints: {} }
    worldData.value = res?.world || { points: [], lines: [], tree: [], total: 0 }
  } catch (e) {
    console.error(e)
    errorMsg.value = '数据加载失败'
  } finally {
    loading.value = false
  }
}

watch([chinaTree, chinaCityList], ([tree, cityList]) => {
  // World 内部的 gqGroup 等分组尚未就绪时，提前返回，避免 setTripData 过程中访问 undefined
  if (!worldApp || !tree || !worldApp.gqGroup) return
  worldApp.setTripData(tree, cityList)
}, { deep: true })

const DARK_CLS = 'trip-map-dark-mode'

onMounted(async () => {
  const main = document.querySelector('.app-main')
  const wrap = document.querySelector('.app-content-wrap')
  main?.classList.add(DARK_CLS)
  wrap?.classList.add(DARK_CLS)

  worldApp = new World(canvasRef.value, {
    geoProjectionCenter: [108.55, 34.32],
    onBarHover,
    onBarLeave,
    onReady: () => {
      if (chinaTree.value.length) {
        worldApp.setTripData(chinaTree.value, chinaCityList.value)
      }
      worldApp.particles.enable = true
      worldApp.particles.instance.visible = true
    }
  })

  try {
    await loadData()
  } catch (e) {
    console.error(e)
  }
})

onBeforeUnmount(() => {
  document.querySelector('.app-main')?.classList.remove(DARK_CLS)
  document.querySelector('.app-content-wrap')?.classList.remove(DARK_CLS)
  if (worldApp) {
    worldApp.destroy()
    worldApp = null
  }
})
</script>

<!-- 全局样式覆盖（非 scoped） -->
<style>
.app-main.trip-map-dark-mode,
.app-content-wrap.trip-map-dark-mode {
  background: #011024 !important;
}
.app-main.trip-map-dark-mode {
  padding: 0 !important;
  overflow: hidden !important;
}
.app-main.trip-map-dark-mode .page-header-bar,
.app-main.trip-map-dark-mode .page-header {
  background: transparent !important;
  box-shadow: none !important;
  border: none !important;
}
</style>

<!-- scoped 样式 -->
<style scoped>
.trip-map-page {
  position: relative;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  background: #011024;
}

.map-canvas {
  display: block;
  width: 100%;
  height: 100%;
  background: #000;
}

/* 右侧按钮组 */
.map-btn-group {
  position: absolute;
  left: 16px;
  bottom: 16px;
  display: flex;
  gap: 8px;
  z-index: 20;
}
.map-btn-group .btn {
  padding: 5px 12px;
  color: #fff;
  border: 1px solid #2bc4dc;
  font-size: 12px;
  text-align: center;
  opacity: 0.5;
  cursor: pointer;
  transition: all 0.3s;
  border-radius: 4px;
}
.map-btn-group .btn.active {
  opacity: 1;
}

/* 顶部统计条 */
.top-bar {
  position: absolute;
  top: 0; left: 0; right: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  z-index: 10;
  background: linear-gradient(180deg, rgba(1,16,36,0.85) 0%, rgba(1,16,36,0) 100%);
  pointer-events: none;
}
.top-bar__title {
  font-size: 18px;
  font-weight: 700;
  color: #e8f3ff;
  margin: 0;
  letter-spacing: 1px;
  text-shadow: 0 0 12px rgba(43,196,220,0.3);
}
.top-bar__stats {
  display: flex;
  align-items: center;
  pointer-events: auto;
}
.kpi {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 18px;
}
.kpi__num {
  font-size: 22px;
  font-weight: 700;
  color: #5aadff;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}
.kpi__num--warn { color: #c49a5c; }
.kpi__label {
  font-size: 11px;
  color: rgba(138,175,220,0.6);
  margin-top: 2px;
}
.kpi__sep {
  width: 1px;
  height: 24px;
  background: rgba(255,255,255,0.1);
  flex-shrink: 0;
}

/* 右侧明细面板 */
.detail-panel {
  position: absolute;
  top: 60px;
  right: 0;
  bottom: 0;
  width: 340px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  background: linear-gradient(270deg, rgba(1,16,36,0.92) 0%, rgba(1,16,36,0.6) 80%, rgba(1,16,36,0) 100%);
  padding: 16px 16px 16px 24px;
  pointer-events: auto;
}
.detail-panel__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: #e8f3ff;
}
.badge {
  font-size: 11px;
  font-weight: 400;
  color: rgba(138,175,220,0.5);
}
.detail-scroll {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}
.detail-scroll::-webkit-scrollbar { width: 3px; }
.detail-scroll::-webkit-scrollbar-track { background: transparent; }
.detail-scroll::-webkit-scrollbar-thumb { background: rgba(90,173,255,0.2); border-radius: 2px; }

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: rgba(90,173,255,0.8);
  padding: 6px 0;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  margin-bottom: 8px;
  letter-spacing: 0.5px;
}

.region-group { margin-bottom: 10px; }
.region-group__head {
  font-size: 13px;
  font-weight: 600;
  color: #e8f3ff;
  padding: 5px 0;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}
.region-group__num {
  font-size: 12px;
  font-weight: 600;
  color: #5aadff;
  margin-left: auto;
  opacity: 0.7;
}
.dept-label {
  font-size: 11px;
  color: rgba(138,175,220,0.5);
  padding: 3px 0 1px;
}

.person-row {
  padding: 7px 10px;
  margin-bottom: 3px;
  border-radius: 6px;
  background: rgba(14,34,60,0.5);
  transition: background 0.2s;
}
.person-row:hover { background: rgba(22,48,80,0.8); }
.person-row__main {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 6px;
  margin-bottom: 2px;
}
.person-row__name {
  font-size: 13px;
  font-weight: 600;
  color: #e8f3ff;
}
.person-row__loc {
  font-size: 11px;
  color: rgba(138,175,220,0.5);
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: right;
}
.person-row__meta {
  font-size: 11px;
  color: rgba(138,175,220,0.5);
  line-height: 1.5;
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.meta-sep { color: rgba(255,255,255,0.12); }
.person-row__tags { display: flex; gap: 4px; margin-top: 3px; }

.pill {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 500;
  color: rgba(138,175,220,0.7);
  background: rgba(90,173,255,0.08);
}
.pill--warn { color: #c49a5c; background: rgba(196,154,92,0.1); }
.pill--alert { color: #b56a6a; background: rgba(181,106,106,0.1); }

.state-box {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%,-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: rgba(138,175,220,0.5);
  font-size: 13px;
  z-index: 5;
}
.state-box--error { color: #b56a6a; }
.spinner {
  width: 28px; height: 28px;
  border: 2px solid rgba(90,173,255,0.15);
  border-top-color: #5aadff;
  border-radius: 50%;
  animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 1200px) {
  .detail-panel { width: 280px; }
}
@media (max-width: 900px) {
  .detail-panel { display: none; }
}

/* 光柱悬停弹窗 */
.bar-tooltip {
  position: fixed;
  z-index: 100;
  min-width: 240px;
  max-width: 360px;
  max-height: 400px;
  background: rgba(2, 18, 48, 0.94);
  border: 1px solid rgba(43, 196, 220, 0.6);
  border-radius: 8px;
  padding: 0;
  pointer-events: none;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.5), inset 0 0 20px rgba(43, 196, 220, 0.05);
  backdrop-filter: blur(6px);
  overflow: hidden;
}
.bar-tooltip__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: rgba(43, 196, 220, 0.12);
  border-bottom: 1px solid rgba(43, 196, 220, 0.2);
}
.bar-tooltip__name {
  font-size: 14px;
  font-weight: 600;
  color: #2bc4dc;
}
.bar-tooltip__count {
  font-size: 13px;
  color: #fbdf88;
  font-weight: 600;
}
.bar-tooltip__body {
  padding: 6px 14px 10px;
  max-height: 320px;
  overflow-y: auto;
}
.bar-tooltip__person {
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.bar-tooltip__person:last-child { border-bottom: none; }
.btp__row1 { display: flex; align-items: center; gap: 8px; margin-bottom: 3px; }
.btp__name { font-size: 13px; font-weight: 600; color: #fff; }
.btp__dept { font-size: 11px; color: rgba(255, 255, 255, 0.45); }
.btp__row2 { font-size: 12px; color: rgba(255, 255, 255, 0.7); margin-bottom: 3px; }
.btp__proj { color: rgba(255, 255, 255, 0.5); }
.btp__row3 { display: flex; align-items: center; gap: 8px; font-size: 11px; }
.btp__period { color: rgba(255, 255, 255, 0.5); }
.btp__pill {
  padding: 1px 6px;
  border-radius: 3px;
  background: rgba(43, 196, 220, 0.15);
  color: #2bc4dc;
  font-size: 11px;
}
.btp__pill--warn {
  background: rgba(251, 223, 136, 0.18);
  color: #fbdf88;
}
</style>

<!-- 全局 CSS3D 标签样式（非 scoped） -->
<style>
/* 3D 地图上的 CSS3D 公出标签 */
.trip-label-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  pointer-events: none;
  opacity: 0;
}
.trip-label-name {
  font-size: 13px;
  font-weight: 600;
  color: #e8f3ff;
  text-shadow: 0 0 6px rgba(0,0,0,0.8), 0 0 3px rgba(43,196,220,0.4);
  white-space: nowrap;
}
.trip-label-count {
  font-size: 16px;
  font-weight: 700;
  color: #7efbf6;
  text-shadow: 0 0 8px rgba(126,251,246,0.5);
}

/* 柱状图数值标签 */
.provinces-label-style02 {
  z-index: 2;
}
.provinces-label-style02-wrap {
  transform: translate(0%, 200%);
  opacity: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 40px;
  z-index: 2;
}
.provinces-label-style02 .number {
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 10px;
}
.provinces-label-style02 .no {
  display: flex;
  justify-content: center;
  align-items: center;
  color: #7efbf6;
  text-shadow: 0 0 5px #7efbf6;
  font-size: 16px;
  width: 30px;
  height: 30px;
  background: rgba(0,0,0,0.5);
  border-radius: 50%;
  border: 2px solid rgba(255,255,255,0.5);
}
.provinces-label-style02.yellow .no {
  color: #fef99e !important;
  text-shadow: 0 0 5px #fef99e !important;
}

/* 省份名称标签 */
.provinces-name-label-wrap {
  color: #5fc6dc;
  opacity: 0;
  text-shadow: 1px 1px 0px #000;
}
.area-name-label-wrap {
  color: #5fc6dc;
  opacity: 1;
  text-shadow: 1px 1px 0px #000;
}

/* 标牌 */
.badges-label {
  z-index: 99999;
}
.badges-label-wrap {
  position: relative;
  padding: 10px 10px;
  background: #0e1937;
  border: 1px solid #1e7491;
  font-size: 12px;
  font-weight: bold;
  color: #fff;
  bottom: 50px;
  z-index: 99999;
}
.badges-label-wrap span {
  color: #ffe70b;
}
.badges-label-wrap:after {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 10px;
  height: 10px;
  display: block;
  content: '';
  border-right: 2px solid #6cfffe;
  border-bottom: 2px solid #6cfffe;
}
.badges-label-wrap:before {
  position: absolute;
  left: 0;
  top: 0;
  width: 10px;
  height: 10px;
  display: block;
  content: '';
  border-left: 2px solid #6cfffe;
  border-top: 2px solid #6cfffe;
}
.badges-label-wrap .icon {
  position: absolute;
  width: 27px;
  height: 20px;
  left: 50%;
  transform: translateX(-13px);
  bottom: -40px;
}

/* 信息框 */
.info-point {
  background: rgba(0,0,0,0.5);
  color: #a3dcde;
  font-size: 14px;
  width: 170px;
  height: 106px;
  padding: 16px 12px 0;
  margin-bottom: 30px;
}
.info-point-wrap:after,
.info-point-wrap:before {
  display: block;
  content: '';
  position: absolute;
  top: 0;
  width: 15px;
  height: 15px;
  border-top: 1px solid #4b87a6;
}
.info-point-wrap:before {
  left: 0;
  border-left: 1px solid #4b87a6;
}
.info-point-wrap:after {
  right: 0;
  border-right: 1px solid #4b87a6;
}
.info-point-wrap-inner:after,
.info-point-wrap-inner:before {
  display: block;
  content: '';
  position: absolute;
  bottom: 0;
  width: 15px;
  height: 15px;
  border-bottom: 1px solid #4b87a6;
}
.info-point-wrap-inner:before {
  left: 0;
  border-left: 1px solid #4b87a6;
}
.info-point-wrap-inner:after {
  right: 0;
  border-right: 1px solid #4b87a6;
}
.info-point-line {
  position: absolute;
  top: 7px;
  right: 12px;
  display: flex;
}
.info-point-line .line {
  width: 5px;
  height: 2px;
  margin-right: 5px;
  background: #17e5c3;
}
.info-point-content .content-item {
  display: flex;
  height: 28px;
  line-height: 28px;
  background: rgba(35,47,58,0.6);
  margin-bottom: 5px;
}
.info-point-content .content-item .label {
  width: 60px;
  padding-left: 10px;
}
.info-point-content .content-item .value {
  color: #fff;
}

/* loading toast */
.fixed-loading {
  position: absolute;
  left: 0; top: 0; z-index: 99;
  width: 100%; height: 100%;
  display: flex; justify-content: center; align-items: center;
  background: rgba(0,0,0,0.5);
}
.page-loading-container {
  display: flex; justify-content: center; align-items: center;
  width: 60px; height: 60px;
  background: rgba(0,0,0,0.8);
  border-radius: 10px;
}
.page-loading {
  width: 30px; height: 30px;
  border: 2px solid #fff; border-top-color: transparent;
  border-radius: 100%;
  animation: spin 0.75s linear infinite;
}
</style>
