<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">技术分类录入</h1>
          <p class="header-subtitle">维护本专业的技术文件分类编码与名称，供文件编号使用</p>
        </div>
        <div class="header-actions">
          <button class="btn" @click="goBack">返回文件编号</button>
        </div>
      </div>
    </div>

    <div class="container">
      <div class="card">
        <div class="card-header">
          <h3>新增技术分类</h3>
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
              <label>生效年份</label>
              <input v-model="form.year0" type="number" class="readonly" readonly>
            </div>
            <div class="form-group">
              <label>分类编码</label>
              <input v-model="form.flbianma" type="text" placeholder="例如：2617-" required>
            </div>
            <div class="form-group">
              <label>分类名称</label>
              <input v-model="form.flname" type="text" placeholder="例如：过程控制记录卡" required>
            </div>
            <div class="form-actions">
              <button type="button" @click="resetForm">重置</button>
              <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? '保存中…' : '保存分类' }}</button>
            </div>
          </form>
        </div>
      </div>

      <div class="card mt-xl">
        <div class="card-header">
          <h3>本专业历史技术分类</h3>
        </div>
        <div class="card-body table-wrapper">
          <table class="data-table" v-if="list.length">
            <thead>
              <tr>
                <th>分类编码</th>
                <th>分类名称</th>
                <th>生效年份</th>
                <th>所属科室</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in list" :key="row.id">
                <td>{{ row.flbianma }}</td>
                <td>{{ row.flname }}</td>
                <td>{{ row.year0 }}</td>
                <td>{{ row.ssks }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="empty-text">当前科室暂无技术分类记录。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getBianhaoFlList, addBianhaoFl } from '@/api/fileNumbering'
import { getStatisticsPermission } from '@/api/attendance'

const router = useRouter()

const form = ref({
  tjr: '',
  ssks: '',
  year0: new Date().getFullYear(),
  flbianma: '',
  flname: ''
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
    const res = await getBianhaoFlList({ ssks: form.value.ssks })
    list.value = (res.list || []).filter(Boolean)
  } catch {
    list.value = []
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.value.flbianma = ''
  form.value.flname = ''
}

async function handleSubmit() {
  if (!form.value.flbianma.trim() || !form.value.flname.trim()) return
  if (!form.value.tjr || !form.value.ssks) {
    await loadUserDept()
    if (!form.value.tjr || !form.value.ssks) {
      alert('无法获取当前用户或科室信息，请重新登录后重试')
      return
    }
  }
  saving.value = true
  try {
    await addBianhaoFl({
      tjr: form.value.tjr,
      flbianma: form.value.flbianma.trim(),
      flname: form.value.flname.trim(),
      year0: form.value.year0,
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

