import request from '@/utils/request'

export function getPersonnelAttendanceScene(params) {
  return request({
    url: '/personnel-visualization/scene',
    method: 'get',
    params,
  })
}
