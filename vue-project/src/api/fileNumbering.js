import request from '@/utils/request'

const P = '/file-numbering'

/** 工作号列表 */
export function getGzhList(params) {
  return request({ url: `${P}/gzh/list`, method: 'get', params })
}

/** 添加工作号 */
export function addGzh(data) {
  return request({ url: `${P}/gzh/add`, method: 'post', data })
}

/** 技术文件分类列表 */
export function getBianhaoFlList(params) {
  return request({ url: `${P}/bianhao-fl/list`, method: 'get', params })
}

/** 添加技术文件分类 */
export function addBianhaoFl(data) {
  return request({ url: `${P}/bianhao-fl/add`, method: 'post', data })
}

/** 技术文件编号-添加 */
export function addBianhaoTech(data) {
  return request({ url: `${P}/bianhao/tech/add`, method: 'post', data })
}

/** 技术文件编号-列表 */
export function getBianhaoTechList(params) {
  return request({ url: `${P}/bianhao/tech/list`, method: 'get', params })
}

/** 技术管理分类选项 */
export function getJsglFenlei() {
  return request({ url: `${P}/bianhao-jsgl/fenlei`, method: 'get' })
}

/** 技术管理编号-添加 */
export function addBianhaogljs(data) {
  return request({ url: `${P}/bianhaogljs/add`, method: 'post', data })
}

/** 技术管理编号-列表 */
export function getBianhaogljsList(params) {
  return request({ url: `${P}/bianhaogljs/list`, method: 'get', params })
}

/** 管理文件分类选项 */
export function getGlFenlei() {
  return request({ url: `${P}/bianhaogl/fenlei`, method: 'get' })
}

/** 管理文件编号-添加 */
export function addBianhaogl(data) {
  return request({ url: `${P}/bianhaogl/add`, method: 'post', data })
}

/** 管理文件编号-列表 */
export function getBianhaoglList(params) {
  return request({ url: `${P}/bianhaogl/list`, method: 'get', params })
}

/** 上传编号对应 PDF（仅支持 PDF），按编号代码命名 type: tech | jsgl | manage, code: 编号代码 */
export function uploadNumberingPdf(type, code, file) {
  const form = new FormData()
  form.append('file', file)
  return request({
    url: `${P}/file/upload`,
    method: 'post',
    params: { type, code },
    data: form,
    timeout: 60000
  })
}

/** 删除编号对应 PDF（按编号代码） */
export function deleteNumberingPdf(type, code) {
  return request({
    url: `${P}/file`,
    method: 'delete',
    params: { type, code }
  })
}

/** 预览/下载 PDF 的 URL（按编号代码），download=1 为下载 */
export function getNumberingFileUrl(type, code, download = 0) {
  return `/api${P}/file?type=${encodeURIComponent(type)}&code=${encodeURIComponent(code)}&download=${download}`
}
