import request from '@/utils/request'
export const trackPageVisit = (data) => request({ url: '/access-dashboard/track', method: 'post', data })
export const getAccessDashboard = (params) => request({ url: '/access-dashboard/overview', method: 'get', params })
