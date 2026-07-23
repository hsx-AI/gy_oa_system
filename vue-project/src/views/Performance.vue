<template>
  <div class="performance-page">
    <div class="page-header">
      <div><h1>月度绩效</h1><p>按姓名首字母排序录入；可直接从 Excel 复制一列得分后粘贴到任一得分格。</p></div>
      <div class="header-actions"><button class="btn btn-secondary" @click="activeTab = 'history'">查看往期统计</button></div>
    </div>

    <div v-if="loadingPermission" class="card empty">正在加载权限…</div>
    <template v-else-if="permission.can_edit">
      <div class="tabs"><button :class="{ active: activeTab === 'entry' }" @click="activeTab = 'entry'">绩效录入</button><button :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">往期统计</button></div>
      <section v-if="activeTab === 'entry'" class="card">
        <div class="toolbar">
          <label>考核月份 <input v-model="month" type="month" @change="loadRoster" /></label>
          <span class="dept-name">班组：{{ permission.department }}</span>
          <span class="entry-hint">标记“总师 / 新入职”的人员不参与排名，排名与百分比自动置空。</span>
          <button class="btn btn-primary" :disabled="loading || saving" @click="save">{{ saving ? '保存中…' : '保存并计算排名' }}</button>
        </div>
        <div v-if="loading" class="empty">正在加载人员…</div>
        <div v-else class="table-wrap">
          <table class="performance-table"><thead><tr><th>#</th><th>班组</th><th>姓名</th><th>绩效得分</th><th>职级</th><th>标记</th><th>排名百分比</th><th>排名</th><th>绩效等级</th></tr></thead>
            <tbody><tr v-for="(row, index) in roster" :key="row.employee_name"><td>{{ index + 1 }}</td><td>{{ row.department }}</td><td class="name">{{ row.employee_name }}</td>
              <td><input v-model="row.score" inputmode="decimal" class="score-input" placeholder="粘贴得分" @paste="pasteScores(index, $event)" /></td><td>{{ row.job_level || '—' }}</td>
              <td><select v-model="row.marker"><option value="">无</option><option value="总师">总师</option><option value="新入职">新入职</option></select></td>
              <td>{{ formatPercent(row.rank_percent) }}</td><td>{{ row.rank_no ?? '—' }}</td><td><span v-if="row.performance_grade" class="grade">{{ row.performance_grade }}</span><span v-else>—</span></td></tr></tbody>
          </table>
          <p v-if="!roster.length" class="empty">该班组暂无在职人员。</p>
        </div>
      </section>
      <PerformanceHistoryPanel v-else />
    </template>
    <div v-else class="card empty">仅班组长、主任或副主任可录入绩效。</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getPerformancePermission, getPerformanceRoster, savePerformance } from '@/api/performance'
import PerformanceHistoryPanel from '@/components/PerformanceHistoryPanel.vue'

const now = new Date()
const month = ref(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`)
const activeTab = ref('entry')
const permission = ref({ can_edit: false, department: '' })
const roster = ref([])
const loadingPermission = ref(true), loading = ref(false), saving = ref(false)
const currentUser = computed(() => { try { const u = JSON.parse(localStorage.getItem('userInfo') || '{}'); return (u.name || u.userName || '').trim() } catch { return '' } })
const collator = new Intl.Collator('zh-Hans-CN', { sensitivity: 'base' })
const formatPercent = (value) => value == null ? '—' : `${(Number(value) * 100).toFixed(1)}%`

async function loadRoster () {
  if (!permission.value.can_edit) return
  loading.value = true
  try {
    const res = await getPerformanceRoster({ current_user: currentUser.value, month: month.value })
    roster.value = (res.list || []).sort((a, b) => collator.compare(a.employee_name, b.employee_name))
  } catch (error) { alert(error?.response?.data?.detail || '加载绩效人员失败') } finally { loading.value = false }
}
function pasteScores (startIndex, event) {
  const text = event.clipboardData?.getData('text/plain') || ''
  const values = text.replace(/\r/g, '').split('\n').map(v => v.trim()).filter(v => v !== '')
  if (values.length < 2) return
  event.preventDefault()
  values.forEach((value, offset) => { if (roster.value[startIndex + offset]) roster.value[startIndex + offset].score = value })
}
async function save () {
  saving.value = true
  try {
    await savePerformance({ current_user: currentUser.value, month: month.value, entries: roster.value.map(row => ({ employee_name: row.employee_name, score: row.score === '' || row.score == null ? null : Number(row.score), marker: row.marker || '', job_level: row.job_level })) })
    await loadRoster()
    alert('已保存，并按科室有效得分重新计算排名。')
  } catch (error) { alert(error?.response?.data?.detail || '保存失败，请检查得分格式') } finally { saving.value = false }
}
onMounted(async () => { try { permission.value = await getPerformancePermission({ current_user: currentUser.value }); await loadRoster() } catch (error) { alert('获取绩效权限失败') } finally { loadingPermission.value = false } })
</script>

<style scoped>
.performance-page{padding:24px;max-width:1440px;margin:auto}.page-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}.page-header h1{margin:0 0 8px;font-size:26px}.page-header p,.entry-hint{color:#6b7280;margin:0}.card{background:#fff;border-radius:12px;box-shadow:0 2px 12px #0f172a0d;padding:20px}.tabs{display:flex;gap:4px;margin-bottom:16px}.tabs button{border:0;background:#eaf0f7;padding:9px 18px;border-radius:7px;cursor:pointer}.tabs .active{background:#1677ff;color:#fff}.toolbar{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:16px}.toolbar label{font-weight:600}.toolbar input,.toolbar select,select,.score-input{height:34px;border:1px solid #d7dce5;border-radius:5px;padding:0 9px;background:#fff}.dept-name{font-weight:600;color:#1d4ed8}.entry-hint{flex:1;min-width:230px;font-size:13px}.table-wrap{overflow:auto}.performance-table{width:100%;border-collapse:collapse;min-width:840px}.performance-table th{background:#f4f7fb;color:#475569;text-align:left}.performance-table th,.performance-table td{border-bottom:1px solid #e9edf3;padding:10px 12px}.performance-table .name{font-weight:600}.score-input{width:112px;text-align:right}.empty{text-align:center;color:#64748b;padding:40px}.btn{border:0;border-radius:6px;padding:9px 15px;cursor:pointer}.btn-primary{background:#1677ff;color:#fff}.btn-secondary{background:#e8eef6;color:#334155}@media(max-width:700px){.performance-page{padding:14px}.page-header{align-items:flex-start;gap:10px;flex-direction:column}}
.grade{display:inline-block;background:#e8f3ff;color:#145bb6;font-weight:700;border-radius:10px;padding:2px 8px}
</style>
