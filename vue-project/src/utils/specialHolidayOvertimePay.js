/** 指定假日（春节/国庆节/高温防暑休假）固定 200 元：须 8 点前到、17 点后走（覆盖标准班段） */

export const SPECIAL_FESTIVALS = new Set(['春节', '国庆节', '高温防暑休假'])
export const SPECIAL_DAY_PAY = 200

/** 归一化 HH:mm（忽略秒）；支持 "08:00" / "08:00:00" / "2026-10-01 08:00:00" */
export function normalizeClockHm(t) {
  const raw = String(t || '').trim().replace('T', ' ')
  if (!raw) return ''
  const timePart = raw.includes(' ') ? raw.split(/\s+/).pop() : raw
  const parts = String(timePart).split(':')
  if (parts.length < 2) return ''
  const h = parseInt(parts[0], 10)
  const m = parseInt(parts[1], 10)
  if (Number.isNaN(h) || Number.isNaN(m)) return ''
  return `${String(Math.min(23, Math.max(0, h))).padStart(2, '0')}:${String(Math.min(59, Math.max(0, m))).padStart(2, '0')}`
}

/** 是否覆盖标准班段：开始<=08:00 且 结束>=17:00（固定 200 的前提） */
export function isStrictStandardDutyTime(startTime, endTime) {
  const start = normalizeClockHm(startTime)
  const end = normalizeClockHm(endTime)
  if (!start || !end) return false
  return start <= '08:00' && end >= '17:00'
}

/**
 * 指定假日其他绩效激励金额：
 * - 覆盖标准班段（<=08:00 到 >=17:00）：固定 200；超出 8 小时部分按小时费
 * - 未覆盖：一律按小时费，不给 200
 */
export function calcSpecialHolidayIncentivePay(billableHours, zhibanfei, startTime, endTime) {
  const hours = Number(billableHours) || 0
  const rate = Number(zhibanfei) || 0
  if (hours <= 0) return 0
  if (isStrictStandardDutyTime(startTime, endTime)) {
    const extra = Math.max(0, hours - 8)
    return SPECIAL_DAY_PAY + extra * rate
  }
  return hours * rate
}
