import request from '@/utils/request'

/** 获取共用邮箱配置（脱敏） */
export function getInboxConfig(currentUser) {
  return request({ url: '/inbox-email/config', method: 'get', params: { current_user: currentUser } })
}

/** 更新共用邮箱配置 */
export function updateInboxConfig(data) {
  return request({ url: '/inbox-email/config', method: 'post', data })
}

/** 分页列出共用邮箱收到的邮件 */
export function listInboxEmails(params) {
  return request({ url: '/inbox-email/list', method: 'get', params })
}

/** 获取单封邮件详情（含正文） */
export function getInboxEmailDetail(params) {
  return request({ url: '/inbox-email/detail', method: 'get', params })
}

/** 手动触发一次邮件同步 */
export function syncInboxEmails(currentUser) {
  return request({ url: '/inbox-email/sync', method: 'post', params: { current_user: currentUser } })
}

/** 列出已被大模型识别为“含任务”的邮件（用于看板滚动展示） */
export function listInboxTasks(params) {
  return request({ url: '/inbox-email/tasks', method: 'get', params })
}

/** 手动触发大模型任务抽取（不传 id 则批量处理 pending/failed） */
export function analyzeInboxEmails(params) {
  return request({ url: '/inbox-email/analyze', method: 'post', params })
}

/** 标记任务已完成（去旗帜 + 删记录） */
export function completeInboxTask(params) {
  return request({ url: '/inbox-email/complete', method: 'post', params })
}
