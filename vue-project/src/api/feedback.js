import request from '@/utils/request'

const P = '/feedback'

// ========== 吐槽墙 ==========
export function submitWall(data) {
  const fd = new FormData()
  fd.append('content', data.content)
  if (data.image) fd.append('image', data.image)
  return request({ url: `${P}/wall/submit`, method: 'post', data: fd })
}
export function getWallList(params) {
  return request({ url: `${P}/wall/list`, method: 'get', params })
}
export function getWallRecords(params) {
  return getWallList({ include_all: true, ...(params || {}) })
}
export function getWallPending(params) {
  return request({ url: `${P}/wall/pending`, method: 'get', params })
}
export function getWallAssigned(params) {
  return request({ url: `${P}/wall/assigned`, method: 'get', params })
}
export function reviewWall(id, data) {
  return request({ url: `${P}/wall/${id}/review`, method: 'post', data })
}
export function likeWall(id, data) {
  return request({ url: `${P}/wall/${id}/like`, method: 'post', data })
}
export function getWallDetail(id, params) {
  return request({ url: `${P}/wall/${id}/detail`, method: 'get', params })
}
export function replyWall(id, data) {
  return request({ url: `${P}/wall/${id}/reply`, method: 'post', data })
}
export function resolveWall(id, data) {
  return request({ url: `${P}/wall/${id}/resolve`, method: 'post', data })
}
export function wallImageUrl(filename) {
  return `/api${P}/wall/image?filename=${encodeURIComponent(filename)}`
}

// ========== 领导匿名信箱 ==========
export function getLeaderTargets() {
  return request({ url: `${P}/leader/targets`, method: 'get' })
}
export function submitLeaderMsg(data) {
  const fd = new FormData()
  fd.append('target_leader', data.target_leader)
  fd.append('content', data.content)
  if (data.image) fd.append('image', data.image)
  return request({ url: `${P}/leader/submit`, method: 'post', data: fd })
}
export function leaderImageUrl(filename) {
  return `/api${P}/leader/image?filename=${encodeURIComponent(filename)}`
}
export function getLeaderInbox(params) {
  return request({ url: `${P}/leader/inbox`, method: 'get', params })
}
export function markLeaderInboxRead(data) {
  return request({ url: `${P}/leader/mark-read`, method: 'post', data })
}
export function replyLeaderMsg(id, data) {
  return request({ url: `${P}/leader/${id}/reply`, method: 'post', data })
}
export function getLeaderPublic() {
  return request({ url: `${P}/leader/public`, method: 'get' })
}

// ========== 系统功能建议 ==========
export function submitSystemFeedback(data) {
  const fd = new FormData()
  fd.append('submitter', data.submitter)
  fd.append('department', data.department || '')
  fd.append('content', data.content)
  if (data.image) fd.append('image', data.image)
  return request({ url: `${P}/system/submit`, method: 'post', data: fd })
}
export function getSystemList() {
  return request({ url: `${P}/system/list`, method: 'get' })
}
export function replySystemFeedback(id, data) {
  return request({ url: `${P}/system/${id}/reply`, method: 'post', data })
}
export function systemImageUrl(filename) {
  return `/api${P}/system/image?filename=${encodeURIComponent(filename)}`
}
