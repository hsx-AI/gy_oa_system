<template>
  <section class="quarterly-entry card">
    <div class="entry-head"><div><h2>季度绩效录入</h2><p>本季度绩效合计仅供参考，不参与季度绩效总分；工作业绩满分 70 分、能力素养满分 20 分、行为表现满分 10 分，总分不超过 100 分。</p></div>
      <div class="quarter-picker"><label>考核季度 <select v-model="quarter" @change="load"><option v-for="item in quarters" :key="item" :value="item">{{ item }}</option></select></label><button class="btn btn-secondary" :disabled="loading || saving || !rows.length" @click="autoFill">按本季度绩效合计自动填充</button><button class="btn btn-primary" :disabled="loading || saving" @click="save">{{ saving ? '保存中…' : '保存并计算' }}</button></div>
    </div>
    <div v-if="loading" class="empty">正在汇总本季度月绩效…</div>
    <div v-else class="table-wrap"><table><thead><tr><th>#</th><th>班组</th><th>姓名</th><th>职级</th><th>本季度绩效合计<br><small>仅供参考，不参与季度绩效</small></th><th>工作业绩得分</th><th>能力素养得分</th><th>行为表现得分</th><th>加/减分</th><th>总分</th><th>排名</th><th>考核等级</th><th>备注</th></tr></thead>
      <tbody><tr v-for="(row, index) in rows" :key="row.employee_name"><td>{{ index + 1 }}</td><td>{{ row.department }}</td><td class="name">{{ row.employee_name }}</td><td>{{ row.job_level || '—' }}</td><td>{{ number(row.monthly_total) }}</td><td><input v-model="row.work_performance_score" type="number" min="0" max="70" step="0.01" class="score" /></td>
        <td><input v-model="row.ability_score" type="number" min="0" max="20" step="0.01" class="score" /></td><td><input v-model="row.behavior_score" type="number" min="0" max="10" step="0.01" class="score" /></td><td><input v-model="row.adjustment_score" type="number" min="-100" max="100" step="0.01" class="score" /></td><td class="total">{{ number(total(row)) }}</td><td>{{ row.rank_no ?? '—' }}</td>
        <td><select v-model="row.gradeValue" @change="row.grade_manual = !!row.gradeValue"><option value="">自动（{{ row.auto_grade || '待计算' }}）</option><option value="A">A</option><option value="B+">B+</option><option value="B">B</option><option value="C">C</option></select></td><td><input v-model.trim="row.remark" class="remark" placeholder="选填" /></td></tr></tbody></table>
      <p v-if="!rows.length" class="empty">该科室暂无在职人员。</p></div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getQuarterlyPerformanceRoster, saveQuarterlyPerformance } from '@/api/performance'
const current = new Date(), rows = ref([]), loading = ref(false), saving = ref(false)
const currentUser = computed(() => { try { const user = JSON.parse(localStorage.getItem('userInfo') || '{}'); return (user.name || user.userName || '').trim() } catch { return '' } })
function currentQuarter () { return `${current.getFullYear()}-Q${Math.floor(current.getMonth() / 3) + 1}` }
const quarter = ref(currentQuarter())
const quarters = computed(() => { const list = []; for (let year = current.getFullYear(); year >= current.getFullYear() - 2; year--) for (let q = 4; q >= 1; q--) list.push(`${year}-Q${q}`); return list })
const number = value => value == null || value === '' ? '' : Number(value).toFixed(2).replace(/\.00$/, '')
const total = row => {
  const hasScore = [row.work_performance_score, row.ability_score, row.behavior_score].some(value => value !== '' && value != null) || Number(row.adjustment_score || 0) !== 0
  return hasScore ? Number(row.work_performance_score || 0) + Number(row.ability_score || 0) + Number(row.behavior_score || 0) + Number(row.adjustment_score || 0) : null
}
function autoFill () {
  if (!window.confirm('本系统自动填充数据仅为了方便填写，请认真审查！')) return
  const count = rows.value.length
  rows.value.forEach((row, index) => {
    const factor = count <= 1 ? 1 : (count - index - 1) / (count - 1)
    // 自动填充的基础总分限定在 60–99 分，避免自动给出满分，再按 70/20/10 拆分。
    const targetTotal = Math.round(60 + 39 * factor)
    row.work_performance_score = Math.round(targetTotal * 0.7)
    row.ability_score = Math.round(targetTotal * 0.2)
    row.behavior_score = targetTotal - row.work_performance_score - row.ability_score
  })
}
async function load () { loading.value = true; try { const res = await getQuarterlyPerformanceRoster({ current_user: currentUser.value, quarter: quarter.value }); rows.value = (res.list || []).map(row => ({ ...row, gradeValue: row.grade_manual ? row.assessment_grade : '', auto_grade: row.assessment_grade || '' })) } catch (error) { alert(error?.response?.data?.detail || '加载季度绩效失败') } finally { loading.value = false } }
async function save () { saving.value = true; try { await saveQuarterlyPerformance({ current_user: currentUser.value, quarter: quarter.value, entries: rows.value.map(row => ({ employee_name: row.employee_name, work_performance_score: row.work_performance_score == null || row.work_performance_score === '' ? null : Number(row.work_performance_score), ability_score: row.ability_score == null || row.ability_score === '' ? null : Number(row.ability_score), behavior_score: row.behavior_score == null || row.behavior_score === '' ? null : Number(row.behavior_score), adjustment_score: row.adjustment_score === '' ? 0 : Number(row.adjustment_score || 0), assessment_grade: row.gradeValue || '', grade_manual: !!row.gradeValue, remark: row.remark || '' })) }); await load(); alert('季度绩效已保存。') } catch (error) { alert(error?.response?.data?.detail || '保存失败，请检查填写内容') } finally { saving.value = false } }
onMounted(load)
</script>

<style scoped>
.card{background:#fff;border-radius:12px;box-shadow:0 2px 12px #0f172a0d;padding:20px}.entry-head{display:flex;justify-content:space-between;gap:16px;align-items:start;margin-bottom:18px}.entry-head h2{margin:0 0 6px;font-size:19px}.entry-head p{margin:0;color:#64748b;font-size:13px}.quarter-picker{display:flex;align-items:end;gap:10px;white-space:nowrap}.quarter-picker label{display:flex;flex-direction:column;gap:5px;font-size:13px;color:#475569}.quarter-picker select,input{height:34px;border:1px solid #d7dce5;border-radius:5px;padding:0 8px;background:#fff}.table-wrap{overflow:auto}.table-wrap table{width:100%;border-collapse:collapse;min-width:1420px}.table-wrap th{background:#f4f7fb;color:#475569;text-align:left}.table-wrap th small{font-weight:400;color:#94a3b8;white-space:nowrap}.table-wrap th,.table-wrap td{border-bottom:1px solid #e9edf3;padding:9px 10px}.name{font-weight:600}.score{width:88px;text-align:right}.remark{width:120px}.total{font-weight:700;color:#145bb6}.btn{height:34px;border:0;border-radius:5px;padding:0 14px;cursor:pointer}.btn-primary{background:#1677ff;color:#fff}.btn-secondary{background:#e8eef6;color:#334155}.empty{text-align:center;color:#64748b;padding:32px}@media(max-width:700px){.entry-head{flex-direction:column}.quarter-picker{align-items:center}}
</style>
