<template>
  <div v-if="visible" class="modal-overlay" @click.self="onClose">
    <div class="modal-content">
      <button type="button" class="modal-close-btn" @click="onClose">&times;</button>
      <h2 class="modal-title">打卡异常申请</h2>
      <p class="modal-subtitle">基于考勤建议发起，二级审批通过后将自动处理为该时段的市内公出</p>

      <form class="kqyc-form" @submit.prevent="handleSubmit" autocomplete="off">
        <div class="form-row">
          <div class="form-group half">
            <label>申请人</label>
            <input type="text" :value="form.applicant" disabled>
          </div>
          <div class="form-group half">
            <label>所在科室</label>
            <input type="text" :value="form.department" disabled>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group full">
            <label>异常日期 <span class="required">*</span></label>
            <input type="date" v-model="form.attendance_date" :readonly="lockedDate" :class="{ 'locked': lockedDate }">
            <small v-if="lockedDate" class="hint">日期由智能建议预填，如需修改请取消后手动重新发起</small>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group half">
            <label>异常时段-开始 <span class="required">*</span></label>
            <input type="time" v-model="form.time_from" step="1" :readonly="lockedTime" :class="{ 'locked': lockedTime }">
          </div>
          <div class="form-group half">
            <label>异常时段-结束 <span class="required">*</span></label>
            <input type="time" v-model="form.time_to" step="1" :readonly="lockedTime" :class="{ 'locked': lockedTime }">
          </div>
        </div>

        <div class="form-row">
          <div class="form-group full">
            <label>事由 <span class="required">*</span></label>
            <select v-model="form.reason_type">
              <option value="">请选择事由</option>
              <option v-for="r in reasonOptions" :key="r" :value="r">{{ r }}</option>
            </select>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group full">
            <label>情况说明 <span class="required">*</span></label>
            <textarea v-model="form.description" rows="4" placeholder="请详细说明本次打卡异常的情况（必填）"></textarea>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group full">
            <label>佐证材料 <span class="required">*</span></label>
            <div class="file-upload" :class="{ 'has-file': selectedFile }">
              <input ref="fileInput" type="file" class="file-hidden" :accept="acceptExts" @change="onFileChange">
              <div v-if="!selectedFile" class="file-placeholder" @click="$refs.fileInput.click()">
                <span>点击上传附件</span>
                <small>支持 Word、Excel、PPT、PDF、图片、压缩包等（必传）</small>
              </div>
              <div v-else class="file-selected">
                <span class="file-name">{{ selectedFile.name }}</span>
                <small class="file-size">{{ formatSize(selectedFile.size) }}</small>
                <button type="button" class="file-remove" @click="removeFile" title="移除">&times;</button>
              </div>
            </div>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group half">
            <label>一级审批人 <span v-if="!skipFirstApproval" class="required">*</span></label>
            <select v-model="form.first_approver" :disabled="loadingFirst || skipFirstApproval">
              <option value="">{{ firstApproverPlaceholder }}</option>
              <option v-for="a in firstApprovers" :key="a.name" :value="a.name">{{ a.label }}</option>
            </select>
            <small v-if="skipFirstApproval" class="hint">当前科室无可用一级审批人，将直接提交至二级审批</small>
          </div>
          <div class="form-group half">
            <label>二级审批人 <span class="required">*</span></label>
            <select v-model="form.second_approver" :disabled="loadingSecond">
              <option value="">{{ loadingSecond ? '加载中...' : '请选择经理/副经理' }}</option>
              <option v-for="a in secondApprovers" :key="a.name" :value="a.name">{{ a.label }}</option>
            </select>
          </div>
        </div>

        <div class="form-tips">
          <p>1. 一级 主任/副主任/班组长 → 二级 经理/副经理；</p>
          <p>2. 二级审批通过后，系统自动将该时段写入市内公出记录；</p>
          <p>3. 处理结果会通知打卡管理员进行已读确认。</p>
        </div>

        <div class="form-actions">
          <button type="button" class="btn-cancel" @click="onClose">取消</button>
          <button type="submit" class="btn-submit" :disabled="submitting">
            {{ submitting ? '提交中...' : '提交申请' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { getKqycApprovers, submitKqycApply } from '@/api/attendanceException'

const props = defineProps({
  visible: { type: Boolean, default: false },
  prefill: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['close', 'submitted'])

const reasonOptions = ['忘记刷脸', '错误刷脸', '24:00之后离厂', '打卡机器异常']

const acceptExts = '.doc,.docx,.xls,.xlsx,.ppt,.pptx,.pdf,.txt,.csv,.jpg,.jpeg,.png,.gif,.bmp,.webp,.zip,.rar,.7z,.odt,.ods,.odp,.wps,.et'

function getCurrentUser() {
  try {
    const u = JSON.parse(localStorage.getItem('userInfo') || '{}')
    return {
      name: (u.name || u.userName || '').trim(),
      dept: (u.dept || u.lsys || u.department || '').trim(),
    }
  } catch {
    return { name: '', dept: '' }
  }
}

const form = reactive({
  applicant: '',
  department: '',
  attendance_date: '',
  time_from: '',
  time_to: '',
  reason_type: '',
  description: '',
  first_approver: '',
  second_approver: '',
})

const selectedFile = ref(null)
const submitting = ref(false)
const firstApprovers = ref([])
const secondApprovers = ref([])
const loadingFirst = ref(false)
const loadingSecond = ref(false)
const fileInput = ref(null)
const skipFirstApproval = ref(false)

const lockedDate = computed(() => !!props.prefill?.locked && !!props.prefill?.attendance_date)
const lockedTime = computed(() => !!props.prefill?.locked && (!!props.prefill?.time_from || !!props.prefill?.time_to))
const firstApproverPlaceholder = computed(() => {
  if (loadingFirst.value) return '加载中...'
  if (skipFirstApproval.value) return '无需一级审批'
  return '请选择主任/副主任/班组长'
})

function resetForm() {
  const u = getCurrentUser()
  form.applicant = u.name
  form.department = u.dept
  form.attendance_date = props.prefill?.attendance_date || ''
  form.time_from = props.prefill?.time_from || ''
  form.time_to = props.prefill?.time_to || ''
  form.reason_type = ''
  form.description = ''
  form.first_approver = ''
  form.second_approver = ''
  skipFirstApproval.value = false
  selectedFile.value = null
  if (fileInput.value) fileInput.value.value = ''
}

async function loadApprovers() {
  const name = form.applicant
  if (!name) return
  loadingFirst.value = true
  loadingSecond.value = true
  try {
    const [r1, r2] = await Promise.all([
      getKqycApprovers({ name, level: 'first' }),
      getKqycApprovers({ name, level: 'second' }),
    ])
    firstApprovers.value = (r1?.approvers) || []
    secondApprovers.value = (r2?.approvers) || []
    skipFirstApproval.value = !!r1?.skip_first_approval
    if (skipFirstApproval.value) form.first_approver = ''
  } catch (e) {
    firstApprovers.value = []
    secondApprovers.value = []
    skipFirstApproval.value = false
  } finally {
    loadingFirst.value = false
    loadingSecond.value = false
  }
}

watch(
  () => props.visible,
  (v) => {
    if (v) {
      resetForm()
      loadApprovers()
    }
  },
  { immediate: true }
)

function onFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  selectedFile.value = file
}

function removeFile() {
  selectedFile.value = null
  if (fileInput.value) fileInput.value.value = ''
}

function formatSize(bytes) {
  if (!bytes) return ''
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  return `${(kb / 1024).toFixed(2)} MB`
}

function onClose() {
  emit('close')
}

async function handleSubmit() {
  const tips = []
  if (!form.attendance_date) tips.push('异常日期')
  if (!form.time_from) tips.push('开始时间')
  if (!form.time_to) tips.push('结束时间')
  if (form.time_from && form.time_to && form.time_to <= form.time_from) {
    alert('结束时间需晚于开始时间')
    return
  }
  if (!form.reason_type) tips.push('事由')
  if (!(form.description || '').trim()) tips.push('情况说明')
  if (!selectedFile.value) tips.push('佐证材料')
  if (!skipFirstApproval.value && !form.first_approver) tips.push('一级审批人')
  if (!form.second_approver) tips.push('二级审批人')
  if (form.first_approver && form.first_approver === form.second_approver) {
    alert('一级与二级审批人不能为同一人')
    return
  }
  if (tips.length) {
    alert('请完善以下内容：\n· ' + tips.join('\n· '))
    return
  }

  submitting.value = true
  try {
    const res = await submitKqycApply({
      ...form,
      attachment: selectedFile.value,
    })
    if (res?.success) {
      alert('打卡异常申请已提交，请等待审批')
      emit('submitted')
      emit('close')
    } else {
      alert(res?.message || '提交失败')
    }
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '提交失败'
    alert(typeof msg === 'string' ? msg : '提交失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 9999;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 40px 16px;
  overflow-y: auto;
}

.modal-content {
  background: #fff;
  border-radius: 12px;
  width: 100%;
  max-width: 640px;
  position: relative;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  padding: 28px 28px 22px;
}

.modal-close-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #888;
  border-radius: 4px;
}
.modal-close-btn:hover {
  background: #f5f5f5;
  color: #333;
}

.modal-title {
  margin: 0 0 6px;
  font-size: 20px;
  font-weight: 600;
  color: #222;
}
.modal-subtitle {
  color: #888;
  font-size: 13px;
  margin: 0 0 18px;
}

.kqyc-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-row {
  display: flex;
  gap: 14px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-group.full { flex: 1 1 100%; }
.form-group.half { flex: 1 1 0; }

.form-group label {
  font-size: 13px;
  color: #444;
  font-weight: 500;
}
.required { color: #ef4444; margin-left: 2px; }

.form-group input,
.form-group select,
.form-group textarea {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  color: #222;
  outline: none;
  transition: border-color 0.15s;
}
.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  border-color: #3b82f6;
}
.form-group input:disabled,
.form-group input[readonly].locked {
  background: #f3f4f6;
  color: #6b7280;
  cursor: not-allowed;
}
.hint { color: #6b7280; font-size: 12px; }

.file-upload {
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  padding: 18px;
  transition: border-color 0.15s;
}
.file-upload.has-file { border-style: solid; border-color: #3b82f6; padding: 10px 14px; }
.file-hidden { display: none; }
.file-placeholder {
  text-align: center;
  cursor: pointer;
  color: #6b7280;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.file-placeholder:hover { color: #3b82f6; }
.file-placeholder small { font-size: 12px; color: #9ca3af; }

.file-selected {
  display: flex;
  align-items: center;
  gap: 10px;
}
.file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #222;
  font-size: 14px;
}
.file-size { color: #6b7280; font-size: 12px; }
.file-remove {
  background: transparent;
  border: none;
  color: #ef4444;
  font-size: 20px;
  cursor: pointer;
  padding: 0 6px;
}

.form-tips {
  margin: 6px 0;
  padding: 12px 14px;
  background: #f0f9ff;
  border-left: 3px solid #3b82f6;
  border-radius: 4px;
  color: #1e3a8a;
  font-size: 12.5px;
}
.form-tips p { margin: 0; line-height: 1.6; }

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}
.btn-cancel,
.btn-submit {
  padding: 8px 22px;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  font-size: 14px;
  cursor: pointer;
  background: #fff;
  transition: all 0.15s;
}
.btn-cancel:hover { background: #f9fafb; }
.btn-submit {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  border-color: transparent;
  color: #fff;
  font-weight: 500;
}
.btn-submit:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(79, 172, 254, 0.4);
  transform: translateY(-1px);
}
.btn-submit:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
