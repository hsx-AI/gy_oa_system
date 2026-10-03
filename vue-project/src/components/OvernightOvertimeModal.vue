<template>
  <div v-if="visible" class="modal-overlay">
    <div class="modal-content">
      <button type="button" class="modal-close-btn" @click="$emit('close')">&times;</button>
      <h2>跨夜加班登记</h2>
      <p class="modal-hint">凌晨段（0:00 之后）。当天 17:00 到 24:00 仍按平时加班填报。</p>

      <div class="effect-note">
        <p><strong>{{ needCityTrip ? '填报后会同时发生两件事' : '填报说明' }}</strong></p>
        <p>1. 奖励二选一：双倍其他绩效激励（时长按 2 倍计入）；或者同时领取换休票和加班费（换休票按平时加班标准，不加倍，加班费按实际时长）。</p>
        <p v-if="needCityTrip">2. 主任/班组长、部门领导都通过后，系统会自动为前一天（{{ prevDate || '加班日前一天' }}）补记全天市内公出（08:00-17:00），事由「跨夜加班处理」，用来补上跨夜导致的前一天少一次打卡。</p>
        <p v-else>2. 前一天（{{ prevDate || '加班日前一天' }}）不是工作日，当天不上班，没有考勤异常，审批通过后不补市内公出。</p>
      </div>

      <form @submit.prevent="handleSubmit" class="application-form">
        <div class="form-row">
          <div class="form-group half">
            <label>班组</label>
            <input type="text" v-model="form.department" readonly>
          </div>
          <div class="form-group half">
            <label>姓名</label>
            <input type="text" v-model="form.name" readonly>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group half">
            <label>性别</label>
            <input type="text" v-model="form.gender" readonly>
          </div>
          <div class="form-group half">
            <label>类别</label>
            <input type="text" value="跨夜加班（凌晨段）" readonly>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group half">
            <label>登记方式</label>
            <input type="text" value="补报" readonly>
          </div>
          <div class="form-group half">
            <label>加班日期</label>
            <input type="text" :value="form.date" readonly>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group half">
            <label>开始时间</label>
            <input type="text" :value="form.startTime" readonly>
          </div>
          <div class="form-group half">
            <label>结束时间</label>
            <input type="text" :value="form.endTime" readonly>
          </div>
        </div>

        <div class="form-group">
          <label>奖励方式</label>
          <div class="reward-options">
            <label class="reward-option" :class="{ active: form.rewardMode === 'double_pay' }">
              <input type="radio" value="double_pay" v-model="form.rewardMode">
              <span>
                <strong>双倍其他绩效激励</strong>
                <small>约 {{ hoursText }} 小时按 2 倍计入，约 {{ money(doubledPay) }} 元。不发换休票。</small>
              </span>
            </label>
            <label class="reward-option" :class="{ active: form.rewardMode === 'ticket_and_pay' }">
              <input type="radio" value="ticket_and_pay" v-model="form.rewardMode">
              <span>
                <strong>换休票 + 加班费</strong>
                <small>换休票 {{ ticketText }} 张（不加倍），加班费约 {{ money(singlePay) }} 元。</small>
              </span>
            </label>
          </div>
        </div>

        <div class="form-group">
          <label>加班内容</label>
          <textarea v-model="form.content" rows="3" placeholder="请填写跨夜加班内容"></textarea>
        </div>

        <div class="form-row">
          <div class="form-group half">
            <label>主任/班组长</label>
            <select v-model="form.approver" :disabled="loadingApprovers">
              <option value="">{{ loadingApprovers ? '加载中…' : '请选择' }}</option>
              <option v-for="name in firstApprovers" :key="name" :value="name">{{ name }}</option>
            </select>
          </div>
          <div class="form-group half">
            <label>部门领导（经理/副经理/经理助理）</label>
            <select v-model="form.approver2" :disabled="loadingApprovers">
              <option value="">{{ loadingApprovers ? '加载中…' : '请选择' }}</option>
              <option v-for="name in secondApprovers" :key="name" :value="name">{{ name }}</option>
            </select>
          </div>
        </div>
        <p class="flow-hint">审批在「加班审批」中办理，顺序是主任/班组长，然后部门领导。不经过打卡管理员的打卡校验。</p>

        <label class="consent" :class="{ shake: consentShake, error: consentError }">
          <input type="checkbox" v-model="voluntaryConfirmed" @change="consentError = false">
          <span>本人自愿加班，知晓上述奖励<template v-if="needCityTrip">和自动补记市内公出</template></span>
        </label>
        <p v-if="consentError" class="consent-error">请勾选确认后方可提交</p>

        <div class="form-actions">
          <button type="button" @click="$emit('close')">取消</button>
          <button type="submit" class="btn-primary" :disabled="submitting">{{ submitting ? '提交中…' : '提交' }}</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { getApprovers, getOvertimeWebconfig, submitOvernightOvertime, getHolidays } from '@/api/attendance'
import { overtimeWorkMinutesBetween, calcOvertimeExchangeTicketsFromTimes } from '@/utils/overtimeExchangeTickets'
import { isWorkday } from '@/utils/leaveDuration'

const props = defineProps({
  visible: { type: Boolean, default: false },
  prefill: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['close', 'submitted'])

const form = reactive({
  department: '',
  name: '',
  gender: '男',
  date: '',
  startTime: '00:00:00',
  endTime: '06:00:00',
  content: '',
  rewardMode: 'double_pay',
  approver: '',
  approver2: ''
})
const zhibanfei = ref(15)
const firstApprovers = ref([])
const leaderApprovers = ref([])
const loadingApprovers = ref(false)
const submitting = ref(false)
const voluntaryConfirmed = ref(false)
const consentError = ref(false)
const consentShake = ref(false)
const holidayMap = ref({})

const secondApprovers = computed(() =>
  leaderApprovers.value.filter((name) => name && name !== form.approver)
)

const hours = computed(() => overtimeWorkMinutesBetween(form.startTime, form.endTime) / 60)
const hoursText = computed(() => formatNum(hours.value))
const tickets = computed(() => calcOvertimeExchangeTicketsFromTimes(form.startTime, form.endTime, '平时加班'))
const ticketText = computed(() => formatNum(tickets.value))
const singlePay = computed(() => hours.value * zhibanfei.value)
const doubledPay = computed(() => hours.value * 2 * zhibanfei.value)

const prevDate = computed(() => shiftDate(form.date, -1))
const needCityTrip = computed(() => {
  if (!prevDate.value) return false
  const d = new Date(`${prevDate.value}T00:00:00`)
  if (Number.isNaN(d.getTime())) return false
  return isWorkday(d, holidayMap.value)
})

watch(() => props.visible, (open) => {
  if (!open) return
  const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
  form.department = userInfo.dept || userInfo.department || userInfo.lsys || ''
  form.name = userInfo.name || userInfo.userName || ''
  form.gender = userInfo.xbie || userInfo.gender || '男'
  form.date = String(props.prefill.date || '').slice(0, 10)
  form.startTime = toTime(props.prefill.startTime, '00:00:00')
  form.endTime = toTime(props.prefill.endTime, '06:00:00')
  form.content = ''
  form.rewardMode = 'double_pay'
  form.approver = ''
  form.approver2 = ''
  voluntaryConfirmed.value = false
  consentError.value = false
  getOvertimeWebconfig().then((res) => {
    if (res?.success && res.zhibanfei != null) zhibanfei.value = Number(res.zhibanfei) || 15
  }).catch(() => {})
  const y = String(form.date || '').slice(0, 4)
  if (y) {
    getHolidays(y).then((res) => {
      if (res?.success && res.holidays) {
        const map = {}
        for (const h of res.holidays) {
          const key = String(h.date || '').slice(0, 10)
          const typ = h.type || h.festival || ''
          if (key && typ) map[key] = typ
        }
        holidayMap.value = map
      }
    }).catch(() => {})
  }
  loadApprovers()
})

function toTime(value, fallback) {
  if (!value) return fallback
  const parts = String(value).split(':')
  const h = String(parseInt(parts[0] || '0', 10)).padStart(2, '0')
  const m = String(parseInt(parts[1] || '0', 10)).padStart(2, '0')
  const s = String(parseInt(parts[2] || '0', 10)).padStart(2, '0')
  return `${h}:${m}:${s}`
}

function shiftDate(dateStr, days) {
  const s = String(dateStr || '').slice(0, 10)
  const d = new Date(`${s}T00:00:00`)
  if (Number.isNaN(d.getTime())) return ''
  d.setDate(d.getDate() + days)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function formatNum(n) {
  const v = Number(n) || 0
  if (Math.abs(v - Math.round(v)) < 1e-6) return String(Math.round(v))
  return String(Math.round(v * 100) / 100)
}

function money(n) {
  return (Number(n) || 0).toFixed(2)
}

async function loadApprovers() {
  if (!form.name) return
  loadingApprovers.value = true
  try {
    const selfName = form.name.trim()
    const [firstRes, leaderRes] = await Promise.all([
      getApprovers({ name: form.name, level: 'overnight_first' }),
      getApprovers({ name: form.name, level: 'dept_leader' })
    ])
    const names = (res) => (res?.success && res.approvers ? res.approvers.map((a) => a.name) : [])
    firstApprovers.value = names(firstRes).filter((n) => (n || '').trim() && n.trim() !== selfName)
    leaderApprovers.value = names(leaderRes).filter((n) => (n || '').trim() && n.trim() !== selfName)
  } catch {
    firstApprovers.value = []
    leaderApprovers.value = []
  } finally {
    loadingApprovers.value = false
  }
}

async function handleSubmit() {
  if (!voluntaryConfirmed.value) {
    consentError.value = true
    consentShake.value = false
    requestAnimationFrame(() => {
      consentShake.value = true
      setTimeout(() => { consentShake.value = false }, 500)
    })
    return
  }
  if (!form.content.trim()) {
    alert('请输入加班内容')
    return
  }
  if (!form.rewardMode) {
    alert('请选择奖励方式')
    return
  }
  if (!form.approver || !form.approver2) {
    alert('请选择主任/班组长和部门领导')
    return
  }
  if (form.approver === form.approver2) {
    alert('两级审批人不能是同一人')
    return
  }
  submitting.value = true
  try {
    const res = await submitOvernightOvertime({
      department: form.department,
      name: form.name,
      gender: form.gender,
      registerMethod: '补报',
      date: form.date,
      startTime: form.startTime,
      endTime: form.endTime,
      content: form.content.trim(),
      approver: form.approver,
      approver2: form.approver2,
      rewardMode: form.rewardMode
    })
    if (res?.success) {
      alert(res.message || '已提交')
      emit('close')
      emit('submitted')
    } else {
      alert(res?.message || '提交失败')
    }
  } catch (err) {
    const d = err.response?.data?.detail
    alert(Array.isArray(d) ? d.map((x) => x.msg || x).join('; ') : (d || err.message) || '提交失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal-content { position: relative; background: white; padding: 24px; border-radius: 12px; width: 760px; max-width: 96vw; max-height: 90vh; overflow-y: auto; }
.modal-close-btn { position: absolute; top: 12px; right: 14px; border: none; background: transparent; font-size: 28px; line-height: 1; cursor: pointer; color: #64748b; }
h2 { margin: 0 0 6px; font-size: 20px; }
.modal-hint { margin: 0 0 12px; color: #64748b; font-size: 13px; }
.effect-note { background: #eef2ff; border: 1px solid #c7d2fe; border-radius: 8px; padding: 12px 14px; margin-bottom: 16px; color: #312e81; font-size: 13px; line-height: 1.6; }
.effect-note p { margin: 0 0 6px; }
.effect-note p:last-child { margin-bottom: 0; }
.form-row { display: flex; gap: 12px; }
.form-group { margin-bottom: 12px; flex: 1; }
.form-group.half { min-width: 0; }
label { display: block; margin-bottom: 4px; font-size: 13px; color: #334155; }
input, select, textarea { width: 100%; box-sizing: border-box; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 10px; font-size: 14px; background: #fff; }
input[readonly] { background: #f8fafc; color: #475569; }
.reward-options { display: flex; flex-direction: column; gap: 8px; }
.reward-option { display: flex; gap: 8px; align-items: flex-start; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px; cursor: pointer; }
.reward-option.active { border-color: #4f46e5; background: #eef2ff; }
.reward-option input { width: auto; margin-top: 3px; }
.reward-option strong { display: block; }
.reward-option small { display: block; color: #475569; line-height: 1.4; margin-top: 2px; }
.flow-hint { margin: 0 0 12px; font-size: 12px; color: #4338ca; line-height: 1.5; }
.consent { display: flex; gap: 8px; align-items: flex-start; font-size: 13px; margin-bottom: 8px; }
.consent input { width: auto; margin-top: 2px; }
.consent.error { color: #b91c1c; }
.consent.shake { animation: shake 0.4s linear; }
.consent-error { color: #b91c1c; font-size: 12px; margin: 0 0 8px; }
.form-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }
.form-actions button { border: 1px solid #cbd5e1; background: #fff; border-radius: 6px; padding: 8px 16px; cursor: pointer; }
.btn-primary { background: #4338ca !important; color: #fff; border-color: #4338ca !important; }
.btn-primary:disabled { opacity: 0.7; cursor: not-allowed; }
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}
</style>
