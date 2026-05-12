import request from '@/utils/request'

const P = '/attendance-exception'

/** 获取审批人 level=first/second */
export function getKqycApprovers(params) {
  return request({ url: `${P}/approvers`, method: 'get', params })
}

/** 提交打卡异常申请（FormData，含附件） */
export function submitKqycApply(data) {
  const fd = new FormData()
  fd.append('applicant', data.applicant || '')
  fd.append('department', data.department || '')
  fd.append('attendance_date', data.attendance_date || '')
  fd.append('time_from', data.time_from || '')
  fd.append('time_to', data.time_to || '')
  fd.append('reason_type', data.reason_type || '')
  fd.append('description', data.description || '')
  fd.append('first_approver', data.first_approver || '')
  fd.append('second_approver', data.second_approver || '')
  if (data.attachment) fd.append('attachment', data.attachment)
  return request({ url: `${P}/apply`, method: 'post', data: fd })
}

/** 获取审批人的待审批列表（自动区分一/二级） */
export function getPendingKqyc(params) {
  return request({ url: `${P}/pending`, method: 'get', params })
}

/** 审批操作 approve/reject */
export function approveKqyc(data) {
  const fd = new FormData()
  fd.append('id', data.id)
  fd.append('approver', data.approver || '')
  fd.append('action', data.action || '')
  if (data.reject_reason) fd.append('reject_reason', data.reject_reason)
  return request({ url: `${P}/approve`, method: 'post', data: fd })
}

/** dakaman 已读确认列表 */
export function getKqycDakamanPending(params) {
  return request({ url: `${P}/pending-dakaman`, method: 'get', params })
}

/** dakaman 标记已读确认 */
export function confirmKqycByDakaman(data) {
  const fd = new FormData()
  fd.append('id', data.id)
  fd.append('current_user', data.current_user || '')
  return request({ url: `${P}/dakaman-confirm`, method: 'post', data: fd })
}

/** 查询记录（按权限） */
export function getKqycRecords(params) {
  return request({ url: `${P}/records`, method: 'get', params })
}

/** 我的申请 */
export function getMyKqycApplications(params) {
  return request({ url: `${P}/my-applications`, method: 'get', params })
}

/** 附件下载 URL（直接放 a 标签的 href） */
export function kqycAttachmentUrl(filename) {
  return `/api${P}/attachment?filename=${encodeURIComponent(filename)}`
}
