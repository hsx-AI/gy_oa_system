import request from '@/utils/request'

const P = '/confidentiality-ledger'

function toFormData(data = {}) {
  const fd = new FormData()
  fd.append('applicant', data.applicant || '')
  fd.append('paper_title', data.paper_title || '')
  fd.append('apply_time', data.apply_time || '')
  fd.append('material_form', data.material_form || '')
  fd.append('publish_channel', data.publish_channel || '')
  fd.append('is_confidential', data.is_confidential || '')
  fd.append('military_research', data.military_research || '')
  fd.append('current_user', data.current_user || '')
  return fd
}

export function getConfidentialityLedgerRecords(params) {
  return request({ url: `${P}/records`, method: 'get', params })
}

export function createConfidentialityLedgerRecord(data) {
  return request({ url: `${P}/records`, method: 'post', data: toFormData(data) })
}

export function updateConfidentialityLedgerRecord(id, data) {
  return request({ url: `${P}/records/${id}`, method: 'put', data: toFormData(data) })
}

export function deleteConfidentialityLedgerRecord(id) {
  return request({ url: `${P}/records/${id}`, method: 'delete' })
}

export function exportConfidentialityLedger(params) {
  return request({ url: `${P}/export`, method: 'get', params, responseType: 'blob' })
}
