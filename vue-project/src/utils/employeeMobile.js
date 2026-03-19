import { getEmployeeProfile } from '@/api/attendance'

/**
 * 根据姓名从 /auth/profile 取人事信息库（demo.employee_info）同步的手机号；无则返回空串
 */
export async function fetchProfileMobile(name) {
  const n = (name || '').trim()
  if (!n) return ''
  try {
    const res = await getEmployeeProfile({ name: n })
    const m =
      res?.success && res?.data?.mobile != null
        ? String(res.data.mobile).trim()
        : ''
    return m
  } catch {
    return ''
  }
}
