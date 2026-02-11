<template>
  <div class="page-container">
    <div class="page-header">
      <h1>全部待办事项</h1>
      <button class="btn btn-outline" @click="router.push('/attendance/approvals')">进入审批</button>
    </div>

    <template v-if="!canApprove">
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
                      {{ task.isReturnReminder ? '去登记' : '处理' }}
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
  getBusinessTripList
} from '@/api/attendance'

const router = useRouter()
const canApprove = ref(false)
const todoList = ref([])
const loading = ref(false)
/** 公出已通过但未做返回登记的数量 */
const tripReturnPendingCount = ref(0)

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
  return list
})

function goApprove(task) {
  if (task.isReturnReminder) {
    router.push('/attendance/business-trip')
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
    if (canApprove.value) {
      const [leaveRes, overtimeRes, btRes] = await Promise.all([
      getPendingLeave({ approver: userName }),
      getPendingOvertime({ approver: userName }),
      getPendingBusinessTrip({ approver: userName })
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
