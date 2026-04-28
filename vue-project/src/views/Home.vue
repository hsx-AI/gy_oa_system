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
              <span class="dashboard-card__badge">{{ totalBadgeCount }}</span>
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
                  <button type="button" class="todo-item__btn" @click="handleTodoAction(task)">
                    {{ task.isHxpNotice ? '已读' : (task.isHxpApproval ? '去审批' : (task.isPersonnel ? '去处理' : (task.isSixianghuibao ? (task.btnLabel || '去处理') : (task.isReturnReminder ? '去登记' : (task.btnLabel || '处理'))))) }}
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

    <!-- 常用功能 -->
    <section class="home-favorites-section">
      <div class="favorites-header">
        <h2 class="favorites-title">
          <svg class="favorites-title-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
          常用功能
        </h2>
        <button type="button" class="favorites-edit-btn" @click="openFavEditor" title="自定义常用功能">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          自定义
        </button>
      </div>
      <div class="favorites-grid">
        <button
          v-for="fav in favFeatures"
          :key="fav.id"
          type="button"
          class="fav-card"
          @click="navigateTo(fav)"
        >
          <span class="fav-card__icon" :style="{ background: fav.color }">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path :d="fav.iconPath" /></svg>
          </span>
          <span class="fav-card__label">{{ fav.title }}</span>
        </button>
      </div>
    </section>

    <!-- 常用功能编辑弹窗 -->
    <div v-if="favEditorVisible" class="modal-overlay" @click.self="closeFavEditor">
      <div class="fav-editor-modal">
        <div class="fav-editor-header">
          <h3>自定义常用功能</h3>
          <button type="button" class="fav-editor-close" @click="closeFavEditor">&times;</button>
        </div>
        <p class="fav-editor-hint">勾选要显示在首页的功能（最多 8 个）</p>
        <div class="fav-editor-groups">
          <div v-for="group in featureGroups" :key="group.title" class="fav-editor-group">
            <h4 class="fav-editor-group-title">{{ group.title }}</h4>
            <div class="fav-editor-items">
              <label
                v-for="item in group.items"
                :key="item.id"
                class="fav-editor-item"
                :class="{ checked: favEditorSet.has(item.id), disabled: !favEditorSet.has(item.id) && favEditorSet.size >= 8 }"
              >
                <input
                  type="checkbox"
                  :checked="favEditorSet.has(item.id)"
                  :disabled="!favEditorSet.has(item.id) && favEditorSet.size >= 8"
                  @change="toggleFavEditorItem(item.id)"
                />
                <span class="fav-editor-item__icon" :style="{ background: item.color }">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path :d="item.iconPath" /></svg>
                </span>
                <span class="fav-editor-item__name">{{ item.title }}</span>
              </label>
            </div>
          </div>
        </div>
        <div class="fav-editor-footer">
          <span class="fav-editor-count">已选 {{ favEditorSet.size }} / 8</span>
          <div class="fav-editor-btns">
            <button type="button" class="btn-fav-cancel" @click="closeFavEditor">取消</button>
            <button type="button" class="btn-fav-save" @click="saveFavEditor">保存</button>
          </div>
        </div>
      </div>
    </div>

    <section v-if="canAccessInboxBoard" class="home-ai-task-section">
      <article class="dashboard-card ai-task-card">
        <header class="dashboard-card__header ai-task-card__header">
          <h2 class="dashboard-card__title">
            <span class="dashboard-card__icon dashboard-card__icon--ai" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
                <circle cx="12" cy="12" r="4"/>
              </svg>
            </span>
            <span class="dashboard-card__title-text">AI 待办任务看板</span>
            <span class="dashboard-card__badge">{{ inboxTaskStats.taskCount }}</span>
          </h2>
          <div class="ai-task-actions">
            <span class="ai-task-stat">待分析 {{ inboxTaskStats.pending }}</span>
            <span class="ai-task-stat" :class="{ 'ai-task-stat--warn': inboxTaskStats.failed > 0 }">失败 {{ inboxTaskStats.failed }}</span>
            <button type="button" class="ai-task-icon-btn" :disabled="inboxSyncing" :title="inboxSyncing ? '同步中…' : '同步邮箱并刷新'" @click="syncAndRefresh">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :class="{ spinning: inboxSyncing }">
                <polyline points="23 4 23 10 17 10"/>
                <polyline points="1 20 1 14 7 14"/>
                <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4-4.64 4.36A9 9 0 0 1 3.51 15"/>
              </svg>
            </button>
            <router-link to="/admin/inbox-emails" class="ai-task-viewall-btn">
              查看全部
            </router-link>
          </div>
        </header>

        <div v-if="inboxTaskMsg" class="ai-task-toast" :class="inboxTaskMsgType">{{ inboxTaskMsg }}</div>

        <div class="ai-task-body">
          <div v-if="!inboxConfigured && !inboxTaskLoading" class="ai-task-unconfigured">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="ai-task-unconfigured__icon">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <p>您尚未配置个人企业邮箱授权码，无法同步和分析邮件任务。</p>
            <ol class="ai-task-unconfigured__steps">
              <li>点击下方按钮，填写您的企业邮箱地址和 IMAP 授权码</li>
              <li>在企业邮箱客户端中，将需要处理的邮件标记为<strong>红旗（FLAGGED）</strong>，系统将自动同步并由 AI 提取待办任务</li>
            </ol>
            <router-link to="/admin/inbox-emails?tab=emails" class="ai-task-unconfigured__link">
              前往配置邮箱 →
            </router-link>
          </div>
          <div v-else-if="!inboxTasks.length && !inboxTaskLoading" class="dashboard-empty">
            <p>暂无识别出的邮件待办任务</p>
          </div>
          <div v-else-if="inboxTaskLoading" class="dashboard-empty">
            <p>加载中...</p>
          </div>
          <div
            v-else
            ref="inboxTaskBoardRef"
            class="ai-task-marquee"
            @mouseenter="inboxTaskMarqueePaused = true"
            @mouseleave="inboxTaskMarqueePaused = false"
            @wheel="onInboxTaskWheel"
          >
            <div class="ai-task-track" :class="{ paused: inboxTaskMarqueePaused, 'no-anim': inboxTasks.length <= 2 }">
              <button
                v-for="(task, idx) in inboxDisplayTasks"
                :key="`${task.id}-${idx}`"
                type="button"
                class="ai-mail-task"
                @click="openInboxTask(task.id)"
              >
                <span class="ai-mail-task__top">
                  <span class="ai-mail-task__deadline" :class="deadlineClass(task.taskDeadline)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="10" />
                      <polyline points="12 6 12 12 16 14" />
                    </svg>
                    {{ task.taskDeadline || '未指定截止时间' }}
                    <span v-if="task.taskDeadline && deadlineCountdown(task.taskDeadline)" class="ai-mail-task__countdown">{{ deadlineCountdown(task.taskDeadline) }}</span>
                  </span>
                  <span class="ai-mail-task__from" :title="task.from">{{ shortFrom(task.from) }}</span>
                  <span
                    class="ai-mail-task__complete"
                    role="button"
                    title="标记已完成（去除旗帜并删除记录）"
                    @click.stop="completeInboxTaskAction(task.id)"
                    :class="{ disabled: inboxCompletingId === task.id }"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/></svg>
                    {{ inboxCompletingId === task.id ? '处理中…' : '待完成' }}
                  </span>
                </span>
                <span class="ai-mail-task__summary" :title="task.taskSummary">{{ task.taskSummary }}</span>
                <span class="ai-mail-task__sub">
                  <span :title="task.subject">{{ task.subject || '（无主题）' }}</span>
                  <span>{{ task.emailDate || task.receivedAt }}</span>
                </span>
              </button>
            </div>
          </div>
        </div>
      </article>
    </section>

    <!-- 邮件详情弹窗 -->
    <div v-if="inboxDetailOpen" class="inbox-detail-overlay" @click.self="closeInboxDetail">
      <div class="inbox-detail-modal">
        <div class="inbox-detail-modal__header">
          <h2 class="inbox-detail-modal__title">邮件详情</h2>
          <button type="button" class="inbox-detail-modal__close" aria-label="关闭" @click="closeInboxDetail">×</button>
        </div>
        <div class="inbox-detail-modal__body" v-if="inboxDetailItem">
          <div class="inbox-detail-meta">
            <div class="inbox-detail-meta__row"><span class="inbox-detail-meta__label">主题</span><span>{{ inboxDetailItem.subject || '（无主题）' }}</span></div>
            <div class="inbox-detail-meta__row"><span class="inbox-detail-meta__label">发件人</span><span>{{ inboxDetailItem.from || '—' }}</span></div>
            <div class="inbox-detail-meta__row"><span class="inbox-detail-meta__label">收件人</span><span>{{ inboxDetailItem.to || '—' }}</span></div>
            <div class="inbox-detail-meta__row"><span class="inbox-detail-meta__label">抄送</span><span>{{ inboxDetailItem.cc || '—' }}</span></div>
            <div class="inbox-detail-meta__row"><span class="inbox-detail-meta__label">发件时间</span><span class="mono">{{ inboxDetailItem.emailDate || '—' }}</span></div>
          </div>
          <div class="inbox-detail-toggle">
            <button type="button" :class="{ active: inboxDetailBodyMode === 'html' }" :disabled="!inboxDetailItem.bodyHtml" @click="inboxDetailBodyMode = 'html'">HTML</button>
            <button type="button" :class="{ active: inboxDetailBodyMode === 'text' }" @click="inboxDetailBodyMode = 'text'">纯文本</button>
          </div>
          <div class="inbox-detail-body">
            <iframe v-if="inboxDetailBodyMode === 'html' && inboxDetailItem.bodyHtml" class="inbox-detail-iframe" :srcdoc="inboxDetailSafeHtml" sandbox=""></iframe>
            <pre v-else class="inbox-detail-text">{{ inboxDetailItem.bodyText || '（无正文）' }}</pre>
          </div>
        </div>
        <div class="inbox-detail-modal__body" v-else>
          <p>加载中…</p>
        </div>
      </div>
    </div>

    <!-- 吐槽墙预览 -->
    <section class="home-wall-section">
      <article class="dashboard-card wall-preview-card">
        <header class="dashboard-card__header wall-preview-card__header">
          <h2 class="dashboard-card__title">
            <span class="dashboard-card__icon dashboard-card__icon--wall" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
            </span>
            <span class="dashboard-card__title-text">吐槽墙</span>
            <span class="dashboard-card__badge" v-if="wallList.length">{{ wallList.length }}</span>
          </h2>
          <div class="wall-preview-actions">
            <button type="button" class="wall-preview-refresh" title="刷新" @click="loadWallList">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23 4 23 10 17 10"/>
                <polyline points="1 20 1 14 7 14"/>
                <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4-4.64 4.36A9 9 0 0 1 3.51 15"/>
              </svg>
            </button>
            <router-link to="/feedback" class="wall-preview-viewall">
              查看全部
            </router-link>
          </div>
        </header>
        <div class="wall-preview-body">
          <div v-if="wallLoading" class="dashboard-empty"><p>加载中...</p></div>
          <div v-else-if="!wallDisplayCards.length" class="dashboard-empty"><p>暂无吐槽</p></div>
          <div v-else class="wall-preview-grid">
            <div
              v-for="card in wallDisplayCards"
              :key="card.id"
              class="wall-mini-card"
              :style="{ background: card._bg, '--rot': card._rotate + 'deg' }"
              @click="router.push('/feedback')"
            >
              <span :class="['wall-mini-badge', `wmb-${card.resolved || 0}`]">
                {{ wallResolveLabel(card.resolved) }}
              </span>
              <p class="wall-mini-body">{{ card.content }}</p>
              <div v-if="card.replies?.length" class="wall-mini-reply">
                {{ card.replies[card.replies.length - 1].replyBy }} 回复：{{ (card.replies[card.replies.length - 1].replyContent || '').slice(0, 12) }}{{ (card.replies[card.replies.length - 1].replyContent || '').length > 12 ? '…' : '' }}
              </div>
              <div class="wall-mini-foot">
                <span class="wall-mini-avatar">匿</span>
                <span class="wall-mini-dept">匿名</span>
                <span
                  class="wall-mini-like"
                  :class="{ liked: wallLikedIds.has(card.id), animating: wallLikeAnimating.has(card.id) }"
                  @click.stop="doWallLike(card.id)"
                >
                  <span class="wall-like-icon">👍</span>
                  <span class="wall-like-count">{{ card.likeCount || 0 }}</span>
                </span>
              </div>
            </div>
          </div>
        </div>
      </article>
    </section>

    <!-- 重要信息审阅（仅部长可见） -->
    <section v-if="isBuzhang && briefingItems.length > 0" class="briefing-section">
      <article class="dashboard-card dashboard-card--briefing">
        <header class="dashboard-card__header">
          <h2 class="dashboard-card__title">
            <span class="dashboard-card__icon dashboard-card__icon--briefing" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
              </svg>
            </span>
            <span class="dashboard-card__title-text">重要信息审阅</span>
            <span class="dashboard-card__badge">{{ briefingFilteredItems.length }}</span>
          </h2>
          <div class="briefing-header-right">
            <div class="briefing-filter-tabs">
              <button
                v-for="f in briefingFilterOptions"
                :key="f.value"
                type="button"
                class="briefing-filter-tab"
                :class="{ active: briefingFilter === f.value }"
                @click="briefingFilter = f.value"
              >{{ f.label }}</button>
            </div>
            <select v-model="briefingDays" class="briefing-days-select" @change="fetchBriefing">
              <option :value="3">最近3天</option>
              <option :value="7">最近7天</option>
              <option :value="30">最近30天</option>
            </select>
            <button type="button" class="briefing-viewall-btn" @click="showBriefingModal = true">查看全部</button>
          </div>
        </header>
        <div
          class="briefing-marquee"
          :class="{ 'briefing-marquee--hover': briefingHover }"
          @mouseenter="onMarqueeEnter"
          @mouseleave="onMarqueeLeave"
          @wheel.prevent="onMarqueeWheel"
        >
          <div class="briefing-track" ref="briefingTrackRef">
            <div
              v-for="(item, idx) in briefingItemsDup"
              :key="idx"
              class="briefing-item"
              :class="'briefing-item--' + item.type"
              @click="goBriefingDetail(item)"
            >
              <span class="briefing-tag">{{ briefingTagLabel(item.type) }}</span>
              <span class="briefing-text">{{ item.text }}</span>
              <span class="briefing-arrow">→</span>
            </div>
            <div v-if="!briefingItemsDup.length" class="briefing-empty-inline">当前筛选下暂无信息</div>
          </div>
        </div>
      </article>
    </section>

    <!-- 信息审阅全部列表弹窗 -->
    <div v-if="showBriefingModal" class="modal-overlay" @click.self="showBriefingModal = false">
      <div class="briefing-modal">
        <div class="briefing-modal__header">
          <h2>重要信息审阅（最近{{ briefingDays }}天，共{{ briefingFilteredItems.length }}条）</h2>
          <button type="button" class="briefing-modal__close" @click="showBriefingModal = false">&times;</button>
        </div>
        <div class="briefing-modal__body">
          <div
            v-for="(item, idx) in briefingFilteredItems"
            :key="idx"
            class="briefing-modal__item"
            :class="'briefing-modal__item--' + item.type"
            @click="goBriefingDetail(item); showBriefingModal = false"
          >
            <span class="briefing-modal__idx">{{ idx + 1 }}</span>
            <span class="briefing-tag">{{ briefingTagLabel(item.type) }}</span>
            <span class="briefing-modal__text">{{ item.text }}</span>
          </div>
          <p v-if="!briefingFilteredItems.length" class="briefing-modal__empty">当前筛选下暂无信息</p>
        </div>
      </div>
    </div>

    <!-- 功能快捷入口：分类文件夹 -->
    <div class="container shortcuts-container">
      <section class="shortcuts-section">
        <header class="shortcuts-header">
          <h2 class="section-title">快捷入口</h2>
          <span class="shortcuts-count">{{ visibleFeatureCount }} 项功能</span>
        </header>
        <div class="shortcut-folders">
          <button
            v-for="group in featureGroups"
            :key="group.title"
            type="button"
            class="shortcut-folder"
            @click="openShortcutGroup(group)"
          >
            <span class="shortcut-folder__icon" :style="{ background: folderAccent(group) }">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z"/>
              </svg>
            </span>
            <span class="shortcut-folder__body">
              <strong>{{ group.title }}</strong>
              <small>{{ group.items.length }} 项</small>
            </span>
            <span class="shortcut-folder__arrow">→</span>
          </button>
        </div>
      </section>
    </div>

    <div v-if="selectedShortcutGroup" class="modal-overlay" @click.self="closeShortcutGroup">
      <div class="shortcut-modal">
        <div class="shortcut-modal__header">
          <div>
            <h2>{{ selectedShortcutGroup.title }}</h2>
            <p>{{ selectedShortcutGroup.items.length }} 项可用功能</p>
          </div>
          <button type="button" class="shortcut-modal__close" aria-label="关闭" @click="closeShortcutGroup">&times;</button>
        </div>
        <div class="shortcut-modal__grid">
          <button
            v-for="feature in selectedShortcutGroup.items"
            :key="feature.id"
            type="button"
            class="shortcut-app"
            @click="navigateFromShortcut(feature)"
          >
            <span class="shortcut-app__icon" :style="{ background: feature.color }">
              <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path :d="feature.iconPath" />
              </svg>
            </span>
            <span class="shortcut-app__text">
              <strong>{{ feature.title }}</strong>
              <small>{{ feature.description }}</small>
            </span>
            <span v-if="feature.tag" class="shortcut-app__tag">{{ feature.tag }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  getLeaveList,
  getOvertimeList,
  getBusinessTripList,
  getUploadConfig,
} from '@/api/attendance'
import { getLeaderBriefing } from '@/api/admin'
import { getWallList, likeWall, wallImageUrl } from '@/api/feedback'
import { getDbManagerPermission } from '@/api/dbManager'
import { analyzeInboxEmails, listInboxTasks, getInboxConfig, completeInboxTask, syncInboxEmails, getInboxEmailDetail } from '@/api/inboxEmail'
import { getSSOLink } from '@/api/sso'
import { useWorkplaceTodos, refreshWorkplaceTodos } from '@/composables/useWorkplaceTodos'
import { isMinisterLevel, isMinisterOrDeptLeader, isDirectorLevel, jbMatch } from '@/utils/roleMatch'
const router = useRouter()

const {
  displayTodoList,
  totalBadgeCount,
  todoLoading,
  tripReturnLoading,
  handleTodoAction,
} = useWorkplaceTodos()

const dakaman = ref('')
const admin2 = ref('')
const admin1 = ref('')
const personnelArchiveUrl = ref('')
const canAccessDbManager = ref(false)
const canAccessInboxBoard = computed(() => {
  if (canAccessDbManager.value) return true
  const jb = (userJb.value || '').trim()
  return isMinisterOrDeptLeader(jb)
})
const selectedShortcutGroup = ref(null)
const inboxTasks = ref([])
const inboxTaskStats = ref({ pending: 0, failed: 0, taskCount: 0, total: 0 })
const inboxTaskLoading = ref(false)
const inboxConfigured = ref(true)
const inboxCompletingId = ref(null)
const inboxSyncing = ref(false)
const inboxDetailOpen = ref(false)
const inboxDetailItem = ref(null)
const inboxDetailBodyMode = ref('html')
const inboxAnalyzing = ref(false)
const inboxTaskMsg = ref('')
const inboxTaskMsgType = ref('')
const inboxTaskBoardRef = ref(null)
const inboxTaskMarqueePaused = ref(false)
let inboxTaskRefreshTimer = null

// 吐槽墙首页预览
const wallList = ref([])
const wallLoading = ref(false)
const WALL_CARD_BG = [
  'linear-gradient(135deg,#e74c5e,#c62d42)', 'linear-gradient(135deg,#3a7bd5,#2b5ea7)',
  'linear-gradient(135deg,#43a047,#2e7d32)', 'linear-gradient(135deg,#f4a62a,#e88d1a)',
  'linear-gradient(135deg,#8e44ad,#6c3483)', 'linear-gradient(135deg,#00acc1,#00838f)',
]
const WALL_CARD_ROT = [-2, 1.5, -1, 2, -1.5, 1]

const wallDisplayCards = computed(() => {
  return (wallList.value || []).slice(0, 6).map((w, i) => ({
    ...w,
    _bg: WALL_CARD_BG[i % WALL_CARD_BG.length],
    _rotate: WALL_CARD_ROT[i % WALL_CARD_ROT.length],
  }))
})

function wallResolveLabel(v) {
  return v === 2 ? '已回复' : v === 1 ? '处理中' : '未处理'
}

function getWallImgSrc(filename) {
  return wallImageUrl(filename)
}

async function loadWallList() {
  wallLoading.value = true
  try {
    const res = await getWallList()
    if (res && res.success) wallList.value = res.data || []
  } catch { /* ignore */ }
  wallLoading.value = false
}

const wallLikedIds = ref(new Set())
const wallLikeAnimating = ref(new Set())

async function doWallLike(id) {
  const name = (userName.value || '').trim()
  if (!name) return
  try {
    const res = await likeWall(id, { current_user: name })
    if (res && res.success) {
      const card = wallList.value.find(w => w.id === id)
      if (card) card.likeCount = res.likeCount ?? card.likeCount
      if (res.liked) {
        wallLikedIds.value.add(id)
      } else {
        wallLikedIds.value.delete(id)
      }
      wallLikedIds.value = new Set(wallLikedIds.value)
      wallLikeAnimating.value.add(id)
      wallLikeAnimating.value = new Set(wallLikeAnimating.value)
      setTimeout(() => {
        wallLikeAnimating.value.delete(id)
        wallLikeAnimating.value = new Set(wallLikeAnimating.value)
      }, 600)
    }
  } catch { /* ignore */ }
}

const isBuzhang = ref(false)
const briefingItems = ref([])
const briefingTrackRef = ref(null)
const briefingDays = ref(7)
const briefingHover = ref(false)
const showBriefingModal = ref(false)
const briefingFilter = ref('all')
const briefingFilterOptions = [
  { value: 'all', label: '全部' },
  { value: 'trip_city', label: '市内公出' },
  { value: 'trip_domestic', label: '境内公出' },
  { value: 'trip_abroad', label: '境外公出' },
  { value: 'hxp_all', label: '换休票' },
]
let marqueeTimer = null
let marqueeOffset = 0
let marqueePaused = false

const inboxLoopedTasks = computed(() => {
  const arr = inboxTasks.value || []
  return arr.length <= 1 ? arr : arr.concat(arr)
})

const inboxDisplayTasks = computed(() => {
  const arr = inboxTasks.value || []
  return arr.length <= 2 ? arr : inboxLoopedTasks.value
})

function startMarquee() {
  stopMarquee()
  if (briefingFilteredItems.value.length <= 4) return
  marqueeOffset = 0
  const step = () => {
    if (marqueePaused) { marqueeTimer = requestAnimationFrame(step); return }
    const el = briefingTrackRef.value
    if (!el) { marqueeTimer = requestAnimationFrame(step); return }
    marqueeOffset += 0.4
    const halfH = el.scrollHeight / 2
    if (halfH > 0 && marqueeOffset >= halfH) marqueeOffset = 0
    el.style.transform = `translateY(-${marqueeOffset}px)`
    marqueeTimer = requestAnimationFrame(step)
  }
  marqueeTimer = requestAnimationFrame(step)
}
function stopMarquee() { if (marqueeTimer) { cancelAnimationFrame(marqueeTimer); marqueeTimer = null } }

function onMarqueeEnter() {
  briefingHover.value = true
  marqueePaused = true
}
function onMarqueeLeave() {
  briefingHover.value = false
  marqueePaused = false
}
function onMarqueeWheel(e) {
  const el = briefingTrackRef.value
  if (!el) return
  marqueeOffset += e.deltaY * 0.5
  const halfH = el.scrollHeight / 2
  if (halfH > 0) {
    if (marqueeOffset < 0) marqueeOffset = halfH + marqueeOffset
    if (marqueeOffset >= halfH) marqueeOffset -= halfH
  }
  el.style.transform = `translateY(-${marqueeOffset}px)`
}

const briefingItemsDup = computed(() => {
  const arr = briefingFilteredItems.value
  return arr.length > 4 ? [...arr, ...arr] : arr
})

function getTripScopeFromItem(item) {
  if ((item?.type || '') !== 'trip') return ''
  const txt = `${item?.text || ''} ${item?.gcdd || ''}`
  const abroadRe = /(境外|国外|海外|香港|澳门|台湾|日本|韩国|美国|加拿大|英国|德国|法国|意大利|俄罗斯|澳大利亚|新加坡|马来西亚|泰国|越南|菲律宾|印尼|阿联酋|迪拜|欧洲|非洲|美洲)/i
  if (abroadRe.test(txt)) return 'trip_abroad'
  const cityRe = /(市内|本市|宁波|鄞州|海曙|江北|北仑|镇海|奉化|余姚|慈溪|宁海|象山)/i
  if (cityRe.test(txt)) return 'trip_city'
  return 'trip_domestic'
}

const briefingFilteredItems = computed(() => {
  const mode = briefingFilter.value
  const arr = briefingItems.value || []
  if (mode === 'all') return arr
  if (mode === 'hxp_all') {
    return arr.filter(i => ['hxp', 'hxp_batch', 'hxp_overtime'].includes(i?.type))
  }
  if (mode === 'trip_city' || mode === 'trip_domestic' || mode === 'trip_abroad') {
    return arr.filter(i => getTripScopeFromItem(i) === mode)
  }
  return arr
})

watch([briefingFilter, briefingItems], async () => {
  marqueeOffset = 0
  if (briefingTrackRef.value) briefingTrackRef.value.style.transform = 'translateY(0)'
  await nextTick()
  startMarquee()
})

function briefingTagLabel(type) {
  if (type === 'hxp_overtime') return '加班换休'
  if (type === 'hxp' || type === 'hxp_batch') return '换休票'
  if (type === 'trip') return '公出'
  return '消息'
}

function goBriefingDetail(item) {
  if (item.type === 'trip') {
    const q = { from: 'leader', scope: 'all', focusName: item.name || '' }
    if (item.year) q.year = item.year
    router.push({ path: '/attendance/business-trip', query: q })
  } else if (item.type === 'hxp') {
    const q = { focusName: item.name || '', scope: 'all', status: 'approved' }
    if (item.year) q.year = item.year
    router.push({ path: '/admin/hxp-records', query: q })
  } else if (item.type === 'hxp_overtime') {
    const q = { tab: 'overtime', from: 'leader', focusName: item.name || '' }
    if (item.year) q.year = item.year
    router.push({ path: '/attendance/manual', query: q })
  } else if (item.type === 'hxp_batch') {
    router.push('/admin/hxp-manage')
  }
}

async function fetchBriefing() {
  const name = (userName.value || '').trim()
  if (!name) return
  try {
    stopMarquee()
    const res = await getLeaderBriefing({ name, days: briefingDays.value })
    if (res && res.success && res.items) {
      briefingItems.value = res.items
      marqueeOffset = 0
      if (briefingTrackRef.value) briefingTrackRef.value.style.transform = 'translateY(0)'
      if (res.items.length > 0) {
        await nextTick()
        startMarquee()
      }
    }
  } catch { /* 非部长会403，忽略 */ }
}

/** 根据 permission 字段判断当前用户是否可见该卡片 */
function canShowFeature(permission) {
  if (!permission) return true
  const name = (userName.value || '').trim()
  const jb = (userJb.value || '').trim()
  const lsys = (userLsys.value || '').trim()
  const d = (dakaman.value || '').trim()
  const a2 = (admin2.value || '').trim()
  const a1 = (admin1.value || '').trim()
  const isAdmin1 = !!a1 && name === a1
  switch (permission) {
    case 'upload':
      return isAdmin1 || (!!d && name === d)
    case 'holidaySettings':
      return isAdmin1 || (!!d && name === d)
    case 'leaderDashboard':
      return isAdmin1 || isMinisterLevel(jb) ||
        (lsys === '综合技术室' && isDirectorLevel(jb))
    case 'overtimePay':
      return true
    case 'exceptions':
      return isAdmin1 || (!!d && name === d) || isMinisterOrDeptLeader(jb)
    case 'hxpRecords':
      return isMinisterLevel(jb) || (!!a2 && name === a2)
    case 'employeeAdmin':
      return isAdmin1 || isMinisterOrDeptLeader(jb) || (!!a2 && name === a2)
    case 'dbManager':
    case 'ygglFill':
      return canAccessDbManager.value
    case 'healthMonitor':
      return isAdmin1
    default:
      return true
  }
}

const userJb = ref('')
// 隶属科室（yggl.lsys），登录返回在 userInfo.dept 中
const userLsys = ref('')

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
        id: 'hxp-records',
        title: '换休票明细查询',
        description: '汇总查看所有人的公出节假日换休票申请记录与审批状态',
        path: '/admin/hxp-records',
        permission: 'hxpRecords',
        color: 'linear-gradient(135deg, #fbc2eb 0%, #a6c1ee 100%)',
        iconPath: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4'
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
        description: '部长/副部长查看全员异常；班组长/主任查看本科室异常（需请假或公出覆盖的智能提示）',
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
        title: '其他绩效激励统计',
        description: '按权限查看本人/本室/全部门其他绩效激励汇总与导出',
        path: '/overtime-pay',
        permission: 'overtimePay',
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
        description: '跳转人事档案系统，需使用人事档案系统独立账号登录',
        color: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
        tag: '外链',
        iconPath: 'M12 14l9-5-9-5-9 5 9 5zM12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z'
      },
      {
        id: 'sixianghuibao',
        title: '思想汇报管理',
        description: '跳转思想汇报审核平台，主系统登录后免登（用户名一致）',
        color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        tag: '外链',
        iconPath: 'M12 14l9-5-9-5-9 5 9 5zM12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z'
      },
      {
        id: 'old-230',
        title: '老230系统',
        description: '打开历史考勤系统入口（10.42.60.223）',
        color: 'linear-gradient(135deg, #fb7185 0%, #f43f5e 100%)',
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
        id: 'policy-query',
        title: '部门制度查询',
        description: '制度上传、制度查询、关键词搜索，支持 PDF、Word、Excel',
        path: '/file/policy-query',
        color: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
        iconPath: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z'
      },
      {
        id: 'tech-problem',
        title: '工艺技术问题手册',
        description: '工艺技术问题记录、原因分析与措施跟踪',
        path: '/file/tech-problem',
        color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        tag: '核心',
        iconPath: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4'
      },
      {
        id: 'contacts',
        title: '部门通讯录',
        description: '按科室查看员工手机号、座机号等联系方式',
        path: '/contacts',
        color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
        iconPath: 'M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M9 7a4 4 0 100 8 4 4 0 000-8zM23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75'
      },
      {
        id: 'feedback',
        title: '意见与建议',
        description: '部门吐槽墙、领导匿名信箱、系统功能建议',
        path: '/feedback',
        color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        tag: '新功能',
        iconPath: 'M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z'
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
        id: 'health-monitor',
        title: '系统健康监控',
        description: '数据库、大模型、外链与打卡自动获取服务状态一览',
        path: '/admin/health-monitor',
        permission: 'healthMonitor',
        tag: '系统',
        color: 'linear-gradient(135deg, #0f766e 0%, #14b8a6 100%)',
        iconPath: 'M22 12h-4l-3 9L9 3l-3 9H2'
      },
      {
        id: 'yggl-fill',
        title: '主表批量填充',
        description: '按 Excel 以身份证号匹配，批量更新员工信息字段',
        path: '/admin/yggl-fill',
        permission: 'ygglFill',
        color: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
        iconPath: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12'
      },
      {
        id: 'email-sender',
        title: '邮件发送',
        description: '通过企业邮箱向公司员工发送邮件',
        path: '/admin/email',
        permission: 'dbManager',
        tag: '系统',
        color: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
        iconPath: 'M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2zM22 6l-10 7L2 6'
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

const visibleFeatureCount = computed(() => {
  return featureGroups.value.reduce((sum, group) => sum + group.items.length, 0)
})

// ==================== 常用功能 ====================
const DEFAULT_FAV_IDS = ['attendance', 'businesstrip', 'filenumbering', 'contacts']

function _favStorageKey() {
  const name = (userName.value || '').trim()
  return name ? `home_fav_ids_${name}` : 'home_fav_ids'
}

function loadFavIds() {
  try {
    const raw = localStorage.getItem(_favStorageKey())
    if (raw) {
      const arr = JSON.parse(raw)
      if (Array.isArray(arr) && arr.length) return arr
    }
  } catch { /* ignore */ }
  return [...DEFAULT_FAV_IDS]
}

const favIds = ref(loadFavIds())

const allFeaturesFlat = computed(() => {
  const map = {}
  for (const group of rawFeatureGroups) {
    for (const item of group.items) {
      map[item.id] = item
    }
  }
  return map
})

const favFeatures = computed(() => {
  return favIds.value
    .map(id => allFeaturesFlat.value[id])
    .filter(Boolean)
    .filter(f => canShowFeature(f.permission))
})

const favEditorVisible = ref(false)
const favEditorSet = reactive(new Set())

function openFavEditor() {
  favEditorSet.clear()
  for (const id of favIds.value) favEditorSet.add(id)
  favEditorVisible.value = true
}

function closeFavEditor() {
  favEditorVisible.value = false
}

function toggleFavEditorItem(id) {
  if (favEditorSet.has(id)) {
    favEditorSet.delete(id)
  } else if (favEditorSet.size < 8) {
    favEditorSet.add(id)
  }
}

function saveFavEditor() {
  const ids = [...favEditorSet]
  favIds.value = ids
  try {
    localStorage.setItem(_favStorageKey(), JSON.stringify(ids))
  } catch { /* ignore */ }
  favEditorVisible.value = false
}

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

async function loadInboxTasks() {
  const name = (userName.value || '').trim()
  if (!name) return
  const isFirstLoad = !inboxTasks.value.length && !inboxTaskLoading.value
  if (isFirstLoad) inboxTaskLoading.value = true
  try {
    const [tasksRes, cfgRes] = await Promise.all([
      listInboxTasks({ current_user: name, limit: 50 }),
      getInboxConfig(name),
    ])
    if (tasksRes && tasksRes.success) {
      inboxTasks.value = tasksRes.items || []
      inboxTaskStats.value = tasksRes.stats || { pending: 0, failed: 0, taskCount: 0, total: 0 }
    }
    inboxConfigured.value = !!(cfgRes && cfgRes.configured)
  } catch (e) {
    console.warn('加载AI邮件待办失败', e)
  } finally {
    inboxTaskLoading.value = false
  }
}

async function manualAnalyzeInboxTasks() {
  const name = (userName.value || '').trim()
  if (!name || inboxAnalyzing.value) return
  inboxAnalyzing.value = true
  inboxTaskMsg.value = '正在调用本地大模型抽取任务，请稍候...'
  inboxTaskMsgType.value = 'info'
  try {
    const res = await analyzeInboxEmails({ current_user: name, limit: 10 })
    if (res && res.success) {
      inboxTaskMsg.value = res.message || '分析完成'
      inboxTaskMsgType.value = 'success'
      await loadInboxTasks()
    } else {
      inboxTaskMsg.value = (res && res.message) || '分析失败'
      inboxTaskMsgType.value = 'error'
    }
  } catch (e) {
    inboxTaskMsg.value = e?.message || '分析失败'
    inboxTaskMsgType.value = 'error'
  } finally {
    inboxAnalyzing.value = false
    setTimeout(() => { inboxTaskMsg.value = '' }, 6000)
  }
}

async function syncAndRefresh() {
  const name = (userName.value || '').trim()
  if (!name || inboxSyncing.value) return
  inboxSyncing.value = true
  inboxTaskMsg.value = '正在同步邮箱…'
  inboxTaskMsgType.value = 'info'
  try {
    const res = await syncInboxEmails(name)
    if (res && res.success) {
      inboxTaskMsg.value = res.message || '同步完成'
      inboxTaskMsgType.value = 'success'
    } else {
      inboxTaskMsg.value = (res && res.message) || '同步失败'
      inboxTaskMsgType.value = 'error'
    }
    await loadInboxTasks()
  } catch (e) {
    inboxTaskMsg.value = e?.message || '同步失败'
    inboxTaskMsgType.value = 'error'
  } finally {
    inboxSyncing.value = false
    setTimeout(() => { inboxTaskMsg.value = '' }, 5000)
  }
}

async function completeInboxTaskAction(id) {
  if (!id || inboxCompletingId.value) return
  const name = (userName.value || '').trim()
  if (!name) return
  inboxCompletingId.value = id
  try {
    const res = await completeInboxTask({ current_user: name, id })
    if (res && res.success) {
      inboxTaskMsg.value = res.message || '任务已完成'
      inboxTaskMsgType.value = 'success'
      await loadInboxTasks()
    } else {
      inboxTaskMsg.value = (res && res.message) || '操作失败'
      inboxTaskMsgType.value = 'error'
    }
  } catch (e) {
    inboxTaskMsg.value = e?.message || '操作失败'
    inboxTaskMsgType.value = 'error'
  } finally {
    inboxCompletingId.value = null
    setTimeout(() => { inboxTaskMsg.value = '' }, 5000)
  }
}

function shortFrom(from) {
  if (!from) return '-'
  const text = String(from)
  const m = text.match(/^(.*?)\s*<([^>]+)>$/)
  if (m) {
    const name = (m[1] || '').trim()
    return name || m[2]
  }
  return text.length > 20 ? `${text.slice(0, 20)}...` : text
}

const nowTick = ref(Date.now())
let _countdownTimer = null

function _parseDeadline(deadline) {
  if (!deadline) return null
  const d = new Date(String(deadline).replace(/\//g, '-').replace(/-(\d)(?!\d)/g, '-0$1'))
  return Number.isNaN(d.getTime()) ? null : d
}

function deadlineClass(deadline) {
  const d = _parseDeadline(deadline)
  if (!d) return 'none'
  const diffDays = (d.getTime() - nowTick.value) / (1000 * 60 * 60 * 24)
  if (diffDays < 0) return 'overdue'
  if (diffDays <= 2) return 'urgent'
  if (diffDays <= 7) return 'soon'
  return 'neutral'
}

function deadlineCountdown(deadline) {
  const d = _parseDeadline(deadline)
  if (!d) return ''
  const diff = d.getTime() - nowTick.value
  if (diff <= 0) {
    const past = -diff
    const days = Math.floor(past / 86400000)
    const hours = Math.floor((past % 86400000) / 3600000)
    if (days > 0) return `已超 ${days}天${hours}小时`
    const mins = Math.floor((past % 3600000) / 60000)
    return `已超 ${hours}时${mins}分`
  }
  const days = Math.floor(diff / 86400000)
  const hours = Math.floor((diff % 86400000) / 3600000)
  const mins = Math.floor((diff % 3600000) / 60000)
  if (days > 0) return `剩 ${days}天${hours}小时`
  if (hours > 0) return `剩 ${hours}时${mins}分`
  return `剩 ${mins}分钟`
}

function onInboxTaskWheel(e) {
  const el = inboxTaskBoardRef.value
  if (!el) return
  const deltaY = Number(e?.deltaY || 0)
  if (!deltaY) return
  const maxScroll = el.scrollHeight - el.clientHeight
  if (maxScroll <= 0) return
  e.preventDefault()
  el.scrollTop += deltaY
}

async function openInboxTask(id) {
  if (!id) return
  const name = (userName.value || '').trim()
  if (!name) return
  inboxDetailOpen.value = true
  inboxDetailItem.value = null
  inboxDetailBodyMode.value = 'html'
  try {
    const res = await getInboxEmailDetail({ current_user: name, id })
    if (res && res.success) {
      inboxDetailItem.value = res.item
      inboxDetailBodyMode.value = res.item && res.item.bodyHtml ? 'html' : 'text'
    }
  } catch (e) {
    console.error('加载邮件详情失败', e)
    inboxDetailItem.value = { subject: '', from: '', to: '', cc: '', emailDate: '', receivedAt: '', bodyText: '加载失败', bodyHtml: '' }
  }
}

function closeInboxDetail() {
  inboxDetailOpen.value = false
  inboxDetailItem.value = null
}

const inboxDetailSafeHtml = computed(() => {
  if (!inboxDetailItem.value || !inboxDetailItem.value.bodyHtml) return ''
  return inboxDetailItem.value.bodyHtml
})

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

function goPersonnelArchive() {
  const url = (personnelArchiveUrl.value || '').trim()
  if (url) {
    window.open(url, '_blank', 'noopener,noreferrer')
  } else {
    alert('人事档案系统链接未配置，请联系管理员')
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

onBeforeUnmount(() => {
  stopMarquee()
  if (inboxTaskRefreshTimer) {
    clearInterval(inboxTaskRefreshTimer)
    inboxTaskRefreshTimer = null
  }
  if (_countdownTimer) {
    clearInterval(_countdownTimer)
    _countdownTimer = null
  }
})

onMounted(() => {
  const info = getStoredUserInfo()
  userName.value = info.name || info.userName || ''
  userJb.value = info.jb || ''
  userLsys.value = (info.dept || info.lsys || '').trim()
  const jb = (info.jb || '').trim()
  isBuzhang.value = jbMatch(jb, '部长')
  refreshWorkplaceTodos()
  fetchRequestList()
  loadWallList()
  if (isBuzhang.value) fetchBriefing()
  getUploadConfig().then(res => {
    if (res && res.success) {
      dakaman.value = res.dakaman != null ? String(res.dakaman).trim() : ''
      admin2.value = res.admin2 != null ? String(res.admin2).trim() : ''
      admin1.value = res.admin1 != null ? String(res.admin1).trim() : ''
      personnelArchiveUrl.value = res.personnelArchiveUrl != null ? String(res.personnelArchiveUrl).trim() : ''
    }
  }).catch(() => { dakaman.value = ''; admin2.value = ''; admin1.value = ''; personnelArchiveUrl.value = '' })
  const name = userName.value?.trim()
  if (name) {
    getDbManagerPermission({ current_user: name }).then(res => {
      canAccessDbManager.value = !!(res && res.canAccess)
      if (canAccessInboxBoard.value) {
        syncInboxEmails(name).then(() => loadInboxTasks()).catch(() => loadInboxTasks())
        inboxTaskRefreshTimer = setInterval(loadInboxTasks, 15000)
      }
  }).catch(() => { canAccessDbManager.value = false })
  }
  _countdownTimer = setInterval(() => { nowTick.value = Date.now() }, 30000)
})

function folderAccent(group) {
  return group?.items?.[0]?.color || 'linear-gradient(135deg, #4f46e5 0%, #0891b2 100%)'
}

function openShortcutGroup(group) {
  selectedShortcutGroup.value = group
}

function closeShortcutGroup() {
  selectedShortcutGroup.value = null
}

async function navigateFromShortcut(feature) {
  closeShortcutGroup()
  await navigateTo(feature)
}

async function navigateTo(feature) {
  if (!feature) return
  if (feature.id === 'personnel-archive') {
    const url = (personnelArchiveUrl.value || '').trim()
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer')
    } else {
      alert('人事档案系统链接未配置，请联系管理员')
    }
    return
  }
  if (feature.id === 'sixianghuibao') {
    const name = (userName.value || '').trim()
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
    return
  }
  if (feature.id === 'old-230') {
    window.open('http://10.42.60.223', '_blank', 'noopener,noreferrer')
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

.ai-task-unconfigured {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: var(--spacing-xl) var(--spacing-xxl);
  text-align: center;
  background: linear-gradient(135deg, #fff7ed 0%, #fffbeb 100%);
  border: 1px dashed #f59e0b;
  border-radius: 10px;
  margin: 0 var(--spacing-md);
}
.ai-task-unconfigured__icon {
  width: 32px;
  height: 32px;
  color: #f59e0b;
}
.ai-task-unconfigured p {
  margin: 0;
  font-size: 0.9rem;
  color: #92400e;
  line-height: 1.6;
}
.ai-task-unconfigured__steps {
  margin: 0;
  padding-left: 1.4em;
  text-align: left;
  font-size: 0.85rem;
  color: #78350f;
  line-height: 1.8;
  list-style: decimal;
}
.ai-task-unconfigured__steps strong {
  color: #dc2626;
}
.ai-task-unconfigured__link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 20px;
  font-size: 0.88rem;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  border-radius: 8px;
  text-decoration: none;
  transition: transform .15s, box-shadow .15s;
}
.ai-task-unconfigured__link:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.35);
}

/* 快捷入口文件夹 */
.shortcuts-container {
  margin-top: var(--spacing-xl);
}

.shortcuts-section {
  padding: var(--spacing-lg);
  background: #fff;
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.shortcuts-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.shortcuts-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  white-space: nowrap;
}

.shortcut-folders {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--spacing-md);
}

.shortcut-folder {
  min-width: 0;
  min-height: 74px;
  padding: var(--spacing-md);
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  text-align: left;
  background: #f8fafc;
  border: 1px solid var(--color-border-lighter);
  border-radius: 8px;
  cursor: pointer;
  transition: transform var(--transition-base) var(--transition-ease), box-shadow var(--transition-base) var(--transition-ease), border-color var(--transition-base) var(--transition-ease);
}

.shortcut-folder:hover {
  transform: translateY(-2px);
  border-color: var(--color-primary-light);
  box-shadow: var(--shadow-md);
  background: #fff;
}

.shortcut-folder__icon {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.shortcut-folder__icon svg {
  width: 23px;
  height: 23px;
}

.shortcut-folder__body {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.shortcut-folder__body strong {
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shortcut-folder__body small {
  color: var(--color-text-tertiary);
  font-size: var(--font-size-xs);
}

.shortcut-folder__arrow {
  flex-shrink: 0;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-lg);
}

.shortcut-modal {
  width: min(900px, calc(100vw - 32px));
  max-height: min(760px, calc(100vh - 56px));
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  box-shadow: var(--shadow-elevated);
  overflow: hidden;
}

.shortcut-modal__header {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-lg);
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
}

.shortcut-modal__header h2 {
  margin: 0 0 4px;
  color: var(--color-text-primary);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
}

.shortcut-modal__header p {
  margin: 0;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

.shortcut-modal__close {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--color-text-tertiary);
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
}

.shortcut-modal__close:hover {
  background: var(--color-bg-layout);
  color: var(--color-text-primary);
}

.shortcut-modal__grid {
  padding: var(--spacing-lg);
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--spacing-md);
  overflow-y: auto;
}

.shortcut-app {
  position: relative;
  min-width: 0;
  min-height: 112px;
  padding: var(--spacing-md);
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md);
  text-align: left;
  background: #fff;
  border: 1px solid var(--color-border-lighter);
  border-radius: 8px;
  cursor: pointer;
  transition: transform var(--transition-base) var(--transition-ease), box-shadow var(--transition-base) var(--transition-ease), border-color var(--transition-base) var(--transition-ease);
}

.shortcut-app:hover {
  transform: translateY(-2px);
  border-color: var(--color-primary-light);
  box-shadow: var(--shadow-md);
}

.shortcut-app__icon {
  width: 40px;
  height: 40px;
  border-radius: 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.shortcut-app__icon svg {
  width: 22px;
  height: 22px;
}

.shortcut-app__text {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.shortcut-app__text strong {
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  line-height: 1.25;
}

.shortcut-app__text small {
  display: -webkit-box;
  overflow: hidden;
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

.shortcut-app__tag {
  position: absolute;
  right: 10px;
  bottom: 8px;
  padding: 2px 7px;
  color: var(--color-primary);
  background: var(--color-primary-lightest);
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: var(--font-weight-medium);
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
  
  .shortcut-folders {
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  }
}

/* ==================== 常用功能 ==================== */
.home-favorites-section {
  margin-bottom: var(--spacing-lg);
}
.favorites-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.favorites-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
}
.favorites-title-icon {
  width: 20px;
  height: 20px;
  color: #f59e0b;
  fill: #fbbf24;
}
.favorites-edit-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 4px 12px;
  font-size: 12px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s;
}
.favorites-edit-btn svg { width: 13px; height: 13px; }
.favorites-edit-btn:hover { background: #f8fafc; border-color: #94a3b8; color: #334155; }

.favorites-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.fav-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.15s;
  text-align: left;
}
.fav-card:hover {
  border-color: #bfdbfe;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.08);
  transform: translateY(-1px);
}
.fav-card__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  min-width: 36px;
  border-radius: 8px;
}
.fav-card__icon svg {
  width: 18px;
  height: 18px;
  color: #fff;
  stroke: #fff;
}
.fav-card__label {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 常用功能编辑弹窗 */
.fav-editor-modal {
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.2);
  width: 520px;
  max-width: 92vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.fav-editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px 12px;
  border-bottom: 1px solid #e5e7eb;
}
.fav-editor-header h3 { margin: 0; font-size: 16px; font-weight: 700; color: #1e293b; }
.fav-editor-close {
  background: none;
  border: none;
  font-size: 22px;
  color: #94a3b8;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}
.fav-editor-close:hover { color: #ef4444; }
.fav-editor-hint {
  margin: 0;
  padding: 10px 20px 6px;
  font-size: 12px;
  color: #94a3b8;
}
.fav-editor-groups {
  flex: 1;
  overflow-y: auto;
  padding: 4px 20px 12px;
}
.fav-editor-group { margin-bottom: 12px; }
.fav-editor-group:last-child { margin-bottom: 0; }
.fav-editor-group-title {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
  letter-spacing: 0.02em;
}
.fav-editor-items {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
}
.fav-editor-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid #f1f5f9;
  cursor: pointer;
  transition: all 0.12s;
  background: #fafafa;
}
.fav-editor-item:hover { background: #f0f9ff; border-color: #bfdbfe; }
.fav-editor-item.checked { background: #eff6ff; border-color: #93c5fd; }
.fav-editor-item.disabled { opacity: 0.4; cursor: not-allowed; }
.fav-editor-item input[type="checkbox"] { width: 15px; height: 15px; accent-color: #3b82f6; cursor: inherit; flex-shrink: 0; }
.fav-editor-item__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  min-width: 24px;
  border-radius: 5px;
}
.fav-editor-item__icon svg { width: 13px; height: 13px; color: #fff; stroke: #fff; }
.fav-editor-item__name { font-size: 12px; font-weight: 500; color: #334155; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fav-editor-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-top: 1px solid #e5e7eb;
  background: #f8fafc;
}
.fav-editor-count { font-size: 12px; color: #94a3b8; font-weight: 500; }
.fav-editor-btns { display: flex; gap: 8px; }
.btn-fav-cancel {
  padding: 6px 18px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  font-size: 13px;
  cursor: pointer;
  color: #475569;
}
.btn-fav-cancel:hover { background: #f1f5f9; }
.btn-fav-save {
  padding: 6px 20px;
  border: none;
  border-radius: 6px;
  background: var(--color-primary, #3b82f6);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-fav-save:hover { opacity: 0.9; }

@media (max-width: 768px) {
  .favorites-grid { grid-template-columns: repeat(2, 1fr); }
  .fav-editor-items { grid-template-columns: 1fr; }
}

.home-ai-task-section {
  margin-bottom: var(--spacing-xxl);
}

.ai-task-card {
  background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 100%);
  border-color: #dbeafe;
}

.dashboard-card__icon--ai {
  background: linear-gradient(135deg, #4f46e5 0%, #0891b2 100%);
}

.ai-task-card__header {
  align-items: flex-start;
  flex-wrap: wrap;
}

.ai-task-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.ai-task-stat {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.ai-task-stat--warn {
  color: #dc2626;
  font-weight: 600;
}

.ai-task-icon-btn,
.ai-task-analyze-btn,
.ai-task-viewall-btn {
  height: 30px;
  border: 1px solid #c7d2fe;
  background: #fff;
  color: #3730a3;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.ai-task-icon-btn {
  width: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.ai-task-icon-btn svg {
  width: 16px;
  height: 16px;
}

.ai-task-analyze-btn,
.ai-task-viewall-btn {
  padding: 0 12px;
  font-size: var(--font-size-sm);
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}

.ai-task-viewall-btn {
  font-weight: 600;
}

.ai-task-icon-btn:hover,
.ai-task-analyze-btn:hover,
.ai-task-viewall-btn:hover {
  background: #eef2ff;
}

.ai-task-icon-btn:disabled,
.ai-task-analyze-btn:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

@keyframes spin-icon {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.ai-task-icon-btn svg.spinning {
  animation: spin-icon 1s linear infinite;
}

.ai-task-toast {
  margin: var(--spacing-md) var(--spacing-xl) 0;
  padding: 7px 12px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
}

.ai-task-toast.info {
  background: #e0e7ff;
  color: #3730a3;
}

.ai-task-toast.success {
  background: #dcfce7;
  color: #166534;
}

.ai-task-toast.error {
  background: #fee2e2;
  color: #991b1b;
}

.ai-task-body {
  padding: var(--spacing-md) var(--spacing-xl) var(--spacing-xl);
}

.ai-task-marquee {
  max-height: 300px;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.ai-task-track {
  display: flex;
  flex-direction: column;
  gap: 6px;
  animation: inbox-task-scroll 40s linear infinite;
  will-change: transform;
}

.ai-task-track.paused {
  animation-play-state: paused;
}

.ai-task-track.no-anim {
  animation: none;
}

@keyframes inbox-task-scroll {
  0% { transform: translateY(0); }
  100% { transform: translateY(-50%); }
}

.ai-mail-task {
  width: 100%;
  min-width: 0;
  padding: 8px 14px;
  text-align: left;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #dbeafe;
  border-left: 4px solid #4f46e5;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.08);
  cursor: pointer;
  transition: transform .15s, box-shadow .15s;
}

.ai-mail-task:hover {
  transform: translateX(2px);
  box-shadow: 0 6px 18px rgba(79, 70, 229, 0.15);
}

.ai-mail-task__top,
.ai-mail-task__sub {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-width: 0;
}

.ai-mail-task__deadline {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 60%;
  padding: 2px 10px;
  border-radius: 999px;
  background: #eef2ff;
  color: #3730a3;
  font-size: var(--font-size-sm);
  font-weight: 600;
  white-space: nowrap;
}

.ai-mail-task__deadline svg {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
}

.ai-mail-task__deadline.none {
  background: #f3f4f6;
  color: #6b7280;
}

.ai-mail-task__deadline.overdue {
  background: #fee2e2;
  color: #b91c1c;
}

.ai-mail-task__deadline.urgent {
  background: #ffedd5;
  color: #c2410c;
}

.ai-mail-task__deadline.soon {
  background: #fef9c3;
  color: #854d0e;
}

.ai-mail-task__countdown {
  font-size: 10px;
  font-weight: 700;
  opacity: 0.85;
  padding-left: 4px;
  white-space: nowrap;
}

.ai-mail-task__from {
  min-width: 0;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}
.ai-mail-task__complete {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 10px;
  font-size: 0.74rem;
  font-weight: 600;
  color: #16a34a;
  background: #dcfce7;
  border: 1px solid #bbf7d0;
  border-radius: 999px;
  cursor: pointer;
  transition: all .15s;
  white-space: nowrap;
  flex-shrink: 0;
}
.ai-mail-task__complete svg {
  width: 12px;
  height: 12px;
}
.ai-mail-task__complete:hover {
  background: #16a34a;
  color: #fff;
  border-color: #16a34a;
}
.ai-mail-task__complete.disabled {
  opacity: 0.5;
  pointer-events: none;
}

.ai-mail-task__summary {
  display: -webkit-box;
  margin: 7px 0 4px;
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 0.95rem;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

.ai-mail-task__sub {
  color: var(--color-text-tertiary);
  font-size: var(--font-size-xs);
}

.ai-mail-task__sub span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ai-mail-task__sub span:last-child {
  flex-shrink: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

/* ========== 吐槽墙首页预览 ========== */
.home-wall-section {
  margin-bottom: var(--spacing-xxl);
}

.wall-preview-card {
  background: linear-gradient(135deg, #fef3f2 0%, #fdf2f8 50%, #f5f3ff 100%);
  border-color: #fecdd3;
}

.dashboard-card__icon--wall {
  background: linear-gradient(135deg, #e11d48 0%, #db2777 100%);
}

.wall-preview-card__header {
  align-items: center;
}

.wall-preview-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.wall-preview-refresh {
  width: 32px;
  height: 30px;
  border: 1px solid #fda4af;
  background: #fff;
  color: #be123c;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.wall-preview-refresh svg {
  width: 16px;
  height: 16px;
}

.wall-preview-refresh:hover {
  background: #fff1f2;
}

.wall-preview-viewall {
  height: 30px;
  padding: 0 12px;
  border: 1px solid #fda4af;
  background: #fff;
  color: #be123c;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  font-weight: 600;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}

.wall-preview-viewall:hover {
  background: #fff1f2;
}

.wall-preview-body {
  padding: var(--spacing-md) var(--spacing-xl) var(--spacing-xl);
}

.wall-preview-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.wall-mini-card {
  position: relative;
  padding: 14px 14px 10px;
  border-radius: 10px;
  color: #fff;
  cursor: pointer;
  transform: rotate(calc(var(--rot, 0deg)));
  transition: transform .2s, box-shadow .2s;
  min-height: 100px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}

.wall-mini-card:hover {
  transform: rotate(0deg) scale(1.04);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  z-index: 1;
}

.wall-mini-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.28);
  color: #fff;
}

.wmb-1 { background: rgba(251, 191, 36, 0.5); }
.wmb-2 { background: rgba(74, 222, 128, 0.5); }

.wall-mini-body {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  flex: 1;
  word-break: break-all;
}

.wall-mini-reply {
  margin-top: 6px;
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  font-size: 11px;
  line-height: 1.4;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.wall-mini-foot {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  font-size: 12px;
  opacity: 0.85;
}

.wall-mini-avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}

.wall-mini-dept {
  flex: 1;
  min-width: 0;
}

.wall-mini-like {
  position: relative;
  cursor: pointer;
  white-space: nowrap;
  transition: transform .15s;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 6px;
  border-radius: 999px;
  user-select: none;
}

.wall-mini-like:hover {
  transform: scale(1.15);
  background: rgba(255, 255, 255, 0.25);
}

.wall-mini-like.liked {
  background: rgba(255, 255, 255, 0.35);
  font-weight: 700;
}

.wall-mini-like.liked .wall-like-count {
  color: #fff;
}

.wall-like-icon {
  display: inline-block;
  transition: transform .3s cubic-bezier(.34, 1.56, .64, 1);
}

.wall-mini-like.animating .wall-like-icon {
  animation: wall-like-pop .5s cubic-bezier(.34, 1.56, .64, 1);
}

@keyframes wall-like-pop {
  0%   { transform: scale(1); }
  25%  { transform: scale(1.5) rotate(-15deg); }
  50%  { transform: scale(0.9) rotate(5deg); }
  75%  { transform: scale(1.2); }
  100% { transform: scale(1); }
}

.wall-mini-like.animating.liked::after {
  content: '';
  position: absolute;
  top: -4px;
  left: 50%;
  width: 6px;
  height: 6px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 50%;
  animation: wall-like-burst .5s ease-out forwards;
  pointer-events: none;
}

@keyframes wall-like-burst {
  0%   { transform: translate(-50%, 0) scale(0); opacity: 1; }
  50%  { transform: translate(-50%, -12px) scale(1.5); opacity: 0.8; }
  100% { transform: translate(-50%, -20px) scale(0.5); opacity: 0; }
}

/* ========== 重要信息审阅 ========== */
/* 重要信息审阅 - 滚动播放窗口 */
.briefing-section {
  margin-bottom: var(--spacing-xxl);
  padding: 0;
}

.dashboard-card--briefing {
  border-left: 3px solid #667eea;
}

.dashboard-card__icon--briefing {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.briefing-header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
  justify-content: flex-end;
}

.briefing-filter-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.briefing-filter-tab {
  padding: 3px 10px;
  border: 1px solid var(--color-border-base);
  border-radius: 999px;
  font-size: 12px;
  color: var(--color-text-secondary);
  background: #fff;
  cursor: pointer;
  transition: all .15s;
}
.briefing-filter-tab:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.briefing-filter-tab.active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.briefing-days-select {
  padding: 4px 10px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  background: white;
  cursor: pointer;
}

.briefing-viewall-btn {
  padding: 4px 12px;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  color: var(--color-primary);
  background: white;
  cursor: pointer;
  transition: all 0.2s;
}
.briefing-viewall-btn:hover {
  background: var(--color-primary);
  color: white;
}

.briefing-marquee {
  height: 160px;
  overflow: hidden;
  position: relative;
  padding: var(--spacing-sm) var(--spacing-xl);
  cursor: default;
  transition: box-shadow 0.2s;
}
.briefing-marquee--hover {
  box-shadow: inset 0 -20px 20px -20px rgba(0,0,0,0.06), inset 0 20px 20px -20px rgba(0,0,0,0.06);
}

.briefing-track {
  will-change: transform;
}

.briefing-empty-inline {
  padding: 22px 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

.briefing-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 8px 4px;
  border-bottom: 1px dashed var(--color-border-lighter);
  line-height: 1.5;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background 0.15s;
}

.briefing-item:hover {
  background: var(--color-bg-spotlight, #f8f9fa);
}

.briefing-item:last-child {
  border-bottom: none;
}

.briefing-arrow {
  flex-shrink: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  opacity: 0;
  transition: opacity 0.15s;
}

.briefing-item:hover .briefing-arrow {
  opacity: 1;
  color: var(--color-primary);
}

.briefing-tag {
  flex-shrink: 0;
  font-size: var(--font-size-xs);
  font-weight: 500;
  padding: 1px 8px;
  border-radius: var(--radius-sm);
  white-space: nowrap;
}

.briefing-item--hxp .briefing-tag {
  color: #b45309;
  background: #fef3c7;
}

.briefing-item--trip .briefing-tag {
  color: #0369a1;
  background: #e0f2fe;
}

.briefing-item--hxp_batch .briefing-tag {
  color: #7c3aed;
  background: #ede9fe;
}

.briefing-item--hxp_overtime .briefing-tag {
  color: #059669;
  background: #d1fae5;
}
.briefing-modal__item--hxp_overtime .briefing-tag {
  color: #059669;
  background: #d1fae5;
}

.briefing-text {
  flex: 1;
  min-width: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 100;
}

.briefing-modal {
  background: white;
  border-radius: var(--radius-md);
  width: 780px;
  max-width: 95vw;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg, 0 10px 40px rgba(0,0,0,0.15));
}
.briefing-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
}
.briefing-modal__header h2 {
  margin: 0;
  font-size: var(--font-size-lg, 18px);
}
.briefing-modal__close {
  border: none;
  background: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--color-text-tertiary);
  padding: 0 4px;
  line-height: 1;
}
.briefing-modal__close:hover {
  color: var(--color-text-primary);
}
.briefing-modal__body {
  overflow-y: auto;
  padding: var(--spacing-md) var(--spacing-xl) var(--spacing-xl);
}
.briefing-modal__item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 10px var(--spacing-md);
  border-bottom: 1px solid var(--color-border-lighter);
  cursor: pointer;
  transition: background 0.15s;
  border-left: 4px solid transparent;
}
.briefing-modal__item:hover {
  background: var(--color-bg-spotlight, #f8f9fa);
}
.briefing-modal__item:last-child {
  border-bottom: none;
}
.briefing-modal__idx {
  flex-shrink: 0;
  width: 26px;
  text-align: center;
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-tertiary);
}
.briefing-modal__text {
  flex: 1;
  min-width: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  line-height: 1.5;
}
.briefing-modal__item--hxp {
  background: #fffaf0;
  border-left-color: #d97706;
}
.briefing-modal__item--hxp:hover {
  background: #fef3c7;
}
.briefing-modal__item--hxp_batch {
  background: #faf5ff;
  border-left-color: #7c3aed;
}
.briefing-modal__item--hxp_batch:hover {
  background: #ede9fe;
}
.briefing-modal__item--hxp_overtime {
  background: #ecfdf5;
  border-left-color: #059669;
}
.briefing-modal__item--hxp_overtime:hover {
  background: #d1fae5;
}
.briefing-modal__item--trip {
  background: #f0f9ff;
  border-left-color: #0284c7;
}
.briefing-modal__item--trip:hover {
  background: #e0f2fe;
}

.briefing-modal__item--hxp .briefing-tag {
  color: #b45309;
  background: #fef3c7;
}
.briefing-modal__item--hxp_batch .briefing-tag {
  color: #7c3aed;
  background: #ede9fe;
}
.briefing-modal__item--trip .briefing-tag {
  color: #0369a1;
  background: #e0f2fe;
}
.briefing-modal__empty {
  text-align: center;
  color: var(--color-text-tertiary);
  padding: var(--spacing-xxl) 0;
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
  
  .shortcuts-container {
    padding: 0 var(--spacing-md);
  }

  .shortcuts-section {
    padding: var(--spacing-md);
  }

  .shortcut-folders,
  .shortcut-modal__grid {
    grid-template-columns: 1fr;
  }

  .shortcut-modal {
    width: calc(100vw - 24px);
    max-height: calc(100vh - 40px);
  }

  .briefing-section {
    padding: 0 var(--spacing-md);
  }

  .home-favorites-section,
  .home-ai-task-section,
  .home-wall-section {
    padding: 0 var(--spacing-md);
  }

  .wall-preview-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .ai-task-card__header {
    gap: var(--spacing-sm);
  }

  .ai-task-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .ai-task-body,
  .ai-task-toast {
    margin-left: var(--spacing-lg);
    margin-right: var(--spacing-lg);
  }

  .ai-task-body {
    padding-left: var(--spacing-lg);
    padding-right: var(--spacing-lg);
  }
}

/* 邮件详情弹窗 */
.inbox-detail-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;
}
.inbox-detail-modal {
  background: #fff;
  border-radius: 8px;
  width: min(920px, 100%);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.25);
}
.inbox-detail-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}
.inbox-detail-modal__title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 600;
}
.inbox-detail-modal__close {
  background: transparent;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--color-text-tertiary);
  line-height: 1;
}
.inbox-detail-modal__body {
  overflow: auto;
  padding: var(--spacing-lg);
  flex: 1;
}
.inbox-detail-meta {
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
  background: #f8fafc;
}
.inbox-detail-meta__row {
  display: flex;
  gap: var(--spacing-md);
  padding: 4px 0;
  font-size: 0.88rem;
}
.inbox-detail-meta__label {
  width: 80px;
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}
.inbox-detail-meta__row > span:last-child {
  flex: 1;
  word-break: break-all;
  color: var(--color-text-primary);
}
.inbox-detail-toggle {
  display: flex;
  gap: 6px;
  margin-bottom: var(--spacing-sm);
}
.inbox-detail-toggle button {
  padding: 4px 14px;
  font-size: 0.85rem;
  border: 1px solid var(--color-border);
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  color: var(--color-text-secondary);
}
.inbox-detail-toggle button.active {
  background: var(--color-primary, #3b82f6);
  color: #fff;
  border-color: var(--color-primary, #3b82f6);
}
.inbox-detail-toggle button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.inbox-detail-body {
  border: 1px solid var(--color-border);
  border-radius: 6px;
  overflow: hidden;
  min-height: 260px;
  max-height: 60vh;
  background: #fff;
}
.inbox-detail-iframe {
  width: 100%;
  height: 60vh;
  border: 0;
  background: #fff;
}
.inbox-detail-text {
  margin: 0;
  padding: var(--spacing-md);
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.86rem;
  line-height: 1.55;
  color: var(--color-text-primary);
  max-height: 60vh;
  overflow: auto;
}
</style>
