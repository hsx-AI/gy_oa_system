import request from '@/utils/request'

export function hxpBatch(data) {
  return request({
    url: '/admin/hxp/batch',
    method: 'post',
    data,
  })
}

export function publishNotification(data) {
  return request({
    url: '/auth/notification/publish',
    method: 'post',
    data,
  })
}

export function listNotifications() {
  return request({
    url: '/auth/notification/list',
    method: 'get',
  })
}

export function dismissNotification(data) {
  return request({
    url: '/auth/notification/dismiss',
    method: 'post',
    data,
  })
}

export function deleteNotification(data) {
  return request({
    url: '/auth/notification/delete',
    method: 'post',
    data,
  })
}
