import request from '@/utils/request'

const P = '/department-policy'

/** 检查是否有制度上传权限（仅综合技术室主任/副主任） */
export function getPolicyUploadPermission(params) {
  return request({ url: `${P}/can-upload`, method: 'get', params })
}

/** 制度列表（含关键词搜索） */
export function getPolicyList(params) {
  return request({ url: `${P}/list`, method: 'get', params })
}

/** 上传制度文件 */
export function uploadPolicy({ title, issue_time, remark, uploader, file }) {
  const form = new FormData()
  form.append('file', file)
  return request({
    url: `${P}/upload`,
    method: 'post',
    params: { title, issue_time, remark, uploader },
    data: form,
    timeout: 60000
  })
}

/** 删除制度（仅综合技术室主任/副主任可删除） */
export function deletePolicy(id, currentUser) {
  return request({
    url: `${P}/delete`,
    method: 'delete',
    params: { id, current_user: currentUser }
  })
}

/** 向量深度搜索（AI 语义检索） */
export function vectorSearchPolicy(params) {
  return request({ url: `${P}/vector-search`, method: 'get', params })
}

/** 预览/下载文件 URL */
export function getPolicyFileUrl(id, download = 0) {
  return `/api${P}/file?id=${encodeURIComponent(id)}&download=${download}`
}
