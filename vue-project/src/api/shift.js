import request from '@/utils/request'

export function getDepartments() {
  return request({ url: '/shift/departments', method: 'get' })
}

export function getShiftHolidayOptions(params) {
  return request({ url: '/shift/holiday-options', method: 'get', params })
}

export function getShiftConfig(params) {
  return request({ url: '/shift/config', method: 'get', params })
}

export function getShiftCoverageGap(params) {
  return request({ url: '/shift/coverage-gap', method: 'get', params })
}

export function saveShiftConfig(data) {
  return request({ url: '/shift/config', method: 'post', data })
}

export function getSchedule(params) {
  return request({ url: '/shift/schedule', method: 'get', params })
}

export function saveSchedule(data) {
  return request({ url: '/shift/schedule', method: 'post', data })
}

export function saveDayPlans(data) {
  return request({ url: '/shift/day-plans', method: 'post', data })
}

export function autoSchedule(data) {
  return request({ url: '/shift/auto-schedule', method: 'post', data })
}

export function copyLastMonth(data) {
  return request({ url: '/shift/copy-last-month', method: 'post', data })
}

export function clearSchedule(data) {
  return request({ url: '/shift/clear-schedule', method: 'post', data })
}

export function setDayLocks(data) {
  return request({ url: '/shift/day-locks', method: 'post', data })
}

export function setDayNoDuty(data) {
  return request({ url: '/shift/day-noduty', method: 'post', data })
}

export function runShiftScheduleEmail(params) {
  return request({ url: '/email/run-shift-schedule-email', method: 'post', params })
}

/** 预览节假日值班表合并邮件（不发信） */
export function previewShiftHolidayEmail(params) {
  return request({ url: '/email/preview-shift-holiday-email', method: 'get', params })
}

/** 手动/临时补发节假日值班表邮件（按各科室排班邮件收件人配置） */
export function runShiftHolidayEmail(params) {
  return request({ url: '/email/run-shift-holiday-email', method: 'post', params })
}

export function getShiftScheduleEmailBlockedPlans(params) {
  return request({ url: '/email/shift-schedule-email-blocked-plans', method: 'get', params })
}

export function getShiftScheduleEmailSentWeeks(params) {
  return request({ url: '/email/shift-schedule-email-sent-weeks', method: 'get', params })
}
