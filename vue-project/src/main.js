import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

// 导入全局样式
import './assets/global.css'

// 图表标准化：注册 ECharts 所需模块（柱状图等），供全项目图表复用
import * as echarts from 'echarts/core'
import { BarChart, ScatterChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, MarkLineComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
echarts.use([BarChart, ScatterChart, GridComponent, TooltipComponent, MarkLineComponent, LegendComponent, DataZoomComponent, CanvasRenderer])

const app = createApp(App)

app.use(router)
app.mount('#app')

// 全局节流：日期/时间/数字输入框的滚轮滚动太快难以选择，限制为每 500ms 生效一次
;(() => {
  const THROTTLE_MS = 500
  const SCROLL_TYPES = new Set(['datetime-local', 'time', 'date', 'number'])
  let lastWheelTime = 0
  document.addEventListener('wheel', (e) => {
    const el = e.target
    if (el.tagName === 'INPUT' && SCROLL_TYPES.has(el.type) && document.activeElement === el) {
      const now = Date.now()
      if (now - lastWheelTime < THROTTLE_MS) {
        e.preventDefault()
      } else {
        lastWheelTime = now
      }
    }
  }, { passive: false, capture: true })
})()
