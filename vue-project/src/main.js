import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

// 导入全局样式
import './assets/global.css'

// 图表标准化：注册 ECharts 所需模块（柱状图等），供全项目图表复用
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const app = createApp(App)

app.use(router)
app.mount('#app')
