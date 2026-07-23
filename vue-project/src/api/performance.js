import request from '@/utils/request'

export const getPerformancePermission = (params) => request({ url: '/performance/permission', method: 'get', params })
export const getPerformanceRoster = (params) => request({ url: '/performance/roster', method: 'get', params })
export const savePerformance = (data) => request({ url: '/performance/save', method: 'post', data, timeout: 120000 })
export const getPerformanceRecords = (params) => request({ url: '/performance/records', method: 'get', params })
export const getPerformanceHistory = (params) => request({ url: '/performance/history', method: 'get', params })
export const getPerformanceDepartments = (params) => request({ url: '/performance/departments', method: 'get', params })
