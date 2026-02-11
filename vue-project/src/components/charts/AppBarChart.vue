<template>
  <div class="app-bar-chart" :style="{ height: chartHeight }">
    <v-chart :option="chartOption" :autoresize="true" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { getBarChartOption } from '@/utils/chartConfig'

const props = defineProps({
  /** X 轴标签（如姓名） */
  labels: {
    type: Array,
    default: () => [],
  },
  /** Y 轴数值（如公出天数） */
  values: {
    type: Array,
    default: () => [],
  },
  /** Y 轴名称，用于 tooltip 和图例 */
  yAxisName: {
    type: String,
    default: '公出天数',
  },
  /** 图表高度 */
  height: {
    type: String,
    default: '280px',
  },
})

const chartHeight = computed(() => props.height)

const chartOption = computed(() => {
  return getBarChartOption({
    xAxisData: props.labels,
    seriesData: props.values,
    yAxisName: props.yAxisName,
  })
})
</script>

<style scoped>
.app-bar-chart {
  width: 100%;
  min-height: 200px;
}
</style>
