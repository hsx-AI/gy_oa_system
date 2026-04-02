import request from '@/utils/request'

const P = '/tech-problem'

/** 问题列表（含搜索、分页） */
export function getTechProblemList(params) {
  return request({ url: `${P}/list`, method: 'get', params })
}

/** 问题详情 */
export function getTechProblemDetail(id) {
  return request({ url: `${P}/detail`, method: 'get', params: { id } })
}

/** 新建问题（FormData，含图片） */
export function createTechProblem(formData) {
  return request({ url: `${P}/create`, method: 'post', data: formData, timeout: 60000 })
}

/** 更新问题（FormData，含图片） */
export function updateTechProblem(id, formData) {
  return request({ url: `${P}/update`, method: 'post', data: formData, params: { id }, timeout: 60000 })
}

/** 删除问题 */
export function deleteTechProblem(id) {
  return request({ url: `${P}/delete`, method: 'delete', params: { id } })
}

/** 获取分类列表 */
export function getTechProblemCategories() {
  return request({ url: `${P}/categories`, method: 'get' })
}

/** 获取所属专业列表（yggl.lsys） */
export function getTechProblemDepartments() {
  return request({ url: `${P}/departments`, method: 'get' })
}

/** 图片访问 URL */
export function getTechProblemImageUrl(filename) {
  return `/api${P}/image?filename=${encodeURIComponent(filename)}`
}
