export const DEFAULT_WEATHER_LOCATION = '126.66,45.72'

export const cityOptions = [
  { name: '哈尔滨电机厂有限责任公司', location: DEFAULT_WEATHER_LOCATION },
  { name: '北京', location: '101010100' },
  { name: '天津', location: '101030100' },
  { name: '上海', location: '101020100' },
  { name: '重庆', location: '101040100' },
  { name: '石家庄', location: '101090101' },
  { name: '太原', location: '101100101' },
  { name: '呼和浩特', location: '101080101' },
  { name: '沈阳', location: '101070101' },
  { name: '长春', location: '101060101' },
  { name: '哈尔滨', location: '101050101' },
  { name: '南京', location: '101190101' },
  { name: '杭州', location: '101210101' },
  { name: '合肥', location: '101220101' },
  { name: '福州', location: '101230101' },
  { name: '南昌', location: '101240101' },
  { name: '济南', location: '101120101' },
  { name: '郑州', location: '101180101' },
  { name: '武汉', location: '101200101' },
  { name: '长沙', location: '101250101' },
  { name: '广州', location: '101280101' },
  { name: '南宁', location: '101300101' },
  { name: '海口', location: '101310101' },
  { name: '成都', location: '101270101' },
  { name: '贵阳', location: '101260101' },
  { name: '昆明', location: '101290101' },
  { name: '拉萨', location: '101140101' },
  { name: '西安', location: '101110101' },
  { name: '兰州', location: '101160101' },
  { name: '西宁', location: '101150101' },
  { name: '银川', location: '101170101' },
  { name: '乌鲁木齐', location: '101130101' },
  { name: '香港', location: '101320101' },
  { name: '澳门', location: '101330101' },
  { name: '台北', location: '101340101' },
]

export function weatherIcon(text = '') {
  const value = String(text)
  if (/雷|电/.test(value)) return '⛈'
  if (/雪|冻雨|冰粒/.test(value)) return '❄'
  if (/雨|阵雨|暴雨|小雨|中雨|大雨/.test(value)) return '🌧'
  if (/雾|霾|沙|尘|浮尘|扬沙/.test(value)) return '🌫'
  if (/阴/.test(value)) return '☁'
  if (/云/.test(value)) return '⛅'
  if (/晴/.test(value)) return '☀'
  return '🌡'
}
