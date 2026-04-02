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

/** 换休票全员余额汇总 */
export function getHxpSummary(params) {
  return request({ url: '/admin/hxp/summary', method: 'get', params })
}

/** 换休票个人获取明细 */
export function getHxpDetail(params) {
  return request({ url: '/admin/hxp/detail', method: 'get', params })
}

/** 提交换休票增减审批申请 */
export function submitHxpApproval(data) {
  return request({ url: '/admin/hxp/apply', method: 'post', data })
}

/** 查询待审批的换休票申请（审批人视角） */
export function getPendingHxpApprovals(params) {
  return request({ url: '/admin/hxp/pending-approvals', method: 'get', params })
}

/** 换休票审批操作（通过/驳回） */
export function hxpApprovalAction(id, data) {
  return request({ url: `/admin/hxp/approval/${id}/action`, method: 'post', data })
}

/** 查询自己提交的换休票审批记录 */
export function getMyHxpRequests(params) {
  return request({ url: '/admin/hxp/my-requests', method: 'get', params })
}

/** 重新提交已驳回的换休票管理申请 */
export function resubmitHxpApproval(id, params) {
  return request({ url: `/admin/hxp/approval/${id}/resubmit`, method: 'post', params })
}

/** 部长信息简报：最近 N 天换休票+公出审批通过记录 */
export function getLeaderBriefing(params) {
  return request({ url: '/admin/leader-briefing', method: 'get', params })
}
