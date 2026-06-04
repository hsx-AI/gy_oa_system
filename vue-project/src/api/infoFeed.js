import request from '@/utils/request'

export function getInfoFeedSummary() {
  return request.get('/info-feed/summary')
}

export function getWeatherNow(location) {
  return request.get('/info-feed/weather/now', { params: { location } })
}

export function getWeatherHourly(hours, location) {
  return request.get(`/info-feed/weather/hourly/${hours}`, { params: { location } })
}

export function getWeatherDaily(days, location) {
  return request.get(`/info-feed/weather/daily/${days}`, { params: { location } })
}

export function getNewsList(params) {
  return request.get('/info-feed/news/list', { params })
}

export function getNewsDetail(uniquekey) {
  return request.get('/info-feed/news/detail', { params: { uniquekey } })
}
