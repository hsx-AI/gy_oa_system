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

/** 手动修正 AI 邮件待办任务截止时间 */
export function updateInboxTaskDeadline(data) {
  return request({ url: '/inbox-email/task-deadline', method: 'post', data })
}

/** 标记任务已完成（去旗帜 + 删记录） */
export function completeInboxTask(params) {
  return request({ url: '/inbox-email/complete', method: 'post', params })
}

/** 原个人红旗邮箱待办链路（与经理层公用邮箱独立）。 */
export function getPersonalInboxConfig(currentUser) {
  return request({ url: '/inbox-email/personal/config', method: 'get', params: { current_user: currentUser } })
}
export function updatePersonalInboxConfig(data) {
  return request({ url: '/inbox-email/personal/config', method: 'post', data })
}
export function syncPersonalInbox(currentUser) {
  return request({ url: '/inbox-email/personal/sync', method: 'post', params: { current_user: currentUser } })
}
export function listPersonalInboxTasks(params) {
  return request({ url: '/inbox-email/personal/tasks', method: 'get', params })
}
export function analyzePersonalInbox(params) {
  return request({ url: '/inbox-email/personal/analyze', method: 'post', params })
}
export function completePersonalInboxTask(params) {
  return request({ url: '/inbox-email/personal/complete', method: 'post', params })
}
export function updatePersonalInboxTaskDeadline(data) {
  return request({ url: '/inbox-email/personal/task-deadline', method: 'post', data })
}
export function getPersonalInboxEmailDetail(params) {
  return request({ url: '/inbox-email/personal/detail', method: 'get', params })
}
