<template>
  <div class="profile-page">
    <div class="container">
      <div class="page-header">
        <div class="header-content">
          <div class="header-info">
            <h1 class="header-title">员工信息</h1>
            <p class="header-subtitle">查看个人基本信息与所在科室</p>
          </div>
        </div>
      </div>
      <div class="profile-card card">
        <div class="profile-body" v-if="profile">
          <div class="profile-row">
            <span class="profile-label">用户名</span>
            <span class="profile-value">{{ profile.name || '-' }}</span>
          </div>
          <div class="profile-row">
            <span class="profile-label">工号</span>
            <span class="profile-value">{{ profile.workNo || '-' }}</span>
          </div>
          <div class="profile-row">
            <span class="profile-label">所在科室</span>
            <span class="profile-value">{{ profile.department || '-' }}</span>
          </div>
          <div class="profile-row">
            <span class="profile-label">当前级别</span>
            <span class="profile-value">{{ profile.level || '-' }}</span>
          </div>
          <div class="profile-row">
            <span class="profile-label">身份证号</span>
            <span class="profile-value">{{ profile.idNumber || '-' }}</span>
          </div>
          <div class="profile-row">
            <span class="profile-label">入厂时间</span>
            <span class="profile-value">{{ profile.entryDate || '-' }}</span>
          </div>
          <div class="profile-row">
            <span class="profile-label">带薪休假剩余</span>
            <span class="profile-value">
              <template v-if="profile.paidLeaveRemaining != null">
                {{ formatPaidLeave(profile.paidLeaveRemaining) }}
                <span v-if="profile.paidLeaveDetail" class="profile-value-sub">（应得{{ profile.paidLeaveDetail.entitlement }}天，固定扣除{{ profile.paidLeaveDetail.deducted }}天，本年已用{{ profile.paidLeaveDetail.used }}天）</span>
              </template>
              <template v-else>{{ '-' }}</template>
            </span>
          </div>
          <div class="profile-row">
            <span class="profile-label">换休票总数</span>
            <span class="profile-value">{{ profile.exchangeTickets ?? '-' }}</span>
          </div>
          <div v-if="profile.exchangeTicketDetails?.length" class="profile-row profile-row--details">
            <span class="profile-label">换休票明细</span>
            <div class="profile-value profile-details-wrap">
              <div class="profile-details-scroll">
                <template v-for="(d, i) in profile.exchangeTicketDetails" :key="d.expireDate">
                  <span v-if="i">，</span>{{ formatTicketCount(d.count) }}张于{{ formatExpireDate(d.expireDate) }}过期
                </template>
              </div>
            </div>
          </div>
        </div>
        <div v-else-if="loading" class="profile-loading">加载中...</div>
        <div v-else class="profile-empty">暂无员工信息</div>

        <div class="profile-actions">
          <button type="button" class="btn btn-primary" @click="showPasswordModal = true">修改密码</button>
        </div>
      </div>
    </div>

    <!-- 修改密码弹窗 -->
    <div v-if="showPasswordModal" class="modal-overlay" @click.self="showPasswordModal = false">
      <div class="modal-content">
        <h2>修改密码</h2>
        <form @submit.prevent="handleChangePassword" class="password-form" autocomplete="on">
          <div class="form-group">
            <label>原密码</label>
            <input type="password" v-model="passwordForm.oldPassword" name="oldPassword" autocomplete="current-password" required placeholder="请输入原密码">
          </div>
          <div class="form-group">
            <label>新密码</label>
            <input type="password" v-model="passwordForm.newPassword" name="newPassword" autocomplete="new-password" required minlength="4" placeholder="至少4位">
          </div>
          <div class="form-group">
            <label>确认新密码</label>
            <input type="password" v-model="passwordForm.confirmPassword" name="confirmPassword" autocomplete="new-password" required placeholder="请再次输入新密码">
          </div>
          <p v-if="passwordError" class="text-danger">{{ passwordError }}</p>
          <div class="form-actions">
            <button type="button" @click="showPasswordModal = false">取消</button>
            <button type="submit" class="btn-primary">确定</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getEmployeeProfile, changePassword } from '@/api/attendance'

const profile = ref(null)
const loading = ref(true)
const showPasswordModal = ref(false)
const passwordError = ref('')
const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const fetchProfile = async () => {
  const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
  const name = userInfo.name || userInfo.userName
  if (!name) {
    loading.value = false
    return
  }
  loading.value = true
  try {
    const res = await getEmployeeProfile({ name })
    if (res.success && res.data) {
      profile.value = res.data
    }
  } catch (e) {
    console.error('获取员工信息失败:', e)
  } finally {
    loading.value = false
  }
}

const handleChangePassword = async () => {
  passwordError.value = ''
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    passwordError.value = '两次输入的新密码不一致'
    return
  }
  if (passwordForm.value.newPassword.length < 4) {
    passwordError.value = '新密码至少4位'
    return
  }
  try {
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
    const name = userInfo.name || userInfo.userName
    const res = await changePassword({
      name,
      oldPassword: passwordForm.value.oldPassword,
      newPassword: passwordForm.value.newPassword
    })
    if (res.success) {
      alert('密码修改成功')
      showPasswordModal.value = false
      passwordForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
    } else {
      passwordError.value = res.message || '修改失败'
    }
  } catch (e) {
    passwordError.value = '修改失败，请重试'
  }
}

function formatTicketCount(n) {
  if (n == null || n === '') return ''
  const v = Number(n)
  return Number.isInteger(v) ? String(v) : String(v)  // 支持 0.5 张，不进位
}

function formatExpireDate(s) {
  if (!s || typeof s !== 'string') return s || ''
  const parts = s.split('-')
  if (parts.length >= 3) return `${parts[0]}年${parseInt(parts[1], 10)}月${parseInt(parts[2], 10)}日`
  if (parts.length >= 2) return `${parts[0]}年${parseInt(parts[1], 10)}月`
  return s
}

function formatPaidLeave(days) {
  if (days == null || days === '') return '-'
  const v = Number(days)
  if (Number.isNaN(v)) return '-'
  return `${v} 天`
}

onMounted(fetchProfile)
</script>

<style scoped>
.profile-page {
  min-height: 100%;
  padding-bottom: var(--spacing-xxl);
}
.container {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0;
}
.profile-card {
  padding: var(--spacing-xl);
}
.profile-body {
  margin-bottom: var(--spacing-xl);
}
.profile-row {
  display: flex;
  padding: var(--spacing-md) 0;
  border-bottom: 1px solid var(--color-border-lighter);
}
.profile-row:last-child {
  border-bottom: none;
}
.profile-row--details .profile-label {
  flex-shrink: 0;
}
.profile-details-wrap {
  min-width: 0;
}
.profile-details-scroll {
  max-height: 200px;
  overflow-y: auto;
  overflow-x: hidden;
  line-height: 1.6;
  padding-right: 4px;
}
.profile-row--details .profile-value {
  flex-wrap: wrap;
  line-height: 1.6;
}
.profile-label {
  width: 120px;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}
.profile-value {
  flex: 1;
  color: var(--color-text-primary);
}
.profile-value-sub {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-left: 0.25em;
}
.profile-loading, .profile-empty {
  padding: var(--spacing-xxl);
  text-align: center;
  color: var(--color-text-tertiary);
}
.profile-actions {
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-border-lighter);
}
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal-content {
  background: white;
  padding: var(--spacing-xl);
  border-radius: var(--radius-md);
  width: 400px;
  max-width: 90%;
}
.modal-content h2 {
  margin: 0 0 var(--spacing-lg);
  font-size: var(--font-size-lg);
}
.password-form .form-group {
  margin-bottom: var(--spacing-md);
}
.password-form label {
  display: block;
  margin-bottom: var(--spacing-xs);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
.password-form input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
}
.form-actions {
  margin-top: var(--spacing-lg);
  display: flex;
  gap: var(--spacing-md);
}
.form-actions button {
  padding: 8px 20px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-base);
  background: white;
  cursor: pointer;
}
.form-actions .btn-primary {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}
.text-danger {
  color: #dc2626;
  font-size: var(--font-size-sm);
  margin-top: var(--spacing-sm);
}
</style>
