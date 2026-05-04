import { getSchedule } from '@/api/shift'
import { shouldSkipOvertimeShiftValidation } from '@/utils/overtimeLeaderRules'

function normalizeDate(d) {
  return String(d || '').trim().slice(0, 10)
}

function normalizeTime(t, fallback) {
  const raw = String(t || fallback || '').trim()
  if (!raw) return ''
  const timePart = raw.includes(' ') ? raw.split(' ').pop() : raw.replace(/^\d{4}-\d{2}-\d{2}T?/, '')
  const parts = timePart.split(':')
  const h = parseInt(parts[0] || '0', 10)
  const m = parseInt(parts[1] || '0', 10)
  const s = parseInt(parts[2] || '0', 10)
  if ([h, m, s].some(Number.isNaN)) return ''
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function timeToMinutes(t) {
  const parts = normalizeTime(t).split(':')
  if (parts.length < 2) return null
  const h = parseInt(parts[0], 10)
  const m = parseInt(parts[1], 10)
  const s = parseInt(parts[2] || '0', 10)
  if ([h, m, s].some(Number.isNaN)) return null
  return h * 60 + m + s / 60
}

function hasOverlap(startA, endA, startB, endB) {
  return startA < endB && endA > startB
}

function shiftRanges(shiftType) {
  const v = String(shiftType || '').trim()
  if (v === '白班') return [{ label: '白班', start: 0, end: 17 * 60 }]
  if (v === '夜班') return [{ label: '夜班', start: 17 * 60, end: 24 * 60 }]
  if (v === '白+夜') {
    return [
      { label: '白班', start: 0, end: 17 * 60 },
      { label: '夜班', start: 17 * 60, end: 24 * 60 },
    ]
  }
  return []
}

function shouldValidateShiftForTicket(form) {
  if (shouldSkipOvertimeShiftValidation(form)) return false
  return String(form?.level || '').trim() === '值班' && String(form?.needExchangeTicket || '').trim() === '是'
}

export async function validateOvertimeShiftTicket(form) {
  if (!shouldValidateShiftForTicket(form)) return { valid: true }

  const department = String(form?.department || '').trim()
  const name = String(form?.name || '').trim()
  const date = normalizeDate(form?.date)
  const start = timeToMinutes(form?.startTime || '08:00:00')
  const end = timeToMinutes(form?.endTime || '17:00:00')

  if (!department || !name || !date) {
    return { valid: false, message: '值班申请换休票时，需先确认本人科室、姓名和加班日期。' }
  }
  if (start == null || end == null || end <= start) {
    return { valid: false, message: '值班申请换休票时，请填写有效的加班开始和结束时间。' }
  }

  let res
  try {
    res = await getSchedule({ department, start_date: date, end_date: date })
  } catch (err) {
    const detail = err?.response?.data?.detail
    return {
      valid: false,
      message: Array.isArray(detail) ? detail.map((d) => d.msg || d).join('; ') : (detail || err.message || '排班校验失败，请稍后重试。'),
    }
  }
  if (!res?.success) {
    return { valid: false, message: res?.message || '排班校验失败，请稍后重试。' }
  }

  const dayMap = res.schedule?.[name] || {}
  const shiftType = String(dayMap[date] || '').trim()
  const ranges = shiftRanges(shiftType)
  if (!ranges.length) {
    return {
      valid: false,
      message: `${date} 未查询到您本人的值班排班记录，值班申请换休票不能提交。`,
    }
  }

  const matched = ranges.some((r) => hasOverlap(start, end, r.start, r.end))
  if (!matched) {
    const rangeText = ranges.map((r) => `${r.label}${formatRange(r.start, r.end)}`).join('、')
    return {
      valid: false,
      message: `${date} 您的排班为${shiftType}（${rangeText}），本次加班时间不在该排班时段内。值班申请换休票要求加班时间与本人历史排班有交集。`,
    }
  }

  return { valid: true, shiftType }
}

function formatRange(start, end) {
  const fmt = (mins) => {
    const h = Math.floor(mins / 60)
    const m = Math.floor(mins % 60)
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
  }
  return `${fmt(start)}-${fmt(end)}`
}
