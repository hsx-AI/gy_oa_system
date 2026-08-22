import request from '@/utils/request'

/**
 * 获取单点登录免登链接（跳转人事档案等外部系统）
 * @param {string} target - 目标系统标识，如 'B' 表示人事档案系统
 * @param {string} name - 当前登录用户姓名
 * @returns {Promise<{ success: boolean, url: string }>} 返回 B 系统完整入口 URL，前端执行 window.location.href = url 即可跳转
 */
export function getSSOLink(target, name) {
  return request({
    url: '/sso/link',
    method: 'get',
    params: { target, name }
  })
}

/**
 * 获取思想汇报系统待办数量（供 OA 首页待办提醒）
 * @param {Object} params - { name: 当前用户姓名 }
 * @returns {Promise<{ username, pending_reviews, returned_reports, total }>}
 */
export function getSixianghuibaoTodos(params) {
  return request({
    url: '/sso/sixianghuibao-todos',
    method: 'get',
    params
  })
}

/**
 * 获取人事档案系统待办数量（后端代理 GET pending-count，解析对方 { code, data: { myPendingCount, needAuditCount } }）
 * OA 首页与顶栏待办仅展示 needAuditCount
 * @param {Object} params - { name: 当前用户姓名 }
 * @returns {Promise<{ success, myPendingCount?, needAuditCount }>}
 */
export function getPersonnelPendingCount(params) {
  return request({
    url: '/sso/personnel-pending',
    method: 'get',
    params
  })
}

/**
 * 获取人事档案前端页面 URL（公开页内嵌，不含 SSO ticket）
 * @param {string} path - 前端路径，默认 /public-dashboard
 */
export function getPersonnelPageUrl(path = '/public-dashboard') {
  return request({
    url: '/sso/personnel-page-url',
    method: 'get',
    params: { path }
  })
}
