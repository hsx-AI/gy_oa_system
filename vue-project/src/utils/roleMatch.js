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
