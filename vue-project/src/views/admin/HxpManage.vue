<template>
  <div class="hxp-manage-page">
    <div class="container">
      <header class="page-header">
        <div class="header-content">
          <div class="header-info">
            <h1 class="header-title">换休票批量管理</h1>
            <p class="header-subtitle">批量为员工增加或减少换休票。增加以当前时间入账；减少优先扣最早过期的票。</p>
          </div>
        </div>
      </header>

      <div v-if="!canAccess" class="card no-permission">
        <p>您暂无权限访问此页面，仅系统管理员或人事管理员可操作。</p>
        <router-link to="/" class="btn btn-primary">返回首页</router-link>
      </div>

      <template v-else>
        <div class="card form-section">
          <form @submit.prevent="submit" class="fill-form">
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
            <div class="form-row" v-if="action === 'add'">
              <label class="form-label">来源备注（选填）</label>
              <input type="text" v-model="ly" class="form-input" placeholder="如：3月补发、手工调整" />
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
              <button type="submit" class="btn btn-primary" :disabled="submitting || !parsedNames.length || !amount">
                {{ submitting ? '处理中…' : (action === 'add' ? '确认增加' : '确认减少') }}
              </button>
              <button type="button" class="btn btn-outline" @click="reset">重置</button>
            </div>
          </form>
        </div>

        <div v-if="result" class="card result-section" :class="result.allOk ? 'result-success' : 'result-warn'">
          <h3 class="result-title">{{ result.message }}</h3>
          <div class="result-table-wrap">
            <table class="result-table">
              <thead>
                <tr>
                  <th>姓名</th>
                  <th>结果</th>
                  <th>说明</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in result.items" :key="r.name" :class="r.ok ? '' : 'row-fail'">
                  <td>{{ r.name }}</td>
                  <td>{{ r.ok ? '成功' : '失败' }}</td>
                  <td>{{ r.msg }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { hxpBatch } from '@/api/admin'
import { getUploadConfig } from '@/api/attendance'

const canAccess = ref(false)
const action = ref('add')
const amount = ref(1)
const ly = ref('')
const namesText = ref('')
const submitting = ref(false)
const result = ref(null)

const parsedNames = computed(() => {
  if (!namesText.value.trim()) return []
  return [...new Set(
    namesText.value
      .split(/[\n,，、\s]+/)
      .map(s => s.trim())
      .filter(Boolean)
  )]
})

onMounted(async () => {
  try {
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
    const name = (userInfo.name || userInfo.userName || '').trim()
    if (!name) return
    const res = await getUploadConfig()
    const a1 = (res?.admin1 || '').trim()
    const a2 = (res?.admin2 || '').trim()
    canAccess.value = (a1 && name === a1) || (a2 && name === a2)
  } catch {
    canAccess.value = false
  }
})

async function submit() {
  if (!parsedNames.value.length || !amount.value) return
  if (!confirm(`确认为 ${parsedNames.value.length} 人${action.value === 'add' ? '增加' : '减少'} ${amount.value} 张换休票？`)) return

  submitting.value = true
  result.value = null
  try {
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
    const res = await hxpBatch({
      current_user: (userInfo.name || userInfo.userName || '').trim(),
      names: parsedNames.value,
      amount: amount.value,
      action: action.value,
      ly: ly.value.trim(),
    })
    const items = res.results || []
    result.value = {
      message: res.message,
      allOk: items.every(r => r.ok),
      items,
    }
  } catch (e) {
    result.value = {
      message: e.response?.data?.detail || e.message || '操作失败',
      allOk: false,
      items: [],
    }
  } finally {
    submitting.value = false
  }
}

function reset() {
  namesText.value = ''
  amount.value = 1
  ly.value = ''
  result.value = null
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
.result-section {
  margin-top: var(--spacing-xl);
  padding: var(--spacing-xl);
}
.result-success { border-left: 4px solid var(--color-success); }
.result-warn { border-left: 4px solid #f59e0b; }
.result-title {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--spacing-lg);
}
.result-table-wrap {
  overflow-x: auto;
}
.result-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}
.result-table th, .result-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid var(--color-border-lighter);
}
.result-table th {
  background: var(--color-bg-spotlight);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
}
.row-fail td {
  color: var(--color-error);
}
</style>
