import request from '@/utils/request'

const P = '/bid-templates'

export function getBidTemplateOptions() {
  return request({ url: `${P}/options`, method: 'get' })
}

export function getBidTemplateList(params) {
  return request({ url: `${P}/list`, method: 'get', params })
}

export function getBidTemplateHistory(templateId) {
  return request({ url: `${P}/history`, method: 'get', params: { template_id: templateId } })
}

export function uploadBidTemplate(payload) {
  const form = new FormData()
  form.append('file', payload.file)
  for (const key of [
    'title',
    'template_id',
    'description',
    'change_note',
    'uploader',
    'machine_type',
    'file_scope',
    'speed',
    'capacity',
    'shaft_type',
    'support_arm_count',
    'reference_project',
    'custom_tags'
  ]) {
    form.append(key, payload[key] || '')
  }
  return request({ url: `${P}/upload`, method: 'post', data: form, timeout: 120000 })
}

export function getBidTemplateFileUrl({ templateId, versionId } = {}) {
  const qs = new URLSearchParams()
  if (templateId) qs.set('template_id', templateId)
  if (versionId) qs.set('version_id', versionId)
  return `/api${P}/file?${qs.toString()}`
}
