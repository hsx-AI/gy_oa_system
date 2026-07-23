<template>
  <section class="performance-history card">
    <div class="history-head"><div><h2>{{ dashboard ? '全员绩效统计' : '科室绩效统计' }}</h2><p>按月查询已录入的绩效得分、标记和自动排名。</p></div><slot name="action" /></div>
    <div v-if="loadingPermission" class="empty">正在加载…</div>
    <template v-else-if="permission.scope !== 'self'">
      <div class="filters">
        <label>年份 <select v-model="year" @change="load"><option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option></select></label>
        <label>月份 <select v-model="month" @change="load"><option value="">全年</option><option v-for="m in 12" :key="m" :value="m">{{ m }}月</option></select></label>
        <label v-if="permission.scope === 'all'">班组 <select v-model="department" @change="load"><option value="">全部班组</option><option v-for="item in departments" :key="item" :value="item">{{ item }}</option></select></label>
        <label>姓名 <input v-model.trim="employeeName" placeholder="精确姓名" @keyup.enter="load" /></label><button class="btn btn-primary" @click="load">查询</button>
      </div>
      <div class="table-wrap"><table><thead><tr><th>月份</th><th>班组</th><th>姓名</th><th>绩效得分</th><th>职级</th><th>标记</th><th>排名百分比</th><th>排名</th><th>绩效等级</th></tr></thead>
        <tbody><tr v-for="row in rows" :key="`${row.month}-${row.employee_name}`"><td>{{ row.month }}</td><td>{{ row.department }}</td><td class="name">{{ row.employee_name }}</td><td>{{ row.score ?? '—' }}</td><td>{{ row.job_level || '—' }}</td><td><span v-if="row.marker" class="marker">{{ row.marker }}</span><span v-else>—</span></td><td>{{ pct(row.rank_percent) }}</td><td>{{ row.rank_no ?? '—' }}</td><td><span v-if="row.performance_grade" class="grade">{{ row.performance_grade }}</span><span v-else>—</span></td></tr></tbody></table><p v-if="!rows.length" class="empty">暂无符合条件的绩效数据。</p></div>
    </template><div v-else class="empty">暂无查看科室绩效统计的权限。</div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getPerformanceDepartments, getPerformanceHistory, getPerformancePermission } from '@/api/performance'
const props = defineProps({ dashboard: { type: Boolean, default: false } })
const date = new Date(), year = ref(date.getFullYear()), month = ref(''), department = ref(''), employeeName = ref('')
const rows = ref([]), departments = ref([]), permission = ref({ scope: 'self' }), loadingPermission = ref(true)
const currentUser = computed(() => { try { const u = JSON.parse(localStorage.getItem('userInfo') || '{}'); return (u.name || u.userName || '').trim() } catch { return '' } })
const yearOptions = computed(() => Array.from({ length: 5 }, (_, i) => date.getFullYear() - i))
const pct = v => v == null ? '—' : `${(Number(v) * 100).toFixed(1)}%`
async function load () { try { const res = await getPerformanceHistory({ current_user: currentUser.value, year: year.value, month: month.value || undefined, department: department.value || undefined, employee_name: employeeName.value || undefined }); rows.value = res.list || [] } catch (e) { rows.value = []; alert(e?.response?.data?.detail || '绩效统计加载失败') } }
onMounted(async () => { try { permission.value = await getPerformancePermission({ current_user: currentUser.value }); const res = await getPerformanceDepartments({ current_user: currentUser.value }); departments.value = res.list || []; if (permission.value.scope !== 'all') department.value = permission.value.department || ''; if (permission.value.scope !== 'self') await load() } finally { loadingPermission.value = false } })
</script>

<style scoped>
.card{background:#fff;border-radius:12px;box-shadow:0 2px 12px #0f172a0d;padding:20px}.history-head{display:flex;justify-content:space-between;align-items:start;gap:12px}.history-head h2{font-size:19px;margin:0 0 6px}.history-head p{margin:0;color:#64748b;font-size:13px}.filters{display:flex;gap:12px;align-items:end;flex-wrap:wrap;margin:18px 0}.filters label{display:flex;flex-direction:column;gap:5px;color:#475569;font-size:13px}.filters select,.filters input{height:34px;border:1px solid #d7dce5;border-radius:5px;padding:0 9px;background:#fff;min-width:90px}.table-wrap{overflow:auto}.table-wrap table{width:100%;border-collapse:collapse;min-width:800px}.table-wrap th{background:#f4f7fb;color:#475569;text-align:left}.table-wrap th,.table-wrap td{border-bottom:1px solid #e9edf3;padding:10px 12px}.name{font-weight:600}.marker{background:#fff7d6;color:#9a6700;padding:2px 7px;border-radius:10px;font-size:12px}.empty{text-align:center;color:#64748b;padding:28px}.btn{height:34px;border:0;border-radius:5px;padding:0 14px;cursor:pointer}.btn-primary{background:#1677ff;color:#fff}
.grade{display:inline-block;background:#e8f3ff;color:#145bb6;font-weight:700;border-radius:10px;padding:2px 8px}
</style>
