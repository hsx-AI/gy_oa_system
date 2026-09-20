import request from '@/utils/request'

function currentUserName() {
  try {
    const u = JSON.parse(localStorage.getItem('userInfo') || '{}')
    return (u.name || u.userName || '').trim()
  } catch {
    return ''
  }
}

export function listSharedFiles(params = {}) {
  return request({
    url: '/shared-files',
    method: 'get',
    params: {
      current_user: currentUserName(),
      parent_id: params.parent_id || undefined
    }
  })
}

export function createSharedFolder(data) {
  return request({
    url: '/shared-files/folders',
    method: 'post',
    data: {
      name: data.name,
      parent_id: data.parent_id || null,
      current_user: currentUserName()
    }
  })
}

export function uploadSharedFile({ file, parent_id }) {
  const form = new FormData()
  form.append('current_user', currentUserName())
  if (parent_id) form.append('parent_id', String(parent_id))
  form.append('file', file)
  return request({
    url: '/shared-files/upload',
    method: 'post',
    data: form
  })
}

export function renameSharedFile(fileId, name) {
  return request({
    url: `/shared-files/${fileId}`,
    method: 'patch',
    data: { name, current_user: currentUserName() }
  })
}

export function deleteSharedFile(fileId) {
  return request({
    url: `/shared-files/${fileId}`,
    method: 'delete',
    params: { current_user: currentUserName() }
  })
}

export function getSharedFileMeta(fileId) {
  return request({
    url: `/shared-files/${fileId}`,
    method: 'get',
    params: { current_user: currentUserName() }
  })
}

export function getEditorConfig(fileId) {
  return request({
    url: `/shared-files/${fileId}/editor-config`,
    method: 'get',
    params: { current_user: currentUserName() }
  })
}

export function getPhase2TestInfo() {
  return request({
    url: '/shared-files/phase2-test-info',
    method: 'get',
    params: { current_user: currentUserName() }
  })
}

export function downloadSharedFileUrl(fileId) {
  const user = encodeURIComponent(currentUserName())
  return `/api/shared-files/${fileId}/download?current_user=${user}`
}
