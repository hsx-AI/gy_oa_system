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
