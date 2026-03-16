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
