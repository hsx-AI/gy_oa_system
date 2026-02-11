<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">公出管理</h1>
          <p class="header-subtitle">公出登记、返回登记与审批</p>
        </div>
        <div class="header-actions">
          <button
            v-if="canApprove"
            class="btn btn-outline"
            @click="$router.push({ path: '/attendance/approvals', query: { type: 'business-trip' } })"
          >
            审批
          </button>
          <button class="btn btn-primary" @click="showApplyModal = true">公出登记</button>
          <button class="btn btn-primary" @click="openReturnModal">返回登记</button>
        </div>
      </div>
    </div>

    <!-- 公出记录 -->
    <div class="content mt-xl">
      <div class="card record-card">
        <div class="card-header record-card__header">
          <div>
            <h3>公出记录</h3>
            <p class="record-card__desc">{{ recordFilterLabel }}</p>
          </div>
          <div class="record-card__filters">
            <label class="filter-label">筛选：</label>
            <select v-model.number="recordYear" class="filter-select">
              <option v-for="y in recordYearOptions" :key="y" :value="y">{{ y }}年</option>
            </select>
            <span class="filter-text">全年</span>
            <select v-model="recordStatusFilter" class="filter-select">
              <option value="">全部</option>
              <option value="已通过">已通过</option>
              <option value="processing_rejected">审批中/已驳回</option>
            </select>
          </div>
        </div>
        <div class="card-body record-card__body">
          <div class="table-wrap" v-if="filteredRecordList.length">
            <table class="record-table">
              <thead>
                <tr>
                  <th>委派单位</th>
                  <th>公出人</th>
                  <th>委派时间</th>
                  <th>项目名称</th>
                  <th>公出地点</th>
                  <th>出发时间</th>
                  <th>实际返回时间</th>
                  <th>审批状态</th>
                  <th>当前审批人</th>
                  <th>驳回原因</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in recordDisplayList" :key="r.id" :data-record-id="r.id">
                  <td>{{ r.targetUnit }}</td>
                  <td>{{ r.person }}</td>
                  <td>{{ r.assignTime }}</td>
                  <td>{{ r.projectName }}</td>
                  <td>{{ r.location }}</td>
                  <td>{{ r.startTime || '—' }}</td>
                  <td>{{ r.actualReturnTime ? r.actualReturnTime.replace('T', ' ').slice(0, 16) : '—' }}</td>
                  <td><span class="status-tag" :class="r.statusClass || 'status-processing'">{{ r.status || '审批中' }}</span></td>
                  <td>{{ r.status === '审批中' && r.currentApprover ? r.currentApprover : '—' }}</td>
                  <td class="reject-reason-cell">{{ r.status === '已驳回' && r.rejectReason ? r.rejectReason : '—' }}</td>
                  <td>
                    <button v-if="r.status === '已驳回'" type="button" class="btn btn-sm btn-danger" @click="deleteRejectedBusinessTrip(r)">删除</button>
                    <span v-else>—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <!-- 分页 -->
          <div class="record-pagination" v-if="filteredRecordList.length">
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
              <button
                type="button"
                class="record-pagination__btn"
                :disabled="recordPage <= 1"
                @click="recordPage = Math.max(1, recordPage - 1)"
              >
                上一页
              </button>
              <span class="record-pagination__num">
                第 {{ recordPage }} / {{ recordTotalPages || 1 }} 页
              </span>
              <button
                type="button"
                class="record-pagination__btn"
                :disabled="recordPage >= recordTotalPages"
                @click="recordPage = Math.min(recordTotalPages, recordPage + 1)"
              >
                下一页
              </button>
            </div>
          </div>
          <p class="empty-text" v-else>{{ myRecordList.length ? '当前筛选条件下暂无记录' : '暂无公出记录' }}</p>
        </div>
      </div>
    </div>

    <!-- 公出登记弹窗 -->
    <div v-if="showApplyModal" class="modal-overlay" @click.self="showApplyModal = false">
      <div class="modal-content">
        <h2>公出登记</h2>
        <form name="business-trip-form" @submit.prevent="submitApplication" class="application-form" autocomplete="on">
          <!-- 基础信息 -->
          <div class="form-row">
            <div class="form-group half">
              <label>委派单位</label>
              <select v-model="form.targetUnit" name="targetUnit" autocomplete="on">
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
            <div class="form-group half">
              <label>委派时间 <span class="label-optional">（可选）</span></label>
              <input type="date" v-model="form.assignTime" name="assignTime" autocomplete="on" placeholder="选填">
            </div>
          </div>

          <div class="form-row">
            <div class="form-group half">
              <label>通知单编号 <span class="label-optional">（选填）</span></label>
              <input id="bt-noticeNo" type="text" v-model="form.noticeNo" name="noticeNo" autocomplete="on" placeholder="选填">
            </div>
            <div class="form-group half">
              <label>填报单位</label>
              <input type="text" v-model="form.department" readonly>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group half">
              <label>公出人员姓名</label>
              <input type="text" v-model="form.name" readonly>
            </div>
            <div class="form-group half">
              <label>本次公出总人数</label>
              <input type="number" v-model="form.totalPeople" name="totalPeople" autocomplete="on" min="1">
            </div>
          </div>

          <!-- 公出详情 -->
          <div class="form-row">
            <div class="form-group half">
              <label>工作号 <span class="label-optional">（选填）</span></label>
              <input id="bt-workNo" type="text" v-model="form.workNo" name="workNo" autocomplete="on" placeholder="选填">
            </div>
            <div class="form-group half">
              <label>项目名称 <span class="label-optional">（选填）</span></label>
              <input id="bt-projectName" type="text" v-model="form.projectName" name="projectName" autocomplete="on" placeholder="选填">
            </div>
          </div>

          <div class="form-row">
            <div class="form-group full">
              <label>公出地点</label>
              <input id="bt-location" type="text" v-model="form.location" name="location" autocomplete="street-address" placeholder="请输入公出地点">
            </div>
          </div>

          <!-- 时间与费用（仅选日期，不参与考勤统计） -->
          <div class="form-row">
            <div class="form-group half">
              <label>出发时间</label>
              <input type="date" v-model="form.startTime" name="btStartTime" autocomplete="on">
            </div>
            <div class="form-group half">
              <label>预计返回时间</label>
              <input type="date" v-model="form.endTime" name="btEndTime" autocomplete="on">
            </div>
          </div>

          <div class="form-row">
            <div class="form-group half">
              <label>请款金额 <span class="label-optional">（选填）</span></label>
              <input type="number" v-model="form.amount" name="amount" autocomplete="on" min="0" step="0.01" placeholder="选填">
            </div>
            <div class="form-group half">
              <label>联系电话</label>
              <input id="bt-phone" type="text" v-model="form.phone" name="btPhone" autocomplete="tel" placeholder="请输入联系电话">
            </div>
          </div>

          <div class="form-group">
            <label>公出任务</label>
            <textarea id="bt-task" v-model="form.task" name="btTask" autocomplete="on" rows="4" placeholder="请输入公出任务详情"></textarea>
          </div>

          <!-- 审批人 -->
          <div class="form-row">
            <div class="form-group half">
              <label>部领导</label>
              <select v-model="form.deptLeader" name="deptLeader" autocomplete="on" :disabled="loadingApprovers">
                <option value="">请选择部领导</option>
                <option v-for="person in deptLeaders" :key="person" :value="person">{{ person }}</option>
              </select>
            </div>
            <div class="form-group half">
              <label>室主任</label>
              <select v-model="form.responsiblePerson" name="roomDirector" autocomplete="on" :disabled="loadingApprovers">
                <option value="">请选择室主任</option>
                <option v-for="person in roomDirectors" :key="person" :value="person">{{ person }}</option>
              </select>
            </div>
          </div>

           <div class="form-group checkbox-group">
            <label class="checkbox-label text-danger">
              <input type="checkbox" v-model="form.confirmed">
              我确认已阅读并遵守《GYBG-047 智能制造工艺部公出人员管理办法》及公司相关规定。
            </label>
            <a :href="managementDocUrl" target="_blank" rel="noopener noreferrer" class="doc-link">点击阅读《GYBG-047 智能制造工艺部公出人员管理办法》</a>
          </div>

          <!-- 底部操作 -->
          <div class="form-actions">
            <button type="button" @click="showApplyModal = false">取消</button>
            <button type="submit" class="btn-primary">提交</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 公出返回登记弹窗 -->
    <div v-if="showReturnModal" class="modal-overlay" @click.self="showReturnModal = false">
      <div class="modal-content">
        <h2>公出返回登记</h2>
        <form
          name="business-trip-return-form"
          @submit.prevent="submitReturn"
          class="application-form"
          autocomplete="on"
        >
          <div class="form-row">
            <div class="form-group full">
              <label>选择已审批通过的公出记录</label>
              <select v-model="returnForm.recordId">
                <option value="">请选择公出记录</option>
                <option
                  v-for="r in returnCandidates"
                  :key="r.id"
                  :value="r.id"
                >
                  {{ r.assignTime || '无委派时间' }}｜{{ r.projectName || '无项目名称' }}｜{{ r.location || '无地点' }}
                </option>
              </select>
              <p class="hint-text">仅展示状态为“已通过”且未做返回登记的记录。</p>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group half">
              <label>实际出发时间</label>
              <input
                type="datetime-local"
                v-model="returnForm.actualStartTime"
                name="btActualStartTime"
                autocomplete="on"
              >
            </div>
            <div class="form-group half">
              <label>实际返回时间</label>
              <input
                type="datetime-local"
                v-model="returnForm.actualReturnTime"
                name="btActualReturnTime"
                autocomplete="on"
              >
            </div>
          </div>

          <div class="form-actions">
            <button type="button" @click="showReturnModal = false">取消</button>
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
import { getApprovers, submitBusinessTripApply, getBusinessTripList, updateBusinessTripReturnTime, checkCanApprove, deleteBusinessTripRecord } from '@/api/attendance'

const router = useRouter()
const route = useRoute()
const showApplyModal = ref(false)
const showReturnModal = ref(false)

// 部领导、室主任选项（从 API 按 yggl 规则获取）
const deptLeaders = ref([])
const roomDirectors = ref([])
const loadingApprovers = ref(false)

const fetchApprovers = async () => {
  if (!form.name) return
  loadingApprovers.value = true
  try {
    const [r1, r2] = await Promise.all([
      getApprovers({ name: form.name, level: 'dept_leader' }),
      getApprovers({ name: form.name, level: 'room_director' })
    ])
    deptLeaders.value = (r1.success && r1.approvers) ? r1.approvers.map(a => a.name) : []
    roomDirectors.value = (r2.success && r2.approvers) ? r2.approvers.map(a => a.name) : []
  } catch (err) {
    console.error('获取审批人失败:', err)
    deptLeaders.value = []
    roomDirectors.value = []
  } finally {
    loadingApprovers.value = false
  }
}

// 本人的公出记录（从 API 获取）
const myRecordList = ref([])
const loadingList = ref(false)

// 公出记录分页
const recordPage = ref(1)
const recordPageSize = ref(10)

// 本人记录筛选：年份 + 审批状态（全部/已通过/审批中/已驳回）
const recordYear = ref(new Date().getFullYear())
const recordStatusFilter = ref('')  // ''=全部 已通过 processing_rejected=审批中/已驳回
const recordYearOptions = computed(() => {
  const y = new Date().getFullYear()
  return Array.from({ length: 6 }, (_, i) => y - i)  // 当前年及前5年
})

const filteredRecordList = computed(() => {
  const list = myRecordList.value
  if (!recordStatusFilter.value) return list
  if (recordStatusFilter.value === 'processing_rejected') {
    return list.filter(r => (r.status || '') === '审批中' || (r.status || '') === '已驳回')
  }
  return list.filter(r => (r.status || '') === recordStatusFilter.value)
})

const recordTotal = computed(() => filteredRecordList.value.length)
const recordTotalPages = computed(() => Math.max(1, Math.ceil(recordTotal.value / recordPageSize.value)))
const recordDisplayList = computed(() => {
  const list = filteredRecordList.value
  const size = recordPageSize.value
  const start = (recordPage.value - 1) * size
  return list.slice(start, start + size)
})

const recordFilterLabel = computed(() => {
  const statusText = recordStatusFilter.value === 'processing_rejected' ? '、审批中/已驳回' : recordStatusFilter.value ? `、${recordStatusFilter.value}` : ''
  return `展示 ${recordYear.value}年全年本人的公出记录${statusText}`
})

// 每页条数或状态筛选变化时回到第一页
watch(recordPageSize, () => { recordPage.value = 1 })
watch(recordStatusFilter, () => { recordPage.value = 1 })
watch(recordYear, () => { fetchBusinessTripList() })

// 返回登记候选记录：已通过且未做返回登记
const returnCandidates = computed(() =>
  myRecordList.value.filter(r => r.status === '已通过' && !(Number(r.fhdjStatus) === 1))
)

const returnForm = reactive({
  recordId: '',
  actualStartTime: '',
  actualReturnTime: ''
})

// 管理办法文档链接（可改为实际文档地址或路由）
const managementDocUrl = '/doc/gybg-047' // 或外部链接，如 'https://...'

// 从 localStorage 获取当前用户
function initUserInfo() {
  const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
  return {
    department: userInfo.dept || userInfo.department || '智能制造工艺部',
    name: userInfo.name || userInfo.userName || '当前用户',
    jb: userInfo.jb || ''
  }
}

const userInfo = initUserInfo()
const canApprove = ref(false)
const form = reactive({
  targetUnit: '项目管理部',
  assignTime: '', // 委派时间（可选）
  noticeNo: '',
  department: userInfo.department,
  name: userInfo.name,
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

const resetForm = () => {
  form.targetUnit = '项目管理部'
  form.assignTime = ''
  form.noticeNo = ''
  form.totalPeople = 1
  form.workNo = ''
  form.projectName = ''
  form.location = ''
  form.startTime = ''
  form.endTime = ''
  form.amount = 0
  form.phone = ''
  form.task = ''
  form.deptLeader = ''
  form.responsiblePerson = ''
  form.confirmed = false
}

const fetchBusinessTripList = async () => {
  loadingList.value = true
  try {
    const params = { name: form.name, year: recordYear.value }
    const res = await getBusinessTripList(params)
    if (res.success && res.data) {
      myRecordList.value = res.data.map(r => ({
        ...r,
        actualReturnTime: r.actualReturnTime ? r.actualReturnTime.replace(' ', 'T').slice(0, 16) : ''
      }))
    }
  } catch (err) {
    console.error('获取公出记录失败:', err)
    myRecordList.value = []
  } finally {
    loadingList.value = false
  }
}

async function deleteRejectedBusinessTrip(r) {
  if (!r?.id || r.status !== '已驳回') return
  if (!confirm('确认删除这条已驳回的公出记录？删除后不可恢复。')) return
  try {
    await deleteBusinessTripRecord(r.id, { name: form.name })
    alert('已删除')
    fetchBusinessTripList()
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
  // 从首页点击流程：以业务时间(委派年+状态)筛选，再按 focusId 定位到该条并滚动
  const q = route.query
  if (q.focusId) {
    if (q.year) recordYear.value = Number(q.year)
    if (q.status === 'processing_rejected' || q.status === '已通过') recordStatusFilter.value = q.status
  }
  await fetchBusinessTripList()
  if (q.focusId) {
    const list = filteredRecordList.value
    const idx = list.findIndex(r => String(r.id) === String(q.focusId))
    if (idx >= 0) {
      recordPage.value = Math.ceil((idx + 1) / recordPageSize.value)
      await nextTick()
      document.querySelector(`[data-record-id="${q.focusId}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }
})

// 从考勤页「公出返回」跳转过来时：列表加载完成后自动打开返回登记弹窗并预选公出单
watch(
  () => [route.query.action, route.query.id, myRecordList.value.length, loadingList.value],
  () => {
    if (route.query.action !== 'return' || loadingList.value) return
    const candidates = returnCandidates.value
    if (!candidates.length) return
    const id = route.query.id
    const preselectedId = id && candidates.some(r => r.id === id)
      ? id
      : candidates.length === 1
        ? candidates[0].id
        : ''
    returnForm.recordId = preselectedId
    returnForm.actualStartTime = ''
    returnForm.actualReturnTime = ''
    showReturnModal.value = true
    router.replace({ path: '/attendance/business-trip' })
  },
  { flush: 'post' }
)

// 日期/日期时间转后端格式。仅选日期时为 YYYY-MM-DD，转为 YYYY-MM-DD 00:00:00
const toDateTime = (s) => {
  if (!s) return ''
  const t = (s || '').replace('T', ' ').trim()
  if (t.length === 10 && /^\d{4}-\d{2}-\d{2}$/.test(t)) return t + ' 00:00:00'
  return t.length <= 16 ? t + ':00' : t.slice(0, 19)
}

const submitApplication = async () => {
  const tips = []
  if (!(form.location || '').trim()) tips.push('公出地点')
  if (!(form.task || '').trim()) tips.push('公出任务')
  if (!(form.phone || '').trim()) tips.push('联系电话')
  if (!(form.startTime || '').trim()) tips.push('出发时间')
  if (!(form.endTime || '').trim()) tips.push('预计返回时间')
  if (!(form.deptLeader || '').trim()) tips.push('部领导')
  if (!(form.responsiblePerson || '').trim()) tips.push('室主任')
  if (!form.confirmed) tips.push('勾选并确认已阅读管理办法')
  if (tips.length) {
    alert('请完善后再提交：\n\n' + tips.map(t => '· ' + t).join('\n'))
    return
  }

  try {
    const payload = {
      targetUnit: form.targetUnit,
      assignTime: toDateTime(form.assignTime),
      noticeNo: form.noticeNo,
      department: form.department,
      name: form.name,
      totalPeople: Number(form.totalPeople) || 1,
      workNo: form.workNo,
      projectName: form.projectName,
      location: form.location,
      startTime: toDateTime(form.startTime),
      endTime: toDateTime(form.endTime),
      amount: Number(form.amount) || 0,
      phone: form.phone,
      task: form.task,
      deptLeader: form.deptLeader,
      responsiblePerson: form.responsiblePerson
    }
    const res = await submitBusinessTripApply(payload)
    if (res.success) {
      alert('登记已提交')
      showApplyModal.value = false
      fetchBusinessTripList()
    } else {
      alert(res.message || '提交失败')
    }
  } catch (err) {
    const detail = err.response?.data?.detail
    const msg = Array.isArray(detail) ? detail.map(d => d.msg || d).join('; ') : (detail || err.message)
    alert(msg || '提交失败，请稍后重试')
  }
}

// 打开返回登记弹窗
const openReturnModal = () => {
  if (!returnCandidates.value.length) {
    alert('暂无已审批通过且未做返回登记的公出记录。')
    return
  }
  returnForm.recordId = ''
  returnForm.actualStartTime = ''
  returnForm.actualReturnTime = ''
  showReturnModal.value = true
}

// 提交公出返回登记
const submitReturn = async () => {
  const tips = []
  if (!(returnForm.recordId || '').trim()) tips.push('公出记录')
  if (!(returnForm.actualStartTime || '').trim()) tips.push('实际出发时间')
  if (!(returnForm.actualReturnTime || '').trim()) tips.push('实际返回时间')
  if (tips.length) {
    alert('请完善后再提交：\n\n' + tips.map(t => '· ' + t).join('\n'))
    return
  }

  try {
    const payload = {
      actualStartTime: toDateTime(returnForm.actualStartTime),
      actualReturnTime: toDateTime(returnForm.actualReturnTime)
    }
    const res = await updateBusinessTripReturnTime(returnForm.recordId, payload)
    if (res.success) {
      alert('返回登记已提交')
      showReturnModal.value = false
      fetchBusinessTripList()
    } else {
      alert(res.message || '返回登记提交失败')
    }
  } catch (err) {
    const detail = err.response?.data?.detail
    const msg = Array.isArray(detail) ? detail.map(d => d.msg || d).join('; ') : (detail || err.message)
    alert(msg || '返回登记提交失败，请稍后重试')
  }
}

watch(showApplyModal, (visible) => {
  if (visible && form.name) fetchApprovers()
})

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

/* 公出记录：标题、说明、表格统一在一个白底容器内，减少割裂感 */
.record-card {
  background: white;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-lighter);
  overflow: hidden;
}

.record-card__header {
  padding: var(--spacing-lg) var(--spacing-xl);
  background: white;
  border-bottom: 1px solid var(--color-border-lighter);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: var(--spacing-md);
}

.record-card__header h3 {
  margin: 0 0 var(--spacing-xs);
}

.record-card__filters {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-shrink: 0;
}

.record-card__filters .filter-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.record-card__filters .filter-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.record-card__filters .filter-select {
  padding: 6px 10px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
}

.record-card__desc {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: normal;
}

.card-body {
  padding: var(--spacing-lg);
}

.record-card__body {
  padding: 0;
  background: white;
}

.record-card__body .table-wrap {
  overflow-x: auto;
}

.record-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
  background: white;
}

.record-table th,
.record-table td {
  padding: 12px var(--spacing-xl);
  text-align: left;
  border-bottom: 1px solid var(--color-border-lighter);
  background: white;
}

.record-table th {
  font-weight: 600;
  color: var(--color-text-primary);
}

.record-table tbody tr:hover td {
  background: var(--color-bg-spotlight);
}

.return-time-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  min-width: 0;
}

.record-table__return-input {
  flex: 1;
  min-width: 140px;
  padding: 6px 10px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  background: white;
}

.record-table__return-input:focus {
  border-color: var(--color-primary);
  outline: none;
}

.record-table__save-btn {
  flex-shrink: 0;
  padding: 6px 12px;
  font-size: var(--font-size-sm);
  color: white;
  background: var(--color-primary);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  white-space: nowrap;
}

.record-table__save-btn:hover:not(:disabled) {
  background: var(--color-primary-light);
  border-color: var(--color-primary-light);
}

.record-table__save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.record-table__muted {
  color: var(--color-text-quaternary);
}

.record-card__body .status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
}

.record-card__body .status-tag.status-approved {
  color: #059669;
  background: #d1fae5;
}

.record-card__body .status-tag.status-processing {
  color: #d97706;
  background: #fef3c7;
}

.record-card__body .status-tag.status-rejected {
  color: #dc2626;
  background: #fee2e2;
}
.reject-reason-cell {
  max-width: 200px;
  word-break: break-word;
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}

/* 公出记录分页 */
.record-pagination {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: var(--spacing-lg);
  padding: var(--spacing-md) var(--spacing-xl);
  border-top: 1px solid var(--color-border-lighter);
  background: white;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.record-pagination__total {
  margin-right: auto;
}

.record-pagination__size {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.record-pagination__select {
  padding: 4px 8px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  background: white;
}

.record-pagination__pages {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.record-pagination__btn {
  padding: 6px 12px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  background: white;
  font-size: var(--font-size-sm);
  cursor: pointer;
  color: var(--color-text-primary);
}

.record-pagination__btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.record-pagination__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.record-pagination__num {
  color: var(--color-text-tertiary);
  min-width: 80px;
  text-align: center;
}

.empty-text {
  text-align: center;
  color: var(--color-text-secondary);
  padding: var(--spacing-xxl) 0;
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

.modal-content {
  background: white;
  padding: var(--spacing-xl);
  border-radius: var(--radius-md);
  width: 800px; /* 进一步增加宽度 */
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

.label-optional {
  font-weight: normal;
  color: var(--color-text-tertiary);
}

.doc-link {
  display: block;
  margin-top: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  text-decoration: none;
}

.doc-link:hover {
  text-decoration: underline;
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

.hint-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-top: 4px;
}

.text-danger {
  color: #f5222d;
}

.mb-md {
  margin-bottom: var(--spacing-md);
}

.checkbox-group {
  display: flex;
  align-items: flex-start;
  padding: 10px 0;
  background-color: #fff1f0;
  border: 1px solid #ffa39e;
  border-radius: var(--radius-sm);
  padding: var(--spacing-md);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
  font-weight: bold;
  font-size: var(--font-size-sm);
}

.checkbox-label input {
  width: auto;
  margin: 0;
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
</style>
