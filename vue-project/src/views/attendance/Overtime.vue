<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">加班管理</h1>
          <p class="header-subtitle">加班登记与审批、记录查询</p>
        </div>
        <div class="header-actions">
          <button v-if="canApprove" class="btn btn-outline" @click="$router.push({ path: '/attendance/approvals', query: { type: 'overtime' } })">审批</button>
          <button class="btn btn-primary" @click="showRegisterModal = true">加班登记</button>
        </div>
      </div>
    </div>

    <!-- 加班记录 -->
    <div class="content mt-xl">
      <div class="card record-card">
        <div class="card-header record-card__header">
          <div>
            <h3>加班记录</h3>
            <p class="record-card__desc">{{ recordFilterLabel }}</p>
          </div>
          <div class="record-card__filters">
            <label class="filter-label">数据范围：</label>
            <select v-model="recordScope" class="filter-select filter-select--source">
              <option value="self">本人</option>
              <option v-if="overtimeListMeta.canViewAll" value="all">全员</option>
              <template v-if="overtimeListMeta.canViewAll && overtimeListMeta.lsysList?.length">
                <option v-for="ls in overtimeListMeta.lsysList" :key="ls" :value="'dept:' + ls">{{ ls }}</option>
              </template>
              <template v-else-if="overtimeListMeta.canViewLsys && overtimeListMeta.lsysLabel">
                <option :value="'dept:' + overtimeListMeta.lsysLabel">{{ overtimeListMeta.lsysLabel }}</option>
              </template>
            </select>
            <input type="month" v-model="recordMonth" class="filter-input">
            <select v-model="recordStatus" class="filter-select">
              <option value="processing">审批中/已驳回</option>
              <option value="approved">已通过</option>
              <option value="all">全部</option>
            </select>
            <input
              v-model.trim="recordKeyword"
              type="search"
              class="filter-input filter-input--search"
              placeholder="关键词"
              aria-label="关键词筛选"
            >
            <select v-model="recordSort" class="filter-select" aria-label="排序">
              <option value="date_desc">加班日期 ↓</option>
              <option value="date_asc">加班日期 ↑</option>
              <option value="applyTime_desc">登记时间 ↓</option>
              <option value="applyTime_asc">登记时间 ↑</option>
              <option value="applicant_asc">姓名 A→Z</option>
              <option value="applicant_desc">姓名 Z→A</option>
              <option value="hours_desc">时长(小时) ↓</option>
              <option value="hours_asc">时长(小时) ↑</option>
            </select>
          </div>
        </div>
        <div class="card-body record-card__body">
          <div class="table-wrap" v-if="recordProcessedList.length">
            <table class="record-table">
              <thead>
                <tr>
                  <th v-if="showApplicantColumn">姓名</th>
                  <th>类别</th>
                  <th>加班日期</th>
                  <th>开始时间</th>
                  <th>结束时间</th>
                  <th>时长(小时)</th>
                  <th>换休</th>
                  <th>加班内容</th>
                  <th>登记时间</th>
                  <th>审批状态</th>
                  <th>当前审批人</th>
                  <th>驳回原因</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in recordDisplayList" :key="r.id" :data-record-id="r.id">
                  <td v-if="showApplicantColumn">{{ r.applicant || '—' }}</td>
                  <td>{{ r.level }}</td>
                  <td>{{ r.date }}</td>
                  <td>{{ r.startTime }}</td>
                  <td>{{ r.endTime }}</td>
                  <td>{{ r.hours }}</td>
                  <td><span class="status-tag" :class="r.hx === '是' ? 'status-hx-yes' : 'status-hx-no'">{{ r.hx || '否' }}</span></td>
                  <td class="content-cell">{{ r.content || '—' }}</td>
                  <td>{{ r.applyTime }}</td>
                  <td><span class="status-tag" :class="r.statusClass">{{ r.status }}</span></td>
                  <td>{{ r.currentApprover || '-' }}</td>
                  <td class="reject-reason-cell">{{ r.status === '已驳回' && r.rejectReason ? r.rejectReason : '—' }}</td>
                  <td>
                    <template v-if="r.status === '已驳回' && isMyOvertimeRecord(r)">
                      <button type="button" class="btn btn-sm btn-primary" @click="editRejectedOvertime(r)" style="margin-right:6px">重新编辑</button>
                      <button type="button" class="btn btn-sm btn-danger" @click="deleteRejectedOvertime(r)">删除</button>
                    </template>
                    <span v-else>—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="record-pagination" v-if="recordProcessedList.length">
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
          <p class="empty-text" v-else-if="!myRecordList.length">暂无加班记录</p>
          <p class="empty-text" v-else>当前筛选条件下无匹配记录</p>
        </div>
      </div>
    </div>

    <!-- 加班登记弹窗 -->
    <div v-if="showRegisterModal" class="modal-overlay" @click.self="showRegisterModal = false">
      <div class="modal-content">
        <h2>{{ editingRejectedId ? '重新编辑加班' : '加班登记' }}</h2>
        <form @submit.prevent="submitRegister" class="application-form" autocomplete="on">
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

          <!-- 加班详情 -->
          <div class="form-row">
            <div class="form-group half">
              <label>登记方式</label>
              <input type="text" v-model="form.registerMethod" readonly>
            </div>
            <div class="form-group half">
              <label>是否要换休票</label>
              <select v-model="form.needExchangeTicket" name="needExchangeTicket" autocomplete="on" :disabled="form.level === '平时加班'">
                <option value="是">是</option>
                <option value="否">否</option>
              </select>
            </div>
          </div>

          <!-- 时间信息 -->
          <div class="form-group">
            <label>加班时间</label>
            <div class="date-range-inputs">
              <select v-model="form.date" name="overtimeDate" autocomplete="on">
                <option v-for="date in dateOptions" :key="date" :value="date">{{ date }}</option>
              </select>
              <div class="time-inputs">
                <TimePicker v-model="form.startTime" />
                <span>至</span>
                <TimePicker v-model="form.endTime" />
              </div>
            </div>
            <p v-if="form.needExchangeTicket === '是'" class="hint-text ticket-hint">
              获得换休票：{{ overtimeExchangeTickets }} 张（1天=8小时=2张，以0.25为单位，不足0.25张舍弃）
            </p>
            <p v-if="form.needExchangeTicket === '否'" class="hint-text ticket-hint">
              <template v-if="isSpecialHoliday && overtimePayBillableHours >= 8">
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

          <!-- 审批人 -->
          <div class="form-group">
            <label>审批人</label>
            <select v-model="form.approver" name="overtimeApprover" autocomplete="on" :disabled="loadingApprovers">
              <option value="">请选择审批人</option>
              <option v-for="person in approvers" :key="person" :value="person">{{ person }}</option>
            </select>
          </div>

          <!-- 底部操作 -->
          <div class="form-actions">
            <button type="button" @click="showRegisterModal = false">取消</button>
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
import { getOvertimeList, submitOvertimeRegister, getApprovers, getOvertimeWebconfig, checkCanApprove, deleteOvertimeRecord, resubmitOvertimeRecord, getHolidays } from '@/api/attendance'
import { keywordMatches, sortRecordRows } from '@/utils/recordTableHelpers'
import RecentTextInput from '@/components/RecentTextInput.vue'
import TimePicker from '@/components/TimePicker.vue'

const router = useRouter()
const route = useRoute()
const showRegisterModal = ref(false)
const editingRejectedId = ref(null)
const loadingList = ref(false)

// 本人的加班记录（从 API 获取）
const myRecordList = ref([])

// 加班记录分页（关键词 + 排序后分页）
const recordPage = ref(1)
const recordPageSize = ref(10)
const recordKeyword = ref('')
const recordSort = ref('date_desc')
const OVERTIME_SORT_FIELDS = [
  { field: 'date', type: 'date', get: (r) => r.date },
  { field: 'applyTime', type: 'date', get: (r) => r.applyTime },
  { field: 'applicant', type: 'string', get: (r) => r.applicant },
  { field: 'hours', type: 'number', get: (r) => r.hours }
]
const recordProcessedList = computed(() => {
  let list = myRecordList.value
  const kw = recordKeyword.value
  if (kw && kw.trim()) {
    list = list.filter((r) =>
      keywordMatches(kw, [
        r.applicant,
        r.level,
        r.date,
        r.startTime,
        r.endTime,
        r.content,
        r.applyTime,
        r.status,
        r.hx,
        r.currentApprover,
        r.rejectReason
      ])
    )
  }
  return sortRecordRows(list, recordSort.value, OVERTIME_SORT_FIELDS)
})
const recordTotal = computed(() => recordProcessedList.value.length)
const recordTotalPages = computed(() => Math.max(1, Math.ceil(recordTotal.value / recordPageSize.value)))
const recordDisplayList = computed(() => {
  const list = recordProcessedList.value
  const size = recordPageSize.value
  const start = (recordPage.value - 1) * size
  return list.slice(start, start + size)
})
watch(recordPageSize, () => { recordPage.value = 1 })
watch([recordKeyword, recordSort], () => { recordPage.value = 1 })

// 本人记录筛选：按月，审批状态默认已通过
const _d2 = new Date()
const recordMonth = ref(`${_d2.getFullYear()}-${String(_d2.getMonth() + 1).padStart(2, '0')}`)
const recordStatus = ref('processing')
const recordScope = ref('self')
const overtimeListMeta = ref({ canViewLsys: false, canViewAll: false, lsysLabel: '', lsysList: [] })
const showApplicantColumn = computed(() => recordScope.value !== 'self')

const recordFilterLabel = computed(() => {
  const r = (recordMonth.value || '').trim()
  const statusText = recordStatus.value === 'approved' ? '已通过' : recordStatus.value === 'processing' ? '审批中/已驳回' : '全部'
  let who = '本人'
  const src = recordScope.value
  if (src === 'all') {
    who = '全员'
  } else if (src.startsWith('dept:')) {
    who = src.slice(5)
  }
  if (r) {
    const [y, m] = r.split('-')
    return `展示 ${y}年${parseInt(m, 10)}月，${statusText} ${who}的加班记录`
  }
  return `展示 ${new Date().getFullYear()}年全年，${statusText} ${who}的加班记录`
})

function isMyOvertimeRecord(r) {
  const n = (form.name || '').trim()
  const a = (r?.applicant || '').trim()
  return !a || a === n
}

watch([recordMonth, recordStatus, recordScope], () => { fetchOvertimeList() })
watch(recordScope, () => { recordPage.value = 1 })

// 审批人列表（从API按规则获取）
const approvers = ref([])
const loadingApprovers = ref(false)

const fetchApprovers = async () => {
  if (!form.name) return
  loadingApprovers.value = true
  try {
    const res = await getApprovers({ name: form.name, level: 'first' })
    const selfName = (form.name || '').trim()
    approvers.value = (res.success && res.approvers)
      ? res.approvers.map(a => a.name).filter(n => (n || '').trim() !== selfName)
      : []
  } catch (err) {
    console.error('获取审批人失败:', err)
    approvers.value = []
  } finally {
    loadingApprovers.value = false
  }
}

// 生成最近30天日期选项
const dateOptions = ref([])

// 从 localStorage 获取当前用户
function initUserInfo() {
  const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
  return {
    department: userInfo.dept || userInfo.department || '技术部',
    name: userInfo.name || userInfo.userName || '当前用户',
    gender: userInfo.xbie || userInfo.gender || '男',
    jb: userInfo.jb || ''
  }
}

const userInfo = initUserInfo()
const canApprove = ref(false)
const form = reactive({
  department: userInfo.department,
  name: userInfo.name,
  gender: userInfo.gender,
  level: '平时加班',
  registerMethod: '书面',
  needExchangeTicket: '否',
  date: new Date().toISOString().split('T')[0],
  startTime: '08:00:00',
  endTime: '17:00:00',
  content: '',
  approver: ''
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

// 解析粘贴的时间文本为 HH:mm:ss（支持 8:00、08:00、17:30:00 等格式）
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

const zhibanfei = ref(15)

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

// 平时加班时锁定「是否要换休票」为否
watch(() => form.level, (level) => {
  if (level === '平时加班') form.needExchangeTicket = '否'
})

watch(() => form.date, (newDate) => {
  if (newDate) {
    const y = parseInt(newDate.slice(0, 4), 10)
    if (y && !Object.keys(holidayMap.value).some(d => d.startsWith(String(y)))) {
      loadHolidaysForYear(y)
    }
  }
})

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
    return SPECIAL_DAY_PAY.toFixed(2)
  }
  return (overtimePayBillableHours.value * zhibanfei.value).toFixed(2)
})

const resetForm = () => {
  form.level = '平时加班'
  form.registerMethod = '书面'
  form.needExchangeTicket = '否'
  form.date = new Date().toISOString().split('T')[0]
  form.startTime = '08:00:00'
  form.endTime = '17:00:00'
  form.content = ''
  form.approver = ''
}

const fetchOvertimeList = async () => {
  loadingList.value = true
  try {
    const r = (recordMonth.value || '').trim()
    const src = recordScope.value
    let scope = 'self'
    let targetLsys = null
    if (src === 'all') {
      scope = 'all'
    } else if (src.startsWith('dept:')) {
      const deptName = src.slice(5)
      if (overtimeListMeta.value.canViewAll) {
        scope = 'all'
        targetLsys = deptName
      } else {
        scope = 'lsys'
      }
    }
    const params = {
      name: form.name,
      year: new Date().getFullYear(),
      status: recordStatus.value,
      scope,
    }
    if (targetLsys) params.target_lsys = targetLsys
    if (r) {
      const [y, m] = r.split('-')
      if (y) params.year = parseInt(y, 10)
      if (m) params.month = parseInt(m, 10)
    }
    const res = await getOvertimeList(params)
    if (res.success && res.data) {
      myRecordList.value = res.data
      if (res.meta) {
        overtimeListMeta.value = {
          canViewLsys: !!res.meta.canViewLsys,
          canViewAll: !!res.meta.canViewAll,
          lsysLabel: (res.meta.lsysLabel || '').trim(),
          lsysList: res.meta.lsysList || []
        }
      }
      if ((src === 'all' || src.startsWith('dept:')) && !overtimeListMeta.value.canViewAll && !overtimeListMeta.value.canViewLsys) {
        recordScope.value = 'self'
      }
    }
  } catch (err) {
    console.error('获取加班记录失败:', err)
    const st = err?.response?.status
    if (st === 403 && recordScope.value !== 'self') {
      recordScope.value = 'self'
      await fetchOvertimeList()
      return
    }
    myRecordList.value = []
  } finally {
    loadingList.value = false
  }
}

function editRejectedOvertime(r) {
  if (!r?.id || r.status !== '已驳回') return
  editingRejectedId.value = r.id
  form.level = r.level || '平时加班'
  form.date = r.date || new Date().toISOString().split('T')[0]
  form.startTime = r.startTime || '08:00:00'
  form.endTime = r.endTime || '17:00:00'
  form.content = r.content || ''
  form.needExchangeTicket = r.hx || '否'
  form.approver = ''
  showRegisterModal.value = true
}

async function deleteRejectedOvertime(r) {
  if (!r?.id || r.status !== '已驳回') return
  if (!confirm('确认删除这条已驳回的加班记录？删除后不可恢复。')) return
  try {
    await deleteOvertimeRecord(r.id, { name: form.name })
    alert('已删除')
    fetchOvertimeList()
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
  getOvertimeWebconfig().then((res) => {
    if (res.success && res.zhibanfei != null) zhibanfei.value = Number(res.zhibanfei)
  }).catch(() => {})
  loadHolidaysForYear(new Date().getFullYear())
  const today = new Date()
  for (let i = 0; i < 30; i++) {
    const date = new Date(today)
    date.setDate(today.getDate() - i)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    dateOptions.value.push(`${year}-${month}-${day}`)
  }
  const q = route.query
  // 领导看板跳转：全员+已通过+年月+可选姓名
  if (q.from === 'leader') {
    if (q.year && q.month) {
      recordMonth.value = `${q.year}-${String(q.month).padStart(2, '0')}`
    } else if (q.year) {
      recordMonth.value = String(q.year)
    }
    recordStatus.value = 'approved'
    recordScope.value = 'all'
    if (q.focusName) recordKeyword.value = q.focusName
  }
  // 从首页点击流程：以业务时间(加班日期年月+状态)筛选，再按 focusId 定位到该条并滚动
  if (q.focusId) {
    if (q.month) recordMonth.value = String(q.month).slice(0, 7)
    if (q.status === 'processing' || q.status === 'approved' || q.status === 'all') recordStatus.value = q.status
  }
  await fetchOvertimeList()
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
    const d = String(q.prefillDate).slice(0, 10)
    if (d && !dateOptions.value.includes(d)) dateOptions.value.unshift(d)
    form.date = d
    form.startTime = (q.prefillStart || '08:00:00').length >= 8 ? q.prefillStart : (q.prefillStart || '08:00') + ':00'
    form.endTime = (q.prefillEnd || '17:00:00').length >= 8 ? q.prefillEnd : (q.prefillEnd || '17:00') + ':00'
    if (q.prefillContent) form.content = q.prefillContent
    showRegisterModal.value = true
    router.replace({ path: '/attendance/overtime' })
  }
})

watch(showRegisterModal, (visible) => {
  if (!visible) editingRejectedId.value = null
  if (visible && form.name) fetchApprovers()
})

const submitRegister = async () => {
  if (!form.content) {
    alert('请输入加班内容')
    return
  }
  if (!form.approver) {
    alert('请选择审批人')
    return
  }

  try {
    // 时间格式：HH:mm 或 HH:mm:ss，后端会补齐
    const st = (form.startTime || '08:00').length <= 5 ? form.startTime + ':00' : form.startTime
    const et = (form.endTime || '17:00').length <= 5 ? form.endTime + ':00' : form.endTime
    const payload = {
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
    }
    const isResubmit = !!editingRejectedId.value
    const res = isResubmit
      ? await resubmitOvertimeRecord(editingRejectedId.value, payload)
      : await submitOvertimeRegister(payload)
    if (res.success) {
      alert(isResubmit ? '已重新提交，等待审批' : '登记已提交')
      showRegisterModal.value = false
      editingRejectedId.value = null
      fetchOvertimeList()
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
.record-card__filters .filter-input { padding: 6px 10px; border: 1px solid var(--color-border-base); border-radius: var(--radius-sm); font-size: var(--font-size-sm); }
.record-card__filters .filter-input--search { min-width: 8rem; flex: 1; max-width: 14rem; }
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
.content-cell { max-width: 180px; word-break: break-word; font-size: var(--font-size-sm); color: var(--color-text-secondary); }
.status-hx-yes { color: #059669; background: #d1fae5; }
.status-hx-no { color: var(--color-text-tertiary); background: var(--color-bg-spotlight, #f5f5f5); }
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
  width: 700px;
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

.hint-text.ticket-hint { margin: var(--spacing-sm) 0 0; font-size: var(--font-size-sm); color: rgba(24, 144, 255, 1); }
.form-group input[readonly] {
  background-color: var(--color-bg-layout);
  cursor: not-allowed;
}

.date-range-inputs {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.time-inputs {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.time-inputs input {
  flex: 1;
}

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

.btn-outline {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
</style>
