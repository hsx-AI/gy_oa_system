<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">换休票明细查询</h1>
          <p class="header-subtitle">汇总查看所有人的公出节假日换休票申请记录</p>
        </div>
        <div class="header-actions">
          <router-link to="/" class="btn btn-outline">← 返回首页</router-link>
        </div>
      </div>
    </div>

    <div v-if="!canAccess" class="content mt-xl">
      <div class="card record-card">
        <div class="record-empty">
          <p>您暂无权限访问此页面，仅部长、副部长或人事管理员可查看。</p>
          <router-link to="/" class="btn btn-primary" style="margin-top:12px">返回首页</router-link>
        </div>
      </div>
    </div>

    <div v-else class="content mt-xl">
      <div class="card record-card">
        <div class="card-header record-card__header">
          <div>
            <h3>换休票记录</h3>
            <p class="record-card__desc">{{ filterLabel }}</p>
          </div>
          <div class="record-card__filters">
            <label class="filter-label">范围</label>
            <select v-model="scopeVal" class="filter-select filter-select--scope">
              <option value="self">本人</option>
              <option value="lsys">本专业</option>
              <template v-if="canViewAll">
                <option value="all">全部科室</option>
                <option v-for="d in deptOptions" :key="d" :value="'lsys:' + d">{{ d }}</option>
              </template>
            </select>
            <label class="filter-label">年份</label>
            <select v-model.number="yearVal" class="filter-select">
              <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option>
            </select>
            <label class="filter-label">状态</label>
            <select v-model="statusVal" class="filter-select">
              <option value="all">全部</option>
              <option value="approved">已通过</option>
              <option value="processing">审批中</option>
              <option value="rejected">已驳回</option>
            </select>
            <input
              v-model.trim="nameFilter"
              type="search"
              class="filter-input filter-input--search"
              placeholder="姓名"
              aria-label="姓名筛选"
            >
          </div>
        </div>
        <div class="card-body record-card__body">
          <div v-if="loading" class="record-empty">加载中…</div>
          <div v-else-if="filteredRecords.length === 0" class="record-empty">暂无记录</div>
          <div v-else class="table-wrap">
            <table class="record-table">
              <thead>
                <tr>
                  <th>姓名</th>
                  <th>科室</th>
                  <th>加班日期</th>
                  <th>日期性质</th>
                  <th>天数</th>
                  <th>换休票</th>
                  <th>佐证材料</th>
                  <th>状态</th>
                  <th>一级审批</th>
                  <th>二级审批</th>
                  <th>申请时间</th>
                  <th>驳回原因</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in filteredRecords" :key="r.id" @click="openDetail(r)" class="clickable-row">
                  <td class="td-name">{{ r.applicant }}</td>
                  <td>{{ r.department }}</td>
                  <td>
                    <template v-if="r.dateRanges && r.dateRanges.length > 1">
                      <div v-for="(seg, si) in r.dateRanges" :key="si" class="cell-range-seg">{{ seg.from }} ~ {{ seg.to }}</div>
                    </template>
                    <template v-else>{{ r.dateFrom === r.dateTo ? r.dateFrom : r.dateFrom + ' ~ ' + r.dateTo }}</template>
                  </td>
                  <td class="cell-rest-summary" :title="r.restDaySummary">{{ r.restDaySummary || '—' }}</td>
                  <td class="td-num">{{ r.days }}</td>
                  <td class="td-num td-hxp">{{ formatHxp(r.hxpCount) }}</td>
                  <td>
                    <template v-if="r.materialFiles && r.materialFiles.length">
                      <a
                        v-for="(f, fi) in r.materialFiles"
                        :key="fi"
                        :href="getDownloadUrl(f.name)"
                        target="_blank"
                        rel="noopener"
                        class="file-link"
                        @click.stop
                      >{{ f.original || f.name }}</a>
                    </template>
                    <span v-else class="td-muted">—</span>
                  </td>
                  <td><span class="status-tag" :class="r.statusClass">{{ r.status }}</span></td>
                  <td>{{ r.spr }}</td>
                  <td>{{ r.spr2 }}</td>
                  <td>{{ r.applyTime }}</td>
                  <td class="reject-reason-cell">{{ r.statusCode === 22 && r.rejectReason ? r.rejectReason : '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="filteredRecords.length > 0" class="record-card__footer">
            共 <strong>{{ filteredRecords.length }}</strong> 条，
            合计换休票 <strong>{{ totalHxp }}</strong> 张
          </div>
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="detailRecord" class="modal-overlay" @click.self="detailRecord = null">
      <div class="detail-modal">
        <div class="detail-modal__header">
          <h3>换休票申请详情</h3>
          <button type="button" class="detail-modal__close" @click="detailRecord = null">&times;</button>
        </div>
        <div class="detail-modal__body">
          <p><strong>申请人：</strong>{{ detailRecord.applicant }}</p>
          <p><strong>科室：</strong>{{ detailRecord.department || '—' }}</p>
          <template v-if="detailRecord.dateRanges && detailRecord.dateRanges.length > 1">
            <p><strong>加班时间段：</strong>共 {{ detailRecord.dateRanges.length }} 段</p>
            <div class="detail-ranges">
              <div v-for="(seg, si) in detailRecord.dateRanges" :key="si" class="detail-range-line">
                {{ si + 1 }}. {{ seg.from }} 至 {{ seg.to }}
              </div>
            </div>
          </template>
          <template v-else>
            <p><strong>加班开始日期：</strong>{{ detailRecord.dateFrom }}</p>
            <p><strong>加班截止日期：</strong>{{ detailRecord.dateTo }}</p>
          </template>
          <p><strong>日期性质：</strong>{{ detailRecord.restDaySummary || '—' }}</p>
          <div v-if="detailRecord.restDayBreakdown && detailRecord.restDayBreakdown.length" class="detail-breakdown">
            <p><strong>逐日说明：</strong></p>
            <ul class="detail-breakdown-list">
              <li v-for="(line, li) in detailRecord.restDayBreakdown" :key="li"
                  :class="{ 'breakdown-sep': line.startsWith('---') }">{{ line }}</li>
            </ul>
          </div>
          <p><strong>加班天数：</strong>{{ detailRecord.days }} 天</p>
          <p><strong>换休票数量：</strong>{{ formatHxp(detailRecord.hxpCount) }} 张</p>
          <div>
            <p><strong>佐证材料：</strong></p>
            <ul v-if="detailRecord.materialFiles && detailRecord.materialFiles.length" class="detail-file-list">
              <li v-for="(f, fi) in detailRecord.materialFiles" :key="fi">
                <a :href="getDownloadUrl(f.name)" target="_blank" rel="noopener">{{ f.original || f.name }}</a>
              </li>
            </ul>
            <p v-else class="td-muted">无</p>
          </div>
          <p><strong>一级审批人：</strong>{{ detailRecord.spr }}</p>
          <p><strong>二级审批人：</strong>{{ detailRecord.spr2 }}</p>
          <p><strong>申请时间：</strong>{{ detailRecord.applyTime }}</p>
          <p><strong>审批状态：</strong><span class="status-tag" :class="detailRecord.statusClass">{{ detailRecord.status }}</span></p>
          <p v-if="detailRecord.statusCode === 22 && detailRecord.rejectReason"><strong>驳回原因：</strong>{{ detailRecord.rejectReason }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getHolidayExchangeList, getDeptLsysList, getUploadConfig, getHolidayExchangeDownloadUrl } from '@/api/attendance'

const route = useRoute()
const now = new Date()

function getStoredUserInfo() {
  try { return JSON.parse(localStorage.getItem('userInfo') || '{}') } catch { return {} }
}

const userInfo = getStoredUserInfo()
const userName = ref(userInfo.name || userInfo.userName || '')
const userJb = ref((userInfo.jb || '').trim())
const canAccess = ref(false)

const isMinister = computed(() => {
  const jb = userJb.value
  return jb === '部长' || jb.startsWith('部长') || jb === '副部长' || jb.startsWith('副部长')
})

const canViewAll = computed(() => isMinister.value)

const deptOptions = ref([])
const scopeVal = ref('self')
const yearVal = ref(now.getFullYear())
const statusVal = ref('all')
const nameFilter = ref('')
const records = ref([])
const loading = ref(false)

const yearOptions = computed(() => {
  const cur = now.getFullYear()
  return Array.from({ length: cur - 2020 }, (_, i) => cur - i)
})

const filteredRecords = computed(() => {
  const kw = nameFilter.value.trim().toLowerCase()
  if (!kw) return records.value
  return records.value.filter(r => (r.applicant || '').toLowerCase().includes(kw))
})

const totalHxp = computed(() => {
  const s = filteredRecords.value.reduce((a, r) => a + (r.hxpCount || 0), 0)
  return s === Math.floor(s) ? s : s.toFixed(2)
})

const filterLabel = computed(() => {
  const parts = []
  parts.push(`${yearVal.value}年`)
  const st = { all: '全部', approved: '已通过', processing: '审批中', rejected: '已驳回' }
  parts.push(st[statusVal.value] || '全部')
  if (scopeVal.value === 'self') parts.push('本人')
  else if (scopeVal.value === 'lsys') parts.push('本专业')
  else if (scopeVal.value === 'all') parts.push('全部科室')
  else if (scopeVal.value.startsWith('lsys:')) parts.push(scopeVal.value.slice(5))
  if (nameFilter.value.trim()) parts.push(`搜索: ${nameFilter.value.trim()}`)
  return parts.join('，')
})

const detailRecord = ref(null)

function openDetail(r) {
  detailRecord.value = r
}

function getDownloadUrl(filename) {
  return getHolidayExchangeDownloadUrl(filename)
}

function formatHxp(v) {
  if (v == null) return '—'
  const f = parseFloat(v)
  return f === Math.floor(f) ? f : parseFloat(f.toFixed(4))
}

async function fetchRecords() {
  loading.value = true
  try {
    const params = { name: userName.value, year: yearVal.value, status: statusVal.value }
    if (scopeVal.value === 'all') {
      params.scope = 'all'
    } else if (scopeVal.value.startsWith('lsys:')) {
      params.scope = 'all'
      params.filter_lsys = scopeVal.value.slice(5)
    } else {
      params.scope = scopeVal.value
    }
    const res = await getHolidayExchangeList(params)
    records.value = (res && res.data) || []
  } catch {
    records.value = []
  } finally {
    loading.value = false
  }
}

watch([scopeVal, yearVal, statusVal], () => { fetchRecords() })

onMounted(async () => {
  let isAdmin2 = false
  try {
    const cfg = await getUploadConfig()
    const a2 = (cfg?.admin2 || '').trim()
    isAdmin2 = !!(a2 && userName.value.trim() === a2)
  } catch {}
  canAccess.value = isMinister.value || isAdmin2
  if (!canAccess.value) return

  const q = route.query
  if (q.scope) scopeVal.value = q.scope
  if (q.year) yearVal.value = parseInt(q.year) || yearVal.value
  if (q.status) statusVal.value = q.status
  if (q.focusName) nameFilter.value = q.focusName

  if (canViewAll.value) {
    try {
      const res = await getDeptLsysList()
      deptOptions.value = (res && res.data) || []
    } catch {}
  }

  await fetchRecords()
})
</script>

<style scoped>
.page-container {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0 0 var(--spacing-xl);
}

.btn-outline { background: white; border: 1px solid var(--color-primary); color: var(--color-primary); text-decoration: none; }
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
  flex-wrap: wrap;
}

.record-card__filters .filter-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.record-card__filters .filter-select--scope {
  min-width: 10rem;
  max-width: 20rem;
}

.record-card__filters .filter-select {
  padding: 6px 10px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
}

.record-card__filters .filter-input {
  padding: 6px 10px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
}

.record-card__filters .filter-input--search {
  min-width: 8rem;
  flex: 1;
  max-width: 14rem;
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

.td-name { font-weight: 500; }
.td-num { text-align: center; }
.td-hxp { color: var(--color-primary); font-weight: 600; }

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

.record-card__footer {
  padding: var(--spacing-md) var(--spacing-xl);
  border-top: 1px solid var(--color-border-lighter);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.record-card__footer strong {
  color: var(--color-primary);
}

.record-empty {
  padding: var(--spacing-xxl);
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.clickable-row { cursor: pointer; }

.cell-rest-summary {
  max-width: 180px;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  line-height: 1.45;
  word-break: break-word;
}
.cell-range-seg { font-size: var(--font-size-xs); line-height: 1.6; }

.file-link {
  display: inline-block;
  margin-right: 6px;
  color: var(--color-primary);
  text-decoration: none;
  font-size: var(--font-size-xs);
}
.file-link:hover { text-decoration: underline; }

.td-muted { color: var(--color-text-tertiary); }

.reject-reason-cell {
  max-width: 160px;
  word-break: break-word;
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}

/* 详情弹窗 */
.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 100;
}
.detail-modal {
  background: white;
  border-radius: var(--radius-md);
  width: 680px;
  max-width: 95vw;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg, 0 10px 40px rgba(0,0,0,0.15));
}
.detail-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
}
.detail-modal__header h3 { margin: 0; }
.detail-modal__close {
  border: none; background: none; font-size: 24px;
  cursor: pointer; color: var(--color-text-tertiary); padding: 0 4px; line-height: 1;
}
.detail-modal__close:hover { color: var(--color-text-primary); }
.detail-modal__body {
  overflow-y: auto;
  padding: var(--spacing-lg) var(--spacing-xl) var(--spacing-xl);
  font-size: var(--font-size-sm);
  line-height: 1.8;
}
.detail-modal__body p { margin: 4px 0; }
.detail-ranges { padding-left: var(--spacing-md); margin-bottom: var(--spacing-sm); }
.detail-range-line { font-size: var(--font-size-sm); line-height: 1.7; }
.detail-breakdown { margin: var(--spacing-sm) 0; }
.detail-breakdown-list {
  margin: var(--spacing-xs) 0 0;
  padding-left: 1.25rem;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.5;
}
.detail-breakdown-list li { margin-bottom: 4px; }
.detail-breakdown-list li.breakdown-sep {
  list-style: none; margin-left: -1.25rem;
  font-weight: 600; color: var(--color-text-primary);
  margin-top: var(--spacing-sm);
}
.detail-file-list {
  margin: var(--spacing-xs) 0;
  padding-left: 1.25rem;
}
.detail-file-list li { margin-bottom: 4px; }
.detail-file-list a {
  color: var(--color-primary);
  text-decoration: none;
}
.detail-file-list a:hover { text-decoration: underline; }

@media (max-width: 768px) {
  .record-card__header {
    flex-direction: column;
  }
  .record-card__filters {
    flex-wrap: wrap;
    width: 100%;
  }
}
</style>
