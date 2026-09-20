import request from '@/utils/request'

function currentUserName() {
  try {
    const u = JSON.parse(localStorage.getItem('userInfo') || '{}')
    return (u.name || u.userName || '').trim()
  } catch {
    return ''
  }
}

/** Phase 2����ѯ test.xlsx ��Ϣ */
export function getPhase2TestInfo() {
  return request({
    url: '/shared-files/phase2-test-info',
    method: 'get',
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
