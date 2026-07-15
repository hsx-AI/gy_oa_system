import request from '@/utils/request'

const P = '/low-value-reimbursement'

export function getLowValueApprovers() {
  return request({ url: `${P}/approvers`, method: 'get' })
}

export function submitLowValueReimbursement(data) {
  const fd = new FormData()
  ;[
    'material_name',
    'specification',
    'unit_price',
    'quantity',
    'supplier',
    'work_no',
    'part_no',
    'usage_detail',
    'applicant',
    'department',
    'approver2',
    'approver3',
    'remark',
  ].forEach((key) => fd.append(key, data[key] ?? ''))
  if (data.photo) fd.append('photo', data.photo)
  if (data.invoice) fd.append('invoice', data.invoice)
  return request({ url: `${P}/apply`, method: 'post', data: fd })
}

export function parseLowValueInvoice(file) {
  const fd = new FormData()
  fd.append('invoice', file)
  return request({ url: `${P}/invoice/parse`, method: 'post', data: fd })
}

export function getPendingLowValueReimbursements(params) {
  return request({ url: `${P}/pending`, method: 'get', params })
}

export function actionLowValueReimbursement(data) {
  const fd = new FormData()
  fd.append('id', data.id)
  fd.append('operator', data.operator)
  fd.append('action', data.action)
  if (data.reject_reason) fd.append('reject_reason', data.reject_reason)
  return request({ url: `${P}/action`, method: 'post', data: fd })
}

export function batchActionLowValueReimbursement(data) {
  const fd = new FormData()
  fd.append('ids', Array.isArray(data.ids) ? data.ids.join(',') : String(data.ids ?? ''))
  fd.append('operator', data.operator)
  fd.append('action', data.action)
  if (data.reject_reason) fd.append('reject_reason', data.reject_reason)
  return request({ url: `${P}/action-batch`, method: 'post', data: fd })
}

export function deleteLowValueReimbursement(data) {
  const fd = new FormData()
  fd.append('id', data.id)
  fd.append('operator', data.operator)
  return request({ url: `${P}/delete`, method: 'post', data: fd })
}

export function getLowValueRecords(params) {
  return request({ url: `${P}/records`, method: 'get', params })
}

export function getLowValueBudgetSummary(params) {
  return request({ url: `${P}/budget/summary`, method: 'get', params })
}

export function getLowValueBudgetList(params) {
  return request({ url: `${P}/budget/list`, method: 'get', params })
}

export function saveLowValueBudget(data) {
  const fd = new FormData()
  fd.append('budget_year', data.budget_year)
  fd.append('total_amount', data.total_amount)
  fd.append('remark', data.remark ?? '')
  fd.append('operator', data.operator ?? '')
  return request({ url: `${P}/budget`, method: 'post', data: fd })
}

export function getMyLowValueApplications(params) {
  return request({ url: `${P}/my-applications`, method: 'get', params })
}

export function lowValueAttachmentUrl(kind, filename, disposition = 'attachment') {
  const base = `/api${P}/attachment?kind=${encodeURIComponent(kind)}&filename=${encodeURIComponent(filename)}`
  return disposition === 'inline' ? `${base}&disposition=inline` : base
}

const IMAGE_EXTS = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']

export function lowValueAttachmentExt(filename) {
  const name = String(filename || '')
  const idx = name.lastIndexOf('.')
  return idx >= 0 ? name.slice(idx + 1).toLowerCase() : ''
}

export function isLowValueImage(filename) {
  return IMAGE_EXTS.includes(lowValueAttachmentExt(filename))
}

export function isLowValuePdf(filename) {
  return lowValueAttachmentExt(filename) === 'pdf'
}

export function lowValueExportUrl(params = {}) {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value) !== '') qs.append(key, value)
  })
  return `/api${P}/export?${qs.toString()}`
}

export function lowValueInvoiceZipUrl(params = {}) {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value) !== '') qs.append(key, value)
  })
  return `/api${P}/invoices/export-zip?${qs.toString()}`
}
