<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">公出节假日领换休票</h1>
          <p class="header-subtitle">公出节假日加班换休票申请与记录</p>
        </div>
        <div class="header-actions">
          <button class="btn btn-primary" @click="showApplyModal = true">申请换休票</button>
        </div>
      </div>
    </div>

    <!-- 记录列表 -->
    <div class="content mt-xl">
      <div class="card record-card">
        <div class="card-header record-card__header">
          <div>
            <h3>申请记录</h3>
            <p class="record-card__desc">{{ recordFilterLabel }}</p>
          </div>
          <div class="record-card__filters">
            <select v-if="canViewAll" v-model="recordScope" class="filter-select filter-select--scope">
              <option value="self">本人</option>
              <option value="lsys">本专业</option>
              <option value="all">全部科室</option>
              <option v-for="d in deptOptions" :key="d" :value="'lsys:' + d">{{ d }}</option>
            </select>
            <input type="month" v-model="recordMonth" class="filter-input">
            <select v-model="recordStatus" class="filter-select">
              <option value="all">全部</option>
              <option value="processing">审批中</option>
              <option value="approved">已通过</option>
              <option value="rejected">已驳回</option>
            </select>
            <input
              v-if="canViewAll && recordScope !== 'self'"
              v-model.trim="nameFilter"
              type="search"
              class="filter-input filter-input--search"
              placeholder="搜索姓名"
            >
          </div>
        </div>
        <div class="card-body record-card__body">
          <div class="table-wrap" v-if="filteredList.length">
            <table class="record-table">
              <thead>
                <tr>
                  <th>班组</th>
                  <th>姓名</th>
                  <th>加班起始日</th>
                  <th>加班截止日</th>
                  <th>日期性质</th>
                  <th>天数</th>
                  <th>换休票(张)</th>
                  <th>佐证材料</th>
                  <th>申请时间</th>
                  <th>审批状态</th>
                  <th>当前审批人</th>
                  <th>驳回原因</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in paginatedList" :key="r.id">
                  <td>{{ r.department || '—' }}</td>
                  <td>{{ r.applicant || '—' }}</td>
                  <td>
                    <template v-if="r.dateRanges && r.dateRanges.length > 1">
                      <div v-for="(seg, si) in r.dateRanges" :key="si" class="cell-range-seg">{{ seg.from }}</div>
                    </template>
                    <template v-else>{{ r.dateFrom }}</template>
                  </td>
                  <td>
                    <template v-if="r.dateRanges && r.dateRanges.length > 1">
                      <div v-for="(seg, si) in r.dateRanges" :key="si" class="cell-range-seg">{{ seg.to }}</div>
                    </template>
                    <template v-else>{{ r.dateTo }}</template>
                  </td>
                  <td class="cell-rest-summary" :title="r.restDaySummary">{{ r.restDaySummary || '—' }}</td>
                  <td>{{ r.days }}</td>
                  <td>{{ r.hxpCount }}</td>
                  <td>
                    <template v-if="r.materialFiles && r.materialFiles.length">
                      <a
                        v-for="(f, idx) in r.materialFiles"
                        :key="idx"
                        :href="getDownloadUrl(f.name)"
                        target="_blank"
                        rel="noopener"
                        class="file-link"
                      >{{ f.original || f.name }}</a>
                    </template>
                    <span v-else>—</span>
                  </td>
                  <td>{{ r.applyTime }}</td>
                  <td><span class="status-tag" :class="r.statusClass">{{ r.status }}</span></td>
                  <td>{{ r.currentApprover || '—' }}</td>
                  <td class="reject-reason-cell">{{ r.statusCode === 22 && r.rejectReason ? r.rejectReason : '—' }}</td>
                  <td>
                    <template v-if="r.statusCode === 22 && r.applicant === userName">
                      <button type="button" class="btn btn-sm btn-primary" @click="editRejectedRecord(r)" style="margin-right:6px">重新编辑</button>
                      <button type="button" class="btn btn-sm btn-danger" @click="deleteRecord(r)">删除</button>
                    </template>
                    <span v-else>—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="record-pagination" v-if="filteredList.length">
            <span class="record-pagination__total">共 {{ filteredList.length }} 条</span>
            <span class="record-pagination__size">
              每页
              <select v-model.number="pageSize" class="record-pagination__select">
                <option :value="10">10</option>
                <option :value="20">20</option>
                <option :value="50">50</option>
              </select>
              条
            </span>
            <div class="record-pagination__pages">
              <button type="button" class="record-pagination__btn" :disabled="page <= 1" @click="page = Math.max(1, page - 1)">上一页</button>
              <span class="record-pagination__num">第 {{ page }} / {{ totalPages || 1 }} 页</span>
              <button type="button" class="record-pagination__btn" :disabled="page >= totalPages" @click="page = Math.min(totalPages, page + 1)">下一页</button>
            </div>
          </div>
          <p class="empty-text" v-else>暂无申请记录</p>
        </div>
      </div>
    </div>

    <!-- 申请弹窗 -->
    <div v-if="showApplyModal" class="modal-overlay" @click.self="showApplyModal = false">
      <div class="modal-content">
        <h2>{{ editingRejectedId ? '重新编辑换休票申请' : '公出节假日领换休票' }}</h2>
        <form @submit.prevent="handleSubmit" class="application-form" autocomplete="on">
          <div class="form-row">
            <div class="form-group half">
              <label>姓名</label>
              <input type="text" :value="userName" readonly>
            </div>
            <div class="form-group half">
              <label>班组</label>
              <input type="text" :value="userDept" readonly>
            </div>
          </div>

          <div class="form-group">
            <label>加班时间 <span class="range-count-hint" v-if="form.ranges.length > 1">（共 {{ form.ranges.length }} 段）</span></label>
            <div v-for="(rng, idx) in form.ranges" :key="idx" class="range-item">
              <span class="range-index" v-if="form.ranges.length > 1">{{ idx + 1 }}.</span>
              <div class="date-range-row">
                <input type="date" v-model="rng.from" required>
                <span class="date-range-sep">至</span>
                <input type="date" v-model="rng.to" required>
              </div>
              <button type="button" class="range-remove-btn" v-if="form.ranges.length > 1" @click="removeRange(idx)" title="移除此段">&times;</button>
              <span class="range-days" v-if="rangeDays(rng) > 0">{{ rangeDays(rng) }}天</span>
            </div>
            <button type="button" class="range-add-btn" @click="addRange">+ 添加时间段</button>
            <div class="calc-info" v-if="calcDays > 0">
              <p>加班天数：<strong>{{ calcDays }}</strong> 天<span v-if="form.ranges.length > 1">（{{ form.ranges.length }} 段合计）</span></p>
              <p>换休票数量：<strong>{{ calcTickets }}</strong> 张（计算规则：加班天数 ÷ 4）</p>
            </div>
            <p class="date-range-hint">
              区间内每一天须为<strong>周六、周日</strong>或<strong>公司假期与调休表</strong>中的放假/调休休息日（类型含「假」或「休」）；标记为<strong>补班</strong>（含「班」）的日期不可选。
            </p>
            <p class="date-range-hint">
              所选起止日期须<strong>完全落在</strong>您本人已在「公出管理」中申报且<strong>部领导、室主任均已通过</strong>的某条公出单的<strong>预计出发时间～预计返回时间</strong>（按日历日）范围内。
            </p>
          </div>

          <div class="form-group">
            <label>佐证材料 <span class="required-mark">*</span></label>
            <div class="file-upload-area" @click="triggerFileInput" @dragover.prevent @drop.prevent="handleDrop">
              <input
                ref="fileInputRef"
                type="file"
                multiple
                :accept="acceptTypes"
                style="display:none"
                @change="handleFileChange"
              >
              <div v-if="!selectedFiles.length" class="file-upload-placeholder">
                <p class="upload-icon">📎</p>
                <p>点击或拖拽上传佐证材料</p>
                <p class="upload-hint">支持图片、Word、Excel、PPT、PDF 等格式，单文件不超过 20MB</p>
              </div>
              <div v-else class="file-list">
                <div v-for="(f, idx) in selectedFiles" :key="idx" class="file-item">
                  <span class="file-name">{{ f.name }}</span>
                  <span class="file-size">{{ formatFileSize(f.size) }}</span>
                  <button type="button" class="file-remove" @click.stop="removeFile(idx)">&times;</button>
                </div>
                <p class="upload-more" @click.stop>点击上方区域可继续添加</p>
              </div>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group half">
              <label>一级审批人（科室主任）</label>
              <select v-model="form.approver1" required :disabled="loadingApprovers1">
                <option value="">请选择</option>
                <option v-for="p in approvers1" :key="p" :value="p">{{ p }}</option>
              </select>
            </div>
            <div class="form-group half">
              <label>二级审批人（部长/副部长）</label>
              <select v-model="form.approver2" required :disabled="loadingApprovers2">
                <option value="">请选择</option>
                <option v-for="p in approvers2" :key="p" :value="p">{{ p }}</option>
              </select>
            </div>
          </div>

          <p class="form-dept-notice" role="note">
            部门严格管理换休票制度，每个换休票增加的申请都将推送部门主要领导。
          </p>

          <div class="form-actions">
            <button type="button" @click="showApplyModal = false">取消</button>
            <button type="submit" class="btn-primary" :disabled="submitting">
              {{ submitting ? '提交中...' : '提交' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import {
  submitHolidayExchange,
  getHolidayExchangeList,
  deleteHolidayExchangeRecord,
  resubmitHolidayExchangeRecord,
  getHolidayExchangeDownloadUrl,
  getApprovers,
  getHolidays,
  getDeptLsysList,
  getUploadConfig
} from '@/api/attendance'
import { isMinisterOrDeptLeader } from '@/utils/roleMatch'

const showApplyModal = ref(false)
const editingRejectedId = ref(null)
const submitting = ref(false)

const userInfo = (() => {
  const u = JSON.parse(localStorage.getItem('userInfo') || '{}')
  return {
    name: u.name || u.userName || '',
    dept: u.dept || u.department || '',
    jb: (u.jb || '').trim(),
  }
})()
const userName = userInfo.name
const userDept = userInfo.dept

const canViewAll = ref(false)
const recordScope = ref('self')
const deptOptions = ref([])

const isLeaderRole = computed(() => {
  return isMinisterOrDeptLeader(userInfo.jb)
})

const form = reactive({
  ranges: [{ from: '', to: '' }],
  approver1: '',
  approver2: '',
})

function addRange() {
  form.ranges.push({ from: '', to: '' })
}

function removeRange(idx) {
  if (form.ranges.length > 1) form.ranges.splice(idx, 1)
}

function rangeDays(rng) {
  if (!rng.from || !rng.to) return 0
  const d1 = new Date(rng.from)
  const d2 = new Date(rng.to)
  if (isNaN(d1) || isNaN(d2) || d2 < d1) return 0
  return Math.round((d2 - d1) / 86400000) + 1
}

const selectedFiles = ref([])
const fileInputRef = ref(null)
const acceptTypes = '.jpg,.jpeg,.png,.gif,.bmp,.webp,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.pdf,.txt,.zip,.rar,.7z,.wps,.et,.dps'

function triggerFileInput() {
  fileInputRef.value?.click()
}

function handleFileChange(e) {
  const files = Array.from(e.target.files || [])
  selectedFiles.value.push(...files)
  e.target.value = ''
}

function handleDrop(e) {
  const files = Array.from(e.dataTransfer?.files || [])
  selectedFiles.value.push(...files)
}

function removeFile(idx) {
  selectedFiles.value.splice(idx, 1)
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const calcDays = computed(() => {
  let total = 0
  for (const rng of form.ranges) {
    total += rangeDays(rng)
  }
  return total
})

const calcTickets = computed(() => {
  if (calcDays.value <= 0) return 0
  return (calcDays.value / 4).toFixed(4).replace(/\.?0+$/, '') || '0'
})

/** 与后端 holiday_exchange 校验一致：周末或 holiday 表含「假」「休」且不含「班」 */
function normalizeHolidayDateKey(s) {
  const parts = String(s).trim().slice(0, 10).split('-')
  if (parts.length < 3) return String(s).trim().slice(0, 10)
  return `${parts[0]}-${parts[1].padStart(2, '0')}-${parts[2].padStart(2, '0')}`
}

function isCompanyRestDay(ymdStr, localDate, typeMap) {
  const t = typeMap[ymdStr] || ''
  const w = localDate.getDay()
  const isWeekend = w === 0 || w === 6
  if (t.includes('班')) return false
  if (isWeekend) return true
  if (t.includes('假') || t.includes('休')) return true
  return false
}

async function findInvalidDatesInRange(dateFrom, dateTo) {
  const y1 = parseInt(dateFrom.slice(0, 4), 10)
  const y2 = parseInt(dateTo.slice(0, 4), 10)
  if (isNaN(y1) || isNaN(y2)) return []
  const typeMap = {}
  for (let y = y1; y <= y2; y++) {
    try {
      const res = await getHolidays(y)
      if (res.success && res.holidays) {
        for (const h of res.holidays) {
          if (h.date) typeMap[normalizeHolidayDateKey(h.date)] = (h.type || '').trim()
        }
      }
    } catch {
      /* 某年拉取失败则该年无表内假日，仅周末仍算休息 */
    }
  }
  const invalid = []
  const cur = new Date(`${dateFrom}T12:00:00`)
  const end = new Date(`${dateTo}T12:00:00`)
  while (cur <= end) {
    const y = cur.getFullYear()
    const m = String(cur.getMonth() + 1).padStart(2, '0')
    const d = String(cur.getDate()).padStart(2, '0')
    const key = `${y}-${m}-${d}`
    if (!isCompanyRestDay(key, cur, typeMap)) invalid.push(key)
    cur.setDate(cur.getDate() + 1)
  }
  return invalid
}

// 审批人
const approvers1 = ref([])
const approvers2 = ref([])
const loadingApprovers1 = ref(false)
const loadingApprovers2 = ref(false)

async function fetchApprovers() {
  if (!userName) return
  loadingApprovers1.value = true
  loadingApprovers2.value = true
  try {
    const [res1, res2] = await Promise.all([
      getApprovers({ name: userName, level: 'room_director' }),
      getApprovers({ name: userName, level: 'second' }),
    ])
    const self = userName.trim()
    approvers1.value = (res1.success && res1.approvers)
      ? res1.approvers.map(a => a.name).filter(n => n.trim() !== self)
      : []
    approvers2.value = (res2.success && res2.approvers)
      ? res2.approvers.map(a => a.name).filter(n => n.trim() !== self)
      : []
  } catch (err) {
    console.error('获取审批人失败:', err)
  } finally {
    loadingApprovers1.value = false
    loadingApprovers2.value = false
  }
}

// 记录列表
const recordList = ref([])
const nameFilter = ref('')
const _d = new Date()
const recordMonth = ref(`${_d.getFullYear()}-${String(_d.getMonth() + 1).padStart(2, '0')}`)
const recordStatus = ref('all')
const page = ref(1)
const pageSize = ref(10)

const filteredList = computed(() => {
  const kw = nameFilter.value.trim().toLowerCase()
  if (!kw || recordScope.value === 'self') return recordList.value
  return recordList.value.filter(r => (r.applicant || '').toLowerCase().includes(kw))
})
const totalPages = computed(() => Math.max(1, Math.ceil(filteredList.value.length / pageSize.value)))
const paginatedList = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredList.value.slice(start, start + pageSize.value)
})

const recordFilterLabel = computed(() => {
  const m = (recordMonth.value || '').trim()
  const statusMap = { all: '全部', processing: '审批中', approved: '已通过', rejected: '已驳回' }
  const st = statusMap[recordStatus.value] || '全部'
  const scopeMap = { self: '本人', lsys: '本专业', all: '全部科室' }
  const sc = recordScope.value.startsWith('lsys:') ? recordScope.value.slice(5) : (scopeMap[recordScope.value] || '本人')
  const parts = [sc, st]
  if (m) {
    const [y, mo] = m.split('-')
    parts.unshift(`${y}年${parseInt(mo)}月`)
  }
  if (nameFilter.value.trim()) parts.push(`搜索: ${nameFilter.value.trim()}`)
  return parts.join('，')
})

watch([recordMonth, recordStatus, recordScope], () => { page.value = 1; fetchList() })
watch(pageSize, () => { page.value = 1 })

async function fetchList() {
  try {
    const m = (recordMonth.value || '').trim()
    const params = { name: userName, status: recordStatus.value }
    if (m) {
      const [y, mo] = m.split('-')
      if (y) params.year = parseInt(y)
      if (mo) params.month = parseInt(mo)
    }
    if (recordScope.value === 'all') {
      params.scope = 'all'
    } else if (recordScope.value.startsWith('lsys:')) {
      params.scope = 'all'
      params.filter_lsys = recordScope.value.slice(5)
    } else if (recordScope.value === 'lsys') {
      params.scope = 'lsys'
    } else {
      params.scope = 'self'
    }
    const res = await getHolidayExchangeList(params)
    recordList.value = (res.success && res.data) ? res.data : []
  } catch (err) {
    console.error('获取记录失败:', err)
    recordList.value = []
  }
}

function getDownloadUrl(filename) {
  return getHolidayExchangeDownloadUrl(filename)
}

function editRejectedRecord(r) {
  if (!r?.id || r.statusCode !== 22) return
  editingRejectedId.value = r.id
  if (r.dateRanges && Array.isArray(r.dateRanges) && r.dateRanges.length) {
    form.ranges = r.dateRanges.map(seg => ({ from: seg.from || '', to: seg.to || '' }))
  } else {
    form.ranges = [{ from: r.dateFrom || '', to: r.dateTo || '' }]
  }
  form.approver1 = ''
  form.approver2 = ''
  showApplyModal.value = true
}

async function deleteRecord(r) {
  if (!r?.id || r.statusCode !== 22) return
  if (!confirm('确认删除这条已驳回的记录？删除后不可恢复。')) return
  try {
    await deleteHolidayExchangeRecord(r.id, { name: userName })
    alert('已删除')
    fetchList()
  } catch (e) {
    alert(e.response?.data?.detail || e.message || '删除失败')
  }
}

async function handleSubmit() {
  for (let i = 0; i < form.ranges.length; i++) {
    const rng = form.ranges[i]
    if (!rng.from || !rng.to) {
      alert(`第 ${i + 1} 段时间范围未填写完整`)
      return
    }
    if (new Date(rng.to) < new Date(rng.from)) {
      alert(`第 ${i + 1} 段截止日期不能早于起始日期`)
      return
    }
  }
  if (!selectedFiles.value.length) {
    alert('请上传佐证材料')
    return
  }
  if (!form.approver1) {
    alert('请选择一级审批人（科室主任）')
    return
  }
  if (!form.approver2) {
    alert('请选择二级审批人（部长/副部长）')
    return
  }

  submitting.value = true
  try {
    for (let i = 0; i < form.ranges.length; i++) {
      const rng = form.ranges[i]
      const invalidDates = await findInvalidDatesInRange(rng.from, rng.to)
      if (invalidDates.length) {
        const label = form.ranges.length > 1 ? `第 ${i + 1} 段` : ''
        const sample = invalidDates.slice(0, 8).join('、')
        const tail = invalidDates.length > 8 ? ` 等共 ${invalidDates.length} 天` : ''
        alert(
          `${label}公出节假日换休票仅可选择周末及公司节假日（以「假期与调休」维护的数据为准）。` +
            `以下日期为工作日或非放假安排，请调整区间：${sample}${tail}`
        )
        return
      }
    }

    const allFrom = form.ranges.map(r => r.from).sort()
    const allTo = form.ranges.map(r => r.to).sort()

    const fd = new FormData()
    fd.append('name', userName)
    fd.append('department', userDept)
    fd.append('dateFrom', allFrom[0])
    fd.append('dateTo', allTo[allTo.length - 1])
    fd.append('approver1', form.approver1)
    fd.append('approver2', form.approver2)
    if (form.ranges.length > 1) {
      fd.append('dateRanges', JSON.stringify(form.ranges.map(r => ({ from: r.from, to: r.to }))))
    }
    for (const f of selectedFiles.value) {
      fd.append('files', f)
    }

    const isResubmit = !!editingRejectedId.value
    if (isResubmit) {
      fd.append('keepExistingFiles', selectedFiles.value.length ? 'false' : 'true')
    }
    const res = isResubmit
      ? await resubmitHolidayExchangeRecord(editingRejectedId.value, fd)
      : await submitHolidayExchange(fd)
    if (res.success) {
      alert(isResubmit ? `已重新提交！加班 ${res.days} 天，换休票 ${res.hxp_count} 张` : `申请已提交！加班 ${res.days} 天，换休票 ${res.hxp_count} 张`)
      showApplyModal.value = false
      editingRejectedId.value = null
      resetForm()
      fetchList()
    } else {
      alert(res.message || '提交失败')
    }
  } catch (err) {
    const d = err.response?.data?.detail
    alert(Array.isArray(d) ? d.map(x => x.msg || x).join('; ') : (d || err.message || '提交失败'))
  } finally {
    submitting.value = false
  }
}

function resetForm() {
  form.ranges = [{ from: '', to: '' }]
  form.approver1 = ''
  form.approver2 = ''
  selectedFiles.value = []
}

watch(showApplyModal, (v) => {
  if (!v) editingRejectedId.value = null
  if (v) fetchApprovers()
})

onMounted(async () => {
  let isDakaman = false
  try {
    const cfg = await getUploadConfig()
    const dk = (cfg?.dakaman || '').trim()
    isDakaman = !!(dk && userName.trim() === dk)
  } catch {}

  canViewAll.value = isLeaderRole.value || isDakaman

  if (canViewAll.value) {
    try {
      const res = await getDeptLsysList()
      deptOptions.value = (res && res.data) || []
    } catch {}
  }

  fetchList()
})
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
.record-card { overflow: hidden; }
.record-card__header { padding: var(--spacing-lg) var(--spacing-xl); background: white; border-bottom: 1px solid var(--color-border-lighter); display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: var(--spacing-md); }
.record-card__header h3 { margin: 0 0 var(--spacing-xs); }
.record-card__filters { display: flex; align-items: center; gap: var(--spacing-sm); flex-shrink: 0; }
.record-card__filters .filter-label { font-size: var(--font-size-sm); color: var(--color-text-secondary); }
.record-card__filters .filter-input { padding: 6px 10px; border: 1px solid var(--color-border-base); border-radius: var(--radius-sm); font-size: var(--font-size-sm); }
.record-card__filters .filter-input--search { min-width: 7rem; max-width: 10rem; }
.record-card__filters .filter-select { padding: 6px 10px; border: 1px solid var(--color-border-base); border-radius: var(--radius-sm); font-size: var(--font-size-sm); }
.record-card__filters .filter-select--scope { min-width: 9rem; max-width: 18rem; }
.record-card__desc { margin: 0; font-size: var(--font-size-sm); color: var(--color-text-secondary); font-weight: normal; }
.record-card__body { padding: 0; background: white; }
.record-card__body .table-wrap { overflow-x: auto; }
.record-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); background: white; }
.record-table th, .record-table td { padding: 12px var(--spacing-xl); text-align: left; border-bottom: 1px solid var(--color-border-lighter); background: white; }
.record-table th { font-weight: 600; color: var(--color-text-primary); }
.record-table tbody tr:hover td { background: var(--color-bg-spotlight); }
.status-tag { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: var(--font-size-xs); }
.status-approved { color: #059669; background: #d1fae5; }
.status-processing { color: #d97706; background: #fef3c7; }
.status-rejected { color: #dc2626; background: #fee2e2; }
.reject-reason-cell { max-width: 200px; word-break: break-word; color: var(--color-text-secondary); font-size: var(--font-size-xs); }
.file-link { display: inline-block; margin-right: 8px; color: var(--color-primary); text-decoration: none; font-size: var(--font-size-xs); }
.file-link:hover { text-decoration: underline; }
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

.cell-rest-summary {
  max-width: 200px;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  line-height: 1.45;
  word-break: break-word;
}

/* Modal */
.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 100;
}
.modal-content {
  background: white; padding: var(--spacing-xl); border-radius: var(--radius-md);
  width: 700px; max-width: 95%; max-height: 90vh; overflow-y: auto;
}
.application-form { margin-top: var(--spacing-lg); }
.form-row { display: flex; gap: var(--spacing-lg); margin-bottom: var(--spacing-lg); }
.form-group { margin-bottom: var(--spacing-lg); }
.form-group.half { flex: 1; margin-bottom: 0; }
.form-group label { display: block; margin-bottom: var(--spacing-xs); font-weight: 500; font-size: var(--font-size-sm); color: var(--color-text-primary); }
.form-group input, .form-group select, .form-group textarea { width: 100%; padding: 8px 12px; border: 1px solid var(--color-border-base); border-radius: var(--radius-sm); font-size: var(--font-size-base); transition: border-color 0.2s; box-sizing: border-box; }
.form-group input:focus, .form-group select:focus { border-color: var(--color-primary); outline: none; }
.form-group input[readonly] { background-color: var(--color-bg-layout); cursor: not-allowed; }
.required-mark { color: #dc2626; }

.range-item {
  display: flex; align-items: center; gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}
.range-index {
  flex-shrink: 0; font-size: var(--font-size-sm); font-weight: 600;
  color: var(--color-text-secondary); min-width: 20px;
}
.date-range-row { display: flex; align-items: center; gap: var(--spacing-md); flex: 1; }
.date-range-row input { flex: 1; min-width: 130px; }
.date-range-sep { color: var(--color-text-secondary); flex-shrink: 0; }
.range-remove-btn {
  flex-shrink: 0; border: none; background: none; color: #dc2626;
  font-size: 20px; cursor: pointer; padding: 0 4px; line-height: 1;
}
.range-remove-btn:hover { color: #991b1b; }
.range-days {
  flex-shrink: 0; font-size: var(--font-size-xs); color: var(--color-primary);
  font-weight: 500; min-width: 40px; text-align: right;
}
.range-add-btn {
  display: inline-block; padding: 4px 14px; border: 1px dashed var(--color-primary);
  color: var(--color-primary); background: #f0f7ff; border-radius: var(--radius-sm);
  cursor: pointer; font-size: var(--font-size-sm); margin-bottom: var(--spacing-sm);
  transition: background 0.2s;
}
.range-add-btn:hover { background: #dbeafe; }
.range-count-hint { font-weight: 400; font-size: var(--font-size-xs); color: var(--color-text-secondary); }
.cell-range-seg { font-size: var(--font-size-xs); line-height: 1.6; }

.calc-info { margin-top: var(--spacing-sm); padding: var(--spacing-sm) var(--spacing-md); background: #eff6ff; border-radius: var(--radius-sm); border: 1px solid #bfdbfe; }
.calc-info p { margin: 4px 0; font-size: var(--font-size-sm); color: #1e40af; }
.calc-info strong { color: #1d4ed8; }

.date-range-hint {
  margin-top: var(--spacing-sm);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.form-dept-notice {
  margin: var(--spacing-lg) 0 var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-xs);
  font-weight: 600;
  line-height: 1.55;
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-left-width: 4px;
  border-left-color: #dc2626;
  border-radius: var(--radius-sm);
}

/* File upload */
.file-upload-area {
  border: 2px dashed var(--color-border-base);
  border-radius: var(--radius-sm);
  padding: var(--spacing-lg);
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
  min-height: 100px;
}
.file-upload-area:hover { border-color: var(--color-primary); background: #f0f7ff; }
.file-upload-placeholder p { margin: 4px 0; color: var(--color-text-secondary); }
.upload-icon { font-size: 2em; margin-bottom: 4px; }
.upload-hint { font-size: var(--font-size-xs); color: var(--color-text-tertiary); }
.file-list { text-align: left; }
.file-item {
  display: flex; align-items: center; gap: var(--spacing-sm);
  padding: 6px 8px; background: var(--color-bg-layout);
  border-radius: var(--radius-sm); margin-bottom: 6px;
}
.file-name { flex: 1; font-size: var(--font-size-sm); color: var(--color-text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-size { font-size: var(--font-size-xs); color: var(--color-text-tertiary); flex-shrink: 0; }
.file-remove { border: none; background: none; color: #dc2626; font-size: 18px; cursor: pointer; padding: 0 4px; flex-shrink: 0; }
.file-remove:hover { color: #991b1b; }
.upload-more { margin-top: 8px; text-align: center; font-size: var(--font-size-xs); color: var(--color-primary); }

.form-actions {
  display: flex; justify-content: flex-end; gap: var(--spacing-md);
  margin-top: var(--spacing-xxl); padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-border-lighter);
}
button { padding: 8px 20px; border-radius: var(--radius-sm); border: 1px solid var(--color-border-base); cursor: pointer; background: white; font-size: var(--font-size-base); transition: all 0.2s; }
button:hover { border-color: var(--color-primary-light); color: var(--color-primary); }
button:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-primary { background: var(--color-primary); color: white; border-color: var(--color-primary); }
.btn-primary:hover { background: var(--color-primary-light); border-color: var(--color-primary-light); color: white; }
.btn-outline { border-color: var(--color-primary); color: var(--color-primary); }
</style>
