function normalizeText(v) {
  return String(v || '').trim()
}

function readUserInfo() {
  try {
    return JSON.parse(localStorage.getItem('userInfo') || '{}')
  } catch {
    return {}
  }
}

export function getOvertimeUserMeta(source = {}) {
  const userInfo = readUserInfo()
  const jb = normalizeText(source.jb || userInfo.jb)
  const lsys = normalizeText(
    source.lsys ||
    source.dept ||
    source.department ||
    userInfo.lsys ||
    userInfo.dept ||
    userInfo.department
  )
  return { jb, lsys }
}

export function isManagerLevelLeader(source = {}) {
  const { jb } = getOvertimeUserMeta(source)
  return ['经理', '副经理', '经理助理'].some((role) => jb === role || jb.startsWith(role))
}

export function isBubanUser(source = {}) {
  return getOvertimeUserMeta(source).lsys === '部办'
}

export function isBubanOtherLeader(source = {}) {
  return isBubanUser(source) && !isManagerLevelLeader(source)
}

export function shouldSkipOvertimeShiftValidation(source = {}) {
  return isBubanUser(source) || isManagerLevelLeader(source)
}

export function shouldLockExchangeTicketToYes(source = {}) {
  return isManagerLevelLeader(source)
}

export function canChooseExchangeTicketWhenNormalOvertime(source = {}) {
  return isBubanOtherLeader(source)
}
