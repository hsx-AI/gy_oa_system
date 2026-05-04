import request from '@/utils/request'

const P = '/seal'

/** 获取可选审批人（经理/副经理）*/
export function getSealApprovers() {
  return request({ url: `${P}/approvers`, method: 'get' })
}

/** 提交用印申请（FormData） */
export function submitSealApply(data) {
  const fd = new FormData()
  fd.append('applicant', data.applicant)
  fd.append('department', data.department || '')
  fd.append('seal_type', data.seal_type || '')
  fd.append('reason', data.reason)
  fd.append('approver', data.approver)
  fd.append('remark', data.remark || '')
  if (data.attachment) fd.append('attachment', data.attachment)
  return request({ url: `${P}/apply`, method: 'post', data: fd })
}

/** 获取待审批用印列表 */
export function getPendingSeal(params) {
  return request({ url: `${P}/pending`, method: 'get', params })
}

/** 审批用印申请 */
export function approveSeal(data) {
  const fd = new FormData()
  fd.append('id', data.id)
  fd.append('approver', data.approver)
  fd.append('action', data.action)
  if (data.reject_reason) fd.append('reject_reason', data.reject_reason)
  return request({ url: `${P}/approve`, method: 'post', data: fd })
}

/** 获取全部用印记录（分页） */
export function getSealRecords(params) {
  return request({ url: `${P}/records`, method: 'get', params })
}

/** 附件下载 URL */
export function sealAttachmentUrl(filename) {
  return `/api${P}/attachment?filename=${encodeURIComponent(filename)}`
}

/** 获取我的用印申请 */
export function getMySealApplications(params) {
  return request({ url: `${P}/my-applications`, method: 'get', params })
}

/** 已通过、待用印列表（申请人） */
export function getPendingSealUse(params) {
  return request({ url: `${P}/pending-use`, method: 'get', params })
}

/** 申请人标记已用印 */
export function markSealUsed(data) {
  const fd = new FormData()
  fd.append('id', data.id)
  fd.append('applicant', data.applicant)
  return request({ url: `${P}/mark-used`, method: 'post', data: fd })
}
