<template>
  <div class="personnel-visual-page">
    <section class="visual-header">
      <div>
        <p class="eyebrow">人员出勤可视化</p>
        <h1>科室办公室实时状态</h1>
        <p class="subtitle">{{ scene.department || '本科室' }} · {{ selectedDate }} · {{ summary.total }} 人</p>
      </div>
      <div class="header-actions">
        <label class="field">
          <span>日期</span>
          <input v-model="selectedDate" type="date" @change="loadScene" />
        </label>
        <label v-if="availableDepartments.length > 1" class="field">
          <span>科室</span>
          <select v-model="selectedDept" @change="loadScene">
            <option v-for="dept in availableDepartments" :key="dept" :value="dept">{{ dept }}</option>
          </select>
        </label>
        <label v-if="showStatusFilter" class="field">
          <span>状态</span>
          <select v-model="selectedStatus">
            <option v-for="opt in statusFilterOptions" :key="opt.value || 'all'" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </label>
        <button class="refresh-btn" type="button" :disabled="loading" @click="loadScene" title="刷新">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 2v6h-6" />
            <path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
            <path d="M3 22v-6h6" />
            <path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
          </svg>
          {{ loading ? '刷新中' : '刷新' }}
        </button>
        <button
          v-if="canExtend"
          class="extend-btn"
          type="button"
          title="为本科室已通过且未返回登记的公出延长返回时间"
          @click="openExtend()"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 7v5l3 2" />
          </svg>
          公出延长
        </button>
      </div>
    </section>

    <section class="summary-strip" aria-label="出勤汇总">
      <div class="summary-item summary-present">
        <span class="summary-dot"></span>
        <div>
          <strong>{{ summary.present }}</strong>
          <span>在岗办公</span>
        </div>
      </div>
      <div class="summary-item summary-trip">
        <span class="summary-dot"></span>
        <div>
          <strong>{{ summary.businessTrip }}</strong>
          <span>公出中</span>
        </div>
      </div>
      <div class="summary-item summary-leave">
        <span class="summary-dot"></span>
        <div>
          <strong>{{ summary.leave }}</strong>
          <span>请假</span>
        </div>
      </div>
      <div class="summary-item summary-empty">
        <span class="summary-dot"></span>
        <div>
          <strong>{{ summary.noRecord }}</strong>
          <span>暂无打卡<span v-if="summary.leavePending"> / 审核中 {{ summary.leavePending }}</span></span>
        </div>
      </div>
      <div class="summary-time">更新时间 {{ scene.generatedAt || '-' }}</div>
    </section>

    <section class="office-scene" :class="{ 'is-loading': loading, 'office-scene--compact': isCompactView }">
      <div class="scene-wall">
        <div class="window">
          <span></span><span></span><span></span><span></span>
        </div>
        <div class="status-board">
          <span class="board-title">今日状态</span>
          <span>{{ summary.present }} 在岗 / {{ summary.businessTrip }} 公出 / {{ summary.leave }} 请假 / {{ summary.noRecord }} 缺勤</span>
        </div>
      </div>

      <div v-if="loading" class="scene-loading">
        <span class="loader"></span>
        <p>正在布置办公室...</p>
      </div>
      <div v-else-if="!filteredPeople.length" class="scene-empty">
        <p>{{ errorMessage || (selectedStatus ? '当前状态下暂无人员' : '暂无人员数据') }}</p>
      </div>
      <div v-else-if="isAllView" class="dept-office-list">
        <section v-for="dept in peopleByDept" :key="dept.name" class="dept-office-section">
          <header class="dept-office-header">
            <h2>{{ dept.name }}</h2>
            <div class="dept-office-stats">
              <span>{{ dept.people.length }} 人</span>
              <span class="stat-present">{{ dept.summary.present }} 在岗</span>
              <span class="stat-trip">{{ dept.summary.businessTrip }} 公出</span>
              <span class="stat-leave">{{ dept.summary.leave }} 请假</span>
              <span class="stat-empty">{{ dept.summary.noRecord }} 暂无打卡</span>
            </div>
          </header>
          <div class="desk-sections desk-sections--dept">
            <div
              v-for="row in dept.rows"
              :key="row.key"
              class="desk-grid desk-grid--dept"
            >
              <article
                v-for="(person, index) in row.people"
                :key="person.gh || person.name"
                class="desk-card"
                :class="[
                  `desk-card--${person.status}`,
                  `desk-card--${genderClass(person)}`,
                  {
                    'desk-card--extendable': canExtendPerson(person) && !canNavigatePerson(person),
                    'desk-card--clickable': canNavigatePerson(person) || canExtendPerson(person),
                    'desk-card--navigable': canNavigatePerson(person),
                  },
                ]"
                :style="{ '--delay': `${(index % 6) * 0.12}s` }"
                :title="deskCardTitle(person)"
                @click="onDeskClick(person)"
              >
                <span v-if="canExtendPerson(person)" class="extend-flag">公出延长</span>
                <div class="desk-card__top">
                  <div class="person-name">
                    <strong>{{ person.name }}</strong>
                    <span class="dept-mini">{{ person.department }}</span>
                    <span v-if="person.jb">{{ person.jb }}</span>
                  </div>
                  <span class="status-pill">{{ person.statusLabel }}</span>
                </div>
                <div class="workstation" :class="{ travelling: person.status === 'business_trip' }">
                  <div class="desk-surface">
                    <div class="monitor"><span class="monitor-glow"></span></div>
                    <div class="keyboard"></div>
                    <div class="coffee"></div>
                  </div>
                  <div v-if="person.status === 'business_trip'" class="trip-motion" aria-hidden="true">
                    <div class="route-line"></div>
                    <div class="suitcase"><span></span></div>
                    <svg class="plane" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M22 2L11 13" />
                      <path d="M22 2l-7 20-4-9-9-4 20-7z" />
                    </svg>
                  </div>
                  <div
                    v-if="hasLeaveMarker(person)"
                    class="leave-marker"
                    :class="{ pending: !person.leave.approved }"
                  >
                    {{ person.leave.approved ? '假' : '审' }}
                  </div>
                  <div class="worker" :class="[person.status, genderClass(person)]" aria-hidden="true">
                    <div class="head"><span class="hair"></span></div>
                    <div class="body"></div>
                    <div class="arm arm-left"></div>
                    <div class="arm arm-right"></div>
                  </div>
                  <div class="chair"></div>
                </div>
                <div class="desk-meta">
                  <template v-if="person.status === 'business_trip'">
                    <span class="meta-main">{{ person.businessTrip?.location || '公出地点未填' }}</span>
                    <span class="meta-sub">{{ person.businessTrip?.startTime || '-' }} 至 {{ person.businessTrip?.endTime || '-' }}</span>
                  </template>
                  <template v-else-if="hasLeaveMarker(person)">
                    <span class="meta-main">{{ person.leave.statusLabel }} · {{ person.leave.type }}</span>
                    <span class="meta-sub">{{ person.leave.startTime || '-' }} 至 {{ person.leave.endTime || '-' }}</span>
                  </template>
                  <template v-else-if="person.attendance">
                    <span class="meta-main">首次 {{ person.attendance.firstTime || '-' }} · 最近 {{ person.attendance.lastTime || '-' }}</span>
                    <span class="meta-sub">打卡 {{ person.attendance.times?.length || 0 }} 次</span>
                  </template>
                  <template v-else>
                    <span class="meta-main">未查询到当天打卡</span>
                    <span class="meta-sub">可能未到岗、未同步或非工作日</span>
                  </template>
                  <span v-if="canNavigatePerson(person)" class="meta-link-hint">点击查看详情 →</span>
                </div>
              </article>
            </div>
          </div>
        </section>
      </div>
      <div v-else class="desk-sections">
        <div
          v-for="row in peopleRows"
          :key="row.key"
          class="desk-grid"
        >
          <article
            v-for="(person, index) in row.people"
            :key="person.gh || person.name"
            class="desk-card"
            :class="[
              `desk-card--${person.status}`,
              `desk-card--${genderClass(person)}`,
              {
                'desk-card--extendable': canExtendPerson(person) && !canNavigatePerson(person),
                'desk-card--clickable': canNavigatePerson(person) || canExtendPerson(person),
                'desk-card--navigable': canNavigatePerson(person),
              },
            ]"
            :style="{ '--delay': `${(index % 6) * 0.12}s` }"
            :title="deskCardTitle(person)"
            @click="onDeskClick(person)"
          >
            <span v-if="canExtendPerson(person)" class="extend-flag">公出延长</span>
            <div class="desk-card__top">
              <div class="person-name">
                <strong>{{ person.name }}</strong>
                <span v-if="person.jb">{{ person.jb }}</span>
              </div>
              <span class="status-pill">{{ person.statusLabel }}</span>
            </div>
            <div class="workstation" :class="{ travelling: person.status === 'business_trip' }">
              <div class="desk-surface">
                <div class="monitor"><span class="monitor-glow"></span></div>
                <div class="keyboard"></div>
                <div class="coffee"></div>
              </div>
              <div v-if="person.status === 'business_trip'" class="trip-motion" aria-hidden="true">
                <div class="route-line"></div>
                <div class="suitcase"><span></span></div>
                <svg class="plane" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 2L11 13" />
                  <path d="M22 2l-7 20-4-9-9-4 20-7z" />
                </svg>
              </div>
              <div
                v-if="hasLeaveMarker(person)"
                class="leave-marker"
                :class="{ pending: !person.leave.approved }"
              >
                {{ person.leave.approved ? '假' : '审' }}
              </div>
              <div class="worker" :class="[person.status, genderClass(person)]" aria-hidden="true">
                <div class="head"><span class="hair"></span></div>
                <div class="body"></div>
                <div class="arm arm-left"></div>
                <div class="arm arm-right"></div>
              </div>
              <div class="chair"></div>
            </div>
            <div class="desk-meta">
              <template v-if="person.status === 'business_trip'">
                <span class="meta-main">{{ person.businessTrip?.location || '公出地点未填' }}</span>
                <span class="meta-sub">{{ person.businessTrip?.startTime || '-' }} 至 {{ person.businessTrip?.endTime || '-' }}</span>
              </template>
              <template v-else-if="hasLeaveMarker(person)">
                <span class="meta-main">{{ person.leave.statusLabel }} · {{ person.leave.type }}</span>
                <span class="meta-sub">{{ person.leave.startTime || '-' }} 至 {{ person.leave.endTime || '-' }}</span>
              </template>
              <template v-else-if="person.attendance">
                <span class="meta-main">首次 {{ person.attendance.firstTime || '-' }} · 最近 {{ person.attendance.lastTime || '-' }}</span>
                <span class="meta-sub">打卡 {{ person.attendance.times?.length || 0 }} 次</span>
              </template>
              <template v-else>
                <span class="meta-main">未查询到当天打卡</span>
                <span class="meta-sub">可能未到岗、未同步或非工作日</span>
              </template>
              <span v-if="canNavigatePerson(person)" class="meta-link-hint">点击查看详情 →</span>
            </div>
          </article>
        </div>
      </div>
    </section>

    <!-- 公出延长弹窗 -->
    <div v-if="showExtendModal" class="modal-overlay" @click.self="closeExtend">
      <div class="modal-content">
        <button type="button" class="modal-close-btn" @click="closeExtend">&times;</button>
        <h2>公出延长</h2>
        <p class="modal-hint">为本科室已通过审批且未返回登记的公出修改预计返回时间，将重新提交部领导审批。</p>
        <form @submit.prevent="submitExtend" class="extend-form">
          <div class="extend-row">
            <div class="extend-field">
              <label>年度</label>
              <select v-model="extendFilterYear" :disabled="extendListLoading" @change="onExtendYearChange">
                <option value="">全部（近15年）</option>
                <option v-for="y in extendYearOptions" :key="'ex-y-' + y" :value="String(y)">{{ y }} 年</option>
              </select>
            </div>
            <div class="extend-field">
              <label>公出人</label>
              <select v-model="extendFilterPerson" :disabled="extendListLoading" @change="onExtendPersonChange">
                <option value="">全部</option>
                <option v-for="p in extendPeopleOptions" :key="'ex-p-' + p" :value="p">{{ p }}</option>
              </select>
            </div>
          </div>

          <p v-if="extendListLoading" class="modal-hint">加载可延长列表…</p>
          <p v-else-if="!extendableList.length" class="modal-hint extend-empty-hint">
            当前筛选下暂无可延长记录（需已通过审批且未返回登记）。可切换「全部（近15年）」、其他年度或公出人后查看。
          </p>

          <div class="extend-field">
            <label>选择公出记录</label>
            <select v-model="extendForm.selectedId" :disabled="extendListLoading" @change="onExtendSelect">
              <option value="">请选择</option>
              <option v-for="r in extendableList" :key="r.id" :value="r.id">
                {{ r.person }} · {{ r.location || '地点未填' }} · {{ r.expectedStartTime || '—' }}～{{ r.expectedReturnTime || '—' }}
              </option>
            </select>
          </div>

          <div v-if="extendForm.selectedId" class="extend-row">
            <div class="extend-field">
              <label>原预计返回时间</label>
              <input type="text" :value="extendForm.oldReturnTime || '—'" readonly class="readonly-input">
            </div>
            <div class="extend-field">
              <label>新预计返回时间</label>
              <input type="datetime-local" v-model="extendForm.newReturnTime" required>
            </div>
          </div>

          <div class="extend-field" v-if="extendForm.selectedId">
            <label>部领导</label>
            <select v-model="extendForm.deptLeader" required :disabled="extendLoadingApprovers">
              <option value="">请选择部领导</option>
              <option v-for="p in extendDeptLeaders" :key="p" :value="p">{{ p }}</option>
            </select>
          </div>

          <div class="extend-field" v-if="extendForm.selectedId">
            <label>备注（选填）</label>
            <input type="text" v-model="extendForm.remark" placeholder="延长原因说明">
          </div>

          <p v-if="extendError" class="extend-error">{{ extendError }}</p>

          <div class="extend-actions">
            <button type="button" class="ghost-btn" @click="closeExtend">取消</button>
            <button type="submit" class="primary-btn" :disabled="extendSubmitting || !extendForm.selectedId">
              {{ extendSubmitting ? '提交中…' : '确认延长' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getPersonnelAttendanceScene } from '@/api/personnelVisualization'
import { getApprovers, getExtendableBusinessTrips, extendBusinessTrip } from '@/api/attendance'
import { isDeptLeader, jbMatch } from '@/utils/roleMatch'

const router = useRouter()

const loading = ref(false)
const errorMessage = ref('')
const selectedDate = ref(formatLocalDate(new Date()))
const selectedDept = ref('')
const selectedStatus = ref('')
const statusFilterOptions = [
  { value: '', label: '全部状态' },
  { value: 'present', label: '在岗' },
  { value: 'business_trip', label: '公出' },
  { value: 'leave', label: '请假' },
  { value: 'no_record', label: '暂无打卡' },
]
const scene = ref({
  department: '',
  generatedAt: '',
  people: [],
  availableDepartments: [],
  summary: { total: 0, present: 0, businessTrip: 0, leave: 0, leavePending: 0, noRecord: 0 },
})

const people = computed(() => scene.value.people || [])
const showStatusFilter = computed(() => selectedDept.value === '全员' || scene.value.department === '全员')
const filteredPeople = computed(() => {
  const list = people.value
  if (!showStatusFilter.value || !selectedStatus.value) return list
  return list.filter((p) => p.status === selectedStatus.value)
})
const sceneSummary = computed(() => ({
  total: 0,
  present: 0,
  businessTrip: 0,
  leave: 0,
  leavePending: 0,
  noRecord: 0,
  ...(scene.value.summary || {}),
}))
const summary = computed(() => {
  if (!showStatusFilter.value || !selectedStatus.value) return sceneSummary.value
  const s = { total: 0, present: 0, businessTrip: 0, leave: 0, leavePending: 0, noRecord: 0 }
  for (const p of filteredPeople.value) {
    s.total += 1
    if (p.status === 'present') s.present += 1
    else if (p.status === 'business_trip') s.businessTrip += 1
    else if (p.status === 'leave') s.leave += 1
    else {
      s.noRecord += 1
      if (p.leave && !p.leave.approved) s.leavePending += 1
    }
  }
  return s
})
const availableDepartments = computed(() => scene.value.availableDepartments || [])
const isAllView = computed(() => scene.value.department === '全员')
const isCompactView = computed(() => isAllView.value || filteredPeople.value.length > 35)
const peopleRows = computed(() => buildDeskRows(filteredPeople.value))
const peopleByDept = computed(() => {
  const groups = new Map()
  for (const person of filteredPeople.value) {
    const dept = person.department || '未分科室'
    if (!groups.has(dept)) {
      groups.set(dept, {
        name: dept,
        people: [],
        summary: { present: 0, businessTrip: 0, leave: 0, noRecord: 0 },
      })
    }
    const group = groups.get(dept)
    group.people.push(person)
    if (person.status === 'present') group.summary.present += 1
    else if (person.status === 'business_trip') group.summary.businessTrip += 1
    else if (person.status === 'leave') group.summary.leave += 1
    else group.summary.noRecord += 1
  }
  return [...groups.values()]
    .map((group) => ({
      ...group,
      rows: buildDeskRows(group.people),
    }))
    .filter((group) => group.people.length > 0)
})

/** 领导岗排序：经理 → 副经理 → 主任/主任责 → 副主任 → 班组长/组长 */
function leadershipRank(jb) {
  const j = (jb || '').trim()
  if (!j) return 0
  if (j.includes('副经理')) return 2
  if (j === '经理' || (j.startsWith('经理') && !j.includes('经理助理'))) return 1
  if (j.includes('副主任')) return 4
  if (j.includes('主任责') || jbMatch(j, '主任')) return 3
  if (jbMatch(j, '组长')) return 5
  return 0
}

function compareByName(a, b) {
  return String(a?.name || '').localeCompare(String(b?.name || ''), 'zh-Hans-CN')
}

/**
 * 工位分组：
 * 1. 经理/副经理、主任/主任责、副主任、班组长/组长（固定首行）
 * 2. 其他在岗（姓名首字母）
 * 3. 其他公出
 * 4. 其他请假
 * 5. 其他暂无打卡
 * 各组另起一行展示
 */
function buildDeskRows(list) {
  const leaders = []
  const present = []
  const trip = []
  const leave = []
  const noRecord = []

  for (const person of list || []) {
    if (leadershipRank(person.jb) > 0) {
      leaders.push(person)
      continue
    }
    if (person.status === 'present') present.push(person)
    else if (person.status === 'business_trip') trip.push(person)
    else if (person.status === 'leave') leave.push(person)
    else noRecord.push(person)
  }

  leaders.sort((a, b) => leadershipRank(a.jb) - leadershipRank(b.jb) || compareByName(a, b))
  present.sort(compareByName)
  trip.sort(compareByName)
  leave.sort(compareByName)
  noRecord.sort(compareByName)

  return [
    { key: 'leaders', people: leaders },
    { key: 'present', people: present },
    { key: 'business_trip', people: trip },
    { key: 'leave', people: leave },
    { key: 'no_record', people: noRecord },
  ].filter((row) => row.people.length > 0)
}

function formatLocalDate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function getCurrentUser() {
  try {
    const raw = localStorage.getItem('userInfo')
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function getCurrentUserName() {
  const user = getCurrentUser()
  return (user.name || user.userName || '').trim()
}

const currentUserJb = computed(() => (getCurrentUser().jb || '').trim())
const canExtend = computed(() => isDeptLeader(currentUserJb.value))

function canExtendPerson(person) {
  return canExtend.value && person?.status === 'no_record'
}

function hasLeaveMarker(person) {
  return Boolean(person?.leave && (person.status === 'leave' || person.status === 'no_record'))
}

function canNavigatePerson(person) {
  if (person?.status === 'business_trip' && person.businessTrip?.id != null) return true
  if (hasLeaveMarker(person) && person.leave?.id != null) return true
  return false
}

function personTitle(person) {
  if (person.status === 'business_trip') {
    const trip = person.businessTrip || {}
    return `${person.name}：${person.statusLabel}，${trip.location || '地点未填'}`
  }
  if (hasLeaveMarker(person)) {
    const leave = person.leave || {}
    return `${person.name}：${leave.statusLabel || person.statusLabel}，${leave.type || ''}`
  }
  if (person.attendance) {
    return `${person.name}：${person.statusLabel}，${person.attendance.times?.join(' / ') || ''}`
  }
  return `${person.name}：${person.statusLabel}`
}

function deskCardTitle(person) {
  if (canNavigatePerson(person)) {
    if (person.status === 'business_trip') {
      return `${personTitle(person)}（点击查看公出详情）`
    }
    return `${personTitle(person)}（点击查看请假详情）`
  }
  if (canExtendPerson(person)) {
    return `${person.name}：暂无打卡，点击为其办理公出延长`
  }
  return personTitle(person)
}

function navigatePersonDetail(person) {
  if (person?.status === 'business_trip' && person.businessTrip?.id != null) {
    const trip = person.businessTrip
    const year = String(trip.startTime || selectedDate.value || '').slice(0, 4)
    router.push({
      path: '/attendance/business-trip',
      query: {
        view: 'ledger',
        focusId: String(trip.id),
        focusName: person.name || '',
        ...(year ? { year } : {}),
        status: '已通过',
      },
    })
    return
  }
  if (hasLeaveMarker(person) && person.leave?.id != null) {
    const leave = person.leave
    const year = String(leave.startTime || selectedDate.value || '').slice(0, 4)
    router.push({
      path: '/attendance/manual',
      query: {
        tab: 'leave',
        view: 'ledger',
        from: 'all-records',
        focusId: String(leave.id),
        focusName: person.name || '',
        ...(year ? { year } : {}),
        status: leave.approved ? 'approved' : 'processing',
      },
    })
  }
}

function onDeskClick(person) {
  if (canNavigatePerson(person)) {
    navigatePersonDetail(person)
    return
  }
  if (canExtendPerson(person)) {
    openExtend(person)
  }
}

function genderClass(person) {
  if (person?.gender === 'female' || String(person?.xbie || '').includes('女')) return 'female'
  if (person?.gender === 'male' || String(person?.xbie || '').includes('男')) return 'male'
  return 'unknown-gender'
}

async function loadScene() {
  const currentUser = getCurrentUserName()
  if (!currentUser) {
    errorMessage.value = '未获取到当前登录用户'
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const res = await getPersonnelAttendanceScene({
      current_user: currentUser,
      department: selectedDept.value || undefined,
      target_date: selectedDate.value,
    })
    if (res?.success) {
      scene.value = res
      if (!selectedDept.value && res.department) selectedDept.value = res.department
    } else {
      errorMessage.value = res?.message || '加载失败'
      scene.value = { ...scene.value, people: [] }
    }
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || e?.message || '加载失败'
    scene.value = { ...scene.value, people: [] }
  } finally {
    loading.value = false
  }
}

// ==================== 公出延长 ====================
const showExtendModal = ref(false)
const extendableList = ref([])
const extendListLoading = ref(false)
const extendFilterYear = ref(String(new Date().getFullYear()))
const extendFilterPerson = ref('')
const extendPeopleOptions = ref([])
const extendYearOptions = computed(() => {
  const y = new Date().getFullYear()
  return Array.from({ length: 15 }, (_, i) => y - i)
})
const extendDeptLeaders = ref([])
const extendLoadingApprovers = ref(false)
const extendSubmitting = ref(false)
const extendError = ref('')
const extendForm = reactive({
  selectedId: '',
  oldReturnTime: '',
  newReturnTime: '',
  deptLeader: '',
  remark: '',
})

async function fetchExtendableList() {
  const name = getCurrentUserName()
  if (!name) return
  extendListLoading.value = true
  extendError.value = ''
  try {
    const params = { name }
    if (extendFilterYear.value !== '' && extendFilterYear.value != null) {
      const yy = parseInt(String(extendFilterYear.value), 10)
      if (!Number.isNaN(yy)) params.year = yy
    }
    if ((extendFilterPerson.value || '').trim()) params.person = extendFilterPerson.value.trim()
    const res = await getExtendableBusinessTrips(params)
    extendableList.value = (res && res.list) || []
    extendPeopleOptions.value = (res && res.people) || []
  } catch (e) {
    extendError.value = e?.response?.data?.detail || e?.message || '获取可延长列表失败'
    extendableList.value = []
    extendPeopleOptions.value = []
  } finally {
    extendListLoading.value = false
  }
}

function resetExtendSelection() {
  extendForm.selectedId = ''
  extendForm.oldReturnTime = ''
  extendForm.newReturnTime = ''
  extendForm.deptLeader = ''
  extendForm.remark = ''
  extendDeptLeaders.value = []
}

async function onExtendYearChange() {
  extendFilterPerson.value = ''
  resetExtendSelection()
  await fetchExtendableList()
}

async function onExtendPersonChange() {
  resetExtendSelection()
  await fetchExtendableList()
}

async function openExtend(person) {
  if (!canExtend.value) return
  extendError.value = ''
  extendFilterYear.value = String(new Date().getFullYear())
  extendFilterPerson.value = (person?.name || '').trim()
  resetExtendSelection()
  extendPeopleOptions.value = []
  showExtendModal.value = true
  await fetchExtendableList()
  // 从某人卡片进入时：若该人恰好只有一条可延长记录，自动选中
  const target = (person?.name || '').trim()
  if (target) {
    const mine = extendableList.value.filter((r) => (r.person || '').trim() === target)
    if (mine.length === 1) {
      extendForm.selectedId = mine[0].id
      await onExtendSelect()
    }
  }
}

function closeExtend() {
  showExtendModal.value = false
}

async function onExtendSelect() {
  const rec = extendableList.value.find((r) => r.id === extendForm.selectedId)
  extendForm.oldReturnTime = rec ? rec.expectedReturnTime : ''
  extendForm.newReturnTime = ''
  extendForm.deptLeader = ''
  if (extendForm.selectedId) {
    extendLoadingApprovers.value = true
    try {
      const res = await getApprovers({ name: rec?.person || getCurrentUserName(), level: 'dept_leader' })
      extendDeptLeaders.value = res && res.approvers ? res.approvers.map((a) => a.name) : []
    } catch {
      extendDeptLeaders.value = []
    }
    extendLoadingApprovers.value = false
    const origLeader = (rec?.deptLeader || '').trim()
    if (origLeader && extendDeptLeaders.value.includes(origLeader)) {
      extendForm.deptLeader = origLeader
    }
  }
}

async function submitExtend() {
  extendError.value = ''
  if (!extendForm.selectedId) { extendError.value = '请选择公出记录'; return }
  if (!extendForm.newReturnTime) { extendError.value = '请填写新的预计返回时间'; return }
  if (!extendForm.deptLeader) { extendError.value = '请选择部领导'; return }
  extendSubmitting.value = true
  try {
    const res = await extendBusinessTrip(extendForm.selectedId, {
      current_user: getCurrentUserName(),
      new_return_time: extendForm.newReturnTime,
      dept_leader: extendForm.deptLeader,
      remark: extendForm.remark,
    })
    if (res.success) {
      alert(res.message || '延长已提交')
      showExtendModal.value = false
      loadScene()
    } else {
      extendError.value = res.message || '提交失败'
    }
  } catch (err) {
    const detail = err?.response?.data?.detail
    extendError.value = Array.isArray(detail)
      ? detail.map((d) => d.msg || d).join('; ')
      : detail || err?.message || '延长提交失败'
  } finally {
    extendSubmitting.value = false
  }
}

onMounted(loadScene)
</script>

<style scoped>
.personnel-visual-page {
  min-height: 100vh;
  padding: 0 18px 28px 0;
  color: #172033;
}

.visual-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 16px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #2563eb;
  font-size: 13px;
  font-weight: 700;
}

.visual-header h1 {
  margin: 0;
  font-size: 26px;
  line-height: 1.2;
  font-weight: 800;
}

.subtitle {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 14px;
}

.header-actions {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
  font-weight: 700;
}

.field input,
.field select {
  height: 36px;
  min-width: 150px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 10px;
  background: #fff;
  color: #172033;
}

.refresh-btn {
  height: 36px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid #2563eb;
  border-radius: 6px;
  padding: 0 14px;
  background: #2563eb;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.refresh-btn:disabled {
  opacity: 0.7;
  cursor: default;
}

.refresh-btn svg {
  width: 15px;
  height: 15px;
}

.summary-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(130px, 1fr)) minmax(180px, auto);
  gap: 10px;
  margin-bottom: 14px;
}

.summary-item,
.summary-time {
  min-height: 64px;
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 14px;
  background: #fff;
}

.summary-item strong {
  display: block;
  font-size: 24px;
  line-height: 1;
}

.summary-item span:last-child {
  display: block;
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.summary-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.summary-present .summary-dot { background: #10b981; }
.summary-trip .summary-dot { background: #f59e0b; }
.summary-leave .summary-dot { background: #8b5cf6; }
.summary-empty .summary-dot { background: #94a3b8; }

.summary-time {
  justify-content: center;
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
}

.office-scene {
  position: relative;
  overflow: hidden;
  min-height: 620px;
  border: 1px solid #d8e0ea;
  border-radius: 8px;
  background:
    linear-gradient(180deg, rgba(226, 244, 255, 0.84) 0 34%, rgba(245, 247, 251, 0) 34%),
    linear-gradient(90deg, rgba(15, 23, 42, 0.04) 1px, transparent 1px),
    linear-gradient(180deg, rgba(15, 23, 42, 0.04) 1px, transparent 1px),
    #f7fafc;
  background-size: auto, 34px 34px, 34px 34px, auto;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.scene-wall {
  position: relative;
  height: 150px;
  border-bottom: 10px solid #d6b88c;
  background:
    linear-gradient(90deg, rgba(255,255,255,0.28) 1px, transparent 1px),
    #dbeafe;
  background-size: 42px 42px;
}

.window {
  position: absolute;
  left: 34px;
  top: 26px;
  width: 170px;
  height: 88px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  border: 7px solid #ffffff;
  border-radius: 8px;
  background: linear-gradient(160deg, #93c5fd, #e0f2fe 60%, #fef08a);
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.16);
}

.window span {
  border: 1px solid rgba(255,255,255,0.9);
}

.status-board {
  position: absolute;
  right: 38px;
  top: 34px;
  min-width: 280px;
  padding: 12px 16px;
  border-radius: 8px;
  background: #0f172a;
  color: #dbeafe;
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.18);
}

.board-title {
  display: block;
  margin-bottom: 4px;
  color: #93c5fd;
  font-size: 12px;
  font-weight: 800;
}

.desk-grid {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  padding: 16px;
}

.desk-sections {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
}

.desk-sections .desk-grid {
  padding: 0;
}

.desk-sections--dept {
  padding: 8px;
  gap: 10px;
}

.dept-office-list {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 10px;
}

.dept-office-section {
  border: 1px solid rgba(148, 163, 184, 0.32);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.72);
  overflow: hidden;
}

.dept-office-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 42px;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(248, 250, 252, 0.9);
}

.dept-office-header h2 {
  margin: 0;
  color: #0f172a;
  font-size: 15px;
  font-weight: 800;
  white-space: nowrap;
}

.dept-office-stats {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
}

.dept-office-stats span {
  white-space: nowrap;
}

.dept-office-stats .stat-present { color: #059669; }
.dept-office-stats .stat-trip { color: #d97706; }
.dept-office-stats .stat-leave { color: #7c3aed; }
.dept-office-stats .stat-empty { color: #64748b; }

.desk-grid--dept {
  padding: 8px;
}

.desk-card {
  position: relative;
  min-height: 214px;
  border: 1px solid rgba(148, 163, 184, 0.38);
  border-radius: 8px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
  animation: deskIn 0.35s ease both;
  animation-delay: var(--delay);
}

.desk-card--present {
  border-top: 4px solid #10b981;
}

.desk-card--business_trip {
  border-top: 4px solid #f59e0b;
  background: #fff8ed;
}

.desk-card--leave {
  border-top: 4px solid #8b5cf6;
  background: #f7f3ff;
}

.desk-card--no_record {
  border-top: 4px solid #94a3b8;
  background: #f8fafc;
}

@keyframes deskIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.desk-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.person-name {
  min-width: 0;
}

.person-name strong {
  display: block;
  color: #0f172a;
  font-size: 14px;
}

.person-name span {
  display: block;
  margin-top: 2px;
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
}

.person-name .dept-mini {
  color: #2563eb;
}

.status-pill {
  flex-shrink: 0;
  border-radius: 999px;
  padding: 3px 7px;
  color: #fff;
  background: #64748b;
  font-size: 11px;
  font-weight: 800;
}

.desk-card--present .status-pill { background: #059669; }
.desk-card--business_trip .status-pill { background: #d97706; }
.desk-card--leave .status-pill { background: #7c3aed; }

.workstation {
  position: relative;
  height: 116px;
  margin-top: 10px;
}

.desk-surface {
  position: absolute;
  left: 18px;
  right: 18px;
  bottom: 16px;
  height: 54px;
  border-radius: 7px 7px 10px 10px;
  background: linear-gradient(180deg, #c08457, #8b5e3c);
  box-shadow: inset 0 4px rgba(255,255,255,0.14), 0 12px 18px rgba(91, 62, 38, 0.16);
}

.desk-surface::before,
.desk-surface::after {
  content: '';
  position: absolute;
  bottom: -38px;
  width: 8px;
  height: 40px;
  background: #70472b;
}

.desk-surface::before { left: 18px; }
.desk-surface::after { right: 18px; }

.monitor {
  position: absolute;
  left: 50%;
  bottom: 38px;
  width: 74px;
  height: 46px;
  transform: translateX(-50%);
  border: 5px solid #1f2937;
  border-radius: 6px;
  background: linear-gradient(135deg, #0ea5e9, #22c55e);
}

.desk-card--no_record .monitor {
  background: #cbd5e1;
}

.monitor-glow {
  position: absolute;
  inset: 5px;
  border-radius: 3px;
  background: rgba(255,255,255,0.26);
  animation: screenGlow 1.8s ease-in-out infinite;
}

.desk-card--no_record .monitor-glow {
  animation: none;
  opacity: 0.3;
}

@keyframes screenGlow {
  0%, 100% { opacity: 0.25; }
  50% { opacity: 0.72; }
}

.keyboard {
  position: absolute;
  left: 50%;
  bottom: 11px;
  width: 70px;
  height: 12px;
  transform: translateX(-50%);
  border-radius: 3px;
  background: repeating-linear-gradient(90deg, #1f2937 0 5px, #374151 5px 9px);
}

.coffee {
  position: absolute;
  right: 20px;
  bottom: 16px;
  width: 16px;
  height: 18px;
  border-radius: 0 0 6px 6px;
  background: #f8fafc;
}

.coffee::after {
  content: '';
  position: absolute;
  right: -7px;
  top: 4px;
  width: 7px;
  height: 7px;
  border: 2px solid #f8fafc;
  border-left: 0;
  border-radius: 0 8px 8px 0;
}

.worker {
  position: absolute;
  left: 50%;
  bottom: 55px;
  width: 56px;
  height: 86px;
  transform: translateX(-50%);
}

.worker.business_trip {
  left: 26%;
  animation: walking 1.1s ease-in-out infinite;
}

.worker.leave {
  opacity: 0.82;
}

.worker.no_record {
  opacity: 0.38;
  filter: grayscale(0.4);
}

@keyframes walking {
  0%, 100% { transform: translateX(-50%) translateY(0); }
  50% { transform: translateX(-50%) translateY(-4px); }
}

.head {
  position: absolute;
  top: 0;
  left: 50%;
  width: 34px;
  height: 34px;
  transform: translateX(-50%);
  border-radius: 50%;
  background: #f6c99f;
  box-shadow: inset 0 -2px rgba(133, 76, 38, 0.12);
}

.hair {
  position: absolute;
  top: -2px;
  left: 4px;
  right: 4px;
  height: 13px;
  border-radius: 15px 15px 8px 8px;
  background: #334155;
}

.worker.female .hair {
  top: -3px;
  left: 1px;
  right: 1px;
  height: 22px;
  border-radius: 18px 18px 10px 10px;
  background: #3f2f46;
}

.worker.female .hair::before,
.worker.female .hair::after {
  content: '';
  position: absolute;
  top: 10px;
  width: 11px;
  height: 26px;
  border-radius: 10px;
  background: #3f2f46;
}

.worker.female .hair::before {
  left: -2px;
  transform: rotate(8deg);
}

.worker.female .hair::after {
  right: -2px;
  transform: rotate(-8deg);
}

.worker.male .hair::after {
  content: '';
  position: absolute;
  right: 1px;
  bottom: -3px;
  width: 11px;
  height: 7px;
  border-radius: 0 0 8px 8px;
  background: #334155;
}

.body {
  position: absolute;
  top: 34px;
  left: 50%;
  width: 42px;
  height: 46px;
  transform: translateX(-50%);
  border-radius: 14px 14px 7px 7px;
  background: #2563eb;
}

.worker.female .body {
  width: 38px;
  border-radius: 16px 16px 12px 12px;
  background: #db2777;
}

.worker.female .body::after {
  content: '';
  position: absolute;
  left: 4px;
  right: 4px;
  bottom: -6px;
  height: 12px;
  border-radius: 0 0 14px 14px;
  background: inherit;
  transform: skewX(-10deg);
}

.desk-card--business_trip .body { background: #ea580c; }
.desk-card--leave .body { background: #7c3aed; }
.desk-card--no_record .body { background: #94a3b8; }

.desk-card--female.desk-card--present {
  border-top-color: #db2777;
}

.desk-card--female.desk-card--present .status-pill {
  background: #be185d;
}

.desk-card--female.desk-card--business_trip .body {
  background: #f97316;
}

.desk-card--female.desk-card--leave .body {
  background: #c026d3;
}

.desk-card--female.desk-card--no_record .body {
  background: #a8aebd;
}

.arm {
  position: absolute;
  top: 48px;
  width: 12px;
  height: 34px;
  border-radius: 8px;
  background: #f6c99f;
  transform-origin: top center;
}

.arm-left {
  left: 8px;
  transform: rotate(26deg);
  animation: typingLeft 0.7s ease-in-out infinite;
}

.arm-right {
  right: 8px;
  transform: rotate(-26deg);
  animation: typingRight 0.7s ease-in-out infinite;
}

.worker.business_trip .arm-left,
.worker.business_trip .arm-right,
.worker.leave .arm-left,
.worker.leave .arm-right,
.worker.no_record .arm-left,
.worker.no_record .arm-right {
  animation: none;
}

.worker.business_trip .arm-left { transform: rotate(58deg); }
.worker.business_trip .arm-right { transform: rotate(-58deg); }
.worker.leave .arm-left { transform: rotate(8deg); }
.worker.leave .arm-right { transform: rotate(-8deg); }

@keyframes typingLeft {
  0%, 100% { transform: rotate(22deg); }
  50% { transform: rotate(35deg); }
}

@keyframes typingRight {
  0%, 100% { transform: rotate(-22deg); }
  50% { transform: rotate(-35deg); }
}

.chair {
  position: absolute;
  left: 50%;
  bottom: 31px;
  width: 72px;
  height: 44px;
  transform: translateX(-50%);
  border-radius: 14px 14px 6px 6px;
  background: #334155;
  z-index: -1;
}

.trip-motion {
  position: absolute;
  inset: 0;
}

.leave-marker {
  position: absolute;
  right: 22px;
  top: 26px;
  z-index: 2;
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #fff;
  border-radius: 50%;
  background: #8b5cf6;
  color: #fff;
  font-size: 16px;
  font-weight: 900;
  box-shadow: 0 8px 18px rgba(124, 58, 237, 0.24);
  animation: leavePulse 1.9s ease-in-out infinite;
}

.leave-marker::after {
  content: '';
  position: absolute;
  inset: -5px;
  border: 1px solid rgba(139, 92, 246, 0.35);
  border-radius: 50%;
}

.leave-marker.pending {
  background: #f97316;
  box-shadow: 0 8px 18px rgba(249, 115, 22, 0.24);
}

.leave-marker.pending::after {
  border-color: rgba(249, 115, 22, 0.35);
}

@keyframes leavePulse {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-2px) scale(1.05); }
}

.route-line {
  position: absolute;
  left: 28px;
  right: 30px;
  top: 78px;
  height: 3px;
  border-top: 3px dashed #f59e0b;
}

.suitcase {
  position: absolute;
  left: 55%;
  top: 66px;
  width: 24px;
  height: 28px;
  border-radius: 5px;
  background: #0f766e;
  animation: suitcaseMove 1.7s ease-in-out infinite;
}

.suitcase::before {
  content: '';
  position: absolute;
  left: 7px;
  top: -8px;
  width: 10px;
  height: 8px;
  border: 2px solid #0f766e;
  border-bottom: 0;
  border-radius: 8px 8px 0 0;
}

.suitcase span,
.suitcase::after {
  content: '';
  position: absolute;
  bottom: -4px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #334155;
}

.suitcase span { left: 3px; }
.suitcase::after { right: 3px; }

@keyframes suitcaseMove {
  0%, 100% { transform: translateX(-6px); }
  50% { transform: translateX(10px); }
}

.plane {
  position: absolute;
  right: 14px;
  top: 18px;
  width: 30px;
  height: 30px;
  color: #0284c7;
  animation: planeFloat 2.2s ease-in-out infinite;
}

@keyframes planeFloat {
  0%, 100% { transform: translate(0, 0) rotate(0deg); }
  50% { transform: translate(-12px, 6px) rotate(-7deg); }
}

.desk-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed #d6dee9;
}

.office-scene--compact {
  min-height: 520px;
}

.office-scene--compact .scene-wall {
  height: 82px;
  border-bottom-width: 6px;
}

.office-scene--compact .window {
  left: 18px;
  top: 14px;
  width: 104px;
  height: 50px;
  border-width: 4px;
  border-radius: 6px;
}

.office-scene--compact .status-board {
  top: 14px;
  right: 18px;
  min-width: 180px;
  padding: 8px 12px;
  font-size: 12px;
}

.office-scene--compact .desk-grid {
  grid-template-columns: repeat(auto-fill, minmax(104px, 1fr));
  gap: 7px;
  padding: 10px;
}

.office-scene--compact .desk-sections {
  padding: 10px;
  gap: 10px;
}

.office-scene--compact .desk-sections .desk-grid {
  padding: 0;
}

.office-scene--compact .desk-sections--dept {
  padding: 8px;
}

.office-scene--compact .desk-card {
  min-height: 128px;
  padding: 6px;
  border-radius: 6px;
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.07);
}

.office-scene--compact .desk-card__top {
  gap: 4px;
}

.office-scene--compact .person-name strong {
  font-size: 12px;
  line-height: 1.15;
}

.office-scene--compact .person-name span {
  display: none;
}

.office-scene--compact .person-name .dept-mini {
  display: block;
  max-width: 64px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 9px;
}

.office-scene--compact .status-pill {
  padding: 2px 5px;
  font-size: 9px;
}

.office-scene--compact .workstation {
  height: 74px;
  margin-top: 4px;
}

.office-scene--compact .desk-surface {
  left: 8px;
  right: 8px;
  bottom: 9px;
  height: 28px;
  border-radius: 5px 5px 7px 7px;
}

.office-scene--compact .desk-surface::before,
.office-scene--compact .desk-surface::after {
  bottom: -20px;
  width: 5px;
  height: 22px;
}

.office-scene--compact .desk-surface::before { left: 10px; }
.office-scene--compact .desk-surface::after { right: 10px; }

.office-scene--compact .monitor {
  bottom: 21px;
  width: 38px;
  height: 24px;
  border-width: 3px;
  border-radius: 4px;
}

.office-scene--compact .keyboard {
  bottom: 6px;
  width: 38px;
  height: 7px;
  background: repeating-linear-gradient(90deg, #1f2937 0 3px, #374151 3px 5px);
}

.office-scene--compact .coffee {
  display: none;
}

.office-scene--compact .worker {
  bottom: 32px;
  width: 34px;
  height: 50px;
}

.office-scene--compact .head {
  width: 20px;
  height: 20px;
}

.office-scene--compact .hair {
  left: 3px;
  right: 3px;
  height: 8px;
}

.office-scene--compact .worker.female .hair {
  left: 0;
  right: 0;
  height: 14px;
}

.office-scene--compact .worker.female .hair::before,
.office-scene--compact .worker.female .hair::after {
  top: 7px;
  width: 7px;
  height: 15px;
}

.office-scene--compact .body {
  top: 20px;
  width: 25px;
  height: 27px;
  border-radius: 9px 9px 5px 5px;
}

.office-scene--compact .worker.female .body {
  width: 23px;
}

.office-scene--compact .arm {
  top: 29px;
  width: 7px;
  height: 19px;
}

.office-scene--compact .arm-left { left: 5px; }
.office-scene--compact .arm-right { right: 5px; }

.office-scene--compact .chair {
  bottom: 18px;
  width: 42px;
  height: 25px;
  border-radius: 9px 9px 5px 5px;
}

.office-scene--compact .desk-meta {
  display: none;
}

.office-scene--compact .route-line {
  left: 15px;
  right: 16px;
  top: 42px;
  border-top-width: 2px;
}

.office-scene--compact .suitcase {
  left: 54%;
  top: 34px;
  width: 14px;
  height: 16px;
  border-radius: 3px;
}

.office-scene--compact .suitcase::before {
  left: 4px;
  top: -5px;
  width: 6px;
  height: 5px;
}

.office-scene--compact .plane {
  right: 5px;
  top: 8px;
  width: 18px;
  height: 18px;
}

.office-scene--compact .leave-marker {
  right: 9px;
  top: 15px;
  width: 22px;
  height: 22px;
  font-size: 11px;
  border-width: 1px;
}

.meta-main {
  color: #172033;
  font-size: 13px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta-sub {
  color: #64748b;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.scene-loading,
.scene-empty {
  min-height: 420px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #64748b;
  font-weight: 700;
}

.loader {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 4px solid #dbeafe;
  border-top-color: #2563eb;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.extend-btn {
  height: 36px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid #f59e0b;
  border-radius: 6px;
  padding: 0 14px;
  background: #fff;
  color: #b45309;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.extend-btn:hover {
  background: #fffbeb;
}

.extend-btn svg {
  width: 15px;
  height: 15px;
}

.desk-card--extendable {
  cursor: pointer;
  transition: box-shadow 0.18s ease, transform 0.18s ease;
}

.desk-card--extendable:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 30px rgba(245, 158, 11, 0.26);
  border-color: #f59e0b;
}

.desk-card--clickable {
  cursor: pointer;
  transition: box-shadow 0.18s ease, transform 0.18s ease, border-color 0.18s ease;
}

.desk-card--navigable:hover {
  transform: translateY(-2px);
}

.desk-card--business_trip.desk-card--navigable:hover {
  box-shadow: 0 16px 30px rgba(217, 119, 6, 0.24);
  border-color: #d97706;
}

.desk-card--leave.desk-card--navigable:hover,
.desk-card--no_record.desk-card--navigable:hover {
  box-shadow: 0 16px 30px rgba(124, 58, 237, 0.22);
  border-color: #7c3aed;
}

.meta-link-hint {
  display: block;
  margin-top: 6px;
  font-size: 11px;
  font-weight: 600;
  color: #2563eb;
}

.desk-card--business_trip .meta-link-hint { color: #d97706; }
.desk-card--leave .meta-link-hint,
.desk-card--no_record.desk-card--navigable .meta-link-hint { color: #7c3aed; }

.extend-flag {
  position: absolute;
  z-index: 3;
  top: -1px;
  right: -1px;
  padding: 3px 8px;
  border-radius: 0 7px 0 10px;
  background: #f59e0b;
  color: #fff;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.5px;
  box-shadow: 0 4px 10px rgba(245, 158, 11, 0.3);
}

.office-scene--compact .extend-flag {
  padding: 2px 5px;
  font-size: 9px;
  border-radius: 0 6px 0 8px;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.5);
  padding: 16px;
}

.modal-content {
  position: relative;
  width: 540px;
  max-width: 100%;
  max-height: 88vh;
  overflow-y: auto;
  padding: 22px 24px 20px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.28);
}

.modal-content h2 {
  margin: 0 0 6px;
  font-size: 20px;
  font-weight: 800;
  color: #0f172a;
}

.modal-close-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #94a3b8;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
}

.modal-close-btn:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.modal-hint {
  margin: 0 0 12px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}

.extend-empty-hint {
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 6px;
  padding: 8px 10px;
}

.extend-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.extend-row {
  display: flex;
  gap: 12px;
}

.extend-field {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.extend-field label {
  font-size: 12px;
  font-weight: 700;
  color: #475569;
}

.extend-field input,
.extend-field select {
  height: 38px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 10px;
  background: #fff;
  color: #172033;
  font-size: 13px;
}

.extend-field input:focus,
.extend-field select:focus {
  border-color: #2563eb;
  outline: none;
}

.readonly-input {
  background: #f1f5f9;
  cursor: default;
}

.extend-error {
  margin: 0;
  color: #dc2626;
  font-size: 13px;
  font-weight: 600;
}

.extend-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 6px;
  padding-top: 14px;
  border-top: 1px solid #e2e8f0;
}

.ghost-btn,
.primary-btn {
  height: 38px;
  padding: 0 18px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.ghost-btn {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #475569;
}

.ghost-btn:hover {
  background: #f8fafc;
}

.primary-btn {
  border: 1px solid #2563eb;
  background: #2563eb;
  color: #fff;
}

.primary-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 980px) {
  .visual-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .header-actions {
    justify-content: flex-start;
  }

  .summary-strip {
    grid-template-columns: repeat(2, minmax(150px, 1fr));
  }

  .summary-time {
    grid-column: 1 / -1;
  }
}

@media (max-width: 640px) {
  .personnel-visual-page {
    padding-right: 0;
  }

  .header-actions,
  .field,
  .field input,
  .field select,
  .refresh-btn {
    width: 100%;
  }

  .summary-strip {
    grid-template-columns: 1fr;
  }

  .scene-wall {
    height: 122px;
  }

  .window {
    display: none;
  }

  .status-board {
    left: 18px;
    right: 18px;
    top: 24px;
  }

  .desk-grid {
    grid-template-columns: 1fr;
    padding: 14px;
  }

  .desk-sections {
    padding: 14px;
  }

  .desk-sections .desk-grid {
    padding: 0;
  }

  .desk-sections--dept {
    padding: 8px;
  }
}
</style>
