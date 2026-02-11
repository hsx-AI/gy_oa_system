/**
 * 请假时长计算（考虑 holiday 表：排除周六日与假期，调休日算工作日）
 * holidayMap: { "YYYY-MM-DD": "类型" }，类型含「班」为调休上班，含「假」或「休」为放假
 */

/**
 * 将日期格式化为 YYYY-MM-DD（统一键格式）
 * @param {Date|string} date - Date 或 "YYYY-MM-DD" / "YYYY-M-D"
 */
export function normalizeDateKey(date) {
  if (!date) return ''
  if (date instanceof Date) {
    const y = date.getFullYear()
    const m = String(date.getMonth() + 1).padStart(2, '0')
    const d = String(date.getDate()).padStart(2, '0')
    return `${y}-${m}-${d}`
  }
  const s = String(date).trim()
  if (!s) return ''
  const parts = s.split(/[-/]/).map(Number).filter(n => !isNaN(n))
  if (parts.length < 3) return s
  const [y, mo, day] = parts
  return `${y}-${String(mo).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

/**
 * 判断是否为工作日
 * - 假期表中 type 含「班」：调休上班，算工作日
 * - 假期表中 type 含「假」或「休」：放假，不算工作日
 * - 周六日：不算工作日（除非该日为调休上班）
 */
export function isWorkday(date, holidayMap) {
  if (!date) return false
  const key = normalizeDateKey(date)
  const type = (holidayMap && holidayMap[key]) || ''
  if (type && type.includes('班')) return true
  if (type && (type.includes('假') || type.includes('休'))) return false
  const dow = date.getDay()
  return dow !== 0 && dow !== 6
}

/**
 * 解析 datetime-local 字符串为本地 Date
 */
function parseLocalDateTime(str) {
  if (!str || typeof str !== 'string') return null
  const s = str.trim().replace('T', ' ')
  const [datePart, timePart] = s.split(' ')
  if (!datePart) return null
  const parts = datePart.split('-').map(Number)
  if (parts.length < 3) return null
  const [y, mo, day] = parts
  if (!timePart) return new Date(y, mo - 1, day, 0, 0, 0, 0)
  const [h, m] = timePart.split(':').map(Number)
  return new Date(y, mo - 1, day, h || 0, m || 0, 0, 0)
}

/**
 * 根据开始、结束时间计算请假时长(天)
 * - 工作日：排除周六日 + 排除假期表内「假/休」；调休上班（表中含「班」）计为工作日
 * - 每日工作 8 小时（8:00-12:00、13:00-17:00），最小单位 0.25 天
 * @param {string} startStr - 开始时间
 * @param {string} endStr - 结束时间
 * @param {Object} holidayMap - 可选，日期 -> 类型（来自 holiday 表）；不传则仅排除周六日
 */
export function calcDurationFromTimes(startStr, endStr, holidayMap = null) {
  if (!startStr || !endStr) return 0
  try {
    const start = parseLocalDateTime(startStr)
    const end = parseLocalDateTime(endStr)
    if (!start || !end || end <= start) return 0

    const WORK_AM = { h: 8, m: 0 }
    const WORK_AM_END = { h: 12, m: 0 }
    const WORK_PM = { h: 13, m: 0 }
    const WORK_PM_END = { h: 17, m: 0 }

    function toMs(d, h, m) {
      return new Date(d.getFullYear(), d.getMonth(), d.getDate(), h, m, 0, 0).getTime()
    }

    let workMs = 0
    const dayMs = 24 * 60 * 60 * 1000
    let d = new Date(start.getFullYear(), start.getMonth(), start.getDate(), 0, 0, 0, 0)
    const endDateOnly = new Date(end.getFullYear(), end.getMonth(), end.getDate(), 23, 59, 59, 999)

    while (d <= endDateOnly) {
      const isWork = holidayMap != null ? isWorkday(d, holidayMap) : (d.getDay() !== 0 && d.getDay() !== 6)
      if (!isWork) {
        d.setTime(d.getTime() + dayMs)
        continue
      }

      const amStart = toMs(d, WORK_AM.h, WORK_AM.m)
      const amEnd = toMs(d, WORK_AM_END.h, WORK_AM_END.m)
      const pmStart = toMs(d, WORK_PM.h, WORK_PM.m)
      const pmEnd = toMs(d, WORK_PM_END.h, WORK_PM_END.m)
      const ov = (a, b) => Math.max(0, Math.min(end.getTime(), b) - Math.max(start.getTime(), a))
      workMs += ov(amStart, amEnd) + ov(pmStart, pmEnd)
      d.setTime(d.getTime() + dayMs)
    }

    const workHours = workMs / (1000 * 60 * 60)
    const days = workHours / 8
    const rounded = Math.ceil(days * 4) / 4
    return rounded < 0.25 ? 0.25 : Math.round(rounded * 100) / 100
  } catch {
    return 0
  }
}
