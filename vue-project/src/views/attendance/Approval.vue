<template>
  <div class="page-container">
    <div class="page-header">
      <h1>考勤审批</h1>
    </div>

    <template v-if="!canApprove">
      <div class="no-permission card">
        <p>您暂无审批权限（员工无审批功能）</p>
      </div>
    </template>

    <template v-else>
      <div class="approval-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="approval-tab"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
          <span class="approval-tab__badge" v-if="pendingCount(tab.key)">{{ pendingCount(tab.key) }}</span>
        </button>
      </div>

      <!-- 请假审批 -->
      <section v-show="activeTab === 'leave'" class="approval-section card">
        <div class="card-body">
          <div class="batch-actions" v-if="leaveList.length">
            <label class="checkbox-label">
              <input type="checkbox" :checked="leaveSelectedAll" @change="toggleLeaveSelectAll">
              全选
            </label>
            <button type="button" class="btn btn-approve" @click="batchApprove('leave')" :disabled="!selectedLeaveIds.length">
              批量通过 ({{ selectedLeaveIds.length }})
            </button>
          </div>
          <div class="table-wrap" v-if="leaveList.length">
            <table class="approval-table">
              <thead>
                <tr>
                  <th width="40"><input type="checkbox" :checked="leaveSelectedAll" @change="toggleLeaveSelectAll"></th>
                  <th>申请人</th>
                  <th>请假类型</th>
                  <th>开始时间</th>
                  <th>结束时间</th>
                  <th>时长(天)</th>
                  <th>申请时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in leaveList" :key="item.id">
                  <td><input type="checkbox" :value="item.id" v-model="selectedLeaveIds"></td>
                  <td>{{ item.applicant }}</td>
                  <td>{{ item.type }}</td>
                  <td>{{ item.startTime }}</td>
                  <td>{{ item.endTime }}</td>
                  <td>{{ item.duration }}</td>
                  <td>{{ item.applyTime }}</td>
                  <td class="approval-actions">
                    <button type="button" class="btn btn-link" @click="showDetail('leave', item)">查看</button>
                    <button type="button" class="btn btn-approve" @click="handleApprove('leave', item)">通过</button>
                    <button type="button" class="btn btn-reject" @click="openRejectModal('leave', item)">驳回</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="empty-text" v-else>暂无待审批的请假申请</p>
        </div>
      </section>

      <!-- 加班审批 -->
      <section v-show="activeTab === 'overtime'" class="approval-section card">
        <div class="card-body">
          <div class="batch-actions" v-if="overtimeList.length">
            <label class="checkbox-label">
              <input type="checkbox" :checked="overtimeSelectedAll" @change="toggleOvertimeSelectAll">
              全选
            </label>
            <button type="button" class="btn btn-approve" @click="batchApprove('overtime')" :disabled="!selectedOvertimeIds.length">
              批量通过 ({{ selectedOvertimeIds.length }})
            </button>
            <button type="button" class="btn btn-validate" @click="runOvertimeValidate" :disabled="overtimeValidateLoading">
              {{ overtimeValidateLoading ? '校验中…' : '智能校验' }}
            </button>
            <button type="button" class="btn btn-secondary" @click="selectOvertimeValidated">
              全选校验通过的审批
            </button>
          </div>
          <div class="table-wrap" v-if="overtimeList.length">
            <table class="approval-table">
              <thead>
                <tr>
                  <th width="40"><input type="checkbox" :checked="overtimeSelectedAll" @change="toggleOvertimeSelectAll"></th>
                  <th>申请人</th>
                  <th>级别</th>
                  <th>加班日期</th>
                  <th>开始-结束时间</th>
                  <th>时长(小时)</th>
                  <th>换休票</th>
                  <th>申请时间</th>
                  <th>校验通过</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in overtimeList" :key="item.id">
                  <td><input type="checkbox" :value="item.id" v-model="selectedOvertimeIds"></td>
                  <td>{{ item.applicant }}</td>
                  <td>{{ item.level }}</td>
                  <td>{{ item.date }}</td>
                  <td>{{ item.startTime }} - {{ item.endTime }}</td>
                  <td>{{ item.hours }}</td>
                  <td>{{ item.needExchangeTicket || '否' }}</td>
                  <td>{{ item.applyTime }}</td>
                  <td class="validation-cell">
                    <span v-if="overtimeValidation[item.id] === undefined" class="validation-empty">—</span>
                    <template v-else>
                      <span class="validation-box" :class="{ 'validation-pass': overtimeValidation[item.id].pass, 'validation-fail': !overtimeValidation[item.id].pass }">
                        <span v-if="overtimeValidation[item.id].pass" class="validation-check">✓</span>
                        <span v-else class="validation-cross">✗</span>
                      </span>
                      <span v-if="!overtimeValidation[item.id].pass && overtimeValidation[item.id].reason" class="validation-reason">{{ overtimeValidation[item.id].reason }}</span>
                    </template>
                  </td>
                  <td class="approval-actions">
                    <button type="button" class="btn btn-link" @click="showDetail('overtime', item)">查看</button>
                    <button type="button" class="btn btn-approve" @click="handleApprove('overtime', item)">通过</button>
                    <button type="button" class="btn btn-reject" @click="openRejectModal('overtime', item)">驳回</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="empty-text" v-else>暂无待审批的加班申请</p>
        </div>
      </section>

      <!-- 公出审批 -->
      <section v-show="activeTab === 'business-trip'" class="approval-section card">
        <div class="card-body">
          <div class="batch-actions" v-if="businessTripList.length">
            <label class="checkbox-label">
              <input type="checkbox" :checked="businessTripSelectedAll" @change="toggleBusinessTripSelectAll">
              全选
            </label>
            <button type="button" class="btn btn-approve" @click="batchApprove('business-trip')" :disabled="!selectedBusinessTripIds.length">
              批量通过 ({{ selectedBusinessTripIds.length }})
            </button>
          </div>
          <div class="table-wrap" v-if="businessTripList.length">
            <table class="approval-table">
              <thead>
                <tr>
                  <th width="40"><input type="checkbox" :checked="businessTripSelectedAll" @change="toggleBusinessTripSelectAll"></th>
                  <th>申请人</th>
                  <th>委派单位</th>
                  <th>公出地点</th>
                  <th>出发-返回时间</th>
                  <th>当前审批</th>
                  <th>申请时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in businessTripList" :key="item.id">
                  <td><input type="checkbox" :value="item.id" v-model="selectedBusinessTripIds"></td>
                  <td>{{ item.applicant }}</td>
                  <td>{{ item.targetUnit }}</td>
                  <td>{{ item.location }}</td>
                  <td>{{ item.startTime }} 至 {{ item.endTime }}</td>
                  <td>{{ item.approvalLevel }}</td>
                  <td>{{ item.applyTime }}</td>
                  <td class="approval-actions">
                    <button type="button" class="btn btn-link" @click="showDetail('business-trip', item)">查看</button>
                    <button type="button" class="btn btn-approve" @click="handleApprove('business-trip', item)">通过</button>
                    <button type="button" class="btn btn-reject" @click="openRejectModal('business-trip', item)">驳回</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="empty-text" v-else>暂无待审批的公出申请</p>
        </div>
      </section>

      <!-- 详情弹窗 -->
      <div v-if="detailVisible" class="modal-overlay" @click.self="detailVisible = false">
        <div class="modal-content detail-modal">
          <div class="modal-header">
            <h3>{{ detailTitle }}</h3>
            <button type="button" class="close-btn" @click="detailVisible = false">&times;</button>
          </div>
          <div class="modal-body" v-if="detailData">
            <template v-if="detailType === 'leave'">
              <p><strong>申请人：</strong>{{ detailData.applicant }}</p>
              <p><strong>请假类型：</strong>{{ detailData.type }}</p>
              <p><strong>班组：</strong>{{ detailData.department }}</p>
              <p><strong>班次：</strong>{{ detailData.shift }}</p>
              <p><strong>联系方式：</strong>{{ detailData.contactMethod || '-' }}</p>
              <p><strong>开始时间：</strong>{{ detailData.startTime }}</p>
              <p><strong>结束时间：</strong>{{ detailData.endTime }}</p>
              <p><strong>时长：</strong>{{ detailData.duration }} 天</p>
              <p><strong>事由：</strong>{{ detailData.reason }}</p>
              <p><strong>说明材料：</strong>{{ detailData.material || '-' }}</p>
              <p v-if="detailData.materialFile">
                <strong>材料文件：</strong>
                <a :href="materialFileDownloadUrl" target="_blank" rel="noopener" class="download-link">下载</a>
              </p>
              <p><strong>申请时间：</strong>{{ detailData.applyTime }}</p>
              <p><strong>第一审批人：</strong>{{ detailData.spr }}</p>
              <p><strong>第二审批人：</strong>{{ detailData.spr2 || '-' }}</p>
            </template>
            <template v-else-if="detailType === 'overtime'">
              <p><strong>申请人：</strong>{{ detailData.applicant }}</p>
              <p><strong>级别：</strong>{{ detailData.level }}</p>
              <p><strong>部门：</strong>{{ detailData.department || '-' }}</p>
              <p><strong>加班日期：</strong>{{ detailData.date }}</p>
              <p><strong>开始时间：</strong>{{ detailData.startTime }}</p>
              <p><strong>结束时间：</strong>{{ detailData.endTime }}</p>
              <p><strong>时长：</strong>{{ detailData.hours }} 小时</p>
              <p><strong>换休票：</strong>{{ detailData.needExchangeTicket || '否' }}</p>
              <p><strong>加班内容：</strong>{{ detailData.content || '-' }}</p>
              <p><strong>申请时间：</strong>{{ detailData.applyTime }}</p>
              <p><strong>审批人：</strong>{{ detailData.spr }}</p>
              <div class="detail-attendance-section">
                <p><strong>当日打卡记录：</strong></p>
                <p v-if="overtimeDetailAttendanceLoading" class="detail-attendance-loading">加载中…</p>
                <p v-else-if="!overtimeDetailAttendance.length" class="detail-attendance-empty">暂无该日打卡记录</p>
                <ul v-else class="detail-attendance-list">
                  <li v-for="(rec, idx) in overtimeDetailAttendance" :key="idx">
                    <span v-if="rec.attendance_date">{{ rec.attendance_date }}</span>
                    <span class="detail-attendance-times">
                      {{ formatAttendanceTimes(rec) }}
                    </span>
                  </li>
                </ul>
              </div>
            </template>
            <template v-else-if="detailType === 'business-trip'">
              <p><strong>申请人：</strong>{{ detailData.applicant }}</p>
              <p><strong>委派单位：</strong>{{ detailData.targetUnit }}</p>
              <p><strong>填报单位：</strong>{{ detailData.department }}</p>
              <p><strong>公出地点：</strong>{{ detailData.location }}</p>
              <p><strong>通知单编号：</strong>{{ detailData.noticeNo }}</p>
              <p><strong>项目名称：</strong>{{ detailData.projectName || '-' }}</p>
              <p><strong>出发时间：</strong>{{ detailData.startTime }}</p>
              <p><strong>预计返回时间：</strong>{{ detailData.endTime }}</p>
              <p><strong>公出任务：</strong>{{ detailData.task }}</p>
              <p><strong>联系电话：</strong>{{ detailData.phone }}</p>
              <p><strong>申请时间：</strong>{{ detailData.applyTime }}</p>
              <p><strong>部领导：</strong>{{ detailData.deptLeader }}</p>
              <p><strong>室主任：</strong>{{ detailData.roomDirector }}</p>
            </template>
          </div>
          <div class="modal-footer">
            <template v-if="(detailType === 'leave' || detailType === 'overtime') && detailData?.id">
              <button type="button" class="btn btn-approve" @click="handleApprove(detailType, detailData)">通过</button>
              <button type="button" class="btn btn-reject" @click="detailVisible = false; openRejectModal(detailType, detailData)">驳回</button>
            </template>
            <button type="button" class="btn btn-secondary" @click="detailVisible = false">关闭</button>
          </div>
        </div>
      </div>

      <!-- 驳回原因弹窗（单条/批量统一） -->
      <div v-if="rejectModalVisible" class="modal-overlay" @click.self="rejectModalVisible = false">
        <div class="modal-card modal-reject">
          <h3 class="modal-title">驳回原因</h3>
          <p class="modal-hint">请填写驳回原因，申请人将看到该原因。</p>
          <textarea
            v-model="rejectReasonInput"
            class="modal-textarea"
            placeholder="请输入驳回原因（必填）"
            rows="4"
          ></textarea>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="rejectModalVisible = false">取消</button>
            <button type="button" class="btn btn-reject" :disabled="!rejectReasonInput.trim()" @click="confirmReject">确认驳回</button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  checkCanApprove,
  getPendingLeave,
  getPendingOvertime,
  getPendingBusinessTrip,
  getLeaveDetail,
  getOvertimeDetail,
  getBusinessTripApprovalDetail,
  getLeaveMaterialDownloadUrl,
  leaveApproveAction,
  overtimeApproveAction,
  businessTripApproveAction,
  leaveBatchApprove,
  overtimeBatchApprove,
  businessTripBatchApprove,
  queryAttendance,
  validateOvertimeApproval
} from '@/api/attendance'

const route = useRoute()
const currentUser = (() => {
  const u = JSON.parse(localStorage.getItem('userInfo') || '{}')
  return u.name || u.userName || ''
})()

const canApprove = ref(true)
const tabs = [
  { key: 'leave', label: '请假审批' },
  { key: 'overtime', label: '加班审批' },
  { key: 'business-trip', label: '公出审批' }
]

const activeTab = ref('leave')
const leaveList = ref([])
const overtimeList = ref([])
const businessTripList = ref([])
const selectedLeaveIds = ref([])
const selectedOvertimeIds = ref([])
const selectedBusinessTripIds = ref([])
const detailVisible = ref(false)
const detailType = ref('leave')
const detailData = ref(null)
const rejectModalVisible = ref(false)
const rejectReasonInput = ref('')
const rejectTarget = ref(null)
const overtimeDetailAttendance = ref([])  // 加班详情：申请人当日的打卡记录
const overtimeDetailAttendanceLoading = ref(false)
const overtimeValidation = ref({})  // 加班智能校验结果 { [id]: { pass, reason? } }
const overtimeValidateLoading = ref(false)

const leaveSelectedAll = computed(() =>
  leaveList.value.length > 0 && selectedLeaveIds.value.length === leaveList.value.length
)
const overtimeSelectedAll = computed(() =>
  overtimeList.value.length > 0 && selectedOvertimeIds.value.length === overtimeList.value.length
)
const businessTripSelectedAll = computed(() =>
  businessTripList.value.length > 0 && selectedBusinessTripIds.value.length === businessTripList.value.length
)
const detailTitle = computed(() => {
  if (detailType.value === 'leave') return '请假详情'
  if (detailType.value === 'overtime') return '加班详情'
  if (detailType.value === 'business-trip') return '公出详情'
  return '详情'
})
const materialFileDownloadUrl = computed(() => {
  const fn = detailData.value?.materialFile
  return fn ? getLeaveMaterialDownloadUrl(fn) : ''
})

onMounted(() => {
  const type = route.query.type
  if (type === 'leave' || type === 'overtime' || type === 'business-trip') {
    activeTab.value = type
  }
  init()
})

watch(activeTab, () => {
  selectedLeaveIds.value = []
  selectedOvertimeIds.value = []
  selectedBusinessTripIds.value = []
})

async function init() {
  if (!currentUser) return
  const res = await checkCanApprove({ name: currentUser })
  canApprove.value = res.canApprove
  if (res.canApprove) {
    fetchLeaveList()
    fetchOvertimeList()
    fetchBusinessTripList()
  }
}

async function fetchLeaveList() {
  try {
    const res = await getPendingLeave({ approver: currentUser })
    leaveList.value = (res.data || []).map(r => ({ ...r, applicant: r.applicant || r.xm }))
  } catch {
    leaveList.value = []
  }
}

async function fetchOvertimeList() {
  try {
    const res = await getPendingOvertime({ approver: currentUser })
    overtimeList.value = res.data || []
  } catch {
    overtimeList.value = []
  }
}

async function fetchBusinessTripList() {
  try {
    const res = await getPendingBusinessTrip({ approver: currentUser })
    businessTripList.value = res.data || []
  } catch {
    businessTripList.value = []
  }
}

function pendingCount(key) {
  if (key === 'leave') return leaveList.value.length
  if (key === 'overtime') return overtimeList.value.length
  if (key === 'business-trip') return businessTripList.value.length
  return 0
}

function toggleLeaveSelectAll() {
  selectedLeaveIds.value = leaveSelectedAll.value ? [] : leaveList.value.map(r => r.id)
}
function toggleOvertimeSelectAll() {
  selectedOvertimeIds.value = overtimeSelectedAll.value ? [] : overtimeList.value.map(r => r.id)
}
function toggleBusinessTripSelectAll() {
  selectedBusinessTripIds.value = businessTripSelectedAll.value ? [] : businessTripList.value.map(r => r.id)
}

async function showDetail(type, item) {
  detailType.value = type
  overtimeDetailAttendance.value = []
  try {
    let res
    if (type === 'leave') res = await getLeaveDetail(item.id)
    else if (type === 'overtime') res = await getOvertimeDetail(item.id)
    else res = await getBusinessTripApprovalDetail(item.id)
    detailData.value = res.data || item
  } catch {
    detailData.value = item
  }
  detailVisible.value = true
  if (type === 'overtime' && detailData.value?.applicant && detailData.value?.date) {
    fetchOvertimeDetailAttendance()
  }
}

function selectOvertimeValidated() {
  const passedIds = overtimeList.value
    .filter(it => overtimeValidation.value[it.id]?.pass === true)
    .map(it => it.id)
  const current = selectedOvertimeIds.value
  const isAlreadySelected =
    passedIds.length === current.length &&
    passedIds.every((id) => current.includes(id))
  selectedOvertimeIds.value = isAlreadySelected ? [] : passedIds
}

async function runOvertimeValidate() {
  if (!overtimeList.value.length) return
  overtimeValidateLoading.value = true
  overtimeValidation.value = {}
  try {
    const items = overtimeList.value.map(it => ({
      id: it.id,
      applicant: it.applicant,
      date: String(it.date || '').slice(0, 10),
      startTime: it.startTime || '',
      endTime: it.endTime || ''
    }))
    const res = await validateOvertimeApproval({ items })
    const map = {}
    ;(res.results || []).forEach(r => {
      map[r.id] = { pass: !!r.pass, reason: r.reason || null }
    })
    overtimeValidation.value = map
  } catch (e) {
    alert(e.response?.data?.detail || e.message || '校验请求失败')
  } finally {
    overtimeValidateLoading.value = false
  }
}

async function fetchOvertimeDetailAttendance() {
  const d = detailData.value
  if (!d?.applicant || !d?.date) return
  const dateStr = String(d.date).trim().slice(0, 10)
  if (!dateStr) return
  overtimeDetailAttendanceLoading.value = true
  try {
    const res = await queryAttendance({
      name: d.applicant,
      start_date: dateStr,
      end_date: dateStr
    })
    overtimeDetailAttendance.value = (res.data || []).filter(Boolean)
  } catch {
    overtimeDetailAttendance.value = []
  } finally {
    overtimeDetailAttendanceLoading.value = false
  }
}

function formatAttendanceTimes(rec) {
  const times = []
  for (let i = 1; i <= 10; i++) {
    const t = rec[`time_${i}`]
    if (t != null && String(t).trim()) times.push(String(t).trim())
  }
  return times.length ? times.join('、') : '—'
}

async function handleApprove(type, item) {
  const typeName = type === 'leave' ? '请假' : type === 'overtime' ? '加班' : '公出'
  if (!confirm(`确认通过该${typeName}申请？`)) return
  try {
    const fn = type === 'leave' ? leaveApproveAction : type === 'overtime' ? overtimeApproveAction : businessTripApproveAction
    await fn(item.id, { action: 'approve' })
    alert('已通过')
    detailVisible.value = false
    refreshList(type)
  } catch (e) {
    alert(e.response?.data?.detail || '操作失败')
  }
}

function openRejectModal(type, item) {
  const id = item?.id
  if (!id) {
    alert('无法获取申请单号，请刷新后重试')
    return
  }
  rejectTarget.value = { type, item, batch: false, id: String(id) }
  rejectReasonInput.value = ''
  rejectModalVisible.value = true
}

function openBatchRejectModal(type) {
  const ids = type === 'leave' ? selectedLeaveIds.value : type === 'overtime' ? selectedOvertimeIds.value : selectedBusinessTripIds.value
  if (!ids.length) return
  rejectTarget.value = { type, ids, batch: true }
  rejectReasonInput.value = ''
  rejectModalVisible.value = true
}

async function confirmReject() {
  const reason = (rejectReasonInput.value || '').trim()
  if (!reason) return
  const target = rejectTarget.value
  if (!target) return
  const { type, batch } = target
  if (batch && !confirm(`确认批量驳回选中的 ${target.ids.length} 条申请？`)) return
  const id = !batch && (target.id ?? target.item?.id)
  if (!batch && !id) {
    alert('无法获取申请单号，请关闭弹窗后重试')
    return
  }
  try {
    if (batch) {
      const fn = type === 'leave' ? leaveBatchApprove : type === 'overtime' ? overtimeBatchApprove : businessTripBatchApprove
      await fn({ ids: target.ids, action: 'reject', reason })
      selectedLeaveIds.value = []
      selectedOvertimeIds.value = []
      selectedBusinessTripIds.value = []
    } else {
      const fn = type === 'leave' ? leaveApproveAction : type === 'overtime' ? overtimeApproveAction : businessTripApproveAction
      await fn(id, { action: 'reject', reason })
      detailVisible.value = false
    }
    rejectModalVisible.value = false
    rejectTarget.value = null
    await refreshList(type)
    alert('已驳回')
  } catch (e) {
    const msg = e.response?.data?.detail ?? e.message ?? '操作失败'
    alert(typeof msg === 'string' ? msg : JSON.stringify(msg))
  }
}

async function refreshList(type) {
  if (type === 'leave') await fetchLeaveList()
  else if (type === 'overtime') await fetchOvertimeList()
  else await fetchBusinessTripList()
}

async function batchApprove(type) {
  const ids = type === 'leave' ? selectedLeaveIds.value : type === 'overtime' ? selectedOvertimeIds.value : selectedBusinessTripIds.value
  if (!ids.length) return
  const typeName = type === 'leave' ? '请假' : type === 'overtime' ? '加班' : '公出'
  if (!confirm(`确认批量通过选中的 ${ids.length} 条${typeName}申请？`)) return
  try {
    const fn = type === 'leave' ? leaveBatchApprove : type === 'overtime' ? overtimeBatchApprove : businessTripBatchApprove
    const res = await fn({ ids, action: 'approve' })
    alert(res.message || '操作完成')
    selectedLeaveIds.value = []
    selectedOvertimeIds.value = []
    selectedBusinessTripIds.value = []
    refreshList(type)
  } catch (e) {
    alert(e.response?.data?.detail || '操作失败')
  }
}

// 批量驳回已改为 openBatchRejectModal + confirmReject
</script>

<style scoped>
.page-container {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0 0 var(--spacing-xl);
}

.page-header {
  margin-bottom: var(--spacing-xl);
}

.page-header h1 {
  margin: 0;
  font-size: var(--font-size-xxl);
  font-weight: 600;
  color: var(--color-text-primary);
}

.no-permission {
  padding: var(--spacing-xxl);
  text-align: center;
  color: var(--color-text-secondary);
}

.approval-tabs {
  display: flex;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
}

.approval-tab {
  padding: var(--spacing-md) var(--spacing-lg);
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  background: none;
  border: none;
  border-bottom: 3px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.approval-tab:hover {
  color: var(--color-primary);
}

.approval-tab.active {
  color: var(--color-primary);
  font-weight: 500;
  border-bottom-color: var(--color-primary);
}

.approval-tab__badge {
  padding: 2px 8px;
  font-size: var(--font-size-xs);
  background: var(--color-error);
  color: white;
  border-radius: 999px;
}

.approval-section {
  background: white;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-lighter);
}

.approval-section .card-body {
  padding: var(--spacing-lg);
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  cursor: pointer;
  font-size: var(--font-size-sm);
}

.btn-batch {
  padding: 6px 14px;
  font-size: var(--font-size-sm);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-base);
  background: white;
  cursor: pointer;
}

.btn-batch:not(:disabled):hover {
  background: var(--color-bg-spotlight);
}

.btn-batch:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.table-wrap {
  overflow-x: auto;
}

.approval-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}

.approval-table th,
.approval-table td {
  padding: 12px var(--spacing-lg);
  text-align: left;
  border-bottom: 1px solid var(--color-border-lighter);
}

.approval-table th {
  font-weight: 600;
  color: var(--color-text-primary);
  background: var(--color-bg-layout);
}

.approval-table tbody tr:hover {
  background: var(--color-bg-spotlight);
}

.approval-actions {
  display: flex;
  gap: var(--spacing-sm);
}

.validation-cell {
  vertical-align: top;
  white-space: nowrap;
}
.validation-cell .validation-box {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: 1px solid var(--color-border);
  border-radius: 3px;
  font-size: 14px;
  line-height: 1;
}
.validation-cell .validation-pass {
  border-color: #10b981;
  background: #d1fae5;
  color: #059669;
}
.validation-cell .validation-fail {
  border-color: #f59e0b;
  background: #fef3c7;
  color: #d97706;
}
.validation-cell .validation-check { font-weight: bold; }
.validation-cell .validation-cross { font-weight: bold; }
.validation-cell .validation-reason {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: var(--color-text-secondary);
  white-space: normal;
  max-width: 90px;
}
.validation-cell .validation-empty {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.btn-link {
  padding: 6px 10px;
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  background: none;
  border: none;
  cursor: pointer;
}

.btn-link:hover {
  text-decoration: underline;
}

.btn-approve {
  padding: 6px 14px;
  font-size: var(--font-size-sm);
  color: #059669;
  background: #d1fae5;
  border: 1px solid #10b981;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.btn-approve:hover:not(:disabled) {
  background: #a7f3d0;
}

.btn-approve:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 智能校验：蓝色主按钮风格，与批量通过同结构 */
.btn-validate {
  padding: 6px 14px;
  font-size: var(--font-size-sm);
  color: #2563eb;
  background: #dbeafe;
  border: 1px solid #3b82f6;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.btn-validate:hover:not(:disabled) {
  background: #bfdbfe;
}
.btn-validate:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-reject {
  padding: 6px 14px;
  font-size: var(--font-size-sm);
  color: #dc2626;
  background: #fee2e2;
  border: 1px solid #ef4444;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.btn-reject:hover {
  background: #fecaca;
}

.btn-reject:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.modal-reject {
  background: white;
  border-radius: var(--radius-md);
  width: 420px;
  max-width: 95%;
  padding: var(--spacing-xl);
}
.modal-reject .modal-title {
  margin: 0 0 var(--spacing-sm);
  font-size: 1.1rem;
}
.modal-reject .modal-hint {
  margin: 0 0 var(--spacing-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
.modal-reject .modal-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  resize: vertical;
  margin-bottom: var(--spacing-lg);
  box-sizing: border-box;
}
.modal-reject .modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
}

.empty-text {
  text-align: center;
  color: var(--color-text-secondary);
  padding: var(--spacing-xxl) 0;
  margin: 0;
}

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

.detail-modal {
  background: white;
  border-radius: var(--radius-md);
  width: 500px;
  max-width: 95%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-lighter);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--color-text-secondary);
}

.modal-body {
  padding: var(--spacing-lg);
  overflow-y: auto;
}

.modal-body p {
  margin: 0 0 var(--spacing-sm);
  font-size: var(--font-size-sm);
}

.detail-attendance-section {
  margin-top: var(--spacing-md);
  padding: var(--spacing-md);
  border-radius: var(--radius-sm);
  background: rgba(22, 119, 255, 0.08);
  border-left: 4px solid var(--color-primary, #1677ff);
}
.detail-attendance-section p:first-child {
  margin-bottom: var(--spacing-xs);
  color: var(--color-primary, #1677ff);
  font-weight: 600;
}
.detail-attendance-loading,
.detail-attendance-empty {
  color: var(--color-text-secondary);
  margin: 0;
  font-size: var(--font-size-sm);
}
.detail-attendance-list {
  margin: 0;
  padding-left: 1.2em;
  font-size: var(--font-size-sm);
}
.detail-attendance-list li {
  margin-bottom: var(--spacing-xs);
}
.detail-attendance-times {
  margin-left: 0.25em;
  font-weight: 500;
  color: var(--color-text-primary);
}

.download-link {
  color: var(--color-primary);
  text-decoration: underline;
}

.download-link:hover {
  color: var(--color-primary-light);
}

.modal-footer {
  padding: var(--spacing-lg);
  border-top: 1px solid var(--color-border-lighter);
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-md);
  align-items: center;
}

.btn-secondary {
  padding: 8px 20px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  background: white;
  cursor: pointer;
}
</style>
