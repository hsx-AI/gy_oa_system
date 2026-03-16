<template>
  <div class="login-page" @mousemove="onMouseMove">
    <!-- 粒子背景 canvas -->
    <canvas ref="particleCanvas" class="particle-bg"></canvas>

    <!-- 浮动科技装饰 -->
    <div class="tech-grid"></div>
    <div class="glow-orb orb-1"></div>
    <div class="glow-orb orb-2"></div>
    <div class="glow-orb orb-3"></div>

    <div class="login-container">
      <!-- 左侧品牌区 -->
      <div class="brand-panel">
        <div class="brand-content">
          <div class="brand-top">
            <img :src="logoUrl" alt="LOGO" class="brand-logo" />
            <h1 class="brand-title">
              <span class="title-line" v-for="(line, i) in titleLines" :key="i"
                    :style="{ animationDelay: i * 0.15 + 's' }">{{ line }}</span>
            </h1>
          </div>
          <p class="brand-slogan">
            <span class="typing-text">{{ displaySlogan }}</span>
            <span class="cursor-blink">|</span>
          </p>

          <!-- 特性卡片 -->
          <div class="feature-row">
            <div class="feature-card" v-for="(f, i) in features" :key="i"
                 :style="{ animationDelay: 0.6 + i * 0.15 + 's' }">
              <div class="feature-icon-wrap">
                <svg v-if="f.icon === 'ai'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2a4 4 0 014 4v1a1 1 0 001 1h1a4 4 0 010 8h-1a1 1 0 00-1 1v1a4 4 0 01-8 0v-1a1 1 0 00-1-1H6a4 4 0 010-8h1a1 1 0 001-1V6a4 4 0 014-4z"/><circle cx="9" cy="12" r="1"/><circle cx="15" cy="12" r="1"/></svg>
                <svg v-else-if="f.icon === 'shield'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
              </div>
              <div class="feature-text">
                <span class="feature-name">{{ f.name }}</span>
                <span class="feature-desc">{{ f.desc }}</span>
              </div>
            </div>
          </div>

          <div class="tech-stats-row">
            <div class="tech-stats">
              <div class="stat" v-for="(s, i) in stats" :key="i">
                <span class="stat-num">{{ animatedStats[i] }}</span>
                <span class="stat-label">{{ s.label }}</span>
              </div>
            </div>
            <div class="legacy-entry">
              <a
                href="http://10.42.60.230"
                target="_blank"
                rel="noopener noreferrer"
                class="legacy-btn"
              >
                <svg class="legacy-btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
                原考勤系统入口
              </a>
              <span class="legacy-note">原「230」系统入口</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧登录卡片 -->
      <div class="login-card-wrap">
        <div class="login-card">
          <div class="card-glow"></div>

          <div class="login-header">
            <div class="welcome-badge">WELCOME</div>
            <h2 class="login-heading">欢迎回来</h2>
            <p class="login-desc">登录您的账户以继续工作</p>
          </div>

          <form class="login-form" @submit.prevent="handleLogin" autocomplete="on">
            <div class="field-group" :class="{ focused: focusField === 'user', filled: form.username }">
              <div class="field-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              </div>
              <input v-model="form.username" type="text" name="username" autocomplete="username"
                     placeholder="原230考勤系统你的用户名（汉字姓名）" required
                     @focus="focusField = 'user'" @blur="focusField = ''" />
              <div class="field-line"></div>
            </div>

            <div class="field-group" :class="{ focused: focusField === 'pass', filled: form.password }">
              <div class="field-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>
              </div>
              <input v-model="form.password" :type="showPwd ? 'text' : 'password'" name="password"
                     autocomplete="current-password" placeholder="原230考勤系统你的密码" required
                     @focus="focusField = 'pass'" @blur="focusField = ''" />
              <button type="button" class="toggle-pwd" @click="showPwd = !showPwd" tabindex="-1">
                <svg v-if="showPwd" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
              </button>
              <div class="field-line"></div>
            </div>

            <div class="form-options">
              <label class="remember-check">
                <input type="checkbox" v-model="form.remember" />
                <span class="check-box"><svg viewBox="0 0 12 12"><polyline points="2 6 5 9 10 3" fill="none" stroke="currentColor" stroke-width="1.5"/></svg></span>
                <span>记住我</span>
              </label>
            </div>

            <button type="submit" class="login-btn" :disabled="loading" :class="{ loading: loading }">
              <span class="btn-bg"></span>
              <span class="btn-content">
                <svg v-if="!loading" class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
                <span v-if="!loading">安 全 登 录</span>
                <span v-else class="loading-dots">
                  <i></i><i></i><i></i>
                </span>
              </span>
            </button>
          </form>

          <div class="card-footer">
            <div class="secure-badge">
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 1L2 3.5v4c0 3.5 3 6.5 6 7.5 3-1 6-4 6-7.5v-4L8 1z"/></svg>
              <span>内网安全环境</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部版权 -->
    <div class="footer-bar">
      <span>© {{ new Date().getFullYear() }} 智能制造工艺部 · 集成办公平台</span>
      <span class="footer-team">智能制造技术室 · 能做！科技团队</span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, computed } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '@/api/attendance'
import logoUrl from '@/assets/changbiao.png'

const router = useRouter()
const loading = ref(false)
const showPwd = ref(false)
const focusField = ref('')
const particleCanvas = ref(null)

const form = reactive({
  username: '',
  password: '',
  remember: false
})

const titleLines = ['智能制造工艺部', '集成办公平台']
const slogan = '数字赋能 · 智慧工艺 · 高效协同'
const displaySlogan = ref('')

const features = [
  { icon: 'ai', name: 'AI 智能分析', desc: '考勤异常自动识别' },
  { icon: 'shield', name: '安全可靠', desc: '企业级数据保障' },
  { icon: 'grid', name: '一站集成', desc: '编号·审批·制度' },
]

const stats = [
  { value: 200, label: '在线员工', suffix: '+' },
  { value: 99.9, label: '系统可用率', suffix: '%' },
  { value: 24, label: '全天候服务', suffix: 'h' },
]
const animatedStats = ref(stats.map(() => '0'))

let animFrame = null
let typingTimer = null

function typeSlogan() {
  let idx = 0
  typingTimer = setInterval(() => {
    if (idx <= slogan.length) {
      displaySlogan.value = slogan.slice(0, idx)
      idx++
    } else {
      clearInterval(typingTimer)
    }
  }, 80)
}

function animateStats() {
  const duration = 1500
  const start = performance.now()
  function tick(now) {
    const t = Math.min((now - start) / duration, 1)
    const ease = 1 - Math.pow(1 - t, 3)
    animatedStats.value = stats.map(s => {
      const v = s.value * ease
      const str = Number.isInteger(s.value) ? Math.round(v).toString() : v.toFixed(1)
      return str + (s.suffix || '')
    })
    if (t < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

// ===== 3D 线框地球 + 繁星 + 流星 =====
const STAR_COUNT = 220
const METEOR_COUNT = 3
let stars = []
let meteors = []
let globeAngle = 0
let mouseX = 0, mouseY = 0

function initCanvas(canvas) {
  const ctx = canvas.getContext('2d')
  let W, H
  const resize = () => { W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; initStars() }

  function initStars() {
    stars = Array.from({ length: STAR_COUNT }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      r: Math.random() * 1.6 + 0.3,
      baseO: Math.random() * 0.6 + 0.2,
      twinkleSpeed: Math.random() * 0.02 + 0.005,
      phase: Math.random() * Math.PI * 2,
    }))
    meteors = Array.from({ length: METEOR_COUNT }, () => createMeteor(W, H))
  }

  resize()
  window.addEventListener('resize', resize)

  function draw(time) {
    ctx.clearRect(0, 0, W, H)
    drawStars(ctx, time)
    drawMeteors(ctx)
    drawGlobe(ctx, W, H, time)
    globeAngle += 0.003
    animFrame = requestAnimationFrame(draw)
  }

  function drawStars(ctx, time) {
    for (const s of stars) {
      const o = s.baseO + Math.sin(time * s.twinkleSpeed + s.phase) * 0.25
      ctx.beginPath()
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(255,255,255,${Math.max(0, Math.min(1, o))})`
      ctx.fill()
    }
  }

  function createMeteor(w, h) {
    return {
      x: Math.random() * w * 1.5,
      y: Math.random() * h * 0.4 - h * 0.1,
      len: Math.random() * 80 + 40,
      speed: Math.random() * 6 + 4,
      o: Math.random() * 0.6 + 0.3,
      delay: Math.random() * 400,
      tick: 0,
    }
  }

  function drawMeteors(ctx) {
    for (let i = 0; i < meteors.length; i++) {
      const m = meteors[i]
      m.tick++
      if (m.tick < m.delay) continue
      m.x -= m.speed
      m.y += m.speed * 0.6
      if (m.x < -200 || m.y > H + 100) { meteors[i] = createMeteor(W, H); continue }
      const grad = ctx.createLinearGradient(m.x, m.y, m.x + m.len, m.y - m.len * 0.6)
      grad.addColorStop(0, `rgba(180,220,255,${m.o})`)
      grad.addColorStop(1, 'rgba(180,220,255,0)')
      ctx.beginPath()
      ctx.moveTo(m.x, m.y)
      ctx.lineTo(m.x + m.len, m.y - m.len * 0.6)
      ctx.strokeStyle = grad
      ctx.lineWidth = 1.5
      ctx.stroke()
      ctx.beginPath()
      ctx.arc(m.x, m.y, 2, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(200,230,255,${m.o})`
      ctx.fill()
    }
  }

  function drawGlobe(ctx, w, h, time) {
    const cx = w * 0.5
    const cy = h * 0.5
    const parallaxX = (mouseX - w / 2) * 0.015
    const parallaxY = (mouseY - h / 2) * 0.015
    const gx = cx + parallaxX
    const gy = cy + parallaxY
    const R = Math.min(w, h) * 0.38
    const tilt = 0.4

    // 外圈光晕（更大更亮）
    const glow = ctx.createRadialGradient(gx, gy, R * 0.5, gx, gy, R * 1.6)
    glow.addColorStop(0, 'rgba(24,144,255,0.07)')
    glow.addColorStop(0.5, 'rgba(24,144,255,0.03)')
    glow.addColorStop(1, 'rgba(24,144,255,0)')
    ctx.beginPath()
    ctx.arc(gx, gy, R * 1.6, 0, Math.PI * 2)
    ctx.fillStyle = glow
    ctx.fill()

    ctx.save()
    ctx.translate(gx, gy)

    // 经线（旋转，覆盖整圈 0~2π）
    const lonCount = 16
    for (let i = 0; i < lonCount; i++) {
      const lonAngle = (i / lonCount) * Math.PI * 2 + globeAngle
      ctx.beginPath()
      for (let j = 0; j <= 60; j++) {
        const lat = (j / 60) * Math.PI
        const x3d = R * Math.sin(lat) * Math.cos(lonAngle)
        const y3d = R * Math.cos(lat)
        const z3d = R * Math.sin(lat) * Math.sin(lonAngle)
        const xr = x3d
        const yr = y3d * Math.cos(tilt) - z3d * Math.sin(tilt)
        const zr = y3d * Math.sin(tilt) + z3d * Math.cos(tilt)
        const depth = (zr / R + 1) / 2
        if (j === 0) ctx.moveTo(xr, yr)
        else ctx.lineTo(xr, yr)
      }
      ctx.strokeStyle = 'rgba(24,144,255,0.22)'
      ctx.lineWidth = 1
      ctx.stroke()
    }

    // 纬线（按投影高度更均匀分布）
    const latCount = 8
    for (let i = 1; i < latCount; i++) {
      const t = i / latCount
      const yNorm = -1 + 2 * t
      const lat = Math.acos(yNorm)
      ctx.beginPath()
      for (let j = 0; j <= 80; j++) {
        const lon = (j / 80) * Math.PI * 2 + globeAngle
        const x3d = R * Math.sin(lat) * Math.cos(lon)
        const y3d = R * Math.cos(lat)
        const z3d = R * Math.sin(lat) * Math.sin(lon)
        const xr = x3d
        const yr = y3d * Math.cos(tilt) - z3d * Math.sin(tilt)
        const zr = y3d * Math.sin(tilt) + z3d * Math.cos(tilt)
        if (j === 0) ctx.moveTo(xr, yr)
        else ctx.lineTo(xr, yr)
      }
      ctx.strokeStyle = `rgba(24,144,255,${0.10 + 0.10 * (i / latCount)})`
      ctx.lineWidth = 0.8
      ctx.stroke()
    }

    // 表面亮点（模拟城市灯光）
    const dotCount = 40
    for (let i = 0; i < dotCount; i++) {
      const lat = Math.acos(2 * ((i * 0.618033988749895) % 1) - 1)
      const lon = 2 * Math.PI * ((i * 1.618033988749895) % 1) + globeAngle * 1.5
      const x3d = R * Math.sin(lat) * Math.cos(lon)
      const y3d = R * Math.cos(lat)
      const z3d = R * Math.sin(lat) * Math.sin(lon)
      const xr = x3d
      const yr = y3d * Math.cos(tilt) - z3d * Math.sin(tilt)
      const zr = y3d * Math.sin(tilt) + z3d * Math.cos(tilt)
      if (zr > 0) {
        const bri = (zr / R) * 0.9
        ctx.beginPath()
        ctx.arc(xr, yr, 2, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(64,169,255,${bri})`
        ctx.fill()
      }
    }

    // 赤道高亮环
    ctx.beginPath()
    for (let j = 0; j <= 100; j++) {
      const lon = (j / 100) * Math.PI * 2 + globeAngle
      const x3d = R * Math.cos(lon)
      const z3d = R * Math.sin(lon)
      const yr = -z3d * Math.sin(tilt)
      const zr = z3d * Math.cos(tilt)
      if (j === 0) ctx.moveTo(x3d, yr)
      else ctx.lineTo(x3d, yr)
    }
    ctx.strokeStyle = 'rgba(24,144,255,0.28)'
    ctx.lineWidth = 1.5
    ctx.stroke()

    ctx.restore()
  }

  animFrame = requestAnimationFrame(draw)
}

function onMouseMove(e) {
  mouseX = e.clientX
  mouseY = e.clientY
}

onMounted(() => {
  if (particleCanvas.value) initCanvas(particleCanvas.value)
  setTimeout(typeSlogan, 600)
  setTimeout(animateStats, 800)
})

onBeforeUnmount(() => {
  if (animFrame) cancelAnimationFrame(animFrame)
  if (typingTimer) clearInterval(typingTimer)
})

const handleLogin = async () => {
  loading.value = true
  try {
    const response = await login({ admin: form.username, password: form.password })
    const userInfo = {
      name: response.data.name || form.username,
      dept: response.data.dept || '未分配部门',
      username: form.username,
      ...response.data
    }
    localStorage.setItem('userInfo', JSON.stringify(userInfo))
    router.push('/')
  } catch (error) {
    console.error('登录错误:', error)
    if (error.response) {
      alert('服务器错误（' + error.response.status + '），请联系管理员')
    } else if (error.message === 'Network Error') {
      alert('服务器连接失败，请检查网络连接')
    } else if (error.message && error.message.includes('timeout')) {
      alert('服务器响应超时，请稍后重试')
    } else {
      alert(error.message || '登录失败，请稍后重试')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ===== 全局 ===== */
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0a1628 0%, #0d2137 30%, #122a4e 60%, #0a1628 100%);
  overflow: hidden;
  position: relative;
  padding: 24px;
}

.particle-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

/* 科技网格 */
.tech-grid {
  position: fixed;
  inset: 0;
  z-index: 0;
  background-image:
    linear-gradient(rgba(24, 144, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(24, 144, 255, 0.03) 1px, transparent 1px);
  background-size: 60px 60px;
  pointer-events: none;
}

/* 发光球体 */
.glow-orb {
  position: fixed;
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
  z-index: 0;
}
.orb-1 { width: 400px; height: 400px; top: -100px; left: -100px; background: rgba(24, 144, 255, 0.12); animation: orbFloat 12s ease-in-out infinite; }
.orb-2 { width: 300px; height: 300px; bottom: -80px; right: -60px; background: rgba(114, 46, 209, 0.10); animation: orbFloat 15s ease-in-out infinite reverse; }
.orb-3 { width: 200px; height: 200px; top: 40%; left: 50%; background: rgba(0, 200, 150, 0.06); animation: orbFloat 18s ease-in-out infinite 3s; }

@keyframes orbFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -20px) scale(1.05); }
  66% { transform: translate(-20px, 15px) scale(0.95); }
}

/* ===== 布局 ===== */
.login-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 1100px;
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 48px;
  align-items: center;
}

/* ===== 左侧品牌 ===== */
.brand-panel {
  color: #fff;
}

.brand-top {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 16px;
}

.brand-logo {
  width: 72px;
  height: 72px;
  object-fit: contain;
  border-radius: 14px;
  background: rgba(255,255,255,0.9);
  padding: 6px;
  box-shadow: 0 4px 20px rgba(24,144,255,0.2);
  animation: logoAppear 0.8s ease both, logoPulse 4s ease-in-out 1s infinite;
  flex-shrink: 0;
}

@keyframes logoAppear {
  from { opacity: 0; transform: scale(0.7) rotate(-10deg); }
  to { opacity: 1; transform: scale(1) rotate(0deg); }
}

@keyframes logoPulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(24,144,255,0.2); }
  50% { box-shadow: 0 4px 30px rgba(24,144,255,0.35), 0 0 0 4px rgba(24,144,255,0.08); }
}

.brand-title {
  font-size: 36px;
  font-weight: 700;
  line-height: 1.3;
  margin-bottom: 0;
  letter-spacing: 2px;
}

.title-line {
  display: block;
  opacity: 0;
  transform: translateY(20px);
  animation: fadeUp 0.6s ease forwards;
}

@keyframes fadeUp {
  to { opacity: 1; transform: translateY(0); }
}

.brand-slogan {
  font-size: 15px;
  color: rgba(255,255,255,0.55);
  margin-top: 12px;
  margin-bottom: 36px;
  letter-spacing: 3px;
  min-height: 1.5em;
}

.cursor-blink {
  animation: blink 0.8s step-end infinite;
  color: #40a9ff;
}

@keyframes blink {
  50% { opacity: 0; }
}

/* 特性卡片 */
.feature-row {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 32px;
}

.feature-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  border-radius: 12px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  backdrop-filter: blur(8px);
  transition: all 0.3s ease;
  opacity: 0;
  transform: translateX(-20px);
  animation: slideIn 0.5s ease forwards;
}

.feature-card:hover {
  background: rgba(24,144,255,0.08);
  border-color: rgba(24,144,255,0.2);
  transform: translateX(6px);
}

@keyframes slideIn {
  to { opacity: 1; transform: translateX(0); }
}

.feature-icon-wrap {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(24,144,255,0.15), rgba(24,144,255,0.05));
  flex-shrink: 0;
}

.feature-icon-wrap svg {
  width: 20px; height: 20px; color: #40a9ff;
}

.feature-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.feature-name {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255,255,255,0.9);
}

.feature-desc {
  font-size: 12px;
  color: rgba(255,255,255,0.4);
}

/* 数据统计 + 原考勤系统入口 */
.tech-stats-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}

.tech-stats {
  display: flex;
  gap: 32px;
}

.stat {
  display: flex;
  flex-direction: column;
}

.stat-num {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, #40a9ff, #69c0ff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
}

.stat-label {
  font-size: 12px;
  color: rgba(255,255,255,0.35);
  margin-top: 2px;
}

/* 原考勤系统入口：显眼按钮 + 备注 */
.legacy-entry {
  display: flex;
  align-items: center;
  gap: 10px;
}

.legacy-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 12px 24px;
  font-size: 16px;
  font-weight: 700;
  color: #1a1a1a;
  background: linear-gradient(135deg, #ffc53d, #ff9c2e);
  border: none;
  border-radius: 10px;
  text-decoration: none;
  box-shadow: 0 4px 20px rgba(255, 156, 46, 0.5), 0 0 0 2px rgba(255, 255, 255, 0.2);
  transition: transform 0.2s, box-shadow 0.2s;
}

.legacy-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 28px rgba(255, 156, 46, 0.6), 0 0 0 2px rgba(255, 255, 255, 0.3);
}

.legacy-btn-icon {
  width: 18px;
  height: 18px;
  margin-right: 8px;
  flex-shrink: 0;
}

.legacy-note {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  white-space: nowrap;
}

@media (max-width: 900px) {
  .tech-stats-row {
    flex-direction: column;
    align-items: flex-start;
  }
}

/* ===== 右侧登录卡片 ===== */
.login-card-wrap {
  perspective: 1000px;
}

.login-card {
  position: relative;
  padding: 40px 36px;
  border-radius: 20px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  backdrop-filter: blur(20px);
  animation: cardAppear 0.8s ease 0.3s both;
}

.card-glow {
  position: absolute;
  inset: -1px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(24,144,255,0.15), transparent 40%, transparent 60%, rgba(114,46,209,0.1));
  z-index: -1;
  opacity: 0;
  transition: opacity 0.4s;
}
.login-card:hover .card-glow { opacity: 1; }

@keyframes cardAppear {
  from { opacity: 0; transform: translateY(30px) scale(0.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.welcome-badge {
  display: inline-block;
  padding: 4px 14px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 3px;
  color: #40a9ff;
  background: rgba(24,144,255,0.1);
  border: 1px solid rgba(24,144,255,0.2);
  margin-bottom: 16px;
}

.login-heading {
  font-size: 26px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 6px;
}

.login-desc {
  font-size: 13px;
  color: rgba(255,255,255,0.4);
}

/* 输入框 */
.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.field-group {
  position: relative;
  display: flex;
  align-items: center;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  transition: all 0.3s ease;
  overflow: hidden;
}

.field-group.focused {
  border-color: rgba(24,144,255,0.5);
  background: rgba(24,144,255,0.04);
  box-shadow: 0 0 0 3px rgba(24,144,255,0.08);
}

.field-group.filled:not(.focused) {
  border-color: rgba(255,255,255,0.12);
}

.field-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  flex-shrink: 0;
  color: rgba(255,255,255,0.25);
  transition: color 0.3s;
}
.field-group.focused .field-icon { color: #40a9ff; }
.field-icon svg { width: 18px; height: 18px; }

.field-group input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  color: #fff;
  font-size: 14px;
  padding: 14px 14px 14px 0;
  font-family: inherit;
}

.field-group input::placeholder {
  color: rgba(255,255,255,0.2);
}

.field-line {
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 0;
  height: 2px;
  background: linear-gradient(90deg, #1890ff, #722ed1);
  transition: all 0.4s ease;
  transform: translateX(-50%);
}
.field-group.focused .field-line { width: 100%; }

.toggle-pwd {
  background: none;
  border: none;
  cursor: pointer;
  color: rgba(255,255,255,0.25);
  padding: 8px 12px;
  transition: color 0.2s;
}
.toggle-pwd:hover { color: rgba(255,255,255,0.5); }
.toggle-pwd svg { width: 18px; height: 18px; }

/* 记住我 */
.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: -4px;
}

.remember-check {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  color: rgba(255,255,255,0.45);
  user-select: none;
}

.remember-check input { display: none; }

.check-box {
  width: 16px; height: 16px;
  border-radius: 4px;
  border: 1px solid rgba(255,255,255,0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  color: transparent;
}

.remember-check input:checked + .check-box {
  background: #1890ff;
  border-color: #1890ff;
  color: #fff;
}

/* 登录按钮 */
.login-btn {
  position: relative;
  width: 100%;
  padding: 14px;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  overflow: hidden;
  margin-top: 4px;
  transition: transform 0.2s, box-shadow 0.3s;
}

.login-btn:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 25px rgba(24,144,255,0.3);
}

.login-btn:not(:disabled):active {
  transform: translateY(0);
}

.btn-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #1890ff, #096dd9, #722ed1);
  background-size: 200% 200%;
  animation: gradientShift 4s ease infinite;
  z-index: 0;
}

@keyframes gradientShift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

.btn-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 4px;
}

.btn-icon {
  width: 18px;
  height: 18px;
}

.login-btn:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.loading-dots {
  display: flex;
  gap: 4px;
  align-items: center;
}
.loading-dots i {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #fff;
  animation: dotBounce 1.2s ease-in-out infinite;
}
.loading-dots i:nth-child(2) { animation-delay: 0.15s; }
.loading-dots i:nth-child(3) { animation-delay: 0.3s; }
@keyframes dotBounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* 底部安全 */
.card-footer {
  text-align: center;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid rgba(255,255,255,0.05);
}

.secure-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: rgba(255,255,255,0.25);
}

.secure-badge svg {
  width: 13px; height: 13px; color: rgba(82,196,26,0.6);
}

/* 底部版权 */
.footer-bar {
  position: fixed;
  bottom: 16px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 12px;
  color: rgba(255,255,255,0.7);
  z-index: 1;
  letter-spacing: 1px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
}

.footer-team {
  font-size: 11px;
  color: rgba(255,255,255,0.85);
  letter-spacing: 2px;
  font-weight: 500;
}

/* ===== 响应式 ===== */
@media (max-width: 992px) {
  .login-container {
    grid-template-columns: 1fr;
    max-width: 480px;
    gap: 32px;
  }
  .brand-panel { text-align: center; }
  .brand-top { justify-content: center; }
  .brand-logo { width: 60px; height: 60px; }
  .brand-title { font-size: 28px; }
  .feature-row { flex-direction: row; }
  .feature-card { flex: 1; flex-direction: column; text-align: center; padding: 12px; }
  .tech-stats { justify-content: center; }
  .hex-icon { margin: 0 auto; }
}

@media (max-width: 600px) {
  .login-page { padding: 16px; }
  .login-card { padding: 28px 22px; }
  .brand-logo { width: 50px; height: 50px; }
  .brand-title { font-size: 22px; }
  .feature-row { flex-direction: column; }
  .feature-card { flex-direction: row; text-align: left; }
  .tech-stats { gap: 20px; }
}
</style>
