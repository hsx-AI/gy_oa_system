<template>
  <div class="info-feed-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">天气新闻</h1>
        <p class="page-subtitle">来自公网中转电脑定时推送的实时天气、天气预报和新闻缓存</p>
      </div>
      <button type="button" class="refresh-btn" :disabled="loading" @click="refreshAll">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="23 4 23 10 17 10" />
          <polyline points="1 20 1 14 7 14" />
          <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10" />
          <path d="M20.49 15a9 9 0 0 1-14.85 3.36L1 14" />
        </svg>
        刷新
      </button>
    </div>

    <div class="status-strip">
      <div class="status-item">
        <span class="status-label">缓存条目</span>
        <strong>{{ summary.count ?? '-' }}</strong>
      </div>
      <div class="status-item">
        <span class="status-label">最近推送</span>
        <strong>{{ summary.latestUpdate || '暂无' }}</strong>
      </div>
      <div class="status-item">
        <span class="status-label">当前城市</span>
        <strong>{{ currentCity.name }}</strong>
      </div>
    </div>

    <section class="weather-section">
      <div class="weather-main panel">
        <div class="panel-head">
          <div>
            <h2>实时天气</h2>
            <p>{{ weatherNow?.updateTime || '等待 pusher 推送数据' }}</p>
          </div>
          <select v-model="selectedLocation" class="city-select" @change="loadWeather">
            <option v-for="city in cityOptions" :key="city.location" :value="city.location">
              {{ city.name }}
            </option>
          </select>
        </div>

        <div v-if="weatherNow?.now" class="current-weather">
          <div class="temp-block">
            <span class="temp">{{ weatherNow.now.temp }}</span>
            <span class="unit">°C</span>
          </div>
          <div class="weather-text">
            <strong>{{ weatherNow.now.text }}</strong>
            <span>体感 {{ weatherNow.now.feelsLike || '-' }}°C</span>
          </div>
          <div class="weather-metrics">
            <div><span>湿度</span><strong>{{ weatherNow.now.humidity || '-' }}%</strong></div>
            <div><span>风向</span><strong>{{ weatherNow.now.windDir || '-' }}</strong></div>
            <div><span>风力</span><strong>{{ weatherNow.now.windScale || '-' }} 级</strong></div>
            <div><span>能见度</span><strong>{{ weatherNow.now.vis || '-' }} km</strong></div>
          </div>
        </div>
        <div v-else class="empty-state">暂无实时天气缓存</div>
      </div>

      <div class="forecast-panel panel">
        <div class="panel-head">
          <div>
            <h2>7 天预报</h2>
            <p>{{ dailyForecast?.updateTime || '' }}</p>
          </div>
        </div>
        <div v-if="dailyItems.length" class="daily-list">
          <div v-for="day in dailyItems" :key="day.fxDate" class="daily-item">
            <span class="date">{{ shortDate(day.fxDate) }}</span>
            <strong>{{ day.textDay }}</strong>
            <span>{{ day.tempMin }}° / {{ day.tempMax }}°</span>
          </div>
        </div>
        <div v-else class="empty-state">暂无天气预报缓存</div>
      </div>
    </section>

    <section class="hourly-section panel">
      <div class="panel-head">
        <div>
          <h2>未来 24 小时</h2>
          <p>{{ hourlyForecast?.updateTime || '' }}</p>
        </div>
      </div>
      <div v-if="hourlyItems.length" class="hourly-scroll">
        <div v-for="hour in hourlyItems" :key="hour.fxTime" class="hourly-item">
          <span>{{ hourLabel(hour.fxTime) }}</span>
          <strong>{{ hour.temp }}°</strong>
          <small>{{ hour.text }}</small>
        </div>
      </div>
      <div v-else class="empty-state">暂无逐小时预报缓存</div>
    </section>

    <section class="news-section">
      <div class="news-main panel">
        <div class="panel-head">
          <div>
            <h2>新闻</h2>
            <p>选择分类查看已推送列表</p>
          </div>
          <div class="news-tabs">
            <button
              v-for="tab in newsTypes"
              :key="tab.value"
              type="button"
              :class="{ active: selectedNewsType === tab.value }"
              @click="switchNewsType(tab.value)"
            >
              {{ tab.label }}
            </button>
          </div>
        </div>

        <div v-if="newsLoading" class="empty-state">新闻加载中...</div>
        <div v-else-if="newsItems.length" class="news-list">
          <button
            v-for="item in newsItems"
            :key="item.uniquekey || item.title"
            type="button"
            class="news-item"
            :class="{ active: selectedNews?.uniquekey === item.uniquekey }"
            @click="openNews(item)"
          >
            <img v-if="item.thumbnail_pic_s" :src="item.thumbnail_pic_s" alt="" />
            <div class="news-item-body">
              <strong>{{ item.title }}</strong>
              <span>{{ item.author_name || item.category || '新闻' }} · {{ item.date || '' }}</span>
            </div>
          </button>
        </div>
        <div v-else class="empty-state">暂无该分类新闻缓存</div>
      </div>

      <aside class="news-detail panel">
        <div v-if="selectedNewsDetail" class="detail-content">
          <h2>{{ selectedNewsDetail.title || selectedNews?.title }}</h2>
          <p class="detail-meta">{{ selectedNewsDetail.author_name || selectedNews?.author_name || '新闻' }} · {{ selectedNewsDetail.date || selectedNews?.date || '' }}</p>
          <div v-if="selectedNewsDetail.content" class="article-body" v-html="selectedNewsDetail.content"></div>
          <p v-else class="detail-summary">当前缓存没有正文详情，可通过新闻列表中的原文链接查看。</p>
          <a v-if="selectedNewsDetail.url || selectedNews?.url" class="source-link" :href="selectedNewsDetail.url || selectedNews.url" target="_blank" rel="noopener">打开原文</a>
        </div>
        <div v-else class="empty-state">请选择一条新闻</div>
      </aside>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  getInfoFeedSummary,
  getNewsDetail,
  getNewsList,
  getWeatherDaily,
  getWeatherHourly,
  getWeatherNow,
} from '@/api/infoFeed'

const cityOptions = [
  { name: '哈尔滨', location: '101050101' },
  { name: '北京', location: '101010100' },
  { name: '上海', location: '101020100' },
  { name: '广州', location: '101280101' },
  { name: '深圳', location: '101280601' },
  { name: '成都', location: '101270101' },
  { name: '杭州', location: '101210101' },
]

const newsTypes = [
  { label: '头条', value: 'top' },
  { label: '国内', value: 'guonei' },
  { label: '国际', value: 'guoji' },
  { label: '财经', value: 'caijing' },
  { label: '娱乐', value: 'yule' },
  { label: '体育', value: 'tiyu' },
  { label: '军事', value: 'junshi' },
  { label: '科技', value: 'keji' },
  { label: '社会', value: 'shehui' },
]

const selectedLocation = ref('101050101')
const selectedNewsType = ref('top')
const summary = ref({})
const weatherNow = ref(null)
const hourlyForecast = ref(null)
const dailyForecast = ref(null)
const newsList = ref(null)
const selectedNews = ref(null)
const selectedNewsDetail = ref(null)
const loading = ref(false)
const newsLoading = ref(false)

const currentCity = computed(() => cityOptions.find(c => c.location === selectedLocation.value) || cityOptions[0])
const hourlyItems = computed(() => (hourlyForecast.value?.hourly || []).slice(0, 24))
const dailyItems = computed(() => (dailyForecast.value?.daily || []).slice(0, 7))
const newsItems = computed(() => newsList.value?.result?.data || newsList.value?.data || [])

function shortDate(value) {
  if (!value) return '-'
  const parts = value.split('-')
  return parts.length === 3 ? `${parts[1]}/${parts[2]}` : value
}

function hourLabel(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value.slice(11, 16)
  return `${String(date.getHours()).padStart(2, '0')}:00`
}

async function loadSummary() {
  try {
    summary.value = await getInfoFeedSummary()
  } catch {
    summary.value = {}
  }
}

async function loadWeather() {
  loading.value = true
  try {
    const location = selectedLocation.value
    const [now, hourly, daily] = await Promise.allSettled([
      getWeatherNow(location),
      getWeatherHourly('24h', location),
      getWeatherDaily('7d', location),
    ])
    weatherNow.value = now.status === 'fulfilled' ? now.value : null
    hourlyForecast.value = hourly.status === 'fulfilled' ? hourly.value : null
    dailyForecast.value = daily.status === 'fulfilled' ? daily.value : null
  } finally {
    loading.value = false
  }
}

async function loadNews() {
  newsLoading.value = true
  selectedNews.value = null
  selectedNewsDetail.value = null
  try {
    newsList.value = await getNewsList({ type: selectedNewsType.value, page: '1' })
    if (newsItems.value.length) {
      await openNews(newsItems.value[0])
    }
  } catch {
    newsList.value = null
  } finally {
    newsLoading.value = false
  }
}

async function openNews(item) {
  selectedNews.value = item
  selectedNewsDetail.value = item
  if (!item?.uniquekey) return
  try {
    const detail = await getNewsDetail(item.uniquekey)
    selectedNewsDetail.value = detail?.result || detail || item
  } catch {
    selectedNewsDetail.value = item
  }
}

function switchNewsType(type) {
  if (selectedNewsType.value === type) return
  selectedNewsType.value = type
  loadNews()
}

async function refreshAll() {
  await Promise.all([loadSummary(), loadWeather(), loadNews()])
}

onMounted(refreshAll)
</script>

<style scoped>
.info-feed-page {
  width: 100%;
  padding: 0 20px 28px 0;
}
.page-header, .panel-head, .status-strip, .weather-section, .news-section {
  display: flex;
  gap: 16px;
}
.page-header {
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-title {
  margin: 0;
  font-size: 24px;
  color: #0f172a;
}
.page-subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: #64748b;
}
.refresh-btn, .news-tabs button {
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
}
.refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  color: #1e293b;
}
.refresh-btn svg {
  width: 16px;
  height: 16px;
}
.panel, .status-strip {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}
.status-strip {
  padding: 14px 18px;
  margin-bottom: 16px;
}
.status-item {
  min-width: 160px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.status-label, .panel-head p, .weather-text span, .daily-item span, .hourly-item small, .news-item span, .detail-meta {
  color: #64748b;
  font-size: 12px;
}
.status-item strong {
  color: #0f172a;
  font-size: 15px;
}
.weather-section {
  align-items: stretch;
  margin-bottom: 16px;
}
.weather-main {
  flex: 1.35;
  padding: 18px;
}
.forecast-panel {
  flex: 1;
  padding: 18px;
}
.panel-head {
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.panel-head h2 {
  margin: 0;
  font-size: 17px;
  color: #0f172a;
}
.panel-head p {
  margin: 4px 0 0;
}
.city-select {
  min-width: 112px;
  padding: 7px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #fff;
}
.current-weather {
  display: grid;
  grid-template-columns: auto minmax(110px, 0.5fr) 1fr;
  gap: 22px;
  align-items: center;
}
.temp-block {
  display: flex;
  align-items: flex-start;
}
.temp {
  font-size: 64px;
  line-height: 0.9;
  font-weight: 700;
  color: #0f766e;
}
.unit {
  margin-top: 8px;
  font-size: 20px;
  color: #0f766e;
}
.weather-text {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.weather-text strong {
  font-size: 22px;
  color: #0f172a;
}
.weather-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(100px, 1fr));
  gap: 10px;
}
.weather-metrics div {
  padding: 10px 12px;
  background: #f8fafc;
  border: 1px solid #edf2f7;
  border-radius: 6px;
  display: flex;
  justify-content: space-between;
}
.weather-metrics span {
  color: #64748b;
  font-size: 12px;
}
.weather-metrics strong {
  color: #0f172a;
  font-size: 13px;
}
.daily-list {
  display: grid;
  gap: 8px;
}
.daily-item {
  display: grid;
  grid-template-columns: 52px 1fr auto;
  gap: 10px;
  align-items: center;
  padding: 9px 10px;
  background: #f8fafc;
  border-radius: 6px;
}
.daily-item strong {
  color: #1e293b;
  font-size: 13px;
}
.hourly-section {
  padding: 18px;
  margin-bottom: 16px;
}
.hourly-scroll {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 4px;
}
.hourly-item {
  flex: 0 0 84px;
  display: flex;
  flex-direction: column;
  gap: 7px;
  align-items: center;
  padding: 12px 8px;
  background: #f8fafc;
  border: 1px solid #edf2f7;
  border-radius: 6px;
}
.hourly-item span {
  font-size: 12px;
  color: #475569;
}
.hourly-item strong {
  font-size: 18px;
  color: #0f766e;
}
.news-section {
  align-items: flex-start;
}
.news-main {
  flex: 1;
  padding: 18px;
}
.news-detail {
  width: 40%;
  min-width: 360px;
  padding: 18px;
  position: sticky;
  top: 78px;
}
.news-tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.news-tabs button {
  padding: 6px 10px;
  color: #475569;
}
.news-tabs button.active {
  color: #fff;
  background: #0f766e;
  border-color: #0f766e;
}
.news-list {
  display: grid;
  gap: 10px;
}
.news-item {
  width: 100%;
  display: flex;
  gap: 12px;
  padding: 10px;
  text-align: left;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
}
.news-item:hover, .news-item.active {
  border-color: #14b8a6;
  background: #f0fdfa;
}
.news-item img {
  width: 96px;
  height: 64px;
  object-fit: cover;
  border-radius: 6px;
  background: #f1f5f9;
}
.news-item-body {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.news-item strong {
  color: #0f172a;
  font-size: 14px;
  line-height: 1.45;
}
.detail-content h2 {
  margin: 0 0 8px;
  font-size: 20px;
  line-height: 1.35;
  color: #0f172a;
}
.detail-meta {
  margin: 0 0 14px;
}
.article-body {
  max-height: 620px;
  overflow: auto;
  color: #334155;
  font-size: 14px;
  line-height: 1.8;
}
.article-body :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 6px;
}
.detail-summary {
  color: #475569;
  line-height: 1.7;
}
.source-link {
  display: inline-flex;
  margin-top: 14px;
  color: #0f766e;
  font-weight: 600;
  text-decoration: none;
}
.empty-state {
  padding: 28px 12px;
  text-align: center;
  color: #94a3b8;
  font-size: 14px;
}
@media (max-width: 1100px) {
  .weather-section, .news-section {
    flex-direction: column;
  }
  .news-detail {
    width: auto;
    min-width: 0;
    position: static;
  }
  .current-weather {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 700px) {
  .info-feed-page {
    padding-right: 0;
  }
  .page-header, .status-strip, .panel-head {
    flex-direction: column;
    align-items: stretch;
  }
  .status-item {
    min-width: 0;
  }
  .weather-metrics, .daily-item {
    grid-template-columns: 1fr;
  }
  .news-item img {
    display: none;
  }
}
</style>
