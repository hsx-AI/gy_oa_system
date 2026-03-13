import request from '@/utils/request'

/** 检查当前用户是否有系统健康监控权限（webconfig.admin1） */
export function getHealthMonitorPermission(params) {
  return request({ url: '/health-monitor/permission', method: 'get', params })
}

/** 获取系统健康监控概览（各组件状态） */
export function getHealthOverview(params) {
  return request({ url: '/health-monitor/overview', method: 'get', params })
}
