import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Attendance from '../views/Attendance.vue'
import Login from '../views/Login.vue'
import UploadAttendance from '../views/UploadAttendance.vue'
import Statistics from '../views/Statistics.vue'
import LeaderDashboard from '../views/LeaderDashboard.vue'
import OvertimePay from '../views/OvertimePay.vue'
import Performance from '../views/Performance.vue'
import { getUploadConfig } from '@/api/attendance'
import { getDbManagerPermission } from '@/api/dbManager'
import { isMinisterLevel, isMinisterOrDeptLeader, isDirectorLevel, isManagerLevel, canAccessLeaderDashboard, canManageHxpBatch, canUseAiAssistant } from '@/utils/roleMatch'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/attendance',
    name: 'Attendance',
    component: Attendance
  },
  {
    path: '/attendance/personnel-visualization',
    name: 'PersonnelVisualization',
    component: () => import('../views/attendance/PersonnelVisualization.vue'),
    meta: { title: '人员出勤可视化' }
  },
  {
    path: '/upload',
    name: 'UploadAttendance',
    component: UploadAttendance
  },
  {
    path: '/attendance/holiday-settings',
    name: 'HolidaySettings',
    component: () => import('../views/attendance/HolidaySettings.vue'),
    meta: { title: '假期调休设置' }
  },
  {
    path: '/attendance/exceptions',
    name: 'AttendanceExceptions',
    component: () => import('../views/attendance/AttendanceExceptions.vue'),
    meta: { title: '考勤异常管理' }
  },
  {
    path: '/statistics',
    name: 'Statistics',
    component: Statistics
  },
  {
    path: '/reports-hub',
    name: 'ReportsHub',
    component: () => import('../views/ReportsHub.vue'),
    meta: { title: '报表汇聚' }
  },
  {
    path: '/confidentiality-ledger',
    name: 'ConfidentialityLedger',
    component: () => import('../views/ConfidentialityLedger.vue'),
    meta: { title: '保密审批台账' }
  },
  {
    path: '/leader-dashboard',
    name: 'LeaderDashboard',
    component: LeaderDashboard
  },
  {
    path: '/leader-overtime-statistics',
    name: 'LeaderOvertimeStats',
    component: () => import('../views/LeaderOvertimeStats.vue'),
    meta: { title: '领导加班统计' }
  },
  {
    path: '/overtime-pay',
    name: 'OvertimePay',
    component: OvertimePay
  },
  {
    path: '/performance',
    name: 'Performance',
    component: Performance,
    meta: { title: '绩效统计' }
  },
  {
    path: '/attendance/manual',
    name: 'ManualEntry',
    component: () => import('../views/attendance/ManualEntry.vue'),
    meta: { title: '考勤手动填报' }
  },
  {
    path: '/attendance/leave',
    redirect: (to) => ({ path: '/attendance/manual', query: { ...to.query, tab: 'leave' } })
  },
  {
    path: '/attendance/overtime',
    redirect: (to) => ({ path: '/attendance/manual', query: { ...to.query, tab: 'overtime' } })
  },
  {
    path: '/attendance/business-trip',
    name: 'BusinessTrip',
    component: () => import('../views/attendance/BusinessTrip.vue')
  },
  {
    path: '/attendance/business-trip/all-records',
    name: 'BusinessTripAllRecords',
    redirect: (to) => ({
      path: '/attendance/business-trip',
      query: { ...to.query, view: 'ledger' }
    })
  },
  {
    path: '/attendance/leave/all-records',
    name: 'LeaveAllRecords',
    redirect: (to) => ({
      path: '/attendance/manual',
      query: { ...to.query, tab: 'leave', from: to.query.from || 'all-records', view: 'ledger' }
    })
  },
  {
    path: '/attendance/approvals',
    name: 'Approvals',
    component: () => import('../views/attendance/Approval.vue')
  },
  {
    path: '/attendance/pending-tasks',
    name: 'PendingTasks',
    component: () => import('../views/attendance/PendingTasks.vue')
  },
  {
    path: '/attendance/my-applications',
    name: 'MyApplications',
    component: () => import('../views/attendance/MyApplications.vue')
  },
  {
    path: '/attendance/business-trip/dept-detail',
    name: 'BusinessTripDeptDetail',
    component: () => import('../views/attendance/BusinessTripDeptDetail.vue')
  },
  {
    path: '/file/numbering',
    name: 'FileNumbering',
    component: () => import('../views/file/FileNumbering.vue')
  },
  {
    path: '/file/tech-category',
    name: 'TechCategoryManage',
    component: () => import('../views/file/TechCategoryManage.vue')
  },
  {
    path: '/file/workno',
    name: 'WorkNoManage',
    component: () => import('../views/file/WorkNoManage.vue')
  },
  {
    path: '/file/policy-query',
    name: 'PolicyQuery',
    component: () => import('../views/file/PolicyQuery.vue'),
    meta: { title: '部门制度查询' }
  },
  {
    path: '/file/bid-templates',
    name: 'BidTemplateLibrary',
    component: () => import('../views/file/BidTemplateLibrary.vue'),
    meta: { title: '工艺投标文件管理' }
  },
  {
    path: '/file/tech-problem',
    name: 'TechProblemList',
    component: () => import('../views/file/TechProblemList.vue'),
    meta: { title: '工艺技术问题手册' }
  },
  {
    path: '/file/tech-problem/create',
    name: 'TechProblemCreate',
    component: () => import('../views/file/TechProblemForm.vue'),
    meta: { title: '新建技术问题' }
  },
  {
    path: '/file/tech-problem/edit/:id',
    name: 'TechProblemEdit',
    component: () => import('../views/file/TechProblemForm.vue'),
    meta: { title: '编辑技术问题' }
  },
  {
    path: '/weldoa/ypp_main',
    alias: '/weldoa/ypp_main.asp',
    name: 'RotorBladeBalance',
    component: () => import('../views/RotorBladeBalance.vue'),
    meta: { title: '转轮叶片配重工艺程序' }
  },
  {
    path: '/profile',
    name: 'EmployeeProfile',
    component: () => import('../views/EmployeeProfile.vue')
  },
  {
    path: '/admin/employees',
    name: 'AdminEmployeeStatus',
    component: () => import('../views/AdminEmployeeStatus.vue')
  },
  {
    path: '/admin/db-manager',
    name: 'DbManager',
    component: () => import('../views/admin/DbManager.vue'),
    meta: { title: '数据库表管理' }
  },
  {
    path: '/admin/health-monitor',
    name: 'HealthMonitor',
    component: () => import('../views/admin/HealthMonitor.vue'),
    meta: { title: '系统管理员' }
  },
  {
    path: '/admin/access-dashboard',
    name: 'AccessDashboard',
    component: () => import('../views/admin/AccessDashboard.vue'),
    meta: { title: '系统访问情况看板', fullscreen: true }
  },
  {
    path: '/admin/yggl-fill',
    name: 'YgglFill',
    component: () => import('../views/admin/YgglFill.vue'),
    meta: { title: '主表批量填充' }
  },
  {
    path: '/admin/email',
    name: 'EmailSender',
    component: () => import('../views/admin/EmailSender.vue'),
    meta: { title: '邮件发送' }
  },
  {
    path: '/admin/notification',
    name: 'NotificationManage',
    component: () => import('../views/admin/NotificationManage.vue'),
    meta: { title: '消息推送管理' }
  },
  {
    path: '/admin/inbox-emails',
    name: 'InboxEmails',
    component: () => import('../views/admin/InboxEmails.vue'),
    meta: { title: '经理层重要邮箱' }
  },
  {
    path: '/attendance/shift-schedule',
    name: 'ShiftSchedule',
    component: () => import('../views/attendance/ShiftSchedule.vue'),
    meta: { title: '排班管理' }
  },
  {
    path: '/admin/hxp-manage',
    name: 'HxpManage',
    component: () => import('../views/admin/HxpManage.vue'),
    meta: { title: '换休票管理' }
  },
  {
    path: '/admin/hxp-records',
    name: 'HxpRecords',
    component: () => import('../views/admin/HxpRecords.vue'),
    meta: { title: '换休票明细查询' }
  },
  {
    path: '/attendance/business-trip/map',
    name: 'BusinessTripMap',
    component: () => import('@/views/attendance/BusinessTripMap.vue')
  },
  {
    path: '/attendance/discipline',
    name: 'AttendanceDiscipline',
    component: () => import('@/views/attendance/AttendanceDiscipline.vue'),
    meta: { title: '考勤纪律审查' }
  },
  {
    path: '/attendance/holiday-duty-check',
    name: 'HolidayDutyCheck',
    component: () => import('@/views/attendance/HolidayDutyCheck.vue'),
    meta: { title: '假期值班出勤核查' }
  },
  {
    path: '/attendance/kqyc-records',
    name: 'AttendanceExceptionRecords',
    component: () => import('@/views/attendance/AttendanceExceptionRecords.vue'),
    meta: { title: '打卡异常申请记录' }
  },
  {
    path: '/feedback',
    name: 'FeedbackCenter',
    component: () => import('@/views/feedback/FeedbackCenter.vue'),
    meta: { title: '意见与建议' }
  },
  {
    path: '/contacts',
    name: 'Contacts',
    component: () => import('@/views/Contacts.vue'),
    meta: { title: '部门通讯录' }
  },
  {
    path: '/action-items/dashboard',
    name: 'ActionItemDashboard',
    component: () => import('@/views/action-items/ActionItemCenter.vue'),
    props: { mode: 'dashboard' },
    meta: { title: '行动项驾驶舱' }
  },
  {
    path: '/action-items/minutes',
    name: 'ActionItemMinutes',
    component: () => import('@/views/action-items/ActionItemCenter.vue'),
    props: { mode: 'minutes' },
    meta: { title: '会议纪要' }
  },
  {
    path: '/action-items/ledger',
    name: 'ActionItemLedger',
    component: () => import('@/views/action-items/ActionItemCenter.vue'),
    props: { mode: 'ledger' },
    meta: { title: '行动项台账' }
  },
  {
    path: '/action-items/my',
    name: 'MyActionItems',
    component: () => import('@/views/action-items/ActionItemCenter.vue'),
    props: { mode: 'my' },
    meta: { title: '我的行动项' }
  },
  {
    path: '/action-items/messages',
    name: 'MyActionItemMessages',
    component: () => import('@/views/action-items/ActionItemCenter.vue'),
    props: { mode: 'messages' },
    meta: { title: '行动项消息' }
  },
  {
    path: '/action-items/approvals',
    name: 'ActionItemApprovals',
    component: () => import('@/views/action-items/ActionItemCenter.vue'),
    props: { mode: 'approvals' },
    meta: { title: '行动项审批' }
  },
  {
    path: '/action-items/review/:meetingId',
    name: 'ActionItemReview',
    component: () => import('@/views/action-items/ActionItemReview.vue'),
    meta: { title: 'AI提取确认' }
  },
  {
    path: '/action-items/:id',
    name: 'ActionItemDetail',
    component: () => import('@/views/action-items/ActionItemDetail.vue'),
    meta: { title: '行动项详情' }
  },
  {
    path: '/info-feed',
    name: 'InfoFeed',
    component: () => import('@/views/InfoFeed.vue'),
    meta: { title: '天气新闻' }
  },
  {
    path: '/seal/apply',
    name: 'SealApply',
    component: () => import('@/views/seal/SealApply.vue'),
    meta: { title: '部门用印申请' }
  },
  {
    path: '/low-value-reimbursement',
    name: 'LowValueReimbursement',
    component: () => import('@/views/LowValueReimbursement.vue'),
    meta: { title: '低值易耗报销' }
  },
  {
    path: '/massage-chair',
    name: 'MassageChairBooking',
    component: () => import('@/views/massage/MassageChairBooking.vue'),
    meta: { title: '健康角预约' }
  },
  // AI 助手（公测）：仅智能制造技术室全员 + 公司经理/副经理/经理助理可访问，见下方 beforeEach 守卫
  {
    path: '/ai-assistant',
    name: 'AiAssistant',
    component: () => import('@/views/AiAssistant.vue'),
    meta: { title: '智能制造工艺部AI助手' }
  }
  // 未来可以添加更多路由：
  // {
  //   path: '/approval/leader',
  //   name: 'LeaderApproval',
  //   component: () => import('../views/LeaderApproval.vue')
  // },
  // {
  //   path: '/approval/admin',
  //   name: 'AdminApproval',
  //   component: () => import('../views/AdminApproval.vue')
  // },
  // {
  //   path: '/stats',
  //   name: 'Statistics',
  //   component: () => import('../views/Statistics.vue')
  // },
  // {
  //   path: '/profile',
  //   name: 'Profile',
  //   component: () => import('../views/Profile.vue')
  // }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 未登录时仅允许访问登录页，其余一律重定向到 /login
router.beforeEach(async (to, _from, next) => {
  if (to.path === '/login') {
    next()
    return
  }
  const raw = localStorage.getItem('userInfo')
  if (!raw) {
    next('/login')
    return
  }
  if (to.name === 'RotorBladeBalance') {
    try {
      const user = JSON.parse(raw)
      const name = (user.name || user.userName || '').trim()
      const lsys = (user.lsys || user.dept || '').trim()
      if (!name) {
        next('/login')
      } else if (lsys === '焊接工艺室' || lsys === '部办') {
        next()
      } else {
        next('/')
      }
    } catch {
      next('/login')
    }
    return
  }

  // AI 助手（公测）：仅智能制造技术室全员 + 公司经理/副经理/经理助理
  if (to.name === 'AiAssistant') {
    try {
      const user = JSON.parse(raw)
      const name = (user.name || user.userName || '').trim()
      const jb = (user.jb || '').trim()
      const lsys = (user.lsys || user.dept || '').trim()
      if (!name) {
        next('/login')
      } else if (canUseAiAssistant({ jb, lsys })) {
        next()
      } else {
        next('/')
      }
    } catch {
      next('/login')
    }
    return
  }
  try {
    const user = JSON.parse(raw)
    const name = (user.name || user.userName || '').trim()
    if (!name) {
      next('/login')
      return
    }
  } catch {
    next('/login')
    return
  }

  // "其他部门成员"仅可访问文件编号相关页面
  try {
    const u = JSON.parse(raw)
    const lsys = (u.dept || u.lsys || '').trim()
    if (lsys === '其他部门成员') {
      const allowed = ['/file/numbering', '/file/tech-category', '/file/workno', '/attendance/personnel-visualization', '/confidentiality-ledger']
      if (!allowed.includes(to.path)) {
        next('/file/numbering')
        return
      }
    }
  } catch { /* ignore */ }

  // 以下为各页面单独权限校验
  if (to.path === '/leader-overtime-statistics') {
    try {
      const raw = localStorage.getItem('userInfo')
      if (!raw) {
        next('/login')
        return
      }
      const user = JSON.parse(raw)
      const jb = (user.jb || '').trim()
      if (isMinisterLevel(jb)) next()
      else next('/')
    } catch {
      next('/')
    }
    return
  }

  if (to.path === '/leader-dashboard' || to.path === '/attendance/discipline') {
    try {
      const raw = localStorage.getItem('userInfo')
      if (!raw) {
        next('/login')
        return
      }
      const user = JSON.parse(raw)
      const name = (user.name || user.userName || '').trim()
      const jb = (user.jb || '').trim()
      const lsys = (user.dept || user.lsys || '').trim()
      const res = await getUploadConfig()
      const admin1 = (res && res.admin1 != null ? res.admin1 : '').trim()
      const admin2 = (res && res.admin2 != null ? res.admin2 : '').trim()
      if (canAccessLeaderDashboard({ name, jb, lsys, admin1, admin2 })) next()
      else next('/')
    } catch {
      next('/')
    }
    return
  }
  if (to.path === '/attendance/holiday-duty-check') {
    try {
      const raw = localStorage.getItem('userInfo')
      if (!raw) {
        next('/login')
        return
      }
      const user = JSON.parse(raw)
      const name = (user.name || user.userName || '').trim()
      const jb = (user.jb || '').trim()
      const lsys = (user.dept || user.lsys || '').trim()
      const res = await getUploadConfig()
      const admin2 = (res && res.admin2 != null ? res.admin2 : '').trim()
      const allowedByAdmin2 = admin2 && name === admin2
      const allowedZhjsDirector = lsys === '综合技术室' && isDirectorLevel(jb)
      if (allowedByAdmin2 || allowedZhjsDirector) next()
      else next('/')
    } catch {
      next('/')
    }
    return
  }
  if (to.path === '/upload' || to.path === '/attendance/holiday-settings') {
    try {
      const raw = localStorage.getItem('userInfo')
      if (!raw) {
        next('/login')
        return
      }
      const user = JSON.parse(raw)
      const name = (user.name || user.userName || '').trim()
      const res = await getUploadConfig()
      const dakaman = (res && res.dakaman != null ? res.dakaman : '').trim()
      const admin1 = (res && res.admin1 != null ? res.admin1 : '').trim()
      if ((dakaman && name === dakaman) || (admin1 && name === admin1)) {
        next()
      } else {
        next('/')
      }
    } catch {
      next('/')
    }
    return
  }
  if (to.path === '/attendance/exceptions') {
    try {
      const raw = localStorage.getItem('userInfo')
      if (!raw) {
        next('/login')
        return
      }
      const user = JSON.parse(raw)
      const name = (user.name || user.userName || '').trim()
      const jb = (user.jb || '').trim()
      const res = await getUploadConfig()
      const dakaman = (res && res.dakaman != null ? res.dakaman : '').trim()
      const admin1 = (res && res.admin1 != null ? res.admin1 : '').trim()
      const isDakaman = dakaman && name === dakaman
      const isAdmin1 = admin1 && name === admin1
      const isMinister = isMinisterLevel(jb)
      const isDeptLeader = isMinisterOrDeptLeader(jb) && !isMinister
      if (isAdmin1 || isDakaman || isMinister || isDeptLeader) {
        next()
      } else {
        next('/')
      }
    } catch {
      next('/')
    }
    return
  }
  if (to.path === '/admin/employees') {
    try {
      const raw = localStorage.getItem('userInfo')
      if (!raw) {
        next('/login')
        return
      }
      const user = JSON.parse(raw)
      const name = (user.name || user.userName || '').trim()
      const jb = (user.jb || '').trim()
      const res = await getUploadConfig()
      const admin1Name = (res && res.admin1 != null ? res.admin1 : '').trim()
      if (admin1Name && name === admin1Name) {
        next()
        return
      }
      const isLeaderOrDept = isMinisterOrDeptLeader(jb)
      if (isLeaderOrDept) {
        next()
        return
      }
      const admin2Name = (res && res.admin2 != null ? res.admin2 : '').trim()
      if (admin2Name && name === admin2Name) {
        next()
      } else {
        next('/')
      }
    } catch {
      next('/')
    }
    return
  }
  if (to.path === '/admin/hxp-records') {
    try {
      const raw = localStorage.getItem('userInfo')
      if (!raw) { next('/login'); return }
      const user = JSON.parse(raw)
      const name = (user.name || user.userName || '').trim()
      if (!name) { next('/'); return }
      const jb = (user.jb || '').trim()
      const minister = isMinisterLevel(jb)
      const res = await getUploadConfig()
      const a2 = (res?.admin2 || '').trim()
      if (minister || (a2 && name === a2)) {
        next()
      } else {
        next('/')
      }
    } catch { next('/') }
    return
  }
  if (to.path === '/admin/hxp-manage') {
    try {
      const raw = localStorage.getItem('userInfo')
      if (!raw) { next('/login'); return }
      const user = JSON.parse(raw)
      const name = (user.name || user.userName || '').trim()
      if (!name) { next('/'); return }
      const res = await getUploadConfig()
      const allowed = canManageHxpBatch({
        name,
        jb: (user.jb || '').trim(),
        lsys: (user.dept || user.lsys || '').trim(),
        admin1: res?.admin1,
        admin2: res?.admin2,
      })
      if (allowed) {
        next()
      } else {
        next('/')
      }
    } catch { next('/') }
    return
  }
  if (to.path === '/admin/inbox-emails') {
    try {
      const raw = localStorage.getItem('userInfo')
      if (!raw) { next('/login'); return }
      const user = JSON.parse(raw)
      const name = (user.name || user.userName || '').trim()
      const jb = (user.jb || '').trim()
      if (!name) { next('/'); return }
      const res = await getDbManagerPermission({ current_user: name })
      const canDbAdmin = !!(res && res.canAccess)
      const canLeader = isManagerLevel(jb)
      if (canDbAdmin || canLeader) next()
      else next('/')
    } catch {
      next('/')
    }
    return
  }
  if (to.path === '/admin/db-manager' || to.path === '/admin/health-monitor' || to.path === '/admin/yggl-fill' || to.path === '/admin/email' || to.path === '/admin/notification') {
    try {
      const raw = localStorage.getItem('userInfo')
      if (!raw) {
        next('/login')
        return
      }
      const user = JSON.parse(raw)
      const name = (user.name || user.userName || '').trim()
      if (!name) {
        next('/')
        return
      }
      const res = await getDbManagerPermission({ current_user: name })
      if (res && res.canAccess) {
        next()
      } else {
        next('/')
      }
    } catch {
      next('/')
    }
    return
  }
  next()
})

export default router
