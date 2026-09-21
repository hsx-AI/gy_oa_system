import request from '@/utils/request'

export const getPerformancePermission = (params) => request({ url: '/performance/permission', method: 'get', params })
export const getPerformanceRoster = (params) => request({ url: '/performance/roster', method: 'get', params })
export const savePerformance = (data) => request({ url: '/performance/save', method: 'post', data, timeout: 120000 })
export const getPerformanceRecords = (params) => request({ url: '/performance/records', method: 'get', params })
export const getPerformanceHistory = (params) => request({ url: '/performance/history', method: 'get', params })
export const getPerformanceDepartments = (params) => request({ url: '/performance/departments', method: 'get', params })
export const getQuarterlyPerformanceRoster = (params) => request({ url: '/performance/quarterly/roster', method: 'get', params })
export const saveQuarterlyPerformance = (data) => request({ url: '/performance/quarterly/save', method: 'post', data, timeout: 120000 })
export const getPerformanceOnlineContext = (params) => request({ url: '/performance/online/context', method: 'get', params })
export const openPerformanceOnline = (data) => request({ url: '/performance/online/open', method: 'post', data, timeout: 120000 })
export const getPerformanceOnlineEditorConfig = (id, params) => request({ url: `/performance/online/docs/${id}/editor-config`, method: 'get', params })
export const uploadPerformanceTemplate = (params, data) => request({ url: '/performance/online/template', method: 'post', params, data, timeout: 120000 })
