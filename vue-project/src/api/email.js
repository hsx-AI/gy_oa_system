import request from '@/utils/request'

export function getEmailConfig(currentUser) {
  return request({ url: '/email/config', method: 'get', params: { current_user: currentUser } })
}

export function updateEmailConfig(data) {
  return request({ url: '/email/config', method: 'post', data })
}

export function sendEmail(data) {
  return request({ url: '/email/send', method: 'post', data })
}

export function previewAttendanceReminder(data) {
  return request({ url: '/email/preview-attendance-reminder', method: 'post', data })
}

export function sendAttendanceReminder(data) {
  return request({ url: '/email/send-attendance-reminder', method: 'post', data })
}

export function getAutoReminderConfig(currentUser) {
  return request({ url: '/email/auto-reminder-config', method: 'get', params: { current_user: currentUser } })
}

export function saveAutoReminderConfig(data) {
  return request({ url: '/email/auto-reminder-config', method: 'post', data })
}

export function getAutoReminderLog(currentUser) {
  return request({ url: '/email/auto-reminder-log', method: 'get', params: { current_user: currentUser } })
}
