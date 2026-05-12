<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">{{ isEdit ? '编辑问题记录' : '新建问题记录' }}</h1>
          <p class="header-subtitle">工艺技术问题手册 — {{ isEdit ? '修改已有记录' : '录入新的技术问题' }}</p>
        </div>
        <div class="header-actions">
          <button class="btn btn-default" @click="goBack">← 返回列表</button>
        </div>
      </div>
    </div>

    <div class="content mt-xl">
      <div v-if="pageLoading" class="empty-text">加载中...</div>
      <form v-else class="form-container" @submit.prevent="submitForm">
        <!-- 基本信息 -->
        <div class="card mb-lg">
          <div class="card-header"><h3>基本信息</h3></div>
          <div class="card-body">
            <div class="form-row">
              <div class="form-group flex-1">
                <label>分类 <span class="required">*</span></label>
                <input
                  v-model="form.category"
                  type="text"
                  list="category-list"
                  placeholder="输入或选择分类"
                  required
                >
                <datalist id="category-list">
                  <option v-for="c in categories" :key="c" :value="c" />
                </datalist>
              </div>
              <div class="form-group flex-1">
                <label>所属专业</label>
                <select v-model="form.department">
                  <option value="">请选择</option>
                  <option v-for="d in departments" :key="d" :value="d">{{ d }}</option>
                </select>
              </div>
              <div class="form-group flex-2">
                <label>主题 <span class="required">*</span></label>
                <input v-model="form.title" type="text" placeholder="请输入问题主题" required>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group flex-1">
                <label>记录人 <span class="required">*</span></label>
                <input v-model="form.recorder" type="text" placeholder="记录人姓名" required>
              </div>
              <div class="form-group flex-1">
                <label>记录时间 <span class="required">*</span></label>
                <input v-model="form.record_time" type="month" required>
              </div>
            </div>
          </div>
        </div>

        <!-- 问题描述 -->
        <div class="card mb-lg">
          <div class="card-header"><h3>问题描述 <span class="required">*</span></h3></div>
          <div class="card-body">
            <div class="form-group">
              <textarea
                v-model="form.problem_desc"
                rows="6"
                placeholder="请详细描述问题（支持数百字）"
                required
              ></textarea>
            </div>
            <div class="form-group">
              <label>配图（可选，最多 10 张，单张限 5MB，支持拖拽 / 粘贴）</label>
              <div
                class="image-upload-area"
                :class="{ 'drag-over': dragGroup === 'problem' }"
                @dragover.prevent="dragGroup = 'problem'"
                @dragleave.prevent="dragGroup = ''"
                @drop.prevent="e => onDrop(e, 'problem')"
                @paste.prevent="e => onPaste(e, 'problem')"
                tabindex="0"
              >
                <div v-for="(img, i) in problemImages" :key="'pi' + i" class="image-thumb-wrap">
                  <img :src="img.url" class="image-thumb">
                  <button type="button" class="image-remove" @click="removeImage('problem', i)">×</button>
                </div>
                <label v-if="problemImages.length < 10" class="image-add-btn">
                  <input type="file" :accept="IMAGE_ACCEPT" multiple hidden @change="e => onFileChange(e, 'problem')">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/></svg>
                  <span class="upload-hint">点击、拖拽或粘贴</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- 原因分析 -->
        <div class="card mb-lg">
          <div class="card-header"><h3>原因分析 <span class="required">*</span></h3></div>
          <div class="card-body">
            <div class="form-group">
              <textarea
                v-model="form.cause_analysis"
                rows="5"
                placeholder="请分析问题产生的原因"
                required
              ></textarea>
            </div>
            <div class="form-group">
              <label>配图（可选，最多 10 张，单张限 5MB，支持拖拽 / 粘贴）</label>
              <div
                class="image-upload-area"
                :class="{ 'drag-over': dragGroup === 'cause' }"
                @dragover.prevent="dragGroup = 'cause'"
                @dragleave.prevent="dragGroup = ''"
                @drop.prevent="e => onDrop(e, 'cause')"
                @paste.prevent="e => onPaste(e, 'cause')"
                tabindex="0"
              >
                <div v-for="(img, i) in causeImages" :key="'ci' + i" class="image-thumb-wrap">
                  <img :src="img.url" class="image-thumb">
                  <button type="button" class="image-remove" @click="removeImage('cause', i)">×</button>
                </div>
                <label v-if="causeImages.length < 10" class="image-add-btn">
                  <input type="file" :accept="IMAGE_ACCEPT" multiple hidden @change="e => onFileChange(e, 'cause')">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/></svg>
                  <span class="upload-hint">点击、拖拽或粘贴</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- 采取措施及效果（可选） -->
        <div class="card mb-lg">
          <div class="card-header">
            <h3>采取措施及效果</h3>
            <span class="optional-tag">选填，可后期补充</span>
          </div>
          <div class="card-body">
            <div class="form-group">
              <textarea
                v-model="form.measures"
                rows="5"
                placeholder="描述采取的措施及效果（可留空，后期编辑补充）"
              ></textarea>
            </div>
            <div class="form-group">
              <label>配图（可选，最多 10 张，单张限 5MB，支持拖拽 / 粘贴）</label>
              <div
                class="image-upload-area"
                :class="{ 'drag-over': dragGroup === 'measures' }"
                @dragover.prevent="dragGroup = 'measures'"
                @dragleave.prevent="dragGroup = ''"
                @drop.prevent="e => onDrop(e, 'measures')"
                @paste.prevent="e => onPaste(e, 'measures')"
                tabindex="0"
              >
                <div v-for="(img, i) in measuresImages" :key="'mi' + i" class="image-thumb-wrap">
                  <img :src="img.url" class="image-thumb">
                  <button type="button" class="image-remove" @click="removeImage('measures', i)">×</button>
                </div>
                <label v-if="measuresImages.length < 10" class="image-add-btn">
                  <input type="file" :accept="IMAGE_ACCEPT" multiple hidden @change="e => onFileChange(e, 'measures')">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/></svg>
                  <span class="upload-hint">点击、拖拽或粘贴</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- 提交 -->
        <div class="form-submit-bar">
          <button type="button" class="btn btn-default btn-lg" @click="goBack">取消</button>
          <button type="submit" class="btn btn-outline btn-lg" :disabled="submitting">
            保存
          </button>
          <button type="submit" class="btn btn-primary btn-lg" :disabled="submitting">
            {{ submitting ? '提交中...' : (isEdit ? '保存修改' : '提交') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { createTechProblem, updateTechProblem, getTechProblemDetail, getTechProblemCategories, getTechProblemDepartments, getTechProblemImageUrl } from '@/api/techProblem'

const router = useRouter()
const route = useRoute()

const editId = computed(() => route.params.id || null)
const isEdit = computed(() => !!editId.value)

const pageLoading = ref(false)
const submitting = ref(false)
const categories = ref([])
const departments = ref([])

const form = reactive({
  category: '',
  department: '',
  title: '',
  recorder: '',
  record_time: '',
  problem_desc: '',
  cause_analysis: '',
  measures: ''
})

const problemImages = ref([])
const causeImages = ref([])
const measuresImages = ref([])

const MAX_SIZE = 5 * 1024 * 1024
const MAX_IMAGES = 10
const ALLOWED_IMAGE_EXT = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
const ALLOWED_IMAGE_MIME = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp']
const IMAGE_ACCEPT = [...ALLOWED_IMAGE_EXT, ...ALLOWED_IMAGE_MIME].join(',')
const MIME_EXT_MAP = {
  'image/jpeg': '.jpg',
  'image/png': '.png',
  'image/gif': '.gif',
  'image/bmp': '.bmp',
  'image/webp': '.webp'
}
const dragGroup = ref('')

function initRecorder() {
  try {
    const raw = localStorage.getItem('userInfo')
    if (raw) {
      const u = JSON.parse(raw)
      form.recorder = u.name || u.userName || ''
      form.department = u.dept || u.lsys || ''
    }
  } catch { /* ignore */ }
}

function initRecordTime() {
  const now = new Date()
  form.record_time = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function getTargetArr(group) {
  return group === 'problem' ? problemImages : group === 'cause' ? causeImages : measuresImages
}

function imageExt(file) {
  const name = file?.name || ''
  const dot = name.lastIndexOf('.')
  return dot >= 0 ? name.slice(dot).toLowerCase() : ''
}

function imageDisplayName(file) {
  return file?.name || '粘贴图片'
}

function normalizeImageFile(file) {
  const ext = imageExt(file)
  if (ext) return file
  const inferredExt = MIME_EXT_MAP[file?.type || '']
  if (!inferredExt) return file
  return new File([file], `pasted-image-${Date.now()}${inferredExt}`, { type: file.type })
}

function validateImageFile(file) {
  const normalized = normalizeImageFile(file)
  const ext = imageExt(normalized)
  const type = normalized?.type || ''
  if (!ALLOWED_IMAGE_EXT.includes(ext) || (type && !ALLOWED_IMAGE_MIME.includes(type))) {
    return {
      valid: false,
      file: normalized,
      message: `图片 "${imageDisplayName(file)}" 格式不支持，仅支持 JPG、PNG、GIF、BMP、WEBP`
    }
  }
  if (normalized.size > MAX_SIZE) {
    return {
      valid: false,
      file: normalized,
      message: `图片 "${imageDisplayName(file)}" 超过 5MB 限制`
    }
  }
  return { valid: true, file: normalized }
}

function addFiles(files, group) {
  const targetArr = getTargetArr(group)
  const messages = []
  for (const f of files) {
    if (targetArr.value.length >= MAX_IMAGES) {
      messages.push(`每个区域最多上传 ${MAX_IMAGES} 张图片`)
      break
    }
    const result = validateImageFile(f)
    if (!result.valid) {
      messages.push(result.message)
      continue
    }
    targetArr.value.push({
      file: result.file,
      url: URL.createObjectURL(result.file),
      existing: false
    })
  }
  if (messages.length) {
    alert([...new Set(messages)].join('\n'))
  }
}

function onFileChange(e, group) {
  addFiles(Array.from(e.target.files || []), group)
  e.target.value = ''
}

function onDrop(e, group) {
  dragGroup.value = ''
  const files = Array.from(e.dataTransfer?.files || [])
  if (files.length) {
    addFiles(files, group)
  }
}

function onPaste(e, group) {
  const items = Array.from(e.clipboardData?.items || [])
  const files = items
    .filter(item => item.kind === 'file')
    .map(item => item.getAsFile())
    .filter(Boolean)
  if (files.length) {
    addFiles(files, group)
  }
}

function removeImage(group, idx) {
  const targetArr = group === 'problem' ? problemImages : group === 'cause' ? causeImages : measuresImages
  const item = targetArr.value[idx]
  if (item && !item.existing) URL.revokeObjectURL(item.url)
  targetArr.value.splice(idx, 1)
}

function buildFormData() {
  const fd = new FormData()
  fd.append('category', form.category)
  fd.append('department', form.department || '')
  fd.append('title', form.title)
  fd.append('recorder', form.recorder)
  fd.append('record_time', form.record_time)
  fd.append('problem_desc', form.problem_desc)
  fd.append('cause_analysis', form.cause_analysis)
  fd.append('measures', form.measures || '')

  const existingProblem = []
  const existingCause = []
  const existingMeasures = []

  for (const img of problemImages.value) {
    if (img.existing) existingProblem.push(img.filename)
    else fd.append('problem_files', img.file)
  }
  for (const img of causeImages.value) {
    if (img.existing) existingCause.push(img.filename)
    else fd.append('cause_files', img.file)
  }
  for (const img of measuresImages.value) {
    if (img.existing) existingMeasures.push(img.filename)
    else fd.append('measures_files', img.file)
  }

  fd.append('existing_problem_images', JSON.stringify(existingProblem))
  fd.append('existing_cause_images', JSON.stringify(existingCause))
  fd.append('existing_measures_images', JSON.stringify(existingMeasures))

  return fd
}

async function submitForm() {
  if (!form.category.trim() || !form.title.trim() || !form.recorder.trim() || !form.record_time) {
    alert('请填写所有必填项')
    return
  }
  if (!form.problem_desc.trim()) {
    alert('请填写问题描述')
    return
  }
  if (!form.cause_analysis.trim()) {
    alert('请填写原因分析')
    return
  }
  submitting.value = true
  try {
    const fd = buildFormData()
    if (isEdit.value) {
      await updateTechProblem(editId.value, fd)
    } else {
      await createTechProblem(fd)
    }
    alert(isEdit.value ? '修改成功' : '创建成功')
    router.push('/file/tech-problem')
  } catch (e) {
    alert('提交失败: ' + (e.message || e))
  } finally {
    submitting.value = false
  }
}

async function loadDetail() {
  pageLoading.value = true
  try {
    const res = await getTechProblemDetail(editId.value)
    form.category = res.category || ''
    form.department = res.department || ''
    form.title = res.title || ''
    form.recorder = res.recorder || ''
    form.record_time = res.record_time || ''
    form.problem_desc = res.problem_desc || ''
    form.cause_analysis = res.cause_analysis || ''
    form.measures = res.measures || ''

    if (res.problem_images) {
      problemImages.value = res.problem_images.map(f => ({ filename: f, url: getTechProblemImageUrl(f), existing: true }))
    }
    if (res.cause_images) {
      causeImages.value = res.cause_images.map(f => ({ filename: f, url: getTechProblemImageUrl(f), existing: true }))
    }
    if (res.measures_images) {
      measuresImages.value = res.measures_images.map(f => ({ filename: f, url: getTechProblemImageUrl(f), existing: true }))
    }
  } catch (e) {
    alert('加载详情失败: ' + (e.message || e))
    router.push('/file/tech-problem')
  } finally {
    pageLoading.value = false
  }
}

async function loadCategories() {
  try {
    const res = await getTechProblemCategories()
    categories.value = res.categories || []
  } catch { /* ignore */ }
}

async function loadDepartments() {
  try {
    const res = await getTechProblemDepartments()
    departments.value = res.departments || []
  } catch { /* ignore */ }
}

function goBack() {
  router.push('/file/tech-problem')
}

onMounted(() => {
  loadCategories()
  loadDepartments()
  if (isEdit.value) {
    loadDetail()
  } else {
    initRecorder()
    initRecordTime()
  }
})
</script>

<style scoped>
.page-container {
  width: 100%;
  max-width: none;
  margin: 0;
  padding-top: 0;
  padding-bottom: var(--spacing-xl);
  padding-left: 0;
  padding-right: 0;
}

.form-container {
  width: 100%;
  max-width: none;
}

.card {
  background: var(--color-bg-container);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  border: 1px solid var(--color-border-lighter);
}

.card-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-lighter);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-body {
  padding: var(--spacing-lg);
}

.empty-text {
  text-align: center;
  color: var(--color-text-secondary);
  padding: var(--spacing-xxl) 0;
}

.form-row {
  display: flex;
  gap: var(--spacing-base);
  flex-wrap: wrap;
}
.flex-1 { flex: 1; min-width: 200px; }
.flex-2 { flex: 2; min-width: 280px; }

.form-group {
  margin-bottom: var(--spacing-lg);
}
.form-group label {
  display: block;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
}

.required {
  color: var(--color-error);
}
.optional-tag {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-weight: var(--font-weight-regular);
}

.form-group input[type="text"],
.form-group input[type="month"],
.form-group select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-base);
  outline: none;
  transition: border-color var(--transition-base) var(--transition-ease), box-shadow var(--transition-base);
  box-sizing: border-box;
  color: var(--color-text-primary);
  background: var(--color-bg-container);
}
.form-group input[type="text"]:focus,
.form-group input[type="month"]:focus,
.form-group select:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-lightest);
}
.form-group input[type="text"]::placeholder {
  color: var(--color-text-quaternary);
}

.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-base);
  line-height: var(--line-height-lg);
  outline: none;
  resize: vertical;
  transition: border-color var(--transition-base) var(--transition-ease), box-shadow var(--transition-base);
  box-sizing: border-box;
  font-family: inherit;
  color: var(--color-text-primary);
  background: var(--color-bg-container);
}
.form-group textarea:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-lightest);
}
.form-group textarea::placeholder {
  color: var(--color-text-quaternary);
}

/* 图片上传区 */
.image-upload-area {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-xs);
  padding: var(--spacing-sm);
  border: 2px dashed transparent;
  border-radius: var(--radius-md);
  transition: border-color var(--transition-base), background var(--transition-base);
  outline: none;
  min-height: 96px;
}
.image-upload-area:focus-within,
.image-upload-area:focus {
  border-color: var(--color-primary-lighter);
}
.image-upload-area.drag-over {
  border-color: var(--color-primary);
  background: var(--color-primary-lightest);
}
.image-thumb-wrap {
  position: relative;
  width: 100px;
  height: 80px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--color-border-lighter);
}
.image-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.image-remove {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 22px;
  height: 22px;
  border-radius: var(--radius-circle);
  background: var(--color-bg-mask);
  color: #fff;
  border: none;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  transition: background var(--transition-base);
}
.image-remove:hover {
  background: var(--color-error);
}
.image-add-btn {
  width: 130px;
  height: 96px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 10px 12px;
  box-sizing: border-box;
  border: 2px dashed var(--color-border-base);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color var(--transition-base), background var(--transition-base);
}
.image-add-btn:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-lightest);
}
.image-add-btn svg {
  color: var(--color-text-tertiary);
  margin-bottom: 2px;
}
.upload-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-quaternary);
  line-height: 1.2;
  text-align: center;
}

.form-submit-bar {
  display: flex;
  gap: var(--spacing-md);
  justify-content: flex-end;
  padding: var(--spacing-lg) 0 var(--spacing-xxl);
}
</style>
