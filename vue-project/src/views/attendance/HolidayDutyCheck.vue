<template>
  <div class="holiday-duty-page">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">假期值班出勤核查</h1>
          <p class="header-subtitle">按排班白班、夜班核对打卡；人事管理员与综合技术室主任职级可用。完成后可返回排班管理。</p>
        </div>
        <router-link to="/attendance/shift-schedule" class="btn btn-back">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          返回排班
        </router-link>
      </div>
    </div>

    <div class="container">
      <HolidayDutySection />
    </div>
  </div>
</template>

<script setup>
import HolidayDutySection from '@/components/attendance/HolidayDutySection.vue'
</script>

<style scoped>
.holiday-duty-page {
  width: 100%;
}

.page-header {
  margin-bottom: var(--spacing-lg);
}

.header-content {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-lg);
  flex-wrap: wrap;
}

.header-title {
  font-size: var(--font-size-xxl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-xs);
}

.header-subtitle {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0;
  max-width: 560px;
}

.btn-back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  background: var(--color-bg-container);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  text-decoration: none;
  transition: all 0.15s;
  flex-shrink: 0;
}
.btn-back:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.btn-back .btn-icon { width: 16px; height: 16px; }

.container {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0 0 var(--spacing-xxl);
}
</style>
