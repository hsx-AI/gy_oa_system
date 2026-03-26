/**
 * 考勤打卡时间列：time_N 与 time_N_mark（0=进 1=出）展示用
 */

export function hasAttendanceTimeMark(record, slot) {
  if (!record) return false
  const t = record[`time_${slot}`]
  const m = record[`time_${slot}_mark`]
  if (t == null || t === '' || String(t).trim() === '' || t === '-') return false
  return m === 0 || m === 1 || m === '0' || m === '1'
}

/** 是否为「出」；否则为「进」（仅在 hasAttendanceTimeMark 为 true 时调用） */
export function isOutAttendanceMark(record, slot) {
  const m = record[`time_${slot}_mark`]
  return m === 1 || m === '1'
}
