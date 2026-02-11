<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-left">
        <button type="button" class="btn-back" @click="goBack">← 返回</button>
        <h1>科室公出详情</h1>
      </div>
      <p class="header-sub" v-if="periodLabel">{{ periodLabel }}</p>
    </div>

    <div class="card table-card">
      <div class="card-body">
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>委派单位</th>
                <th>通知单编号</th>
                <th>填报单位</th>
                <th>公出人员姓名</th>
                <th>人数</th>
                <th>工作号</th>
                <th>项目名称</th>
                <th>公出地点</th>
                <th>出发时间</th>
                <th>预计返回时间</th>
                <th>请款金额(元)</th>
                <th>联系电话</th>
                <th>公出任务</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in deptDetailList" :key="row.id">
                <td>{{ row.targetUnit }}</td>
                <td>{{ row.noticeNo }}</td>
                <td>{{ row.department }}</td>
                <td>{{ row.name }}</td>
                <td>{{ row.totalPeople }}</td>
                <td>{{ row.workNo }}</td>
                <td>{{ row.projectName }}</td>
                <td>{{ row.location }}</td>
                <td>{{ row.startTime }}</td>
                <td>{{ row.endTime }}</td>
                <td>{{ row.amount }}</td>
                <td>{{ row.phone }}</td>
                <td class="cell-task">{{ row.task }}</td>
                <td><span class="status-tag" :class="row.statusClass">{{ row.status }}</span></td>
              </tr>
              <tr v-if="!deptDetailList.length">
                <td colspan="14" class="empty-cell">暂无公出记录</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const periodLabel = computed(() => {
  const { month, year, quarter } = route.query
  if (month) {
    const [y, m] = String(month).split('-')
    return y && m ? `${y}年${parseInt(m, 10)}月` : ''
  }
  if (year) {
    const y = year
    if (quarter) {
      const q = { '1': '第一季度', '2': '第二季度', '3': '第三季度', '4': '第四季度' }[quarter]
      return `${y}年${q || ''}`
    }
    return `${y}年`
  }
  return '全部'
})

// 模拟科室公出明细（与公出表结构一致）
const mockDeptDetail = [
  {
    id: 1,
    targetUnit: '研发中心',
    noticeNo: 'TZ202501001',
    department: '智能制造工艺部',
    name: '张三',
    totalPeople: 1,
    workNo: 'W001',
    projectName: '研发对接',
    location: '北京',
    startTime: '2025-01-06 08:00',
    endTime: '2025-01-08 18:00',
    amount: 0,
    phone: '138****0001',
    task: '技术对接与需求沟通',
    status: '已通过',
    statusClass: 'status-approved'
  },
  {
    id: 2,
    targetUnit: '采购部',
    noticeNo: 'TZ202501002',
    department: '智能制造工艺部',
    name: '李四',
    totalPeople: 2,
    workNo: 'W002',
    projectName: '供应商考察',
    location: '上海',
    startTime: '2025-01-10 09:00',
    endTime: '2025-01-14 17:00',
    amount: 5000,
    phone: '139****0002',
    task: '供应商现场考察与洽谈',
    status: '已通过',
    statusClass: 'status-approved'
  },
  {
    id: 3,
    targetUnit: '质量保证和售后服务部',
    noticeNo: 'TZ202501003',
    department: '智能制造工艺部',
    name: '王五',
    totalPeople: 1,
    workNo: 'W003',
    projectName: '质量审核',
    location: '广州',
    startTime: '2025-01-15 08:30',
    endTime: '2025-01-16 17:00',
    amount: 0,
    phone: '137****0003',
    task: '体系审核配合',
    status: '审批中',
    statusClass: 'status-processing'
  },
  {
    id: 4,
    targetUnit: '市场部',
    noticeNo: 'TZ202501004',
    department: '智能制造工艺部',
    name: '赵六',
    totalPeople: 1,
    workNo: 'W004',
    projectName: '客户拜访',
    location: '深圳',
    startTime: '2025-01-20 09:00',
    endTime: '2025-01-20 18:00',
    amount: 800,
    phone: '136****0004',
    task: '客户技术交流',
    status: '已通过',
    statusClass: 'status-approved'
  }
]

const deptDetailList = ref([...mockDeptDetail])

function goBack() {
  router.push('/attendance/business-trip')
}
</script>

<style scoped>
.page-container {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0 0 var(--spacing-xl);
}

.page-header {
  margin-bottom: var(--spacing-xl);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xs);
}

.btn-back {
  padding: 6px 12px;
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  background: transparent;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.btn-back:hover {
  background: var(--color-primary-lightest);
}

.page-header h1 {
  margin: 0;
  font-size: var(--font-size-xxl);
  font-weight: 600;
  color: var(--color-text-primary);
}

.header-sub {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.table-card {
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  background: white;
}

.card-body {
  padding: 0;
}

.table-wrap {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  min-width: 1200px;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}

.data-table th,
.data-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--color-border-lighter);
  white-space: nowrap;
}

.data-table th {
  font-weight: 600;
  color: var(--color-text-primary);
  background: var(--color-bg-layout);
  position: sticky;
  top: 0;
}

.data-table tbody tr:hover {
  background: var(--color-bg-layout);
}

.data-table .cell-task {
  max-width: 180px;
  white-space: normal;
  word-break: break-all;
}

.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
}

.status-tag.status-approved {
  color: #059669;
  background: #d1fae5;
}

.status-tag.status-processing {
  color: #d97706;
  background: #fef3c7;
}

.status-tag.status-rejected {
  color: #dc2626;
  background: #fee2e2;
}

.empty-cell {
  text-align: center;
  color: var(--color-text-tertiary);
  padding: var(--spacing-xxl);
}
</style>
