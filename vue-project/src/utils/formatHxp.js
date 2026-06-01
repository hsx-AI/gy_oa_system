/** 换休票数量展示：最小步长 0.125，最多保留 3 位小数并去掉多余尾零 */

export function formatHxpAmount(v) {
  if (v == null || v === '') return '—'
  const f = parseFloat(v)
  if (Number.isNaN(f)) return '—'
  if (f === Math.floor(f)) return String(f)
  return parseFloat(f.toFixed(3)).toString()
}
