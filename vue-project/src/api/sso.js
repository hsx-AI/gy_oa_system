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
