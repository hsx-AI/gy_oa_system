<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">工作号录入</h1>
          <p class="header-subtitle">为本专业维护工作号及项目名称，供技术文件与技术管理编号使用</p>
        </div>
        <div class="header-actions">
          <button class="btn" @click="goBack">返回文件编号</button>
        </div>
      </div>
    </div>

    <div class="container">
      <div class="card">
        <div class="card-header">
          <h3>新增工作号</h3>
        </div>
        <div class="card-body">
          <form class="form-grid" @submit.prevent="handleSubmit">
            <div class="form-group">
              <label>添加人</label>
              <input v-model="form.tjr" type="text" class="readonly" readonly>
            </div>
            <div class="form-group">
              <label>所属科室</label>
              <input v-model="form.ssks" type="text" class="readonly" readonly>
            </div>
            <div class="form-group">
              <label>截止年份（基准年）</label>
              <input v-model.number="form.jznf" type="number" min="2000" :max="maxYear" required>
            </div>
            <div class="form-group">
              <label>工作号</label>
              <input v-model="form.gzh" type="text" placeholder="例如：001289" required>
            </div>
            <div class="form-group">
              <label>工作号名称</label>
              <input v-model="form.gzhname" type="text" placeholder="例如：云浮水源山抽水蓄能" required>
            </div>
            <div class="form-actions">
              <button type="button" @click="resetForm">重置</button>
              <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? '保存中…' : '保存工作号' }}</button>
            </div>
          </form>
        </div>
      </div>

      <div class="card mt-xl">
        <div class="card-header">
          <h3>本专业工作号列表</h3>
        </div>
        <div class="card-body table-wrapper">
          <table class="data-table" v-if="list.length">
            <thead>
              <tr>
                <th>工作号</th>
                <th>工作号名称</th>
                <th>截止年份</th>
                <th>所属科室</th>
                <th>添加人</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in list" :key="row.id">
                <td>{{ row.gzh }}</td>
                <td>{{ row.gzhname }}</td>
                <td>{{ row.year0 }}</td>
                <td>{{ row.ssks }}</td>
                <td>{{ row.tjr }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="empty-text">当前科室暂无工作号记录。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getGzhList, addGzh } from '@/api/fileNumbering'
import { getStatisticsPermission } from '@/api/attendance'

const router = useRouter()

const currentYear = new Date().getFullYear()
const maxYear = computed(() => currentYear + 10)

const form = ref({
  tjr: '',
  ssks: '',
  jznf: currentYear,
  gzh: '',
  gzhname: ''
})

const list = ref([])
const loading = ref(false)
const saving = ref(false)

function getCurrentUser() {
  try {
    const raw = localStorage.getItem('userInfo')
    if (!raw) return null
    const u = JSON.parse(raw)
    return { name: (u.name || u.userName || '').trim() }
  } catch {
    return null
  }
}

async function loadUserDept() {
  const user = getCurrentUser()
  if (!user?.name) return
  form.value.tjr = user.name
  try {
    const res = await getStatisticsPermission({ name: user.name })
    if (res && res.success !== false) {
      form.value.ssks = (res.lsys || '').trim()
    }
  } catch {
    // ignore
  }
}

async function loadList() {
  if (!form.value.ssks) return
  loading.value = true
  try {
    const res = await getGzhList({ ssks: form.value.ssks })
    list.value = (res.list || []).filter(Boolean)
  } catch {
    list.value = []
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.value.gzh = ''
  form.value.gzhname = ''
  form.value.jznf = currentYear
}

async function handleSubmit() {
  if (!form.value.gzh.trim() || !form.value.gzhname.trim()) return
  if (!form.value.tjr || !form.value.ssks) {
    await loadUserDept()
    if (!form.value.tjr || !form.value.ssks) {
      alert('无法获取当前用户或科室信息，请重新登录后重试')
      return
    }
  }
  saving.value = true
  try {
    await addGzh({
      tjr: form.value.tjr,
      gzh: form.value.gzh.trim(),
      xmm: form.value.gzhname.trim(),
      jznf: form.value.jznf,
      ssks: form.value.ssks
    })
    alert('保存成功')
    resetForm()
    await loadList()
  } catch (e) {
    alert(e?.response?.data?.detail || e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

function goBack() {
  router.push('/file/numbering')
}

onMounted(async () => {
  await loadUserDept()
  await loadList()
})
</script>

<style scoped>
.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--spacing-lg);
}

.card-header {
  padding: var(--spacing-md) var(--spacing-xl);
}

.card-body {
  padding: var(--spacing-lg) var(--spacing-xl);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.form-group label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.form-group input,
.form-group select {
  padding: 6px 10px;
  border-radius: var(--radius-base);
  border: 1px solid var(--color-border-lighter);
  font-size: var(--font-size-sm);
}

.readonly {
  background-color: var(--color-bg-layout);
}

.form-actions {
  grid-column: 1 / -1;
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-md);
}

.form-actions button {
  min-width: 80px;
  padding: 6px 16px;
  font-size: var(--font-size-sm);
  border-radius: var(--radius-base);
}

.table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}

.data-table th,
.data-table td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--color-border-lighter);
  text-align: left;
}

.empty-text {
  padding: var(--spacing-xl);
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}
</style>

