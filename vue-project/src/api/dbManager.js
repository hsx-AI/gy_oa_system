import request from '@/utils/request'

/** 检查当前用户是否有数据库管理权限（webconfig.admin1） */
export function getDbManagerPermission(params) {
  return request({ url: '/db-manager/permission', method: 'get', params })
}

/** 获取所有表名 */
export function getDbManagerTables(params) {
  return request({ url: '/db-manager/tables', method: 'get', params })
}

/** 获取表列信息（含主键） */
export function getDbManagerColumns(tableName, params) {
  return request({
    url: `/db-manager/table/${encodeURIComponent(tableName)}/columns`,
    method: 'get',
    params
  })
}

/** 分页获取表数据 */
export function getDbManagerRows(tableName, params) {
  return request({
    url: `/db-manager/table/${encodeURIComponent(tableName)}/rows`,
    method: 'get',
    params
  })
}

/** 插入一行 */
export function insertDbManagerRow(tableName, data) {
  return request({
    url: `/db-manager/table/${encodeURIComponent(tableName)}/rows`,
    method: 'post',
    data
  })
}

/** 更新一行（body 含主键 + 要更新的列） */
export function updateDbManagerRow(tableName, data) {
  return request({
    url: `/db-manager/table/${encodeURIComponent(tableName)}/rows`,
    method: 'put',
    data
  })
}

/** 删除一行（body 仅需主键列） */
export function deleteDbManagerRow(tableName, data) {
  return request({
    url: `/db-manager/table/${encodeURIComponent(tableName)}/rows`,
    method: 'delete',
    data
  })
}

/** 获取 yggl 批量填充可选字段（仅系统管理员） */
export function getYgglFillFields(params) {
  return request({ url: '/db-manager/yggl-fill-fields', method: 'get', params })
}

/** 按 Excel 批量填充 yggl 指定字段（A列身份证号，B列填充值） */
export function ygglFillByExcel(params, formData) {
  return request({
    url: '/db-manager/yggl-fill-by-excel',
    method: 'post',
    params,
    data: formData
  })
}
