<template>
  <div class="trip-map-page">
    <div class="page-title">公出地图</div>

    <div v-if="loading" class="loading-box">数据加载中...</div>
    <div v-else-if="errorMsg" class="error-box">{{ errorMsg }}</div>

    <template v-else>
      <!-- 中国 -->
      <div class="section-card">
        <div class="section-header">
          <div class="section-title">
            中国境内公出（{{ chinaTotal }}人）
          </div>
          <div class="section-subtitle">
            只显示境内公出；市内公出不显示；黑龙江省内不画飞线
          </div>
        </div>

        <div class="section-body">
          <div class="map-panel map-panel-large">
            <VChart
              v-if="chinaMapReady"
              class="chart"
              :option="chinaOption"
            />
            <div v-else class="chart-placeholder">中国地图加载中...</div>
          </div>

          <div class="detail-panel detail-panel-narrow">
            <div class="detail-title">中国明细</div>

            <div v-if="!chinaTree.length" class="empty-text">暂无中国境内公出数据</div>

            <div
              v-for="province in chinaTree"
              :key="province.name"
              class="group-card"
            >
              <div class="group-title">
                {{ displayChinaName(province.name) }}（{{ province.count }}人）
              </div>

              <div
                v-for="dept in province.depts"
                :key="province.name + '-' + dept.dept"
                class="dept-block"
              >
                <div class="dept-title">
                  {{ dept.dept }}（{{ dept.count }}人）
                </div>

                <div
                  v-for="person in dept.persons"
                  :key="province.name + '-' + dept.dept + '-' + person.name + '-' + person.location"
                  class="person-card"
                >
                  <div class="person-row">
                    <span class="label">姓名：</span>
                    <span>{{ person.name }}</span>
                  </div>
                  <div class="person-row">
                    <span class="label">项目：</span>
                    <span>{{ person.project || '无' }}</span>
                  </div>
                  <div class="person-row">
                    <span class="label">时间：</span>
                    <span>{{ person.period }}</span>
                  </div>
                  <div class="person-row">
                    <span class="label">已公出：</span>
                    <span>{{ person.passed }}天</span>
                    <span class="split-dot">｜</span>
                    <span class="label">还剩：</span>
                    <span>{{ person.remain }}天</span>
                  </div>
                  <div class="person-row">
                    <span class="label">地点：</span>
                    <span>{{ person.location }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div><!-- /中国 -->

      <!-- 世界 -->
      <div class="section-card">
        <div class="section-header">
          <div class="section-title">
            国外公出（{{ worldTotal }}人）
          </div>
          <div class="section-subtitle">
            世界地图按国家展示，只有有公出数据的国家显示中文国家名
          </div>
        </div>

        <div class="section-body">
          <div class="map-panel map-panel-large">
            <VChart
              v-if="worldMapReady"
              class="chart"
              :option="worldOption"
            />
            <div v-else class="chart-placeholder">世界地图加载中...</div>
          </div>

          <div class="detail-panel detail-panel-narrow">
            <div class="detail-title">国外明细</div>

            <div v-if="!worldTree.length" class="empty-text">暂无国外公出数据</div>

            <div
              v-for="country in worldTree"
              :key="country.name"
              class="group-card"
            >
              <div class="group-title">
                {{ displayWorldCountryTitle(country.name) }}（{{ country.count }}人）
              </div>

              <div
                v-for="dept in country.depts"
                :key="country.name + '-' + dept.dept"
                class="dept-block"
              >
                <div class="dept-title">
                  {{ dept.dept }}（{{ dept.count }}人）
                </div>

                <div
                  v-for="person in dept.persons"
                  :key="country.name + '-' + dept.dept + '-' + person.name + '-' + person.location"
                  class="person-card"
                >
                  <div class="person-row">
                    <span class="label">姓名：</span>
                    <span>{{ person.name }}</span>
                  </div>
                  <div class="person-row">
                    <span class="label">项目：</span>
                    <span>{{ person.project || '无' }}</span>
                  </div>
                  <div class="person-row">
                    <span class="label">时间：</span>
                    <span>{{ person.period }}</span>
                  </div>
                  <div class="person-row">
                    <span class="label">已公出：</span>
                    <span>{{ person.passed }}天</span>
                    <span class="split-dot">｜</span>
                    <span class="label">还剩：</span>
                    <span>{{ person.remain }}天</span>
                  </div>
                  <div class="person-row">
                    <span class="label">地点：</span>
                    <span>{{ person.location }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div><!-- /世界 -->
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import * as echarts from 'echarts'
import VChart from 'vue-echarts'
import { getBusinessTripMap } from '@/api/businessTripMap'

const loading = ref(false)
const errorMsg = ref('')

const chinaData = ref({ points: [], lines: [], tree: [], total: 0, cityPoints: {} })
const worldData = ref({ points: [], lines: [], tree: [], total: 0 })

const chinaMapReady = ref(false)
const worldMapReady = ref(false)

const chinaCoordMap = ref({})
const worldCoordMap = ref({})
const chinaCityCoordMap = ref({})

const HEILONGJIANG_CENTER = [127.9688, 45.368]
const CHINA_CENTER = [104.1954, 35.8617]

/**
 * world.json 实际国家名称映射
 * 这里保持你原来的映射思路，并补充常见别名
 */
const WORLD_NAME_ALIASES = {
  '美国': 'United States',
  '美利坚合众国': 'United States',
  'USA': 'United States',
  'U.S.A.': 'United States',
  '英国': 'United Kingdom',
  '大不列颠及北爱尔兰联合王国': 'United Kingdom',
  'UK': 'United Kingdom',
  '阿联酋': 'United Arab Emirates',
  '阿拉伯联合酋长国': 'United Arab Emirates',

  '巴西': 'Brazil',
  '日本': 'Japan',
  '韩国': 'South Korea',
  '朝鲜': 'North Korea',
  '俄罗斯': 'Russia',
  '蒙古': 'Mongolia',
  '印度': 'India',
  '泰国': 'Thailand',
  '越南': 'Vietnam',
  '马来西亚': 'Malaysia',
  '新加坡': 'Singapore',
  '印度尼西亚': 'Indonesia',
  '菲律宾': 'Philippines',
  '缅甸': 'Myanmar',
  '老挝': 'Laos',
  '柬埔寨': 'Cambodia',
  '巴基斯坦': 'Pakistan',
  '阿富汗': 'Afghanistan',
  '哈萨克斯坦': 'Kazakhstan',
  '乌兹别克斯坦': 'Uzbekistan',
  '吉尔吉斯斯坦': 'Kyrgyzstan',
  '塔吉克斯坦': 'Tajikistan',

  '德国': 'Germany',
  '法国': 'France',
  '意大利': 'Italy',
  '西班牙': 'Spain',
  '葡萄牙': 'Portugal',
  '荷兰': 'Netherlands',
  '比利时': 'Belgium',
  '瑞士': 'Switzerland',
  '奥地利': 'Austria',
  '波兰': 'Poland',
  '瑞典': 'Sweden',
  '挪威': 'Norway',
  '芬兰': 'Finland',
  '丹麦': 'Denmark',
  '爱尔兰': 'Ireland',
  '乌克兰': 'Ukraine',
  '白俄罗斯': 'Belarus',
  '土耳其': 'Turkey',
  '希腊': 'Greece',
  '罗马尼亚': 'Romania',
  '保加利亚': 'Bulgaria',
  '匈牙利': 'Hungary',
  '塞尔维亚': 'Serbia',
  '克罗地亚': 'Croatia',
  '捷克': 'Czechia',
  '阿尔巴尼亚': 'Albania',
  '卢森堡': 'Luxembourg',
  '塞浦路斯': 'Cyprus',

  '澳大利亚': 'Australia',
  '新西兰': 'New Zealand',

  '加拿大': 'Canada',
  '墨西哥': 'Mexico',
  '阿根廷': 'Argentina',
  '智利': 'Chile',
  '秘鲁': 'Peru',
  '哥伦比亚': 'Colombia',
  '委内瑞拉': 'Venezuela',

  '埃及': 'Egypt',
  '利比亚': 'Libya',
  '阿尔及利亚': 'Algeria',
  '摩洛哥': 'Morocco',
  '突尼斯': 'Tunisia',
  '苏丹': 'Sudan',
  '埃塞俄比亚': 'Ethiopia',
  '肯尼亚': 'Kenya',
  '坦桑尼亚': 'Tanzania',
  '尼日利亚': 'Nigeria',
  '安哥拉': 'Angola',
  '南非': 'South Africa',

  '沙特阿拉伯': 'Saudi Arabia',
  '伊朗': 'Iran',
  '伊拉克': 'Iraq',
  '叙利亚': 'Syria',
  '以色列': 'Israel',
  '约旦': 'Jordan',
  '黎巴嫩': 'Lebanon',
  '卡塔尔': 'Qatar',
  '科威特': 'Kuwait',
  '阿曼': 'Oman',
  '也门': 'Yemen',
  '格鲁吉亚': 'Georgia'
}

const EN_TO_ZH_DISPLAY = {
  'United States': '美国',
  'United Kingdom': '英国',
  'United Arab Emirates': '阿联酋',
  'Brazil': '巴西',
  'Japan': '日本',
  'South Korea': '韩国',
  'North Korea': '朝鲜',
  'Russia': '俄罗斯',
  'Mongolia': '蒙古',
  'India': '印度',
  'Thailand': '泰国',
  'Vietnam': '越南',
  'Malaysia': '马来西亚',
  'Singapore': '新加坡',
  'Indonesia': '印度尼西亚',
  'Philippines': '菲律宾',
  'Myanmar': '缅甸',
  'Laos': '老挝',
  'Cambodia': '柬埔寨',
  'Pakistan': '巴基斯坦',
  'Afghanistan': '阿富汗',
  'Kazakhstan': '哈萨克斯坦',
  'Uzbekistan': '乌兹别克斯坦',
  'Kyrgyzstan': '吉尔吉斯斯坦',
  'Tajikistan': '塔吉克斯坦',
  'Germany': '德国',
  'France': '法国',
  'Italy': '意大利',
  'Spain': '西班牙',
  'Portugal': '葡萄牙',
  'Netherlands': '荷兰',
  'Belgium': '比利时',
  'Switzerland': '瑞士',
  'Austria': '奥地利',
  'Poland': '波兰',
  'Sweden': '瑞典',
  'Norway': '挪威',
  'Finland': '芬兰',
  'Denmark': '丹麦',
  'Ireland': '爱尔兰',
  'Ukraine': '乌克兰',
  'Belarus': '白俄罗斯',
  'Turkey': '土耳其',
  'Greece': '希腊',
  'Romania': '罗马尼亚',
  'Bulgaria': '保加利亚',
  'Hungary': '匈牙利',
  'Serbia': '塞尔维亚',
  'Croatia': '克罗地亚',
  'Czechia': '捷克',
  'Albania': '阿尔巴尼亚',
  'Australia': '澳大利亚',
  'New Zealand': '新西兰',
  'Canada': '加拿大',
  'Mexico': '墨西哥',
  'Argentina': '阿根廷',
  'Chile': '智利',
  'Peru': '秘鲁',
  'Colombia': '哥伦比亚',
  'Venezuela': '委内瑞拉',
  'Egypt': '埃及',
  'Libya': '利比亚',
  'Algeria': '阿尔及利亚',
  'Morocco': '摩洛哥',
  'Tunisia': '突尼斯',
  'Sudan': '苏丹',
  'Ethiopia': '埃塞俄比亚',
  'Kenya': '肯尼亚',
  'Tanzania': '坦桑尼亚',
  'Nigeria': '尼日利亚',
  'Angola': '安哥拉',
  'South Africa': '南非',
  'Saudi Arabia': '沙特阿拉伯',
  'Iran': '伊朗',
  'Iraq': '伊拉克',
  'Syria': '叙利亚',
  'Israel': '以色列',
  'Jordan': '约旦',
  'Lebanon': '黎巴嫩',
  'Qatar': '卡塔尔',
  'Kuwait': '科威特',
  'Oman': '阿曼',
  'Yemen': '也门',
  'Georgia': '格鲁吉亚',
  'Luxembourg': '卢森堡',
  'Cyprus': '塞浦路斯'
}

/**
 * 修复世界飞线终点偏移的关键：
 * 对多区域、多岛屿、跨日期变更线的国家使用人工中心点覆盖。
 * 尤其是 United States，如果用 bbox 中心算法会偏到欧洲附近。
 */
const WORLD_CENTER_OVERRIDES = {
  'United States': [-98.5, 39.8],
  'United Kingdom': [-2.5830348, 54.4598409],
  'Brazil': [-51.9253, -14.235],
  'Canada': [-106.3468, 56.1304],
  'Russia': [105.3188, 61.524],
  'Australia': [133.7751, -25.2744],
  'New Zealand': [174.885971, -40.900557],
  'Japan': [138.2529, 36.2048],
  'Indonesia': [113.9213, -0.7893],
  'Philippines': [121.774, 12.8797],
  'France': [2.2137, 46.2276],
  'Norway': [8.4689, 60.472],
  'Chile': [-71.543, -35.6751],
  'Argentina': [-63.6167, -38.4161]
}

const chinaTree = computed(() => chinaData.value.tree || [])
const worldTree = computed(() => worldData.value.tree || [])

const chinaTotal = computed(() => chinaData.value.total || 0)
const worldTotal = computed(() => worldData.value.total || 0)

const chinaTreeMap = computed(() => {
  const m = {}
  chinaTree.value.forEach(item => {
    m[item.name] = item
  })
  return m
})

function displayChinaName(name) {
  if (name === '香港特别行政区') return '香港'
  if (name === '澳门特别行政区') return '澳门'
  return name
}

function flattenPersonNames(depts = []) {
  return depts.flatMap(d => d.persons.map(p => p.name))
}

function resolveWorldChartName(name) {
  const raw = (name || '').trim()
  if (!raw) return raw

  if (worldCoordMap.value[raw]) return raw

  const alias = WORLD_NAME_ALIASES[raw]
  if (alias && worldCoordMap.value[alias]) return alias

  return alias || raw
}

function displayWorldName(chartName, fallback = '') {
  return EN_TO_ZH_DISPLAY[chartName] || fallback || chartName
}

function displayWorldCountryTitle(rawName) {
  const chartName = resolveWorldChartName(rawName)
  return displayWorldName(chartName, rawName)
}

const worldTreeMap = computed(() => {
  const m = {}
  worldTree.value.forEach(item => {
    const chartName = resolveWorldChartName(item.name)
    m[chartName] = item
  })
  return m
})

async function fetchJson(url) {
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(`地图资源加载失败：${url}`)
  }
  return await res.json()
}

function walkCoords(coords, bucket = []) {
  if (!Array.isArray(coords)) return bucket
  if (typeof coords[0] === 'number' && typeof coords[1] === 'number') {
    bucket.push(coords)
    return bucket
  }
  coords.forEach(item => walkCoords(item, bucket))
  return bucket
}

function calcFeatureCenter(feature) {
  const props = feature.properties || {}
  const name = props.name

  // 1. 优先用人工覆盖中心点
  if (WORLD_CENTER_OVERRIDES[name]) {
    return WORLD_CENTER_OVERRIDES[name]
  }

  // 2. 再用 geojson 自带中心点
  if (Array.isArray(props.center)) return props.center
  if (Array.isArray(props.cp)) return props.cp
  if (Array.isArray(props.centroid)) return props.centroid

  // 3. 最后兜底用坐标平均值，避免 bbox 中心把美国算到法国附近
  const all = walkCoords(feature.geometry?.coordinates || [])
  if (!all.length) return null

  let sumLng = 0
  let sumLat = 0

  all.forEach(([lng, lat]) => {
    sumLng += lng
    sumLat += lat
  })

  return [sumLng / all.length, sumLat / all.length]
}

function buildCoordMap(geojson) {
  const map = {}
  ;(geojson.features || []).forEach(feature => {
    const name = feature.properties?.name
    const center = calcFeatureCenter(feature)
    if (name && center) {
      map[name] = center
    }
  })
  return map
}

async function initMaps() {
  const chinaUrl = '/china.json'
  const worldUrl = '/world.json'
  const cityUrl = '/china_city_coords.json'

  const [chinaJson, worldJson, cityCoords] = await Promise.all([
    fetchJson(chinaUrl),
    fetchJson(worldUrl),
    fetchJson(cityUrl)
  ])
  chinaCityCoordMap.value = cityCoords

  const cleanChinaJson = {
    ...chinaJson,
    features: (chinaJson.features || []).filter(
      f => f?.properties?.name !== '南海诸岛'
    )
  }

  echarts.registerMap('trip-china-map', cleanChinaJson)
  echarts.registerMap('trip-world-map', worldJson)

  chinaCoordMap.value = buildCoordMap(cleanChinaJson)
  worldCoordMap.value = buildCoordMap(worldJson)

  chinaMapReady.value = true
  worldMapReady.value = true
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
    errorMsg.value = '接口数据加载失败，请检查后端是否正常启动'
  } finally {
    loading.value = false
  }
}

function buildTooltipHtml(title, count, names) {
  return `
    <div style="min-width:220px;line-height:1.7;">
      <div style="font-weight:700;font-size:14px;margin-bottom:4px;">${title}</div>
      <div>公出人数：${count}</div>
      <div style="white-space:normal;word-break:break-all;">人员：${names.length ? names.join('、') : '无'}</div>
    </div>
  `
}

function chinaTooltipFormatter(params) {
  const rawName = params.name
  const item = chinaTreeMap.value[rawName]
  const showName = displayChinaName(rawName)
  if (!item) return buildTooltipHtml(showName || '未知地点', 0, [])
  return buildTooltipHtml(displayChinaName(item.name), item.count, flattenPersonNames(item.depts))
}

function worldTooltipFormatter(params) {
  const chartName = params.name
  const item = worldTreeMap.value[chartName]
  const showName = displayWorldName(chartName, chartName)
  if (!item) return buildTooltipHtml(showName || '未知国家', 0, [])
  return buildTooltipHtml(displayWorldName(chartName, item.name), item.count, flattenPersonNames(item.depts))
}

const chinaCityScatterData = computed(() => {
  const cp = chinaData.value.cityPoints || {}
  return Object.entries(cp)
    .map(([city, count]) => {
      const coord = chinaCityCoordMap.value[city]
      if (!coord) return null
      return { name: city, value: [...coord, count] }
    })
    .filter(Boolean)
})

const chinaLineData = computed(() => {
  const cityCoords = chinaCityCoordMap.value
  const cp = chinaData.value.cityPoints || {}
  const cityTargets = Object.keys(cp)
    .map(city => {
      const coord = cityCoords[city]
      if (!coord) return null
      const prov = chinaCityProvMap(city)
      if (prov === '黑龙江省') return null
      return { fromName: '哈尔滨', toName: city, coords: [HEILONGJIANG_CENTER, coord] }
    })
    .filter(Boolean)

  if (cityTargets.length) return cityTargets

  return (chinaData.value.lines || [])
    .map(name => {
      const coord = chinaCoordMap.value[name]
      if (!coord) return null
      return { fromName: '黑龙江省', toName: name, coords: [HEILONGJIANG_CENTER, coord] }
    })
    .filter(Boolean)
})

function chinaCityProvMap(city) {
  const tree = chinaTree.value
  for (const prov of tree) {
    for (const dept of prov.depts) {
      for (const p of dept.persons) {
        if (p.location && p.location.includes(city.replace(/市$/, ''))) {
          return prov.name
        }
      }
    }
  }
  return ''
}

const worldMapSeriesData = computed(() => {
  return worldTree.value
    .map(item => {
      const chartName = resolveWorldChartName(item.name)
      if (!chartName) return null
      return {
        name: chartName,
        value: item.count
      }
    })
    .filter(Boolean)
})

const worldLineData = computed(() => {
  return (worldData.value.lines || [])
    .map(rawName => {
      const chartName = resolveWorldChartName(rawName)
      const coord = worldCoordMap.value[chartName]
      if (!coord) return null
      return {
        fromName: '中国',
        toName: chartName,
        rawName,
        coords: [CHINA_CENTER, coord]
      }
    })
    .filter(Boolean)
})

const worldLabelNameSet = computed(() => {
  return new Set(worldMapSeriesData.value.map(i => i.name))
})

const chinaOption = computed(() => {
  if (!chinaMapReady.value) return {}

  const regionNames = chinaTree.value.map(item => item.name)

  return {
    backgroundColor: '#f7fbff',
    tooltip: {
      trigger: 'item',
      formatter: chinaTooltipFormatter
    },
    geo: {
      map: 'trip-china-map',
      roam: true,
      zoom: 1.12,
      label: {
        show: true,
        color: '#1f2d3d',
        fontSize: 10,
        formatter: params => displayChinaName(params.name)
      },
      itemStyle: {
        areaColor: '#eef5ff',
        borderColor: '#5b8ff9',
        borderWidth: 1
      },
      emphasis: {
        label: {
          color: '#000'
        },
        itemStyle: {
          areaColor: '#cfe3ff'
        }
      },
      regions: regionNames.map(name => ({
        name,
        itemStyle: {
          areaColor: '#8db7ff'
        },
        emphasis: {
          itemStyle: {
            areaColor: '#5b8ff9'
          }
        }
      }))
    },
    series: [
      {
        name: '城市公出',
        type: 'scatter',
        coordinateSystem: 'geo',
        z: 12,
        symbolSize: val => Math.min(8 + (val[2] || 1) * 4, 24),
        itemStyle: { color: '#fa541c', opacity: 0.85 },
        label: {
          show: true,
          position: 'right',
          formatter: p => p.name,
          fontSize: 11,
          color: '#c41d7f',
          fontWeight: 600
        },
        tooltip: {
          formatter: p => `<b>${p.name}</b><br/>公出人数: ${p.value[2]}`
        },
        data: chinaCityScatterData.value
      },
      {
        name: '中国飞线端点',
        type: 'effectScatter',
        coordinateSystem: 'geo',
        z: 11,
        rippleEffect: { brushType: 'stroke', scale: 3 },
        symbolSize: 10,
        itemStyle: { color: '#ff4d4f' },
        data: [
          { name: '哈尔滨', value: [...HEILONGJIANG_CENTER, 1] },
          ...chinaLineData.value.map(item => ({
            name: item.toName,
            value: [...item.coords[1], 1]
          }))
        ]
      },
      {
        name: '中国飞线底线',
        type: 'lines',
        coordinateSystem: 'geo',
        z: 9,
        lineStyle: { color: '#ff7875', width: 2, opacity: 0.8, curveness: 0.25 },
        data: chinaLineData.value
      },
      {
        name: '中国飞线动画',
        type: 'lines',
        coordinateSystem: 'geo',
        z: 10,
        effect: { show: true, period: 4, trailLength: 0, symbol: 'arrow', symbolSize: 10 },
        lineStyle: { color: '#ff4d4f', width: 0, opacity: 0, curveness: 0.25 },
        data: chinaLineData.value
      }
    ]
  }
})

const worldOption = computed(() => {
  if (!worldMapReady.value) return {}

  const regionNames = worldTree.value
    .map(item => resolveWorldChartName(item.name))
    .filter(Boolean)

  return {
    backgroundColor: '#f7fbff',
    tooltip: {
      trigger: 'item',
      formatter: worldTooltipFormatter
    },
    geo: {
      map: 'trip-world-map',
      roam: true,
      zoom: 1,
      label: {
        show: true,
        color: '#1f2d3d',
        fontSize: 8,
        formatter: params => {
          return worldLabelNameSet.value.has(params.name)
            ? displayWorldName(params.name, params.name)
            : ''
        }
      },
      itemStyle: {
        areaColor: '#f6fbff',
        borderColor: '#7aa7ff',
        borderWidth: 0.6
      },
      emphasis: {
        label: {
          color: '#000',
          formatter: params => displayWorldName(params.name, params.name)
        },
        itemStyle: {
          areaColor: '#d6f5f3'
        }
      },
      regions: regionNames.map(name => ({
        name,
        itemStyle: {
          areaColor: '#79dfd4'
        },
        emphasis: {
          itemStyle: {
            areaColor: '#13c2c2'
          }
        }
      }))
    },
    series: [
      {
        name: '世界飞线端点',
        type: 'effectScatter',
        coordinateSystem: 'geo',
        z: 11,
        rippleEffect: {
          brushType: 'stroke',
          scale: 3
        },
        symbolSize: 8,
        itemStyle: {
          color: '#13c2c2'
        },
        data: [
          {
            name: 'China',
            value: [...CHINA_CENTER, 1]
          },
          ...worldLineData.value.map(item => ({
            name: item.toName,
            value: [...item.coords[1], 1]
          }))
        ]
      },
      {
        name: '世界飞线底线',
        type: 'lines',
        coordinateSystem: 'geo',
        z: 9,
        lineStyle: {
          color: '#5cdbd3',
          width: 2,
          opacity: 0.85,
          curveness: 0.2
        },
        data: worldLineData.value
      },
      {
        name: '世界飞线动画',
        type: 'lines',
        coordinateSystem: 'geo',
        z: 10,
        effect: {
          show: true,
          period: 4,
          trailLength: 0,
          symbol: 'arrow',
          symbolSize: 9
        },
        lineStyle: {
          color: '#13c2c2',
          width: 0,
          opacity: 0,
          curveness: 0.2
        },
        data: worldLineData.value
      }
    ]
  }
})

onMounted(async () => {
  try {
    await Promise.all([initMaps(), loadData()])
  } catch (e) {
    console.error(e)
    errorMsg.value = '地图资源加载失败，请检查 public/china.json 和 public/world.json 是否存在'
  }
})
</script>

<style scoped>
.trip-map-page {
  padding: 16px;
  background: #f5f7fa;
  min-height: 100%;
  box-sizing: border-box;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #1f2d3d;
  margin-bottom: 16px;
}

.section-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
}

.section-header {
  margin-bottom: 12px;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2d3d;
  margin-bottom: 6px;
}

.section-subtitle {
  font-size: 13px;
  color: #909399;
}

.section-body {
  display: flex;
  gap: 16px;
  align-items: stretch;
}

.map-panel {
  min-width: 0;
  height: 540px;
  background: linear-gradient(180deg, #f7fbff 0%, #eef6ff 100%);
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #edf2f7;
}

.map-panel-large {
  flex: 1.75;
}

.chart {
  width: 100%;
  height: 100%;
}

.chart-placeholder,
.loading-box,
.error-box,
.empty-text {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
  min-height: 180px;
}

.detail-panel {
  height: 540px;
  overflow-y: auto;
  padding-right: 4px;
}

.detail-panel-narrow {
  flex: 0.82;
  min-width: 320px;
  max-width: 440px;
}

.detail-title {
  font-size: 16px;
  font-weight: 700;
  color: #1f2d3d;
  margin-bottom: 10px;
}

.group-card {
  border: 1px solid #ebeef5;
  border-radius: 10px;
  margin-bottom: 12px;
  padding: 12px;
  background: #fafcff;
}

.group-title {
  font-size: 15px;
  font-weight: 700;
  color: #1f2d3d;
  margin-bottom: 10px;
}

.dept-block {
  margin-bottom: 10px;
  padding: 10px;
  background: #fff;
  border-radius: 8px;
  border-left: 3px solid #5b8ff9;
}

.dept-title {
  font-size: 14px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 8px;
}

.person-card {
  background: #f8fafc;
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 8px;
  border: 1px solid #edf2f7;
}

.person-row {
  font-size: 13px;
  color: #606266;
  line-height: 1.8;
  word-break: break-all;
}

.label {
  color: #909399;
}

.split-dot {
  color: #c0c4cc;
  margin: 0 6px;
}

@media (max-width: 1500px) {
  .map-panel-large {
    flex: 1.55;
  }

  .detail-panel-narrow {
    flex: 0.9;
    min-width: 300px;
  }
}

@media (max-width: 1280px) {
  .section-body {
    flex-direction: column;
  }

  .detail-panel-narrow {
    min-width: 0;
    max-width: none;
    height: auto;
    max-height: 520px;
  }

  .map-panel {
    height: 500px;
  }
}
</style>