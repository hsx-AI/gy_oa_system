import request from '@/utils/request'

export function getBusinessTripMap() {
  return request({
    url: '/business-trip-map',
    method: 'get'
  })
}