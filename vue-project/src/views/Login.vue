<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-card card">
        <div class="login-header">
          <div class="logo-circle">
            <svg class="logo-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 11l3 3L22 4" />
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
          </div>
          <h1 class="login-title">智能制造工艺部集成办公平台</h1>
          <p class="login-subtitle">企业级智能考勤解决方案</p>
        </div>

        <form class="login-form" @submit.prevent="handleLogin" autocomplete="on">
          <div class="form-group">
            <label class="form-label">用户名</label>
            <div class="input-wrapper">
              <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
              <input
                v-model="form.username"
                type="text"
                name="username"
                autocomplete="username"
                class="input input-with-icon"
                placeholder="请输入用户名"
                required
              />
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">密码</label>
            <div class="input-wrapper">
              <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <input
                v-model="form.password"
                type="password"
                name="password"
                autocomplete="current-password"
                class="input input-with-icon"
                placeholder="请输入密码"
                required
              />
            </div>
          </div>

          <div class="form-options">
            <label class="checkbox-label">
              <input type="checkbox" v-model="form.remember" />
              <span class="checkbox-text">记住我</span>
            </label>
            <a href="#" class="link-text">忘记密码？</a>
          </div>

          <button type="submit" class="btn btn-primary btn-lg login-btn" :disabled="loading">
            <span v-if="!loading">登录</span>
            <span v-else class="flex-center">
              <span class="loading mr-sm"></span>
              登录中...
            </span>
          </button>
        </form>

      </div>

      <div class="login-info">
        <div class="info-item">
          <svg class="info-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5M2 12l10 5 10-5" />
          </svg>
          <div class="info-content">
            <div class="info-title">智能管理</div>
            <div class="info-desc">基于AI的智能考勤分析</div>
          </div>
        </div>
        <div class="info-item">
          <svg class="info-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
          <div class="info-content">
            <div class="info-title">安全可靠</div>
            <div class="info-desc">企业级数据安全保障</div>
          </div>
        </div>
        <div class="info-item">
          <svg class="info-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
          </svg>
          <div class="info-content">
            <div class="info-title">实时监控</div>
            <div class="info-desc">7x24小时实时数据更新</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '@/api/attendance'

const router = useRouter()

const loading = ref(false)
const form = reactive({
  username: '',
  password: '',
  remember: false
})

const handleLogin = async () => {
  loading.value = true
  
  try {
    // 调用登录 API
    const response = await login({
      admin: form.username,
      password: form.password
    })
    
    if (response.success) {
      // 保存用户信息到 localStorage
      const userInfo = {
        name: response.data.name || form.username,
        dept: response.data.dept || '未分配部门',
        username: form.username,
        ...response.data
      }
      localStorage.setItem('userInfo', JSON.stringify(userInfo))
      
      // 跳转到首页
      router.push('/')
    } else {
      alert('登录失败：' + (response.message || '用户名或密码错误'))
    }
  } catch (error) {
    console.error('登录错误:', error)
    alert('登录失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: var(--spacing-xl);
}

.login-container {
  width: 100%;
  max-width: 1000px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-xxl);
  align-items: center;
}

.login-card {
  padding: var(--spacing-xxxl);
  background: white;
  border: none;
  box-shadow: var(--shadow-elevated);
}

.login-header {
  text-align: center;
  margin-bottom: var(--spacing-xxl);
}

.logo-circle {
  width: 80px;
  height: 80px;
  margin: 0 auto var(--spacing-lg);
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-svg {
  width: 40px;
  height: 40px;
  color: white;
}

.login-title {
  font-size: var(--font-size-xxl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
}

.login-subtitle {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.form-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.input-wrapper {
  position: relative;
}

.input-icon {
  position: absolute;
  left: var(--spacing-md);
  top: 50%;
  transform: translateY(-50%);
  width: 18px;
  height: 18px;
  color: var(--color-text-tertiary);
  pointer-events: none;
}

.input-with-icon {
  padding-left: 42px;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: calc(-1 * var(--spacing-sm));
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  cursor: pointer;
  user-select: none;
}

.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.checkbox-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.link-text {
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  text-decoration: none;
  transition: opacity var(--transition-base) var(--transition-ease);
}

.link-text:hover {
  opacity: 0.8;
}

.login-btn {
  width: 100%;
  margin-top: var(--spacing-base);
}

/* 登录信息 */
.login-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xl);
}

.info-item {
  display: flex;
  gap: var(--spacing-base);
  padding: var(--spacing-lg);
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border-radius: var(--radius-md);
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: all var(--transition-base) var(--transition-ease);
}

.info-item:hover {
  background: rgba(255, 255, 255, 0.25);
  transform: translateX(8px);
}

.info-icon {
  width: 48px;
  height: 48px;
  padding: var(--spacing-sm);
  background: rgba(255, 255, 255, 0.2);
  border-radius: var(--radius-base);
  color: white;
  flex-shrink: 0;
}

.info-content {
  color: white;
}

.info-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--spacing-xs);
}

.info-desc {
  font-size: var(--font-size-sm);
  opacity: 0.9;
}

/* 响应式 */
@media (max-width: 992px) {
  .login-container {
    grid-template-columns: 1fr;
  }
  
  .login-info {
    flex-direction: row;
  }
  
  .info-item {
    flex-direction: column;
    text-align: center;
  }
}

@media (max-width: 768px) {
  .login-page {
    padding: var(--spacing-base);
  }
  
  .login-card {
    padding: var(--spacing-xl);
  }
  
  .login-info {
    flex-direction: column;
  }
  
  .info-item {
    flex-direction: row;
    text-align: left;
  }
}
</style>
