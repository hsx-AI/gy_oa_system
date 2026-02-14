<template>
  <div id="app" class="app-container" :class="{ 'with-sidebar': showNav }">
    <template v-if="showNav">
      <!-- 左侧选项栏 -->
      <aside class="app-sidebar">
        <div class="sidebar-header">
          <svg class="sidebar-logo" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 11l3 3L22 4" />
            <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
          </svg>
          <span class="sidebar-title">集成办公平台</span>
        </div>
        <nav class="sidebar-nav">
          <router-link to="/" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            <span>首页</span>
          </router-link>
          <router-link to="/profile" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            <span>员工信息</span>
          </router-link>
          <router-link to="/attendance" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 11l3 3L22 4" />
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
            <span>考勤智能填报</span>
          </router-link>
          <router-link to="/attendance/business-trip" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <span>公出管理</span>
          </router-link>
          <router-link to="/statistics" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="20" x2="18" y2="10" />
              <line x1="12" y1="20" x2="12" y2="4" />
              <line x1="6" y1="20" x2="6" y2="14" />
            </svg>
            <span>统计汇总</span>
          </router-link>
          <router-link v-if="canSeeOvertimePay" to="/overtime-pay" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="1" x2="12" y2="23" />
              <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
            <span>加班费统计</span>
          </router-link>
          <router-link v-if="canSeeLeaderDashboard" to="/leader-dashboard" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            <span>领导人看板</span>
          </router-link>
          <router-link v-if="canShowUpload" to="/upload" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span>打卡数据上传</span>
          </router-link>
          <router-link v-if="canShowUpload" to="/attendance/holiday-settings" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
            <span>假期调休设置</span>
          </router-link>
          <router-link v-if="canShowAttendanceExceptions" to="/attendance/exceptions" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            <span>考勤异常管理</span>
          </router-link>
          <router-link to="/file/numbering" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
            <span>文件编号</span>
          </router-link>
          <router-link to="/file/policy-query" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
            <span>制度查询</span>
          </router-link>
          <router-link v-if="canShowEmployeeAdmin" to="/admin/employees" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
            <span>员工在职管理</span>
          </router-link>
          <router-link v-if="canAccessDbManager" to="/admin/db-manager" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <ellipse cx="12" cy="5" rx="9" ry="3" />
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
            </svg>
            <span>数据库表管理</span>
          </router-link>
          <router-link v-if="canAccessDbManager" to="/admin/yggl-fill" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span>主表批量填充</span>
          </router-link>
        </nav>
      </aside>

      <!-- 右侧：顶栏 + 主内容 + 页脚 -->
      <div class="app-content-wrap">
        <header class="app-header">
          <div class="header-container">
            <div class="header-left">
              <span class="app-title">智能制造工艺部集成办公平台</span>
            </div>
            <div class="header-right">
              <button class="header-action-btn">
                <svg class="action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                  <path d="M13.73 21a2 2 0 0 1-3.46 0" />
                </svg>
                <span class="badge-dot"></span>
              </button>
              <button class="header-action-btn">
                <svg class="action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                </svg>
              </button>
              <div class="user-info" ref="userInfoRef" @click="toggleUserMenu">
                <div class="user-avatar">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </div>
                <span class="user-name">{{ displayUserName }}</span>
                <div v-if="showUserMenu" class="user-menu">
                  <router-link to="/profile" class="user-menu__item" @click="showUserMenu = false">
                    员工信息
                  </router-link>
                  <button type="button" class="user-menu__item" @click.stop="handleLogout">
                    退出登录
                  </button>
                </div>
              </div>
            </div>
          </div>
        </header>

        <main class="app-main">
          <router-view />
        </main>

        <footer class="app-footer">
          <div class="footer-container">
            <div class="footer-text">
              © 2026 智能制造工艺部集成办公平台
            </div>
            <div class="footer-links">
              智能制造技术室 | 能做科技团队
            </div>
          </div>
        </footer>
      </div>
    </template>

    <template v-else>
      <main class="app-main no-header">
        <router-view />
      </main>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getUploadConfig, getOvertimePayPermission } from '@/api/attendance'
import { getDbManagerPermission } from '@/api/dbManager'

const route = useRoute()
const router = useRouter()

// 当前用户信息
const currentUser = ref({
  name: '',
  dept: '',
  username: ''
})

const showUserMenu = ref(false)
const userInfoRef = ref(null)
// 打卡数据上传权限：webconfig.dakaman 对应用户
const dakaman = ref('')
// 人事管理员：webconfig.admin2，权限等同于部长/副部长（含员工在职管理）
const admin2 = ref('')

// 是否显示员工在职管理入口（部长/副部长/科室主任/副主任 或 人事管理员 admin2）
const canShowEmployeeAdmin = computed(() => {
  const jb = (currentUser.value?.jb || '').trim()
  const name = (currentUser.value?.name || currentUser.value?.userName || '').trim()
  const isLeaderOrDept = jb === '部长' || jb.startsWith('部长') || jb === '副部长' || jb.startsWith('副部长') ||
    jb === '主任' || (jb && jb.startsWith('主任')) ||
    jb === '副主任' || (jb && jb.includes('副主任'))
  const isAdmin2 = (admin2.value || '').trim() && name === (admin2.value || '').trim()
  return isLeaderOrDept || isAdmin2
})

// 是否显示领导人看板（仅 yggl 表中 jb 为 部长/副部长 可见）
const canSeeLeaderDashboard = computed(() => {
  const jb = (currentUser.value?.jb || '').trim()
  return jb === '部长' || jb.startsWith('部长') || jb === '副部长' || jb.startsWith('副部长')
})

// 是否显示加班费统计入口（部长/副部长 或 人事管理员 webconfig.admin2）
const canSeeOvertimePay = ref(false)

// 是否显示数据库表管理入口（仅 webconfig.admin1 系统管理员）
const canAccessDbManager = ref(false)

// 是否显示打卡数据上传（仅 webconfig.dakaman 用户可见）
const canShowUpload = computed(() => {
  const name = (currentUser.value?.name || currentUser.value?.userName || '').trim()
  const d = (dakaman.value || '').trim()
  return !!d && name === d
})

// 是否显示考勤异常管理（班组长/主任/副主任 或 打卡管理员可见；部长/副部长/员工不可见）
const canShowAttendanceExceptions = computed(() => {
  const jb = (currentUser.value?.jb || '').trim()
  const name = (currentUser.value?.name || currentUser.value?.userName || '').trim()
  const d = (dakaman.value || '').trim()
  if (d && name === d) return true
  return jb === '组长' || (jb && jb.startsWith('组长')) ||
    jb === '主任' || (jb && jb.startsWith('主任')) ||
    jb === '副主任' || (jb && jb.includes('副主任'))
})

// 切换用户菜单
const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value
}

// 点击外部关闭菜单
const onDocumentClick = (e) => {
  if (userInfoRef.value && !userInfoRef.value.contains(e.target)) {
    showUserMenu.value = false
  }
}

// 退出登录
const handleLogout = () => {
  localStorage.removeItem('userInfo')
  currentUser.value = { name: '', dept: '', username: '' }
  canSeeOvertimePay.value = false
  canAccessDbManager.value = false
  admin2.value = ''
  showUserMenu.value = false
  router.push('/login')
}

// 加载用户信息
const loadUserInfo = () => {
  try {
    const userInfo = localStorage.getItem('userInfo')
    if (userInfo) {
      currentUser.value = JSON.parse(userInfo)
      const name = (currentUser.value?.name || currentUser.value?.userName || '').trim()
      if (name) {
        getOvertimePayPermission({ name }).then(res => {
          canSeeOvertimePay.value = !!(res && res.canView)
        }).catch(() => { canSeeOvertimePay.value = false })
        getDbManagerPermission({ current_user: name }).then(res => {
          canAccessDbManager.value = !!(res && res.canAccess)
        }).catch(() => { canAccessDbManager.value = false })
      } else {
        canSeeOvertimePay.value = false
        canAccessDbManager.value = false
      }
    } else {
      canSeeOvertimePay.value = false
      canAccessDbManager.value = false
    }
  } catch (error) {
    console.error('加载用户信息失败:', error)
    canSeeOvertimePay.value = false
    canAccessDbManager.value = false
  }
}

// 路由变化时重新加载用户信息（登录后跳转时 currentUser 能正确更新）
watch(() => route.path, () => {
  loadUserInfo()
}, { immediate: true })

// 加载打卡/人事配置（dakaman、admin2）
const loadUploadConfig = () => {
  getUploadConfig().then(res => {
    if (res && res.success) {
      if (res.dakaman != null) dakaman.value = res.dakaman || ''
      if (res.admin2 != null) admin2.value = res.admin2 || ''
    }
  }).catch(() => { dakaman.value = ''; admin2.value = '' })
}

onMounted(() => {
  document.addEventListener('click', onDocumentClick)
  loadUploadConfig()
})

onUnmounted(() => {
  document.removeEventListener('click', onDocumentClick)
})

// 不显示导航的路由
const noNavRoutes = ['/login']
const showNav = computed(() => !noNavRoutes.includes(route.path))

// 显示用户名：优先 currentUser.name，其次 username（有登录态时才显示主布局，此处不应出现空）
const displayUserName = computed(() => {
  const u = currentUser.value
  return (u.name || u.userName || u.username || '').trim() || '用户'
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-layout);
}

.app-container.with-sidebar {
  flex-direction: row;
  width: 100%;
}

/* 左侧选项栏 */
.app-sidebar {
  width: 220px;
  min-width: 220px;
  background: linear-gradient(180deg, #1f2937 0%, #111827 100%);
  color: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  height: var(--header-height);
  padding: 0 var(--spacing-lg);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
}

.sidebar-logo {
  width: 28px;
  height: 28px;
  color: #fff;
  flex-shrink: 0;
}

.sidebar-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: #fff;
  white-space: nowrap;
}

.sidebar-nav {
  flex: 1;
  padding: var(--spacing-md) 0;
  overflow-y: auto;
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: 12px var(--spacing-lg);
  font-size: var(--font-size-sm);
  color: rgba(255, 255, 255, 0.75);
  text-decoration: none;
  transition: all 0.2s ease;
  border-left: 3px solid transparent;
}

.sidebar-item:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.06);
}

.sidebar-item-active {
  color: #fff;
  background: rgba(96, 165, 250, 0.15);
  border-left-color: #60a5fa;
  font-weight: 500;
}

.sidebar-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  opacity: 0.9;
}

.sidebar-item span {
  white-space: nowrap;
}

/* 右侧内容区 */
.app-content-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-layout);
}

/* 顶栏：与侧栏头部同高、同色，下边线平齐；铺满右侧至画面右边缘 */
.app-header {
  position: sticky;
  top: 0;
  z-index: var(--z-index-sticky);
  background: linear-gradient(180deg, #1f2937 0%, #111827 100%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
  width: 100%;
  min-width: 0;
}

.header-container {
  width: 100%;
  margin: 0 auto;
  padding: 0 0 0 var(--spacing-xl);
  height: var(--header-height);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
}

.app-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: #fff;
  white-space: nowrap;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-base);
}

.header-action-btn {
  position: relative;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: all var(--transition-base) var(--transition-ease);
}

.header-action-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.action-icon {
  width: 20px;
  height: 20px;
  color: #fff;
}

.badge-dot {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 8px;
  height: 8px;
  background: var(--color-error);
  border-radius: 50%;
  border: 2px solid #1f2937;
}

.user-info {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: background-color var(--transition-base) var(--transition-ease);
}

.user-info:hover {
  background: rgba(255, 255, 255, 0.1);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-circle);
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-avatar svg {
  width: 18px;
  height: 18px;
}

.user-name {
  font-size: var(--font-size-sm);
  color: #fff;
  font-weight: var(--font-weight-medium);
}

.user-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  min-width: 120px;
  background: var(--color-bg-container);
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-md);
  padding: var(--spacing-xs);
  z-index: 100;
}

.user-menu__item {
  display: block;
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  background: none;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  text-align: left;
  transition: background-color var(--transition-base) var(--transition-ease);
}

.user-menu__item:hover {
  background: var(--color-bg-spotlight);
}

a.user-menu__item {
  text-decoration: none;
  box-sizing: border-box;
}

/* 主内容区：与系统顶栏保持统一上间距，最小左右留白 */
.app-main {
  flex: 1;
  padding: var(--spacing-xl) 0 0 var(--page-content-gap, 20px);
  min-width: 0;
}

.app-main.no-header {
  padding-top: var(--spacing-xl);
}

/* 页脚 */
.app-footer {
  background: var(--color-bg-container);
  border-top: 1px solid var(--color-border-lighter);
  padding: var(--spacing-xl) 0;
  margin-top: var(--spacing-xxl);
}

.footer-container {
  max-width: 100%;
  margin: 0 auto;
  padding: 0 0 0 var(--spacing-xl);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.footer-links {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.footer-link {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  text-decoration: none;
  transition: color var(--transition-base) var(--transition-ease);
}

.footer-link:hover {
  color: var(--color-primary);
}

.footer-divider {
  color: var(--color-border-base);
}

/* 响应式：小屏时侧栏收窄 */
@media (max-width: 992px) {
  .app-sidebar {
    width: 64px;
    min-width: 64px;
  }

  .sidebar-title,
  .sidebar-item span {
    display: none;
  }

  .sidebar-header {
    justify-content: center;
    padding: var(--spacing-lg);
  }

  .sidebar-item {
    justify-content: center;
    padding: 12px;
  }
}

@media (max-width: 768px) {
  .app-container.with-sidebar {
    flex-direction: column;
  }

  .app-sidebar {
    width: 100%;
    min-width: 0;
    flex-direction: row;
    flex-wrap: wrap;
    padding: var(--spacing-sm);
    gap: var(--spacing-xs);
  }

  .sidebar-header {
    width: 100%;
    justify-content: flex-start;
  }

  .sidebar-title {
    display: block;
  }

  .sidebar-nav {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-xs);
    padding: 0;
  }

  .sidebar-item {
    flex: 1;
    min-width: 80px;
    justify-content: center;
    border-left: none;
    border-bottom: 3px solid transparent;
  }

  .sidebar-item span {
    display: block;
    font-size: 12px;
  }

  .sidebar-item-active {
    border-left: none;
    border-bottom-color: #60a5fa;
  }

  .user-name {
    display: none;
  }

  .footer-container {
    flex-direction: column;
    gap: var(--spacing-base);
    text-align: center;
  }
}
</style>
