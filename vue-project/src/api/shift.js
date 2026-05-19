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

export function runShiftScheduleEmail(params) {
  return request({ url: '/email/run-shift-schedule-email', method: 'post', params })
}

export function getShiftScheduleEmailSentWeeks(params) {
  return request({ url: '/email/shift-schedule-email-sent-weeks', method: 'get', params })
}
