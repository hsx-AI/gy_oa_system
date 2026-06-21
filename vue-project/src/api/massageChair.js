import request from '@/utils/request'

const P = '/massage-chair'

export function getMassageChairConfig() {
  return request({ url: `${P}/config`, method: 'get' })
}

export function getMassageChairSlots(params) {
  return request({ url: `${P}/slots`, method: 'get', params })
}

export function bookMassageChair(data) {
  return request({ url: `${P}/book`, method: 'post', data })
}

export function cancelMassageChairBooking(data) {
  return request({ url: `${P}/cancel`, method: 'post', data })
}
