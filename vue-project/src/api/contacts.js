import request from '@/utils/request'

export function getContacts(params) {
  return request({ url: '/contacts/list', method: 'get', params })
}
