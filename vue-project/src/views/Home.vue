<template>
  <div class="home-page">
    <!-- 待办事项瓦片 -->
    <section
      v-if="isHomeModuleVisible('todo')"
      class="home-tile home-tile--todo"
      data-home-module-id="todo"
      :style="homeModuleStyle('todo')"
    >
      <button
        type="button"
        class="home-tile-drag-handle"
        :class="{ 'is-active': homeLayoutDrag.activeId === 'todo' }"
        title="拖动调整位置"
        aria-label="拖动调整待办事项位置"
        @pointerdown="startHomeTileDrag($event, 'todo')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="9" cy="5" r="1.5"/><circle cx="15" cy="5" r="1.5"/>
          <circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/>
          <circle cx="9" cy="19" r="1.5"/><circle cx="15" cy="19" r="1.5"/>
        </svg>
      </button>
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
                  {{ task.isHxpNotice ? '已读' : (task.isHxpApproval ? '去审批' : (task.isPersonnel ? '去处理' : (task.isSixianghuibao ? (task.btnLabel || '去处理') : (task.isReturnReminder ? '去登记' : (task.isSealUsePending ? '已用印' : (task.isSealApproval ? '去审批' : (task.btnLabel || '处理'))))))) }}
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
    </section>

    <!-- 我的申请流程瓦片 -->
    <section
      v-if="isHomeModuleVisible('request')"
      class="home-tile home-tile--request"
      data-home-module-id="request"
      :style="homeModuleStyle('request')"
    >
      <button
        type="button"
        class="home-tile-drag-handle"
        :class="{ 'is-active': homeLayoutDrag.activeId === 'request' }"
        title="拖动调整位置"
        aria-label="拖动调整我的申请流程位置"
        @pointerdown="startHomeTileDrag($event, 'request')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="9" cy="5" r="1.5"/><circle cx="15" cy="5" r="1.5"/>
          <circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/>
          <circle cx="9" cy="19" r="1.5"/><circle cx="15" cy="19" r="1.5"/>
        </svg>
      </button>
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
    </section>

    <!-- 部门通讯录（电话簿）瓦片：与待办等 home-tile 同尺寸，内部滚动 -->
    <section
      v-if="isHomeModuleVisible('contactsCard')"
      class="home-tile home-tile--contacts"
      data-home-module-id="contactsCard"
      :style="homeModuleStyle('contactsCard')"
    >
      <button
        type="button"
        class="home-tile-drag-handle"
        :class="{ 'is-active': homeLayoutDrag.activeId === 'contactsCard' }"
        title="拖动调整位置"
        aria-label="拖动调整部门通讯录位置"
        @pointerdown="startHomeTileDrag($event, 'contactsCard')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="9" cy="5" r="1.5"/><circle cx="15" cy="5" r="1.5"/>
          <circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/>
          <circle cx="9" cy="19" r="1.5"/><circle cx="15" cy="19" r="1.5"/>
        </svg>
      </button>
      <article class="dashboard-card dashboard-card--contacts">
        <header class="dashboard-card__header">
          <h2 class="dashboard-card__title">
            <span class="dashboard-card__icon dashboard-card__icon--contacts" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="9" cy="7" r="4"/>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
              </svg>
            </span>
            <span class="dashboard-card__title-text">部门通讯录</span>
            <span v-if="contactsHomeTotal > 0" class="dashboard-card__badge">{{ contactsHomeTotal }}</span>
          </h2>
          <router-link to="/contacts" class="dashboard-card__link">查看全部</router-link>
        </header>
        <div class="dashboard-card__body contacts-home-body">
          <div class="contacts-home-toolbar">
            <select v-model="contactsHomeDept" class="contacts-home-select" @change="loadContactsHome">
              <option value="">全部科室</option>
              <option v-for="d in CONTACT_HOME_DEPT_OPTIONS" :key="d" :value="d">{{ d }}</option>
            </select>
            <div class="contacts-home-search">
              <input
                v-model="contactsHomeKeyword"
                type="search"
                class="contacts-home-input"
                placeholder="姓名、手机、座机…"
                @input="onContactsHomeSearchInput"
              />
              <button v-if="contactsHomeKeyword" type="button" class="contacts-home-clear" @click="clearContactsHomeSearch">&times;</button>
            </div>
          </div>
          <div v-if="contactsHomeLoading" class="dashboard-empty"><p>加载中…</p></div>
          <div v-else-if="!contactsHomeFlat.length" class="dashboard-empty"><p>{{ contactsHomeKeyword.trim() ? '未找到匹配联系人' : '暂无通讯录数据' }}</p></div>
          <ul v-else class="contacts-home-list">
            <li
              v-for="(row, idx) in contactsHomeFlat"
              :key="`${row.deptName}-${row.gh || row.name}-${idx}`"
              class="contacts-home-row"
            >
              <div class="contacts-home-row-main">
                <span class="contacts-home-name">{{ row.name }}</span>
                <span v-if="row.jb" class="contacts-home-jb" :class="contactsJbClass(row.jb)">{{ row.jb }}</span>
              </div>
              <div class="contacts-home-row-sub">
                <span class="contacts-home-dept">{{ row.deptName }}</span>
                <span class="contacts-home-phones">
                  <a v-if="row.mobile" :href="'tel:' + row.mobile" class="contacts-home-tel" @click.stop>{{ row.mobile }}</a>
                  <span v-if="row.telephone" class="contacts-home-tel contacts-home-tel--land">{{ row.telephone }}</span>
                  <span v-if="!row.mobile && !row.telephone" class="contacts-home-no">—</span>
                </span>
              </div>
            </li>
          </ul>
        </div>
      </article>
    </section>

    <!-- 重要信息审阅（部长/副部长级别可见，含经理/副经理） -->
    <section
      v-if="isHomeModuleVisible('briefing') && canSeeBriefing && briefingItems.length > 0"
      class="home-tile home-tile--briefing briefing-section"
      data-home-module-id="briefing"
      :style="homeModuleStyle('briefing')"
    >
      <button
        type="button"
        class="home-tile-drag-handle"
        :class="{ 'is-active': homeLayoutDrag.activeId === 'briefing' }"
        title="拖动调整位置"
        aria-label="拖动调整重要信息审阅位置"
        @pointerdown="startHomeTileDrag($event, 'briefing')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="9" cy="5" r="1.5"/><circle cx="15" cy="5" r="1.5"/>
          <circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/>
          <circle cx="9" cy="19" r="1.5"/><circle cx="15" cy="19" r="1.5"/>
        </svg>
      </button>
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

    <!-- 常用功能 -->
    <section
      v-if="isHomeModuleVisible('favorites')"
      class="home-tile home-tile--full home-favorites-section"
      data-home-module-id="favorites"
      :style="homeModuleStyle('favorites')"
    >
      <button
        type="button"
        class="home-tile-drag-handle"
        :class="{ 'is-active': homeLayoutDrag.activeId === 'favorites' }"
        title="拖动调整位置"
        aria-label="拖动调整常用功能位置"
        @pointerdown="startHomeTileDrag($event, 'favorites')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="9" cy="5" r="1.5"/><circle cx="15" cy="5" r="1.5"/>
          <circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/>
          <circle cx="9" cy="19" r="1.5"/><circle cx="15" cy="19" r="1.5"/>
        </svg>
      </button>
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
      <div class="app-tiles app-tiles--favorites">
        <button
          v-for="fav in favFeatures"
          :key="fav.id"
          type="button"
          class="app-tile"
          :title="fav.description || fav.title"
          @click="navigateTo(fav)"
        >
          <span class="app-tile__icon" :style="{ background: fav.color }">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path :d="fav.iconPath" /></svg>
          </span>
          <span class="app-tile__label">{{ fav.title }}</span>
        </button>
      </div>
    </section>

    <!-- 新增功能 -->
    <section
      v-if="isHomeModuleVisible('newFeatures') && newFeatureItems.length"
      class="home-tile home-tile--full home-favorites-section home-new-features-section"
      data-home-module-id="newFeatures"
      :style="homeModuleStyle('newFeatures')"
    >
      <button
        type="button"
        class="home-tile-drag-handle"
        :class="{ 'is-active': homeLayoutDrag.activeId === 'newFeatures' }"
        title="拖动调整位置"
        aria-label="拖动调整新增功能位置"
        @pointerdown="startHomeTileDrag($event, 'newFeatures')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="9" cy="5" r="1.5"/><circle cx="15" cy="5" r="1.5"/>
          <circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/>
          <circle cx="9" cy="19" r="1.5"/><circle cx="15" cy="19" r="1.5"/>
        </svg>
      </button>
      <div class="favorites-header">
        <h2 class="favorites-title">
          <svg class="favorites-title-icon new-features-title-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 5v14M5 12h14" />
          </svg>
          新增功能
        </h2>
      </div>
      <div class="app-tiles app-tiles--favorites">
        <button
          v-for="feature in newFeatureItems"
          :key="feature.id"
          type="button"
          class="app-tile"
          :title="feature.description || feature.title"
          @click="navigateTo(feature)"
        >
          <span class="app-tile__icon" :style="{ background: feature.color }">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path :d="feature.iconPath" /></svg>
          </span>
          <span class="app-tile__label">{{ feature.title }}</span>
          <span v-if="feature.tag" class="app-tile__tag">{{ feature.tag }}</span>
        </button>
      </div>
    </section>

    <!-- 全部功能：按分组紧凑九宫格平铺 -->
    <div
      v-if="isHomeModuleVisible('shortcuts')"
      class="home-tile home-tile--full container shortcuts-container"
      data-home-module-id="shortcuts"
      :style="homeModuleStyle('shortcuts')"
    >
      <button
        type="button"
        class="home-tile-drag-handle"
        :class="{ 'is-active': homeLayoutDrag.activeId === 'shortcuts' }"
        title="拖动调整位置"
        aria-label="拖动调整全部功能位置"
        @pointerdown="startHomeTileDrag($event, 'shortcuts')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="9" cy="5" r="1.5"/><circle cx="15" cy="5" r="1.5"/>
          <circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/>
          <circle cx="9" cy="19" r="1.5"/><circle cx="15" cy="19" r="1.5"/>
        </svg>
      </button>
      <section class="shortcuts-section">
        <header class="shortcuts-header">
          <h2 class="section-title">全部功能</h2>
          <span class="shortcuts-count">{{ visibleFeatureCount }} 项功能</span>
        </header>
        <div class="app-folder-stack">
          <div
            v-for="group in featureGroups"
            :key="group.title"
            class="app-folder"
            :style="{ '--folder-accent': folderAccent(group) }"
          >
            <h3 class="app-folder__title">
              <span class="app-folder__title-dot" :style="{ background: folderAccent(group) }"></span>
              {{ group.title }}
              <small>{{ group.items.length }} 项</small>
            </h3>
            <div class="app-tiles">
              <button
                v-for="item in group.items"
                :key="item.id"
                type="button"
                class="app-tile"
                :title="item.description || item.title"
                @click="navigateTo(item)"
              >
                <span class="app-tile__icon" :style="{ background: item.color }">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path :d="item.iconPath" /></svg>
                </span>
                <span class="app-tile__label">{{ item.title }}</span>
                <span v-if="item.tag" class="app-tile__tag">{{ item.tag }}</span>
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>

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

    <!-- AI 待办任务看板瓦片 -->
    <section
      v-if="isHomeModuleVisible('inboxBoard') && canAccessInboxBoard"
      class="home-tile home-tile--inbox home-ai-task-section"
      data-home-module-id="inboxBoard"
      :style="homeModuleStyle('inboxBoard')"
    >
      <button
        type="button"
        class="home-tile-drag-handle"
        :class="{ 'is-active': homeLayoutDrag.activeId === 'inboxBoard' }"
        title="拖动调整位置"
        aria-label="拖动调整AI待办任务看板位置"
        @pointerdown="startHomeTileDrag($event, 'inboxBoard')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="9" cy="5" r="1.5"/><circle cx="15" cy="5" r="1.5"/>
          <circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/>
          <circle cx="9" cy="19" r="1.5"/><circle cx="15" cy="19" r="1.5"/>
        </svg>
      </button>
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
            <div class="ai-task-unconfigured__img-wrap">
              <img src="/assets/images/imap-auth-code-guide.png" alt="如何获取授权码" class="ai-task-unconfigured__img" />
              <span class="ai-task-unconfigured__img-caption">图示：网易企业邮箱客户端授权码获取位置</span>
            </div>
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
              <div
                v-for="(task, idx) in inboxDisplayTasks"
                :key="`${task.id}-${idx}`"
                role="button"
                tabindex="0"
                class="ai-mail-task"
                @click="openInboxTask(task.id)"
                @keydown.enter.prevent="openInboxTask(task.id)"
                @keydown.space.prevent="openInboxTask(task.id)"
              >
                <span class="ai-mail-task__top">
                  <span
                    v-if="inboxEditingDeadlineId !== task.id"
                    class="ai-mail-task__deadline"
                    :class="deadlineClass(task.taskDeadline)"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="10" />
                      <polyline points="12 6 12 12 16 14" />
                    </svg>
                    {{ task.taskDeadline || '未指定截止时间' }}
                    <span v-if="task.taskDeadline && deadlineCountdown(task.taskDeadline)" class="ai-mail-task__countdown">{{ deadlineCountdown(task.taskDeadline) }}</span>
                    <button
                      type="button"
                      class="ai-mail-task__edit"
                      title="修改截止时间"
                      @click.stop="startEditInboxDeadline(task)"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 20h9" />
                        <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z" />
                      </svg>
                    </button>
                  </span>
                  <span v-else class="ai-mail-task__deadline-editor" @click.stop>
                    <input
                      v-model="inboxDeadlineDraft"
                      type="datetime-local"
                      class="ai-mail-task__deadline-input"
                      @keydown.enter.prevent="saveInboxDeadline(task.id)"
                      @keydown.esc.prevent="cancelEditInboxDeadline"
                    />
                    <button type="button" class="ai-mail-task__deadline-save" :disabled="inboxDeadlineSavingId === task.id" @click.stop="saveInboxDeadline(task.id)">
                      保存
                    </button>
                    <button type="button" class="ai-mail-task__deadline-cancel" @click.stop="cancelEditInboxDeadline">
                      取消
                    </button>
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
              </div>
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

    <!-- 天气新闻预览瓦片 -->
    <section
      v-if="isHomeModuleVisible('infoFeed')"
      class="home-tile home-tile--info-feed"
      data-home-module-id="infoFeed"
      :style="homeModuleStyle('infoFeed')"
    >
      <button
        type="button"
        class="home-tile-drag-handle"
        :class="{ 'is-active': homeLayoutDrag.activeId === 'infoFeed' }"
        title="拖动调整天气新闻位置"
        aria-label="拖动调整天气新闻位置"
        @pointerdown="startHomeTileDrag($event, 'infoFeed')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="9" cy="5" r="1.5"/><circle cx="15" cy="5" r="1.5"/>
          <circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/>
          <circle cx="9" cy="19" r="1.5"/><circle cx="15" cy="19" r="1.5"/>
        </svg>
      </button>
      <article class="dashboard-card info-feed-preview-card">
        <header class="dashboard-card__header info-feed-preview-card__header">
          <h2 class="dashboard-card__title">
            <span class="dashboard-card__icon dashboard-card__icon--info-feed" aria-hidden="true">
              {{ weatherIcon(homeWeatherNow?.now?.text) }}
            </span>
            <span class="dashboard-card__title-text">天气新闻</span>
            <span class="dashboard-card__badge" v-if="homeNewsItems.length">{{ homeNewsItems.length }}</span>
          </h2>
          <div class="wall-preview-actions">
            <button type="button" class="wall-preview-refresh" title="刷新" @click="loadInfoFeedHome">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23 4 23 10 17 10"/>
                <polyline points="1 20 1 14 7 14"/>
                <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4-4.64 4.36A9 9 0 0 1 3.51 15"/>
              </svg>
            </button>
            <router-link to="/info-feed" class="wall-preview-viewall">查看全部</router-link>
          </div>
        </header>
        <div class="info-feed-preview-body" @click="router.push('/info-feed')">
          <div v-if="infoFeedHomeLoading" class="dashboard-empty"><p>加载中...</p></div>
          <template v-else>
            <div
              v-if="homeWeatherNow?.now || homeForecastLine"
              class="info-feed-weather-mini"
            >
              <div
                class="info-feed-weather-icon"
                :class="weatherIconClass(homeWeatherNow?.now?.text || homeDailyItems[0]?.textDay)"
              >
                {{ weatherIcon(homeWeatherNow?.now?.text || homeDailyItems[0]?.textDay) }}
              </div>
              <div class="info-feed-weather-text">
                <template v-if="homeWeatherNow?.now">
                  <strong>{{ homeWeatherNow.now.temp }}°C</strong>
                  <span>{{ homeWeatherNow.now.text }} · {{ homeWeatherNow.now.windDir || '-' }} {{ homeWeatherNow.now.windScale || '-' }}级</span>
                </template>
                <small v-if="homeForecastLine" class="info-feed-forecast-line">预报 {{ homeForecastLine }}</small>
                <small>哈尔滨电机厂有限责任公司<template v-if="homeWeatherNow?.updateTime"> · {{ homeWeatherNow.updateTime }}</template></small>
              </div>
            </div>
            <div v-else class="dashboard-empty">
              <p>等待中转服务推送天气数据</p>
            </div>
            <div class="info-feed-news-mini" v-if="homeNewsItems.length">
              <button
                v-for="item in homeNewsItems"
                :key="item.uniquekey || item.title"
                type="button"
                @click.stop="router.push('/info-feed')"
              >
                <span>{{ item.category || '国际' }}</span>
                <strong>{{ item.title }}</strong>
              </button>
            </div>
            <div v-else class="dashboard-empty"><p>等待中转服务推送国际新闻</p></div>
          </template>
        </div>
      </article>
    </section>

    <!-- 吐槽墙预览瓦片 -->
    <section
      v-if="isHomeModuleVisible('wall')"
      class="home-tile home-tile--wall home-wall-section"
      data-home-module-id="wall"
      :style="homeModuleStyle('wall')"
    >
      <button
        type="button"
        class="home-tile-drag-handle"
        :class="{ 'is-active': homeLayoutDrag.activeId === 'wall' }"
        title="拖动调整位置"
        aria-label="拖动调整吐槽墙位置"
        @pointerdown="startHomeTileDrag($event, 'wall')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="9" cy="5" r="1.5"/><circle cx="15" cy="5" r="1.5"/>
          <circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/>
          <circle cx="9" cy="19" r="1.5"/><circle cx="15" cy="19" r="1.5"/>
        </svg>
      </button>
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
          <div v-else-if="!wallBarrageRows.length" class="dashboard-empty"><p>暂无吐槽</p></div>
          <div
            v-else
            class="wall-barrage-stage"
            @click="router.push('/feedback')"
          >
            <div
              v-for="row in wallBarrageRows"
              :key="row.key"
              class="wall-barrage-row"
              :style="row.style"
            >
              <div class="wall-barrage-track">
                <button
                  v-for="item in row.items"
                  :key="`${row.key}-${item._seq}`"
                  type="button"
                  class="wall-barrage-item"
                  :class="[`wall-barrage-item--${item.resolved || 0}`, { liked: wallLikedIds.has(item.id), animating: wallLikeAnimating.has(item.id) }]"
                  :style="{ '--item-accent': item._accent }"
                  :title="item._title"
                  @click.stop="router.push('/feedback')"
                >
                  <span class="wall-barrage-status">{{ wallResolveLabel(item.resolved) }}</span>
                  <span class="wall-barrage-text">{{ item._displayText }}</span>
                  <span
                    class="wall-barrage-like"
                    title="点赞"
                    @click.stop="doWallLike(item.id)"
                  >
                    <span class="wall-like-icon">👍</span>
                    <span class="wall-like-count">{{ item.likeCount || 0 }}</span>
                  </span>
                </button>
              </div>
            </div>
            <div class="wall-barrage-vignette wall-barrage-vignette--left"></div>
            <div class="wall-barrage-vignette wall-barrage-vignette--right"></div>
          </div>
        </div>
      </article>
    </section>

    <!-- 人员出勤可视化缩略瓦片 -->
    <section
      v-if="isHomeModuleVisible('personnelVisual')"
      class="home-tile home-tile--personnel-visual"
      data-home-module-id="personnelVisual"
      :style="homeModuleStyle('personnelVisual')"
    >
      <button
        type="button"
        class="home-tile-drag-handle"
        :class="{ 'is-active': homeLayoutDrag.activeId === 'personnelVisual' }"
        title="拖动调整位置"
        aria-label="拖动调整人员出勤可视化位置"
        @pointerdown="startHomeTileDrag($event, 'personnelVisual')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="9" cy="5" r="1.5"/><circle cx="15" cy="5" r="1.5"/>
          <circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/>
          <circle cx="9" cy="19" r="1.5"/><circle cx="15" cy="19" r="1.5"/>
        </svg>
      </button>
      <article class="dashboard-card personnel-visual-card">
        <header class="dashboard-card__header personnel-visual-card__header">
          <h2 class="dashboard-card__title">
            <span class="dashboard-card__icon dashboard-card__icon--personnel-visual" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="4" width="18" height="14" rx="2"/>
                <path d="M8 18v2m8-2v2M7 9h3m4 0h3M7 13h10"/>
              </svg>
            </span>
            <span class="dashboard-card__title-text">人员出勤可视化</span>
            <span class="dashboard-card__badge" v-if="personnelVisualSummary.total">{{ personnelVisualSummary.total }}</span>
          </h2>
          <div class="personnel-visual-actions">
            <button type="button" class="wall-preview-refresh" title="刷新" @click="loadPersonnelVisualPreview">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23 4 23 10 17 10"/>
                <polyline points="1 20 1 14 7 14"/>
                <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4-4.64 4.36A9 9 0 0 1 3.51 15"/>
              </svg>
            </button>
            <router-link to="/attendance/personnel-visualization" class="wall-preview-viewall">
              查看全部
            </router-link>
          </div>
        </header>
        <div class="personnel-visual-body" @click="router.push('/attendance/personnel-visualization')">
          <div v-if="personnelVisualLoading" class="dashboard-empty"><p>加载中...</p></div>
          <div v-else-if="personnelVisualError" class="dashboard-empty"><p>{{ personnelVisualError }}</p></div>
          <template v-else>
            <div class="personnel-mini-summary">
              <select
                v-if="personnelVisualAvailableDepartments.length > 1"
                v-model="personnelVisualSelectedDept"
                class="personnel-mini-dept-select"
                title="切换科室"
                @click.stop
                @change="loadPersonnelVisualPreview"
              >
                <option v-for="dept in personnelVisualAvailableDepartments" :key="dept" :value="dept">{{ dept }}</option>
              </select>
              <span v-else class="personnel-mini-dept">{{ personnelVisualScene.department || userLsys || '本科室' }}</span>
              <span>在岗 {{ personnelVisualSummary.present }}</span>
              <span>公出 {{ personnelVisualSummary.businessTrip }}</span>
              <span>请假 {{ personnelVisualSummary.leave }}</span>
              <span>暂无 {{ personnelVisualSummary.noRecord }}</span>
            </div>
            <div v-if="personnelVisualPeople.length" class="personnel-mini-office">
              <div class="personnel-mini-desks">
                <article
                  v-for="(person, index) in personnelVisualPeople"
                  :key="person.gh || person.name || index"
                  class="personnel-mini-desk"
                  :class="[`personnel-mini-desk--${person.status || 'no_record'}`, `personnel-mini-desk--${personnelGenderClass(person)}`]"
                  :style="{ '--desk-delay': `${index * 0.1}s` }"
                  :title="`${person.name || ''}：${person.statusLabel || ''}`"
                >
                  <div class="personnel-mini-name">{{ person.name }}</div>
                  <div class="personnel-mini-workstation">
                    <div class="personnel-mini-screen"><span></span></div>
                    <div class="personnel-mini-worker">
                      <i class="hair"></i><i class="head"></i><i class="body"></i><i class="arm arm-left"></i><i class="arm arm-right"></i>
                    </div>
                    <div v-if="person.status === 'business_trip'" class="personnel-mini-trip">
                      <i></i><b></b>
                    </div>
                    <div v-if="person.status === 'leave'" class="personnel-mini-leave">假</div>
                    <div class="personnel-mini-table"></div>
                  </div>
                </article>
              </div>
            </div>
            <div v-else class="dashboard-empty"><p>暂无人员数据</p></div>
          </template>
        </div>
      </article>
    </section>

    <div v-if="homeLayoutEditorVisible" class="modal-overlay" @click.self="closeHomeLayoutEditor">
      <div class="home-layout-modal">
        <div class="home-layout-modal__header">
          <div>
            <h2>首页布局</h2>
            <p>调整首页模块顺序，关闭暂时不需要的模块。</p>
          </div>
          <button type="button" class="home-layout-modal__close" aria-label="关闭" @click="closeHomeLayoutEditor">&times;</button>
        </div>
        <div class="home-layout-modal__body">
          <div
            v-for="item in homeLayoutConfigurableDraft"
            :key="item.id"
            class="home-layout-item"
            :class="{ disabled: !item.visible }"
          >
            <label class="home-layout-item__toggle">
              <input
                type="checkbox"
                :checked="item.visible"
                :disabled="item.visible && homeLayoutVisibleDraftCount <= 1"
                @change="toggleHomeLayoutDraftItem(item.id)"
              />
              <span></span>
            </label>
            <div class="home-layout-item__main">
              <strong>{{ homeModuleMeta(item.id).label }}</strong>
              <small>{{ homeModuleMeta(item.id).description }}</small>
            </div>
            <span v-if="!isHomeModuleRuntimeAvailable(item.id)" class="home-layout-item__badge">当前无内容</span>
            <div class="home-layout-item__actions">
              <button type="button" :disabled="isHomeLayoutDraftEdge(item.id, 'first')" title="上移" @click="moveHomeLayoutDraftItem(item.id, -1)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 15l-6-6-6 6"/></svg>
              </button>
              <button type="button" :disabled="isHomeLayoutDraftEdge(item.id, 'last')" title="下移" @click="moveHomeLayoutDraftItem(item.id, 1)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>
              </button>
            </div>
          </div>
        </div>
        <div class="home-layout-modal__footer">
          <button type="button" class="home-layout-reset" @click="resetHomeLayoutDraft">恢复默认</button>
          <div class="home-layout-modal__btns">
            <button type="button" class="btn-fav-cancel" @click="closeHomeLayoutEditor">取消</button>
            <button type="button" class="btn-fav-save" @click="saveHomeLayoutEditor">保存</button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getLeaveList,
  getOvertimeList,
  getBusinessTripList,
  getUploadConfig,
} from '@/api/attendance'
import { getMySealApplications } from '@/api/seal'
import { getLeaderBriefing } from '@/api/admin'
import { getContacts } from '@/api/contacts'
import { getWallList, likeWall } from '@/api/feedback'
import { getPersonnelAttendanceScene } from '@/api/personnelVisualization'
import { getDbManagerPermission } from '@/api/dbManager'
import { getNewsList, getWeatherDaily, getWeatherNow } from '@/api/infoFeed'
import { analyzeInboxEmails, listInboxTasks, getInboxConfig, completeInboxTask, syncInboxEmails, getInboxEmailDetail, updateInboxTaskDeadline } from '@/api/inboxEmail'
import { getSSOLink } from '@/api/sso'
import { useWorkplaceTodos, refreshWorkplaceTodos } from '@/composables/useWorkplaceTodos'
import { isMinisterLevel, isMinisterOrDeptLeader, isDirectorLevel, jbMatch, canAccessLeaderDashboard } from '@/utils/roleMatch'
import { DEFAULT_NEWS_TYPE, DEFAULT_WEATHER_LOCATION, shortWeatherDate, weatherIcon } from '@/utils/infoFeedDisplay'
const route = useRoute()
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
const inboxEditingDeadlineId = ref(null)
const inboxDeadlineDraft = ref('')
const inboxDeadlineSavingId = ref(null)
let inboxTaskRefreshTimer = null

// 吐槽墙首页预览
const wallList = ref([])
const wallLoading = ref(false)
const WALL_BARRAGE_COLORS = [
  '#38bdf8', '#fb7185', '#f59e0b', '#34d399', '#a78bfa', '#f97316', '#22c55e', '#60a5fa',
]

const wallBarrageItems = computed(() => {
  return (wallList.value || []).slice(0, 3).map((w, i) => ({
    ...w,
    _accent: WALL_BARRAGE_COLORS[i % WALL_BARRAGE_COLORS.length],
    _displayText: buildWallBarrageText(w),
    _title: buildWallBarrageTitle(w),
  }))
})

const wallBarrageRows = computed(() => {
  const source = wallBarrageItems.value
  if (!source.length) return []
  return source.map((item, rowIndex) => {
    return {
      key: `row-${rowIndex}`,
      items: [{ ...item, _seq: `${item.id}-0` }],
      style: {
        '--row-top': `${24 + rowIndex * 26}%`,
        '--row-duration': `${22 + rowIndex * 3}s`,
        '--row-delay': `${rowIndex * -5}s`,
      },
    }
  })
})

const infoFeedHomeLoading = ref(false)
const homeWeatherNow = ref(null)
const homeWeatherDaily = ref(null)
const homeNewsList = ref(null)
const homeDailyItems = computed(() => (homeWeatherDaily.value?.daily || []).slice(0, 3))
const homeForecastLine = computed(() =>
  homeDailyItems.value
    .map((day) => `${shortWeatherDate(day.fxDate)} ${day.tempMin}~${day.tempMax}°${day.textDay || ''}`)
    .join(' · ')
)
const homeNewsItems = computed(() => (homeNewsList.value?.result?.data || homeNewsList.value?.data || []).slice(0, 3))

function weatherIconClass(text = '') {
  const value = String(text)
  if (/雷|电/.test(value)) return 'weather-visual--storm'
  if (/雪|冻雨|冰粒/.test(value)) return 'weather-visual--snow'
  if (/雨|阵雨|暴雨|小雨|中雨|大雨/.test(value)) return 'weather-visual--rain'
  if (/雾|霾|沙|尘|浮尘|扬沙/.test(value)) return 'weather-visual--fog'
  if (/阴|云/.test(value)) return 'weather-visual--cloud'
  if (/晴/.test(value)) return 'weather-visual--sun'
  return 'weather-visual--default'
}

async function loadInfoFeedHome() {
  infoFeedHomeLoading.value = true
  try {
    const [weather, daily, news] = await Promise.allSettled([
      getWeatherNow(DEFAULT_WEATHER_LOCATION),
      getWeatherDaily('7d', DEFAULT_WEATHER_LOCATION),
      getNewsList({ type: DEFAULT_NEWS_TYPE, page: '1' }),
    ])
    homeWeatherNow.value = weather.status === 'fulfilled' ? weather.value : null
    homeWeatherDaily.value = daily.status === 'fulfilled' ? daily.value : null
    homeNewsList.value = news.status === 'fulfilled' ? news.value : null
  } finally {
    infoFeedHomeLoading.value = false
  }
}

function wallResolveLabel(v) {
  return Number(v) === 3 ? '已解决' : Number(v) === 2 ? '已回复' : Number(v) === 1 ? '处理中' : '未处理'
}

function buildWallBarrageText(item) {
  let text = (item?.content || '').toString().replace(/\s+/g, ' ').trim()
  if (text.length > 42) text = `${text.slice(0, 42)}...`
  const latest = item?.replies?.length ? item.replies[item.replies.length - 1] : null
  if (latest?.replyContent) {
    const reply = latest.replyContent.toString().replace(/\s+/g, ' ').trim()
    text += ` / 回复：${reply.length > 18 ? `${reply.slice(0, 18)}...` : reply}`
  }
  return text || '匿名吐槽'
}

function buildWallBarrageTitle(item) {
  const text = (item?.content || '').toString().replace(/\s+/g, ' ').trim()
  const latest = item?.replies?.length ? item.replies[item.replies.length - 1] : null
  return latest?.replyContent ? `${text}\n回复：${latest.replyContent}` : text
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

// 人员出勤可视化首页缩略
const personnelVisualLoading = ref(false)
const personnelVisualError = ref('')
const personnelVisualSelectedDept = ref('')
const personnelVisualScene = ref({
  department: '',
  generatedAt: '',
  people: [],
  availableDepartments: [],
  summary: { total: 0, present: 0, businessTrip: 0, leave: 0, leavePending: 0, noRecord: 0 },
})

const personnelVisualAvailableDepartments = computed(() =>
  (personnelVisualScene.value.availableDepartments || []).filter(Boolean)
)

const personnelVisualSummary = computed(() => ({
  total: 0,
  present: 0,
  businessTrip: 0,
  leave: 0,
  leavePending: 0,
  noRecord: 0,
  ...(personnelVisualScene.value.summary || {}),
}))

const personnelVisualPeople = computed(() => {
  const order = { present: 0, business_trip: 1, leave: 2, no_record: 3 }
  return [...(personnelVisualScene.value.people || [])]
    .sort((a, b) => (order[a.status] ?? 9) - (order[b.status] ?? 9))
})

function todayLocalDate() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function personnelGenderClass(person) {
  if (person?.gender === 'female' || String(person?.xbie || '').includes('女')) return 'female'
  if (person?.gender === 'male' || String(person?.xbie || '').includes('男')) return 'male'
  return 'unknown'
}

async function loadPersonnelVisualPreview() {
  const currentUser = (userName.value || '').trim()
  if (!currentUser) {
    personnelVisualError.value = '未获取到当前登录用户'
    return
  }
  personnelVisualLoading.value = true
  personnelVisualError.value = ''
  try {
    const res = await getPersonnelAttendanceScene({
      current_user: currentUser,
      department: personnelVisualSelectedDept.value || undefined,
      target_date: todayLocalDate(),
    })
    if (res?.success) {
      personnelVisualScene.value = res
      if (!personnelVisualSelectedDept.value && res.department) {
        personnelVisualSelectedDept.value = res.department
      }
    } else {
      personnelVisualError.value = res?.message || '加载失败'
      personnelVisualScene.value = { ...personnelVisualScene.value, people: [] }
    }
  } catch (e) {
    personnelVisualError.value = e?.response?.data?.detail || e?.message || '加载失败'
    personnelVisualScene.value = { ...personnelVisualScene.value, people: [] }
  } finally {
    personnelVisualLoading.value = false
  }
}

const canSeeBriefing = ref(false)
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
  { value: 'mail', label: '邮件' },
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
  if (mode === 'mail') {
    return arr.filter(i => i?.type === 'mail')
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
  if (type === 'hxp_overtime') return '值班换休'
  if (type === 'hxp') return '公出节假日领取'
  if (type === 'hxp_batch') return '系统批量增加'
  if (type === 'trip') return '公出'
  if (type === 'mail') return '邮件'
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
  } else if (item.type === 'mail') {
    router.push('/admin/email')
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
  } catch { /* 无权限会403，忽略 */ }
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
      return canAccessLeaderDashboard({
        name,
        jb,
        lsys,
        admin1: a1,
        admin2: a2,
      })
    case 'overtimePay':
      return true
    case 'exceptions':
      return isAdmin1 || (!!d && name === d) || isMinisterOrDeptLeader(jb)
    case 'hxpRecords':
      return isMinisterLevel(jb) || (!!a2 && name === a2)
    case 'employeeAdmin':
      return isAdmin1 || isMinisterOrDeptLeader(jb) || (!!a2 && name === a2)
    case 'rotorBladeBalance':
      return lsys === '焊接工艺室' || lsys === '部办'
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

/** 与 Contacts.vue 科室下拉一致 */
const CONTACT_HOME_DEPT_OPTIONS = [
  '部办',
  '综合技术室', '工具技术室', '数控编程室', '智能制造技术室',
  '水发工艺室', '水轮机工艺室', '汽发工艺室', '焊接工艺室', '非标技术室',
]

const contactsHomeDepartments = ref([])
const contactsHomeLoading = ref(false)
const contactsHomeKeyword = ref('')
const contactsHomeDept = ref('')
const contactsHomeTotal = ref(0)
let contactsHomeSearchTimer = null

const contactsHomeFlat = computed(() => {
  const rows = []
  for (const d of contactsHomeDepartments.value || []) {
    for (const p of d.members || []) {
      rows.push({ ...p, deptName: d.name })
    }
  }
  return rows
})

function contactsJbClass(jb) {
  if (!jb) return ''
  if (/经理/.test(jb)) return 'jb-manager'
  if (/主任/.test(jb)) return 'jb-director'
  if (/组长/.test(jb)) return 'jb-leader'
  return 'jb-default'
}

async function loadContactsHome() {
  contactsHomeLoading.value = true
  try {
    const params = {}
    if (contactsHomeDept.value) params.department = contactsHomeDept.value
    const kw = contactsHomeKeyword.value.trim()
    if (kw) params.keyword = kw
    const res = await getContacts(params)
    if (res?.success) {
      const deps = res.departments || []
      contactsHomeDepartments.value = deps
      contactsHomeTotal.value =
        typeof res.total === 'number'
          ? res.total
          : deps.reduce((n, d) => n + (Array.isArray(d.members) ? d.members.length : 0), 0)
    }
  } catch (e) {
    console.error('首页通讯录加载失败:', e)
  } finally {
    contactsHomeLoading.value = false
  }
}

function onContactsHomeSearchInput() {
  if (contactsHomeSearchTimer) clearTimeout(contactsHomeSearchTimer)
  contactsHomeSearchTimer = setTimeout(() => loadContactsHome(), 300)
}

function clearContactsHomeSearch() {
  contactsHomeKeyword.value = ''
  loadContactsHome()
}

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
        id: 'personnel-visualization',
        title: '人员出勤可视化',
        description: '以办公室工位动画查看本科室在岗、公出和打卡状态',
        path: '/attendance/personnel-visualization',
        color: 'linear-gradient(135deg, #0ea5e9 0%, #22c55e 100%)',
        tag: '新功能',
        iconPath: 'M3 4h18v14H3V4zm4 14v2m10-2v2M8 8a2 2 0 100 4 2 2 0 000-4zm8 0a2 2 0 100 4 2 2 0 000-4z'
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
        id: 'reports-hub',
        title: '报表汇聚',
        description: '集中导出考勤、绩效、排班和台账报表',
        path: '/reports-hub',
        color: 'linear-gradient(135deg, #0f766e 0%, #84cc16 100%)',
        tag: '新功能',
        iconPath: 'M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8zM14 2v6h6M8 13h8M8 17h6'
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
        title: '管理驾驶舱',
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
        id: 'bid-templates',
        title: '工艺投标文件管理',
        description: '维护投标模板最新版本，记录更新要点并支持历史版本下载',
        path: '/file/bid-templates',
        color: 'linear-gradient(135deg, #0ea5e9 0%, #14b8a6 100%)',
        tag: '新功能',
        iconPath: 'M4 4h16v16H4V4zm4 4h8M8 12h8M8 16h5'
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
        id: 'rotor-blade-balance',
        title: '转轮叶片配重',
        description: '按叶片重量优化排列，计算综合偏心矩',
        path: '/weldoa/ypp_main',
        permission: 'rotorBladeBalance',
        color: 'linear-gradient(135deg, #06b6d4 0%, #2563eb 100%)',
        tag: '新功能',
        iconPath: 'M12 3v18M3 12h18M5.64 5.64l12.72 12.72M18.36 5.64L5.64 18.36M12 21a9 9 0 100-18 9 9 0 000 18z'
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
        id: 'seal-apply',
        title: '部门用印申请',
        description: '提交用印申请、审批用印、查看用印记录',
        path: '/seal/apply',
        color: 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)',
        tag: '新功能',
        iconPath: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'
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
        title: '系统管理员',
        description: '系统配置、排班邮件（功能/时间/收件人）与各组件状态一览',
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
const DEFAULT_FAV_IDS = ['attendance', 'businesstrip', 'filenumbering', 'seal-apply']

function _favStorageKey() {
  const name = (userName.value || '').trim()
  return name ? `home_fav_ids_${name}` : 'home_fav_ids'
}

function loadFavIds() {
  try {
    const raw = localStorage.getItem(_favStorageKey())
    if (raw) {
      const arr = JSON.parse(raw)
      if (Array.isArray(arr) && arr.length) {
        // 通讯录已改为首页独立瓦片，从常用入口中移除避免重复
        const next = arr.filter(id => id !== 'contacts')
        if (next.length !== arr.length) {
          try {
            localStorage.setItem(_favStorageKey(), JSON.stringify(next.length ? next : DEFAULT_FAV_IDS))
          } catch { /* ignore */ }
          return next.length ? next : [...DEFAULT_FAV_IDS]
        }
        return arr
      }
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

const newFeatureItems = computed(() => {
  return rawFeatureGroups
    .flatMap(group => group.items)
    .filter(item => item.tag === '新功能')
    .filter(item => canShowFeature(item.permission))
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

// ==================== 首页布局 ====================
// 拆分原 dashboard / focusCards 为更细的 5 个瓦片，便于"恒定大小三栏"以及后续个性化排班
const HOME_LAYOUT_MODULES = [
  { id: 'todo', label: '待办事项', description: '需要我处理的待办与审批' },
  { id: 'request', label: '我的申请流程', description: '我提交的待审批 / 审批中申请' },
  { id: 'contactsCard', label: '部门通讯录', description: '科室人员手机、座机等快捷查看' },
  { id: 'briefing', label: '重要信息审阅', description: '部长/副经理级别可见的重要换休、公出信息滚动审阅' },
  { id: 'inboxBoard', label: 'AI 待办任务看板', description: '由企业邮箱标记自动识别出的待办任务' },
  { id: 'infoFeed', label: '天气新闻', description: '哈电实时天气、预报与国际新闻摘要' },
  { id: 'wall', label: '吐槽墙', description: '匿名吐槽与互动' },
  { id: 'personnelVisual', label: '人员出勤可视化', description: '本科室在岗、公出、请假状态办公室缩略预览' },
  { id: 'favorites', label: '常用功能', description: '用户自定义的常用功能入口' },
  { id: 'newFeatures', label: '新增功能', description: '最近上线的新功能入口' },
  { id: 'shortcuts', label: '全部功能', description: '按分类平铺展示全部可用功能' },
]

// 旧 module id → 新 module id 列表（用于迁移老的本地配置）
const HOME_LAYOUT_MIGRATION = {
  dashboard: ['todo', 'request'],
  focusCards: ['inboxBoard', 'wall'],
}

function defaultHomeLayout() {
  return HOME_LAYOUT_MODULES.map(item => ({ id: item.id, visible: true }))
}

function homeLayoutStorageKey() {
  const name = (userName.value || '').trim()
  return name ? `home_layout_modules_${name}` : 'home_layout_modules'
}

function normalizeHomeLayout(value) {
  const validIds = new Set(HOME_LAYOUT_MODULES.map(item => item.id))
  const saved = Array.isArray(value) ? value : []
  const result = []
  const seen = new Set()
  for (const item of saved) {
    const id = typeof item === 'string' ? item : item?.id
    const visible = typeof item === 'object' && item.visible === false ? false : true
    // 旧 module → 拆分为多个新 module，按声明顺序紧挨原位置
    const migratedIds = HOME_LAYOUT_MIGRATION[id]
    const targetIds = migratedIds && migratedIds.length ? migratedIds : [id]
    for (const targetId of targetIds) {
      if (!validIds.has(targetId) || seen.has(targetId)) continue
      result.push({ id: targetId, visible })
      seen.add(targetId)
    }
  }
  for (const item of HOME_LAYOUT_MODULES) {
    if (!seen.has(item.id)) result.push({ id: item.id, visible: true })
  }
  if (!result.some(item => item.visible)) {
    result[0].visible = true
  }
  return result
}

function loadHomeLayout() {
  try {
    const raw = localStorage.getItem(homeLayoutStorageKey())
    if (raw) return normalizeHomeLayout(JSON.parse(raw))
  } catch { /* ignore */ }
  return defaultHomeLayout()
}

const homeLayout = ref(loadHomeLayout())
const homeLayoutEditorVisible = ref(false)
const homeLayoutDraft = ref(defaultHomeLayout())
const homeLayoutDrag = reactive({
  activeId: '',
  moved: false,
  startX: 0,
  startY: 0,
})

function isHomeModuleConfigurable(id) {
  if (id === 'briefing') return canSeeBriefing.value
  return true
}

const homeLayoutConfigurableDraft = computed(() => {
  return homeLayoutDraft.value.filter(item => isHomeModuleConfigurable(item.id))
})

const homeLayoutVisibleDraftCount = computed(() => {
  return homeLayoutConfigurableDraft.value.filter(item => item.visible).length
})

function homeModuleMeta(id) {
  return HOME_LAYOUT_MODULES.find(item => item.id === id) || { id, label: id, description: '' }
}

function homeModuleConfig(id) {
  return homeLayout.value.find(item => item.id === id)
}

function isHomeModuleVisible(id) {
  return homeModuleConfig(id)?.visible !== false
}

function homeModuleStyle(id) {
  const index = homeLayout.value.findIndex(item => item.id === id)
  return { order: index >= 0 ? (index + 1) * 10 : 999 }
}

function persistHomeLayout() {
  const next = normalizeHomeLayout(homeLayout.value)
  homeLayout.value = next
  try {
    localStorage.setItem(homeLayoutStorageKey(), JSON.stringify(next))
  } catch { /* ignore */ }
}

function moveHomeLayoutItem(id, targetId) {
  if (!id || !targetId || id === targetId) return false
  const arr = [...homeLayout.value]
  const fromIndex = arr.findIndex(item => item.id === id)
  const toIndex = arr.findIndex(item => item.id === targetId)
  if (fromIndex < 0 || toIndex < 0) return false
  const [item] = arr.splice(fromIndex, 1)
  arr.splice(toIndex, 0, item)
  homeLayout.value = arr
  return true
}

function homeTileIdFromPoint(clientX, clientY) {
  const el = document.elementFromPoint(clientX, clientY)
  const tile = el?.closest?.('[data-home-module-id]')
  const id = tile?.dataset?.homeModuleId || ''
  return id && isHomeModuleVisible(id) ? id : ''
}

function cleanupHomeTileDrag(save = false) {
  window.removeEventListener('pointermove', onHomeTileDragMove)
  window.removeEventListener('pointerup', onHomeTileDragEnd)
  window.removeEventListener('pointercancel', onHomeTileDragEnd)
  document.body.classList.remove('home-tile-dragging')
  if (save && homeLayoutDrag.moved) persistHomeLayout()
  homeLayoutDrag.activeId = ''
  homeLayoutDrag.moved = false
  homeLayoutDrag.startX = 0
  homeLayoutDrag.startY = 0
}

function onHomeTileDragMove(event) {
  if (!homeLayoutDrag.activeId) return
  event.preventDefault()
  const dx = Math.abs(event.clientX - homeLayoutDrag.startX)
  const dy = Math.abs(event.clientY - homeLayoutDrag.startY)
  if (dx + dy < 6) return
  const targetId = homeTileIdFromPoint(event.clientX, event.clientY)
  if (moveHomeLayoutItem(homeLayoutDrag.activeId, targetId)) {
    homeLayoutDrag.moved = true
  }
}

function onHomeTileDragEnd() {
  cleanupHomeTileDrag(true)
}

function startHomeTileDrag(event, id) {
  if (event.button != null && event.button !== 0) return
  if (!isHomeModuleVisible(id)) return
  event.preventDefault()
  event.stopPropagation()
  cleanupHomeTileDrag(false)
  homeLayoutDrag.activeId = id
  homeLayoutDrag.startX = event.clientX
  homeLayoutDrag.startY = event.clientY
  document.body.classList.add('home-tile-dragging')
  window.addEventListener('pointermove', onHomeTileDragMove, { passive: false })
  window.addEventListener('pointerup', onHomeTileDragEnd)
  window.addEventListener('pointercancel', onHomeTileDragEnd)
}

function isHomeModuleRuntimeAvailable(id) {
  if (id === 'briefing') return canSeeBriefing.value && briefingItems.value.length > 0
  if (id === 'newFeatures') return newFeatureItems.value.length > 0
  if (id === 'inboxBoard') return canAccessInboxBoard.value
  return true
}

function openHomeLayoutEditor() {
  homeLayoutDraft.value = homeLayout.value.map(item => ({ ...item }))
  homeLayoutEditorVisible.value = true
}

function closeHomeLayoutEditor() {
  homeLayoutEditorVisible.value = false
}

function toggleHomeLayoutDraftItem(id) {
  const item = homeLayoutDraft.value.find(row => row.id === id)
  if (!item) return
  if (item.visible && homeLayoutVisibleDraftCount.value <= 1) return
  item.visible = !item.visible
}

function isHomeLayoutDraftEdge(id, edge) {
  const index = homeLayoutConfigurableDraft.value.findIndex(item => item.id === id)
  if (edge === 'first') return index <= 0
  if (edge === 'last') return index < 0 || index >= homeLayoutConfigurableDraft.value.length - 1
  return false
}

function moveHomeLayoutDraftItem(id, direction) {
  const currentIndex = homeLayoutConfigurableDraft.value.findIndex(item => item.id === id)
  const targetItem = homeLayoutConfigurableDraft.value[currentIndex + direction]
  if (currentIndex < 0 || !targetItem) return
  const arr = [...homeLayoutDraft.value]
  const fromIndex = arr.findIndex(item => item.id === id)
  const toIndex = arr.findIndex(item => item.id === targetItem.id)
  if (fromIndex < 0 || toIndex < 0) return
  const [item] = arr.splice(fromIndex, 1)
  arr.splice(toIndex, 0, item)
  homeLayoutDraft.value = arr
}

function resetHomeLayoutDraft() {
  homeLayoutDraft.value = defaultHomeLayout()
}

function saveHomeLayoutEditor() {
  const next = normalizeHomeLayout(homeLayoutDraft.value)
  homeLayout.value = next
  persistHomeLayout()
  homeLayoutEditorVisible.value = false
}

function handleOpenHomeLayoutSettings() {
  openHomeLayoutEditor()
}

watch(userName, () => {
  homeLayout.value = loadHomeLayout()
})

watch(
  () => route.query.homeLayoutSettings,
  (value) => {
    if (!value) return
    openHomeLayoutEditor()
    const nextQuery = { ...route.query }
    delete nextQuery.homeLayoutSettings
    router.replace({ path: route.path, query: nextQuery }).catch(() => {})
  },
  { immediate: true }
)

watch(
  () => isHomeModuleVisible('contactsCard'),
  (vis, was) => {
    if (vis && was === false) void loadContactsHome()
  }
)

watch(
  () => isHomeModuleVisible('personnelVisual'),
  (vis, was) => {
    if (vis && was === false && !personnelVisualScene.value.people?.length) {
      void loadPersonnelVisualPreview()
    }
  }
)

watch(
  () => isHomeModuleVisible('infoFeed'),
  (vis, was) => {
    if (vis && was === false && !homeWeatherNow.value && !homeNewsItems.value.length) {
      void loadInfoFeedHome()
    }
  }
)

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

function deadlineToInputValue(deadline) {
  const text = String(deadline || '').trim()
  if (!text) return ''
  const normalized = text.replace(/\//g, '-').replace(/\s+/, 'T')
  if (/^\d{4}-\d{1,2}-\d{1,2}$/.test(normalized)) {
    return `${normalized}T00:00`
  }
  const match = normalized.match(/^(\d{4}-\d{1,2}-\d{1,2})T(\d{1,2}:\d{2})/)
  return match ? `${match[1]}T${match[2]}` : ''
}

function inputValueToDeadline(value) {
  return String(value || '').trim().replace('T', ' ')
}

function startEditInboxDeadline(task) {
  inboxTaskMarqueePaused.value = true
  inboxEditingDeadlineId.value = task.id
  inboxDeadlineDraft.value = deadlineToInputValue(task.taskDeadline)
}

function cancelEditInboxDeadline() {
  inboxEditingDeadlineId.value = null
  inboxDeadlineDraft.value = ''
  inboxDeadlineSavingId.value = null
}

async function saveInboxDeadline(id) {
  const name = (userName.value || '').trim()
  if (!name || !id || inboxDeadlineSavingId.value) return
  const taskDeadline = inputValueToDeadline(inboxDeadlineDraft.value)
  inboxDeadlineSavingId.value = id
  try {
    const res = await updateInboxTaskDeadline({ current_user: name, id, task_deadline: taskDeadline })
    if (res && res.success) {
      inboxTasks.value = inboxTasks.value.map(task => (
        task.id === id ? { ...task, taskDeadline: res.taskDeadline || '' } : task
      ))
      inboxTaskMsg.value = res.message || '截止时间已更新'
      inboxTaskMsgType.value = 'success'
      cancelEditInboxDeadline()
      await loadInboxTasks()
    } else {
      inboxTaskMsg.value = (res && res.message) || '更新截止时间失败'
      inboxTaskMsgType.value = 'error'
    }
  } catch (e) {
    inboxTaskMsg.value = e?.message || '更新截止时间失败'
    inboxTaskMsgType.value = 'error'
  } finally {
    inboxDeadlineSavingId.value = null
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
  if (req.source === 'seal') {
    router.push({ path: '/seal/apply', query: { tab: 'mine' } })
    return
  }
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
    const [leaveRes, overtimeRes, btRes, sealRes] = await Promise.all([
      getLeaveList({ name, status: 'all', all_years: true }),
      getOvertimeList({ name, status: 'all', all_years: true }),
      getBusinessTripList({ name, all_years: true }),
      getMySealApplications({ name }),
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
    const seals = (sealRes?.data || []).filter((r) => {
      if (r.status !== 1) return true
      return Number(r.used_stamp) !== 1
    })
    seals.forEach(r => {
      const applyDate = (r.apply_time || '').slice(0, 10)
      let statusText = r.status === 0 ? '待审批' : r.status === 2 ? '已驳回' : '—'
      let statusCls = r.status === 0 ? 'status-processing' : r.status === 2 ? 'status-rejected' : 'status-processing'
      if (r.status === 1) {
        statusText = `${r.approval_status_text || '已通过'}（${r.seal_used_text || '未用印'}）`
        statusCls = 'status-approved'
      }
      items.push({
        uniqueId: `seal-${r.id}`,
        id: `YY${r.id}`,
        recordId: r.id,
        year: applyDate ? applyDate.slice(0, 4) : '',
        title: `${r.seal_type || '用印'}申请`,
        status: statusText,
        statusClass: statusCls,
        time: applyDate,
        businessTimeLabel: applyDate ? `申请时间：${applyDate}` : '',
        source: 'seal',
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
  window.removeEventListener('open-home-layout-settings', handleOpenHomeLayoutSettings)
  cleanupHomeTileDrag(false)
  stopMarquee()
  if (inboxTaskRefreshTimer) {
    clearInterval(inboxTaskRefreshTimer)
    inboxTaskRefreshTimer = null
  }
  if (_countdownTimer) {
    clearInterval(_countdownTimer)
    _countdownTimer = null
  }
  if (contactsHomeSearchTimer) {
    clearTimeout(contactsHomeSearchTimer)
    contactsHomeSearchTimer = null
  }
})

onMounted(() => {
  window.addEventListener('open-home-layout-settings', handleOpenHomeLayoutSettings)
  const info = getStoredUserInfo()
  userName.value = info.name || info.userName || ''
  userJb.value = info.jb || ''
  userLsys.value = (info.lsys || info.dept || '').trim()
  const jb = (info.jb || '').trim()
  canSeeBriefing.value = isMinisterLevel(jb)
  refreshWorkplaceTodos()
  fetchRequestList()
  if (isHomeModuleVisible('infoFeed')) {
    loadInfoFeedHome()
  }
  loadWallList()
  if (isHomeModuleVisible('personnelVisual')) {
    loadPersonnelVisualPreview()
  }
  if (canSeeBriefing.value) fetchBriefing()
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
  if (isHomeModuleVisible('contactsCard')) {
    void loadContactsHome()
  }
  _countdownTimer = setInterval(() => { nowTick.value = Date.now() }, 30000)
})

function folderAccent(group) {
  return group?.items?.[0]?.color || 'linear-gradient(135deg, #4f46e5 0%, #0891b2 100%)'
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
  /* 3 列瓦片网格：信息瓦片大小恒定（便于后续个性化排班），全宽应用集合行高自适应 */
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  grid-auto-rows: auto;
  gap: var(--spacing-xl);
  align-items: stretch;
  --home-tile-h: clamp(320px, 36vh, 400px);
}

/* 信息瓦片：宽 1 列、高严格等于 --home-tile-h，内容溢出由内部滚动处理；
   不能用 min-height，否则一行任意一个瓦片内容多就会把整行撑高 */
.home-tile {
  position: relative;
  min-width: 0;
  height: var(--home-tile-h);
  min-height: 0;
  overflow: hidden;
}

.home-tile-drag-handle {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 12;
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  color: #64748b;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
  cursor: grab;
  touch-action: none;
  transition: color .15s, border-color .15s, background .15s, transform .15s;
}

.home-tile-drag-handle:hover,
.home-tile-drag-handle.is-active {
  border-color: var(--color-primary, #3b82f6);
  color: var(--color-primary, #3b82f6);
  background: #fff;
}

.home-tile-drag-handle.is-active {
  cursor: grabbing;
  transform: scale(1.04);
}

.home-tile-drag-handle svg {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

:global(body.home-tile-dragging) {
  cursor: grabbing;
  user-select: none;
}

:global(body.home-tile-dragging) .home-tile-drag-handle {
  cursor: grabbing;
}

.home-tile > .dashboard-card,
.home-tile > article.dashboard-card {
  height: 100%;
  min-height: 0;
}

.home-tile > .dashboard-card > .dashboard-card__header,
.home-tile > article.dashboard-card > .dashboard-card__header {
  padding-right: calc(var(--spacing-xl) + 36px);
}

/* 跨整行的"应用集合"瓦片（常用/新增/全部功能）：高度自适应内容，避免空白 */
.home-tile--full {
  grid-column: 1 / -1;
  min-height: 0;
  height: auto;
  overflow: visible;
}

.dashboard-card {
  min-width: 0; /* 允许 grid 子项收缩，防止溢出 */
  height: 100%;
  min-height: 0;
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

.dashboard-card__icon--contacts {
  background: linear-gradient(135deg, #6366f1 0%, #7c3aed 100%);
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
  max-height: none;
  padding: var(--spacing-md) var(--spacing-xl) var(--spacing-xl);
  overflow-x: hidden;
  overflow-y: auto;
}

/* 首页部门通讯录：工具条固定，列表区域单独滚动 */
.dashboard-card__body.contacts-home-body {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-top: var(--spacing-sm);
}

.contacts-home-toolbar {
  flex-shrink: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.contacts-home-select {
  flex: 0 1 auto;
  min-width: 0;
  max-width: 11rem;
  padding: 4px 8px;
  font-size: var(--font-size-sm);
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--radius-sm);
  background: var(--color-bg-container, #fff);
  color: var(--color-text-primary);
}

.contacts-home-search {
  flex: 1 1 8rem;
  min-width: 0;
  position: relative;
  display: flex;
  align-items: center;
}

.contacts-home-input {
  width: 100%;
  padding: 4px 28px 4px 8px;
  font-size: var(--font-size-sm);
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--radius-sm);
  background: var(--color-bg-container, #fff);
}

.contacts-home-clear {
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
  border: none;
  background: transparent;
  font-size: 18px;
  line-height: 1;
  color: var(--color-text-tertiary);
  cursor: pointer;
  padding: 0 4px;
}

.contacts-home-clear:hover {
  color: var(--color-text-secondary);
}

.contacts-home-list {
  list-style: none;
  margin: 0;
  padding: 0;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.contacts-home-row {
  padding: var(--spacing-md) 0;
  border-bottom: 1px solid var(--color-border-lighter);
  min-width: 0;
}

.contacts-home-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.contacts-home-row-main {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
  min-width: 0;
}

.contacts-home-name {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.contacts-home-jb {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}

.contacts-home-jb.jb-manager { background: #fef3c7; color: #92400e; }
.contacts-home-jb.jb-director { background: #dbeafe; color: #1e40af; }
.contacts-home-jb.jb-leader { background: #dcfce7; color: #166534; }
.contacts-home-jb.jb-default { background: #f1f5f9; color: #475569; }

.contacts-home-row-sub {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-sm);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  min-width: 0;
}

.contacts-home-dept {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.contacts-home-phones {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  max-width: 55%;
}

.contacts-home-tel {
  font-size: var(--font-size-xs);
  color: var(--color-primary);
  text-decoration: none;
}

.contacts-home-tel:hover {
  text-decoration: underline;
}

.contacts-home-tel--land {
  color: var(--color-text-secondary);
  cursor: default;
}

.contacts-home-tel--land:hover {
  text-decoration: none;
}

.contacts-home-no {
  color: var(--color-text-tertiary);
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
  min-height: 100%;
  padding: var(--spacing-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.dashboard-empty p {
  margin: 0;
}

.ai-task-unconfigured {
  max-height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: var(--spacing-lg) var(--spacing-xl);
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
.ai-task-unconfigured__img-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  margin: 8px 0;
  max-width: 100%;
}
.ai-task-unconfigured__img {
  max-width: 520px;
  width: 100%;
  max-height: 120px;
  object-fit: contain;
  border-radius: 8px;
  border: 1px solid #fcd34d;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.15);
}
.ai-task-unconfigured__img-caption {
  font-size: 0.78rem;
  color: #92400e;
}

/* 全部功能：分组紧凑九宫格 */
.shortcuts-container {
  margin-top: 0;
}

.shortcuts-section {
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
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
  padding-right: 42px;
}

.shortcuts-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  white-space: nowrap;
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
@media (max-width: 1280px) {
  .home-page {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

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
}

/* ==================== 常用功能 ==================== */
.home-favorites-section {
  margin-bottom: 0;
  display: flex;
  flex-direction: column;
}
.favorites-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-right: 42px;
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
.new-features-title-icon {
  color: #10b981;
  fill: none;
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

/* ============= 手机透明文件夹样式 - 应用图标 ============= */
.app-tiles {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(76px, 1fr));
  gap: 16px 8px;
}

/* 常用/新增功能下方平铺，紧贴大段卡片，去掉额外滚动 */
.app-tiles--favorites {
  padding: 4px 2px 2px;
}

.app-tile {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 6px 4px;
  background: transparent;
  border: 0;
  border-radius: 12px;
  cursor: pointer;
  transition: background .15s ease, transform .15s ease;
  text-align: center;
  outline: none;
}
.app-tile:hover {
  background: rgba(255, 255, 255, 0.7);
  transform: translateY(-2px);
}
.app-tile:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
.app-tile__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  min-width: 52px;
  border-radius: 14px;
  color: #fff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.10), inset 0 1px 0 rgba(255, 255, 255, 0.18);
}
.app-tile__icon svg {
  width: 26px;
  height: 26px;
  color: #fff;
  stroke: #fff;
}
.app-tile__label {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  line-height: 1.2;
  color: #1e293b;
  font-weight: 500;
}
.app-tile__tag {
  position: absolute;
  top: 0;
  right: 6px;
  padding: 0 5px;
  font-size: 10px;
  font-weight: 700;
  color: #fff;
  background: #ef4444;
  border-radius: 8px;
  line-height: 14px;
  box-shadow: 0 1px 2px rgba(239, 68, 68, 0.4);
}

/* 透明圆角文件夹容器（包裹一组应用图标） */
.app-folder-stack {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.app-folder {
  padding: 14px 16px 10px;
  border-radius: 18px;
  background: rgba(241, 245, 249, 0.7);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.85);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6), 0 2px 8px rgba(15, 23, 42, 0.04);
}
.app-folder__title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  letter-spacing: 0.02em;
}
.app-folder__title-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.app-folder__title small {
  margin-left: auto;
  font-size: 12px;
  font-weight: 500;
  color: #94a3b8;
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

.home-layout-modal {
  width: 620px;
  max-width: 94vw;
  max-height: 82vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.22);
}

.home-layout-modal__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 22px 14px;
  border-bottom: 1px solid #e5e7eb;
}

.home-layout-modal__header h2 {
  margin: 0;
  color: #1e293b;
  font-size: 17px;
  font-weight: 700;
}

.home-layout-modal__header p {
  margin: 5px 0 0;
  color: #64748b;
  font-size: 13px;
}

.home-layout-modal__close {
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  font-size: 24px;
  line-height: 1;
  padding: 0 4px;
}

.home-layout-modal__close:hover {
  color: #ef4444;
}

.home-layout-modal__body {
  flex: 1;
  overflow-y: auto;
  padding: 12px 20px;
}

.home-layout-item {
  min-height: 64px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  transition: border-color .15s, background .15s;
}

.home-layout-item + .home-layout-item {
  margin-top: 8px;
}

.home-layout-item:hover {
  border-color: #bfdbfe;
  background: #f8fafc;
}

.home-layout-item.disabled {
  background: #f8fafc;
  opacity: 0.72;
}

.home-layout-item__toggle {
  position: relative;
  width: 38px;
  height: 22px;
  flex-shrink: 0;
  cursor: pointer;
}

.home-layout-item__toggle input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.home-layout-item__toggle span {
  position: absolute;
  inset: 0;
  border-radius: 999px;
  background: #cbd5e1;
  transition: background .15s;
}

.home-layout-item__toggle span::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.25);
  transition: transform .15s;
}

.home-layout-item__toggle input:checked + span {
  background: var(--color-primary, #3b82f6);
}

.home-layout-item__toggle input:checked + span::after {
  transform: translateX(16px);
}

.home-layout-item__toggle input:disabled + span {
  opacity: 0.55;
  cursor: not-allowed;
}

.home-layout-item__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.home-layout-item__main strong {
  color: #1e293b;
  font-size: 14px;
  font-weight: 700;
}

.home-layout-item__main small {
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.home-layout-item__badge {
  flex-shrink: 0;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 12px;
}

.home-layout-item__actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.home-layout-item__actions button {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  background: #fff;
  color: #475569;
  cursor: pointer;
}

.home-layout-item__actions button:hover:not(:disabled) {
  border-color: var(--color-primary, #3b82f6);
  color: var(--color-primary, #3b82f6);
}

.home-layout-item__actions button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.home-layout-item__actions svg {
  width: 16px;
  height: 16px;
}

.home-layout-modal__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 20px;
  border-top: 1px solid #e5e7eb;
  background: #f8fafc;
}

.home-layout-reset {
  border: none;
  background: transparent;
  color: var(--color-primary, #3b82f6);
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  padding: 6px 0;
}

.home-layout-reset:hover {
  text-decoration: underline;
}

.home-layout-modal__btns {
  display: flex;
  gap: 8px;
}

@media (max-width: 768px) {
  .app-tiles { grid-template-columns: repeat(auto-fill, minmax(64px, 1fr)); }
  .fav-editor-items { grid-template-columns: 1fr; }
  .home-layout-item {
    align-items: flex-start;
    flex-wrap: wrap;
  }
  .home-layout-item__actions {
    width: 100%;
    justify-content: flex-end;
  }
  .home-layout-modal__footer {
    align-items: stretch;
    flex-direction: column;
  }
  .home-layout-modal__btns {
    justify-content: flex-end;
  }
}

.home-ai-task-section {
  margin-bottom: 0;
}

.ai-task-card {
  background: #fff;
  border-color: var(--color-border-lighter);
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
  flex: 1;
  min-height: 0;
  padding: var(--spacing-md) var(--spacing-xl) var(--spacing-xl);
  overflow: hidden;
}

.ai-task-marquee {
  height: 100%;
  max-height: none;
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
  max-width: 68%;
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

.ai-mail-task__edit {
  width: 18px;
  height: 18px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 50%;
  color: currentColor;
  background: rgba(255, 255, 255, 0.65);
  cursor: pointer;
}

.ai-mail-task__edit svg {
  width: 11px;
  height: 11px;
}

.ai-mail-task__deadline-editor {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  max-width: 68%;
}

.ai-mail-task__deadline-input {
  width: 170px;
  height: 26px;
  padding: 0 8px;
  border: 1px solid #c7d2fe;
  border-radius: 6px;
  font-size: 12px;
  color: #1f2937;
  background: #fff;
}

.ai-mail-task__deadline-save,
.ai-mail-task__deadline-cancel {
  height: 26px;
  padding: 0 8px;
  border-radius: 6px;
  border: 1px solid #c7d2fe;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.ai-mail-task__deadline-save {
  color: #fff;
  background: #4f46e5;
  border-color: #4f46e5;
}

.ai-mail-task__deadline-cancel {
  color: #4b5563;
  background: #fff;
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
  margin-bottom: 0;
}

/* ========== 天气新闻首页预览 ========== */
.info-feed-preview-card {
  min-height: 230px;
  overflow: hidden;
}

.dashboard-card__icon--info-feed {
  background: linear-gradient(135deg, #fde68a, #38bdf8);
  color: #0f172a;
  font-size: 20px;
}

.info-feed-preview-card__header {
  align-items: center;
}

.info-feed-preview-body {
  display: grid;
  gap: 12px;
  cursor: pointer;
}

.info-feed-weather-mini {
  display: grid;
  grid-template-columns: 62px 1fr;
  gap: 12px;
  align-items: center;
  padding: 12px;
  border-radius: 12px;
  background: linear-gradient(135deg, #ecfeff, #f8fafc);
  border: 1px solid rgba(14, 116, 144, 0.14);
}

.info-feed-weather-icon {
  width: 58px;
  height: 58px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  font-size: 32px;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.12);
}

.info-feed-weather-mini strong {
  display: block;
  font-size: 24px;
  line-height: 1;
  color: #0f766e;
  margin-bottom: 5px;
}

.info-feed-weather-text {
  min-width: 0;
}

.info-feed-weather-mini span,
.info-feed-weather-mini small {
  display: block;
  color: #475569;
  font-size: 12px;
  line-height: 1.45;
}

.info-feed-forecast-line {
  color: #0f766e !important;
  font-size: 11px !important;
  line-height: 1.35 !important;
  margin: 2px 0 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.info-feed-news-mini {
  display: grid;
  gap: 8px;
}

.info-feed-news-mini button {
  display: grid;
  grid-template-columns: 42px 1fr;
  gap: 8px;
  align-items: center;
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  text-align: left;
  cursor: pointer;
}

.info-feed-news-mini button:hover {
  border-color: #14b8a6;
  background: #f0fdfa;
}

.info-feed-news-mini span {
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
}

.info-feed-news-mini strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #1e293b;
  font-size: 13px;
}

.weather-visual--sun { background: linear-gradient(135deg, #fff7ad, #f59e0b); }
.weather-visual--cloud { background: linear-gradient(135deg, #e2e8f0, #94a3b8); }
.weather-visual--rain, .weather-visual--storm { background: linear-gradient(135deg, #dbeafe, #2563eb); }
.weather-visual--snow { background: linear-gradient(135deg, #f8fafc, #7dd3fc); }
.weather-visual--fog { background: linear-gradient(135deg, #f1f5f9, #94a3b8); }
.weather-visual--default { background: linear-gradient(135deg, #ecfeff, #14b8a6); }

/* 吐槽墙瓦片：与其他卡片一致的纯白卡片样式 */
.wall-preview-card {
  background: #fff;
  border-color: var(--color-border-lighter);
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
  border: 1px solid var(--color-border-base);
  background: #fff;
  color: var(--color-text-secondary);
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
  background: var(--color-bg-layout);
  color: var(--color-text-primary);
}

.wall-preview-viewall {
  height: 30px;
  padding: 0 12px;
  border: 1px solid var(--color-primary);
  background: #fff;
  color: var(--color-primary);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  font-weight: 600;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}

.wall-preview-viewall:hover {
  background: var(--color-primary);
  color: #fff;
}

.wall-preview-body {
  flex: 1;
  min-height: 0;
  padding: var(--spacing-md) var(--spacing-xl) var(--spacing-xl);
  overflow: hidden;
  position: relative;
}

.wall-barrage-stage {
  position: relative;
  height: 100%;
  min-height: 190px;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  background:
    linear-gradient(180deg, rgba(255,255,255,.82), rgba(248,250,252,.92)),
    radial-gradient(circle at 16% 18%, rgba(56,189,248,.12), transparent 34%),
    radial-gradient(circle at 88% 82%, rgba(251,113,133,.10), transparent 36%),
    #f8fafc;
  box-shadow: inset 0 0 0 1px rgba(148,163,184,.18);
}

.wall-barrage-stage::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(148,163,184,.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148,163,184,.07) 1px, transparent 1px);
  background-size: 24px 24px;
  opacity: .5;
  pointer-events: none;
}

.wall-barrage-stage:hover .wall-barrage-track {
  animation-play-state: paused;
}

.wall-barrage-row {
  position: absolute;
  left: 0;
  right: 0;
  top: var(--row-top);
  height: 48px;
  transform: translateY(-50%);
  pointer-events: none;
}

.wall-barrage-track {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 18px;
  width: 100%;
  animation: wall-barrage-move var(--row-duration) linear infinite;
  animation-delay: var(--row-delay);
  will-change: transform;
}

.wall-barrage-item {
  min-height: 36px;
  max-height: 48px;
  max-width: min(520px, 78vw);
  border: 1px solid rgba(148,163,184,.24);
  border-left: 3px solid var(--item-accent);
  border-radius: 18px;
  padding: 5px 8px 5px 10px;
  background: rgba(255,255,255,.86);
  color: #334155;
  box-shadow: 0 6px 16px rgba(15,23,42,.08);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  pointer-events: auto;
  cursor: pointer;
  backdrop-filter: blur(8px);
  transition: transform .16s ease, background .16s ease, border-color .16s ease;
}

.wall-barrage-item:hover {
  transform: translateY(-1px) scale(1.02);
  background: #fff;
  border-color: rgba(100,116,139,.3);
}

.wall-barrage-status {
  flex: 0 0 auto;
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  color: #2563eb;
  background: #dbeafe;
}

.wall-barrage-text {
  min-width: 0;
  max-width: 390px;
  overflow: hidden;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.35;
  white-space: normal;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.wall-barrage-like {
  position: relative;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 6px;
  border-radius: 999px;
  color: #64748b;
  background: rgba(148,163,184,.12);
  transition: transform .15s ease, background .15s ease;
}

.wall-barrage-like:hover {
  transform: scale(1.12);
  background: rgba(148,163,184,.2);
}

.wall-barrage-item.liked .wall-barrage-like {
  color: #92400e;
  background: rgba(251, 191, 36, .22);
}

.wall-barrage-item.animating .wall-like-icon {
  animation: wall-like-pop .5s cubic-bezier(.34, 1.56, .64, 1);
}

.wall-barrage-item.animating.liked .wall-barrage-like::after {
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

.wall-barrage-vignette {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 58px;
  z-index: 2;
  pointer-events: none;
}

.wall-barrage-vignette--left {
  left: 0;
  background: linear-gradient(90deg, #f8fafc, rgba(248,250,252,0));
}

.wall-barrage-vignette--right {
  right: 0;
  background: linear-gradient(270deg, #f8fafc, rgba(248,250,252,0));
}

@keyframes wall-barrage-move {
  from { transform: translateX(100%); }
  to { transform: translateX(-100%); }
}

.wall-like-icon {
  display: inline-block;
  transition: transform .3s cubic-bezier(.34, 1.56, .64, 1);
}

@keyframes wall-like-pop {
  0%   { transform: scale(1); }
  25%  { transform: scale(1.5) rotate(-15deg); }
  50%  { transform: scale(0.9) rotate(5deg); }
  75%  { transform: scale(1.2); }
  100% { transform: scale(1); }
}

@keyframes wall-like-burst {
  0%   { transform: translate(-50%, 0) scale(0); opacity: 1; }
  50%  { transform: translate(-50%, -12px) scale(1.5); opacity: 0.8; }
  100% { transform: translate(-50%, -20px) scale(0.5); opacity: 0; }
}

/* ========== 人员出勤可视化首页缩略 ========== */
.home-tile--personnel-visual {
  margin-bottom: 0;
}

.personnel-visual-card {
  background: #fff;
  border-color: var(--color-border-lighter);
}

.dashboard-card__icon--personnel-visual {
  background: linear-gradient(135deg, #0ea5e9 0%, #22c55e 100%);
}

.personnel-visual-card__header {
  align-items: center;
}

.personnel-visual-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.personnel-visual-body {
  flex: 1;
  min-height: 0;
  padding: 9px 12px 12px;
  cursor: pointer;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.personnel-mini-summary {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
  margin-bottom: 6px;
  color: #475569;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.personnel-mini-summary span {
  flex: 0 0 auto;
  padding: 3px 7px;
  border-radius: 999px;
  background: #f1f5f9;
}

.personnel-mini-summary .personnel-mini-dept {
  min-width: 0;
  max-width: 128px;
  overflow: hidden;
  color: #0f172a;
  text-overflow: ellipsis;
  background: #e0f2fe;
}

.personnel-mini-dept-select {
  flex: 0 1 auto;
  min-width: 0;
  max-width: 128px;
  padding: 3px 18px 3px 7px;
  border: none;
  border-radius: 999px;
  background: #e0f2fe url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 24 24' fill='none' stroke='%230f172a' stroke-width='2.5'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E") no-repeat right 5px center;
  color: #0f172a;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
}

.personnel-mini-dept-select:focus {
  outline: 2px solid rgba(14, 165, 233, 0.45);
  outline-offset: 1px;
}

.personnel-mini-office {
  position: relative;
  flex: 1;
  height: auto;
  min-height: 0;
  overflow: hidden auto;
  border-radius: 8px;
  background:
    linear-gradient(180deg, rgba(248,250,252,.98), rgba(226,232,240,.88)),
    #f8fafc;
  box-shadow: inset 0 0 0 1px rgba(148,163,184,.2);
  scrollbar-width: thin;
  scrollbar-color: rgba(59,130,246,.45) rgba(226,232,240,.8);
}

.personnel-mini-office::-webkit-scrollbar {
  width: 6px;
}

.personnel-mini-office::-webkit-scrollbar-track {
  background: rgba(226,232,240,.8);
  border-radius: 999px;
}

.personnel-mini-office::-webkit-scrollbar-thumb {
  background: rgba(59,130,246,.45);
  border-radius: 999px;
}

.personnel-mini-office::-webkit-scrollbar-thumb:hover {
  background: rgba(37,99,235,.62);
}

.personnel-mini-office::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 1px;
  background: rgba(148,163,184,.32);
}

.personnel-mini-desks {
  position: relative;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(48px, 1fr));
  grid-auto-rows: 34px;
  gap: 4px;
  padding: 7px;
  min-height: 100%;
}

.personnel-mini-desk {
  position: relative;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border: 1px solid rgba(148,163,184,.28);
  border-left: 3px solid #94a3b8;
  border-radius: 6px;
  background: rgba(255,255,255,.86);
  box-shadow: 0 4px 10px rgba(15,23,42,.06);
  animation: personnel-desk-in .38s ease both;
  animation-delay: var(--desk-delay);
}

.personnel-mini-desk--present { border-left-color: #10b981; }
.personnel-mini-desk--business_trip {
  border-left-color: #f59e0b;
  background: #fff7ed;
}
.personnel-mini-desk--leave {
  border-left-color: #8b5cf6;
  background: #f5f3ff;
}

@keyframes personnel-desk-in {
  from { opacity: 0; transform: translateY(8px) scale(.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.personnel-mini-name {
  position: relative;
  z-index: 6;
  margin: 2px 4px 0;
  padding: 1px 3px;
  overflow: hidden;
  border-radius: 4px;
  color: #0b1220;
  background: rgba(255,255,255,.82);
  font-size: 9px;
  font-weight: 800;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
  box-shadow: 0 1px 4px rgba(15,23,42,.08);
}

.personnel-mini-workstation {
  position: absolute;
  inset: 12px 2px 2px;
}

.personnel-mini-table {
  position: absolute;
  left: 6px;
  right: 6px;
  bottom: 2px;
  height: 11px;
  border-radius: 4px 4px 6px 6px;
  background: linear-gradient(180deg, #c08457, #8b5e3c);
  box-shadow: inset 0 3px rgba(255,255,255,.15);
}

.personnel-mini-screen {
  position: absolute;
  left: 50%;
  bottom: 14px;
  z-index: 2;
  width: 18px;
  height: 12px;
  transform: translateX(-50%);
  border: 2px solid #1f2937;
  border-radius: 3px;
  background: linear-gradient(135deg, #0ea5e9, #22c55e);
}

.personnel-mini-desk--no_record .personnel-mini-screen {
  background: #cbd5e1;
}

.personnel-mini-screen span {
  position: absolute;
  inset: 2px;
  border-radius: 2px;
  background: rgba(255,255,255,.28);
  animation: personnel-screen-glow 1.8s ease-in-out infinite;
}

.personnel-mini-desk--no_record .personnel-mini-screen span {
  animation: none;
  opacity: .35;
}

@keyframes personnel-screen-glow {
  0%, 100% { opacity: .24; }
  50% { opacity: .76; }
}

.personnel-mini-worker {
  position: absolute;
  left: 50%;
  bottom: 7px;
  z-index: 3;
  width: 18px;
  height: 26px;
  transform: translateX(-50%);
}

.personnel-mini-desk--business_trip .personnel-mini-worker {
  left: 30%;
  animation: personnel-walk 1.15s ease-in-out infinite;
}

.personnel-mini-desk--leave .personnel-mini-worker {
  opacity: .78;
}

.personnel-mini-desk--no_record .personnel-mini-worker {
  opacity: .36;
  filter: grayscale(.35);
}

@keyframes personnel-walk {
  0%, 100% { transform: translateX(-50%) translateY(0); }
  50% { transform: translateX(-50%) translateY(-4px); }
}

.personnel-mini-worker i {
  position: absolute;
  display: block;
}

.personnel-mini-worker .head {
  left: 50%;
  top: 1px;
  width: 9px;
  height: 9px;
  transform: translateX(-50%);
  border-radius: 50%;
  background: #f6c99f;
}

.personnel-mini-worker .hair {
  left: 5px;
  right: 5px;
  top: 1px;
  z-index: 2;
  height: 4px;
  border-radius: 7px 7px 4px 4px;
  background: #334155;
}

.personnel-mini-desk--female .hair {
  left: 4px;
  right: 4px;
  height: 6px;
  border-radius: 9px 9px 5px 5px;
  background: #3f2f46;
}

.personnel-mini-worker .body {
  left: 50%;
  top: 10px;
  width: 12px;
  height: 12px;
  transform: translateX(-50%);
  border-radius: 8px 8px 5px 5px;
  background: #2563eb;
}

.personnel-mini-desk--female .body {
  width: 11px;
  background: #db2777;
}

.personnel-mini-desk--business_trip .body { background: #ea580c; }
.personnel-mini-desk--leave .body { background: #7c3aed; }
.personnel-mini-desk--no_record .body { background: #94a3b8; }

.personnel-mini-worker .arm {
  top: 12px;
  width: 4px;
  height: 10px;
  border-radius: 6px;
  background: #f6c99f;
  transform-origin: top center;
}

.personnel-mini-worker .arm-left {
  left: 3px;
  animation: personnel-typing-left .72s ease-in-out infinite;
}

.personnel-mini-worker .arm-right {
  right: 3px;
  animation: personnel-typing-right .72s ease-in-out infinite;
}

.personnel-mini-desk--business_trip .arm,
.personnel-mini-desk--leave .arm,
.personnel-mini-desk--no_record .arm {
  animation: none;
}

@keyframes personnel-typing-left {
  0%, 100% { transform: rotate(18deg); }
  50% { transform: rotate(36deg); }
}

@keyframes personnel-typing-right {
  0%, 100% { transform: rotate(-18deg); }
  50% { transform: rotate(-36deg); }
}

.personnel-mini-trip {
  position: absolute;
  inset: 0;
  z-index: 4;
  pointer-events: none;
}

.personnel-mini-trip i {
  position: absolute;
  left: 40%;
  right: 7px;
  top: 21px;
  border-top: 1px dashed #f59e0b;
}

.personnel-mini-trip b {
  position: absolute;
  right: 6px;
  top: 6px;
  width: 11px;
  height: 11px;
  color: #0284c7;
  animation: personnel-plane-float 2.1s ease-in-out infinite;
}

.personnel-mini-trip b::before,
.personnel-mini-trip b::after {
  content: '';
  position: absolute;
  background: currentColor;
}

.personnel-mini-trip b::before {
  left: 1px;
  top: 5px;
  width: 10px;
  height: 1px;
  transform: rotate(-30deg);
}

.personnel-mini-trip b::after {
  left: 5px;
  top: 1px;
  width: 1px;
  height: 10px;
  transform: rotate(-30deg);
}

@keyframes personnel-plane-float {
  0%, 100% { transform: translate(0, 0) rotate(0deg); }
  50% { transform: translate(-8px, 5px) rotate(-8deg); }
}

.personnel-mini-leave {
  position: absolute;
  right: 4px;
  top: 4px;
  z-index: 5;
  width: 15px;
  height: 15px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #fff;
  border-radius: 50%;
  background: #8b5cf6;
  color: #fff;
  font-size: 9px;
  font-weight: 900;
  box-shadow: 0 6px 14px rgba(124,58,237,.24);
  animation: personnel-leave-pulse 1.9s ease-in-out infinite;
}

@keyframes personnel-leave-pulse {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-2px) scale(1.06); }
}

/* ========== 重要信息审阅 ========== */
.briefing-section {
  margin-bottom: 0;
  padding: 0;
}

.dashboard-card--briefing {
  border-left: 3px solid #667eea;
  height: 100%;
  min-height: 0;
}

/* 窄瓦片：标题独占一行，筛选/天数/查看全部换到下一行，避免标题被挤成几像素 */
.dashboard-card--briefing .dashboard-card__header {
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
  padding: var(--spacing-md) var(--spacing-lg);
}

.dashboard-card--briefing .dashboard-card__title {
  width: 100%;
  flex-shrink: 0;
  min-width: 0;
}

.dashboard-card--briefing .dashboard-card__title-text {
  overflow: visible;
  text-overflow: clip;
  white-space: nowrap;
  flex: 1 1 auto;
  min-width: 0;
}

.dashboard-card__icon--briefing {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.briefing-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-start;
  width: 100%;
}

.briefing-filter-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  flex: 1 1 100%;
  min-width: 0;
}

.dashboard-card--briefing .briefing-filter-tab {
  padding: 2px 8px;
  font-size: 11px;
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
  flex: 1;
  height: auto;
  min-height: 0;
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

.briefing-item--mail .briefing-tag,
.briefing-modal__item--mail .briefing-tag {
  color: #4338ca;
  background: #e0e7ff;
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
.briefing-modal__item--mail {
  background: #eef2ff;
  border-left-color: #4f46e5;
}
.briefing-modal__item--mail:hover {
  background: #e0e7ff;
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
  
  .home-page {
    grid-template-columns: 1fr;
    --home-tile-h: clamp(280px, 60vh, 420px);
  }

  .dashboard-card__header,
  .dashboard-card__body {
    padding-left: var(--spacing-lg);
    padding-right: var(--spacing-lg);
  }

  .shortcuts-section {
    padding: var(--spacing-md);
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
