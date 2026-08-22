/**
 * 项目图表标准化配置
 * 与 design-tokens 保持一致，供各页面图表复用
 */

/** 标准柱状图/折线图配色（顺序使用） */
export const chartColors = [
  '#1890ff', // primary
  '#52c41a', // success
  '#faad14', // warning
  '#13c2c2', // cyan
  '#722ed1', // purple
  '#eb2f96', // magenta
  '#fa8c16', // orange
]

/** 柱状图默认配置（可被各页面覆盖部分项） */
export function getBarChartOption({ xAxisData = [], seriesData = [], title = '', yAxisName = '' } = {}) {
  const categoryCount = xAxisData.length
  const isDense = categoryCount > 12
  return {
    color: chartColors,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#e8e8e8',
      borderWidth: 1,
      textStyle: { color: '#262626', fontSize: 12 },
    },
    grid: {
      left: 72, // 留足 Y 轴名称「公出天数」完整显示
      right: 24,
      bottom: isDense ? 100 : 40, // 分类多时留足 X 轴旋转标签空间
      top: title ? 40 : 24,
      containLabel: false,
    },
    xAxis: {
      type: 'category',
      data: xAxisData,
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisLabel: {
        color: '#595959',
        fontSize: 12,
        interval: 0, // 强制显示全部横坐标，不省略
        rotate: isDense ? 45 : 0, // 分类多时倾斜 45° 避免重叠
      },
    },
    yAxis: {
      type: 'value',
      name: yAxisName || undefined,
      nameGap: 40,
      nameTextStyle: { color: '#8c8c8c', fontSize: 12 },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
      axisLabel: { color: '#595959', fontSize: 12 },
    },
    ...(title ? { title: { text: title, left: 'center', textStyle: { fontSize: 14, color: '#262626' } } } : {}),
    series: [
      {
        name: yAxisName || '数值',
        type: 'bar',
        data: seriesData,
        barWidth: '50%',
        itemStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: '#1890ff' },
              { offset: 1, color: '#69c0ff' },
            ],
          },
        },
      },
    ],
  }
}

/** 折线图（支持平滑曲线、面积渐变） */
export function getLineChartOption({
  xAxisData = [],
  seriesData = [],
  title = '',
  yAxisName = '',
  smooth = true,
  area = true,
} = {}) {
  return {
    color: chartColors,
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#e8e8e8',
      borderWidth: 1,
      textStyle: { color: '#262626', fontSize: 12 },
    },
    grid: {
      left: 56,
      right: 20,
      bottom: 36,
      top: title ? 44 : 28,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: xAxisData,
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisLabel: { color: '#595959', fontSize: 12 },
    },
    yAxis: {
      type: 'value',
      name: yAxisName || undefined,
      nameTextStyle: { color: '#8c8c8c', fontSize: 12 },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
      axisLabel: { color: '#595959', fontSize: 12 },
    },
    ...(title ? { title: { text: title, left: 12, textStyle: { fontSize: 14, color: '#262626', fontWeight: 600 } } } : {}),
    series: [
      {
        name: yAxisName || '数值',
        type: 'line',
        smooth,
        data: seriesData,
        symbol: 'circle',
        symbolSize: 7,
        lineStyle: { width: 3 },
        areaStyle: area
          ? {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: 'rgba(24,144,255,0.28)' },
                  { offset: 1, color: 'rgba(24,144,255,0.02)' },
                ],
              },
            }
          : undefined,
      },
    ],
  }
}

/** 多系列折线图（月度趋势对比） */
export function getMultiLineChartOption({ xAxisData = [], series = [], title = '' } = {}) {
  return {
    color: chartColors,
    tooltip: { trigger: 'axis' },
    legend: {
      bottom: 0,
      type: 'scroll',
      textStyle: { fontSize: 12, color: '#595959' },
    },
    grid: {
      left: 56,
      right: 20,
      bottom: 48,
      top: title ? 44 : 28,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: xAxisData,
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisLabel: { color: '#595959', fontSize: 12 },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
      axisLabel: { color: '#595959', fontSize: 12 },
    },
    ...(title ? { title: { text: title, left: 12, textStyle: { fontSize: 14, color: '#262626', fontWeight: 600 } } } : {}),
    series: series.map((item) => ({
      name: item.name,
      type: 'line',
      smooth: true,
      data: item.data,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { width: 2.5 },
    })),
  }
}

/** 横向柱状图（人员排名等） */
export function getHorizontalBarChartOption({
  labels = [],
  values = [],
  title = '',
  yAxisName = '',
  colors = chartColors,
} = {}) {
  return {
    color: colors,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#e8e8e8',
      borderWidth: 1,
    },
    grid: {
      left: 12,
      right: 28,
      bottom: 12,
      top: title ? 44 : 20,
      containLabel: true,
    },
    xAxis: {
      type: 'value',
      name: yAxisName || undefined,
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
      axisLabel: { color: '#595959', fontSize: 12 },
    },
    yAxis: {
      type: 'category',
      data: [...labels].reverse(),
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisLabel: { color: '#595959', fontSize: 12 },
    },
    ...(title ? { title: { text: title, left: 12, textStyle: { fontSize: 14, color: '#262626', fontWeight: 600 } } } : {}),
    series: [
      {
        name: yAxisName || '数值',
        type: 'bar',
        data: [...values].reverse().map((val, idx) => ({
          value: val,
          itemStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 1,
              y2: 0,
              colorStops: [
                { offset: 0, color: colors[idx % colors.length] || chartColors[0] },
                { offset: 1, color: '#69c0ff' },
              ],
            },
            borderRadius: [0, 6, 6, 0],
          },
        })),
        barMaxWidth: 18,
        label: {
          show: true,
          position: 'right',
          color: '#595959',
          fontSize: 11,
        },
      },
    ],
  }
}

/** 多色柱状图（科室对比） */
export function getColorBarChartOption({ xAxisData = [], seriesData = [], title = '', yAxisName = '' } = {}) {
  const categoryCount = xAxisData.length
  const isDense = categoryCount > 10
  return {
    color: chartColors,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    grid: {
      left: 56,
      right: 20,
      bottom: isDense ? 88 : 40,
      top: title ? 44 : 28,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: xAxisData,
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisLabel: {
        color: '#595959',
        fontSize: 12,
        interval: 0,
        rotate: isDense ? 35 : 0,
      },
    },
    yAxis: {
      type: 'value',
      name: yAxisName || undefined,
      nameTextStyle: { color: '#8c8c8c', fontSize: 12 },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
      axisLabel: { color: '#595959', fontSize: 12 },
    },
    ...(title ? { title: { text: title, left: 12, textStyle: { fontSize: 14, color: '#262626', fontWeight: 600 } } } : {}),
    series: [
      {
        name: yAxisName || '数值',
        type: 'bar',
        data: seriesData.map((val, idx) => ({
          value: val,
          itemStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: chartColors[idx % chartColors.length] },
                { offset: 1, color: `${chartColors[idx % chartColors.length]}55` },
              ],
            },
            borderRadius: [6, 6, 0, 0],
          },
        })),
        barMaxWidth: 42,
        label: {
          show: categoryCount <= 14,
          position: 'top',
          color: '#595959',
          fontSize: 11,
        },
      },
    ],
  }
}
