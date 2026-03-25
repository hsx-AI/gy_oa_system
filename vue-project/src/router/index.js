import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Attendance from '../views/Attendance.vue'
import Login from '../views/Login.vue'
import UploadAttendance from '../views/UploadAttendance.vue'
import Statistics from '../views/Statistics.vue'
import LeaderDashboard from '../views/LeaderDashboard.vue'
import OvertimePay from '../views/OvertimePay.vue'
import { getUploadConfig } from '@/api/attendance'
import { getDbManagerPermission } from '@/api/dbManager'

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
    path: '/leader-dashboard',
    name: 'LeaderDashboard',
    component: LeaderDashboard
  },
  {
    path: '/overtime-pay',
    name: 'OvertimePay',
    component: OvertimePay
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
    component: () => import('../views/attendance/BusinessTripAllRecords.vue')
  },
  {
    path: '/attendance/leave/all-records',
    name: 'LeaveAllRecords',
    redirect: (to) => ({
      path: '/attendance/manual',
      query: { ...to.query, tab: 'leave', from: to.query.from || 'all-records' }
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
    meta: { title: '系统健康监控' }
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

  // 以下为各页面单独权限校验
  if (to.path === '/leader-dashboard') {
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
      const allowedByAdmin1 = admin1 && name === admin1
      const allowedByJb = jb === '部长' || jb.startsWith('部长') || jb === '副部长' || jb.startsWith('副部长')
      const allowedByZhjsDirector = lsys === '综合技术室' && (
        jb === '主任' || (jb && jb.startsWith('主任')) ||
        jb === '副主任' || (jb && jb.includes('副主任'))
      )
      if (allowedByAdmin1 || allowedByJb || allowedByZhjsDirector) next()
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
      const isDeptLeader = jb === '组长' || (jb && jb.startsWith('组长')) ||
        jb === '主任' || (jb && jb.startsWith('主任')) ||
        jb === '副主任' || (jb && jb.includes('副主任'))
      if (isAdmin1 || isDakaman || isDeptLeader) {
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
      const isLeaderOrDept = jb === '部长' || jb.startsWith('部长') || jb === '副部长' || jb.startsWith('副部长') ||
        jb === '主任' || (jb && jb.startsWith('主任')) ||
        jb === '副主任' || (jb && jb.includes('副主任'))
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
  if (to.path === '/admin/hxp-manage') {
    try {
      const raw = localStorage.getItem('userInfo')
      if (!raw) { next('/login'); return }
      const user = JSON.parse(raw)
      const name = (user.name || user.userName || '').trim()
      if (!name) { next('/'); return }
      const res = await getUploadConfig()
      const a1 = (res?.admin1 || '').trim()
      const a2 = (res?.admin2 || '').trim()
      if ((a1 && name === a1) || (a2 && name === a2)) {
        next()
      } else {
        next('/')
      }
    } catch { next('/') }
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




