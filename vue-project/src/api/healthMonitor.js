import request from '@/utils/request'

/** 检查当前用户是否有系统管理员页面权限（webconfig.admin1） */
export function getHealthMonitorPermission(params) {
  return request({ url: '/health-monitor/permission', method: 'get', params })
}

/** 获取系统状态概览（各组件状态） */
export function getHealthOverview(params) {
  return request({ url: '/health-monitor/overview', method: 'get', params })
}

/** 获取各科室排班邮件功能开关配置 */
export function getShiftEmailFeatureConfig(params) {
  return request({ url: '/health-monitor/shift-email-config', method: 'get', params })
}

/** 保存各科室排班邮件功能开关配置 */
export function saveShiftEmailFeatureConfig(data) {
  return request({ url: '/health-monitor/shift-email-config', method: 'post', data })
}

/** 获取打卡自动拉取与建议截止日配置 */
export function getAttendanceFetchConfig(params) {
  return request({ url: '/health-monitor/attendance-fetch-config', method: 'get', params })
}

/** 保存打卡自动拉取配置（支持多条每日执行时间） */
export function saveAttendanceFetchConfig(data) {
  return request({ url: '/health-monitor/attendance-fetch-config', method: 'post', data })
}

/** 手动触发一次管理人员待办邮件提醒（仅 admin1） */
export function runTodoReminder(params) {
  return request({ url: '/email/run-todo-reminder', method: 'post', params })
}
