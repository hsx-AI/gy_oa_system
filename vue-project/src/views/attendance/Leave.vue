<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">请假管理</h1>
          <p class="header-subtitle">申请请假、查看记录与审批状态</p>
        </div>
        <div class="header-actions">
          <button v-if="canApprove" class="btn btn-outline" @click="$router.push({ path: '/attendance/approvals', query: { type: 'leave' } })">审批</button>
          <button class="btn btn-primary" @click="showApplyModal = true">申请请假</button>
        </div>
      </div>
    </div>

    <!-- 请假记录 -->
    <div class="content mt-xl">
      <div class="card record-card">
        <div class="card-header record-card__header">
          <div>
            <h3>请假记录</h3>
            <p class="record-card__desc">{{ recordFilterLabel }}</p>
          </div>
          <div class="record-card__filters">
            <label class="filter-label">筛选：</label>
            <select v-model.number="recordYear" class="filter-select">
              <option v-for="y in recordYearOptions" :key="y" :value="y">{{ y }}年</option>
            </select>
            <span class="filter-text">全年</span>
            <select v-model="recordStatus" class="filter-select">
              <option value="processing">审批中/已驳回</option>
              <option value="approved">已通过</option>
              <option value="all">全部</option>
            </select>
          </div>
        </div>
        <div class="card-body record-card__body">
          <div class="table-wrap" v-if="myRecordList.length">
            <table class="record-table">
              <thead>
                <tr>
                  <th>请假类型</th>
                  <th>开始时间</th>
                  <th>结束时间</th>
                  <th>时长(天)</th>
                  <th>登记时间</th>
                  <th>审批状态</th>
                  <th>当前审批人</th>
                  <th>驳回原因</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in recordDisplayList" :key="r.id" :data-record-id="r.id">
                  <td>{{ r.type }}</td>
                  <td>{{ r.startTime }}</td>
                  <td>{{ r.endTime }}</td>
                  <td>{{ r.duration }}</td>
                  <td>{{ r.applyTime }}</td>
                  <td><span class="status-tag" :class="r.statusClass">{{ r.status }}</span></td>
                  <td>{{ r.currentApprover || '-' }}</td>
                  <td class="reject-reason-cell">{{ r.status === '已驳回' && r.rejectReason ? r.rejectReason : '—' }}</td>
                  <td>
                    <button v-if="r.status === '已驳回'" type="button" class="btn btn-sm btn-danger" @click="deleteRejectedLeave(r)">删除</button>
                    <span v-else>—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="record-pagination" v-if="myRecordList.length">
            <span class="record-pagination__total">共 {{ recordTotal }} 条</span>
            <span class="record-pagination__size">
              每页
              <select v-model.number="recordPageSize" class="record-pagination__select">
                <option :value="10">10</option>
                <option :value="20">20</option>
                <option :value="50">50</option>
              </select>
              条
            </span>
            <div class="record-pagination__pages">
              <button type="button" class="record-pagination__btn" :disabled="recordPage <= 1" @click="recordPage = Math.max(1, recordPage - 1)">上一页</button>
              <span class="record-pagination__num">第 {{ recordPage }} / {{ recordTotalPages || 1 }} 页</span>
              <button type="button" class="record-pagination__btn" :disabled="recordPage >= recordTotalPages" @click="recordPage = Math.min(recordTotalPages, recordPage + 1)">下一页</button>
            </div>
          </div>
          <p class="empty-text" v-else>暂无请假记录</p>
        </div>
      </div>
    </div>

    <!-- 申请弹窗 -->
    <div v-if="showApplyModal" class="modal-overlay" @click.self="showApplyModal = false">
      <div class="modal-content">
        <h2>申请请假</h2>
        <form @submit.prevent="submitApplication" class="application-form" autocomplete="on">
          <!-- 基础信息 -->
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
                <option v-for="type in leaveTypes" :key="type" :value="type">{{ type }}</option>
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

          <!-- 时间信息 -->
          <div class="form-row">
            <div class="form-group half">
              <label>开始时间</label>
              <input type="datetime-local" v-model="form.startTime" name="leaveStartTime" autocomplete="on">
            </div>
            <div class="form-group half">
              <label>结束时间</label>
              <input type="datetime-local" v-model="form.endTime" name="leaveEndTime" autocomplete="on">
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
            <div class="form-group half" v-if="form.type === '员工换休票'">
              <label>换休票序号</label>
              <input type="text" v-model="form.exchangeTicketNo" name="exchangeTicketNo" autocomplete="on" placeholder="请输入换休票序号">
              <p class="hint-text text-danger">剩余换休票：{{ remainingTickets }}</p>
            </div>
          </div>

          <!-- 事由与材料 -->
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
            <textarea v-model="form.material" name="leaveMaterial" autocomplete="on" rows="3" placeholder="如有相关证明材料请在此说明"></textarea>
            <div class="form-file-wrap mt-sm">
              <input type="file" ref="materialFileRef" @change="onMaterialFileChange" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png">
              <span class="file-hint">支持 PDF、Word、图片</span>
              <span v-if="form.materialFileName" class="file-selected">{{ form.materialFileName }}</span>
            </div>
          </div>

          <!-- 审批流程 -->
          <div class="form-row">
            <div class="form-group half">
              <label>第一审批人</label>
              <select v-model="form.approver1" name="approver1" autocomplete="on" :disabled="loadingApprovers">
                <option value="">请选择审批人</option>
                <option v-for="person in approvers1" :key="person" :value="person">{{ person }}</option>
              </select>
            </div>
            <div class="form-group checkbox-group">
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
              <option v-for="person in approvers2" :key="person" :value="person">{{ person }}</option>
            </select>
          </div>

          <!-- 底部操作 -->
          <div class="form-actions">
            <button type="button" @click="showApplyModal = false">取消</button>
            <button type="submit" class="btn-primary">提交</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getLeaveList, submitLeaveApplication, getApprovers, getEmployeeProfile, getHolidays, checkCanApprove, deleteLeaveRecord } from '@/api/attendance'
import { calcDurationFromTimes, normalizeDateKey } from '@/utils/leaveDuration'
import RecentTextInput from '@/components/RecentTextInput.vue'

const router = useRouter()
const route = useRoute()
const showApplyModal = ref(false)
const remainingTickets = ref(0) // 剩余换休票数，后续需从后端获取
const paidLeaveRemaining = ref(null)
const paidLeaveDetail = ref(null)
const paidLeaveDisplay = computed(() => {
  const v = paidLeaveRemaining.value
  if (v == null) return '加载中…'
  const n = Number(v)
  if (Number.isNaN(n) || n < 0) return '0 天'
  return `${n} 天`
})
const loadingList = ref(false)

// 本人的请假记录（从 API 获取）
const myRecordList = ref([])

// 请假记录分页
const recordPage = ref(1)
const recordPageSize = ref(10)
const recordTotal = computed(() => myRecordList.value.length)
const recordTotalPages = computed(() => Math.max(1, Math.ceil(recordTotal.value / recordPageSize.value)))
const recordDisplayList = computed(() => {
  const list = myRecordList.value
  const size = recordPageSize.value
  const start = (recordPage.value - 1) * size
  return list.slice(start, start + size)
})
watch(recordPageSize, () => { recordPage.value = 1 })

// 本人记录筛选：年份+全年，审批状态默认全部
const recordYear = ref(new Date().getFullYear())
const recordYearOptions = computed(() => {
  const y = new Date().getFullYear()
  return Array.from({ length: 6 }, (_, i) => y - i)  // 当前年及前5年
})
const recordStatus = ref('all')
const recordFilterLabel = computed(() => {
  const statusText = recordStatus.value === 'approved' ? '已通过' : recordStatus.value === 'processing' ? '审批中/已驳回' : '全部'
  return `展示 ${recordYear.value}年全年，${statusText} 本人的请假记录`
})
watch([recordYear, recordStatus], () => { fetchLeaveList() })

// 请假类型选项
const leaveTypes = [
  '事假', '换休', '病假', '婚假', '探亲假', '丧假', 
  '产假', '工伤假', '护理', '计划生育假', '带薪年休假'
]

// 审批人列表（从API按规则获取）
const approvers1 = ref([])  // 第一审批人
const approvers2 = ref([])  // 第二审批人（二级审批）
const loadingApprovers = ref(false)

const fetchApprovers = async () => {
  if (!form.name) return
  loadingApprovers.value = true
  try {
    const [r1, r2] = await Promise.all([
      getApprovers({ name: form.name, level: 'first' }),
      getApprovers({ name: form.name, level: 'second' })
    ])
    const selfName = (form.name || '').trim()
    approvers1.value = (r1.success && r1.approvers)
      ? r1.approvers.map(a => a.name).filter(n => (n || '').trim() !== selfName)
      : []
    approvers2.value = (r2.success && r2.approvers) ? r2.approvers.map(a => a.name) : []
  } catch (err) {
    console.error('获取审批人失败:', err)
    approvers1.value = []
    approvers2.value = []
  } finally {
    loadingApprovers.value = false
  }
}

// 从 localStorage 获取当前用户
function initUserInfo() {
  const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
  return {
    department: userInfo.dept || userInfo.department || '技术部',
    name: userInfo.name || userInfo.userName || '当前用户',
    jb: userInfo.jb || ''
  }
}

const userInfo = initUserInfo()
const canApprove = ref(false)
const form = reactive({
  department: userInfo.department,
  name: userInfo.name,
  type: '事假',
  shift: '白班',
  contactMethod: '电话',
  startTime: '',
  endTime: '',
  duration: 0,
  exchangeTicketNo: '',
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
const materialFileRef = ref(null)

// 假期表缓存：按年缓存 { "YYYY-MM-DD": "类型" }，用于时长计算（排除假期、计入调休上班）
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

/** 获取请假时间范围内涉及的年份的假期映射（合并多年），用于 calcDurationFromTimes */
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

const resetForm = () => {
  form.type = '事假'
  form.shift = '白班'
  form.contactMethod = '电话'
  form.startTime = ''
  form.endTime = ''
  form.duration = 0
  form.exchangeTicketNo = ''
  form.reason = ''
  form.material = ''
  form.materialFile = null
  form.materialFileName = ''
  materialFileRef.value && (materialFileRef.value.value = '')
  form.approver1 = ''
  form.needSecondApproval = false
  form.approver2 = ''
}

const fetchLeaveList = async () => {
  loadingList.value = true
  try {
    const params = { name: form.name, year: recordYear.value, status: recordStatus.value }
    const res = await getLeaveList(params)
    if (res.success && res.data) {
      myRecordList.value = res.data
    }
  } catch (err) {
    console.error('获取请假记录失败:', err)
    myRecordList.value = []
  } finally {
    loadingList.value = false
  }
}

async function deleteRejectedLeave(r) {
  if (!r?.id || r.status !== '已驳回') return
  if (!confirm('确认删除这条已驳回的请假记录？删除后不可恢复。')) return
  try {
    await deleteLeaveRecord(r.id, { name: form.name })
    alert('已删除')
    fetchLeaveList()
  } catch (e) {
    alert(e.response?.data?.detail || e.message || '删除失败')
  }
}

onMounted(async () => {
  const name = (userInfo.name || '').trim()
  if (name) {
    try {
      const res = await checkCanApprove({ name })
      canApprove.value = !!(res && res.canApprove)
    } catch (_) {
      canApprove.value = false
    }
  }
  // 从首页点击流程：以业务时间(请假年+状态)筛选，再按 focusId 定位到该条并滚动
  const q = route.query
  if (q.focusId) {
    if (q.year) recordYear.value = Number(q.year)
    if (q.status === 'processing' || q.status === 'approved' || q.status === 'all') recordStatus.value = q.status
  }
  await fetchLeaveList()
  if (q.focusId) {
    const idx = myRecordList.value.findIndex(r => String(r.id) === String(q.focusId))
    if (idx >= 0) {
      recordPage.value = Math.ceil((idx + 1) / recordPageSize.value)
      await nextTick()
      document.querySelector(`[data-record-id="${q.focusId}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }
  // 从打卡记录页跳转来的预填
  if (q.openModal === '1' && q.prefillDate) {
    form.type = q.prefillType || '事假'
    form.startTime = q.prefillStart || ''
    form.endTime = q.prefillEnd || ''
    form.duration = parseFloat(q.prefillDuration) || 0
    if (q.prefillReason) form.reason = q.prefillReason
    showApplyModal.value = true
    router.replace({ path: '/attendance/leave' })
  }
})

watch(showApplyModal, async (visible) => {
  if (visible && form.name) {
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
})

watch([() => form.startTime, () => form.endTime], async () => {
  if (!form.startTime || !form.endTime) {
    form.duration = 0
    return
  }
  const map = await getHolidayMapForRange(form.startTime, form.endTime)
  form.duration = calcDurationFromTimes(form.startTime, form.endTime, map)
})

const submitApplication = async () => {
  if (!form.department?.trim()) {
    alert('请完善班组信息')
    return
  }
  if (!form.name?.trim()) {
    alert('请完善姓名信息')
    return
  }
  if (!form.type) {
    alert('请选择请假类别')
    return
  }
  if (!form.shift) {
    alert('请选择班次')
    return
  }
  if (!form.startTime) {
    alert('请选择开始时间')
    return
  }
  if (!form.endTime) {
    alert('请选择结束时间')
    return
  }
  const dur = Number(form.duration)
  if (isNaN(dur) || dur <= 0) {
    alert('请填写有效的请假时长（大于 0）')
    return
  }
  if (form.type === '员工换休票' && !form.exchangeTicketNo?.trim()) {
    alert('使用员工换休票时请填写换休票序号')
    return
  }
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
  if (!form.reason?.trim()) {
    alert('请输入请假事由')
    return
  }
  if (!form.approver1) {
    alert('请选择第一审批人')
    return
  }
  if (form.needSecondApproval && !form.approver2) {
    alert('需要二级审批时请选择第二审批人')
    return
  }

  try {
    // datetime-local 返回 "2025-02-01T08:00"，转换为 "2025-02-01 08:00:00"
    const toDateTime = (s) => s ? s.replace('T', ' ') + (s.length <= 16 ? ':00' : '') : ''
    const payload = {
      department: form.department,
      name: form.name,
      type: form.type,
      shift: form.shift,
      contactMethod: form.contactMethod,
      startTime: toDateTime(form.startTime),
      endTime: toDateTime(form.endTime),
      duration: Number(form.duration),
      exchangeTicketNo: form.exchangeTicketNo,
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
      showApplyModal.value = false
      fetchLeaveList()
    } else {
      alert(res.message || '提交失败')
    }
  } catch (err) {
    const detail = err.response?.data?.detail
    const msg = Array.isArray(detail) ? detail.map(d => d.msg || d).join('; ') : (detail || err.message)
    alert(msg || '提交失败，请稍后重试')
  }
}
</script>

<style scoped>
.page-container {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0 0 var(--spacing-xl);
}

.btn-outline { background: white; border: 1px solid var(--color-primary); color: var(--color-primary); }
.btn-outline:hover { background: var(--color-primary-lightest); }

.card {
  background: white;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-lighter);
}

.card-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-lighter);
}

.record-card { background: white; border-radius: var(--radius-md); box-shadow: var(--shadow-sm); border: 1px solid var(--color-border-lighter); overflow: hidden; }
.record-card__header { padding: var(--spacing-lg) var(--spacing-xl); background: white; border-bottom: 1px solid var(--color-border-lighter); display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: var(--spacing-md); }
.record-card__header h3 { margin: 0 0 var(--spacing-xs); }
.record-card__filters { display: flex; align-items: center; gap: var(--spacing-sm); flex-shrink: 0; }
.record-card__filters .filter-label { font-size: var(--font-size-sm); color: var(--color-text-secondary); }
.record-card__filters .filter-text { font-size: var(--font-size-sm); color: var(--color-text-secondary); }
.record-card__filters .filter-select { padding: 6px 10px; border: 1px solid var(--color-border-base); border-radius: var(--radius-sm); font-size: var(--font-size-sm); }
.record-card__desc { margin: 0; font-size: var(--font-size-sm); color: var(--color-text-secondary); font-weight: normal; }
.card-body { padding: var(--spacing-lg); }
.record-card__body { padding: 0; background: white; }
.record-card__body .table-wrap { overflow-x: auto; }
.record-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); background: white; }
.record-table th, .record-table td { padding: 12px var(--spacing-xl); text-align: left; border-bottom: 1px solid var(--color-border-lighter); background: white; }
.record-table th { font-weight: 600; color: var(--color-text-primary); }
.record-table tbody tr:hover td { background: var(--color-bg-spotlight); }
.record-card__body .status-tag { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: var(--font-size-xs); }
.record-card__body .status-tag.status-approved { color: #059669; background: #d1fae5; }
.record-card__body .status-tag.status-processing { color: #d97706; background: #fef3c7; }
.record-card__body .status-tag.status-rejected { color: #dc2626; background: #fee2e2; }
.reject-reason-cell { max-width: 200px; word-break: break-word; color: var(--color-text-secondary); font-size: var(--font-size-xs); }
.record-pagination { display: flex; align-items: center; justify-content: flex-end; flex-wrap: wrap; gap: var(--spacing-lg); padding: var(--spacing-md) var(--spacing-xl); border-top: 1px solid var(--color-border-lighter); background: white; font-size: var(--font-size-sm); color: var(--color-text-secondary); }
.record-pagination__total { margin-right: auto; }
.record-pagination__size { display: flex; align-items: center; gap: var(--spacing-xs); }
.record-pagination__select { padding: 4px 8px; border: 1px solid var(--color-border-base); border-radius: var(--radius-sm); font-size: var(--font-size-sm); background: white; }
.record-pagination__pages { display: flex; align-items: center; gap: var(--spacing-sm); }
.record-pagination__btn { padding: 6px 12px; border: 1px solid var(--color-border-base); border-radius: var(--radius-sm); background: white; font-size: var(--font-size-sm); cursor: pointer; color: var(--color-text-primary); }
.record-pagination__btn:hover:not(:disabled) { border-color: var(--color-primary); color: var(--color-primary); }
.record-pagination__btn:disabled { opacity: 0.5; cursor: not-allowed; }
.record-pagination__num { color: var(--color-text-tertiary); min-width: 80px; text-align: center; }

.empty-text { text-align: center; color: var(--color-text-secondary); padding: var(--spacing-xxl) 0; }

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
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
  width: 700px; /* 增加宽度以容纳更复杂的表单 */
  max-width: 95%;
  max-height: 90vh;
  overflow-y: auto;
}

.application-form {
  margin-top: var(--spacing-lg);
}

.form-row {
  display: flex;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.form-group {
  margin-bottom: var(--spacing-lg);
}

.form-group.half {
  flex: 1;
  margin-bottom: 0;
}

.form-group--full {
  flex: 1;
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-xs);
  font-weight: 500;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-base);
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  border-color: var(--color-primary);
  outline: none;
}

.form-group input[readonly],
.duration-readonly {
  background-color: var(--color-bg-layout);
  cursor: not-allowed;
}

.checkbox-group {
  display: flex;
  align-items: flex-end;
  padding-bottom: 10px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
  font-weight: normal;
}

.checkbox-label input {
  width: auto;
  margin: 0;
}

.hint-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-top: 4px;
}

.text-danger {
  color: #f5222d;
}

.form-file-wrap { display: flex; align-items: center; gap: var(--spacing-sm); flex-wrap: wrap; }
.form-file-wrap.mt-sm { margin-top: var(--spacing-sm); }
.form-file-wrap input[type="file"] { font-size: var(--font-size-sm); }
.file-hint { font-size: var(--font-size-xs); color: var(--color-text-tertiary); }
.file-selected { font-size: var(--font-size-sm); color: var(--color-primary); }
.ticket-consumption { color: var(--color-primary); font-weight: 500; margin-top: 6px; }
.hint-sub { font-weight: normal; color: var(--color-text-tertiary); margin-left: 0.25em; }

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
  margin-top: var(--spacing-xxl);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-border-lighter);
}

button {
  padding: 8px 20px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-base);
  cursor: pointer;
  background: white;
  font-size: var(--font-size-base);
  transition: all 0.2s;
}

button:hover {
  border-color: var(--color-primary-light);
  color: var(--color-primary);
}

.btn-primary {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.btn-primary:hover {
  background: var(--color-primary-light);
  border-color: var(--color-primary-light);
  color: white;
}
</style>
