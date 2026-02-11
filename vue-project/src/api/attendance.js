import request from '@/utils/request'

/**
 * 用户登录
 */
export function login(data) {
  return request({
    url: '/auth/login',
    method: 'post',
    data
  })
}

/** 获取员工信息（用户名、工号、科室、级别、换休票） */
export function getEmployeeProfile(params) {
  return request({ url: '/auth/profile', method: 'get', params })
}

/** 修改密码 */
export function changePassword(data) {
  return request({ url: '/auth/change-password', method: 'post', data })
}

/**
 * 获取打卡记录（已废弃，请使用 queryAttendance）
 * @deprecated 使用 queryAttendance 代替
 */
export function getAttendanceRecords(params) {
  // 重定向到新接口
  return queryAttendance(params)
}

/**
 * 获取智能建议
 */
export function getSuggestions(params) {
  return request({
    url: '/suggestions',
    method: 'get',
    params
  })
}

/**
 * 获取假期数据
 */
export function getHolidays(year) {
  return request({
    url: '/holiday',
    method: 'get',
    params: { year }
  })
}

/**
 * 保存某年的假期与调休设置（仅打卡管理员）
 * @param {Object} data - { year, current_user, holidays: [{ date, type }] }
 */
export function saveHolidays(data) {
  return request({
    url: '/holiday/save',
    method: 'post',
    params: {
      year: data.year,
      current_user: data.current_user
    },
    data: data.holidays || []
  })
}

/** 下载假期调休模板（仅打卡管理员） */
export function downloadHolidayTemplate(params) {
  // params: { year, current_user }
  return request({
    url: '/holiday/template',
    method: 'get',
    params,
    responseType: 'blob'
  })
}

/** 上传假期调休 Excel 文件（仅打卡管理员） */
export function uploadHolidayFile({ year, current_user, file }) {
  const fd = new FormData()
  fd.append('file', file)
  return request({
    url: '/holiday/upload',
    method: 'post',
    params: { year, current_user },
    data: fd,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 获取加班配置（zhibanfei：每小时加班费，用于“否”换休票时计算加班费）
 */
export function getOvertimeWebconfig() {
  return request({ url: '/overtime/webconfig', method: 'get' })
}

/**
 * 提交加班登记
 * @param {Object} data - 加班登记数据 { department, name, gender, level, registerMethod, needExchangeTicket, date, startTime, endTime, content, approver }
 */
export function submitOvertimeRegister(data) {
  return request({
    url: '/overtime/register',
    method: 'post',
    data
  })
}

/**
 * 提交请假申请（支持可选文件上传）
 * @param {Object} data - 请假申请数据
 * @param {File} [data.materialFile] - 可选，说明材料文件
 */
export function submitLeaveApplication(data) {
  const hasFile = data.materialFile && data.materialFile instanceof File
  const fd = new FormData()
  const keys = ['department', 'name', 'type', 'shift', 'contactMethod', 'startTime', 'endTime', 'duration', 'exchangeTicketNo', 'reason', 'material', 'approver1', 'needSecondApproval', 'approver2']
  keys.forEach(k => fd.append(k, data[k] ?? ''))
  if (hasFile) fd.append('materialFile', data.materialFile)
  return request({
    url: '/leave/apply',
    method: 'post',
    data: fd
  })
}

/** 获取请假说明材料文件下载地址 */
export function getLeaveMaterialDownloadUrl(filename) {
  return `/api/leave/download-material/${encodeURIComponent(filename)}`
}

/**
 * 获取本人请假记录列表
 * @param {Object} params - { name, year?, month? }
 */
export function getLeaveList(params) {
  return request({
    url: '/leave/list',
    method: 'get',
    params
  })
}

/**
 * 获取本人加班记录列表
 * @param {Object} params - { name, year?, month? }
 */
export function getOvertimeList(params) {
  return request({
    url: '/overtime/list',
    method: 'get',
    params
  })
}

/** 删除本人已驳回的请假记录 */
export function deleteLeaveRecord(id, params) {
  return request({ url: `/leave/${id}`, method: 'delete', params })
}

/** 删除本人已驳回的加班记录 */
export function deleteOvertimeRecord(id, params) {
  return request({ url: `/overtime/${id}`, method: 'delete', params })
}

/**
 * 获取审批人列表（按 yggl 表 jb/lsys 审批规则）
 * @param {Object} params - { name, level: 'first'|'second' }
 */
export function getApprovers(params) {
  return request({
    url: '/approvers',
    method: 'get',
    params
  })
}

/**
 * 公出登记
 * @param {Object} data - 公出登记表单数据
 */
export function submitBusinessTripApply(data) {
  return request({
    url: '/business-trip/apply',
    method: 'post',
    data
  })
}

/**
 * 获取本人公出记录列表
 * @param {Object} params - { name, year?, month? }
 */
export function getBusinessTripList(params) {
  return request({
    url: '/business-trip/list',
    method: 'get',
    params
  })
}

/** 删除本人已驳回的公出记录 */
export function deleteBusinessTripRecord(id, params) {
  return request({ url: `/business-trip/${id}`, method: 'delete', params })
}

/** 公出返回登记：填写实际出发时间和实际返回时间 */
export function updateBusinessTripReturnTime(id, data) {
  return request({
    url: `/business-trip/${id}/return-time`,
    method: 'post',
    data
  })
}

// ==================== 审批 API ====================

/** 检查是否有审批权限（员工无权限） */
export function checkCanApprove(params) {
  return request({ url: '/approval/can-approve', method: 'get', params })
}

/** 待审批请假列表 */
export function getPendingLeave(params) {
  return request({ url: '/approval/pending/leave', method: 'get', params })
}

/** 待审批加班列表 */
export function getPendingOvertime(params) {
  return request({ url: '/approval/pending/overtime', method: 'get', params })
}

/** 请假详情 */
export function getLeaveDetail(id) {
  return request({ url: `/approval/leave/${id}`, method: 'get' })
}

/** 加班详情 */
export function getOvertimeDetail(id) {
  return request({ url: `/approval/overtime/${id}`, method: 'get' })
}

/** 请假审批（通过/驳回） */
export function leaveApproveAction(id, data) {
  return request({ url: `/approval/leave/${id}/action`, method: 'post', data })
}

/** 加班审批（通过/驳回） */
export function overtimeApproveAction(id, data) {
  return request({ url: `/approval/overtime/${id}/action`, method: 'post', data })
}

/** 请假批量审批 */
export function leaveBatchApprove(data) {
  return request({ url: '/approval/leave/batch', method: 'post', data })
}

/** 加班批量审批 */
export function overtimeBatchApprove(data) {
  return request({ url: '/approval/overtime/batch', method: 'post', data })
}

/** 加班审批智能校验：列表内重复 + 打卡包含 + jiaban 重叠 */
export function validateOvertimeApproval(data) {
  return request({ url: '/approval/overtime/validate', method: 'post', data })
}

/** 待审批公出列表 */
export function getPendingBusinessTrip(params) {
  return request({ url: '/approval/pending/business-trip', method: 'get', params })
}

/** 公出详情 */
export function getBusinessTripApprovalDetail(id) {
  return request({ url: `/approval/business-trip/${id}`, method: 'get' })
}

/** 公出审批 */
export function businessTripApproveAction(id, data) {
  return request({ url: `/approval/business-trip/${id}/action`, method: 'post', data })
}

/** 公出批量审批 */
export function businessTripBatchApprove(data) {
  return request({ url: '/approval/business-trip/batch', method: 'post', data })
}

// ==================== 科室统计 API ====================

/** 本科室请假统计 */
export function getDeptLeaveStats(params) {
  return request({ url: '/dept/leave', method: 'get', params })
}

/** 本科室加班统计 */
export function getDeptOvertimeStats(params) {
  return request({ url: '/dept/overtime', method: 'get', params })
}

/** 本科室公出统计 */
export function getDeptBusinessTripStats(params) {
  return request({ url: '/dept/business-trip', method: 'get', params })
}

/** 本科室加班费按月份统计（审核通过且换休票为否，jbf*zhibanfei） */
export function getDeptOvertimePayByMonth(params) {
  return request({ url: '/dept/overtime-pay-by-month', method: 'get', params })
}

/** 本科室加班费按员工统计（审核通过且换休票为否，jbf*zhibanfei） */
export function getDeptOvertimePayByEmployee(params) {
  return request({ url: '/dept/overtime-pay-by-employee', method: 'get', params })
}

/** 加班费按月导出（全员+各科室，用于 Excel 工资报表） */
export function getOvertimePayExport(params) {
  return request({ url: '/dept/overtime-pay-export', method: 'get', params })
}

/** 全部科室列表（领导人看板部长/副部长下拉用） */
export function getDeptLsysList() {
  return request({ url: '/dept/lsys-list', method: 'get' })
}

/** 领导人看板：满勤率（指定月全员或科室） */
export function getLeaderFullAttendance(params) {
  return request({ url: '/leader/full-attendance', method: 'get', params })
}

/** 领导人看板：满勤率（全年全员或科室） */
export function getLeaderFullAttendanceYear(params) {
  return request({ url: '/leader/full-attendance-year', method: 'get', params })
}

/** 领导人看板：按月考勤满勤人数（横轴月，纵轴满勤人数，可筛科室） */
export function getLeaderFullAttendanceByMonth(params) {
  return request({ url: '/leader/full-attendance-by-month', method: 'get', params })
}

/** 领导人看板：科室横向对比（加班/请假/公出总数及人均） */
export function getLeaderDeptComparison(params) {
  return request({ url: '/leader/dept-comparison', method: 'get', params })
}

/** 领导人看板：全体员工排序（加班/请假/公出） */
export function getLeaderRankings(params) {
  return request({ url: '/leader/rankings', method: 'get', params })
}

/** 统计汇总权限（1=仅自己 2=科室下拉 3=全部搜索） */
export function getStatisticsPermission(params) {
  return request({ url: '/report/statistics-permission', method: 'get', params })
}

/** 加班费统计页权限：仅部长/副部长或人事管理员(webconfig.admin2)可访问 */
export function getOvertimePayPermission(params) {
  return request({ url: '/report/overtime-pay-permission', method: 'get', params })
}

/** 统计汇总可选员工（2级传lsys 3级传q搜索） */
export function getStatisticsEmployees(params) {
  return request({ url: '/report/statistics-employees', method: 'get', params })
}

// ==================== 管理员：员工在职/离职管理（仅部长/副部长） ====================

/** 管理员：员工列表（含在职状态） */
export function getAdminEmployees(params) {
  return request({ url: '/admin/employees', method: 'get', params })
}

/** 管理员：设置员工在职状态（0=在职 1=离职） */
export function setEmployeeStatus(data) {
  return request({ url: '/admin/employee-status', method: 'post', data })
}

/** 更新员工科室/级别（升职降级、部门调动） */
export function updateEmployeeDeptLevel(data) {
  return request({ url: '/admin/employee-update-dept-level', method: 'post', data })
}

/** 管理员：添丁（向 yggl 主表新增员工） */
export function addEmployee(data) {
  return request({ url: '/admin/employee', method: 'post', data })
}

/** 管理员：科室列表（用于筛选） */
export function getAdminDeptList(params) {
  return request({ url: '/admin/dept-list', method: 'get', params })
}

/** 管理员：导出全体在职员工表（按科室）Excel，返回 Blob */
export function exportEmployeesExcel(params) {
  return request({
    url: '/admin/export-employees',
    method: 'get',
    params,
    responseType: 'blob'
  })
}

/**
 * 获取打卡数据上传配置（webconfig.dakaman，仅该用户可上传）
 */
export function getUploadConfig() {
  return request({
    url: '/attendance/upload/config',
    method: 'get'
  })
}

/**
 * 上传考勤数据 Excel 文件（仅 dakaman 用户可上传，需传 uploader 为当前登录姓名）
 * @param {File} file - Excel 文件对象
 * @param {string} uploader - 当前登录用户姓名，后端校验与 webconfig.dakaman 一致
 */
export function uploadAttendanceExcel(file, uploader = '') {
  const formData = new FormData()
  formData.append('file', file)
  if (uploader) formData.append('uploader', uploader)

  return request({
    url: '/attendance/upload',
    method: 'post',
    data: formData,
    timeout: 120000,  // 文件上传超时设为 120 秒（Excel 处理可能较慢）
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 查询考勤记录（新接口）
 * @param {Object} params - 查询参数
 */
export function queryAttendance(params) {
  return request({
    url: '/attendance/query',
    method: 'get',
    params
  })
}

/**
 * 获取打卡日期列表
 * @param {Object} params - 查询参数
 */
export function getAttendanceDates(params) {
  return request({
    url: '/attendance/dates',
    method: 'get',
    params
  })
}

/**
 * 考勤异常列表（打卡管理员或班组长/主任/副主任）
 * @param {Object} params - { year, month, current_user }
 */
export function getAttendanceExceptions(params) {
  return request({
    url: '/attendance/exceptions',
    method: 'get',
    params
  })
}

/**
 * 导出考勤异常列表为 Excel（打卡管理员或班组长/主任/副主任）
 * @param {Object} params - { year, month, current_user }
 */
export function exportAttendanceExceptions(params) {
  return request({
    url: '/attendance/exceptions/export',
    method: 'get',
    params,
    responseType: 'blob'
  })
}

// ==================== 加班/请假统计 API ====================

/**
 * 获取员工加班记录
 * @param {Object} params - 查询参数 { name, year?, month? }
 */
export function getOvertimeRecords(params) {
  return request({
    url: '/report/overtime',
    method: 'get',
    params
  })
}

/**
 * 获取员工请假记录
 * @param {Object} params - 查询参数 { name, year?, month? }
 */
export function getLeaveRecords(params) {
  return request({
    url: '/report/leave',
    method: 'get',
    params
  })
}

/**
 * 获取员工月度统计汇总
 * @param {Object} params - 查询参数 { name, year? }
 */
export function getMonthlySummary(params) {
  return request({
    url: '/report/monthly-summary',
    method: 'get',
    params
  })
}

/**
 * 获取员工公出记录
 * @param {Object} params - 查询参数 { name, year?, month? }
 */
export function getBusinessTripRecords(params) {
  return request({
    url: '/report/business-trip',
    method: 'get',
    params
  })
}

/**
 * 获取所有请假类型
 */
export function getLeaveTypes() {
  return request({
    url: '/report/leave-types',
    method: 'get'
  })
}

/**
 * 获取所有加班类型
 */
export function getOvertimeTypes() {
  return request({
    url: '/report/overtime-types',
    method: 'get'
  })
}




