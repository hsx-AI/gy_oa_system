/**
 * 记录表：前端关键词筛选与排序（在已拉取的列表上处理）
 */

export function keywordMatches(kw, fields) {
  const k = (kw || '').trim().toLowerCase()
  if (!k) return true
  return fields.some((f) => String(f ?? '').toLowerCase().includes(k))
}

export function compareByDateStrings(a, b) {
  const ta = Date.parse(String(a || '').replace(' ', 'T'))
  const tb = Date.parse(String(b || '').replace(' ', 'T'))
  const na = Number.isNaN(ta) ? 0 : ta
  const nb = Number.isNaN(tb) ? 0 : tb
  if (na < nb) return -1
  if (na > nb) return 1
  return 0
}

export function compareStrings(a, b) {
  return String(a ?? '').localeCompare(String(b ?? ''), 'zh-CN')
}

export function compareNumbers(a, b) {
  const na = Number(a)
  const nb = Number(b)
  if (Number.isNaN(na) && Number.isNaN(nb)) return 0
  if (Number.isNaN(na)) return 1
  if (Number.isNaN(nb)) return -1
  if (na < nb) return -1
  if (na > nb) return 1
  return 0
}

/**
 * @param {Array} rows
 * @param {string} sortVal 形如 field_desc | field_asc
 * @param {{ field: string, get: (r) => any }[]} fieldMap
 */
export function sortRecordRows(rows, sortVal, fieldMap) {
  if (!sortVal || !rows.length) return [...rows]
  const [field, ord] = String(sortVal).split('_')
  const dir = ord === 'asc' ? 1 : -1
  const spec = fieldMap.find((x) => x.field === field)
  const get = spec?.get || ((r) => r[field])
  const copy = [...rows]
  copy.sort((a, b) => {
    const va = get(a)
    const vb = get(b)
    let c = 0
    if (spec?.type === 'number') c = compareNumbers(va, vb)
    else if (spec?.type === 'date') c = compareByDateStrings(va, vb)
    else c = compareStrings(va, vb)
    if (c !== 0) return dir * c
    return compareStrings(String(a.id ?? ''), String(b.id ?? ''))
  })
  return copy
}
