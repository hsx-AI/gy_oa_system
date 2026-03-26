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
} from '@/api/attendance'
import { getSSOLink, getSixianghuibaoTodos, getPersonnelPendingCount } from '@/api/sso'

function readUserName() {
  try {
    const s = localStorage.getItem('userInfo')
    const u = s ? JSON.parse(s) : {}
    return (u.name || u.userName || '').trim()
  } catch {
    return ''
  }
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
const personnelMyPending = ref(0)
const personnelNeedAudit = ref(0)
const todoRealTotal = ref(0)

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
    list.push({
      uniqueId: 'sixianghuibao-todos',
      type: '思想汇报待审核',
      description: `您有 ${sixianghuibaoTodoTotal.value} 篇思想汇报待审核`,
      applicant: '思想汇报系统',
      time: '',
      isSixianghuibao: true,
    })
  }
  if (personnelMyPending.value > 0) {
    list.push({
      uniqueId: 'personnel-my-pending',
      type: '人事档案待审批',
      description: `您有 ${personnelMyPending.value} 条人事档案待处理`,
      applicant: '人事档案系统',
      time: '',
      isPersonnel: true,
    })
  }
  if (personnelNeedAudit.value > 0) {
    list.push({
      uniqueId: 'personnel-need-audit',
      type: '人事档案需审核',
      description: `您有 ${personnelNeedAudit.value} 条人事档案需您审核`,
      applicant: '人事档案系统',
      time: '',
      isPersonnel: true,
    })
  }
  return list
})

const totalBadgeCount = computed(() => {
  let count = todoRealTotal.value
  if (tripReturnPendingCount.value > 0) count += 1
  if (sixianghuibaoTodoTotal.value > 0) count += 1
  if (personnelMyPending.value > 0) count += 1
  if (personnelNeedAudit.value > 0) count += 1
  return count
})

const todoPanelLoading = computed(() => todoLoading.value || tripReturnLoading.value)

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
        tabType: 'holiday-exchange',
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
  } catch {
    sixianghuibaoTodoTotal.value = 0
  }
}

async function fetchPersonnelPending() {
  const name = readUserName()
  if (!name) return
  try {
    const res = await getPersonnelPendingCount({ name })
    personnelMyPending.value = Math.max(0, Number(res?.myPendingCount) || 0)
    personnelNeedAudit.value = Math.max(0, Number(res?.needAuditCount) || 0)
  } catch {
    personnelMyPending.value = 0
    personnelNeedAudit.value = 0
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

export async function refreshWorkplaceTodos() {
  await Promise.all([
    fetchTodoList(),
    fetchTripReturnPending(),
    fetchSixianghuibaoTodos(),
    fetchPersonnelPending(),
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

  function handleTodoAction(task) {
    if (task.isPersonnel) {
      goPersonnelArchiveLazy()
      return
    }
    if (task.isSixianghuibao) {
      goSixianghuibao()
      return
    }
    if (task.isReturnReminder) {
      router.push('/attendance/business-trip')
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
    personnelMyPending,
    personnelNeedAudit,
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
