<template>
  <div class="manual-entry-page">
    <div class="page-header with-tabs">
      <div class="header-left">
        <div>
          <h1 class="page-title">考勤手动填报</h1>
          <p class="page-subtitle">请假申请、加班登记与节假日换休票</p>
        </div>
        <div class="header-tabs">
          <router-link
            :to="leaveTabTo"
            :class="['tab-link', { active: currentTab === 'leave' }]"
          >
            请假管理
          </router-link>
          <router-link
            :to="overtimeTabTo"
            :class="['tab-link', { active: currentTab === 'overtime' }]"
          >
            加班管理
          </router-link>
          <router-link
            :to="holidayExchangeTabTo"
            :class="['tab-link', { active: currentTab === 'holiday-exchange' }]"
          >
            公出节假日换休票
          </router-link>
        </div>
      </div>
    </div>
    <div class="tab-content">
      <Leave v-if="currentTab === 'leave'" />
      <Overtime v-else-if="currentTab === 'overtime'" />
      <HolidayExchange v-else-if="currentTab === 'holiday-exchange'" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Leave from './Leave.vue'
import Overtime from './Overtime.vue'
import HolidayExchange from './HolidayExchange.vue'

const route = useRoute()
const currentTab = computed(() => {
  const t = route.query.tab
  if (t === 'overtime') return 'overtime'
  if (t === 'holiday-exchange') return 'holiday-exchange'
  return 'leave'
})

/** 切换 tab 时保留 from、year、month 等查询参数（领导看板跳转等） */
const leaveTabTo = computed(() => ({
  path: '/attendance/manual',
  query: { ...route.query, tab: 'leave' }
}))
const overtimeTabTo = computed(() => ({
  path: '/attendance/manual',
  query: { ...route.query, tab: 'overtime' }
}))
const holidayExchangeTabTo = computed(() => ({
  path: '/attendance/manual',
  query: { ...route.query, tab: 'holiday-exchange' }
}))
</script>

<style scoped>
.manual-entry-page {
  min-height: 100%;
  display: flex;
  flex-direction: column;
}
/* 与“公出管理”页标题到内容间距一致（约 16px） */
.page-header.with-tabs {
  margin-bottom: var(--spacing-sm);
}
.page-header.with-tabs .header-content {
  justify-content: flex-start;
}
.header-left {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-xl);
}
.header-left > div:first-child {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.header-tabs {
  display: flex;
  gap: var(--spacing-xs);
}
.tab-link {
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: var(--radius-base);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  text-decoration: none;
  background: var(--color-bg-spotlight);
  border: 1px solid var(--color-border-lighter);
  transition: all var(--transition-base);
}
.tab-link:hover {
  color: var(--color-primary);
  border-color: var(--color-primary);
}
.tab-link.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}
.tab-content {
  flex: 1;
}
.tab-content :deep(.page-container) {
  padding-top: 0;
}
.tab-content :deep(.page-container .page-header) {
  margin-top: var(--spacing-sm);
  margin-bottom: 0;
}
/* 标题栏与下方记录卡片紧贴，不留间距 */
.tab-content :deep(.page-container .page-header + .content) {
  margin-top: 0;
}
</style>
