<template>
  <div class="attendance-page">
    <!-- 页面头部 -->
    <div class="page-header-bar">
      <div class="container">
        <div class="header-bar-content">
          <div>
            <h1 class="page-title">考勤智能填报</h1>
            <p class="page-subtitle">基于打卡数据的智能分析和填报</p>
          </div>
          <div class="header-actions">
            <div v-if="canApprove" class="header-btn-wrap">
              <router-link to="/attendance/approvals" class="btn btn-header-link">考勤审批</router-link>
            </div>
            <div class="header-btn-wrap">
              <router-link to="/attendance/manual" class="btn btn-header-link">手动填报</router-link>
              <p class="header-btn-hint">智能填报无法满足时可手动填报</p>
            </div>
            <!-- 月份选择器 -->
            <div class="month-selector">
              <label class="month-label">选择月份：</label>
              <input 
                v-model="selectedMonth" 
                type="month" 
                name="attendanceMonth"
                autocomplete="on"
                class="input month-input"
                @change="handleMonthChange"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="container">

      <!-- 智能建议面板 -->
      <div v-if="suggestions.length > 0" class="suggestions-section mt-xl">
        <div class="suggestions-header mb-base">
          <div class="flex-center">
            <svg class="icon-md mr-sm text-warning" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            <h3 class="section-title">智能建议 ({{ suggestions.length }})</h3>
          </div>
          <span class="suggestions-hint text-tertiary text-sm">基于当前数据分析</span>
        </div>
        <div class="suggestions-grid">
          <div
            v-for="(suggestion, index) in suggestions"
            :key="index"
            class="suggestion-card"
            :class="[`suggestion-${suggestion.type}`, { 'suggestion-handled': suggestion.handled, 'suggestion-under-review': suggestion.under_review }]"
          >
            <div class="suggestion-icon">
              <svg v-if="suggestion.type === 'warning'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
              <svg v-else-if="suggestion.type === 'info'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 16v-4" />
                <path d="M12 8h.01" />
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 9v4M12 17h.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z" />
              </svg>
            </div>
            <div class="suggestion-content">
              <div class="suggestion-meta">
                <span class="suggestion-date">{{ suggestion.date }}</span>
                <span class="suggestion-badge" :class="`badge-${suggestion.type}`">
                  {{ suggestion.typeLabel }}
                </span>
              </div>
              <div class="suggestion-desc">{{ suggestion.message }}</div>
            </div>
            <!-- 自动填报按钮 - 处理完成(绿)/正在审核(橙)/未处理显示操作按钮 -->
            <!-- 加班建议 -->
            <button 
              v-if="suggestion.message && suggestion.message.includes('加班')"
              class="auto-fill-btn btn-overtime"
              :class="{ 'btn-handled': suggestion.handled, 'btn-under-review': suggestion.under_review }"
              :disabled="suggestion.handled || suggestion.under_review"
              @click.stop="!suggestion.handled && !suggestion.under_review && handleOvertimeFill(suggestion)"
              :title="suggestion.handled ? '已处理完成' : suggestion.under_review ? '已提交，正在审核' : '自动填报加班申请'"
            >
              <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <template v-if="suggestion.handled">
                  <path d="M9 11l3 3L22 4"/>
                  <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
                </template>
                <template v-else-if="suggestion.under_review">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M12 6v6l4 2"/>
                </template>
                <template v-else>
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </template>
              </svg>
              {{ suggestion.handled ? '处理完成' : suggestion.under_review ? '正在审核' : '填报加班' }}
            </button>
            <!-- 缺勤/考勤建议 - 处理完成 / 正在审核 / 或两个操作按钮 -->
            <template v-else-if="suggestion.message && (suggestion.message.includes('缺勤') || suggestion.message.includes('考勤建议'))">
              <button 
                v-if="suggestion.handled"
                class="auto-fill-btn btn-handled"
                disabled
                title="已处理完成"
              >
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M9 11l3 3L22 4"/>
                  <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
                </svg>
                处理完成
              </button>
              <button 
                v-else-if="suggestion.under_review"
                class="auto-fill-btn btn-under-review"
                disabled
                title="已提交，正在审核"
              >
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M12 6v6l4 2"/>
                </svg>
                正在审核
              </button>
              <div v-else class="button-group">
                <button 
                  class="auto-fill-btn btn-leave"
                  @click.stop="handleLeaveFill(suggestion)"
                  title="使用换休票填报请假"
                >
                  <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M9 11l3 3L22 4"/>
                    <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
                  </svg>
                  填报请假
                </button>
                <button 
                  class="auto-fill-btn btn-business-trip"
                  @click.stop="handleBusinessTripReturnFill(suggestion)"
                  title="调整公出申请并填充时间"
                >
                  <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                    <polyline points="9 22 9 12 15 12 15 22"/>
                  </svg>
                  公出登记
                </button>
              </div>
            </template>
          </div>
        </div>
      </div>


      <!-- 数据表格 -->
      <div class="table-container card mt-xl">
        <div class="table-header">
          <h3 class="table-title">考勤记录列表</h3>
          <div class="table-toolbar">
            <span class="table-info text-tertiary text-sm">
              共 {{ records.length }} 条记录
            </span>
          </div>
        </div>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>日期</th>
                <th>姓名</th>
                <th>所在单位</th>
                <th>考勤时间1</th>
                <th>考勤时间2</th>
                <th>考勤时间3</th>
                <th>考勤时间4</th>
                <th>考勤时间5</th>
                <th>考勤时间6</th>
                <th>考勤时间7</th>
                <th>考勤时间8</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="records.length === 0">
                <td colspan="11" class="text-center text-tertiary">
                  暂无考勤记录
                </td>
              </tr>
              <tr v-for="record in records" :key="record.id">
                <td>
                  <span class="table-date">{{ record.attendance_date }}</span>
                </td>
                <td>
                  <div class="employee-cell">
                    <div class="employee-avatar">
                      {{ record.employee_name ? record.employee_name.charAt(0) : '' }}
                    </div>
                    <span class="employee-name">{{ record.employee_name }}</span>
                  </div>
                </td>
                <td>
                  <span class="text-secondary">{{ record.department }}</span>
                </td>
                <td>
                  <span class="time-badge">{{ record.time_1 || '-' }}</span>
                </td>
                <td>
                  <span class="time-badge">{{ record.time_2 || '-' }}</span>
                </td>
                <td>
                  <span class="time-badge">{{ record.time_3 || '-' }}</span>
                </td>
                <td>
                  <span class="time-badge">{{ record.time_4 || '-' }}</span>
                </td>
                <td>
                  <span class="time-badge">{{ record.time_5 || '-' }}</span>
                </td>
                <td>
                  <span class="time-badge">{{ record.time_6 || '-' }}</span>
                </td>
                <td>
                  <span class="time-badge">{{ record.time_7 || '-' }}</span>
                </td>
                <td>
                  <span class="time-badge">{{ record.time_8 || '-' }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 加班登记弹窗（本页填写，无需跳转） -->
    <OvertimeRegisterModal
      :visible="overtimeModalVisible"
      :prefill="overtimePrefill"
      @close="overtimeModalVisible = false"
      @submitted="loadSuggestions"
    />

    <!-- 请假申请弹窗（本页填写，无需跳转） -->
    <LeaveApplyModal
      :visible="leaveModalVisible"
      :prefill="leavePrefill"
      @close="leaveModalVisible = false"
      @submitted="loadSuggestions"
    />

    <!-- 公出申请弹窗（本页填写，无需跳转，与公出管理页保持一致） -->
    <div v-if="businessTripModalVisible" class="modal-overlay" @click.self="businessTripModalVisible = false">
      <div class="modal-content">
        <h2>公出登记</h2>
        <form @submit.prevent="handleBusinessTripSubmit" class="application-form" autocomplete="on">
          <!-- 公出类型：市内 / 境内 / 境外 -->
          <div class="form-row">
            <div class="form-group full">
              <label>公出类型 <span class="label-required">*</span></label>
              <select v-model="btTripScope" name="tripScope" autocomplete="on">
                <option value="市内公出">市内公出</option>
                <option value="境内公出">境内公出</option>
                <option value="境外公出">境外公出</option>
              </select>
            </div>
          </div>

          <!-- 基础信息（委派单位仅境内/境外显示） -->
          <div class="form-row" v-if="!btIsCityTrip">
            <div class="form-group half">
              <label>委派单位</label>
              <select v-model="btForm.targetUnit" name="targetUnit" autocomplete="on">
                <option value="项目管理部">项目管理部</option>
                <option value="大电机研究所">大电机研究所</option>
                <option value="采购部">采购部</option>
                <option value="装备能源部">装备能源部</option>
                <option value="质量检测部">质量检测部</option>
                <option value="人力资源部">人力资源部</option>
                <option value="市场部">市场部</option>
                <option value="数字化部">数字化部</option>
                <option value="科技创新部">科技创新部</option>
                <option value="智能制造工艺部">智能制造工艺部</option>
                <option value="新产业开发部">新产业发展部</option>
                <option value="新能源事业部">新能源事业部</option>
                <option value="其他">其他</option>
              </select>
            </div>
            <div class="form-group half" v-if="!btIsCityTrip">
              <label>委派时间 <span class="label-optional">（可选）</span></label>
              <input type="date" v-model="btForm.assignTime" name="assignTime" autocomplete="on" placeholder="选填">
            </div>
          </div>

          <div class="form-row">
            <div class="form-group half" v-if="!btIsCityTrip">
              <label>通知单编号 <span class="label-optional">（选填）</span></label>
              <input id="bt-noticeNo" type="text" v-model="btForm.noticeNo" name="noticeNo" autocomplete="on" placeholder="选填">
            </div>
            <div class="form-group half" :class="{ full: btIsCityTrip }">
              <label>填报单位</label>
              <input type="text" v-model="btForm.department" readonly>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group half">
              <label>公出人员姓名</label>
              <input type="text" v-model="btForm.name" readonly>
            </div>
            <div class="form-group half">
              <label>本次公出总人数</label>
              <input type="number" v-model="btForm.totalPeople" name="totalPeople" autocomplete="on" min="1">
            </div>
          </div>

          <!-- 公出详情（工作号、项目名称仅境内/境外） -->
          <div class="form-row" v-if="!btIsCityTrip">
            <div class="form-group half">
              <label>工作号 <span class="label-optional">（选填）</span></label>
              <input id="bt-workNo" type="text" v-model="btForm.workNo" name="workNo" autocomplete="on" placeholder="选填">
            </div>
            <div class="form-group half">
              <label>项目名称 <span class="label-optional">（选填）</span></label>
              <input id="bt-projectName" type="text" v-model="btForm.projectName" name="projectName" autocomplete="on" placeholder="选填">
            </div>
          </div>

          <div class="form-row">
            <div class="form-group full">
              <label>公出地点</label>
              <input v-if="btIsCityTrip" id="bt-location" type="text" :value="'市内'" readonly class="readonly-input">
              <input v-else id="bt-location" type="text" v-model="btForm.location" name="location" autocomplete="street-address" placeholder="请输入公出地点">
            </div>
          </div>

          <!-- 时间与费用（仅选日期，不参与考勤统计） -->
          <div class="form-row">
            <div class="form-group half">
              <label>出发时间</label>
              <input type="date" v-model="btForm.startTime" name="btStartTime" autocomplete="on">
            </div>
            <div class="form-group half">
              <label>预计返回时间</label>
              <input type="date" v-model="btForm.endTime" name="btEndTime" autocomplete="on">
            </div>
          </div>

          <div class="form-row">
            <div class="form-group half" v-if="!btIsCityTrip">
              <label>请款金额 <span class="label-optional">（选填）</span></label>
              <input type="number" v-model="btForm.amount" name="amount" autocomplete="on" min="0" step="0.01" placeholder="选填">
            </div>
            <div class="form-group half" :class="{ full: btIsCityTrip }">
              <label>联系电话</label>
              <input id="bt-phone" type="text" v-model="btForm.phone" name="btPhone" autocomplete="tel" placeholder="请输入联系电话">
            </div>
          </div>

          <div class="form-group">
            <label>公出任务</label>
            <textarea id="bt-task" v-model="btForm.task" name="btTask" autocomplete="on" rows="4" placeholder="请输入公出任务详情"></textarea>
          </div>

          <!-- 审批人 -->
          <div class="form-row">
            <div class="form-group half">
              <label>部领导</label>
              <select v-model="btForm.deptLeader" name="deptLeader" autocomplete="on" :disabled="btLoadingApprovers">
                <option value="">请选择部领导</option>
                <option v-for="person in btDeptLeaders" :key="person" :value="person">{{ person }}</option>
              </select>
            </div>
            <div class="form-group half">
              <label>室主任</label>
              <select v-model="btForm.responsiblePerson" name="roomDirector" autocomplete="on" :disabled="btLoadingApprovers">
                <option value="">请选择室主任</option>
                <option v-for="person in btRoomDirectors" :key="person" :value="person">{{ person }}</option>
              </select>
            </div>
          </div>

          <div class="form-group checkbox-group">
            <label class="checkbox-label text-danger">
              <input type="checkbox" v-model="btForm.confirmed">
              我确认已阅读并遵守《GYBG-047 智能制造工艺部公出人员管理办法》及公司相关规定。
            </label>
            <a :href="btManagementDocUrl" target="_blank" rel="noopener noreferrer" class="doc-link">点击阅读《GYBG-047 智能制造工艺部公出人员管理办法》</a>
          </div>

          <!-- 底部操作 -->
          <div class="form-actions">
            <button type="button" @click="businessTripModalVisible = false">取消</button>
            <button type="submit" class="btn-primary">提交</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getSuggestions, queryAttendance, getAttendanceDates, checkCanApprove, submitBusinessTripApply, getApprovers } from '@/api/attendance'
import OvertimeRegisterModal from '@/components/OvertimeRegisterModal.vue'
import LeaveApplyModal from '@/components/LeaveApplyModal.vue'

const router = useRouter()

const canApprove = ref(false)

const overtimeModalVisible = ref(false)
const overtimePrefill = ref({})
const leaveModalVisible = ref(false)
const leavePrefill = ref({})

// 公出申请弹窗（考勤页内，与公出管理页一致）
const businessTripModalVisible = ref(false)
const btTripScope = ref('市内公出')
const btIsCityTrip = computed(() => btTripScope.value === '市内公出')
const btForm = reactive({
  targetUnit: '项目管理部',
  assignTime: '',
  noticeNo: '',
  department: '',
  name: '',
  totalPeople: 1,
  workNo: '',
  projectName: '',
  location: '',
  startTime: '',
  endTime: '',
  amount: 0,
  phone: '',
  task: '',
  deptLeader: '',
  responsiblePerson: '',
  confirmed: false
})
const btDeptLeaders = ref([])
const btRoomDirectors = ref([])
const btLoadingApprovers = ref(false)
const btManagementDocUrl = '/doc/gybg-047'

const toTimeValue = (t) => {
  if (!t) return '08:00:00'
  const parts = String(t).split(':')
  const h = String(parseInt(parts[0] || 0, 10)).padStart(2, '0')
  const m = String(parseInt(parts[1] || 0, 10)).padStart(2, '0')
  const s = String(parseInt(parts[2] || 0, 10)).padStart(2, '0')
  return `${h}:${m}:${s}`
}

// 处理加班自动填报：本页弹窗，无需跳转，可连续填报
const handleOvertimeFill = (suggestion) => {
  if (!suggestion) return
  const timeMatch = (suggestion.message || '').match(/(\d{1,2}:\d{2}(?::\d{2})?)\s*到\s*(\d{1,2}:\d{2}(?::\d{2})?)/)
  const startTime = timeMatch ? toTimeValue(timeMatch[1]) : '08:00:00'
  const endTime = timeMatch ? toTimeValue(timeMatch[2]) : '17:00:00'
  const date = suggestion.date ? suggestion.date.slice(0, 10) : ''
  overtimePrefill.value = {
    date,
    startTime,
    endTime,
    content: '',  // 加班内容不自动填充，由用户输入
    locked: true  // 从智能建议入口进入时锁定日期与时间，不可修改
  }
  overtimeModalVisible.value = true
}

// 处理请假自动填报：本页弹窗，无需跳转，可连续填报
const handleLeaveFill = (suggestion) => {
  if (!suggestion) return
  const timeMatch = (suggestion.message || '').match(/(\d{1,2}:\d{2}(?::\d{2})?)\s*到\s*(\d{1,2}:\d{2}(?::\d{2})?)/)
  let duration = 0.25
  if (timeMatch) {
    const parts1 = timeMatch[1].split(':').map(Number)
    const parts2 = timeMatch[2].split(':').map(Number)
    const sh = parts1[0], sm = parts1[1], ss = parts1[2] || 0
    const eh = parts2[0], em = parts2[1], es = parts2[2] || 0
    let hours = (eh + em / 60 + es / 3600) - (sh + sm / 60 + ss / 3600)
    if (sh <= 12 && eh >= 13) hours -= 1
    duration = Math.round((hours / 8) * 4) / 4
    if (duration < 0.25) duration = 0.25
  }
  if ((suggestion.message || '').includes('全天') || (suggestion.message || '').includes('全天缺勤')) {
    duration = 1
  }
  const date = suggestion.date ? suggestion.date.slice(0, 10) : ''
  const fmt = (t) => {
    if (!t) return '08:00:00'
    const p = t.split(':').map(v => v.padStart(2, '0'))
    while (p.length < 3) p.push('00')
    return p.join(':')
  }
  const startTime = date && timeMatch ? `${date}T${fmt(timeMatch[1])}` : ''
  const endTime = date && timeMatch ? `${date}T${fmt(timeMatch[2])}` : ''
  leavePrefill.value = {
    type: '换休',
    startTime,
    endTime,
    duration: String(duration),
    reason: '',  // 事由不自动填充，由用户填写
    locked: true // 从智能建议入口进入时锁定开始/结束时间，不可编辑
  }
  leaveModalVisible.value = true
}

// 公出：从考勤建议入口，在本页打开公出登记弹窗并预填时间（表单与公出管理页一致）
const handleBusinessTripReturnFill = async (suggestion) => {
  const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
  const name = userInfo.name || userInfo.userName || ''
  if (!name) {
    alert('请先登录')
    return
  }
  const dept = userInfo.dept || userInfo.department || ''
  const date = suggestion?.date ? String(suggestion.date).slice(0, 10) : ''

  btTripScope.value = '市内公出'
  btForm.targetUnit = '项目管理部'
  btForm.assignTime = ''
  btForm.noticeNo = ''
  btForm.department = dept
  btForm.name = name
  btForm.totalPeople = 1
  btForm.workNo = ''
  btForm.projectName = ''
  btForm.location = '市内'
  btForm.startTime = date
  btForm.endTime = date
  btForm.amount = 0
  btForm.phone = ''
  btForm.task = ''
  btForm.deptLeader = ''
  btForm.responsiblePerson = ''
  btForm.confirmed = false

  // 获取当前用户对应的部领导与室主任列表
  btLoadingApprovers.value = true
  try {
    const [r1, r2] = await Promise.all([
      getApprovers({ name, level: 'dept_leader' }),
      getApprovers({ name, level: 'room_director' })
    ])
    btDeptLeaders.value = (r1.success && r1.approvers) ? r1.approvers.map(a => a.name) : []
    btRoomDirectors.value = (r2.success && r2.approvers) ? r2.approvers.map(a => a.name) : []
  } catch (e) {
    console.error('获取公出审批人失败:', e)
    btDeptLeaders.value = []
    btRoomDirectors.value = []
  } finally {
    btLoadingApprovers.value = false
  }

  businessTripModalVisible.value = true
}

// 公出申请弹窗提交
const handleBusinessTripSubmit = async () => {
  const tips = []
  if (btIsCityTrip.value) btForm.location = '市内'
  if (!(btForm.location || '').trim()) tips.push('公出地点')
  if (!(btForm.task || '').trim()) tips.push('公出任务')
  if (!(btForm.phone || '').trim()) tips.push('联系电话')
  if (!(btForm.startTime || '').trim()) tips.push('出发时间')
  if (!(btForm.endTime || '').trim()) tips.push('预计返回时间')
  if (!(btForm.deptLeader || '').trim()) tips.push('部领导')
  if (!(btForm.responsiblePerson || '').trim()) tips.push('室主任')
  if (!btForm.confirmed) tips.push('勾选并确认已阅读管理办法')
  if (tips.length) {
    alert('请完善后再提交：\n\n' + tips.map(t => '· ' + t).join('\n'))
    return
  }

  const startTime = `${btForm.startTime}T08:00:00`
  const endTime = `${btForm.endTime}T17:00:00`

  try {
    const payload = {
      tripScope: btTripScope.value,
      targetUnit: btForm.targetUnit,
      assignTime: '',
      noticeNo: '',
      department: btForm.department,
      name: btForm.name,
      totalPeople: Number(btForm.totalPeople) || 1,
      workNo: '',
      projectName: '',
      location: btForm.location,
      startTime,
      endTime,
      amount: 0,
      phone: btForm.phone,
      task: btForm.task,
      deptLeader: btForm.deptLeader,
      responsiblePerson: btForm.responsiblePerson
    }
    const res = await submitBusinessTripApply(payload)
    if (res.success) {
      alert('公出申请已提交')
      businessTripModalVisible.value = false
      await loadSuggestions()
    } else {
      alert(res.message || '提交失败')
    }
  } catch (e) {
    const msg = e?.response?.data?.detail || e.message
    alert(msg || '提交失败，请稍后重试')
  }
}

// 选中的月份（格式：YYYY-MM）
const selectedMonth = ref('')

// 默认当前月份（无考勤数据时使用）
const initCurrentMonth = () => {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  selectedMonth.value = `${year}-${month}`
}

// 选择距离当前最近的有考勤记录的月份
const initMonthWithLatestData = async () => {
  const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
  if (!userInfo.name || !userInfo.dept) {
    initCurrentMonth()
    return
  }
  try {
    const res = await getAttendanceDates({ name: userInfo.name, dept: userInfo.dept })
    const dates = (res && res.dates) || []
    if (dates.length === 0) {
      initCurrentMonth()
      return
    }
    // dates 为 YYYY-MM-DD 字符串，取最后一条所在月份
    const sorted = [...dates].sort()
    const lastDate = sorted[sorted.length - 1]
    const ymd = String(lastDate).trim()
    if (ymd.length >= 7) {
      selectedMonth.value = ymd.slice(0, 7) // YYYY-MM
    } else {
      initCurrentMonth()
    }
  } catch {
    initCurrentMonth()
  }
}

// 智能建议
const suggestions = ref([])

// 加载智能建议（按选定月份从表读取，上传打卡时已预生成）
const loadSuggestions = async () => {
  try {
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
    if (!userInfo.name || !userInfo.dept) return
    const [year, month] = selectedMonth.value.split('-')
    if (!year || !month) return
    const response = await getSuggestions({
      name: userInfo.name,
      dept: userInfo.dept,
      year: parseInt(year, 10),
      month: parseInt(month, 10)
    })
    if (response.success && response.suggestions) {
      suggestions.value = response.suggestions.map(item => {
        let type = 'info'
        if ((item.suggestion || '').includes('缺勤') || (item.suggestion || '').includes('迟到')) type = 'warning'
        return {
          type,
          typeLabel: item.dayType || '',
          date: item.date || '',
          message: item.suggestion || '',
          status: item.status ?? 0,
          handled: !!item.handled,
          under_review: !!item.under_review
        }
      })
    } else {
      suggestions.value = []
    }
  } catch (error) {
    console.error('加载智能建议失败:', error)
    suggestions.value = []
  }
}

// 页面加载时：优先选中有考勤记录的最近月份，再拉取建议与记录
onMounted(async () => {
  await initMonthWithLatestData()
  loadSuggestions()
  loadAttendanceRecords()
  const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
  const name = (userInfo.name || userInfo.userName || '').trim()
  if (name) {
    checkCanApprove({ name }).then(res => {
      canApprove.value = !!res?.canApprove
    }).catch(() => {})
  }
})

// 考勤记录
const records = ref([])

// 加载考勤记录
const loadAttendanceRecords = async () => {
  try {
    // 从 localStorage 获取当前登录用户信息
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
    
    console.log('正在加载考勤记录，用户信息:', userInfo)
    
    if (!userInfo.name || !userInfo.dept) {
      console.error('用户信息不完整')
      return
    }
    
    // 使用选定的月份
    const [year, month] = selectedMonth.value.split('-')
    const startDate = `${year}-${month}-01`
    
    // 计算当月最后一天
    const lastDay = new Date(parseInt(year), parseInt(month), 0).getDate()
    const endDate = `${year}-${month}-${String(lastDay).padStart(2, '0')}`
    
    console.log('查询日期范围:', startDate, '到', endDate)
    
    const response = await queryAttendance({
      name: userInfo.name,
      dept: userInfo.dept,
      start_date: startDate,
      end_date: endDate
    })
    
    console.log('后端返回数据:', response)
    
    if (response.success && response.data) {
      // 直接使用后端返回的数据，只添加id
      records.value = response.data.map((record, index) => ({
        id: index + 1,
        ...record
      }))
      console.log('加载了', records.value.length, '条考勤记录')
    } else {
      console.error('查询失败:', response.message)
    }
  } catch (error) {
    console.error('加载考勤记录失败:', error)
  }
}

// 月份改变时重新加载数据
const handleMonthChange = () => {
  console.log('选择的月份:', selectedMonth.value)
  loadSuggestions()
  loadAttendanceRecords()
}

// 监听月份变化，确保切换月份或打开界面时都会重新拉取智能建议（含“是否已处理”校验）
watch(selectedMonth, () => {
  if (selectedMonth.value && selectedMonth.value.includes('-')) {
    loadSuggestions()
    loadAttendanceRecords()
  }
}, { immediate: false })
</script>

<style scoped>
.attendance-page {
  min-height: 100vh;
  background: var(--color-bg-layout);
  padding-bottom: var(--spacing-xxl);
}

.header-bar-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 头部操作区 */
.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-base);
}

/* 月份选择器 */
.month-selector {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.month-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
}

.month-input {
  min-width: 150px;
  padding: var(--spacing-sm) var(--spacing-base);
  cursor: pointer;
}

.btn-header-link {
  display: inline-flex;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-primary);
  background: transparent;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-sm);
  text-decoration: none;
  transition: all 0.2s ease;
}
.btn-header-link:hover {
  background: var(--color-primary-lightest, #eff6ff);
}
.header-btn-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
}
.header-btn-hint {
  margin: 0;
  font-size: 11px;
  color: var(--color-text-tertiary, #9ca3af);
  line-height: 1.2;
  white-space: nowrap;
}

.manual-entry-hint {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-tertiary, #6b7280);
  line-height: 1.3;
}

/* 筛选面板 */
.filter-panel {
  padding: var(--spacing-xl);
  border: 1px solid var(--color-border-lighter);
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-base);
}

.filter-title {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.filter-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-base);
}

.filter-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-base);
}

.filter-item {
  display: flex;
  flex-direction: column;
}

.filter-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-xs);
  font-weight: var(--font-weight-medium);
}

.filter-actions {
  display: flex;
  gap: var(--spacing-sm);
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--color-border-lighter);
}

/* 智能建议 */
.suggestions-section {
  padding: var(--spacing-xl);
  background: var(--color-bg-container);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-lighter);
}

/* 公出申请弹窗样式（与公出管理页保持一致） */
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
  width: 800px;
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

.form-group.full {
  flex: 1 1 100%;
  min-width: 0;
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

.form-group input[readonly] {
  background-color: var(--color-bg-layout);
  cursor: not-allowed;
}

.form-actions {
  margin-top: var(--spacing-xl);
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
}

.suggestions-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.icon-md {
  width: 20px;
  height: 20px;
}

.suggestions-hint {
  font-style: italic;
}

.suggestions-grid {
  display: grid;
  gap: var(--spacing-base);
}

.suggestion-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-base);
  padding: var(--spacing-base);
  border-radius: var(--radius-base);
  border-left: 3px solid;
  transition: all var(--transition-base) var(--transition-ease);
}

/* 缺勤建议：淡红配色，与「正在审核」橙区分 */
.suggestion-warning {
  background: #ffebee;
  border-left-color: #e57373;
}

.suggestion-info {
  background: var(--color-info-bg);
  border-left-color: var(--color-info);
}

/* 已处理完成的建议卡 - 整卡淡绿底 */
.suggestion-card.suggestion-handled {
  background: #e8f5e9;
  border-left-color: #4caf50;
}

/* 正在审核的建议卡 - 整卡淡橙底 */
.suggestion-card.suggestion-under-review {
  background: #fff3e0;
  border-left-color: #ff9800;
}

.suggestion-card:hover {
  box-shadow: var(--shadow-card);
  transform: translateX(4px);
}

.suggestion-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-base);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.suggestion-warning .suggestion-icon {
  background: white;
  color: #c62828;
}

.suggestion-info .suggestion-icon {
  background: white;
  color: var(--color-info);
}

.suggestion-icon svg {
  width: 20px;
  height: 20px;
}

.suggestion-content {
  flex: 1;
}

.suggestion-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.suggestion-date {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-family-code);
}

.suggestion-badge {
  font-size: var(--font-size-xs);
  padding: 2px var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-weight: var(--font-weight-medium);
}

.badge-warning {
  background: var(--color-warning);
  color: white;
}

.suggestion-warning .badge-warning {
  background: #c62828;
  color: white;
}

.badge-info {
  background: var(--color-info);
  color: white;
}

.suggestion-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
}

.suggestion-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
}

/* 自动填报按钮 */
.auto-fill-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  color: white;
  border: none;
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  flex-shrink: 0;
}

/* 加班填报按钮 - 紫色渐变 */
.btn-overtime {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.btn-overtime:hover {
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  transform: translateY(-2px);
}

/* 请假填报按钮 - 黄橙渐变 */
.btn-leave {
  background: linear-gradient(135deg, #f7b733 0%, #fc8c1a 100%);
}

.btn-leave:hover {
  box-shadow: 0 4px 12px rgba(247, 183, 51, 0.4);
  transform: translateY(-2px);
}

/* 公出填报按钮 - 蓝色渐变 */
.btn-business-trip {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.btn-business-trip:hover {
  box-shadow: 0 4px 12px rgba(79, 172, 254, 0.4);
  transform: translateY(-2px);
}

/* 已处理完成 - 绿色 */
.auto-fill-btn.btn-handled {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  color: #fff;
  cursor: default;
}
.auto-fill-btn.btn-handled:hover {
  box-shadow: none;
  transform: none;
}

/* 正在审核 - 淡橙色 */
.auto-fill-btn.btn-under-review {
  background: linear-gradient(135deg, #f57c00 0%, #ffb74d 100%);
  color: #fff;
  cursor: default;
}
.auto-fill-btn.btn-under-review:hover {
  box-shadow: none;
  transform: none;
}
.auto-fill-btn:disabled {
  cursor: default;
  opacity: 1;
}

.auto-fill-btn:active {
  transform: translateY(0);
}

.auto-fill-btn .btn-icon {
  width: 16px;
  height: 16px;
}

/* 按钮组 - 用于缺勤建议的多个按钮 */
.button-group {
  display: flex;
  gap: var(--spacing-sm, 8px);
  flex-shrink: 0;
}

/* 统计卡片 */
.stat-mini-card {
  padding: var(--spacing-lg);
  border: 1px solid var(--color-border-lighter);
  text-align: center;
  transition: all var(--transition-base) var(--transition-ease);
}

.stat-mini-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-card-hover);
}

.stat-mini-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-sm);
}

.stat-mini-value {
  font-size: var(--font-size-xxl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

/* 表格容器 */
.table-container {
  padding: 0;
  border: 1px solid var(--color-border-lighter);
  overflow: hidden;
}

.table-header {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
  background: var(--color-bg-spotlight);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.table-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.table-toolbar {
  display: flex;
  align-items: center;
  gap: var(--spacing-xl);
}

.table-actions {
  display: flex;
  gap: var(--spacing-sm);
}

.table-wrapper {
  overflow-x: auto;
}

/* 数据表格 */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}

.data-table thead {
  background: var(--color-bg-spotlight);
}

.data-table th {
  padding: var(--spacing-base) var(--spacing-base);
  text-align: left;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border-lighter);
  white-space: nowrap;
}

.data-table td {
  padding: var(--spacing-base);
  border-bottom: 1px solid var(--color-border-lighter);
  color: var(--color-text-primary);
}

.data-table tbody tr {
  transition: background-color var(--transition-base) var(--transition-ease);
}

.data-table tbody tr:hover {
  background-color: var(--color-bg-spotlight);
}

.table-date {
  font-family: var(--font-family-code);
  color: var(--color-text-secondary);
}

.table-code {
  font-family: var(--font-family-code);
  font-weight: var(--font-weight-medium);
  color: var(--color-primary);
}

.employee-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.employee-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-circle);
  background: var(--color-primary-lightest);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-sm);
}

.employee-name {
  font-weight: var(--font-weight-medium);
}

.time-badge {
  font-family: var(--font-family-code);
  font-size: var(--font-size-xs);
  padding: 4px var(--spacing-sm);
  border-radius: var(--radius-sm);
  background: var(--color-bg-spotlight);
  color: var(--color-text-primary);
}

.time-badge.late {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.time-badge.early {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.time-badge.missing {
  background: var(--color-error-bg);
  color: var(--color-error);
}

.text-center {
  text-align: center;
  padding: var(--spacing-xl);
}

.table-actions-cell {
  display: flex;
  gap: var(--spacing-xs);
}

/* 响应式 */
@media (max-width: 768px) {
  .filter-row {
    grid-template-columns: 1fr;
  }
  
  .header-bar-content {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-base);
  }
  
  .header-actions {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }
  
  .month-selector {
    width: 100%;
    justify-content: space-between;
  }
  
  .month-input {
    flex: 1;
  }
  
  .btn-primary {
    width: 100%;
    justify-content: center;
  }
  
  .table-wrapper {
    overflow-x: scroll;
  }
  
  .data-table {
    min-width: 1200px;
  }
}
</style>
