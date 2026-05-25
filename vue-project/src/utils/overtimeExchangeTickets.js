/** 加班换休票：平时加班 1h=0.25张(步长0.25)；值班 1h=0.125张(步长0.125) */

export function overtimeWorkMinutesBetween(st, et) {
  if (!st || !et) return 0
  const toMins = (t) => {
    const s = String(t).trim()
    const parts = s.split(':')
    const h = parseInt(parts[0] || '0', 10)
    const m = parseInt(parts[1] || '0', 10)
    const sec = parseInt(parts[2] || '0', 10)
    return h * 60 + m + sec / 60
  }
  const startMins = toMins(st)
  const endMins = toMins(et)
  let mins = endMins - startMins
  if (mins <= 0) return 0
  const lunchStart = 12 * 60
  const lunchEnd = 13 * 60
  if (startMins < lunchEnd && endMins > lunchStart) {
    const overlap = Math.min(endMins, lunchEnd) - Math.max(startMins, lunchStart)
    mins = Math.max(0, mins - overlap)
  }
  return mins
}

export function calcOvertimeExchangeTicketsFromHours(hours, level = '平时加班') {
  if (!hours || hours <= 0) return 0
  const isDuty = String(level || '').trim() === '值班'
  const step = isDuty ? 0.125 : 0.25
  const perHour = isDuty ? 0.125 : 0.25
  const raw = hours * perHour
  return Math.floor(raw / step + 1e-9) * step
}

export function calcOvertimeExchangeTicketsFromTimes(startTime, endTime, level = '平时加班') {
  const mins = overtimeWorkMinutesBetween(startTime, endTime)
  return calcOvertimeExchangeTicketsFromHours(mins / 60, level)
}

export function overtimeExchangeTicketHint(level = '平时加班') {
  if (String(level || '').trim() === '值班') {
    return '值班：1小时=0.125张，以0.125为单位，不足0.125张舍弃'
  }
  return '1天=8小时=2张，以0.25为单位，不足0.25张舍弃'
}
