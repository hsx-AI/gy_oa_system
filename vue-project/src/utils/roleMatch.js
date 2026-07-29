/**
 * 职务(jb) -> 权限级别 映射。
 * 部长权限: 部长, 经理
 * 副部长权限: 副部长, 副经理, 经理助理
 * 主任权限: 主任
 * 副主任权限: 副主任
 * 组长权限: 组长, 班组长
 * 其他均为普通员工权限。
 */

const ROLE_MAP = {
  部长: ['部长', '经理'],
  副部长: ['副部长', '副经理', '经理助理'],
  主任: ['主任'],
  副主任: ['副主任'],
  组长: ['组长', '班组长'],
}

function _normalize(jb) {
  return (jb || '').trim()
}

export function jbMatch(jb, target) {
  const j = _normalize(jb)
  if (!j) return false
  const titles = ROLE_MAP[target]
  if (titles) {
    for (const t of titles) {
      if (j === t || j.startsWith(t)) return true
    }
    if (target === '副主任' && j.includes('副主任')) return true
    return false
  }
  return j === target || j.startsWith(target)
}

export function isMinisterLevel(jb) {
  return jbMatch(jb, '部长') || jbMatch(jb, '副部长')
}

export function isMinisterOnly(jb) {
  return jbMatch(jb, '部长')
}

export function isDeptLeader(jb) {
  return jbMatch(jb, '组长') || jbMatch(jb, '主任') || jbMatch(jb, '副主任')
}

export function isMinisterOrDeptLeader(jb) {
  return isMinisterLevel(jb) || isDeptLeader(jb)
}

export function isDirectorLevel(jb) {
  return jbMatch(jb, '主任') || jbMatch(jb, '副主任')
}

/** 综合技术室主任/副主任：工作强度可查看全员 */
export function isZongheTechDirector({ jb, lsys }) {
  const l = (lsys || '').trim()
  if (l !== '综合技术室') return false
  return isDirectorLevel(jb)
}

export function isAdmin2User(name, admin2) {
  const n = (name || '').trim()
  const a2 = (admin2 || '').trim()
  return !!(a2 && n === a2)
}

export function isAdmin1User(name, admin1) {
  const n = (name || '').trim()
  const a1 = (admin1 || '').trim()
  return !!(a1 && n === a1)
}

/** 工作强度全员/任意科室：admin1/admin2、综合技术室主任/副主任 */
export function hasWorkIntensityAllScope({ name, jb, lsys, admin1, admin2 }) {
  if (isAdmin2User(name, admin2) || isAdmin1User(name, admin1)) return true
  return isZongheTechDirector({ jb, lsys })
}

function isDepartmentManagerJb(jb) {
  const j = _normalize(jb)
  if (!j) return false
  return j.includes('经理助理') || j.includes('副经理') || jbMatch(j, '经理') || j === '经理'
}

/** 工作强度模块可见：admin1/admin2、经理层、或各科室主任/副主任/主任责/班组长/组长 */
export function canSeeWorkIntensityInStatistics(jb, { name, admin1, admin2 } = {}) {
  if (isAdmin2User(name, admin2) || isAdmin1User(name, admin1)) return true
  if (isDepartmentManagerJb(jb)) return true
  const j = _normalize(jb)
  if (!j) return false
  if (j.includes('副主任')) return true
  if (j.includes('主任责')) return true
  if (jbMatch(j, '主任')) return true
  if (jbMatch(j, '组长')) return true
  return false
}

/** 领导加班统计：仅部长/副部长 */
export function canAccessLeaderOvertimeStats(jb) {
  return isMinisterLevel(jb)
}

/**
 * AI 助手公测开放范围：
 *  - 智能制造技术室全员（lsys === '智能制造技术室'）；
 *  - 公司经理 / 副经理 / 经理助理（jb 精确匹配）。
 */
export function canUseAiAssistant({ jb, lsys }) {
  const l = (lsys || '').trim()
  if (l === '智能制造技术室') return true
  const j = (jb || '').trim()
  return j === '经理' || j === '副经理' || j === '经理助理'
}

/** 换休票批量管理：admin1、admin2、部长/副部长、综合技术室主任/副主任 */
export function canManageHxpBatch({ name, jb, lsys, admin1, admin2 }) {
  if (isAdmin1User(name, admin1) || isAdmin2User(name, admin2)) return true
  if (isMinisterLevel(jb)) return true
  return isZongheTechDirector({ jb, lsys })
}

/** 管理驾驶舱 / 考勤纪律审查：部长副部长、综合技术室主任副主任、admin1、admin2 */
export function canAccessLeaderDashboard({ name, jb, lsys, admin1, admin2 }) {
  const n = (name || '').trim()
  const a1 = (admin1 || '').trim()
  const a2 = (admin2 || '').trim()
  if (a1 && n === a1) return true
  if (a2 && n === a2) return true
  if (isMinisterLevel(jb)) return true
  if ((lsys || '').trim() === '综合技术室' && isDirectorLevel(jb)) return true
  return false
}
