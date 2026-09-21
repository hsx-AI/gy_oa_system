<template>
  <div class="perf-page">
    <header class="perf-head">
      <div>
        <h1>绩效统计</h1>
        <p>智能制造技术室按月在线填报。每人只填自己的绩效行和会议纪实，科室汇总后按合计排名。</p>
      </div>
      <label class="month-box">考核月份
        <input v-model="month" type="month" @change="load">
      </label>
    </header>

    <div v-if="loading" class="panel muted">正在加载…</div>
    <div v-else-if="errorText" class="panel error">{{ errorText }}</div>
    <div v-else-if="!access.can_fill && !access.can_summary" class="panel">
      <h2>该科室尚未开放</h2>
      <p>目前只开放智能制造技术室。其他科室暂不做线上填报。</p>
    </div>
    <template v-else>
      <section class="rules">
        <h2>填报规则</h2>
        <ol>
          <li>第一张表是绩效填报表，表头以下每人一行。你只能看到并填写自己那一行。</li>
          <li>第二张表是你自己的会议纪实，按月记录。</li>
          <li>科室主任、副主任和班组长打开汇总表，能看到全员数据，但只能改自己的行和自己的会议纪实。</li>
          <li>科室主任可以更新模板。模板仍然是第一页绩效表、第二页会议纪实，姓名列不变。</li>
        </ol>
      </section>

      <section class="actions">
        <button v-if="access.can_fill" type="button" class="btn primary" :disabled="opening" @click="openDoc('mine')">填写我的绩效</button>
        <button v-if="access.can_summary" type="button" class="btn" :disabled="opening" @click="openDoc('summary')">打开科室汇总</button>
        <label v-if="access.can_update_template" class="btn">
          更新科室模板
          <input type="file" hidden accept=".xlsx" @change="onTemplate">
        </label>
        <span v-if="access.can_fill" class="status" :class="{ on: mineFilled }">{{ mineFilled ? '本月已有填报' : '本月尚未填报' }}</span>
      </section>

      <section v-if="access.can_summary" class="panel">
        <h2>本月填报情况</h2>
        <table>
          <thead><tr><th>姓名</th><th>状态</th></tr></thead>
          <tbody>
            <tr v-for="person in people" :key="person.name">
              <td>{{ person.name }}</td>
              <td><span class="pill" :class="{ on: person.filled }">{{ person.filled ? '已填写' : '未填写' }}</span></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!people.length" class="muted">暂无科室人员</p>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getPerformanceOnlineContext, openPerformanceOnline, uploadPerformanceTemplate } from '@/api/performance'

const router = useRouter()
const loading = ref(true)
const opening = ref(false)
const errorText = ref('')
const month = ref(new Date().toISOString().slice(0, 7))
const access = ref({ can_fill: false, can_summary: false, can_update_template: false, department: '' })
const people = ref([])
const mineFilled = ref(false)
const pilot = ref('智能制造技术室')

const currentUser = computed(() => {
  try {
    const user = JSON.parse(localStorage.getItem('userInfo') || '{}')
    return (user.name || user.userName || '').trim()
  } catch (e) {
    return ''
  }
})

function detailOf(err) {
  const detail = err && err.response && err.response.data && err.response.data.detail
  return (typeof detail === 'string' && detail) || (err && err.message) || '操作失败'
}

async function load() {
  loading.value = true
  errorText.value = ''
  try {
    const res = await getPerformanceOnlineContext({ current_user: currentUser.value, month: month.value })
    access.value = res.access || access.value
    people.value = res.people || []
    mineFilled.value = !!res.mine_filled
    pilot.value = res.pilot_department || pilot.value
    if (res.month) month.value = res.month
  } catch (err) {
    errorText.value = detailOf(err)
  } finally {
    loading.value = false
  }
}

async function openDoc(scope) {
  opening.value = true
  try {
    const res = await openPerformanceOnline({ current_user: currentUser.value, month: month.value, scope })
    router.push({ path: '/performance/edit', query: { docId: res.doc_id, scope: res.scope || scope } })
  } catch (err) {
    window.alert(detailOf(err))
  } finally {
    opening.value = false
  }
}

async function onTemplate(ev) {
  const input = ev.target
  const file = input.files && input.files[0]
  input.value = ''
  if (!file) return
  const form = new FormData()
  form.append('file', file)
  try {
    await uploadPerformanceTemplate({ current_user: currentUser.value }, form)
    window.alert('模板已更新。下次打开填报或汇总时会按新模板生成。')
    await load()
  } catch (err) {
    window.alert(detailOf(err))
  }
}

onMounted(load)
</script>

<style scoped>
.perf-page { padding: 24px; max-width: 1080px; margin: 0 auto; color: #1e293b; }
.perf-head { display: flex; justify-content: space-between; gap: 16px; align-items: flex-end; margin-bottom: 18px; }
.perf-head h1 { margin: 0 0 6px; font-size: 26px; }
.perf-head p { margin: 0; color: #64748b; }
.month-box { display: flex; align-items: center; gap: 8px; font-weight: 600; }
.month-box input { height: 36px; border: 1px solid #d7dce5; border-radius: 8px; padding: 0 10px; }
.rules, .panel, .actions { background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 16px 18px; margin-bottom: 14px; }
.rules h2, .panel h2 { margin: 0 0 8px; font-size: 16px; }
.rules ol { margin: 0; padding-left: 18px; color: #334155; line-height: 1.7; }
.actions { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.btn { border: 1px solid #d7dce5; background: #fff; border-radius: 8px; padding: 8px 14px; cursor: pointer; }
.btn.primary { background: #1890ff; border-color: #1890ff; color: #fff; }
.status, .pill { font-size: 12px; padding: 2px 8px; border-radius: 999px; background: #f1f5f9; color: #64748b; }
.status.on, .pill.on { background: #ecfdf3; color: #047857; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid #f1f5f9; }
.muted { color: #64748b; }
.error { color: #b91c1c; background: #fef2f2; }
</style>
