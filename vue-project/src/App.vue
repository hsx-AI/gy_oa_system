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
          <router-link v-if="!isOtherDeptUser" to="/" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            <span>首页</span>
          </router-link>
          <!-- TODO: 服务器端测试通过后取消注释 — 侧栏 AI 助手入口
          <router-link v-if="!isOtherDeptUser" to="/ai-assistant" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2a2 2 0 0 1 2 2v1h3a2 2 0 0 1 2 2v3h1a2 2 0 0 1 0 4h-1v3a2 2 0 0 1-2 2h-3v1a2 2 0 0 1-4 0v-1H7a2 2 0 0 1-2-2v-3H4a2 2 0 0 1 0-4h1V7a2 2 0 0 1 2-2h3V4a2 2 0 0 1 2-2z" />
              <circle cx="9.5" cy="11" r="1" />
              <circle cx="14.5" cy="11" r="1" />
              <path d="M9 15c.8.7 1.9 1 3 1s2.2-.3 3-1" />
            </svg>
            <span>AI 助手</span>
          </router-link>
          -->
          <router-link v-if="!isOtherDeptUser" to="/profile" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            <span>员工信息</span>
          </router-link>
          <router-link v-if="!isOtherDeptUser" to="/contacts" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
            <span>通讯录</span>
          </router-link>
          <router-link v-if="!isOtherDeptUser" to="/info-feed" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 15a4 4 0 0 0 4 4h10a4 4 0 0 0 1.2-7.82A6 6 0 0 0 6.2 9.1 4 4 0 0 0 3 15z" />
              <path d="M8 22v-1" />
              <path d="M12 22v-1" />
              <path d="M16 22v-1" />
            </svg>
            <span>天气新闻</span>
          </router-link>
          <router-link v-if="!isOtherDeptUser" to="/attendance" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 11l3 3L22 4" />
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
            <span>考勤智能填报</span>
          </router-link>
          <router-link to="/attendance/personnel-visualization" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="4" width="18" height="14" rx="2" />
              <path d="M7 18v2" />
              <path d="M17 18v2" />
              <circle cx="8" cy="10" r="2" />
              <path d="M5.5 15a3 3 0 0 1 5 0" />
              <circle cx="16" cy="10" r="2" />
              <path d="M13.5 15a3 3 0 0 1 5 0" />
            </svg>
            <span>人员出勤可视化</span>
          </router-link>
          <router-link v-if="!isOtherDeptUser" to="/attendance/business-trip" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <span>公出管理</span>
          </router-link>
          <router-link v-if="!isOtherDeptUser" to="/seal/apply" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            <span>部门用印申请</span>
          </router-link>
          <router-link v-if="!isOtherDeptUser && !canSeeLeaderDashboard" to="/statistics" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="20" x2="18" y2="10" />
              <line x1="12" y1="20" x2="12" y2="4" />
              <line x1="6" y1="20" x2="6" y2="14" />
            </svg>
            <span>统计汇总</span>
          </router-link>
          <router-link v-if="!isOtherDeptUser" to="/reports-hub" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <path d="M14 2v6h6" />
              <path d="M8 13h8" />
              <path d="M8 17h6" />
            </svg>
            <span>报表汇聚</span>
          </router-link>
          <router-link v-if="!isOtherDeptUser" to="/overtime-pay" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="1" x2="12" y2="23" />
              <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
            <span>其他绩效激励统计</span>
          </router-link>
          <router-link v-if="!isOtherDeptUser" to="/attendance/shift-schedule" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="4" width="18" height="18" rx="2" />
              <path d="M3 10h18" />
              <path d="M8 2v4" />
              <path d="M16 2v4" />
              <path d="M7 14h2v2H7z" />
              <path d="M11 14h2v2h-2z" />
              <path d="M15 14h2v2h-2z" />
            </svg>
            <span>排班管理</span>
          </router-link>
          <router-link v-if="canSeeLeaderDashboard" to="/leader-dashboard" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            <span>管理驾驶舱</span>
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
          <router-link v-if="!isOtherDeptUser" to="/file/policy-query" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
            <span>制度查询</span>
          </router-link>
          <router-link v-if="!isOtherDeptUser" to="/file/bid-templates" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 4h16v16H4z" />
              <path d="M8 8h8" />
              <path d="M8 12h8" />
              <path d="M8 16h5" />
            </svg>
            <span>工艺投标文件</span>
          </router-link>
          <router-link v-if="!isOtherDeptUser" to="/file/tech-problem" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
              <rect x="9" y="3" width="6" height="4" rx="1" />
              <path d="M9 14l2 2 4-4" />
            </svg>
            <span>技术问题手册</span>
          </router-link>
          <router-link v-if="canUseRotorBladeBalance" to="/weldoa/ypp_main" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 3v18" />
              <path d="M3 12h18" />
              <path d="M5.64 5.64l12.72 12.72" />
              <path d="M18.36 5.64L5.64 18.36" />
            </svg>
            <span>转轮叶片配重</span>
          </router-link>
          <router-link v-if="!isOtherDeptUser" to="/feedback" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            <span>意见与建议</span>
          </router-link>
          <a v-if="!isOtherDeptUser" href="javascript:;" class="sidebar-item" @click.prevent="goSixianghuibao">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 14l9-5-9-5-9 5 9 5z" />
              <path d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
            </svg>
            <span>思想汇报管理</span>
          </a>
          <a v-if="!isOtherDeptUser" href="javascript:;" class="sidebar-item" @click.prevent="goPersonnelArchive">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
            <span>人事档案系统</span>
          </a>
          <router-link v-if="canShowEmployeeAdmin" to="/admin/employees" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
            <span>员工在职管理</span>
          </router-link>
          <router-link v-if="canManageHxp" to="/admin/hxp-manage" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="5" width="20" height="14" rx="2" />
              <line x1="2" y1="10" x2="22" y2="10" />
            </svg>
            <span>换休票管理</span>
          </router-link>
          <router-link v-if="canAccessDbManager" to="/admin/db-manager" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <ellipse cx="12" cy="5" rx="9" ry="3" />
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
            </svg>
            <span>数据库表管理</span>
          </router-link>
          <router-link v-if="canAccessDbManager" to="/admin/health-monitor" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
            <span>系统管理员</span>
          </router-link>
          <router-link v-if="canAccessDbManager" to="/admin/yggl-fill" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span>主表批量填充</span>
          </router-link>
          <router-link v-if="canAccessDbManager" to="/admin/email" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
              <polyline points="22,6 12,13 2,6" />
            </svg>
            <span>邮件发送</span>
          </router-link>
          <router-link v-if="canAccessDbManager" to="/admin/notification" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
            <span>消息推送</span>
          </router-link>
          <router-link v-if="canAccessInboxEmails" to="/admin/inbox-emails" class="sidebar-item" active-class="sidebar-item-active">
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 12h-6l-2 3h-4l-2-3H2" />
              <path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
            </svg>
            <span>待办邮箱</span>
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
              <div ref="todoBellWrapRef" class="todo-bell-wrap">
                <button
                  type="button"
                  class="header-action-btn"
                  aria-label="待办事项"
                  :aria-expanded="todoPopoverOpen ? 'true' : 'false'"
                  @click.stop="toggleTodoPopover"
                >
                  <svg class="action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                    <path d="M13.73 21a2 2 0 0 1-3.46 0" />
                  </svg>
                  <span v-if="totalBadgeCount > 0" class="badge-dot" aria-hidden="true"></span>
                </button>
                <div
                  v-show="todoPopoverOpen"
                  class="todo-popover"
                  role="dialog"
                  aria-label="待办事项"
                  @click.stop
                >
                  <div class="todo-popover__header">
                    <div class="todo-popover__tabs">
                      <button
                        type="button"
                        :class="['todo-popover__tab', { active: todoActiveTab === 'todo' }]"
                        @click="todoActiveTab = 'todo'"
                      >待办事项 <span class="todo-popover__count">{{ totalBadgeCount }}</span></button>
                      <button
                        type="button"
                        :class="['todo-popover__tab', { active: todoActiveTab === 'notify' }]"
                        @click="switchToNotifyTab"
                      >系统通知</button>
                    </div>
                    <button v-if="todoActiveTab === 'todo'" type="button" class="todo-popover__link" @click="openAllTodos">查看全部</button>
                  </div>
                  <div class="todo-popover__body" v-show="todoActiveTab === 'todo'">
                    <ul v-if="displayTodoList.length" class="todo-popover-list">
                      <li v-for="task in displayTodoList" :key="task.uniqueId" class="todo-popover-item">
                        <div class="todo-popover-item__top">
                          <span class="todo-popover-item__type">{{ task.type }}</span>
                          <p class="todo-popover-item__desc" :title="task.description">{{ task.description }}</p>
                        </div>
                        <div class="todo-popover-item__bottom">
                          <span class="todo-popover-item__meta">{{ task.applicant }}{{ task.time ? ' · ' + task.time : '' }}</span>
                          <button type="button" class="todo-popover-item__btn" @click="onHeaderTodoAction(task)">
                            {{ task.isHxpNotice ? '已读' : (task.isHxpApproval ? '去审批' : (task.isPersonnel ? '去处理' : (task.isSixianghuibao ? (task.btnLabel || '去处理') : (task.isReturnReminder ? '去登记' : (task.isSealUsePending ? '已用印' : (task.isSealApproval ? '去审批' : (task.btnLabel || '处理'))))))) }}
                          </button>
                        </div>
                      </li>
                    </ul>
                    <div v-else-if="!todoPanelLoading" class="todo-popover-empty">暂无待办事项</div>
                    <div v-else class="todo-popover-empty">加载中…</div>
                  </div>
                  <div class="todo-popover__body" v-show="todoActiveTab === 'notify'">
                    <div v-if="todoNotifyLoading" class="todo-popover-empty">加载中…</div>
                    <div v-else-if="!todoNotifyList.length" class="todo-popover-empty">暂无系统通知</div>
                    <div v-else class="changelog-list">
                      <div v-for="n in todoNotifyList" :key="n.id" class="changelog-item">
                        <div class="changelog-item__time">{{ n.time }}</div>
                        <div class="changelog-item__content" v-html="escapeHtml(n.content)"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div ref="settingsWrapRef" class="settings-wrap">
                <button
                  type="button"
                  class="header-action-btn"
                  aria-label="系统设置"
                  :aria-expanded="settingsPopoverOpen ? 'true' : 'false'"
                  @click.stop="toggleSettingsPopover"
                >
                  <svg class="action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="3" />
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                  </svg>
                </button>
                <div v-show="settingsPopoverOpen" class="settings-popover" role="dialog" aria-label="系统设置" @click.stop>
                  <div class="settings-popover__header">
                    <svg class="settings-popover__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="3" />
                      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                    </svg>
                    <span>界面风格</span>
                  </div>
                  <div class="settings-style-grid">
                    <button
                      v-for="item in skinStyleOptions"
                      :key="item.key"
                      type="button"
                      class="settings-style-card"
                      :class="{ active: activeSkinStyle === item.key }"
                      @click="changeSkinStyle(item.key)"
                    >
                      <span class="settings-style-card__preview">
                        <span class="settings-style-card__bar" :style="{ background: item.primary }"></span>
                        <span class="settings-style-card__bar" :style="{ background: item.secondary }"></span>
                      </span>
                      <span class="settings-style-card__label">{{ item.label }}</span>
                      <span v-if="activeSkinStyle === item.key" class="settings-style-card__check">
                        <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                      </span>
                    </button>
                  </div>
                  <div v-if="!isOtherDeptUser" class="settings-popover__divider"></div>
                  <button v-if="!isOtherDeptUser" type="button" class="settings-action-card" @click="openHomeLayoutSettings">
                    <span class="settings-action-card__icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="3" width="7" height="7" rx="1" />
                        <rect x="14" y="3" width="7" height="7" rx="1" />
                        <rect x="3" y="14" width="7" height="7" rx="1" />
                        <rect x="14" y="14" width="7" height="7" rx="1" />
                      </svg>
                    </span>
                    <span class="settings-action-card__body">
                      <strong>首页布局</strong>
                      <small>调整模块顺序和显示状态</small>
                    </span>
                  </button>
                </div>
              </div>
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

    <!-- 首次登录 / 未读介绍 弹窗 -->
    <div v-if="showIntroModal" class="intro-modal-overlay" @click.self="closeIntroModal">
      <div class="intro-modal">
        <div class="intro-modal-header">
          <h2 class="intro-modal-title">欢迎使用集成办公平台</h2>
          <button type="button" class="intro-modal-close" aria-label="关闭" @click="closeIntroModal">×</button>
        </div>
        <div class="intro-modal-body">
          <section class="intro-section">
            <h3>系统功能简介</h3>
            <p>本平台集成考勤智能填报、公出管理、加班/请假审批、统计汇总、管理驾驶舱、文件编号、制度查询、思想汇报与人事档案入口等功能，便于部门统一办公与考勤管理。</p>
          </section>
          <section class="intro-section intro-notice">
            <h3>重要提醒</h3>
            <p><strong>请已登录的同事知悉：</strong>本月起，部门内部考勤（加班、请假、公出等）处理请在本系统上填报。</p>
            <p>左侧侧边栏「<strong>考勤智能填报</strong>」可极大简化填报流程；打卡数据按服务端配置时刻自动同步当天数据，请及时处理考勤异常。</p>
            <p>3 月份的加班/请假数据需重新填报，系统运行初期请各位谅解。</p>
            <p>三月份原老系统上消耗的换休票已经补齐，请各位放心申请三月加班。</p>
            <p class="intro-contact">系统问题请联系：智能室黄圣轩 7480 / 18400021209</p>
          </section>
        </div>
        <div class="intro-modal-footer">
          <button type="button" class="btn btn-primary" @click="closeIntroModal">知道了</button>
        </div>
      </div>
    </div>

    <!-- 更新通知弹窗（支持多条未读） -->
    <div v-if="showNotificationModal" class="notification-modal-overlay" @click.self="closeNotificationModal">
      <div class="notification-modal">
        <div class="notification-modal-header">
          <h2 class="notification-modal-title">系统更新通知</h2>
          <span v-if="unreadNotifications.length > 1" class="notification-count">{{ unreadNotifications.length }} 条未读</span>
          <button type="button" class="notification-modal-close" aria-label="关闭" @click="closeNotificationModal">×</button>
        </div>
        <div class="notification-modal-body">
          <div v-for="(n, idx) in unreadNotifications" :key="n.id" class="notification-item" :class="{ 'notification-item-border': idx > 0 }">
            <div class="notification-item-time">{{ n.time }}</div>
            <div class="notification-item-content" v-html="escapeHtml(n.content)"></div>
          </div>
        </div>
        <div class="notification-modal-footer">
          <button type="button" class="btn btn-primary" @click="closeNotificationModal">全部已读</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getUploadConfig, setLoginStatus, getUserStyle, saveUserStyle } from '@/api/attendance'
import { getDbManagerPermission } from '@/api/dbManager'
import { getSSOLink } from '@/api/sso'
import { dismissNotification, listNotifications } from '@/api/admin'
import { useWorkplaceTodos, refreshWorkplaceTodos } from '@/composables/useWorkplaceTodos'
import { isMinisterLevel, isMinisterOrDeptLeader, isDirectorLevel, canAccessLeaderDashboard } from '@/utils/roleMatch'

const route = useRoute()
const router = useRouter()

const {
  totalBadgeCount,
  displayTodoList,
  todoPanelLoading,
  handleTodoAction,
} = useWorkplaceTodos()

const todoBellWrapRef = ref(null)
const todoPopoverOpen = ref(false)
const settingsWrapRef = ref(null)
const settingsPopoverOpen = ref(false)
const activeSkinStyle = ref('default')

const skinStyleOptions = [
  { key: 'default', label: '默认蓝', primary: '#1890ff', secondary: '#e6f7ff' },
  { key: 'dark', label: '深色夜间', primary: '#5b8cff', secondary: '#161b22' },
  { key: 'green', label: '清新绿色', primary: '#2f9e44', secondary: '#ebfbee' },
  { key: 'purple', label: '优雅紫色', primary: '#7c3aed', secondary: '#f3e8ff' },
  { key: 'pink', label: '甜美粉', primary: '#e84393', secondary: '#fce4ec' },
  { key: 'warm', label: '暖橙风格', primary: '#f97316', secondary: '#fff7ed' },
]

const skinStyleVarMap = {
  default: {
    '--color-primary': '#1890ff',
    '--color-primary-light': '#40a9ff',
    '--color-primary-lighter': '#69c0ff',
    '--color-primary-lightest': '#e6f7ff',
    '--color-primary-dark': '#096dd9',
    '--color-primary-darker': '#0050b3',
    '--color-info': '#1890ff',
    '--color-info-light': '#69c0ff',
    '--color-info-bg': '#e6f7ff',
    '--color-bg-layout': '#f0f2f5',
    '--color-bg-container': '#ffffff',
    '--color-bg-elevated': '#ffffff',
    '--color-bg-spotlight': '#fafafa',
    '--color-text-primary': '#262626',
    '--color-text-secondary': '#595959',
    '--color-text-tertiary': '#8c8c8c',
    '--color-border-base': '#d9d9d9',
    '--color-border-light': '#e8e8e8',
    '--color-border-lighter': '#f0f0f0',
    '--color-sb-bg-start': '#1f2937',
    '--color-sb-bg-end': '#111827',
    '--color-sb-text': 'rgba(255, 255, 255, 0.9)',
    '--color-sb-text-hover': '#fff',
    '--color-sb-text-muted': 'rgba(255, 255, 255, 0.75)',
    '--color-sb-active-bg': 'rgba(96, 165, 250, 0.15)',
    '--color-sb-active-border': '#60a5fa',
    '--color-sb-border': 'rgba(255, 255, 255, 0.08)',
    '--color-header-bg-start': '#1f2937',
    '--color-header-bg-end': '#111827',
    '--color-header-border': 'rgba(255, 255, 255, 0.08)',
    '--color-header-text': '#fff',
    '--color-header-action-hover': 'rgba(255, 255, 255, 0.1)',
    '--color-user-avatar-bg': 'rgba(255, 255, 255, 0.2)',
    '--color-user-hover': 'rgba(255, 255, 255, 0.1)',
    '--color-legacy-bar-start': '#ff4d4f',
    '--color-legacy-bar-end': '#ff7a45',
    '--color-legacy-bar-text': '#fff',
    '--color-legacy-bar-btn-bg': '#ffc53d',
    '--color-legacy-bar-btn-text': '#1a1a1a',
    '--color-legacy-bar-btn-hover': '#ffd666',
    '--color-legacy-bar-note': 'rgba(255,255,255,0.95)',
  },
  dark: {
    '--color-primary': '#5b8cff',
    '--color-primary-light': '#7aa2ff',
    '--color-primary-lighter': '#9bb9ff',
    '--color-primary-lightest': '#1c2538',
    '--color-primary-dark': '#3d6ee6',
    '--color-primary-darker': '#2d57bf',
    '--color-info': '#5b8cff',
    '--color-info-light': '#9bb9ff',
    '--color-info-bg': '#1c2538',
    '--color-bg-layout': '#0f172a',
    '--color-bg-container': '#111827',
    '--color-bg-elevated': '#1f2937',
    '--color-bg-spotlight': '#273449',
    '--color-text-primary': '#e5e7eb',
    '--color-text-secondary': '#cbd5e1',
    '--color-text-tertiary': '#94a3b8',
    '--color-border-base': '#334155',
    '--color-border-light': '#283549',
    '--color-border-lighter': '#1e293b',
    '--color-sb-bg-start': '#0b1120',
    '--color-sb-bg-end': '#070b15',
    '--color-sb-text': 'rgba(255, 255, 255, 0.9)',
    '--color-sb-text-hover': '#fff',
    '--color-sb-text-muted': 'rgba(255, 255, 255, 0.7)',
    '--color-sb-active-bg': 'rgba(91, 140, 255, 0.18)',
    '--color-sb-active-border': '#5b8cff',
    '--color-sb-border': 'rgba(255, 255, 255, 0.08)',
    '--color-header-bg-start': '#0b1120',
    '--color-header-bg-end': '#070b15',
    '--color-header-border': 'rgba(255, 255, 255, 0.08)',
    '--color-header-text': '#e5e7eb',
    '--color-header-action-hover': 'rgba(255, 255, 255, 0.08)',
    '--color-user-avatar-bg': 'rgba(255, 255, 255, 0.12)',
    '--color-user-hover': 'rgba(255, 255, 255, 0.08)',
    '--color-legacy-bar-start': '#dc2626',
    '--color-legacy-bar-end': '#ea580c',
    '--color-legacy-bar-text': '#e5e7eb',
    '--color-legacy-bar-btn-bg': '#fbbf24',
    '--color-legacy-bar-btn-text': '#1a1a1a',
    '--color-legacy-bar-btn-hover': '#fcd34d',
    '--color-legacy-bar-note': 'rgba(229,231,235,0.9)',
  },
  green: {
    '--color-primary': '#2f9e44',
    '--color-primary-light': '#40c057',
    '--color-primary-lighter': '#69db7c',
    '--color-primary-lightest': '#ebfbee',
    '--color-primary-dark': '#2b8a3e',
    '--color-primary-darker': '#237032',
    '--color-info': '#2f9e44',
    '--color-info-light': '#69db7c',
    '--color-info-bg': '#ebfbee',
    '--color-bg-layout': '#f1f8f2',
    '--color-bg-container': '#ffffff',
    '--color-bg-elevated': '#ffffff',
    '--color-bg-spotlight': '#f4fbf5',
    '--color-text-primary': '#1f2937',
    '--color-text-secondary': '#4b5563',
    '--color-text-tertiary': '#6b7280',
    '--color-border-base': '#cfe8d3',
    '--color-border-light': '#dbefde',
    '--color-border-lighter': '#e8f5ea',
    '--color-sb-bg-start': '#1a3a21',
    '--color-sb-bg-end': '#0f2a15',
    '--color-sb-text': 'rgba(255, 255, 255, 0.9)',
    '--color-sb-text-hover': '#fff',
    '--color-sb-text-muted': 'rgba(255, 255, 255, 0.75)',
    '--color-sb-active-bg': 'rgba(47, 158, 68, 0.2)',
    '--color-sb-active-border': '#2f9e44',
    '--color-sb-border': 'rgba(255, 255, 255, 0.08)',
    '--color-header-bg-start': '#1a3a21',
    '--color-header-bg-end': '#0f2a15',
    '--color-header-border': 'rgba(255, 255, 255, 0.08)',
    '--color-header-text': '#fff',
    '--color-header-action-hover': 'rgba(255, 255, 255, 0.1)',
    '--color-user-avatar-bg': 'rgba(255, 255, 255, 0.2)',
    '--color-user-hover': 'rgba(255, 255, 255, 0.1)',
    '--color-legacy-bar-start': '#dc2626',
    '--color-legacy-bar-end': '#f97316',
    '--color-legacy-bar-text': '#fff',
    '--color-legacy-bar-btn-bg': '#86efac',
    '--color-legacy-bar-btn-text': '#1a1a1a',
    '--color-legacy-bar-btn-hover': '#a7f3d0',
    '--color-legacy-bar-note': 'rgba(255,255,255,0.95)',
  },
  purple: {
    '--color-primary': '#7c3aed',
    '--color-primary-light': '#8b5cf6',
    '--color-primary-lighter': '#a78bfa',
    '--color-primary-lightest': '#f3e8ff',
    '--color-primary-dark': '#6d28d9',
    '--color-primary-darker': '#5b21b6',
    '--color-info': '#7c3aed',
    '--color-info-light': '#a78bfa',
    '--color-info-bg': '#f3e8ff',
    '--color-bg-layout': '#f6f3ff',
    '--color-bg-container': '#ffffff',
    '--color-bg-elevated': '#ffffff',
    '--color-bg-spotlight': '#faf5ff',
    '--color-text-primary': '#312e81',
    '--color-text-secondary': '#4c1d95',
    '--color-text-tertiary': '#6d28d9',
    '--color-border-base': '#ddd6fe',
    '--color-border-light': '#ede9fe',
    '--color-border-lighter': '#f5f3ff',
    '--color-sb-bg-start': '#2d1a4a',
    '--color-sb-bg-end': '#1f1035',
    '--color-sb-text': 'rgba(255, 255, 255, 0.9)',
    '--color-sb-text-hover': '#fff',
    '--color-sb-text-muted': 'rgba(255, 255, 255, 0.75)',
    '--color-sb-active-bg': 'rgba(124, 58, 237, 0.2)',
    '--color-sb-active-border': '#a78bfa',
    '--color-sb-border': 'rgba(255, 255, 255, 0.08)',
    '--color-header-bg-start': '#2d1a4a',
    '--color-header-bg-end': '#1f1035',
    '--color-header-border': 'rgba(255, 255, 255, 0.08)',
    '--color-header-text': '#fff',
    '--color-header-action-hover': 'rgba(255, 255, 255, 0.1)',
    '--color-user-avatar-bg': 'rgba(255, 255, 255, 0.2)',
    '--color-user-hover': 'rgba(255, 255, 255, 0.1)',
    '--color-legacy-bar-start': '#dc2626',
    '--color-legacy-bar-end': '#a855f7',
    '--color-legacy-bar-text': '#fff',
    '--color-legacy-bar-btn-bg': '#c084fc',
    '--color-legacy-bar-btn-text': '#1a1a1a',
    '--color-legacy-bar-btn-hover': '#d8b4fe',
    '--color-legacy-bar-note': 'rgba(255,255,255,0.95)',
  },
  pink: {
    '--color-primary': '#e84393',
    '--color-primary-light': '#f06292',
    '--color-primary-lighter': '#f48fb1',
    '--color-primary-lightest': '#fce4ec',
    '--color-primary-dark': '#d81b60',
    '--color-primary-darker': '#c2185b',
    '--color-info': '#e84393',
    '--color-info-light': '#f48fb1',
    '--color-info-bg': '#fce4ec',
    '--color-bg-layout': '#fef0f5',
    '--color-bg-container': '#ffffff',
    '--color-bg-elevated': '#ffffff',
    '--color-bg-spotlight': '#fff0f6',
    '--color-text-primary': '#3f3f46',
    '--color-text-secondary': '#6b3a5a',
    '--color-text-tertiary': '#9c6b87',
    '--color-border-base': '#f5c6d6',
    '--color-border-light': '#f8d6e3',
    '--color-border-lighter': '#fce4ec',
    '--color-sb-bg-start': '#4a1a2e',
    '--color-sb-bg-end': '#2d1020',
    '--color-sb-text': 'rgba(255, 255, 255, 0.9)',
    '--color-sb-text-hover': '#fff',
    '--color-sb-text-muted': 'rgba(255, 255, 255, 0.75)',
    '--color-sb-active-bg': 'rgba(232, 67, 147, 0.2)',
    '--color-sb-active-border': '#f06292',
    '--color-sb-border': 'rgba(255, 255, 255, 0.08)',
    '--color-header-bg-start': '#4a1a2e',
    '--color-header-bg-end': '#2d1020',
    '--color-header-border': 'rgba(255, 255, 255, 0.08)',
    '--color-header-text': '#ffe4ec',
    '--color-header-action-hover': 'rgba(255, 255, 255, 0.1)',
    '--color-user-avatar-bg': 'rgba(255, 255, 255, 0.2)',
    '--color-user-hover': 'rgba(255, 255, 255, 0.1)',
    '--color-legacy-bar-start': '#e84393',
    '--color-legacy-bar-end': '#d81b60',
    '--color-legacy-bar-text': '#fff',
    '--color-legacy-bar-btn-bg': '#f48fb1',
    '--color-legacy-bar-btn-text': '#4a1a2e',
    '--color-legacy-bar-btn-hover': '#f8bbd0',
    '--color-legacy-bar-note': 'rgba(255,228,236,0.95)',
  },
  warm: {
    '--color-primary': '#f97316',
    '--color-primary-light': '#fb923c',
    '--color-primary-lighter': '#fdba74',
    '--color-primary-lightest': '#fff7ed',
    '--color-primary-dark': '#ea580c',
    '--color-primary-darker': '#c2410c',
    '--color-info': '#f97316',
    '--color-info-light': '#fdba74',
    '--color-info-bg': '#fff7ed',
    '--color-bg-layout': '#fffaf5',
    '--color-bg-container': '#ffffff',
    '--color-bg-elevated': '#ffffff',
    '--color-bg-spotlight': '#fff3e8',
    '--color-text-primary': '#3f3f46',
    '--color-text-secondary': '#52525b',
    '--color-text-tertiary': '#71717a',
    '--color-border-base': '#fed7aa',
    '--color-border-light': '#ffedd5',
    '--color-border-lighter': '#fff4e6',
    '--color-sb-bg-start': '#3b2410',
    '--color-sb-bg-end': '#2a190b',
    '--color-sb-text': 'rgba(255, 255, 255, 0.9)',
    '--color-sb-text-hover': '#fff',
    '--color-sb-text-muted': 'rgba(255, 255, 255, 0.75)',
    '--color-sb-active-bg': 'rgba(249, 115, 22, 0.2)',
    '--color-sb-active-border': '#f97316',
    '--color-sb-border': 'rgba(255, 255, 255, 0.08)',
    '--color-header-bg-start': '#3b2410',
    '--color-header-bg-end': '#2a190b',
    '--color-header-border': 'rgba(255, 255, 255, 0.08)',
    '--color-header-text': '#fff',
    '--color-header-action-hover': 'rgba(255, 255, 255, 0.1)',
    '--color-user-avatar-bg': 'rgba(255, 255, 255, 0.2)',
    '--color-user-hover': 'rgba(255, 255, 255, 0.1)',
    '--color-legacy-bar-start': '#dc2626',
    '--color-legacy-bar-end': '#f97316',
    '--color-legacy-bar-text': '#fff',
    '--color-legacy-bar-btn-bg': '#fdba74',
    '--color-legacy-bar-btn-text': '#1a1a1a',
    '--color-legacy-bar-btn-hover': '#fed7aa',
    '--color-legacy-bar-note': 'rgba(255,255,255,0.95)',
  },
}

function applySkinStyle(styleKey) {
  const normalized = skinStyleVarMap[styleKey] ? styleKey : 'default'
  const root = document.documentElement
  const vars = skinStyleVarMap[normalized]
  Object.keys(vars).forEach((cssVar) => {
    root.style.setProperty(cssVar, vars[cssVar])
  })
  activeSkinStyle.value = normalized
}

function toggleSettingsPopover() {
  settingsPopoverOpen.value = !settingsPopoverOpen.value
}

async function openHomeLayoutSettings() {
  settingsPopoverOpen.value = false
  if (route.path === '/') {
    window.dispatchEvent(new CustomEvent('open-home-layout-settings'))
    return
  }
  await router.push({ path: '/', query: { homeLayoutSettings: String(Date.now()) } })
}

async function changeSkinStyle(styleKey) {
  applySkinStyle(styleKey)
  settingsPopoverOpen.value = false
  try {
    localStorage.setItem('skinStyle', activeSkinStyle.value)
  } catch {}
  const name = (currentUser.value?.name || currentUser.value?.userName || '').trim()
  if (!name) return
  try {
    await saveUserStyle({ name, skinStyle: activeSkinStyle.value })
  } catch (e) {
    console.warn('保存用户风格失败:', e)
  }
}

async function loadUserSkinStyle() {
  const name = (currentUser.value?.name || currentUser.value?.userName || '').trim()
  const localStyle = (() => {
    try {
      return localStorage.getItem('skinStyle') || ''
    } catch {
      return ''
    }
  })()
  if (!name) {
    applySkinStyle(localStyle || 'default')
    return
  }
  try {
    const res = await getUserStyle({ name })
    const serverStyle = (res?.skinStyle || '').trim()
    const finalStyle = skinStyleVarMap[serverStyle] ? serverStyle : (skinStyleVarMap[localStyle] ? localStyle : 'default')
    applySkinStyle(finalStyle)
    try {
      localStorage.setItem('skinStyle', finalStyle)
    } catch {}
  } catch {
    applySkinStyle(skinStyleVarMap[localStyle] ? localStyle : 'default')
  }
}

function toggleTodoPopover() {
  todoPopoverOpen.value = !todoPopoverOpen.value
  if (todoPopoverOpen.value) {
    refreshWorkplaceTodos()
  }
}

function openAllTodos() {
  todoPopoverOpen.value = false
  router.push('/attendance/pending-tasks')
}

async function onHeaderTodoAction(task) {
  await handleTodoAction(task)
  todoPopoverOpen.value = false
}

// 待办弹窗 - 系统通知选项卡
const todoActiveTab = ref('todo')
const todoNotifyList = ref([])
const todoNotifyLoading = ref(false)

async function switchToNotifyTab() {
  todoActiveTab.value = 'notify'
  if (todoNotifyList.value.length) return
  todoNotifyLoading.value = true
  try {
    const res = await listNotifications()
    todoNotifyList.value = (res && res.items) || []
  } catch { todoNotifyList.value = [] }
  finally { todoNotifyLoading.value = false }
}

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
// 系统管理员：webconfig.admin1，最高权限（等同部长 + dakaman + admin2）
const admin1 = ref('')
// 人事档案系统外链地址（webconfig.personnelArchiveUrl）
const personnelArchiveUrl = ref('')

// 是否显示员工在职管理入口（部长/副部长/科室主任/副主任 或 人事管理员 admin2 或 系统管理员 admin1）
const canShowEmployeeAdmin = computed(() => {
  const jb = (currentUser.value?.jb || '').trim()
  const name = (currentUser.value?.name || currentUser.value?.userName || '').trim()
  const a1 = (admin1.value || '').trim()
  if (a1 && name === a1) return true
  const isLeaderOrDept = isMinisterOrDeptLeader(jb)
  const isAdmin2 = (admin2.value || '').trim() && name === (admin2.value || '').trim()
  return isLeaderOrDept || isAdmin2
})

const canManageHxp = computed(() => {
  const name = (currentUser.value?.name || currentUser.value?.userName || '').trim()
  const a1 = (admin1.value || '').trim()
  const a2 = (admin2.value || '').trim()
  if ((a1 && name === a1) || (a2 && name === a2)) return true
  const jb = (currentUser.value?.jb || '').trim()
  return isMinisterLevel(jb)
})

// 是否显示管理驾驶舱（部长/副部长、综合技术室主任/副主任、admin1、admin2）
const canSeeLeaderDashboard = computed(() => {
  const name = (currentUser.value?.name || currentUser.value?.userName || '').trim()
  const jb = (currentUser.value?.jb || '').trim()
  const lsys = (currentUser.value?.dept || currentUser.value?.lsys || '').trim()
  return canAccessLeaderDashboard({
    name,
    jb,
    lsys,
    admin1: admin1.value,
    admin2: admin2.value,
  })
})

// 其他绩效激励统计：全员可访问，页面内按权限显示本人/本室/全部门

// 是否显示数据库表管理入口（仅 webconfig.admin1 系统管理员）
const canAccessDbManager = ref(false)

const canAccessInboxEmails = computed(() => {
  if (canAccessDbManager.value) return true
  const jb = (currentUser.value?.jb || '').trim()
  return isMinisterOrDeptLeader(jb)
})

// 是否显示打卡数据上传（webconfig.dakaman 或 系统管理员 admin1）
const canShowUpload = computed(() => {
  const name = (currentUser.value?.name || currentUser.value?.userName || '').trim()
  const d = (dakaman.value || '').trim()
  const a1 = (admin1.value || '').trim()
  return (!!d && name === d) || (!!a1 && name === a1)
})

// 是否显示考勤异常管理（部长/副部长、班组长/主任/副主任、打卡管理员、系统管理员 admin1）
const canShowAttendanceExceptions = computed(() => {
  const jb = (currentUser.value?.jb || '').trim()
  const name = (currentUser.value?.name || currentUser.value?.userName || '').trim()
  const a1 = (admin1.value || '').trim()
  const d = (dakaman.value || '').trim()
  if (a1 && name === a1) return true
  if (d && name === d) return true
  return isMinisterOrDeptLeader(jb)
})

// "其他部门成员"：仅可使用文件编号功能，隐藏其余所有侧边栏入口
const isOtherDeptUser = computed(() => {
  const lsys = (currentUser.value?.dept || currentUser.value?.lsys || '').trim()
  return lsys === '其他部门成员'
})

const canUseRotorBladeBalance = computed(() => {
  const lsys = (currentUser.value?.lsys || currentUser.value?.dept || '').trim()
  return lsys === '焊接工艺室' || lsys === '部办'
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
  if (todoBellWrapRef.value && !todoBellWrapRef.value.contains(e.target)) {
    todoPopoverOpen.value = false
    todoActiveTab.value = 'todo'
  }
  if (settingsWrapRef.value && !settingsWrapRef.value.contains(e.target)) {
    settingsPopoverOpen.value = false
  }
}

// 退出登录
const handleLogout = () => {
  localStorage.removeItem('userInfo')
  localStorage.removeItem('skinStyle')
  currentUser.value = { name: '', dept: '', username: '' }
  canAccessDbManager.value = false
  admin2.value = ''
  admin1.value = ''
  showUserMenu.value = false
  applySkinStyle('default')
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
        getDbManagerPermission({ current_user: name }).then(res => {
          canAccessDbManager.value = !!(res && res.canAccess)
        }).catch(() => { canAccessDbManager.value = false })
      } else {
        canAccessDbManager.value = false
      }
    } else {
      canAccessDbManager.value = false
    }
  } catch (error) {
    console.error('加载用户信息失败:', error)
    canAccessDbManager.value = false
  }
}

// 路由变化时重新加载用户信息（登录后跳转时 currentUser 能正确更新）
watch(() => route.path, () => {
  loadUserInfo()
  if (route.path === '/login') {
    applySkinStyle('default')
  } else {
    loadUserSkinStyle()
  }
  if (route.path !== '/login') {
    refreshWorkplaceTodos()
  }
}, { immediate: true })

// 首次登录介绍弹窗：当用户 showIntro 为 true 且当前在主布局时显示
const showIntroModal = ref(false)
watch(
  () => [route.path, currentUser.value?.showIntro],
  () => {
    if (route.path === '/login') {
      showIntroModal.value = false
      return
    }
    if (currentUser.value?.showIntro === true) {
      showIntroModal.value = true
    }
  },
  { immediate: true }
)

async function closeIntroModal() {
  showIntroModal.value = false
  const name = (currentUser.value?.name || currentUser.value?.userName || '').trim()
  if (!name) return
  try {
    await setLoginStatus({ name })
  } catch (e) {
    console.warn('设置登录状态失败:', e)
  }
  try {
    const raw = localStorage.getItem('userInfo')
    if (raw) {
      const u = JSON.parse(raw)
      u.showIntro = false
      localStorage.setItem('userInfo', JSON.stringify(u))
      currentUser.value = u
    }
  } catch (e) {
    console.warn('更新本地用户信息失败:', e)
  }
}

// 更新通知弹窗（多条未读）
const showNotificationModal = ref(false)
const unreadNotifications = ref([])

function escapeHtml(text) {
  if (!text) return ''
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')
}

watch(
  () => [route.path, currentUser.value?.unreadNotifications, showIntroModal.value],
  () => {
    if (route.path === '/login') {
      showNotificationModal.value = false
      return
    }
    if (showIntroModal.value) return
    const list = currentUser.value?.unreadNotifications
    if (Array.isArray(list) && list.length > 0) {
      unreadNotifications.value = list
      showNotificationModal.value = true
    }
  },
  { immediate: true }
)

async function closeNotificationModal() {
  showNotificationModal.value = false
  const name = (currentUser.value?.name || currentUser.value?.userName || '').trim()
  const maxId = unreadNotifications.value.length
    ? Math.max(...unreadNotifications.value.map(n => n.id))
    : 0
  if (name && maxId > 0) {
    try {
      await dismissNotification({ name, max_id: maxId })
    } catch (e) {
      console.warn('标记通知已读失败:', e)
    }
  }
  try {
    const raw = localStorage.getItem('userInfo')
    if (raw) {
      const u = JSON.parse(raw)
      u.unreadNotifications = []
      localStorage.setItem('userInfo', JSON.stringify(u))
      currentUser.value = u
    }
  } catch (e) {
    console.warn('更新本地用户信息失败:', e)
  }
  unreadNotifications.value = []
}

// 加载打卡/人事/系统管理员配置（dakaman、admin2、admin1）
const loadUploadConfig = () => {
  getUploadConfig().then(res => {
    if (res && res.success) {
      if (res.dakaman != null) dakaman.value = res.dakaman || ''
      if (res.admin2 != null) admin2.value = res.admin2 || ''
      if (res.admin1 != null) admin1.value = res.admin1 || ''
      if (res.personnelArchiveUrl != null) personnelArchiveUrl.value = String(res.personnelArchiveUrl).trim()
    }
  }).catch(() => { dakaman.value = ''; admin2.value = ''; admin1.value = ''; personnelArchiveUrl.value = '' })
}

onMounted(() => {
  document.addEventListener('click', onDocumentClick)
  loadUploadConfig()
})

onUnmounted(() => {
  document.removeEventListener('click', onDocumentClick)
})

// 跳转人事档案系统（外链，需独立账号登录）
function goPersonnelArchive() {
  const url = (personnelArchiveUrl.value || '').trim()
  if (url) {
    window.open(url, '_blank', 'noopener,noreferrer')
  } else {
    alert('人事档案系统链接未配置，请联系管理员')
  }
}

// 跳转思想汇报管理（单点登录）
async function goSixianghuibao() {
  const name = (currentUser.value?.name || currentUser.value?.userName || '').trim()
  if (!name) {
    alert('请先登录')
    return
  }
  try {
    const res = await getSSOLink('sixianghuibao', name)
    if (res && res.success && res.url) {
      window.open(res.url, '_blank', 'noopener,noreferrer')
    } else {
      alert(res?.detail || '获取思想汇报系统链接失败，请联系管理员')
    }
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '跳转失败'
    alert(typeof msg === 'string' ? msg : (Array.isArray(msg) ? msg.join(' ') : '跳转失败'))
  }
}

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
  background: linear-gradient(180deg, var(--color-sb-bg-start) 0%, var(--color-sb-bg-end) 100%);
  color: var(--color-sb-text);
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
  border-bottom: 1px solid var(--color-sb-border);
  flex-shrink: 0;
}

.sidebar-logo {
  width: 28px;
  height: 28px;
  color: var(--color-sb-text-hover);
  flex-shrink: 0;
}

.sidebar-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-header-text);
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
  color: var(--color-sb-text-muted);
  text-decoration: none;
  transition: all 0.2s ease;
  border-left: 3px solid transparent;
}

.sidebar-item:hover {
  color: var(--color-sb-text-hover);
  background: var(--color-sb-active-bg);
}

.sidebar-item-active {
  color: var(--color-sb-text-hover);
  background: var(--color-sb-active-bg);
  border-left-color: var(--color-sb-active-border);
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
  background: linear-gradient(180deg, var(--color-header-bg-start) 0%, var(--color-header-bg-end) 100%);
  border-bottom: 1px solid var(--color-header-border);
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
  color: var(--color-header-text);
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
  background: var(--color-header-action-hover);
}

.action-icon {
  width: 20px;
  height: 20px;
  color: var(--color-header-text);
}

.badge-dot {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 8px;
  height: 8px;
  background: var(--color-error, #ef4444);
  border-radius: 50%;
  border: 2px solid var(--color-header-bg-end);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.2);
}

.todo-bell-wrap {
  position: relative;
}

.settings-wrap {
  position: relative;
}

.settings-popover {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 248px;
  padding: 0 0 10px;
  background: var(--color-bg-container);
  border: 1px solid var(--color-border-lighter);
  border-radius: 14px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.14);
  z-index: 1000;
  overflow: hidden;
}

.settings-popover__header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border-lighter);
  margin-bottom: 8px;
}

.settings-popover__icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  color: var(--color-text-tertiary);
}

.settings-style-grid {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0 10px;
}

.settings-style-card {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--color-text-primary);
  cursor: pointer;
  transition: all .2s ease;
  position: relative;
}

.settings-style-card:hover {
  background: var(--color-primary-lightest);
}

.settings-style-card.active {
  background: var(--color-primary-lightest);
  box-shadow: inset 0 0 0 1.5px var(--color-primary);
}

.settings-style-card__preview {
  width: 32px;
  height: 22px;
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.settings-style-card__bar {
  flex: 1;
  width: 100%;
}

.settings-style-card__label {
  font-size: 13px;
  font-weight: 500;
  flex: 1;
  text-align: left;
}

.settings-style-card__check {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.settings-popover__divider {
  height: 1px;
  margin: 10px 10px 8px;
  background: var(--color-border-lighter);
}

.settings-action-card {
  width: calc(100% - 20px);
  margin: 0 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--color-text-primary);
  cursor: pointer;
  text-align: left;
  transition: background .2s ease;
}

.settings-action-card:hover {
  background: var(--color-primary-lightest);
}

.settings-action-card__icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--color-primary);
  background: var(--color-primary-lightest);
}

.settings-action-card__icon svg {
  width: 18px;
  height: 18px;
}

.settings-action-card__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.settings-action-card__body strong {
  font-size: 13px;
  font-weight: 600;
}

.settings-action-card__body small {
  font-size: 12px;
  color: var(--color-text-tertiary);
  white-space: nowrap;
}

.todo-popover {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: min(400px, calc(100vw - 48px));
  max-height: min(440px, 72vh);
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid var(--color-border-lighter, #e5e7eb);
  border-radius: var(--radius-md, 10px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
  z-index: 1000;
  overflow: hidden;
}

.todo-popover__header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--color-border-lighter, #e5e7eb);
  background: #f9fafb;
  flex-shrink: 0;
}

.todo-popover__title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.todo-popover__count {
  font-size: 12px;
  font-weight: 600;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #fee2e2;
  color: #b91c1c;
  border-radius: 999px;
}

.todo-popover__link {
  margin-left: auto;
  border: none;
  background: none;
  font-size: 13px;
  font-weight: 500;
  color: #6366f1;
  cursor: pointer;
  padding: 4px 0;
}

.todo-popover__link:hover {
  text-decoration: underline;
}

.todo-popover__body {
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.todo-popover-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.todo-popover-item {
  padding: 10px 14px;
  border-bottom: 1px solid #f3f4f6;
}

.todo-popover-item:last-child {
  border-bottom: none;
}

.todo-popover-item__top {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.todo-popover-item__type {
  font-size: 11px;
  font-weight: 600;
  color: #6366f1;
  text-transform: none;
}

.todo-popover-item__desc {
  margin: 0;
  font-size: 13px;
  color: #374151;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.todo-popover-item__bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.todo-popover-item__meta {
  font-size: 12px;
  color: #9ca3af;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.todo-popover-item__btn {
  flex-shrink: 0;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  background: #6366f1;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.todo-popover-item__btn:hover {
  background: #4f46e5;
}

.todo-popover-empty {
  padding: 28px 16px;
  text-align: center;
  font-size: 14px;
  color: #9ca3af;
}

/* 待办弹窗选项卡 */
.todo-popover__tabs {
  display: flex;
  gap: 0;
}
.todo-popover__tab {
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all .15s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}
.todo-popover__tab:hover {
  color: #374151;
}
.todo-popover__tab.active {
  color: #4f46e5;
  border-bottom-color: #4f46e5;
}
.todo-popover__tab .todo-popover__count {
  margin: 0;
}

/* 更新日志弹窗 */
.changelog-wrap {
  position: relative;
}
.changelog-popover {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 400px;
  max-height: 480px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15), 0 2px 10px rgba(0, 0, 0, 0.08);
  z-index: 200;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.changelog-popover__header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid #f3f4f6;
  flex-shrink: 0;
}
.changelog-popover__title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}
.changelog-popover__count {
  font-size: 12px;
  font-weight: 600;
  min-width: 22px;
  text-align: center;
  padding: 1px 7px;
  color: #4f46e5;
  background: #eef2ff;
  border-radius: 999px;
}
.changelog-popover__body {
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}
.changelog-popover__empty {
  padding: 28px 16px;
  text-align: center;
  font-size: 14px;
  color: #9ca3af;
}
.changelog-list {
  padding: 0;
}
.changelog-item {
  padding: 12px 16px;
  border-bottom: 1px solid #f3f4f6;
}
.changelog-item:last-child {
  border-bottom: none;
}
.changelog-item__time {
  font-size: 11px;
  color: #9ca3af;
  margin-bottom: 4px;
}
.changelog-item__content {
  font-size: 13px;
  color: #374151;
  line-height: 1.7;
  word-break: break-word;
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
  background: var(--color-user-hover);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-circle);
  background: var(--color-user-avatar-bg);
  color: var(--color-header-text);
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
  color: var(--color-header-text);
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
    border-bottom-color: var(--color-sb-active-border);
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

/* 首次登录介绍弹窗 */
.intro-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: var(--spacing-xl);
}
.intro-modal {
  background: var(--color-bg-card, #fff);
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
  max-width: 520px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}
.intro-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-xl) var(--spacing-xl) 0;
}
.intro-modal-title {
  margin: 0;
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}
.intro-modal-close {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--color-text-tertiary);
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  border-radius: 6px;
}
.intro-modal-close:hover {
  background: var(--color-bg-spotlight);
  color: var(--color-text-primary);
}
.intro-modal-body {
  padding: var(--spacing-xl);
  overflow-y: auto;
}
.intro-section {
  margin-bottom: var(--spacing-lg);
}
.intro-section:last-child {
  margin-bottom: 0;
}
.intro-section h3 {
  margin: 0 0 var(--spacing-sm);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}
.intro-section p {
  margin: 0 0 var(--spacing-sm);
  font-size: var(--font-size-sm);
  line-height: 1.6;
  color: var(--color-text-secondary);
}
.intro-section p:last-child {
  margin-bottom: 0;
}
.intro-notice {
  padding: var(--spacing-base);
  background: #fef2f2;
  border-radius: 8px;
  border-left: 4px solid #dc2626;
}
.intro-notice h3,
.intro-notice p {
  color: #b91c1c;
  font-weight: 500;
}
.intro-notice p strong {
  color: #991b1b;
}
.intro-contact {
  margin-top: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: #7f1d1d !important;
}
.intro-modal-footer {
  padding: var(--spacing-lg) var(--spacing-xl) var(--spacing-xl);
  border-top: 1px solid var(--color-border-lighter);
}
.intro-modal-footer .btn {
  width: 100%;
  padding: 10px 20px;
}

/* 更新通知弹窗 */
.notification-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 10010;
  background: rgba(0, 0, 0, .55);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: modalFadeIn .2s ease;
}
.notification-modal {
  background: var(--color-bg-card, #fff);
  border-radius: 16px;
  width: 92%;
  max-width: 500px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 12px 48px rgba(0, 0, 0, .25);
  overflow: hidden;
  animation: modalSlideUp .25s ease;
}
.notification-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}
.notification-modal-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0;
}
.notification-modal-close {
  background: none;
  border: none;
  color: rgba(255,255,255,.8);
  font-size: 24px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}
.notification-modal-close:hover {
  color: #fff;
}
.notification-count {
  font-size: 13px;
  font-weight: 500;
  opacity: .85;
  margin-left: 8px;
}
.notification-modal-body {
  padding: 20px 24px;
  font-size: 14px;
  line-height: 1.9;
  color: var(--color-text-primary, #2d3748);
  overflow-y: auto;
  flex: 1;
  max-height: 55vh;
}
.notification-item-border {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed var(--color-border, #e2e8f0);
}
.notification-item-time {
  font-size: 12px;
  color: var(--color-text-tertiary, #a0aec0);
  margin-bottom: 6px;
}
.notification-item-content {
  line-height: 1.8;
}
.notification-modal-footer {
  padding: 14px 24px 20px;
  border-top: 1px solid var(--color-border-lighter, #edf2f7);
  display: flex;
  align-items: center;
  justify-content: flex-end;
}
.notification-modal-footer .btn {
  padding: 8px 28px;
}

</style>
