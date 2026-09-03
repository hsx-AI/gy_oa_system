import request from '@/utils/request'

export function getMashangbanMonths() {
  return request.get('/mashangban/months')
}

export function getMashangbanDept(yearMonth) {
  return request.get('/mashangban/dept', { params: { yearMonth } })
}

export function getMashangbanPerson(yearMonth, dept) {
  return request.get('/mashangban/person', {
    params: { yearMonth, ...(dept ? { dept } : {}) }
  })
}

export function getMashangbanOrders(params) {
  return request.get('/mashangban/orders', { params })
}

export function getMashangbanEmailConfig(currentUser) {
  return request.get('/mashangban/email-config', { params: { current_user: currentUser } })
}

export function saveMashangbanEmailConfig(payload) {
  return request.post('/mashangban/email-config', payload)
}

export function runMashangbanEmail(payload) {
  return request.post('/mashangban/run-email', payload)
}

export function getMashangbanEmailLog(currentUser, limit = 20) {
  return request.get('/mashangban/email-log', { params: { current_user: currentUser, limit } })
}
