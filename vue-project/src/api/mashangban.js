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
