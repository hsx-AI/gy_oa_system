import request from '@/utils/request'

export function hxpBatch(data) {
  return request({
    url: '/admin/hxp/batch',
    method: 'post',
    data,
  })
}
