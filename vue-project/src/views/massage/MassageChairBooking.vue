<template>
  <div class="massage-page">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">健康角预约</h1>
          <p class="header-subtitle">部门健康角 · 以 15 分钟为单位预约 · 每人每日最多 2 个时段（30 分钟）</p>
        </div>
      </div>
    </div>

    <div class="container">
      <!-- 使用须知 -->
      <section class="notice-card card">
        <div class="notice-head" @click="noticeExpanded = !noticeExpanded">
          <h2 class="notice-title">
            <svg class="notice-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            使用须知（请务必阅读并严格遵守）
          </h2>
          <span class="notice-toggle">{{ noticeExpanded ? '收起' : '展开' }}</span>
        </div>
        <ol v-show="noticeExpanded" class="notice-list">
          <li v-for="(item, idx) in usageNotice" :key="idx">{{ item }}</li>
        </ol>
        <p v-show="noticeExpanded" class="notice-emphasis">
          特别提醒：8:00–10:00、10:15–12:00、13:00–15:00、15:15–17:00 为正常上班工作时间，<strong>严禁使用健康角</strong>；仅可在系统开放的可预约时段内使用。
        </p>
      </section>

      <!-- 日期与配额 -->
      <section class="toolbar card">
        <div class="toolbar-row">
          <label class="form-label">预约日期</label>
          <input v-model="selectedDate" type="date" class="form-input date-input" :min="todayStr" @change="loadSlots" />
          <button type="button" class="btn btn-secondary" @click="loadSlots" :disabled="loading">刷新</button>
        </div>
        <div class="quota-bar">
          <span>今日已预约：<strong>{{ myBookedCount }}</strong> / {{ maxSlotsPerDay }} 个时段</span>
          <span class="quota-hint">剩余可约 {{ Math.max(0, maxSlotsPerDay - myBookedCount) }} 个时段</span>
        </div>
      </section>

      <!-- 我的预约 -->
      <section v-if="myBookings.length" class="my-bookings card">
        <h3 class="section-title">我的预约</h3>
        <div class="my-booking-list">
          <div v-for="item in myBookings" :key="item.id" class="my-booking-item">
            <div class="my-booking-time">{{ item.startTime }} – {{ item.endTime }}</div>
            <button
              type="button"
              class="btn-cancel"
              :disabled="actionLoading"
              @click="handleCancel(item)"
            >
              取消
            </button>
          </div>
        </div>
      </section>

      <!-- 时段网格 -->
      <section v-if="loading" class="loading-state card">加载中...</section>
      <section v-else-if="!slots.length" class="empty-state card">暂无可预约时段</section>

      <section v-for="period in periodGroups" :key="period.key" class="period-section card">
        <div class="period-header">
          <h3 class="period-title">{{ period.label }}</h3>
          <span class="period-range">{{ period.start }} – {{ period.end }}</span>
        </div>
        <div class="slot-grid">
          <button
            v-for="slot in period.slots"
            :key="slot.startTime"
            type="button"
            class="slot-btn"
            :class="slotClass(slot)"
            :disabled="!canClickSlot(slot)"
            :title="slotTitle(slot)"
            @click="handleBook(slot)"
          >
            <span class="slot-time">{{ slot.startTime }}</span>
            <span class="slot-status">{{ slotStatusText(slot) }}</span>
          </button>
        </div>
      </section>
    </div>

    <div v-if="toast.show" class="toast" :class="toast.type">{{ toast.message }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  getMassageChairConfig,
  getMassageChairSlots,
  bookMassageChair,
  cancelMassageChairBooking
} from '@/api/massageChair'

function getUserInfo() {
  try {
    const s = localStorage.getItem('userInfo')
    return s ? JSON.parse(s) : {}
  } catch {
    return {}
  }
}

const userInfo = getUserInfo()
const currentUser = (userInfo.name || userInfo.userName || '').trim()

function formatDateLocal(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const todayStr = formatDateLocal(new Date())
const selectedDate = ref(todayStr)
const loading = ref(false)
const actionLoading = ref(false)
const noticeExpanded = ref(true)

const usageNotice = ref([])
const periods = ref([])
const slots = ref([])
const myBookings = ref([])
const myBookedCount = ref(0)
const maxSlotsPerDay = ref(2)

function errMsg(e) {
  const d = e?.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d) && d[0]?.msg) return d[0].msg
  return e?.message || '操作失败'
}

const toast = ref({ show: false, message: '', type: 'success' })
let toastTimer = null

function showToast(message, type = 'success') {
  toast.value = { show: true, message, type }
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value.show = false }, 2800)
}

const periodGroups = computed(() => {
  const list = periods.value.length ? periods.value : [
    { key: 'early', label: '早间', start: '05:00', end: '08:00' },
    { key: 'morning_break', label: '上午工间操', start: '10:00', end: '10:15' },
    { key: 'lunch', label: '午休', start: '12:00', end: '13:00' },
    { key: 'afternoon_break', label: '下午工间操', start: '15:00', end: '15:15' },
    { key: 'evening', label: '晚间', start: '17:00', end: '22:00' }
  ]
  return list.map((p) => ({
    ...p,
    slots: slots.value.filter((s) => s.period === p.key)
  })).filter((p) => p.slots.length)
})

function slotClass(slot) {
  if (slot.isPast) return 'is-past'
  if (slot.isMine) return 'is-mine'
  if (slot.booked) return 'is-booked'
  if (slot.canBook) return 'is-available'
  return 'is-disabled'
}

function slotStatusText(slot) {
  if (slot.isPast) return '已过期'
  if (slot.isMine) return '我的预约'
  if (slot.booked) return slot.booker
  if (myBookedCount.value >= maxSlotsPerDay.value) return '已达上限'
  return '可预约'
}

function slotTitle(slot) {
  if (slot.booked && !slot.isMine) {
    return `${slot.booker}${slot.department ? '（' + slot.department + '）' : ''}`
  }
  return `${slot.startTime} – ${slot.endTime}`
}

function canClickSlot(slot) {
  if (actionLoading.value) return false
  if (slot.isPast) return false
  if (slot.isMine) return false
  if (slot.booked) return false
  return slot.canBook
}

async function loadConfig() {
  try {
    const res = await getMassageChairConfig()
    if (res.success) {
      usageNotice.value = res.usageNotice || []
      if (res.periods) periods.value = res.periods
      if (res.maxSlotsPerDay) maxSlotsPerDay.value = res.maxSlotsPerDay
    }
  } catch (e) {
    console.error(e)
  }
}

async function loadSlots() {
  if (!currentUser) {
    showToast('请先登录', 'error')
    return
  }
  loading.value = true
  try {
    const res = await getMassageChairSlots({
      booking_date: selectedDate.value,
      current_user: currentUser
    })
    if (res.success) {
      slots.value = res.slots || []
      myBookings.value = res.myBookings || []
      myBookedCount.value = res.myBookedCount ?? 0
      maxSlotsPerDay.value = res.maxSlotsPerDay ?? 2
      if (res.periods?.length) periods.value = res.periods
    }
  } catch (e) {
    showToast(errMsg(e), 'error')
    slots.value = []
    myBookings.value = []
  } finally {
    loading.value = false
  }
}

async function handleBook(slot) {
  if (!canClickSlot(slot)) return
  if (!confirm(`确认预约 ${selectedDate.value} ${slot.startTime}–${slot.endTime} ？\n每人每天最多 ${maxSlotsPerDay.value} 个时段，请按时使用。`)) {
    return
  }
  actionLoading.value = true
  try {
    const res = await bookMassageChair({
      current_user: currentUser,
      booking_date: selectedDate.value,
      start_time: slot.startTime
    })
    showToast(res.message || '预约成功')
    await loadSlots()
  } catch (e) {
    showToast(errMsg(e), 'error')
  } finally {
    actionLoading.value = false
  }
}

async function handleCancel(item) {
  if (!confirm(`确认取消 ${item.startTime}–${item.endTime} 的预约？`)) return
  actionLoading.value = true
  try {
    const res = await cancelMassageChairBooking({
      current_user: currentUser,
      booking_id: item.id
    })
    showToast(res.message || '已取消')
    await loadSlots()
  } catch (e) {
    showToast(errMsg(e), 'error')
  } finally {
    actionLoading.value = false
  }
}

onMounted(async () => {
  await loadConfig()
  await loadSlots()
})
</script>

<style scoped>
.massage-page {
  min-height: 100%;
  background: var(--color-bg-secondary, #f5f7fa);
}

.page-header {
  background: var(--color-bg-container, #fff);
  border: 1px solid var(--color-primary, #1890ff);
  border-radius: var(--radius-md, 8px);
  box-shadow: var(--shadow-card, 0 1px 3px rgba(0, 0, 0, 0.08));
  color: var(--color-text-primary, #333);
  padding: var(--spacing-xl, 24px) var(--spacing-lg, 16px);
  margin: var(--spacing-lg, 16px) var(--spacing-lg, 16px) var(--spacing-base, 12px);
}

.header-title {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0 0 8px;
  color: var(--color-text-primary, #333);
}

.header-subtitle {
  margin: 0;
  font-size: 0.9rem;
  color: var(--color-text-secondary, #666);
}

.container {
  max-width: 960px;
  margin: 0 auto;
  padding: var(--spacing-lg, 16px);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg, 16px);
}

.card {
  background: #fff;
  border-radius: var(--radius-lg, 12px);
  padding: var(--spacing-lg, 16px);
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,.08));
}

.notice-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  user-select: none;
}

.notice-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 1rem;
  color: #b45309;
}

.notice-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.notice-toggle {
  font-size: 0.85rem;
  color: var(--color-text-secondary, #666);
}

.notice-list {
  margin: 12px 0 0;
  padding-left: 1.25rem;
  color: var(--color-text-primary, #333);
  line-height: 1.7;
  font-size: 0.9rem;
}

.notice-list li + li {
  margin-top: 6px;
}

.notice-emphasis {
  margin: 12px 0 0;
  padding: 10px 12px;
  background: #fef3c7;
  border-left: 3px solid #f59e0b;
  border-radius: 4px;
  font-size: 0.88rem;
  color: #92400e;
  line-height: 1.6;
}

.toolbar-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.form-label {
  font-size: 0.9rem;
  color: var(--color-text-secondary, #666);
}

.date-input {
  padding: 8px 12px;
  border: 1px solid var(--color-border, #ddd);
  border-radius: var(--radius-md, 8px);
  font-size: 0.95rem;
}

.btn {
  padding: 8px 16px;
  border-radius: var(--radius-md, 8px);
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn-secondary {
  background: var(--color-bg-secondary, #f0f0f0);
  color: var(--color-text-primary, #333);
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.quota-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 12px;
  font-size: 0.9rem;
  color: var(--color-text-secondary, #666);
}

.quota-bar strong {
  color: #2d6a4f;
  font-size: 1.1rem;
}

.quota-hint {
  color: #40916c;
}

.section-title {
  margin: 0 0 12px;
  font-size: 1rem;
}

.my-booking-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.my-booking-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: #ecfdf5;
  border-radius: 8px;
  border: 1px solid #a7f3d0;
}

.my-booking-time {
  font-weight: 600;
  color: #065f46;
}

.btn-cancel {
  padding: 4px 12px;
  border: 1px solid #fca5a5;
  background: #fff;
  color: #dc2626;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
}

.btn-cancel:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.period-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 14px;
}

.period-title {
  margin: 0;
  font-size: 1rem;
  color: var(--color-text-primary, #333);
}

.period-range {
  font-size: 0.85rem;
  color: var(--color-text-secondary, #888);
}

.slot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 10px;
}

.slot-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 64px;
  padding: 8px 6px;
  border-radius: 10px;
  border: 2px solid transparent;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
  background: #f3f4f6;
}

.slot-time {
  font-weight: 600;
  font-size: 0.95rem;
}

.slot-status {
  font-size: 0.72rem;
  margin-top: 4px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.slot-btn.is-available {
  background: #ecfdf5;
  border-color: #6ee7b7;
  color: #065f46;
}

.slot-btn.is-available:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(45, 106, 79, 0.2);
}

.slot-btn.is-mine {
  background: #dbeafe;
  border-color: #60a5fa;
  color: #1e40af;
  cursor: default;
}

.slot-btn.is-booked {
  background: #fef2f2;
  border-color: #fecaca;
  color: #991b1b;
  cursor: not-allowed;
}

.slot-btn.is-past,
.slot-btn.is-disabled {
  background: #f9fafb;
  border-color: #e5e7eb;
  color: #9ca3af;
  cursor: not-allowed;
}

.slot-btn:disabled {
  cursor: not-allowed;
}

.loading-state,
.empty-state {
  text-align: center;
  color: var(--color-text-secondary, #888);
  padding: 32px;
}

.toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 24px;
  border-radius: 8px;
  color: #fff;
  font-size: 0.9rem;
  z-index: 9999;
  box-shadow: 0 4px 16px rgba(0,0,0,.15);
}

.toast.success { background: #059669; }
.toast.error { background: #dc2626; }

@media (max-width: 640px) {
  .slot-grid {
    grid-template-columns: repeat(auto-fill, minmax(84px, 1fr));
  }
}
</style>
