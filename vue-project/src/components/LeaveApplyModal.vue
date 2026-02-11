<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <h2>申请请假</h2>
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
            <label>类别</label>
            <select v-model="form.type" name="leaveType" autocomplete="on">
              <option v-for="t in leaveTypes" :key="t" :value="t">{{ t }}</option>
            </select>
          </div>
          <div class="form-group half">
            <label>班次</label>
            <select v-model="form.shift" name="leaveShift" autocomplete="on">
              <option value="白班">白班</option>
              <option value="夜班">夜班</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group form-group--full">
            <label>联系方式</label>
            <input type="text" v-model="form.contactMethod" name="contactMethod" autocomplete="tel" placeholder="如：电话">
          </div>
        </div>
        <div class="form-row">
          <div class="form-group half">
            <label>开始时间</label>
            <input type="datetime-local" v-model="form.startTime" name="leaveStartTime" autocomplete="on" :disabled="timeLocked">
          </div>
          <div class="form-group half">
            <label>结束时间</label>
            <input type="datetime-local" v-model="form.endTime" name="leaveEndTime" autocomplete="on" :disabled="timeLocked">
          </div>
        </div>
        <div class="form-row">
          <div class="form-group half">
            <label>时长(天)</label>
            <input type="text" :value="form.duration" readonly class="duration-readonly">
            <p class="hint-text">根据开始/结束时间自动计算，仅计工作日：排除周六日与假期，调休上班日计入；工作时段 8:00-12:00、13:00-17:00，最小0.25天</p>
            <p v-if="form.type === '换休'" class="hint-text ticket-consumption">换休票消耗：{{ exchangeTicketConsume }} 张（1天=2张，最小0.5张=0.25天），剩余：{{ remainingTickets }} 张</p>
            <p v-if="form.type === '带薪年休假'" class="hint-text ticket-consumption">带薪年休假剩余：{{ paidLeaveDisplay }}<span v-if="paidLeaveDetail" class="hint-sub">（应得{{ paidLeaveDetail.entitlement }}天，固定扣除{{ paidLeaveDetail.deducted }}天，本年已用{{ paidLeaveDetail.used }}天）</span></p>
          </div>
        </div>
        <div class="form-group">
          <label>事由</label>
          <RecentTextInput
            v-model="form.reason"
            storage-key="recent_leave_reason"
            name="leaveReason"
            placeholder="请输入请假事由"
            tag="input"
          />
        </div>
        <div class="form-group">
          <label>说明材料（选填）</label>
          <textarea v-model="form.material" name="leaveMaterial" autocomplete="on" rows="2" placeholder="如有相关证明材料请在此说明"></textarea>
          <div class="form-file-wrap mt-sm">
            <input type="file" ref="materialFileRef" @change="onMaterialFileChange" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png">
            <span class="file-hint">支持 PDF、Word、图片</span>
            <span v-if="form.materialFileName" class="file-selected">{{ form.materialFileName }}</span>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group half">
            <label>第一审批人</label>
            <select v-model="form.approver1" name="approver1" autocomplete="on" :disabled="loadingApprovers">
              <option value="">请选择审批人</option>
              <option v-for="p in approvers1" :key="p" :value="p">{{ p }}</option>
            </select>
          </div>
          <div class="form-group half checkbox-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="form.needSecondApproval">
              需要二级审批
            </label>
          </div>
        </div>
        <div class="form-group" v-if="form.needSecondApproval">
          <label>第二审批人</label>
            <select v-model="form.approver2" name="approver2" autocomplete="on" :disabled="loadingApprovers">
            <option value="">请选择审批人</option>
            <option v-for="p in approvers2" :key="p" :value="p">{{ p }}</option>
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
import { getApprovers, submitLeaveApplication, getEmployeeProfile, getHolidays } from '@/api/attendance'
import { calcDurationFromTimes, normalizeDateKey } from '@/utils/leaveDuration'
import RecentTextInput from '@/components/RecentTextInput.vue'

const props = defineProps({
  visible: Boolean,
  prefill: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['close', 'submitted'])

const leaveTypes = ['事假', '换休', '病假', '婚假', '探亲假', '丧假', '产假', '工伤假', '护理', '计划生育假', '带薪年休假']

const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
const form = reactive({
  department: userInfo.dept || userInfo.department || '技术部',
  name: userInfo.name || userInfo.userName || '',
  type: '事假',
  shift: '白班',
  contactMethod: '电话',
  startTime: '',
  endTime: '',
  duration: 0,
  reason: '',
  material: '',
  materialFile: null,
  materialFileName: '',
  approver1: '',
  needSecondApproval: false,
  approver2: ''
})

// 1天=2张，最小0.5张(0.25天=2小时)，四舍五入到0.5
const exchangeTicketConsume = computed(() => {
  const d = form.duration || 0
  return d <= 0 ? 0 : Math.round(d * 4) / 2
})
const timeLocked = computed(() => !!props.prefill?.locked)
const remainingTickets = ref(0)
const paidLeaveRemaining = ref(null)
const paidLeaveDetail = ref(null)
const paidLeaveDisplay = computed(() => {
  const v = paidLeaveRemaining.value
  if (v == null) return '加载中…'
  const n = Number(v)
  if (Number.isNaN(n) || n < 0) return '0 天'
  return `${n} 天`
})
const approvers1 = ref([])
const approvers2 = ref([])
const loadingApprovers = ref(false)
const materialFileRef = ref(null)

const holidayMapCache = ref({})

function parseLocalDate(str) {
  if (!str || typeof str !== 'string') return null
  const s = str.trim().replace('T', ' ')
  const datePart = s.split(' ')[0]
  if (!datePart) return null
  const parts = datePart.split('-').map(Number)
  if (parts.length < 3) return null
  const [y, mo, day] = parts
  return new Date(y, mo - 1, day, 0, 0, 0, 0)
}

async function getHolidayMapForRange(startStr, endStr) {
  const start = parseLocalDate(startStr)
  const end = parseLocalDate(endStr)
  if (!start || !end) return {}
  const y1 = start.getFullYear()
  const y2 = end.getFullYear()
  const merged = {}
  for (let y = Math.min(y1, y2); y <= Math.max(y1, y2); y++) {
    if (!holidayMapCache.value[y]) {
      try {
        const res = await getHolidays(String(y))
        const map = {}
        if (res.holidays && Array.isArray(res.holidays)) {
          for (const h of res.holidays) {
            const key = normalizeDateKey(h.date)
            if (key) map[key] = h.type || ''
          }
        }
        holidayMapCache.value[y] = map
      } catch {
        holidayMapCache.value[y] = {}
      }
    }
    Object.assign(merged, holidayMapCache.value[y])
  }
  return merged
}

function onMaterialFileChange(e) {
  const file = e.target.files?.[0]
  form.materialFile = file || null
  form.materialFileName = file ? file.name : ''
}

watch(() => props.visible, async (v) => {
  if (v) {
    form.type = props.prefill.type || '事假'
    form.startTime = props.prefill.startTime || ''
    form.endTime = props.prefill.endTime || ''
    if (form.startTime && form.endTime) {
      const map = await getHolidayMapForRange(form.startTime, form.endTime)
      form.duration = calcDurationFromTimes(form.startTime, form.endTime, map)
    } else {
      form.duration = 0
    }
    if (props.prefill.locked) form.reason = ''
    else form.reason = props.prefill.reason || ''
    form.needSecondApproval = false
    form.approver2 = ''
    if (form.name) {
      fetchApprovers()
      try {
        const res = await getEmployeeProfile({ name: form.name })
        if (res.success && res.data) {
          remainingTickets.value = Number(res.data.exchangeTickets) || 0
          paidLeaveRemaining.value = res.data.paidLeaveRemaining != null ? Number(res.data.paidLeaveRemaining) : null
          paidLeaveDetail.value = res.data.paidLeaveDetail || null
        } else {
          paidLeaveRemaining.value = null
          paidLeaveDetail.value = null
        }
      } catch {
        remainingTickets.value = 0
        paidLeaveRemaining.value = null
        paidLeaveDetail.value = null
      }
    }
  }
})

watch([() => form.startTime, () => form.endTime], async () => {
  if (!form.startTime || !form.endTime) {
    form.duration = 0
    return
  }
  const map = await getHolidayMapForRange(form.startTime, form.endTime)
  form.duration = calcDurationFromTimes(form.startTime, form.endTime, map)
})

async function fetchApprovers() {
  if (!form.name) return
  loadingApprovers.value = true
  try {
    const [r1, r2] = await Promise.all([
      getApprovers({ name: form.name, level: 'first' }),
      getApprovers({ name: form.name, level: 'second' })
    ])
    approvers1.value = (r1.success && r1.approvers) ? r1.approvers.map(a => a.name) : []
    approvers2.value = (r2.success && r2.approvers) ? r2.approvers.map(a => a.name) : []
  } catch {
    approvers1.value = []
    approvers2.value = []
  } finally {
    loadingApprovers.value = false
  }
}

function resetForm() {
  form.type = '事假'
  form.contactMethod = '电话'
  form.material = ''
  form.materialFile = null
  form.materialFileName = ''
  materialFileRef.value && (materialFileRef.value.value = '')
  form.approver1 = ''
  form.needSecondApproval = false
  form.approver2 = ''
}

async function handleSubmit() {
  if (!form.department?.trim()) { alert('请完善班组信息'); return }
  if (!form.name?.trim()) { alert('请完善姓名信息'); return }
  if (!form.type) { alert('请选择请假类别'); return }
  if (!form.shift) { alert('请选择班次'); return }
  if (!form.startTime) { alert('请选择开始时间'); return }
  if (!form.endTime) { alert('请选择结束时间'); return }
  const dur = Number(form.duration)
  if (isNaN(dur) || dur <= 0) { alert('请填写有效的请假时长（大于 0）'); return }
  if (!form.reason?.trim()) { alert('请输入请假事由'); return }
  if (form.type === '换休') {
    const consume = exchangeTicketConsume.value
    const remain = remainingTickets.value
    if (remain - consume < 0) {
      alert(`换休票不足：剩余 ${remain} 张，本次需消耗 ${consume} 张，无法提交`)
      return
    }
  }
  if (form.type === '带薪年休假') {
    const remain = paidLeaveRemaining.value
    if (remain == null) {
      alert('无法获取带薪年休假余额，请稍后重试')
      return
    }
    const remainNum = Math.max(0, Number(remain))
    if (dur > remainNum) {
      alert(`带薪年休假剩余不足：剩余 ${remainNum} 天，本次申请 ${dur} 天，不能超出剩余天数`)
      return
    }
  }
  if (!form.approver1) { alert('请选择第一审批人'); return }
  if (form.needSecondApproval && !form.approver2) { alert('需要二级审批时请选择第二审批人'); return }
  try {
    const toDt = (s) => s ? s.replace('T', ' ') + (s.length <= 16 ? ':00' : '') : ''
    const payload = {
      department: form.department,
      name: form.name,
      type: form.type,
      shift: form.shift,
      contactMethod: form.contactMethod,
      startTime: toDt(form.startTime),
      endTime: toDt(form.endTime),
      duration: Number(form.duration),
      exchangeTicketNo: '',
      reason: form.reason,
      material: form.material || '',
      approver1: form.approver1,
      needSecondApproval: form.needSecondApproval,
      approver2: form.approver2 || ''
    }
    if (form.materialFile) payload.materialFile = form.materialFile
    const res = await submitLeaveApplication(payload)
    if (res.success) {
      alert('申请已提交')
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
.modal-content { background: white; padding: var(--spacing-xl); border-radius: var(--radius-md); width: 700px; max-width: 95%; max-height: 90vh; overflow-y: auto; }
.modal-hint { font-size: var(--font-size-sm); color: var(--color-text-secondary); margin: 0 0 var(--spacing-md); }
.application-form { margin-top: var(--spacing-md); }
.form-row { display: flex; gap: var(--spacing-lg); margin-bottom: var(--spacing-lg); }
.form-group { margin-bottom: var(--spacing-lg); }
.form-group.half { flex: 1; margin-bottom: 0; }
.form-group.form-group--full { flex: 1; }
.form-group label { display: block; margin-bottom: var(--spacing-xs); font-weight: 500; font-size: var(--font-size-sm); }
.form-group input, .form-group select, .form-group textarea { width: 100%; padding: 8px 12px; border: 1px solid var(--color-border-base); border-radius: var(--radius-sm); font-size: var(--font-size-base); }
.form-group input[readonly], .duration-readonly { background: var(--color-bg-layout); }
.hint-text { margin: var(--spacing-xs) 0 0; font-size: var(--font-size-xs); color: var(--color-text-tertiary); }
.form-file-wrap { display: flex; align-items: center; gap: var(--spacing-sm); flex-wrap: wrap; }
.form-file-wrap.mt-sm { margin-top: var(--spacing-sm); }
.form-file-wrap input[type="file"] { font-size: var(--font-size-sm); }
.file-hint { font-size: var(--font-size-xs); color: var(--color-text-tertiary); }
.file-selected { font-size: var(--font-size-sm); color: var(--color-primary); }
.ticket-consumption { color: var(--color-primary); font-weight: 500; margin-top: 6px; }
.hint-sub { font-weight: normal; color: var(--color-text-tertiary); margin-left: 0.25em; }
.checkbox-label { display: flex; align-items: center; gap: var(--spacing-xs); cursor: pointer; }
.form-actions { display: flex; justify-content: flex-end; gap: var(--spacing-md); margin-top: var(--spacing-xl); padding-top: var(--spacing-lg); border-top: 1px solid var(--color-border-lighter); }
.form-actions button { padding: 8px 20px; border-radius: var(--radius-sm); border: 1px solid var(--color-border-base); cursor: pointer; background: white; }
.form-actions .btn-primary { background: var(--color-primary); border-color: var(--color-primary); color: white; }
</style>
