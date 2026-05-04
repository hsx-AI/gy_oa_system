<template>
  <div v-if="visible" class="modal-overlay">
    <div class="modal-content">
      <button type="button" class="modal-close-btn" @click="$emit('close')">&times;</button>
      <h2>加班登记</h2>
      <p class="modal-hint">填报完成后可继续处理其他建议</p>
      <form @submit.prevent="handleSubmit" class="application-form" autocomplete="on">
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
            <select v-model="form.level" name="overtimeLevel" autocomplete="on">
              <option value="平时加班">平时加班</option>
              <option value="值班">值班</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group half">
            <label>登记方式</label>
            <input type="text" v-model="form.registerMethod" readonly>
          </div>
          <div class="form-group half">
            <label>是否要换休票</label>
            <select v-model="form.needExchangeTicket" name="needExchangeTicket" autocomplete="on" :disabled="needExchangeTicketDisabled">
              <option value="是">是</option>
              <option value="否">否</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label>加班时间</label>
          <div class="date-range-inputs">
            <select v-model="form.date" name="overtimeDate" autocomplete="on" :disabled="timeLocked">
              <option v-for="d in dateOptions" :key="d" :value="d">{{ d }}</option>
            </select>
            <div class="time-inputs">
              <TimePicker v-model="form.startTime" :disabled="timeLocked" />
              <span>至</span>
              <TimePicker v-model="form.endTime" :disabled="timeLocked" />
            </div>
          </div>
          <p v-if="timeLocked" class="hint-text lock-hint">当前由智能建议自动填充，日期与时间不可修改</p>
          <p v-if="form.needExchangeTicket === '是'" class="hint-text ticket-hint">
            获得换休票：{{ overtimeExchangeTickets }} 张（1天=8小时=2张，以0.25为单位，不足0.25张舍弃）
          </p>
          <p v-if="form.needExchangeTicket === '否'" class="hint-text ticket-hint">
            <template v-if="isSpecialHoliday && overtimePayBillableHours >= 8 && overtimePayBillableHours > 8">
              本次其他绩效激励：{{ specialHolidayName }}固定奖励{{ SPECIAL_DAY_PAY }}元 + 超出部分{{ overtimePayBillableHours - 8 }}×{{ zhibanfei }}={{ overtimePay }} 元
            </template>
            <template v-else-if="isSpecialHoliday && overtimePayBillableHours >= 8">
              本次其他绩效激励：{{ specialHolidayName }}严格按照上下班打卡满8小时，固定奖励 {{ SPECIAL_DAY_PAY }} 元
            </template>
            <template v-else-if="isSpecialHoliday">
              本次其他绩效激励：{{ overtimePayBillableHours }}×{{ zhibanfei }}={{ overtimePay }} 元（{{ specialHolidayName }}严格按照上下班打卡满8小时可获固定200元奖励）
            </template>
            <template v-else>
              本次其他绩效激励：{{ overtimePayBillableHours }}×{{ zhibanfei }}={{ overtimePay }} 元
            </template>
          </p>
        </div>
        <div class="form-group">
          <label>加班内容</label>
          <RecentTextInput
            v-model="form.content"
            storage-key="recent_overtime_content"
            name="overtimeContent"
            placeholder="请输入加班内容"
            tag="textarea"
            :rows="3"
          />
        </div>
        <div class="form-group">
          <label>审批人</label>
          <select v-model="form.approver" name="overtimeApprover" autocomplete="on" :disabled="loadingApprovers">
            <option value="">请选择审批人</option>
            <option v-for="p in approvers" :key="p" :value="p">{{ p }}</option>
          </select>
        </div>
        <div class="form-actions">
          <button type="button" @click="$emit('close')">取消</button>
          <button type="submit" class="btn-primary">提交</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { getApprovers, getOvertimeWebconfig, submitOvertimeRegister, getHolidays } from '@/api/attendance'
import RecentTextInput from '@/components/RecentTextInput.vue'
import TimePicker from '@/components/TimePicker.vue'
import { validateOvertimeShiftTicket } from '@/utils/overtimeShiftValidation'
import { canChooseExchangeTicketWhenNormalOvertime, getOvertimeUserMeta, shouldLockExchangeTicketToYes } from '@/utils/overtimeLeaderRules'

const props = defineProps({
  visible: Boolean,
  prefill: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['close', 'submitted'])

const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
const form = reactive({
  department: userInfo.dept || userInfo.department || '技术部',
  name: userInfo.name || userInfo.userName || '',
  gender: userInfo.xbie || userInfo.gender || '男',
  jb: userInfo.jb || '',
  lsys: userInfo.lsys || userInfo.dept || userInfo.department || '',
  level: '平时加班',
  registerMethod: '书面',
  needExchangeTicket: '否',
  date: '',
  startTime: '08:00:00',
  endTime: '17:00:00',
  content: '',
  approver: ''
})

const dateOptions = ref([])
const approvers = ref([])
const loadingApprovers = ref(false)
const zhibanfei = ref(15)
/** 从智能建议入口进入时锁定日期与时间，不可编辑 */
const timeLocked = computed(() => !!props.prefill?.locked)
const overtimeUserMeta = computed(() => getOvertimeUserMeta(form))
const managerExchangeTicketLocked = computed(() => shouldLockExchangeTicketToYes(overtimeUserMeta.value))
const bubanCanChooseNormalOvertimeTicket = computed(() => canChooseExchangeTicketWhenNormalOvertime(overtimeUserMeta.value))
const needExchangeTicketDisabled = computed(() =>
  managerExchangeTicketLocked.value || (form.level === '平时加班' && !bubanCanChooseNormalOvertimeTicket.value)
)

function applyExchangeTicketRoleRule() {
  if (managerExchangeTicketLocked.value) {
    form.needExchangeTicket = '是'
  } else if (form.level === '平时加班' && !bubanCanChooseNormalOvertimeTicket.value) {
    form.needExchangeTicket = '否'
  }
}

const SPECIAL_FESTIVALS = new Set(['春节', '国庆节', '高温防暑休假'])
const SPECIAL_DAY_PAY = 200
const holidayMap = ref({})

function normalizeDate(d) {
  if (!d) return ''
  const parts = String(d).split('-')
  if (parts.length < 3) return d
  return `${parts[0]}-${parts[1].padStart(2, '0')}-${parts[2].padStart(2, '0')}`
}

function loadHolidaysForYear(year) {
  if (!year) return
  getHolidays(year).then(res => {
    if (res.success && res.holidays) {
      const map = {}
      for (const h of res.holidays) {
        if (h.date && h.festival) map[normalizeDate(h.date)] = h.festival
      }
      holidayMap.value = { ...holidayMap.value, ...map }
    }
  }).catch(() => {})
}

const isSpecialHoliday = computed(() => {
  if (!form.date) return false
  const fest = holidayMap.value[form.date] || ''
  return SPECIAL_FESTIVALS.has(fest)
})

const specialHolidayName = computed(() => {
  if (!form.date) return ''
  return holidayMap.value[form.date] || ''
})

// 加班获得换休票：早八晚五8小时工作制，午休1小时(12:00-13:00)不计入；1天=8小时=2张，以0.25为单位，不足0.25张舍弃
function calcOvertimeExchangeTickets(st, et) {
  if (!st || !et) return 0
  const toMins = (t) => {
    const s = String(t).trim()
    const parts = s.split(':')
    const h = parseInt(parts[0] || '0', 10)
    const m = parseInt(parts[1] || '0', 10)
    const sec = parseInt(parts[2] || '0', 10)
    return h * 60 + m + sec / 60
  }
  const startMins = toMins(st)
  const endMins = toMins(et)
  let mins = endMins - startMins
  if (mins <= 0) return 0
  const lunchStart = 12 * 60
  const lunchEnd = 13 * 60
  if (startMins < lunchEnd && endMins > lunchStart) {
    const overlap = Math.min(endMins, lunchEnd) - Math.max(startMins, lunchStart)
    mins = Math.max(0, mins - overlap)
  }
  const hours = mins / 60
  const tickets = hours / 4  // 1小时=0.25张
  return Math.floor(tickets * 4) / 4
}
const overtimeExchangeTickets = computed(() =>
  form.needExchangeTicket === '是' ? calcOvertimeExchangeTickets(form.startTime, form.endTime) : 0
)

// 其他绩效激励计算用工作时长：早八晚五，午休 12:00-13:00 不计入，再按 0.5 时为单位
function calcOvertimeWorkHours(st, et) {
  if (!st || !et) return 0
  const toMins = (t) => {
    const s = String(t).trim()
    const parts = s.split(':')
    const h = parseInt(parts[0] || '0', 10)
    const m = parseInt(parts[1] || '0', 10)
    const sec = parseInt(parts[2] || '0', 10)
    return h * 60 + m + sec / 60
  }
  const startMins = toMins(st)
  const endMins = toMins(et)
  let mins = endMins - startMins
  if (mins <= 0) return 0
  const lunchStart = 12 * 60
  const lunchEnd = 13 * 60
  if (startMins < lunchEnd && endMins > lunchStart) {
    const overlap = Math.min(endMins, lunchEnd) - Math.max(startMins, lunchStart)
    mins = Math.max(0, mins - overlap)
  }
  return mins / 60
}

const overtimePayBillableHours = computed(() => {
  if (form.needExchangeTicket !== '否') return 0
  const h = calcOvertimeWorkHours(form.startTime, form.endTime)
  return Math.floor(h * 2) / 2
})

const overtimePay = computed(() => {
  if (form.needExchangeTicket !== '否') return '0.00'
  if (isSpecialHoliday.value && overtimePayBillableHours.value >= 8) {
    const extraHours = overtimePayBillableHours.value - 8
    return (SPECIAL_DAY_PAY + extraHours * zhibanfei.value).toFixed(2)
  }
  return (overtimePayBillableHours.value * zhibanfei.value).toFixed(2)
})

// 解析粘贴的时间文本为 HH:mm 或 HH:mm:ss（支持 8:00、08:00、17:30:00 等格式）
function normalizePasteTime(str) {
  if (!str || typeof str !== 'string') return null
  const s = str.trim().replace(/\s/g, '')
  const parts = s.split(':')
  if (parts.length < 2) return null
  const h = Math.min(23, Math.max(0, parseInt(parts[0], 10)))
  const m = Math.min(59, Math.max(0, parseInt(parts[1], 10)))
  const sec = parts.length >= 3 ? Math.min(59, Math.max(0, parseInt(parts[2], 10))) : 0
  if (isNaN(h) || isNaN(m)) return null
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

function onPasteTime(e, field) {
  const text = e.clipboardData?.getData?.('text') || ''
  const normalized = normalizePasteTime(text)
  if (normalized) {
    e.preventDefault()
    form[field] = normalized
  }
}

// 普通员工平时加班锁定为否；经理/副经理/经理助理锁定为是；部办其他人员可自行选择
watch(
  () => [form.level, form.jb, form.lsys, form.department],
  () => applyExchangeTicketRoleRule(),
  { immediate: true }
)

watch(() => form.date, (newDate) => {
  if (newDate) {
    const y = parseInt(newDate.slice(0, 4), 10)
    if (y && !Object.keys(holidayMap.value).some(d => d.startsWith(String(y)))) {
      loadHolidaysForYear(y)
    }
  }
})

function initDateOptions() {
  const today = new Date()
  const opts = []
  for (let i = 0; i < 30; i++) {
    const d = new Date(today)
    d.setDate(today.getDate() - i)
    opts.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`)
  }
  dateOptions.value = opts
}

watch(() => props.visible, (v) => {
  if (v) {
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
    if (!(form.department || '').trim()) form.department = userInfo.dept || userInfo.department || '技术部'
    if (!(form.name || '').trim()) form.name = userInfo.name || userInfo.userName || ''
    form.jb = userInfo.jb || form.jb || ''
    form.lsys = userInfo.lsys || userInfo.dept || userInfo.department || form.lsys || form.department || ''
    applyExchangeTicketRoleRule()
    getOvertimeWebconfig().then((res) => {
      if (res.success && res.zhibanfei != null) zhibanfei.value = Number(res.zhibanfei)
    }).catch(() => {})
    loadHolidaysForYear(new Date().getFullYear())
    initDateOptions()
    if (props.prefill.date) {
      form.date = String(props.prefill.date).slice(0, 10)
      if (!dateOptions.value.includes(form.date)) dateOptions.value.unshift(form.date)
    } else {
      form.date = dateOptions.value[0] || new Date().toISOString().slice(0, 10)
    }
    const toTime = (t) => {
      if (!t) return '08:00:00'
      const s = String(t).replace(/^\d{4}-\d{2}-\d{2}T?/, '')
      const parts = s.split(':')
      const h = String(parseInt(parts[0] || '8', 10)).padStart(2, '0')
      const m = String(parseInt(parts[1] || '0', 10)).padStart(2, '0')
      const sec = String(parseInt(parts[2] || '0', 10)).padStart(2, '0')
      return `${h}:${m}:${sec}`
    }
    form.startTime = toTime(props.prefill.startTime)
    form.endTime = toTime(props.prefill.endTime)
    if (props.prefill.locked) form.content = ''
    else if (props.prefill.content) form.content = props.prefill.content
    if (form.name) fetchApprovers()
  }
})

async function fetchApprovers() {
  if (!form.name) return
  loadingApprovers.value = true
  try {
    const res = await getApprovers({ name: form.name, level: 'first' })
    approvers.value = (res.success && res.approvers) ? res.approvers.map(a => a.name) : []
  } catch {
    approvers.value = []
  } finally {
    loadingApprovers.value = false
  }
}

function resetForm() {
  form.level = '平时加班'
  form.registerMethod = '书面'
  form.needExchangeTicket = '否'
  form.content = ''
  form.approver = ''
  applyExchangeTicketRoleRule()
}

async function handleSubmit() {
  if (!form.content) { alert('请输入加班内容'); return }
  if (!form.approver) { alert('请选择审批人'); return }
  try {
    const st = (form.startTime || '08:00').length <= 5 ? form.startTime + ':00' : form.startTime
    const et = (form.endTime || '17:00').length <= 5 ? form.endTime + ':00' : form.endTime
    const shiftCheck = await validateOvertimeShiftTicket({
      ...form,
      startTime: st,
      endTime: et,
    })
    if (!shiftCheck.valid) {
      alert(shiftCheck.message || '排班校验未通过')
      return
    }
    const res = await submitOvertimeRegister({
      department: form.department,
      name: form.name,
      gender: form.gender,
      level: form.level,
      registerMethod: form.registerMethod,
      needExchangeTicket: form.needExchangeTicket,
      date: form.date,
      startTime: st,
      endTime: et,
      content: form.content,
      approver: form.approver
    })
    if (res.success) {
      emit('close')
      emit('submitted')
    } else {
      alert(res.message || '提交失败')
    }
  } catch (err) {
    const d = err.response?.data?.detail
    alert(Array.isArray(d) ? d.map(x => x.msg || x).join('; ') : (d || err.message) || '提交失败')
  }
}
</script>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal-content { position: relative; background: white; padding: var(--spacing-xl); border-radius: var(--radius-md); width: 700px; max-width: 95%; max-height: 90vh; overflow-y: auto; }
.modal-close-btn { position: absolute; top: 12px; right: 16px; background: none; border: none; font-size: 24px; color: var(--color-text-tertiary); cursor: pointer; line-height: 1; padding: 4px; z-index: 1; }
.modal-close-btn:hover { color: var(--color-text-primary); }
.modal-hint { font-size: var(--font-size-sm); color: var(--color-text-secondary); margin: 0 0 var(--spacing-md); }
.application-form { margin-top: var(--spacing-md); }
.form-row { display: flex; gap: var(--spacing-lg); margin-bottom: var(--spacing-lg); }
.form-group { margin-bottom: var(--spacing-lg); }
.form-group.half { flex: 1; margin-bottom: 0; }
.form-group label { display: block; margin-bottom: var(--spacing-xs); font-weight: 500; font-size: var(--font-size-sm); }
.form-group input, .form-group select, .form-group textarea { width: 100%; padding: 8px 12px; border: 1px solid var(--color-border-base); border-radius: var(--radius-sm); font-size: var(--font-size-base); }
.hint-text.ticket-hint { margin: var(--spacing-sm) 0 0; font-size: var(--font-size-sm); color: rgba(24, 144, 255, 1); }
.form-group input[readonly],
.form-group input:disabled { background: var(--color-bg-layout); cursor: not-allowed; }
.form-group select:disabled { background: var(--color-bg-layout); cursor: not-allowed; color: var(--color-text-secondary); }
.hint-text.lock-hint { margin: var(--spacing-xs) 0 0; font-size: var(--font-size-sm); color: var(--color-text-tertiary); }
.date-range-inputs { display: flex; flex-direction: column; gap: var(--spacing-sm); }
.time-inputs { display: flex; align-items: center; gap: var(--spacing-md); }
.time-inputs input { flex: 1; }
.form-actions { display: flex; justify-content: flex-end; gap: var(--spacing-md); margin-top: var(--spacing-xl); padding-top: var(--spacing-lg); border-top: 1px solid var(--color-border-lighter); }
.form-actions button { padding: 8px 20px; border-radius: var(--radius-sm); border: 1px solid var(--color-border-base); cursor: pointer; background: white; }
.form-actions .btn-primary { background: var(--color-primary); border-color: var(--color-primary); color: white; }
</style>
