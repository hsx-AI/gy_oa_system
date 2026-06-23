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

/** 获取大模型配置（DeepSeek 开关 + 本地候选模型列表 + 当前生效模型） */
export function getLlmConfig(params) {
  return request({ url: '/health-monitor/llm-config', method: 'get', params })
}

/** 保存/清空 DeepSeek API Key */
export function saveDeepseekKey(data) {
  return request({ url: '/health-monitor/llm-config', method: 'post', data })
}

/** 新增一个本地大模型候选 */
export function addLlmModel(data) {
  return request({ url: '/health-monitor/llm-models', method: 'post', data })
}

/** 删除一个本地大模型候选 */
export function deleteLlmModel(modelId, params) {
  return request({ url: `/health-monitor/llm-models/${modelId}`, method: 'delete', params })
}

/** 将某个本地模型设为当前生效模型 */
export function activateLlmModel(modelId, data) {
  return request({ url: `/health-monitor/llm-models/${modelId}/activate`, method: 'post', data })
}

/** 对当前生效模型或指定本地模型做一次速度/连通性测试（返回 tokens/s 等） */
export function testLlmModel(data) {
  return request({ url: '/health-monitor/llm-test', method: 'post', data, timeout: 80000 })
}

export function saveLlmSceneModel(scene, data) {
  return request({ url: `/health-monitor/llm-scenes/${scene}/model`, method: 'post', data })
}
