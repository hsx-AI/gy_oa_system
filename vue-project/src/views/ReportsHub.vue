<template>
  <div class="reports-hub-page">
    <section class="reports-header">
      <div>
        <p class="eyebrow">报表汇聚</p>
        <h1>导出中心</h1>
        <p class="subtitle">{{ currentUserName || '-' }} · {{ userDept || '-' }} · {{ todayText }}</p>
      </div>
      <div class="header-tools">
        <button type="button" class="ghost-btn" @click="reloadMeta" :disabled="metaLoading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 2v6h-6" />
            <path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
            <path d="M3 22v-6h6" />
            <path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
          </svg>
          {{ metaLoading ? '刷新中' : '刷新权限' }}
        </button>
      </div>
    </section>

    <section class="quick-filters">
      <label>
        <span>报表分类</span>
        <select v-model="activeGroup">
          <option value="all">全部</option>
          <option value="attendance">考勤</option>
          <option value="incentive">绩效</option>
          <option value="duty">值班排班</option>
          <option value="admin">台账</option>
        </select>
      </label>
      <label class="search-field">
        <span>搜索</span>
        <input v-model.trim="keyword" type="search" placeholder="报表名称" />
      </label>
    </section>

    <section class="reports-grid">
      <article v-for="report in visibleReports" :key="report.id" class="report-card" :class="{ locked: !report.canUse }">
        <header class="report-card__head">
          <span class="report-icon" :class="`report-icon--${report.group}`">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <path d="M14 2v6h6" />
              <path d="M8 13h8" />
              <path d="M8 17h6" />
            </svg>
          </span>
          <div>
            <h2>{{ report.title }}</h2>
            <p>{{ report.source }}</p>
          </div>
        </header>

        <div class="report-fields">
          <template v-if="report.kind === 'month'">
            <label>
              <span>年份</span>
              <select v-model.number="filters.year">
                <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}</option>
              </select>
            </label>
            <label>
              <span>月份</span>
              <select v-model.number="filters.month">
                <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
              </select>
            </label>
          </template>

          <template v-else-if="report.kind === 'period'">
            <label>
              <span>方式</span>
              <select v-model="filters.periodMode">
                <option value="month">年月</option>
                <option value="range">日期段</option>
              </select>
            </label>
            <template v-if="filters.periodMode === 'month'">
              <label>
                <span>年份</span>
                <select v-model.number="filters.year">
                  <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}</option>
                </select>
              </label>
              <label>
                <span>月份</span>
                <select v-model="filters.periodMonth">
                  <option value="">全年</option>
                  <option v-for="m in 12" :key="m" :value="String(m)">{{ m }}月</option>
                </select>
              </label>
            </template>
            <template v-else>
              <label>
                <span>开始</span>
                <input v-model="filters.dateFrom" type="date" />
              </label>
              <label>
                <span>结束</span>
                <input v-model="filters.dateTo" type="date" />
              </label>
            </template>
          </template>

          <template v-else-if="report.kind === 'leaderMonth'">
            <label>
              <span>年份</span>
              <select v-model.number="filters.year">
                <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}</option>
              </select>
            </label>
            <label>
              <span>月份</span>
              <select v-model="filters.leaderMonth">
                <option value="">全年</option>
                <option v-for="m in 12" :key="m" :value="String(m)">{{ m }}月</option>
              </select>
            </label>
            <label v-if="canChooseLsys">
              <span>科室</span>
              <select v-model="filters.leaderLsys">
                <option value="">全部科室</option>
                <option v-for="d in lsysList" :key="d" :value="d">{{ d }}</option>
              </select>
            </label>
          </template>

          <template v-else-if="report.kind === 'attendanceWord'">
            <label>
              <span>年份</span>
              <select v-model.number="filters.year">
                <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}</option>
              </select>
            </label>
            <label>
              <span>月份</span>
              <select v-model.number="filters.month">
                <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
              </select>
            </label>
            <label v-if="canChooseLsys">
              <span>科室</span>
              <select v-model="filters.leaderLsys">
                <option value="">全部科室</option>
                <option v-for="d in lsysList" :key="d" :value="d">{{ d }}</option>
              </select>
            </label>
          </template>

          <template v-else-if="report.kind === 'dutyRange'">
            <label>
              <span>开始</span>
              <input v-model="filters.dutyStart" type="date" />
            </label>
            <label>
              <span>结束</span>
              <input v-model="filters.dutyEnd" type="date" />
            </label>
            <label>
              <span>科室</span>
              <select v-model="filters.dutyLsys">
                <option value="">全部科室</option>
                <option v-for="d in lsysList" :key="d" :value="d">{{ d }}</option>
              </select>
            </label>
          </template>

          <template v-else-if="report.kind === 'suggestionAttendance'">
            <label>
              <span>开始</span>
              <input v-model="filters.suggestionStart" type="date" />
            </label>
            <label>
              <span>结束</span>
              <input v-model="filters.suggestionEnd" type="date" />
            </label>
          </template>

          <template v-else-if="report.kind === 'workIntensity'">
            <label>
              <span>方式</span>
              <select v-model="filters.wiMode">
                <option value="month">年月</option>
                <option value="range">日期段</option>
              </select>
            </label>
            <template v-if="filters.wiMode === 'month'">
              <label>
                <span>年份</span>
                <select v-model.number="filters.wiYear">
                  <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}</option>
                </select>
              </label>
              <label>
                <span>月份</span>
                <select v-model="filters.wiMonth">
                  <option value="">全年</option>
                  <option v-for="m in 12" :key="m" :value="String(m)">{{ m }}月</option>
                </select>
              </label>
            </template>
            <template v-else>
              <label>
                <span>开始</span>
                <input v-model="filters.wiDateFrom" type="date" />
              </label>
              <label>
                <span>结束</span>
                <input v-model="filters.wiDateTo" type="date" />
              </label>
            </template>
            <label>
              <span>口径</span>
              <select v-model="filters.wiFormula">
                <option value="a">口径 A</option>
                <option value="b">口径 B</option>
                <option value="c">口径 C</option>
              </select>
            </label>
            <label v-if="statisticsPermission.level === 3">
              <span>科室</span>
              <select v-model="filters.wiLsys">
                <option value="">全员</option>
                <option v-for="d in lsysList" :key="d" :value="d">{{ d }}</option>
              </select>
            </label>
          </template>

          <template v-else-if="report.kind === 'shift'">
            <label>
              <span>格式</span>
              <select v-model="filters.shiftFormat" @change="handleShiftFormatChange">
                <option value="month">月排班表</option>
                <option value="week">周排班明细</option>
                <option value="holiday">假期值班表</option>
              </select>
            </label>
            <label>
              <span>年份</span>
              <select v-model.number="filters.shiftYear" @change="loadShiftHolidayOptions">
                <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}</option>
              </select>
            </label>
            <label v-if="filters.shiftFormat === 'month'">
              <span>月份</span>
              <select v-model.number="filters.shiftMonth">
                <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
              </select>
            </label>
            <label v-if="filters.shiftFormat === 'week'">
              <span>周日期</span>
              <input v-model="filters.shiftWeekDate" type="date" />
            </label>
            <label v-if="filters.shiftFormat === 'holiday'">
              <span>假期</span>
              <select v-model="filters.shiftHoliday">
                <option value="">请选择</option>
                <option v-for="h in shiftHolidayOptions" :key="h.name" :value="h.name">{{ h.name }}</option>
              </select>
            </label>
            <label>
              <span>科室</span>
              <select v-model="filters.shiftDepartment">
                <option v-if="filters.shiftFormat === 'holiday'" value="__ALL__">全部门汇总</option>
                <option value="">请选择科室</option>
                <option v-for="d in shiftDepartments" :key="d" :value="d">{{ d }}</option>
              </select>
            </label>
          </template>

          <template v-else-if="report.kind === 'numbering'">
            <label>
              <span>台账</span>
              <select v-model="filters.numberingTable">
                <option v-for="item in numberingTables" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </label>
          </template>

          <template v-else>
            <div class="no-filter">无筛选项</div>
          </template>
        </div>

        <footer class="report-card__foot">
          <span class="permission-pill" :class="{ ok: report.canUse }">{{ report.canUse ? report.scopeText : '无权限' }}</span>
          <button type="button" class="export-btn" :disabled="!report.canUse || activeExport === report.id" @click="runExport(report.id)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <path d="M7 10l5 5 5-5" />
              <path d="M12 15V3" />
            </svg>
            {{ activeExport === report.id ? '导出中' : '导出' }}
          </button>
        </footer>
      </article>
    </section>

    <div v-if="toast.text" class="toast" :class="toast.type">{{ toast.text }}</div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import * as XLSX from 'xlsx'
import {
  downloadAttendanceReport,
  exportAttendanceExceptions,
  exportEmployeesExcel,
  exportHolidayDutyAttendanceCheck,
  exportLeaveHandlerTable,
  exportSuggestionAttendanceReport,
  getDeptLsysList,
  getBusinessTripHoursExport,
  getFullAttendanceExport,
  getLeaveHoursExport,
  getOvertimeHoursExport,
  getOvertimePayExport,
  getLeaderWorkIntensity,
  getStatisticsPermission,
  getOvertimePayPermission,
  getUploadConfig,
} from '@/api/attendance'
import { exportBianhaoExcel } from '@/api/fileNumbering'
import { exportConfidentialityLedger } from '@/api/confidentialityLedger'
import { getDepartments, getShiftHolidayOptions } from '@/api/shift'
import { canAccessLeaderDashboard, isDirectorLevel, isMinisterLevel, isMinisterOrDeptLeader } from '@/utils/roleMatch'

const now = new Date()
const currentUserName = ref('')
const userDept = ref('')
const userJb = ref('')
const metaLoading = ref(false)
const activeExport = ref('')
const activeGroup = ref('all')
const keyword = ref('')
const lsysList = ref([])
const shiftDepartments = ref([])
const shiftHolidayOptions = ref([])
const uploadConfig = ref({ dakaman: '', admin1: '', admin2: '' })
const overtimePermission = ref({ canView: false, scope: 'self', lsys: '' })
const statisticsPermission = ref({ level: 1, lsys: '' })
const toast = reactive({ text: '', type: 'info' })

const filters = reactive({
  year: now.getFullYear(),
  month: now.getMonth() + 1,
  periodMode: 'month',
  periodMonth: String(now.getMonth() + 1),
  dateFrom: formatDate(new Date(now.getFullYear(), now.getMonth(), 1)),
  dateTo: formatDate(now),
  leaderMonth: String(now.getMonth() + 1),
  leaderLsys: '',
  dutyStart: defaultDutyRange().start,
  dutyEnd: defaultDutyRange().end,
  dutyLsys: '',
  suggestionStart: formatDate(new Date(now.getFullYear(), now.getMonth(), 1)),
  suggestionEnd: formatDate(now),
  shiftFormat: 'month',
  shiftYear: now.getFullYear(),
  shiftMonth: now.getMonth() + 1,
  shiftWeekDate: formatDate(nextSaturday(now)),
  shiftHoliday: '',
  shiftDepartment: '',
  numberingTable: 'tech',
  wiMode: 'month',
  wiYear: now.getFullYear(),
  wiMonth: String(now.getMonth() + 1),
  wiDateFrom: formatDate(new Date(now.getFullYear(), now.getMonth(), 1)),
  wiDateTo: formatDate(now),
  wiFormula: 'a',
  wiLsys: '',
})

const numberingTables = [
  { value: 'tech', label: '技术文件编号' },
  { value: 'jsgl', label: '技术管理文件编号' },
  { value: 'manage', label: '管理文件编号' },
  { value: 'gygch', label: '工艺过程策划表' },
  { value: 'scszh', label: '生产数字化编号' },
]

const yearOptions = computed(() => {
  const y = now.getFullYear()
  return [y + 1, y, y - 1, y - 2, y - 3, y - 4, y - 5]
})

const todayText = computed(() => formatDate(new Date()))
const isAdmin1 = computed(() => Boolean(uploadConfig.value.admin1 && currentUserName.value === uploadConfig.value.admin1))
const isAdmin2 = computed(() => Boolean(uploadConfig.value.admin2 && currentUserName.value === uploadConfig.value.admin2))
const isDakaman = computed(() => Boolean(uploadConfig.value.dakaman && currentUserName.value === uploadConfig.value.dakaman))
const canChooseLsys = computed(() => overtimePermission.value.scope !== 'self')
const canAttendanceExceptions = computed(() => {
  const minister = isMinisterLevel(userJb.value)
  const deptLeader = isMinisterOrDeptLeader(userJb.value) && !minister
  return isAdmin1.value || isDakaman.value || minister || deptLeader
})
const canEmployeeExport = computed(() => isAdmin1.value || isAdmin2.value || isMinisterOrDeptLeader(userJb.value))
const canNumberingExport = computed(() => {
  const jb = userJb.value || ''
  return (userDept.value === '综合技术室' && isDirectorLevel(jb)) || isMinisterLevel(jb)
})
const canLeaderExports = computed(() => Boolean(overtimePermission.value.canView))
const canHolidayDuty = computed(() => canAccessLeaderDashboard({
  name: currentUserName.value,
  jb: userJb.value,
  lsys: userDept.value,
  admin1: uploadConfig.value.admin1,
  admin2: uploadConfig.value.admin2,
}))
const canWorkIntensityExport = computed(() => canHolidayDuty.value)

const reports = computed(() => [
  {
    id: 'attendance-exceptions',
    title: '考勤异常明细',
    source: '原每个月通知处理考勤的那个邮件',
    group: 'attendance',
    kind: 'month',
    canUse: canAttendanceExceptions.value,
    scopeText: '原考勤异常权限',
  },
  {
    id: 'leave-handler',
    title: '异常处理表',
    source: '用于上传给公司考勤系统',
    group: 'attendance',
    kind: 'month',
    canUse: canAttendanceExceptions.value,
    scopeText: '原异常处理权限',
  },
  {
    id: 'suggestion-attendance',
    title: '全员考勤日表',
    source: '可以看到每人每日的打卡记录及缺勤是怎么处理的，谁审批的。',
    group: 'attendance',
    kind: 'suggestionAttendance',
    canUse: canAttendanceExceptions.value,
    scopeText: '原考勤异常权限',
  },
  {
    id: 'overtime-pay',
    title: '其他绩效激励工资报表',
    source: '其他绩效激励统计',
    group: 'incentive',
    kind: 'period',
    canUse: canLeaderExports.value,
    scopeText: scopeLabel.value,
  },
  {
    id: 'overtime-hours',
    title: '全部加班时长',
    source: '其他绩效激励统计',
    group: 'incentive',
    kind: 'period',
    canUse: canLeaderExports.value,
    scopeText: scopeLabel.value,
  },
  {
    id: 'leave-hours',
    title: '全部请假时长',
    source: '统计汇总 / 月度统计趋势',
    group: 'attendance',
    kind: 'period',
    canUse: canLeaderExports.value,
    scopeText: scopeLabel.value,
  },
  {
    id: 'business-trip-hours',
    title: '全部公出时长',
    source: '统计汇总 / 月度统计趋势',
    group: 'attendance',
    kind: 'period',
    canUse: canLeaderExports.value,
    scopeText: scopeLabel.value,
  },
  {
    id: 'full-attendance',
    title: '满勤名单',
    source: '用于统计满勤情况，注，公出处理时，只有走完了全部审批流程的公出才算满勤',
    group: 'attendance',
    kind: 'leaderMonth',
    canUse: canLeaderExports.value,
    scopeText: scopeLabel.value,
  },
  {
    id: 'attendance-report',
    title: '考勤表 Word',
    source: '人事员用于归档的word',
    group: 'attendance',
    kind: 'attendanceWord',
    canUse: canLeaderExports.value,
    scopeText: scopeLabel.value,
  },
  {
    id: 'holiday-duty',
    title: '假期值班出勤核查',
    source: '考勤纪律 / 假期值班核查',
    group: 'duty',
    kind: 'dutyRange',
    canUse: canHolidayDuty.value,
    scopeText: '管理驾驶舱权限',
  },
  {
    id: 'work-intensity',
    title: '工作强度统计',
    source: '管理驾驶舱中工作强度统计报表',
    group: 'attendance',
    kind: 'workIntensity',
    canUse: canWorkIntensityExport.value,
    hiddenWhenLocked: true,
    scopeText: statisticsPermission.value.level === 3 ? '全员/科室' : (statisticsPermission.value.lsys || '本科室'),
  },
  {
    id: 'shift-schedule',
    title: '排班表',
    source: '原每个假期都统计的假期排班表',
    group: 'duty',
    kind: 'shift',
    canUse: true,
    scopeText: '排班页权限',
  },
  {
    id: 'employees',
    title: '在职员工表',
    source: '员工在职管理',
    group: 'admin',
    kind: 'none',
    canUse: canEmployeeExport.value,
    scopeText: '员工管理权限',
  },
  {
    id: 'file-numbering',
    title: '文件编号台账',
    source: '文件编号的详情导出',
    group: 'admin',
    kind: 'numbering',
    canUse: canNumberingExport.value,
    scopeText: '经理/副经理/综合技术室主任权限',
  },
  {
    id: 'confidentiality-ledger',
    title: '保密审批台账',
    source: '智能制造工艺部论文保密审批台账',
    group: 'admin',
    kind: 'none',
    canUse: true,
    scopeText: '全员可导出',
  },
])

const scopeLabel = computed(() => {
  const scope = overtimePermission.value.scope
  if (scope === 'all') return '全部门'
  if (scope === 'lsys') return overtimePermission.value.lsys || '本科室'
  return '本人'
})

const visibleReports = computed(() => {
  const kw = keyword.value.toLowerCase()
  return reports.value.filter((r) => {
    if (!r.canUse) return false
    if (activeGroup.value !== 'all' && r.group !== activeGroup.value) return false
    if (!kw) return true
    return `${r.title} ${r.source}`.toLowerCase().includes(kw)
  })
})

function formatDate(d) {
  const x = new Date(d)
  const y = x.getFullYear()
  const m = String(x.getMonth() + 1).padStart(2, '0')
  const day = String(x.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function nextSaturday(d) {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  x.setDate(x.getDate() + ((6 - x.getDay() + 7) % 7))
  return x
}

function defaultDutyRange() {
  const y = now.getFullYear()
  const m = now.getMonth() + 1
  if (m >= 10) return { start: `${y}-10-01`, end: `${y}-10-07` }
  return { start: `${y}-05-01`, end: `${y}-05-05` }
}

function getCurrentUser() {
  try {
    const user = JSON.parse(localStorage.getItem('userInfo') || '{}')
    return {
      name: (user.name || user.userName || '').trim(),
      dept: (user.dept || user.lsys || '').trim(),
      jb: (user.jb || '').trim(),
    }
  } catch {
    return { name: '', dept: '', jb: '' }
  }
}

async function reloadMeta() {
  metaLoading.value = true
  const user = getCurrentUser()
  currentUserName.value = user.name
  userDept.value = user.dept
  userJb.value = user.jb
  try {
    const [cfg, perm, statPerm, deptRes, shiftRes] = await Promise.all([
      getUploadConfig().catch(() => ({})),
      user.name ? getOvertimePayPermission({ name: user.name }).catch(() => null) : Promise.resolve(null),
      user.name ? getStatisticsPermission({ name: user.name }).catch(() => null) : Promise.resolve(null),
      getDeptLsysList().catch(() => null),
      getDepartments().catch(() => null),
    ])
    uploadConfig.value = {
      dakaman: (cfg?.dakaman || '').trim(),
      admin1: (cfg?.admin1 || '').trim(),
      admin2: (cfg?.admin2 || '').trim(),
    }
    overtimePermission.value = {
      canView: !!perm?.canView,
      scope: perm?.scope || 'self',
      lsys: (perm?.lsys || '').trim(),
    }
    statisticsPermission.value = {
      level: Number(statPerm?.level || 1),
      lsys: (statPerm?.lsys || '').trim(),
    }
    lsysList.value = (deptRes?.list || []).filter((v) => v && !['其他部门员工', '其他部门成员'].includes(String(v).trim()))
    shiftDepartments.value = (shiftRes?.departments || shiftRes?.list || []).filter(Boolean)
    if (overtimePermission.value.scope === 'lsys' && overtimePermission.value.lsys && !filters.leaderLsys) {
      filters.leaderLsys = overtimePermission.value.lsys
    }
    if (statisticsPermission.value.level === 2) {
      filters.wiLsys = statisticsPermission.value.lsys
    }
    if (!filters.shiftDepartment && shiftDepartments.value.includes(user.dept)) {
      filters.shiftDepartment = user.dept
    }
    await loadShiftHolidayOptions()
  } finally {
    metaLoading.value = false
  }
}

function showToast(text, type = 'info') {
  toast.text = text
  toast.type = type
  window.clearTimeout(showToast.timer)
  showToast.timer = window.setTimeout(() => {
    toast.text = ''
  }, 2600)
}

function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob instanceof Blob ? blob : new Blob([blob]))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

async function errorText(e) {
  const data = e?.response?.data
  if (data instanceof Blob) {
    const text = await data.text().catch(() => '')
    try {
      return JSON.parse(text).detail || JSON.parse(text).message || text
    } catch {
      return text || '导出失败'
    }
  }
  return e?.response?.data?.detail || e?.message || '导出失败'
}

function buildMonthParams() {
  return {
    year: Number(filters.year),
    month: Number(filters.month),
    current_user: currentUserName.value,
  }
}

function buildPeriodParams({ requireMonth = false } = {}) {
  const params = {
    current_user: currentUserName.value,
    scope: overtimePermission.value.scope,
  }
  if (overtimePermission.value.scope === 'lsys' && overtimePermission.value.lsys) {
    params.scope_lsys = overtimePermission.value.lsys
  }
  if (filters.periodMode === 'range') {
    if (!filters.dateFrom || !filters.dateTo) throw new Error('请选择开始日期和结束日期')
    params.date_from = filters.dateFrom
    params.date_to = filters.dateTo
  } else {
    if (requireMonth && !filters.periodMonth) throw new Error('请选择月份，或切换为日期段')
    params.year = Number(filters.year)
    if (filters.periodMonth) params.month = Number(filters.periodMonth)
  }
  return params
}

function periodLabel() {
  if (filters.periodMode === 'range') return `${filters.dateFrom}_${filters.dateTo}`
  if (filters.periodMonth) return `${filters.year}年${filters.periodMonth}月`
  return `${filters.year}年全年`
}

function sheetFromPayList(list) {
  const rows = (list || []).map((item) => [item.name || '', item.pay ?? 0])
  return XLSX.utils.aoa_to_sheet([['姓名', '本月其他绩效激励（元）'], ...rows])
}

function sheetFromOvertimeHoursList(list) {
  const rows = (list || []).map((item) => [
    item.name || '',
    item.totalHours ?? 0,
    item.payHours ?? 0,
    item.hxHours ?? 0,
    item.times ?? 0,
  ])
  return XLSX.utils.aoa_to_sheet([['姓名', '加班总时长(小时)', '其他绩效激励时长(小时)', '换休票时长(小时)', '加班次数'], ...rows])
}

function sheetFromLeaveHoursList(list) {
  const rows = (list || []).map((item) => [
    item.name || '',
    item.totalDays ?? 0,
    item.totalHours ?? 0,
    item.times ?? 0,
  ])
  return XLSX.utils.aoa_to_sheet([['姓名', '请假天数(天)', '请假时长(小时)', '请假次数'], ...rows])
}

function formatLeaveDuration(item) {
  const days = Number(item?.days || 0)
  const hours = Number(item?.hours || 0)
  if (days > 0) return `${days} 天`
  if (hours > 0) return `${hours} 小时`
  return '—'
}

function sheetFromLeaveRecordsList(list) {
  const header = [
    '序号',
    '姓名',
    '科室',
    '请假类型',
    '开始时间',
    '结束时间',
    '时长',
    '事由',
    '登记时间',
    '审批状态',
    '当前审批人',
    '驳回原因',
    '计入统计天数',
    '计入统计小时',
  ]
  const rows = (list || []).map((item, i) => [
    i + 1,
    item.name || '',
    item.department || '',
    item.type || '',
    item.startTime || '',
    item.endTime || '',
    formatLeaveDuration(item),
    item.reason || '',
    item.applyTime || '',
    item.status || '',
    item.currentApprover || '',
    item.rejectReason || '',
    item.allocatedDays ?? 0,
    item.allocatedHours ?? 0,
  ])
  const sheet = XLSX.utils.aoa_to_sheet([header, ...rows])
  sheet['!cols'] = [
    { wch: 6 }, { wch: 12 }, { wch: 16 }, { wch: 12 },
    { wch: 20 }, { wch: 20 }, { wch: 12 }, { wch: 36 },
    { wch: 20 }, { wch: 10 }, { wch: 12 }, { wch: 16 },
    { wch: 12 }, { wch: 12 },
  ]
  return sheet
}

function sheetFromBusinessTripHoursList(list) {
  const rows = (list || []).map((item) => [
    item.name || '',
    item.totalDays ?? 0,
    item.totalHours ?? 0,
    item.times ?? 0,
  ])
  return XLSX.utils.aoa_to_sheet([['姓名', '公出天数(天)', '公出时长(小时)', '公出次数'], ...rows])
}

function appendDeptSheets(wb, byDept, sheetBuilder) {
  for (const dept of byDept || []) {
    const sheetName = (dept.lsys || '科室').slice(0, 31)
    XLSX.utils.book_append_sheet(wb, sheetBuilder(dept.list || []), sheetName)
  }
}

function appendAoASheet(wb, name, rows, widths = []) {
  const sheet = XLSX.utils.aoa_to_sheet(rows)
  if (widths.length) sheet['!cols'] = widths.map((wch) => ({ wch }))
  XLSX.utils.book_append_sheet(wb, sheet, name)
}

function roundForExport(value, digits = 2) {
  const n = Number(value || 0)
  return Number(n.toFixed(digits))
}

function percentForExport(value) {
  return `${roundForExport(Number(value || 0) * 100, 1)}%`
}

function wiActualHours(row, wi) {
  if (row?.actualHours != null && row.actualHours !== '') return roundForExport(row.actualHours)
  const expected = Number(wi?.expectedHoursPerPerson || 0)
  const count = Number(row?.personCount || 0)
  const tripDays = Number(row?.tripDays || 0)
  const holidayTripDays = Number(row?.tripHolidayDays || 0)
  return roundForExport(expected * count - tripDays * 8 + holidayTripDays * 8)
}

function wiScopeLsys() {
  if (Number(statisticsPermission.value.level || 1) === 3) return (filters.wiLsys || '').trim()
  return (statisticsPermission.value.lsys || '').trim()
}

function wiRangeLabel(wi) {
  if (wi?.rangeMode && wi.dateFrom && wi.dateTo) {
    return wi.effectiveDateTo && wi.effectiveDateTo !== wi.dateTo
      ? `${wi.dateFrom} ~ ${wi.dateTo}（统计截止 ${wi.effectiveDateTo}）`
      : `${wi.dateFrom} ~ ${wi.dateTo}`
  }
  if (filters.wiMode === 'range') return `${filters.wiDateFrom} ~ ${filters.wiDateTo}`
  return `${filters.wiYear}年${filters.wiMonth ? filters.wiMonth + '月' : '全年'}`
}

function wiExportFileName(wi) {
  const scope = (wiScopeLsys() || '全员').replace(/[\\/:*?"<>|]+/g, '_')
  const range = wiRangeLabel(wi).replace(/[\\/:*?"<>|()\s]+/g, '_').replace(/^_+|_+$/g, '')
  const formulaLabel = { a: '口径A', b: '口径B', c: '口径C' }
  return `工作强度统计_${scope}_${range || filters.wiYear}_${formulaLabel[filters.wiFormula] || '口径A'}.xlsx`
}

async function exportWorkIntensity() {
  if (!canWorkIntensityExport.value) throw new Error('无工作强度统计导出权限')
  const params = {
    year: Number(filters.wiYear),
    intensity_formula: filters.wiFormula,
    current_user: currentUserName.value,
  }
  const lsys = wiScopeLsys()
  if (lsys) params.lsys = lsys
  if (filters.wiMode === 'range') {
    if (!filters.wiDateFrom || !filters.wiDateTo) throw new Error('请选择开始日期和结束日期')
    params.date_from = filters.wiDateFrom
    params.date_to = filters.wiDateTo
  } else if (filters.wiMonth) {
    params.month = Number(filters.wiMonth)
  }

  const wi = await getLeaderWorkIntensity(params)
  if (!wi?.success || !wi.totalPeople) throw new Error('暂无可导出的工作强度数据')

  const deductLeave = filters.wiFormula === 'b' || filters.wiFormula === 'c'
  const deptRows = (wi.byDept || []).map((row, idx) => {
    const cells = [
      idx + 1,
      row.lsys || '',
      row.personCount ?? 0,
      roundForExport(row.overtimeHours),
    ]
    if (deductLeave) cells.push(roundForExport(row.leaveHours ?? 0))
    cells.push(
      roundForExport(row.tripDays),
      roundForExport(row.tripHolidayDays),
      wiActualHours(row, wi),
      percentForExport(row.intensity),
    )
    return cells
  })
  const personRows = [...(wi.byPerson || [])]
    .sort((a, b) => Number(b.intensity || 0) - Number(a.intensity || 0))
    .map((row, idx) => {
      const cells = [
        idx + 1,
        row.name || '',
        row.lsys || '',
        row.jb || '',
        roundForExport(row.overtimeHours),
      ]
      if (deductLeave) cells.push(roundForExport(row.leaveHours ?? 0))
      cells.push(
        roundForExport(row.tripDays),
        roundForExport(row.tripHolidayDays),
        roundForExport(row.actualHours),
        percentForExport(row.intensity),
      )
      return cells
    })

  const allPersons = wi.byPerson || []
  const totalOvertimeHours = wi.totalOvertimeHours != null
    ? Number(wi.totalOvertimeHours)
    : allPersons.reduce((sum, p) => sum + Number(p.overtimeHours || 0), 0)
  const totalActualHours = wi.totalActualHours != null
    ? Number(wi.totalActualHours)
    : allPersons.reduce((sum, p) => sum + Number(p.actualHours || 0), 0)
  const totalLeaveH = deductLeave
    ? (wi.totalLeaveHours != null
        ? Number(wi.totalLeaveHours)
        : allPersons.reduce((sum, p) => sum + Number(p.leaveHours || 0), 0))
    : 0
  const overallPct = totalActualHours > 0
    ? (deductLeave ? (totalOvertimeHours - totalLeaveH) / totalActualHours : totalOvertimeHours / totalActualHours)
    : 0

  const deptActualCol = deductLeave ? 7 : 6
  const sumDeptCount = deptRows.reduce((s, row) => s + Number(row[2] || 0), 0)
  const sumDeptOt = deptRows.reduce((s, row) => s + Number(row[3] || 0), 0)
  const sumDeptActual = deptRows.reduce((s, row) => s + Number(row[deptActualCol] || 0), 0)
  const sumDeptLeave = deductLeave ? deptRows.reduce((s, row) => s + Number(row[4] || 0), 0) : 0

  const overviewRows = [
    ['统计项', '数值'],
    ['统计范围', wiRangeLabel(wi)],
    ['导出范围', lsys || '全员'],
    ['口径', ({ a: '口径 A', b: '口径 B', c: '口径 C' }[filters.wiFormula] || '口径 A')],
    ['加班时长口径', wi.overtimeCalcNote || '工作日 7:30 前 + 17:30 后（不足 1h 也计）；休息日同智能建议'],
    ['应出勤工作日（天）', wi.workdays ?? 0],
    ['应出勤时长/人（h）', wi.expectedHoursPerPerson ?? 0],
    ['统计人数（人）', wi.totalPeople ?? 0],
    ['全员加班（h）', roundForExport(totalOvertimeHours)],
  ]
  if (deductLeave) {
    overviewRows.push(['全员请假（h）', roundForExport(totalLeaveH)])
    overviewRows.push(['全员（加班−请假）（h）', roundForExport(totalOvertimeHours - totalLeaveH)])
  }
  overviewRows.push(
    ['全员实际在岗（h）', roundForExport(totalActualHours)],
    ['全员工作强度', percentForExport(overallPct)],
    ['各科室加班合计（h）', roundForExport(sumDeptOt)],
    ['各科室在岗合计（h）', roundForExport(sumDeptActual)],
  )

  const wb = XLSX.utils.book_new()
  appendAoASheet(wb, '统计概览', overviewRows, [24, 48])
  const deptHead = ['序号', '科室', '人数', '加班（h）']
  if (deductLeave) deptHead.push('请假（h）')
  deptHead.push('公出（天，不含市内）', '公出期间节假日（天，不含市内）', '实际在岗（h）', '工作强度')
  const deptFoot = ['', '各科室合计', sumDeptCount, roundForExport(sumDeptOt)]
  if (deductLeave) deptFoot.push(roundForExport(sumDeptLeave))
  deptFoot.push('', '', roundForExport(sumDeptActual), '')
  appendAoASheet(wb, '按科室', [deptHead, ...deptRows, deptFoot], [8, 24, 10, 12, ...(deductLeave ? [12] : []), 12, 20, 14, 12])
  const personHead = ['序号', '姓名', '科室', '职务', '加班（h）']
  if (deductLeave) personHead.push('请假（h）')
  personHead.push('公出（天，不含市内）', '公出期间节假日（天，不含市内）', '实际在岗（h）', '工作强度')
  appendAoASheet(wb, '按个人', [personHead, ...personRows], [8, 14, 24, 16, 12, ...(deductLeave ? [12] : []), 12, 20, 14, 12])
  XLSX.writeFile(wb, wiExportFileName(wi))
}

async function exportOvertimePay() {
  const res = await getOvertimePayExport(buildPeriodParams({ requireMonth: true }))
  if (!res?.success || res.all === undefined) throw new Error('获取报表数据失败')
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, sheetFromPayList(res.all || []), overtimePermission.value.scope === 'self' ? '本人' : '全员')
  appendDeptSheets(wb, res.byDept, sheetFromPayList)
  XLSX.writeFile(wb, `其他绩效激励工资报表_${periodLabel()}.xlsx`)
}

async function exportOvertimeHours() {
  const res = await getOvertimeHoursExport(buildPeriodParams())
  if (!res?.success || res.all === undefined) throw new Error('获取加班时长数据失败')
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, sheetFromOvertimeHoursList(res.all || []), overtimePermission.value.scope === 'self' ? '本人' : '全员')
  appendDeptSheets(wb, res.byDept, sheetFromOvertimeHoursList)
  XLSX.writeFile(wb, `全部加班时长_${periodLabel()}.xlsx`)
}

async function exportLeaveHours() {
  const res = await getLeaveHoursExport(buildPeriodParams())
  if (!res?.success || res.all === undefined) throw new Error('获取请假时长数据失败')
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, sheetFromLeaveHoursList(res.all || []), overtimePermission.value.scope === 'self' ? '本人' : '全员')
  appendDeptSheets(wb, res.byDept, sheetFromLeaveHoursList)
  XLSX.utils.book_append_sheet(wb, sheetFromLeaveRecordsList(res.records || []), '请假明细')
  XLSX.writeFile(wb, `全部请假时长_${periodLabel()}.xlsx`)
}

async function exportBusinessTripHours() {
  const res = await getBusinessTripHoursExport(buildPeriodParams())
  if (!res?.success || res.all === undefined) throw new Error('获取公出时长数据失败')
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, sheetFromBusinessTripHoursList(res.all || []), overtimePermission.value.scope === 'self' ? '本人' : '全员')
  appendDeptSheets(wb, res.byDept, sheetFromBusinessTripHoursList)
  XLSX.writeFile(wb, `全部公出时长_${periodLabel()}.xlsx`)
}

async function exportFullAttendance() {
  const params = { year: Number(filters.year) }
  if (filters.leaderMonth) params.month = Number(filters.leaderMonth)
  if (overtimePermission.value.scope !== 'self' && filters.leaderLsys) params.lsys = filters.leaderLsys
  const res = await getFullAttendanceExport(params)
  if (!res?.success || !res.byDept) throw new Error('获取满勤名单失败')
  const wb = XLSX.utils.book_new()
  const allDetails = []
  for (const d of res.byDept || []) {
    for (const p of d.fullDetails || []) {
      if ((p.name || '').trim()) allDetails.push(p)
    }
  }
  allDetails.sort((a, b) => (a.name || '').localeCompare(b.name || '', 'zh-Hans-CN'))
  const seen = new Set()
  const unique = allDetails.filter((p) => {
    if (seen.has(p.name)) return false
    seen.add(p.name)
    return true
  })
  const buildSheet = (list) => XLSX.utils.aoa_to_sheet([
    ['序号', '姓名', '出勤天数', '公出天数'],
    ...(list || []).map((p, i) => [i + 1, p.name, p.attendDays ?? '', p.businessDays ?? '']),
  ])
  XLSX.utils.book_append_sheet(wb, buildSheet(unique), '全员满勤名单')
  for (const dept of res.byDept || []) {
    XLSX.utils.book_append_sheet(wb, buildSheet(dept.fullDetails || []), (dept.lsys || '科室').slice(0, 31))
  }
  const monthLabel = filters.leaderMonth ? `${filters.leaderMonth}月` : '全年'
  XLSX.writeFile(wb, `满勤名单_${filters.year}年${monthLabel}.xlsx`)
}

async function exportAttendanceReportWord() {
  const params = { year: Number(filters.year), month: Number(filters.month) }
  if (overtimePermission.value.scope !== 'self' && filters.leaderLsys) params.lsys = filters.leaderLsys
  const blob = await downloadAttendanceReport(params)
  const isAllDepts = overtimePermission.value.scope !== 'self' && !filters.leaderLsys
  const lsysLabel = filters.leaderLsys ? `_${filters.leaderLsys}` : ''
  saveBlob(
    blob,
    isAllDepts
      ? `考勤表_${filters.year}年${filters.month}月_各科室.zip`
      : `考勤表_${filters.year}年${filters.month}月${lsysLabel}.docx`,
  )
}

async function exportShiftSchedule() {
  if ((filters.shiftFormat === 'month' || filters.shiftFormat === 'week') && !filters.shiftDepartment) {
    throw new Error(`${filters.shiftFormat === 'week' ? '周排班表' : '月排班表'}请先选择科室`)
  }
  if (filters.shiftFormat === 'holiday' && !filters.shiftHoliday) throw new Error('请选择要导出的假期')
  const params = new URLSearchParams({
    department: filters.shiftFormat === 'holiday' && filters.shiftDepartment === '__ALL__' ? '__ALL__' : filters.shiftDepartment,
    year: String(filters.shiftYear),
    format: filters.shiftFormat,
  })
  if (filters.shiftFormat === 'month') params.set('month', String(filters.shiftMonth))
  if (filters.shiftFormat === 'week') params.set('week_date', filters.shiftWeekDate)
  if (filters.shiftFormat === 'holiday') params.set('holiday', filters.shiftHoliday)
  const resp = await fetch(`/api/shift/export-excel?${params.toString()}`, { credentials: 'include' })
  if (!resp.ok) {
    const text = await resp.text().catch(() => '')
    try {
      throw new Error(JSON.parse(text).detail || '导出失败')
    } catch {
      throw new Error(text || '导出失败')
    }
  }
  const blob = await resp.blob()
  const scopeName = filters.shiftDepartment === '__ALL__' ? '全部门汇总' : filters.shiftDepartment
  const suffix = filters.shiftFormat === 'holiday'
    ? `${filters.shiftHoliday}期间值班值宿人员安排表`
    : (filters.shiftFormat === 'week' ? `${filters.shiftWeekDate}_周排班明细` : `${filters.shiftMonth}月_排班表`)
  saveBlob(blob, `${scopeName}_${filters.shiftYear}年${suffix}.xlsx`)
}

async function loadShiftHolidayOptions() {
  if (filters.shiftFormat !== 'holiday') return
  const res = await getShiftHolidayOptions({ year: filters.shiftYear }).catch(() => null)
  shiftHolidayOptions.value = res?.options || []
  if (!shiftHolidayOptions.value.some((h) => h.name === filters.shiftHoliday)) {
    filters.shiftHoliday = shiftHolidayOptions.value[0]?.name || ''
  }
}

async function handleShiftFormatChange() {
  if (filters.shiftFormat === 'holiday') {
    if (!filters.shiftDepartment) filters.shiftDepartment = '__ALL__'
    await loadShiftHolidayOptions()
  } else if (filters.shiftDepartment === '__ALL__') {
    filters.shiftDepartment = userDept.value || ''
  }
}

async function runExport(id) {
  const report = reports.value.find((r) => r.id === id)
  if (!report?.canUse) return
  activeExport.value = id
  try {
    if (id === 'attendance-exceptions') {
      const p = buildMonthParams()
      saveBlob(await exportAttendanceExceptions(p), `考勤异常_${p.year}${String(p.month).padStart(2, '0')}.xlsx`)
    } else if (id === 'leave-handler') {
      const p = buildMonthParams()
      saveBlob(await exportLeaveHandlerTable(p), `异常处理表_${p.year}${String(p.month).padStart(2, '0')}.xlsx`)
    } else if (id === 'suggestion-attendance') {
      if (!filters.suggestionStart || !filters.suggestionEnd) throw new Error('请选择开始日期和结束日期')
      if (filters.suggestionStart > filters.suggestionEnd) throw new Error('开始日期不能晚于结束日期')
      const blob = await exportSuggestionAttendanceReport({
        start_date: filters.suggestionStart,
        end_date: filters.suggestionEnd,
        current_user: currentUserName.value,
      })
      saveBlob(blob, `打卡与智能建议处理_${filters.suggestionStart}_${filters.suggestionEnd}.xlsx`)
    } else if (id === 'overtime-pay') {
      await exportOvertimePay()
    } else if (id === 'overtime-hours') {
      await exportOvertimeHours()
    } else if (id === 'leave-hours') {
      await exportLeaveHours()
    } else if (id === 'business-trip-hours') {
      await exportBusinessTripHours()
    } else if (id === 'full-attendance') {
      await exportFullAttendance()
    } else if (id === 'attendance-report') {
      await exportAttendanceReportWord()
    } else if (id === 'holiday-duty') {
      const params = { start_date: filters.dutyStart, end_date: filters.dutyEnd }
      if (filters.dutyLsys) params.lsys = filters.dutyLsys
      const blob = await exportHolidayDutyAttendanceCheck(params)
      saveBlob(blob, `${filters.dutyLsys || '全部科室'}_${filters.dutyStart}_${filters.dutyEnd}_假期值班出勤核查.xlsx`)
    } else if (id === 'work-intensity') {
      await exportWorkIntensity()
    } else if (id === 'shift-schedule') {
      await exportShiftSchedule()
    } else if (id === 'employees') {
      saveBlob(await exportEmployeesExcel({ current_user: currentUserName.value }), `在职员工表_${todayText.value}.xlsx`)
    } else if (id === 'file-numbering') {
      const blob = await exportBianhaoExcel({ table: filters.numberingTable, name: currentUserName.value })
      saveBlob(blob, `文件编号_${filters.numberingTable}.xlsx`)
    } else if (id === 'confidentiality-ledger') {
      const blob = await exportConfidentialityLedger()
      saveBlob(blob, '智能制造工艺部论文保密审批台账.xlsx')
    }
    showToast('导出已开始', 'success')
  } catch (e) {
    showToast(await errorText(e), 'error')
  } finally {
    activeExport.value = ''
  }
}

onMounted(reloadMeta)
</script>

<style scoped>
.reports-hub-page {
  min-height: 100vh;
  padding: 0 18px 28px 0;
  color: #1f2937;
}

.reports-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
  padding: 22px 24px;
  border-radius: 8px;
  background: linear-gradient(135deg, #f8fafc 0%, #eef6f1 48%, #f5f1ea 100%);
  border: 1px solid #e5e7eb;
  box-shadow: 0 12px 28px rgba(31, 41, 55, 0.08);
}

.eyebrow {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  color: #047857;
}

.reports-header h1 {
  margin: 0;
  font-size: 30px;
  line-height: 1.18;
  color: #111827;
}

.subtitle {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 14px;
}

.header-tools {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ghost-btn,
.export-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 36px;
  border-radius: 7px;
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #334155;
  font-weight: 700;
  cursor: pointer;
}

.ghost-btn {
  padding: 0 13px;
}

.ghost-btn svg,
.export-btn svg {
  width: 16px;
  height: 16px;
}

.ghost-btn:disabled,
.export-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.quick-filters {
  display: grid;
  grid-template-columns: minmax(160px, 220px) minmax(220px, 1fr);
  gap: 12px;
  margin-bottom: 14px;
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.quick-filters label,
.report-fields label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  font-size: 12px;
  font-weight: 800;
  color: #64748b;
}

.quick-filters input,
.quick-filters select,
.report-fields input,
.report-fields select {
  height: 36px;
  border: 1px solid #cbd5e1;
  border-radius: 7px;
  padding: 0 10px;
  background: #fff;
  color: #172033;
  font-size: 14px;
  outline: none;
}

.quick-filters input:focus,
.quick-filters select:focus,
.report-fields input:focus,
.report-fields select:focus {
  border-color: #0f766e;
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.12);
}

.reports-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(330px, 1fr));
  gap: 14px;
}

.report-card {
  display: flex;
  flex-direction: column;
  min-height: 260px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
  overflow: hidden;
}

.report-card.locked {
  background: #f8fafc;
}

.report-card__head {
  display: flex;
  gap: 12px;
  padding: 16px 16px 10px;
}

.report-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 38px;
  width: 38px;
  height: 38px;
  border-radius: 8px;
  background: #ecfdf5;
  color: #047857;
}

.report-icon svg {
  width: 21px;
  height: 21px;
}

.report-icon--attendance {
  background: #eff6ff;
  color: #2563eb;
}

.report-icon--incentive {
  background: #fff7ed;
  color: #c2410c;
}

.report-icon--duty {
  background: #f0fdfa;
  color: #0f766e;
}

.report-icon--admin {
  background: #f5f3ff;
  color: #6d28d9;
}

.report-card__head h2 {
  margin: 0;
  font-size: 18px;
  line-height: 1.25;
  color: #111827;
}

.report-card__head p {
  margin: 5px 0 0;
  font-size: 13px;
  color: #64748b;
}

.report-fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(128px, 1fr));
  gap: 10px;
  padding: 8px 16px 16px;
  flex: 1;
  align-content: start;
}

.no-filter {
  display: flex;
  align-items: center;
  min-height: 36px;
  color: #64748b;
  font-size: 13px;
}

.report-card__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  background: #f8fafc;
  border-top: 1px solid #e5e7eb;
}

.permission-pill {
  display: inline-flex;
  align-items: center;
  max-width: 180px;
  min-height: 26px;
  padding: 0 9px;
  border-radius: 999px;
  background: #fee2e2;
  color: #991b1b;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.permission-pill.ok {
  background: #dcfce7;
  color: #166534;
}

.export-btn {
  min-width: 90px;
  padding: 0 14px;
  border-color: #0f766e;
  background: #0f766e;
  color: #fff;
}

.export-btn:not(:disabled):hover {
  background: #115e59;
}

.toast {
  position: fixed;
  right: 22px;
  bottom: 22px;
  z-index: 50;
  max-width: min(420px, calc(100vw - 44px));
  padding: 11px 14px;
  border-radius: 8px;
  background: #111827;
  color: #fff;
  font-size: 14px;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.25);
}

.toast.success {
  background: #047857;
}

.toast.error {
  background: #b91c1c;
}

@media (max-width: 720px) {
  .reports-hub-page {
    padding: 0 0 24px;
  }

  .reports-header {
    align-items: flex-start;
    flex-direction: column;
    padding: 18px;
  }

  .quick-filters,
  .reports-grid {
    grid-template-columns: 1fr;
  }

  .report-card {
    min-height: auto;
  }
}
</style>
