<template>
  <div class="hxp-manage-page">
    <div class="container">
      <header class="page-header">
        <div class="header-content">
          <div class="header-info">
            <h1 class="header-title">换休票批量管理</h1>
            <p class="header-subtitle">批量为员工增加或减少换休票。提交后需领导审批通过方可生效。</p>
          </div>
          <div class="header-actions" v-if="canAccessRecords">
            <router-link to="/admin/hxp-records" class="btn btn-outline">换休票明细查询</router-link>
          </div>
        </div>
      </header>

      <div v-if="!canAccess" class="card no-permission">
        <p>您暂无权限访问此页面，仅系统管理员、人事管理员、部长/副部长或综合技术室主任/副主任可操作。</p>
        <router-link to="/" class="btn btn-primary">返回首页</router-link>
      </div>

      <template v-else>
        <div class="card form-section">
          <div v-if="editingRejectedId" class="resubmit-banner">正在编辑已驳回的申请，修改后点击提交将重新提交审批 <button type="button" class="btn btn-sm btn-outline" @click="editingRejectedId = null; reset()">取消编辑</button></div>
          <form @submit.prevent="openApproverDialog" class="fill-form">
            <div class="form-row">
              <label class="form-label">操作类型</label>
              <div class="action-toggle">
                <button type="button" class="toggle-btn" :class="{ active: action === 'add' }" @click="action = 'add'">增加换休票</button>
                <button type="button" class="toggle-btn" :class="{ active: action === 'subtract' }" @click="action = 'subtract'">减少换休票</button>
              </div>
            </div>
            <div class="form-row">
              <label class="form-label">数量（张）</label>
              <input type="number" v-model.number="amount" min="0.25" step="0.25" class="form-input" required placeholder="如 2、0.5" />
            </div>
            <div class="form-row">
              <label class="form-label">原因 <span class="required-mark">*</span></label>
              <input type="text" v-model="ly" class="form-input" placeholder="请填写增减原因，如：3月补发、手工调整、年度扣减" required />
            </div>
            <div class="form-row">
              <label class="form-label">员工姓名</label>
              <textarea
                v-model="namesText"
                class="form-textarea"
                rows="6"
                placeholder="请输入姓名，支持以下分隔方式：&#10;换行、逗号、空格、顿号&#10;&#10;示例：&#10;张三&#10;李四，王五&#10;赵六、钱七"
                required
              ></textarea>
              <span class="form-hint">已识别 {{ parsedNames.length }} 个姓名</span>
            </div>
            <div v-if="parsedNames.length" class="names-preview">
              <span v-for="n in parsedNames" :key="n" class="name-tag">{{ n }}</span>
            </div>
            <div class="form-actions">
              <button type="submit" class="btn btn-primary" :disabled="submitting || !parsedNames.length || !amount || !ly.trim()">
                {{ action === 'add' ? '提交增加审批' : '提交减少审批' }}
              </button>
              <button type="button" class="btn btn-outline" @click="reset">重置</button>
            </div>
          </form>
        </div>

        <!-- 选择审批人弹窗 -->
        <div v-if="approverDialogVisible" class="modal-overlay" @click.self="approverDialogVisible = false">
          <div class="modal-box">
            <div class="modal-header">
              <h3>选择审批领导</h3>
              <button type="button" class="modal-close" @click="approverDialogVisible = false">&times;</button>
            </div>
            <div class="modal-body">
              <p class="approver-hint">请选择部长/副部长进行审批{{ isDeptLeaderJb(currentUserJb) ? '（您为部领导，不可选本人）' : '' }}：</p>
              <div class="approver-summary">
                <span>操作：<strong>{{ action === 'add' ? '增加' : '减少' }} {{ amount }} 张</strong></span>
                <span>人数：<strong>{{ parsedNames.length }} 人</strong></span>
                <span>原因：<strong>{{ ly }}</strong></span>
              </div>
              <div v-if="approverLoading" class="stat-empty">加载审批人列表…</div>
              <div v-else-if="approverList.length" class="approver-list">
                <label
                  v-for="a in approverList"
                  :key="a.name"
                  class="approver-option"
                  :class="{ selected: selectedApprover === a.name }"
                >
                  <input type="radio" :value="a.name" v-model="selectedApprover" class="approver-radio" />
                  <span class="approver-name">{{ a.name }}</span>
                  <span class="approver-jb">{{ a.jb || '' }}</span>
                </label>
              </div>
              <div v-else class="stat-empty">未找到可选的审批人</div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-outline" @click="approverDialogVisible = false">取消</button>
              <button
                type="button"
                class="btn btn-primary"
                :disabled="!selectedApprover || submitting"
                @click="submitApproval"
              >{{ submitting ? '提交中…' : '确认提交' }}</button>
            </div>
          </div>
        </div>

        <!-- 我的申请记录 -->
        <div class="card my-requests-section">
          <div class="stat-header">
            <h2 class="stat-title">我的审批申请</h2>
            <button type="button" class="btn btn-outline" @click="loadMyRequests">刷新</button>
          </div>
          <div class="stat-table-wrap" v-if="myRequests.length">
            <table class="stat-table">
              <thead>
                <tr>
                  <th>操作</th>
                  <th>数量</th>
                  <th>原因</th>
                  <th>员工</th>
                  <th>审批人</th>
                  <th>状态</th>
                  <th>申请时间</th>
                  <th>驳回原因</th>
                  <th>处理</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in myRequests" :key="r.id" :class="{ 'row-rejected': r.status === 22 }">
                  <td>{{ r.action === 'add' ? '增加' : '减少' }}</td>
                  <td>{{ r.amount }} 张</td>
                  <td class="cell-ly" :title="r.ly">{{ r.ly }}</td>
                  <td class="cell-names" :title="r.names.join('、')">{{ r.namesCount }}人：{{ r.names.slice(0, 3).join('、') }}{{ r.namesCount > 3 ? '…' : '' }}</td>
                  <td>{{ r.approver }}</td>
                  <td>
                    <span class="badge" :class="r.status === 0 ? 'badge-pending' : (r.status === 2 ? 'badge-active' : 'badge-expired')">
                      {{ r.statusText }}
                    </span>
                  </td>
                  <td>{{ r.applyTime }}</td>
                  <td>{{ r.rejectReason || '-' }}</td>
                  <td>
                    <button v-if="r.status === 22" type="button" class="btn btn-sm btn-primary" @click="editRejectedHxp(r)">重新编辑</button>
                    <span v-else>—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else-if="!myRequestsLoading" class="stat-empty">暂无审批记录</div>
          <div v-else class="stat-empty">加载中…</div>
        </div>

        <!-- 换休票统计 -->
        <div class="card stat-section">
          <div class="stat-header">
            <h2 class="stat-title">换休票统计</h2>
            <div class="stat-filters">
              <select v-model="statLsys" class="form-input filter-select" @change="loadSummary">
                <option value="">全部科室</option>
                <option v-for="l in lsysList" :key="l" :value="l">{{ l }}</option>
              </select>
              <input type="text" v-model="statKeyword" class="form-input filter-input" placeholder="搜索姓名…" @input="filterSummary" />
              <button type="button" class="btn btn-outline" @click="loadSummary">刷新</button>
            </div>
          </div>
          <div class="stat-summary-bar" v-if="summaryFiltered.length">
            <span>共 <strong>{{ summaryFiltered.length }}</strong> 人</span>
            <span>总余额 <strong>{{ summaryTotalTickets }}</strong> 张</span>
            <span>有余额 <strong>{{ summaryWithTickets }}</strong> 人</span>
          </div>
          <div class="stat-table-wrap" v-if="summaryFiltered.length">
            <table class="stat-table">
              <thead>
                <tr>
                  <th class="col-idx">#</th>
                  <th class="col-name">姓名</th>
                  <th class="col-lsys">科室</th>
                  <th class="col-total">余额（张）</th>
                  <th class="col-action">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in summaryFiltered" :key="row.name" :class="{ 'row-zero': row.total <= 0 }">
                  <td class="col-idx">{{ idx + 1 }}</td>
                  <td class="col-name">{{ row.name }}</td>
                  <td class="col-lsys">{{ row.lsys || '-' }}</td>
                  <td class="col-total" :class="{ 'text-muted': row.total <= 0 }">{{ row.total }}</td>
                  <td class="col-action">
                    <button type="button" class="btn btn-sm btn-link" @click="openDetail(row.name)">明细</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else-if="!summaryLoading" class="stat-empty">暂无数据</div>
          <div v-else class="stat-empty">加载中…</div>
        </div>

        <!-- 个人明细弹窗 -->
        <div v-if="detailVisible" class="modal-overlay" @click.self="detailVisible = false">
          <div class="modal-box">
            <div class="modal-header">
              <h3>{{ detailName }} 的换休票记录</h3>
              <button type="button" class="modal-close" @click="detailVisible = false">&times;</button>
            </div>
            <div class="modal-body">
              <div v-if="detailLoading" class="stat-empty">加载中…</div>
              <table v-else-if="detailList.length" class="stat-table detail-table">
                <thead>
                  <tr>
                    <th>数量</th>
                    <th>获得时间</th>
                    <th>来源</th>
                    <th>过期日期</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="d in detailList" :key="d.id" :class="{ 'row-expired': d.expired, 'row-zero': d.sl <= 0 }">
                    <td>{{ d.sl }}</td>
                    <td>{{ d.sj }}</td>
                    <td>{{ d.ly }}</td>
                    <td>{{ d.expire || '-' }}</td>
                    <td>
                      <span v-if="d.sl <= 0" class="badge badge-muted">已扣完</span>
                      <span v-else-if="d.expired" class="badge badge-expired">已过期</span>
                      <span v-else class="badge badge-active">有效</span>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="stat-empty">暂无记录</div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getHxpSummary, getHxpDetail, submitHxpApproval, getMyHxpRequests, resubmitHxpApproval } from '@/api/admin'
import { getUploadConfig, getApprovers } from '@/api/attendance'
import { isMinisterLevel, canManageHxpBatch } from '@/utils/roleMatch'

const canAccess = ref(false)
const canAccessRecords = ref(false)
const currentUserName = ref('')
const currentUserJb = ref('')
const currentUserLsys = ref('')

function isDeptLeaderJb(jb) {
  return isMinisterLevel(jb)
}
const action = ref('add')
const amount = ref(1)
const ly = ref('')
const namesText = ref('')
const submitting = ref(false)
const editingRejectedId = ref(null)

const approverDialogVisible = ref(false)
const approverList = ref([])
const approverLoading = ref(false)
const selectedApprover = ref('')

const myRequests = ref([])
const myRequestsLoading = ref(false)

const summaryAll = ref([])
const summaryLoading = ref(false)
const statKeyword = ref('')
const statLsys = ref('')
const lsysList = ref([])

const detailVisible = ref(false)
const detailName = ref('')
const detailList = ref([])
const detailLoading = ref(false)

const summaryFiltered = computed(() => {
  const kw = (statKeyword.value || '').trim()
  if (!kw) return summaryAll.value
  return summaryAll.value.filter(r => r.name.includes(kw))
})

const summaryTotalTickets = computed(() =>
  summaryFiltered.value.reduce((s, r) => s + r.total, 0).toFixed(2)
)

const summaryWithTickets = computed(() =>
  summaryFiltered.value.filter(r => r.total > 0).length
)

const parsedNames = computed(() => {
  if (!namesText.value.trim()) return []
  return [...new Set(
    namesText.value
      .split(/[\n,，、\s]+/)
      .map(s => s.trim())
      .filter(Boolean)
  )]
})

async function loadSummary() {
  summaryLoading.value = true
  try {
    const params = { current_user: currentUserName.value }
    if (statLsys.value) params.lsys = statLsys.value
    const res = await getHxpSummary(params)
    summaryAll.value = res?.data || []
    if (res?.lsys_list?.length) lsysList.value = res.lsys_list
  } catch {
    summaryAll.value = []
  } finally {
    summaryLoading.value = false
  }
}

function filterSummary() { /* computed 自动响应 */ }

async function openDetail(name) {
  detailName.value = name
  detailVisible.value = true
  detailLoading.value = true
  detailList.value = []
  try {
    const res = await getHxpDetail({ name, current_user: currentUserName.value })
    detailList.value = res?.data || []
  } catch {
    detailList.value = []
  } finally {
    detailLoading.value = false
  }
}

async function loadMyRequests() {
  if (!currentUserName.value) return
  myRequestsLoading.value = true
  try {
    const res = await getMyHxpRequests({ applicant: currentUserName.value })
    myRequests.value = res?.data || []
  } catch {
    myRequests.value = []
  } finally {
    myRequestsLoading.value = false
  }
}

function editRejectedHxp(r) {
  if (!r?.id || r.status !== 22) return
  editingRejectedId.value = r.id
  action.value = r.action || 'add'
  amount.value = r.amount || 1
  ly.value = r.ly || ''
  namesText.value = (r.names || []).join('\n')
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function openApproverDialog() {
  if (!parsedNames.value.length || !amount.value || !ly.value.trim()) return
  approverDialogVisible.value = true
  selectedApprover.value = ''
  approverLoading.value = true
  try {
    const res = await getApprovers({ name: currentUserName.value, level: 'dept_leader' })
    let list = res?.approvers || []
    if (isDeptLeaderJb(currentUserJb.value)) {
      const self = (currentUserName.value || '').trim()
      list = list.filter((a) => (a.name || '').trim() !== self)
    }
    approverList.value = list
  } catch {
    approverList.value = []
  } finally {
    approverLoading.value = false
  }
}

async function submitApproval() {
  if (!selectedApprover.value || submitting.value) return
  submitting.value = true
  try {
    const payload = {
      current_user: currentUserName.value,
      names: parsedNames.value,
      amount: amount.value,
      action: action.value,
      ly: ly.value.trim(),
      approver: selectedApprover.value,
    }
    const isResubmit = !!editingRejectedId.value
    const res = isResubmit
      ? await resubmitHxpApproval(editingRejectedId.value, payload)
      : await submitHxpApproval(payload)
    alert(isResubmit ? '已重新提交，等待审批' : (res.message || '已提交审批'))
    approverDialogVisible.value = false
    editingRejectedId.value = null
    reset()
    loadMyRequests()
  } catch (e) {
    alert(e.response?.data?.detail || e.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
    const name = (userInfo.name || userInfo.userName || '').trim()
    currentUserName.value = name
    currentUserJb.value = (userInfo.jb || '').trim()
    currentUserLsys.value = (userInfo.dept || userInfo.lsys || '').trim()
    if (!name) return
    const res = await getUploadConfig()
    const a1 = (res?.admin1 || '').trim()
    const a2 = (res?.admin2 || '').trim()
    canAccess.value = canManageHxpBatch({
      name,
      jb: currentUserJb.value,
      lsys: currentUserLsys.value,
      admin1: a1,
      admin2: a2,
    })
    canAccessRecords.value = isDeptLeaderJb(currentUserJb.value) || !!(a2 && name === a2)
    if (canAccess.value) {
      loadSummary()
      loadMyRequests()
    }
  } catch {
    canAccess.value = false
  }
})

function reset() {
  namesText.value = ''
  amount.value = 1
  ly.value = ''
}
</script>

<style scoped>
.hxp-manage-page {
  min-height: 100vh;
  background: var(--color-bg-layout);
  padding-bottom: var(--spacing-xxl);
}
.page-header { margin-bottom: var(--spacing-xl); }
.header-title {
  font-size: var(--font-size-xxl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}
.header-subtitle {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-top: var(--spacing-xs);
}
.no-permission {
  padding: var(--spacing-xxl);
  text-align: center;
  color: var(--color-text-secondary);
}
.form-section { padding: var(--spacing-xl); }
.form-row {
  margin-bottom: var(--spacing-lg);
}
.form-label {
  display: block;
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
}
.form-input, .form-textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  background: var(--color-bg-container);
  box-sizing: border-box;
}
.form-input:focus, .form-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-lightest);
}
.form-textarea {
  resize: vertical;
  font-family: inherit;
  line-height: 1.6;
}
.form-hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  margin-top: 4px;
  display: block;
}
.action-toggle {
  display: inline-flex;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  overflow: hidden;
}
.toggle-btn {
  padding: 8px 20px;
  border: none;
  background: var(--color-bg-container);
  color: var(--color-text-secondary);
  cursor: pointer;
  font-size: var(--font-size-base);
  transition: all 0.2s;
}
.toggle-btn + .toggle-btn {
  border-left: 1px solid var(--color-border-base);
}
.toggle-btn.active {
  background: var(--color-primary);
  color: #fff;
  font-weight: var(--font-weight-medium);
}
.names-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: var(--spacing-lg);
}
.name-tag {
  display: inline-block;
  padding: 2px 10px;
  background: var(--color-primary-lightest);
  color: var(--color-primary);
  border-radius: 100px;
  font-size: var(--font-size-sm);
}
.form-actions {
  display: flex;
  gap: var(--spacing-sm);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-border-lighter);
}
.required-mark {
  color: var(--color-error);
}

/* 审批人选择弹窗 */
.approver-hint {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-md);
}
.approver-summary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-lg);
  padding: 10px 16px;
  background: var(--color-bg-spotlight);
  border-radius: var(--radius-base);
  margin-bottom: var(--spacing-lg);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
.approver-summary strong {
  color: var(--color-primary);
}
.approver-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.approver-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: all 0.2s;
}
.approver-option:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-lightest, #f0f7ff);
}
.approver-option.selected {
  border-color: var(--color-primary);
  background: var(--color-primary-lightest, #f0f7ff);
  box-shadow: 0 0 0 1px var(--color-primary);
}
.approver-radio {
  accent-color: var(--color-primary);
}
.approver-name {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}
.approver-jb {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  padding: 16px 24px;
  border-top: 1px solid var(--color-border-lighter);
}

/* 我的审批记录 */
.my-requests-section {
  margin-top: var(--spacing-xl);
  padding: var(--spacing-xl);
}
.row-rejected td {
  color: var(--color-error);
}
.cell-ly, .cell-names {
  max-width: 160px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.badge-pending {
  background: #fef3c7;
  color: #d97706;
}

/* 统计模块 */
.stat-section {
  margin-top: var(--spacing-xl);
  padding: var(--spacing-xl);
}
.stat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
}
.stat-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}
.stat-filters {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
}
.filter-select {
  width: 140px;
}
.filter-input {
  width: 160px;
}
.stat-summary-bar {
  display: flex;
  gap: var(--spacing-xl);
  padding: 10px 16px;
  background: var(--color-bg-spotlight);
  border-radius: var(--radius-base);
  margin-bottom: var(--spacing-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
.stat-summary-bar strong {
  color: var(--color-primary);
  font-weight: var(--font-weight-semibold);
}
.stat-table-wrap {
  overflow-x: auto;
  max-height: 520px;
  overflow-y: auto;
}
.stat-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}
.stat-table th, .stat-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid var(--color-border-lighter);
}
.stat-table th {
  background: var(--color-bg-spotlight);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  position: sticky;
  top: 0;
  z-index: 1;
}
.col-idx { width: 50px; text-align: center; }
.col-total { font-weight: var(--font-weight-semibold); }
.col-action { width: 80px; }
.row-zero td { color: var(--color-text-tertiary); }
.text-muted { color: var(--color-text-tertiary) !important; }
.btn-sm {
  padding: 2px 10px;
  font-size: var(--font-size-sm);
}
.btn-link {
  background: none;
  border: none;
  color: var(--color-primary);
  cursor: pointer;
  text-decoration: underline;
  padding: 2px 6px;
}
.btn-link:hover { opacity: 0.8; }
.stat-empty {
  padding: var(--spacing-xl);
  text-align: center;
  color: var(--color-text-tertiary);
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-box {
  background: var(--color-bg-container);
  border-radius: var(--radius-lg, 12px);
  width: 680px;
  max-width: 92vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,0.18);
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--color-border-lighter);
}
.modal-header h3 {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
}
.modal-close {
  background: none;
  border: none;
  font-size: 22px;
  cursor: pointer;
  color: var(--color-text-tertiary);
  line-height: 1;
}
.modal-close:hover { color: var(--color-text-primary); }
.modal-body {
  padding: 16px 24px 24px;
  overflow-y: auto;
  flex: 1;
}
.detail-table td, .detail-table th {
  font-size: 13px;
}
.row-expired td { color: var(--color-text-tertiary); text-decoration: line-through; }
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 100px;
  font-size: 12px;
  font-weight: var(--font-weight-medium);
}
.badge-active { background: #dcfce7; color: #16a34a; }
.badge-expired { background: #fee2e2; color: #dc2626; }
.badge-muted { background: #f1f5f9; color: #94a3b8; }
.resubmit-banner {
  padding: 10px 16px;
  background: #fef3c7;
  color: #92400e;
  border-radius: var(--radius-sm);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}
</style>
