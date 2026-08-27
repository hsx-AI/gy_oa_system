import request from '@/utils/request'

const P = '/file-page-counter'

/** 批量统计上传文件的页数 */
export function countFilePages(files) {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }
  return request({
    url: `${P}/count`,
    method: 'post',
    data: formData,
    timeout: 600000,
  })
}
