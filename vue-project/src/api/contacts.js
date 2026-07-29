import request from '@/utils/request'

export function getContacts(params) {
  return request({ url: '/contacts/list', method: 'get', params })
}

export function canManageCompanyContacts(name) {
  return request({ url: '/contacts/can-manage-company', method: 'get', params: { name } })
}

export function importCompanyContacts(file, name) {
  const data = new FormData()
  data.append('file', file)
  return request({
    url: '/contacts/company/import',
    method: 'post',
    params: { name },
    data,
  })
}
