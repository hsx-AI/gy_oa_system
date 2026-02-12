<template>
  <div class="home-page">
    <!-- 工作台：待办事项 + 我的申请 -->
    <section class="dashboard-section">
      <div class="dashboard-wrap">
        <!-- 待办事项 -->
        <article class="dashboard-card dashboard-card--todo">
          <header class="dashboard-card__header">
            <h2 class="dashboard-card__title">
              <span class="dashboard-card__icon dashboard-card__icon--warning" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                </svg>
              </span>
              <span class="dashboard-card__title-text">待办事项</span>
              <span class="dashboard-card__badge">{{ displayTodoList.length }}</span>
            </h2>
            <a href="javascript:;" class="dashboard-card__link" @click.prevent="router.push('/attendance/pending-tasks')">查看全部</a>
          </header>
          <div class="dashboard-card__body">
            <ul class="todo-list" v-if="displayTodoList.length > 0">
              <li v-for="task in displayTodoList" :key="task.uniqueId" class="todo-item">
                <div class="todo-item__top">
                  <span class="todo-item__type">{{ task.type }}</span>
                  <p class="todo-item__desc" :title="task.description">{{ task.description }}</p>
                </div>
                <div class="todo-item__bottom">
                  <span class="todo-item__meta">{{ task.applicant }} · {{ task.time }}</span>
                  <button type="button" class="todo-item__btn" @click="task.isReturnReminder ? router.push('/attendance/business-trip') : goApprove(task)">
                    {{ task.isReturnReminder ? '去登记' : '处理' }}
                  </button>
                </div>
              </li>
            </ul>
            <div class="dashboard-empty" v-else-if="!todoLoading && !tripReturnLoading">
              <p>暂无待办事项</p>
            </div>
            <div class="dashboard-empty" v-else>
              <p>加载中...</p>
            </div>
          </div>
        </article>

        <!-- 我的申请流程 -->
        <article class="dashboard-card dashboard-card--request">
          <header class="dashboard-card__header">
            <h2 class="dashboard-card__title">
              <span class="dashboard-card__icon dashboard-card__icon--info" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/>
                  <line x1="16" y1="17" x2="8" y2="17"/>
                  <polyline points="10 9 9 9 8 9"/>
                </svg>
              </span>
              <span class="dashboard-card__title-text">我的申请流程</span>
            </h2>
            <a href="javascript:;" class="dashboard-card__link" @click.prevent="goMyApplications">查看全部</a>
          </header>
          <div class="dashboard-card__body">
            <ul class="request-list" v-if="requestList?.length > 0">
              <li v-for="req in requestList" :key="req.uniqueId" class="request-item" @click="goMyApplication(req)">
                <div class="request-item__row request-item__row--main">
                  <span class="request-item__title" :title="req.title">{{ req.title }}</span>
                  <span class="request-item__status" :class="req.statusClass">{{ req.status }}</span>
                </div>
                <div class="request-item__row request-item__row--sub">
                  <span class="request-item__time">{{ req.time }}</span>
                  <span class="request-item__id">{{ req.businessTimeLabel }}</span>
                </div>
              </li>
            </ul>
            <div class="dashboard-empty" v-else-if="!requestLoading">
              <p>暂无待审批或审批中的申请</p>
            </div>
            <div class="dashboard-empty" v-else>
              <p>加载中...</p>
            </div>
          </div>
        </article>
      </div>
    </section>

    <!-- 功能导航卡片 -->
    <div class="container">
      <div v-for="group in featureGroups" :key="group.title" class="feature-group mt-xl">
        <h2 class="section-title mb-lg">{{ group.title }}</h2>
        <div class="features-grid">
          <div
            v-for="feature in group.items"
            :key="feature.id"
            class="feature-card card"
            @click="navigateTo(feature)"
          >
            <div class="feature-icon" :style="{ background: feature.color }">
              <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path :d="feature.iconPath" />
              </svg>
            </div>
            <div class="feature-content">
              <h3 class="feature-title">{{ feature.title }}</h3>
              <p class="feature-desc">{{ feature.description }}</p>
              <div class="feature-footer">
                <span class="feature-tag" v-if="feature.tag">{{ feature.tag }}</span>
                <span class="feature-arrow">→</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
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
  getLeaveList,
  getOvertimeList,
  getBusinessTripList,
  getUploadConfig,
  getOvertimePayPermission
} from '@/api/attendance'
import { getDbManagerPermission } from '@/api/dbManager'
import { getSSOLink } from '@/api/sso'

const router = useRouter()

const dakaman = ref('')
const admin2 = ref('')
const canAccessDbManager = ref(false)
const canSeeOvertimePay = ref(false)

/** 根据 permission 字段判断当前用户是否可见该卡片 */
function canShowFeature(permission) {
  if (!permission) return true
  const name = (userName.value || '').trim()
  const jb = (userJb.value || '').trim()
  const d = (dakaman.value || '').trim()
  const a2 = (admin2.value || '').trim()
  switch (permission) {
    case 'upload':
      return !!d && name === d
    case 'holidaySettings':
      return !!d && name === d
    case 'leaderDashboard':
      return jb === '部长' || jb.startsWith('部长') || jb === '副部长' || jb.startsWith('副部长')
    case 'overtimePay':
      return canSeeOvertimePay.value
    case 'exceptions':
      return (!!d && name === d) || jb === '组长' || jb.startsWith('组长') || jb === '主任' || jb.startsWith('主任') || jb === '副主任' || jb.includes('副主任')
    case 'employeeAdmin':
      return jb === '部长' || jb.startsWith('部长') || jb === '副部长' || jb.startsWith('副部长') || jb === '主任' || jb.startsWith('主任') || jb === '副主任' || jb.includes('副主任') || (!!a2 && name === a2)
    case 'dbManager':
    case 'ygglFill':
      return canAccessDbManager.value
    default:
      return true
  }
}

const userJb = ref('')

const rawFeatureGroups = [
  {
    title: '考勤功能',
    items: [
      {
        id: 'attendance',
        title: '考勤智能填报',
        description: '基于打卡记录智能解析，一键填报考勤并查看分析',
        path: '/attendance',
        color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
        tag: '常用',
        iconPath: 'M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11'
      },
      {
        id: 'manual',
        title: '考勤手动填报',
        description: '请假与加班申请填报，换休票管理及个人记录查询',
        path: '/attendance/manual',
        color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        iconPath: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z'
      },
      {
        id: 'businesstrip',
        title: '公出管理',
        description: '公出申请提交、审批与外出记录统计',
        path: '/attendance/business-trip',
        color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
        iconPath: 'M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z'
      },
      {
        id: 'stats',
        title: '统计汇总',
        description: '加班、请假、公出多维度汇总与报表导出',
        path: '/statistics',
        color: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
        iconPath: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z'
      },
      {
        id: 'upload',
        title: '打卡数据上传',
        description: '批量导入打卡原始数据，为考勤分析提供数据源',
        path: '/upload',
        permission: 'upload',
        color: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
        iconPath: 'M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12'
      },
      {
        id: 'holiday-settings',
        title: '假期调休设置',
        description: '节假日与调休上班日配置，供考勤计算使用',
        path: '/attendance/holiday-settings',
        permission: 'holidaySettings',
        color: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)',
        iconPath: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z'
      },
      {
        id: 'exceptions',
        title: '考勤异常管理',
        description: '班组长/主任查看异常建议，需请假或公出覆盖的智能提示',
        path: '/attendance/exceptions',
        permission: 'exceptions',
        color: 'linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)',
        iconPath: 'M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0zM12 9v4M12 17h.01'
      }
    ]
  },
  {
    title: '领导与人事',
    items: [
      {
        id: 'leader-dashboard',
        title: '领导人看板',
        description: '部长/副部长查看科室加班、请假、公出等汇总看板',
        path: '/leader-dashboard',
        permission: 'leaderDashboard',
        tag: '领导',
        color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        iconPath: 'M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2zM9 22V12h6v10'
      },
      {
        id: 'overtime-pay',
        title: '加班费统计',
        description: '人事管理员查看科室加班费汇总与导出',
        path: '/overtime-pay',
        permission: 'overtimePay',
        tag: '人事',
        color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        iconPath: 'M12 1v22M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6'
      },
      {
        id: 'employee-admin',
        title: '员工在职管理',
        description: '添丁、调岗、离职及员工名单与状态管理',
        path: '/admin/employees',
        permission: 'employeeAdmin',
        color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
        iconPath: 'M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M9 7a4 4 0 104 0 4 4 0 00-4 0zm8 4a4 4 0 11-8 0 4 4 0 018 0z'
      }
    ]
  },
  {
    title: '智能协作与系统',
    items: [
      {
        id: 'personnel-archive',
        title: '人事档案管理系统',
        description: '跳转人事档案系统，使用本系统账号免登',
        ssoTarget: 'B',
        color: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
        tag: '外链',
        iconPath: 'M12 14l9-5-9-5-9 5 9 5zM12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z'
      },
      {
        id: 'filenumbering',
        title: '文件编号管理',
        description: '技术文件与管理文件编号、查询',
        path: '/file/numbering',
        color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        tag: '核心',
        iconPath: 'M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z'
      },
      {
        id: 'db-manager',
        title: '数据库表管理',
        description: '系统管理员对数据库表进行增删改查',
        path: '/admin/db-manager',
        permission: 'dbManager',
        tag: '系统',
        color: 'linear-gradient(135deg, #434343 0%, #000 100%)',
        iconPath: 'M21 12c0 1.66-4 3-9 3s-9-1.34-9-3M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5M12 5c0 1.66-4 3-9 3S0 6.66 0 5'
      },
      {
        id: 'yggl-fill',
        title: '主表批量填充',
        description: '按 Excel 以身份证号匹配，批量更新员工信息字段',
        path: '/admin/yggl-fill',
        permission: 'ygglFill',
        color: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
        iconPath: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12'
      }
    ]
  }
]

const featureGroups = computed(() => {
  return rawFeatureGroups
    .map(group => ({
      ...group,
      items: group.items.filter(item => canShowFeature(item.permission))
    }))
    .filter(group => group.items.length > 0)
})

// 待办事项（真实数据）
const todoList = ref([])
const todoLoading = ref(false)

// 公出已通过但未做返回登记的数量（首页待办提醒）
const tripReturnPendingCount = ref(0)
const tripReturnLoading = ref(false)

// 我的申请（真实数据）
const requestList = ref([])
const requestLoading = ref(false)

function getStoredUserInfo() {
  try {
    const s = localStorage.getItem('userInfo')
    return s ? JSON.parse(s) : {}
  } catch {
    return {}
  }
}

const userInfo = getStoredUserInfo()
// 首页挂载时再读一次，避免登录后 userName 未更新
const userName = ref(userInfo.name || userInfo.userName || '')

/** 相对时间 */
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

// 展示的待办列表 = 审批待办 + 公出返回登记提醒（若有）
const displayTodoList = computed(() => {
  const list = [...(todoList.value || [])]
  if (tripReturnPendingCount.value > 0) {
    list.push({
      uniqueId: 'trip-return-reminder',
      type: '公出返回登记',
      description: `您有 ${tripReturnPendingCount.value} 条公出已通过尚未做返回登记，请及时登记`,
      applicant: '本人',
      time: '',
      isReturnReminder: true
    })
  }
  return list
})

function goApprove(task) {
  router.push({ path: '/attendance/approvals', query: { type: task.tabType } })
}

function goMyApplications() {
  router.push('/attendance/my-applications')
}

function goMyApplication(req) {
  const path = req.source === 'leave' ? '/attendance/leave'
    : req.source === 'overtime' ? '/attendance/overtime'
    : '/attendance/business-trip'
  // 仅用业务时间做筛选定位：year/month 来自上面「请假时间/加班日期/公出时间」，禁止用登记时间
  const year = req.year || new Date().getFullYear()
  const status = req.source === 'business-trip' ? 'processing_rejected' : 'processing'
  const focusIdVal = (req.recordId ?? req.id?.replace(/^QJ|^JB|^GC/, '')) || ''
  const query = { focusId: String(focusIdVal), year: String(year), status }
  if (req.source === 'overtime' && req.month) query.month = req.month
  router.push({ path, query })
}

async function fetchTodoList() {
  if (!userName.value) return
  todoLoading.value = true
  try {
    const res = await checkCanApprove({ name: userName.value })
    if (!res.canApprove) {
      todoList.value = []
      return
    }
    const [leaveRes, overtimeRes, btRes] = await Promise.all([
      getPendingLeave({ approver: userName.value }),
      getPendingOvertime({ approver: userName.value }),
      getPendingBusinessTrip({ approver: userName.value })
    ])
    const items = []
    const leaves = leaveRes.data || []
    leaves.forEach(r => {
      items.push({
        uniqueId: `leave-${r.id}`,
        tabType: 'leave',
        type: '请假审批',
        description: `${r.applicant}的${r.type || '请假'}申请`,
        applicant: r.applicant,
        time: formatRelativeTime(r.applyTime),
        applyTime: r.applyTime || ''
      })
    })
    const overtimes = overtimeRes.data || []
    overtimes.forEach(r => {
      items.push({
        uniqueId: `overtime-${r.id}`,
        tabType: 'overtime',
        type: '加班审批',
        description: `${r.applicant}的${r.date || ''}加班申请`,
        applicant: r.applicant,
        time: formatRelativeTime(r.applyTime),
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
        description: `${r.applicant}${loc}公出申请`,
        applicant: r.applicant,
        time: formatRelativeTime(r.applyTime),
        applyTime: r.applyTime || ''
      })
    })
    items.sort((a, b) => (b.applyTime || '').localeCompare(a.applyTime || ''))
    todoList.value = items.slice(0, 10)
  } catch (e) {
    todoList.value = []
  } finally {
    todoLoading.value = false
  }
}

/** 获取公出已通过但未做返回登记的数量，用于首页待办提醒 */
async function fetchTripReturnPending() {
  if (!userName.value) return
  tripReturnLoading.value = true
  try {
    const res = await getBusinessTripList({ name: userName.value, year: new Date().getFullYear() })
    const data = res?.data || []
    tripReturnPendingCount.value = data.filter(
      r => (r.status === '已通过') && (Number(r.fhdjStatus) !== 1)
    ).length
  } catch (e) {
    tripReturnPendingCount.value = 0
  } finally {
    tripReturnLoading.value = false
  }
}

async function fetchRequestList() {
  const name = userName.value || ''
  if (!name) {
    requestList.value = []
    requestLoading.value = false
    return
  }
  requestLoading.value = true
  try {
    // 拉取全部年份的未通过申请
    const [leaveRes, overtimeRes, btRes] = await Promise.all([
      getLeaveList({ name, status: 'all', all_years: true }),
      getOvertimeList({ name, status: 'all', all_years: true }),
      getBusinessTripList({ name, all_years: true })
    ])
    const items = []
    // ---------- 跳转筛选一律用业务时间，禁止用登记/申请时间 ----------
    // 请假：业务时间 = startTime/endTime（请假开始/结束）；记录页按 timefrom 筛年
    const leaves = (leaveRes.data || []).filter(r => r.status !== '已通过')
    leaves.forEach(r => {
      const startStr = (r.startTime || '').slice(0, 10)  // 请假时间-开始，仅此用于 year
      const endStr = (r.endTime || '').slice(0, 10)
      const businessTimeLabel = startStr && endStr
        ? (startStr === endStr ? `请假时间：${startStr}` : `请假时间：${startStr} 至 ${endStr}`)
        : (startStr ? `请假时间：${startStr}` : '')
      items.push({
        uniqueId: `leave-${r.id}`,
        id: `QJ${r.id}`,
        recordId: r.id,
        year: startStr ? startStr.slice(0, 4) : '',
        title: `${r.type || '请假'}申请`,
        status: r.status,
        statusClass: r.statusClass || 'status-processing',
        time: (r.applyTime || '').slice(0, 10),
        businessTimeLabel,
        source: 'leave'
      })
    })
    // 加班：业务时间 = date（加班日期）；记录页按 timedate 筛年月，禁止用 applyTime
    const overtimes = (overtimeRes.data || []).filter(r => r.status !== '已通过')
    overtimes.forEach(r => {
      const businessDate = (r.date != null && r.date !== '') ? String(r.date).replace('T', ' ').trim().slice(0, 10) : ''
      const businessTimeLabel = businessDate ? `加班日期：${businessDate}` : ''
      items.push({
        uniqueId: `overtime-${r.id}`,
        id: `JB${r.id}`,
        recordId: r.id,
        year: businessDate ? businessDate.slice(0, 4) : '',
        month: businessDate ? businessDate.slice(0, 7) : '',
        title: r.status === '待审批' ? '待审核的加班' : '加班申请',
        status: r.status,
        statusClass: r.statusClass || 'status-processing',
        time: (r.applyTime || r.date || '').slice(0, 10),
        businessTimeLabel,
        source: 'overtime'
      })
    })
    // 公出：业务时间 = assignTime（委派时间）；记录页按 wpsj 筛年，禁止用 startTime/登记时间
    const trips = (btRes.data || []).filter(r => r.status !== '已通过')
    trips.forEach(r => {
      const businessTime = (r.assignTime || '').slice(0, 10)  // 公出时间-委派，仅此用于 year
      const loc = r.location ? `去${r.location}的` : ''
      const businessTimeLabel = businessTime ? `公出时间：${businessTime}` : ''
      items.push({
        uniqueId: `bt-${r.id}`,
        id: `GC${r.id}`,
        recordId: r.id,
        year: businessTime ? businessTime.slice(0, 4) : '',
        title: `${loc}公出登记`,
        status: r.status || '—',
        statusClass: r.statusClass || 'status-processing',
        time: (r.startTime || r.assignTime || '').slice(0, 10),
        businessTimeLabel,
        source: 'business-trip'
      })
    })
    items.sort((a, b) => (b.time || '').localeCompare(a.time || ''))
    requestList.value = items.slice(0, 10)
  } catch (e) {
    requestList.value = []
  } finally {
    requestLoading.value = false
  }
}

onMounted(() => {
  const info = getStoredUserInfo()
  userName.value = info.name || info.userName || ''
  userJb.value = info.jb || ''
  fetchTodoList()
  fetchTripReturnPending()
  fetchRequestList()
  getUploadConfig().then(res => {
    if (res && res.success) {
      dakaman.value = res.dakaman != null ? String(res.dakaman).trim() : ''
      admin2.value = res.admin2 != null ? String(res.admin2).trim() : ''
    }
  }).catch(() => { dakaman.value = ''; admin2.value = '' })
  const name = userName.value?.trim()
  if (name) {
    getDbManagerPermission({ current_user: name }).then(res => {
      canAccessDbManager.value = !!(res && res.canAccess)
    }).catch(() => { canAccessDbManager.value = false })
    getOvertimePayPermission({ name }).then(res => {
      canSeeOvertimePay.value = !!(res && res.canView)
    }).catch(() => { canSeeOvertimePay.value = false })
  }
})

async function navigateTo(feature) {
  if (!feature) return
  if (feature.ssoTarget) {
    const name = (userName.value || '').trim()
    if (!name) {
      alert('请先登录后再使用单点登录')
      return
    }
    try {
      const res = await getSSOLink(feature.ssoTarget, name)
      if (res?.url) {
        window.location.href = res.url
      } else {
        alert(res?.message || '获取跳转链接失败')
      }
    } catch (e) {
      alert(e?.message || e?.response?.data?.detail || '获取免登链接失败，请稍后重试')
    }
    return
  }
  if (!feature.path) return
  if (feature.query) {
    router.push({ path: feature.path, query: feature.query })
  } else {
    router.push(feature.path)
  }
}

</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background: var(--color-bg-layout);
}

/* 工作台：待办 + 我的申请，与系统顶栏间距同其他页（仅 app-main padding-top） */
.dashboard-section {
  margin-top: 0;
  margin-bottom: var(--spacing-xxl);
  padding: 0;
}

.dashboard-wrap {
  width: 100%;
  max-width: none;
  margin: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--spacing-xl);
}

.dashboard-card {
  min-width: 0; /* 允许 grid 子项收缩，防止溢出 */
  background: white;
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.dashboard-card__header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
}

.dashboard-card__title {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  min-width: 0;
}

.dashboard-card__title-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dashboard-card__hint {
  margin: 0;
  padding: 0 var(--spacing-xl) var(--spacing-sm);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  border-bottom: 1px solid var(--color-border-lighter);
}

.dashboard-card__icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.dashboard-card__icon svg {
  width: 20px;
  height: 20px;
  display: block;
}

.dashboard-card__icon--warning {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.dashboard-card__icon--info {
  background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
}

.dashboard-card__badge {
  flex-shrink: 0;
  padding: 2px 8px;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: white;
  background: var(--color-primary);
  border-radius: 999px;
}

.dashboard-card__link {
  flex-shrink: 0;
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  text-decoration: none;
}

.dashboard-card__link:hover {
  text-decoration: underline;
}

.dashboard-card__body {
  flex: 1;
  min-height: 0;
  max-height: 360px;
  padding: var(--spacing-md) var(--spacing-xl) var(--spacing-xl);
  overflow-x: hidden;
  overflow-y: auto;
}

/* 待办列表 */
.todo-list,
.request-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.todo-item {
  padding: var(--spacing-md) 0;
  border-bottom: 1px solid var(--color-border-lighter);
  min-width: 0;
}

.todo-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.todo-item__top {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
  min-width: 0;
}

.todo-item__type {
  flex-shrink: 0;
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-primary);
  padding: 2px 8px;
  background: var(--color-primary-lightest);
  border-radius: var(--radius-sm);
}

.todo-item__desc {
  flex: 1;
  min-width: 0;
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.todo-item__bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-sm);
  padding-left: 0;
}

.todo-item__meta {
  flex: 1;
  min-width: 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.todo-item__btn {
  flex-shrink: 0;
  padding: 4px 12px;
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  background: transparent;
  border: 1px solid var(--color-primary-light);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.todo-item__btn:hover {
  background: var(--color-primary-lightest);
}

/* 我的申请列表 */
.request-item {
  padding: var(--spacing-md) 0;
  border-bottom: 1px solid var(--color-border-lighter);
  min-width: 0;
  cursor: pointer;
}

.request-item:hover {
  background: var(--color-bg-spotlight, #f8f9fa);
}

.request-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.request-item__row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  min-width: 0;
}

.request-item__row--main {
  margin-bottom: var(--spacing-xs);
}

.request-item__title {
  flex: 1;
  min-width: 0;
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.request-item__status {
  flex-shrink: 0;
  font-size: var(--font-size-xs);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.request-item__status.status-processing {
  color: #d97706;
  background: #fef3c7;
}

.request-item__status.status-approved {
  color: #059669;
  background: #d1fae5;
}

.request-item__status.status-rejected {
  color: #dc2626;
  background: #fee2e2;
}

.request-item__row--sub {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.request-item__time {
  flex-shrink: 0;
}

.request-item__id {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dashboard-empty {
  padding: var(--spacing-xxl);
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.dashboard-empty p {
  margin: 0;
}

/* 功能卡片图标尺寸 */
.feature-icon svg {
  width: 100%;
  height: 100%;
  max-width: 24px;
  max-height: 24px;
  display: block;
}

/* 功能卡片 */
.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: var(--spacing-xl);
  margin-top: var(--spacing-md);
}

.feature-card {
  padding: var(--spacing-xl);
  cursor: pointer;
  transition: all var(--transition-base) var(--transition-ease);
  border: 1px solid var(--color-border-lighter);
  display: flex;
  gap: var(--spacing-base);
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-elevated);
  border-color: var(--color-primary-lightest);
}

.feature-icon {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.feature-icon .icon {
  width: 28px;
  height: 28px;
  color: white;
}

.feature-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.feature-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-sm);
}

.feature-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: var(--spacing-base);
  flex: 1;
}

.feature-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.feature-tag {
  font-size: var(--font-size-xs);
  padding: 2px var(--spacing-sm);
  background: var(--color-primary-lightest);
  color: var(--color-primary);
  border-radius: var(--radius-sm);
  font-weight: var(--font-weight-medium);
}

.feature-arrow {
  color: var(--color-text-tertiary);
  font-size: var(--font-size-lg);
  transition: transform var(--transition-base) var(--transition-ease);
}

.feature-card:hover .feature-arrow {
  transform: translateX(4px);
  color: var(--color-primary);
}

.section-title {
  font-size: var(--font-size-xxl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.mb-lg {
  margin-bottom: var(--spacing-lg);
}

/* 响应式 */
@media (max-width: 992px) {
  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-xl);
  }
  
  .header-meta {
    width: 100%;
    justify-content: space-between;
  }
  
  .dashboard-wrap {
    grid-template-columns: 1fr;
  }
  
  .features-grid {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  }
}

@media (max-width: 768px) {
  .page-header {
    padding: var(--spacing-xxl) 0;
  }
  
  .header-title {
    font-size: var(--font-size-xxl);
  }
  
  .dashboard-section {
    padding: 0 var(--spacing-md);
  }
  
  .dashboard-card__header,
  .dashboard-card__body {
    padding-left: var(--spacing-lg);
    padding-right: var(--spacing-lg);
  }
  
  .features-grid {
    grid-template-columns: 1fr;
  }
}
</style>
