/**
 * 首页与顶栏铃铛共用的待办数据（模块级单例状态）
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  checkCanApprove,
  getPendingLeave,
  getPendingOvertime,
  getPendingBusinessTrip,
  getPendingHolidayExchange,
  getBusinessTripList,
  getUploadConfig,
  getUnreadHxp,
  markHxpRead,
} from '@/api/attendance'
import { getPendingHxpApprovals } from '@/api/admin'
import { getSSOLink, getSixianghuibaoTodos, getPersonnelPendingCount } from '@/api/sso'
import { getLeaderInbox, getWallPending, getWallAssigned, getSystemList } from '@/api/feedback'
import { getPendingSeal, getPendingSealUse, markSealUsed } from '@/api/seal'
import { getPendingLowValueReimbursements } from '@/api/lowValueReimbursement'
import { getShiftCoverageGap } from '@/api/shift'
import { getAutoReminderNotices, markAutoReminderNoticeRead } from '@/api/email'
import { getActions, getMyActionReminders, readActionReminder } from '@/api/actionItems'
import {
  getPendingKqyc,
  getKqycDakamanPending,
  confirmKqycByDakaman,
} from '@/api/attendanceException'
import { formatHxpAmount } from '@/utils/formatHxp'

function readUserName() {
  try {
    const s = localStorage.getItem('userInfo')
    const u = s ? JSON.parse(s) : {}
    return (u.name || u.userName || '').trim()
  } catch {
    return ''
  }
}

function readUserJb() {
  try {
    const s = localStorage.getItem('userInfo')
    const u = s ? JSON.parse(s) : {}
    return (u.jb || '').trim()
  } catch {
    return ''
  }
}

function isWallReviewer(userName, admin1) {
  if (admin1 && userName === admin1.trim()) return true
  const jb = readUserJb()
  return jb === '经理' || jb === '部长'
}

function formatRelativeTime(dtStr) {
  if (!dtStr) return ''
  const d = new Date(dtStr.replace(/-/g, '/'))
  const now = Date.now()
  const diff = now - d.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
  if (diff < 604800000) return Math.floor(diff / 86400000) + '天前'
  return dtStr.slice(0, 10)
}

const todoList = ref([])
const todoLoading = ref(false)
const tripReturnPendingCount = ref(0)
const tripReturnLoading = ref(false)
const sixianghuibaoTodoTotal = ref(0)
const sixianghuibaoHint = ref('')
const sixianghuibaoRole = ref('')
/** 人事档案系统 GET pending-count 返回的 data.needAuditCount（仅展示此项，不展示 myPendingCount） */
const personnelNeedAudit = ref(0)
const hxpUnreadList = ref([])
const hxpApprovalPendingList = ref([])
const todoRealTotal = ref(0)
const sealPendingList = ref([])
const sealUsePendingList = ref([])
const lowValuePendingList = ref([])
const feedbackLeaderCount = ref(0)
const feedbackWallPendingCount = ref(0)
const feedbackSystemPendingCount = ref(0)
const feedbackWallAssignedList = ref([])
const shiftCoverageGap = ref(null)
const shiftCoverageLoading = ref(false)
/** 打卡异常待审批列表（自动区分一/二级，仅显示当前节点为本人的） */
const kqycPendingList = ref([])
/** dakaman 待"已读确认"列表（仅 dakaman 可见有数据） */
const kqycDakamanList = ref([])
const autoReminderNoticeList = ref([])
/** 行动项督办未读提醒 */
const actionReminderList = ref([])

const displayTodoList = computed(() => {
  const list = [...(todoList.value || [])]
  if (tripReturnPendingCount.value > 0) {
    list.push({
      uniqueId: 'trip-return-reminder',
      type: '公出返回登记',
      description: `您有 ${tripReturnPendingCount.value} 条公出已通过尚未做返回登记，请及时登记`,
      applicant: '本人',
      time: '',
      isReturnReminder: true,
    })
  }
  if (sixianghuibaoTodoTotal.value > 0) {
    const hint = sixianghuibaoHint.value
    const role = sixianghuibaoRole.value
    const isZzs = role === 'zzs'
    const typeLabel = isZzs ? '思想汇报待审阅' : '思想汇报待处理'
    const desc = hint || `您有 ${sixianghuibaoTodoTotal.value} 篇思想汇报待处理`
    list.push({
      uniqueId: 'sixianghuibao-todos',
      type: typeLabel,
      description: desc,
      applicant: '思想汇报系统',
      time: '',
      isSixianghuibao: true,
      btnLabel: isZzs ? '去审阅' : '去处理',
    })
  }
  if (personnelNeedAudit.value > 0) {
    list.push({
      uniqueId: 'personnel-need-audit',
      type: '人事档案待审核',
      description: `您有 ${personnelNeedAudit.value} 条人事档案待您审核`,
      applicant: '人事档案系统',
      time: '',
      isPersonnel: true,
    })
  }
  if (shiftCoverageGap.value?.hasPending) {
    const gap = shiftCoverageGap.value
    const dept = gap.department || '本科室'
    const range = gap.startDate && gap.endDate ? `${gap.startDate}至${gap.endDate}` : '本周六至下周五'
    const summary = gap.summary ? `：${gap.summary}` : ''
    list.push({
      uniqueId: 'shift-coverage-gap',
      type: '日常排班人数不足',
      description: `${dept}${range}有 ${gap.totalIssues || 0} 天未满足排班人数配置${summary}`,
      applicant: '排班管理',
      time: '',
      isShiftCoverageGap: true,
      btnLabel: '去排班',
    })
  }
  for (const hxp of hxpUnreadList.value) {
    list.push({
      uniqueId: `hxp-${hxp.id}`,
      type: '换休票入账',
      description: `您获得 ${formatHxpAmount(hxp.sl)} 张换休票（来源：${hxp.ly}）`,
      applicant: '本人',
      time: formatRelativeTime(hxp.sj),
      isHxpNotice: true,
      hxpId: hxp.id,
    })
  }
  for (const item of hxpApprovalPendingList.value) {
    list.push({
      uniqueId: `hxp-approval-${item.id}`,
      tabType: 'hxp',
      type: '换休票管理审批',
      description: `${item.applicant}申请为${item.namesCount}人${item.action === 'add' ? '增加' : '减少'}${item.amount}张换休票`,
      applicant: item.applicant,
      time: formatRelativeTime(item.applyTime),
      isHxpApproval: true,
    })
  }
  for (const item of sealPendingList.value) {
    list.push({
      uniqueId: `seal-${item.id}`,
      type: '用印审批',
      description: `${item.applicant}的用印申请（${item.seal_type || '用印'}）`,
      applicant: item.applicant,
      time: formatRelativeTime(item.apply_time),
      applyTime: item.apply_time || '',
      isSealApproval: true,
    })
  }
  for (const item of sealUsePendingList.value) {
    list.push({
      uniqueId: `seal-use-${item.id}`,
      type: '待用印',
      description: `您的用印申请已通过，请完成盖章后点击「已用印」（${item.seal_type || '部门公章'}）`,
      applicant: '本人',
      time: formatRelativeTime(item.approve_time || item.apply_time),
      applyTime: item.approve_time || item.apply_time || '',
      isSealUsePending: true,
      sealUseId: item.id,
    })
  }
  for (const item of lowValuePendingList.value) {
    list.push({
      uniqueId: `low-value-${item.id}`,
      type: '低值易耗报销审批',
      description: `${item.applicant}提交的${item.material_name || '低值易耗'}报销单，金额${formatHxpAmount(item.total_price || 0)}元`,
      applicant: item.applicant,
      time: formatRelativeTime(item.apply_time),
      applyTime: item.apply_time || '',
      isLowValueApproval: true,
      btnLabel: Number(item.status) === 2 ? '完成报销' : '去审批',
    })
  }
  if (feedbackLeaderCount.value > 0) {
    list.push({
      uniqueId: 'feedback-leader-inbox',
      type: '匿名意见待查看',
      description: `您有 ${feedbackLeaderCount.value} 条匿名意见待查看`,
      applicant: '意见与建议',
      time: '',
      isFeedback: true,
      feedbackTab: 'leader',
      btnLabel: '去查看',
    })
  }
  if (feedbackWallPendingCount.value > 0) {
    list.push({
      uniqueId: 'feedback-wall-pending',
      type: '吐槽墙待审核',
      description: `您有 ${feedbackWallPendingCount.value} 条吐槽待审核上墙`,
      applicant: '意见与建议',
      time: '',
      isFeedback: true,
      feedbackTab: 'wall',
      btnLabel: '去审核',
    })
  }
  for (const item of feedbackWallAssignedList.value) {
    const content = (item.content || '').replace(/\s+/g, ' ')
    list.push({
      uniqueId: `feedback-wall-assigned-${item.id}`,
      type: '吐槽问题处理',
      description: content.length > 34 ? `请处理：${content.slice(0, 34)}…` : `请处理：${content}`,
      applicant: item.assignedBy ? `指派人：${item.assignedBy}` : '吐槽墙',
      time: formatRelativeTime(item.assignedAt || item.createdAt),
      applyTime: item.assignedAt || item.createdAt || '',
      isFeedback: true,
      feedbackTab: 'wall',
      feedbackWallId: item.id,
      btnLabel: '去处理',
    })
  }
  if (feedbackSystemPendingCount.value > 0) {
    list.push({
      uniqueId: 'feedback-system-pending',
      type: '系统建议待回复',
      description: `您有 ${feedbackSystemPendingCount.value} 条系统功能建议待回复`,
      applicant: '意见与建议',
      time: '',
      isFeedback: true,
      feedbackTab: 'system',
      btnLabel: '去回复',
    })
  }
  for (const item of kqycPendingList.value) {
    const isSecond = item.pending_for === 'second'
    list.push({
      uniqueId: `kqyc-${item.id}`,
      type: isSecond ? '打卡异常二级审批' : '打卡异常一级审批',
      description: `${item.applicant}的 ${item.attendance_date} ${item.time_from}~${item.time_to} 打卡异常申请（${item.reason_type || '—'}）`,
      applicant: item.applicant,
      time: formatRelativeTime(item.apply_time),
      applyTime: item.apply_time || '',
      isKqycApproval: true,
      btnLabel: '去审批',
    })
  }
  for (const item of kqycDakamanList.value) {
    list.push({
      uniqueId: `kqyc-dakaman-${item.id}`,
      type: '打卡异常处理已读确认',
      description: `经 ${item.second_approver} 审批已将 ${item.applicant} 的 ${item.attendance_date} ${item.time_from}~${item.time_to} 异常处理为市内公出`,
      applicant: '本人',
      time: formatRelativeTime(item.second_approve_time),
      applyTime: item.second_approve_time || '',
      isKqycDakamanConfirm: true,
      kqycDakamanId: item.id,
      btnLabel: '已读确认',
    })
  }
  for (const item of autoReminderNoticeList.value) {
    list.push({
      uniqueId: `auto-reminder-notice-${item.id}`,
      type: item.title || '考勤异常邮件提醒发送结果',
      description: item.description || '',
      applicant: '邮件自动发送',
      time: formatRelativeTime(item.createdAt || item.sourceTime),
      applyTime: item.createdAt || item.sourceTime || '',
      isAutoReminderNotice: true,
      autoReminderNoticeId: item.id,
      btnLabel: '已阅',
    })
  }
  for (const item of actionReminderList.value) {
    list.push({
      uniqueId: `action-reminder-${item.id}`,
      type: `行动项${item.reminder_type || '提醒'}`,
      description: item.reminder_note || item.title || item.action_title || '您有一条行动项待处理',
      applicant: '行动项督办',
      time: formatRelativeTime(item.reminder_time),
      applyTime: item.reminder_time || '',
      isActionReminder: true,
      actionReminderId: item.is_pending_action ? null : item.id,
      actionItemId: item.action_item_id,
      btnLabel: item.is_pending_action ? '查看并接收' : '去处理',
    })
  }
  return list
})

const totalBadgeCount = computed(() => {
  let count = todoRealTotal.value
  if (tripReturnPendingCount.value > 0) count += 1
  if (sixianghuibaoTodoTotal.value > 0) count += 1
  count += Math.max(0, Number(personnelNeedAudit.value) || 0)
  if (shiftCoverageGap.value?.hasPending) count += 1
  count += hxpUnreadList.value.length
  count += hxpApprovalPendingList.value.length
  count += sealPendingList.value.length
  count += sealUsePendingList.value.length
  count += lowValuePendingList.value.length
  if (feedbackLeaderCount.value > 0) count += 1
  if (feedbackWallPendingCount.value > 0) count += 1
  count += feedbackWallAssignedList.value.length
  if (feedbackSystemPendingCount.value > 0) count += 1
  count += kqycPendingList.value.length
  count += kqycDakamanList.value.length
  count += autoReminderNoticeList.value.length
  count += actionReminderList.value.length
  return count
})

const todoPanelLoading = computed(() => todoLoading.value || tripReturnLoading.value || shiftCoverageLoading.value)

async function fetchTodoList() {
  const userName = readUserName()
  if (!userName) {
    todoList.value = []
    todoRealTotal.value = 0
    return
  }
  todoLoading.value = true
  try {
    const res = await checkCanApprove({ name: userName })
    if (!res.canApprove) {
      todoList.value = []
      todoRealTotal.value = 0
      return
    }
    const [leaveRes, overtimeRes, btRes, heRes] = await Promise.all([
      getPendingLeave({ approver: userName }),
      getPendingOvertime({ approver: userName }),
      getPendingBusinessTrip({ approver: userName }),
      getPendingHolidayExchange({ approver: userName }),
    ])
    const items = []
    const leaves = leaveRes.data || []
    leaves.forEach((r) => {
      items.push({
        uniqueId: `leave-${r.id}`,
        tabType: 'leave',
        type: '请假审批',
        description: `${r.applicant}的${r.type || '请假'}申请`,
        applicant: r.applicant,
        time: formatRelativeTime(r.applyTime),
        applyTime: r.applyTime || '',
      })
    })
    const overtimes = overtimeRes.data || []
    overtimes.forEach((r) => {
      items.push({
        uniqueId: `overtime-${r.id}`,
        tabType: 'overtime',
        type: '加班审批',
        description: `${r.applicant}的${r.date || ''}加班申请`,
        applicant: r.applicant,
        time: formatRelativeTime(r.applyTime),
        applyTime: r.applyTime || '',
      })
    })
    const trips = btRes.data || []
    trips.forEach((r) => {
      const loc = r.location ? `去${r.location}的` : ''
      items.push({
        uniqueId: `bt-${r.id}`,
        tabType: 'business-trip',
        type: '公出审批',
        description: `${r.applicant}${loc}公出申请`,
        applicant: r.applicant,
        time: formatRelativeTime(r.applyTime),
        applyTime: r.applyTime || '',
      })
    })
    const heList = heRes.data || []
    heList.forEach((r) => {
      items.push({
        uniqueId: `he-${r.id}`,
        tabType: 'hxp',
        type: '节假日换休票',
        description: `${r.applicant}的公出节假日换休票（${r.dateFrom || ''}至${r.dateTo || ''}，${r.days ?? ''}天）`,
        applicant: r.applicant,
        time: formatRelativeTime(r.applyTime),
        applyTime: r.applyTime || '',
      })
    })
    items.sort((a, b) => (b.applyTime || '').localeCompare(a.applyTime || ''))
    todoRealTotal.value = items.length
    todoList.value = items.slice(0, 10)
  } catch {
    todoList.value = []
    todoRealTotal.value = 0
  } finally {
    todoLoading.value = false
  }
}

async function fetchSixianghuibaoTodos() {
  const name = readUserName()
  if (!name) return
  try {
    const res = await getSixianghuibaoTodos({ name })
    sixianghuibaoTodoTotal.value = Math.max(0, Number(res?.total) || 0)
    sixianghuibaoHint.value = res?.hint || ''
    sixianghuibaoRole.value = res?.role || ''
  } catch {
    sixianghuibaoTodoTotal.value = 0
    sixianghuibaoHint.value = ''
    sixianghuibaoRole.value = ''
  }
}

async function fetchPersonnelPending() {
  const name = readUserName()
  if (!name) return
  try {
    const res = await getPersonnelPendingCount({ name })
    personnelNeedAudit.value = Math.max(0, Number(res?.needAuditCount) || 0)
  } catch {
    personnelNeedAudit.value = 0
  }
}

async function fetchShiftCoverageGap() {
  const name = readUserName()
  if (!name) {
    shiftCoverageGap.value = null
    return
  }
  shiftCoverageLoading.value = true
  try {
    const res = await getShiftCoverageGap({ current_user: name })
    shiftCoverageGap.value = res?.hasPending ? res : null
  } catch {
    shiftCoverageGap.value = null
  } finally {
    shiftCoverageLoading.value = false
  }
}

async function fetchUnreadHxp() {
  const name = readUserName()
  if (!name) {
    hxpUnreadList.value = []
    return
  }
  try {
    const res = await getUnreadHxp({ name })
    hxpUnreadList.value = res?.data || []
  } catch {
    hxpUnreadList.value = []
  }
}

async function fetchHxpApprovalPending() {
  const name = readUserName()
  if (!name) {
    hxpApprovalPendingList.value = []
    return
  }
  try {
    const res = await getPendingHxpApprovals({ approver: name })
    hxpApprovalPendingList.value = res?.data || []
  } catch {
    hxpApprovalPendingList.value = []
  }
}

async function fetchTripReturnPending() {
  const userName = readUserName()
  if (!userName) {
    tripReturnPendingCount.value = 0
    return
  }
  tripReturnLoading.value = true
  try {
    const res = await getBusinessTripList({ name: userName, year: new Date().getFullYear() })
    const data = res?.data || []
    tripReturnPendingCount.value = data.filter(
      (r) => r.status === '已通过' && Number(r.fhdjStatus) !== 1
    ).length
  } catch {
    tripReturnPendingCount.value = 0
  } finally {
    tripReturnLoading.value = false
  }
}

async function fetchKqycPending() {
  const name = readUserName()
  if (!name) {
    kqycPendingList.value = []
    return
  }
  try {
    const res = await getPendingKqyc({ approver: name })
    kqycPendingList.value = res?.data || []
  } catch {
    kqycPendingList.value = []
  }
}

async function fetchKqycDakaman() {
  const name = readUserName()
  if (!name) {
    kqycDakamanList.value = []
    return
  }
  try {
    const res = await getKqycDakamanPending({ name })
    kqycDakamanList.value = res?.data || []
  } catch {
    kqycDakamanList.value = []
  }
}

async function fetchAutoReminderNotices() {
  const name = readUserName()
  if (!name) {
    autoReminderNoticeList.value = []
    return
  }
  try {
    const res = await getAutoReminderNotices({ name })
    autoReminderNoticeList.value = res?.data || []
  } catch {
    autoReminderNoticeList.value = []
  }
}

async function fetchActionReminders() {
  const name = readUserName()
  if (!name) {
    actionReminderList.value = []
    return
  }
  try {
    const [reminderResult, pendingResult] = await Promise.allSettled([
      getMyActionReminders({
        current_user: name,
        unread_only: true,
        limit: 200,
      }),
      getActions({
        current_user: name,
        mine: true,
        status: '待接收',
        page: 1,
        page_size: 200,
      }),
    ])
    const reminders = reminderResult.status === 'fulfilled'
      ? (reminderResult.value?.items || reminderResult.value?.data || [])
      : []
    const pendingActions = pendingResult.status === 'fulfilled'
      ? (pendingResult.value?.items || [])
      : []
    const representedActionIds = new Set(
      reminders.map(item => Number(item.action_item_id)).filter(Boolean),
    )
    const missingPending = pendingActions
      .filter(item => !representedActionIds.has(Number(item.id)))
      .map(item => ({
        id: `pending-${item.id}`,
        action_item_id: item.id,
        title: item.title,
        reminder_type: '待接收',
        reminder_note: '您有一条行动项尚未接收，请选择由本人接收或分配科室成员完成',
        reminder_time: item.published_at || item.updated_at || item.created_at || '',
        is_pending_action: true,
      }))
    actionReminderList.value = [...reminders, ...missingPending]
  } catch {
    actionReminderList.value = []
  }
}

async function fetchSealPending() {
  const name = readUserName()
  if (!name) {
    sealPendingList.value = []
    return
  }
  try {
    const res = await getPendingSeal({ approver: name })
    sealPendingList.value = res?.data || []
  } catch {
    sealPendingList.value = []
  }
}

async function fetchSealUsePending() {
  const name = readUserName()
  if (!name) {
    sealUsePendingList.value = []
    return
  }
  try {
    const res = await getPendingSealUse({ applicant: name })
    sealUsePendingList.value = res?.data || []
  } catch {
    sealUsePendingList.value = []
  }
}

async function fetchLowValuePending() {
  const name = readUserName()
  if (!name) {
    lowValuePendingList.value = []
    return
  }
  try {
    const res = await getPendingLowValueReimbursements({ approver: name })
    lowValuePendingList.value = res?.data || []
  } catch {
    lowValuePendingList.value = []
  }
}

async function fetchFeedbackTodos() {
  const userName = readUserName()
  if (!userName) {
    feedbackLeaderCount.value = 0
    feedbackWallPendingCount.value = 0
    feedbackSystemPendingCount.value = 0
    feedbackWallAssignedList.value = []
    return
  }
  let isAdmin = false
  let admin1 = ''
  try {
    const cfg = await getUploadConfig()
    admin1 = (cfg?.admin1 || '').trim()
    isAdmin = !!(admin1 && userName === admin1)
  } catch { /* ignore */ }
  const canReviewWall = isWallReviewer(userName, admin1)

  const tasks = []

  tasks.push(
    getWallAssigned({ current_user: userName })
      .then(res => { feedbackWallAssignedList.value = res?.data || [] })
      .catch(() => { feedbackWallAssignedList.value = [] })
  )

  tasks.push(
    getLeaderInbox({ current_user: userName })
      .then(res => {
        feedbackLeaderCount.value = (res?.data || []).filter(m => Number(m.status) === 0).length
      })
      .catch(() => { feedbackLeaderCount.value = 0 })
  )

  if (canReviewWall) {
    tasks.push(
      getWallPending({ current_user: userName })
        .then(res => { feedbackWallPendingCount.value = (res?.data || []).length })
        .catch(() => { feedbackWallPendingCount.value = 0 })
    )
  } else {
    feedbackWallPendingCount.value = 0
  }

  if (isAdmin) {
    tasks.push(
      getSystemList()
        .then(res => {
          feedbackSystemPendingCount.value = (res?.data || []).filter(s => s.status !== 1).length
        })
        .catch(() => { feedbackSystemPendingCount.value = 0 })
    )
  } else {
    feedbackSystemPendingCount.value = 0
  }

  await Promise.all(tasks)
}

export async function refreshWorkplaceTodos() {
  await Promise.all([
    fetchTodoList(),
    fetchTripReturnPending(),
    fetchSixianghuibaoTodos(),
    fetchPersonnelPending(),
    fetchShiftCoverageGap(),
    fetchUnreadHxp(),
    fetchHxpApprovalPending(),
    fetchSealPending(),
    fetchSealUsePending(),
    fetchLowValuePending(),
    fetchFeedbackTodos(),
    fetchKqycPending(),
    fetchKqycDakaman(),
    fetchAutoReminderNotices(),
    fetchActionReminders(),
  ])
}

async function goPersonnelArchiveLazy() {
  try {
    const res = await getUploadConfig()
    const url =
      res?.personnelArchiveUrl != null ? String(res.personnelArchiveUrl).trim() : ''
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer')
    } else {
      alert('人事档案系统链接未配置，请联系管理员')
    }
  } catch {
    alert('人事档案系统链接未配置，请联系管理员')
  }
}

export function useWorkplaceTodos() {
  const router = useRouter()

  function goApprove(task) {
    router.push({ path: '/attendance/approvals', query: { type: task.tabType } })
  }

  async function goSixianghuibao() {
    const name = readUserName()
    if (!name) return
    try {
      const res = await getSSOLink('sixianghuibao', name)
      if (res?.success && res?.url) window.open(res.url, '_blank', 'noopener,noreferrer')
      else alert(res?.detail || '获取思想汇报系统链接失败')
    } catch (e) {
      alert(e?.message || e?.response?.data?.detail || '获取思想汇报系统链接失败，请稍后重试')
    }
  }

  async function handleHxpRead(task) {
    if (!task.hxpId) return
    try {
      await markHxpRead({ ids: [task.hxpId] })
      hxpUnreadList.value = hxpUnreadList.value.filter((h) => h.id !== task.hxpId)
    } catch {
      // 静默失败
    }
  }

  async function handleTodoAction(task) {
    if (task.isHxpNotice) {
      handleHxpRead(task)
      return
    }
    if (task.isHxpApproval) {
      router.push({ path: '/attendance/approvals', query: { type: 'hxp' } })
      return
    }
    if (task.isPersonnel) {
      goPersonnelArchiveLazy()
      return
    }
    if (task.isSixianghuibao) {
      goSixianghuibao()
      return
    }
    if (task.isShiftCoverageGap) {
      router.push('/attendance/shift-schedule')
      return
    }
    if (task.isReturnReminder) {
      router.push('/attendance/business-trip')
      return
    }
    if (task.isSealUsePending) {
      const name = readUserName()
      if (!name || !task.sealUseId) return
      try {
        await markSealUsed({ id: task.sealUseId, applicant: name })
        await fetchSealUsePending()
      } catch (e) {
        const msg = e?.response?.data?.detail || e?.message || '标记失败'
        alert(typeof msg === 'string' ? msg : '标记失败')
      }
      return
    }
    if (task.isSealApproval) {
      router.push({ path: '/seal/apply', query: { tab: 'pending' } })
      return
    }
    if (task.isLowValueApproval) {
      router.push({ path: '/low-value-reimbursement', query: { tab: 'pending' } })
      return
    }
    if (task.isFeedback) {
      const query = { tab: task.feedbackTab || 'wall' }
      if (task.feedbackWallId) query.wallId = task.feedbackWallId
      router.push({ path: '/feedback', query })
      return
    }
    if (task.isKqycApproval) {
      router.push({ path: '/attendance/approvals', query: { type: 'kqyc' } })
      return
    }
    if (task.isKqycDakamanConfirm) {
      const name = readUserName()
      if (!name || !task.kqycDakamanId) return
      try {
        await confirmKqycByDakaman({ id: task.kqycDakamanId, current_user: name })
        await fetchKqycDakaman()
      } catch (e) {
        const msg = e?.response?.data?.detail || e?.message || '已读确认失败'
        alert(typeof msg === 'string' ? msg : '已读确认失败')
      }
      return
    }
    if (task.isAutoReminderNotice) {
      const name = readUserName()
      if (!name || !task.autoReminderNoticeId) return
      try {
        await markAutoReminderNoticeRead({ id: task.autoReminderNoticeId, current_user: name })
        autoReminderNoticeList.value = autoReminderNoticeList.value.filter(
          (item) => item.id !== task.autoReminderNoticeId
        )
      } catch (e) {
        const msg = e?.response?.data?.detail || e?.response?.data?.message || e?.message || '标记已阅失败'
        alert(typeof msg === 'string' ? msg : '标记已阅失败')
      }
      return
    }
    if (task.isActionReminder) {
      const name = readUserName()
      if (!name) return
      if (!task.actionReminderId && task.actionItemId) {
        router.push(`/action-items/${task.actionItemId}`)
        return
      }
      if (!task.actionReminderId) return
      try {
        await readActionReminder(task.actionReminderId, { current_user: name })
        actionReminderList.value = actionReminderList.value.filter(
          (item) => item.id !== task.actionReminderId
        )
        if (task.actionItemId) router.push(`/action-items/${task.actionItemId}`)
      } catch (e) {
        const msg = e?.response?.data?.detail || e?.message || '行动项提醒处理失败'
        alert(typeof msg === 'string' ? msg : '行动项提醒处理失败')
      }
      return
    }
    goApprove(task)
  }

  return {
    todoList,
    todoLoading,
    tripReturnLoading,
    tripReturnPendingCount,
    sixianghuibaoTodoTotal,
    personnelNeedAudit,
    shiftCoverageGap,
    todoRealTotal,
    displayTodoList,
    totalBadgeCount,
    todoPanelLoading,
    refreshWorkplaceTodos,
    handleTodoAction,
    goApprove,
    goSixianghuibao,
  }
}
