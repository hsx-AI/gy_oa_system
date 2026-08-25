import request from '@/utils/request'

const P = '/action-items'

export const getActionPermissions = current_user =>
  request({ url: `${P}/permissions`, method: 'get', params: { current_user } })

export const getActionDirectory = current_user =>
  request({ url: `${P}/directory`, method: 'get', params: { current_user } })

export const getActionDashboard = current_user =>
  request({ url: `${P}/dashboard`, method: 'get', params: { current_user } })

export const getMeetingMinutes = params =>
  request({ url: `${P}/minutes`, method: 'get', params })

export const getMeetingMinute = (id, current_user) =>
  request({ url: `${P}/minutes/${id}`, method: 'get', params: { current_user } })

export const deleteMeetingMinute = (id, current_user) =>
  request({ url: `${P}/minutes/${id}`, method: 'delete', params: { current_user } })

export function createMeetingMinute(form) {
  return request({ url: `${P}/minutes`, method: 'post', data: form, timeout: 180000 })
}

export const extractMeetingActions = (id, current_user) =>
  request({
    url: `${P}/minutes/${id}/extract`,
    method: 'post',
    params: { current_user },
    timeout: 180000,
  })

export const getActions = params =>
  request({ url: P, method: 'get', params })

export const getActionDetail = (id, current_user) =>
  request({ url: `${P}/${id}`, method: 'get', params: { current_user } })

export const createActionDraft = data =>
  request({ url: `${P}/drafts`, method: 'post', data })

export const updateAction = (id, data) =>
  request({ url: `${P}/${id}`, method: 'put', data })

export const mergeActions = data =>
  request({ url: `${P}/merge`, method: 'post', data })

export const splitAction = (id, data) =>
  request({ url: `${P}/${id}/split`, method: 'post', data })

export const cancelActionDraft = (id, data) =>
  request({ url: `${P}/${id}/cancel-draft`, method: 'post', data })

export const cancelPublishedAction = (id, data) =>
  request({ url: `${P}/${id}/cancel`, method: 'post', data })

export const forceCompleteAction = (id, data) =>
  request({ url: `${P}/${id}/force-complete`, method: 'post', data })

export const publishActions = data =>
  request({ url: `${P}/publish`, method: 'post', data })

export const receiveAction = (id, data) =>
  request({ url: `${P}/${id}/receive`, method: 'post', data })

export const assignActionResponsible = (id, data) =>
  request({ url: `${P}/${id}/assign`, method: 'post', data })

export const addActionProgress = (id, form) =>
  request({ url: `${P}/${id}/progress`, method: 'post', data: form })

export const applyActionCompletion = (id, form) =>
  request({ url: `${P}/${id}/completion`, method: 'post', data: form })

export const approveActionCompletion = (id, data) =>
  request({ url: `${P}/completions/${id}/approve`, method: 'post', data })

export const applyActionChange = (id, data) =>
  request({ url: `${P}/${id}/changes`, method: 'post', data })

export const approveActionChange = (id, data) =>
  request({ url: `${P}/changes/${id}/approve`, method: 'post', data })

export const getPendingActionApprovals = current_user =>
  request({ url: `${P}/approvals/pending`, method: 'get', params: { current_user } })

export function remindAction(id, currentUser, note) {
  const data = new FormData()
  data.append('current_user', currentUser)
  data.append('note', note)
  return request({ url: `${P}/${id}/remind`, method: 'post', data })
}

export const getMyActionReminders = params =>
  request({ url: `${P}/reminders/my`, method: 'get', params })

export const readActionReminder = (id, data) =>
  request({ url: `${P}/reminders/${id}/read`, method: 'post', data })

export const actionAttachmentUrl = (id, currentUser) =>
  `/api${P}/attachments/${id}?current_user=${encodeURIComponent(currentUser)}`

export function exportActionItems(params) {
  return request({ url: `${P}/export`, method: 'get', params, responseType: 'blob' })
}
