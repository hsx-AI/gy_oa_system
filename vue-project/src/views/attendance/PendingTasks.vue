<template>
  <div class="page-container">
    <div class="page-header">
      <h1>全部待办事项</h1>
      <button class="btn btn-outline" @click="router.push('/attendance/approvals')">进入审批</button>
    </div>

    <template v-if="!canApprove && !displayTodoList.length && !loading">
      <div class="no-permission card">
        <p>您暂无审批权限（员工无审批功能）</p>
      </div>
    </template>

    <template v-else>
      <div class="card">
        <div class="card-header">
          <h3>待办列表</h3>
          <span class="count-badge">共 {{ displayTodoList.length }} 项</span>
        </div>
        <div class="card-body">
          <div class="table-wrap" v-if="displayTodoList.length">
            <table class="data-table">
              <thead>
                <tr>
                  <th>类型</th>
                  <th>描述</th>
                  <th>申请人</th>
                  <th>申请时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="task in displayTodoList" :key="task.uniqueId">
                  <td>
                    <span class="type-tag" :class="task.typeClass">{{ task.type }}</span>
                  </td>
                  <td class="desc-cell">{{ task.description }}</td>
                  <td>{{ task.applicant }}</td>
                  <td>{{ task.applyTime }}</td>
                  <td>
                    <button type="button" class="btn btn-primary btn-sm" @click="goApprove(task)">
                      {{ task.isActionReminder ? '查看并接收' : (task.isAutoReminderNotice ? '已阅' : (task.isShiftCoverageGap ? '去排班' : (task.isReturnReminder ? '去登记' : '处理'))) }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="empty-state" v-else-if="!loading">
            <p>暂无待办事项</p>
          </div>
          <div class="empty-state" v-else>
            <p>加载中...</p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  checkCanApprove,
  getPendingLeave,
  getPendingOvertime,
  getPendingBusinessTrip,
  getPendingHolidayExchange,
  getBusinessTripList
} from '@/api/attendance'
import { getShiftCoverageGap } from '@/api/shift'
import { getAutoReminderNotices, markAutoReminderNoticeRead } from '@/api/email'
import { getMyActionReminders, readActionReminder } from '@/api/actionItems'

const router = useRouter()
const canApprove = ref(false)
const todoList = ref([])
const loading = ref(false)
/** 公出已通过但未做返回登记的数量 */
const tripReturnPendingCount = ref(0)
const shiftCoverageGap = ref(null)
const autoReminderNoticeList = ref([])
const actionReminderList = ref([])

const userInfo = (() => {
  try {
    const s = localStorage.getItem('userInfo')
    return s ? JSON.parse(s) : {}
  } catch {
    return {}
  }
})()

const userName = userInfo.name || userInfo.userName || ''

/** 展示的待办 = 审批待办 + 公出返回登记提醒（若有） */
const displayTodoList = computed(() => {
  const list = [...(todoList.value || [])]
  if (shiftCoverageGap.value?.hasPending) {
    const gap = shiftCoverageGap.value
    const dept = gap.department || '本科室'
    const range = gap.startDate && gap.endDate ? `${gap.startDate}至${gap.endDate}` : '本周六至下周五'
    const summary = gap.summary ? `：${gap.summary}` : ''
    list.push({
      uniqueId: 'shift-coverage-gap',
      tabType: 'shift-schedule',
      type: '日常排班人数不足',
      typeClass: 'type-shift',
      description: `${dept}${range}有 ${gap.totalIssues || 0} 天未满足排班人数配置${summary}`,
      applicant: '排班管理',
      applyTime: '',
      isShiftCoverageGap: true
    })
  }
  if (tripReturnPendingCount.value > 0) {
    list.push({
      uniqueId: 'trip-return-reminder',
      tabType: 'business-trip',
      type: '公出返回登记',
      typeClass: 'type-trip',
      description: `您有 ${tripReturnPendingCount.value} 条公出已通过尚未做返回登记，请及时登记`,
      applicant: '本人',
      applyTime: '',
      isReturnReminder: true
    })
  }
  for (const item of autoReminderNoticeList.value) {
    list.push({
      uniqueId: `auto-reminder-notice-${item.id}`,
      type: item.title || '考勤异常邮件提醒发送结果',
      typeClass: 'type-email',
      description: item.description || '',
      applicant: '邮件自动发送',
      applyTime: item.createdAt || item.sourceTime || '',
      isAutoReminderNotice: true,
      autoReminderNoticeId: item.id
    })
  }
  for (const item of actionReminderList.value) {
    list.push({
      uniqueId: `action-reminder-${item.id}`,
      type: `行动项${item.reminder_type || '提醒'}`,
      typeClass: 'type-action',
      description: `${item.title || '行动项'}：${item.reminder_note || '请及时处理'}`,
      applicant: '行动项督办',
      applyTime: item.reminder_time || '',
      isActionReminder: true,
      actionReminderId: item.id,
      actionItemId: item.action_item_id
    })
  }
  return list
})

async function goApprove(task) {
  if (task.isShiftCoverageGap) {
    router.push('/attendance/shift-schedule')
    return
  }
  if (task.isReturnReminder) {
    router.push('/attendance/business-trip')
    return
  }
  if (task.isAutoReminderNotice) {
    if (!userName || !task.autoReminderNoticeId) return
    try {
      await markAutoReminderNoticeRead({ id: task.autoReminderNoticeId, current_user: userName })
      autoReminderNoticeList.value = autoReminderNoticeList.value.filter(
        item => item.id !== task.autoReminderNoticeId
      )
    } catch (e) {
      alert(e?.response?.data?.message || e?.message || '标记已阅失败')
    }
    return
  }
  if (task.isActionReminder) {
    if (!userName || !task.actionReminderId) return
    try {
      await readActionReminder(task.actionReminderId, { current_user: userName })
      actionReminderList.value = actionReminderList.value.filter(
        item => item.id !== task.actionReminderId
      )
      if (task.actionItemId) router.push(`/action-items/${task.actionItemId}`)
    } catch (e) {
      alert(e?.response?.data?.detail || e?.message || '打开行动项消息失败')
    }
    return
  }
  router.push({ path: '/attendance/approvals', query: { type: task.tabType } })
}

async function fetchData() {
  if (!userName) return
  loading.value = true
  try {
    const res = await checkCanApprove({ name: userName })
    canApprove.value = res.canApprove || false
    try {
      const shiftRes = await getShiftCoverageGap({ current_user: userName })
      shiftCoverageGap.value = shiftRes?.hasPending ? shiftRes : null
    } catch {
      shiftCoverageGap.value = null
    }
    try {
      const noticeRes = await getAutoReminderNotices({ name: userName })
      autoReminderNoticeList.value = noticeRes?.data || []
    } catch {
      autoReminderNoticeList.value = []
    }
    try {
      const actionRes = await getMyActionReminders({
        current_user: userName,
        unread_only: true,
        limit: 200
      })
      actionReminderList.value = actionRes?.items || []
    } catch {
      actionReminderList.value = []
    }
    if (canApprove.value) {
      const [leaveRes, overtimeRes, btRes, heRes] = await Promise.all([
      getPendingLeave({ approver: userName }),
      getPendingOvertime({ approver: userName }),
      getPendingBusinessTrip({ approver: userName }),
      getPendingHolidayExchange({ approver: userName })
    ])
    const items = []
    const leaves = leaveRes.data || []
    leaves.forEach(r => {
      items.push({
        uniqueId: `leave-${r.id}`,
        tabType: 'leave',
        type: '请假审批',
        typeClass: 'type-leave',
        description: `${r.applicant}的${r.type || '请假'}申请`,
        applicant: r.applicant,
        applyTime: r.applyTime || ''
      })
    })
    const overtimes = overtimeRes.data || []
    overtimes.forEach(r => {
      items.push({
        uniqueId: `overtime-${r.id}`,
        tabType: 'overtime',
        type: '加班审批',
        typeClass: 'type-overtime',
        description: `${r.applicant}的${r.date || ''}加班申请`,
        applicant: r.applicant,
        applyTime: r.applyTime || ''
      })
    })
    const trips = btRes.data || []
    trips.forEach(r => {
      const loc = r.location ? `去${r.location}的` : ''
      items.push({
        uniqueId: `bt-${r.id}`,
        tabType: 'business-trip',
        type: '公出审批',
        typeClass: 'type-trip',
        description: `${r.applicant}${loc}公出申请`,
        applicant: r.applicant,
        applyTime: r.applyTime || ''
      })
    })
    const heList = heRes.data || []
    heList.forEach(r => {
      items.push({
        uniqueId: `he-${r.id}`,
        tabType: 'holiday-exchange',
        type: '节假日换休票',
        typeClass: 'type-he',
        description: `${r.applicant}的公出节假日换休票申请（${r.dateFrom}至${r.dateTo}，${r.days}天）`,
        applicant: r.applicant,
        applyTime: r.applyTime || ''
      })
    })
      items.sort((a, b) => (b.applyTime || '').localeCompare(a.applyTime || ''))
      todoList.value = items
    } else {
      todoList.value = []
    }
    // 公出已通过未返回登记数量（所有人均拉取，待办列表展示提醒）
    try {
      const btRes = await getBusinessTripList({ name: userName, year: new Date().getFullYear() })
      const data = btRes?.data || []
      tripReturnPendingCount.value = data.filter(
        r => r.status === '已通过' && Number(r.fhdjStatus) !== 1
      ).length
    } catch {
      tripReturnPendingCount.value = 0
    }
  } catch (e) {
    todoList.value = []
    shiftCoverageGap.value = null
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.page-container {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0 0 var(--spacing-xl);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xl);
}

.page-header h1 {
  margin: 0;
  font-size: var(--font-size-xxl);
  font-weight: var(--font-weight-semibold);
}

.no-permission {
  padding: var(--spacing-xxl);
  text-align: center;
  color: var(--color-text-secondary);
}

.card {
  background: white;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-lighter);
}

.card-header {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: var(--font-size-lg);
}

.count-badge {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.card-body {
  padding: var(--spacing-lg);
}

.table-wrap {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: var(--spacing-md);
  text-align: left;
  border-bottom: 1px solid var(--color-border-lighter);
}

.data-table th {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  background: var(--color-bg-lighter, #f8f9fa);
}

.desc-cell {
  max-width: 360px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.type-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 500;
}

.type-leave {
  background: #fff1f0;
  color: #cf1322;
}

.type-overtime {
  background: var(--color-primary-lightest, #e6f7ff);
  color: var(--color-primary-dark, #096dd9);
}

.type-trip {
  background: #e6fffb;
  color: #08979c;
}

.type-he {
  background: #f0f5ff;
  color: #2f54eb;
}

.type-shift {
  background: #fff7e6;
  color: #d46b08;
}

.type-action {
  background: #eff6ff;
  color: #1d4ed8;
}

.btn-primary.btn-sm {
  padding: 4px 12px;
  font-size: var(--font-size-sm);
}

.empty-state {
  padding: var(--spacing-xxl);
  text-align: center;
  color: var(--color-text-tertiary);
}
</style>
