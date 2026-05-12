import request from '@/utils/request'

const P = '/rotor-blade-balance'

export function saveRotorBladeBalanceRecord(data) {
  return request({
    url: `${P}/records`,
    method: 'post',
    data
  })
}

export function listRotorBladeBalanceRecords(params) {
  return request({
    url: `${P}/records`,
    method: 'get',
    params
  })
}

export function getRotorBladeBalanceRecord(id, params) {
  return request({
    url: `${P}/records/${encodeURIComponent(id)}`,
    method: 'get',
    params
  })
}
