<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">文件编号管理</h1>
          <p class="header-subtitle">技术文件、技术管理文件、管理文件的编号规则与记录查询</p>
        </div>
        <div class="header-actions">
          <button class="btn" @click="goTechCategory">技术分类录入</button>
          <button class="btn" @click="goWorkNo">工作号录入</button>
          <button class="btn btn-primary" @click="showModal = true">获取编号</button>
        </div>
      </div>
    </div>
    
    <div class="tabs">
      <div 
        class="tab-item" 
        :class="{ active: currentTab === 'tech' }"
        @click="currentTab = 'tech'"
      >
        技术文件编号
      </div>
      <div 
        class="tab-item" 
        :class="{ active: currentTab === 'jsgl' }"
        @click="currentTab = 'jsgl'"
      >
        技术管理文件编号
      </div>
      <div 
        class="tab-item" 
        :class="{ active: currentTab === 'manage' }"
        @click="currentTab = 'manage'"
      >
        管理文件编号
      </div>
    </div>

    <div class="content mt-xl">
      <!-- 搜索栏（技术文件 / 技术管理 / 管理文件） -->
      <div class="search-bar card mb-lg" v-if="currentTab === 'tech' || currentTab === 'jsgl' || currentTab === 'manage'">
        <template v-if="currentTab === 'tech'">
          <input v-model="searchKeyword" type="text" placeholder="搜索编号/文件名/项目..." class="search-input">
          <button type="button" class="btn btn-primary" @click="loadTechList">查询</button>
          <button type="button" class="btn" @click="searchKeyword = ''; loadTechList()">重置</button>
        </template>
        <template v-else-if="currentTab === 'jsgl'">
          <input v-model="searchKeywordJsgl" type="text" placeholder="搜索编号/内容/项目..." class="search-input">
          <button type="button" class="btn btn-primary" @click="loadJsglList">查询</button>
          <button type="button" class="btn" @click="searchKeywordJsgl = ''; loadJsglList()">重置</button>
        </template>
        <template v-else>
          <input v-model="searchKeywordManage" type="text" placeholder="搜索编号/内容..." class="search-input">
          <button type="button" class="btn btn-primary" @click="loadManageList">查询</button>
          <button type="button" class="btn" @click="searchKeywordManage = ''; loadManageList()">重置</button>
        </template>
      </div>

      <!-- 列表 -->
      <div class="card">
        <div class="card-header">
          <h3>{{ currentTab === 'tech' ? '技术文件列表' : currentTab === 'jsgl' ? '技术管理文件列表' : '管理文件列表' }}</h3>
        </div>
        <div class="card-body">
          <template v-if="currentTab === 'tech'">
            <div v-if="techListLoading" class="empty-text">加载中...</div>
            <div v-else-if="filteredTechList.length === 0" class="empty-text">{{ canSeeAllFiles ? '暂无文件记录' : '您只能看到本专业的文件哦' }}</div>
            <div v-else class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>编号单位</th>
                    <th>编制人</th>
                    <th>工作号</th>
                    <th>项目名称</th>
                    <th>编号类别</th>
                    <th>编号内容</th>
                    <th>编号时间</th>
                    <th>编号代码</th>
                    <th>PDF 文件</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in filteredTechList" :key="row.id">
                    <td>{{ row.bz }}</td>
                    <td>{{ row.xm }}</td>
                    <td>{{ row.gzh }}</td>
                    <td>{{ row.cpname }}</td>
                    <td>{{ row.fenlei }}</td>
                    <td>{{ row.neirong }}</td>
                    <td>{{ row.bhtime || '—' }}</td>
                    <td>
                      <span class="bianhao-code">{{ row.bianhao_code }}</span>
                      <button type="button" class="btn-copy-small" @click="copyText(row.bianhao_code)" title="复制">复制</button>
                    </td>
                    <td class="file-actions">
                      <button v-if="!row.has_pdf" type="button" class="btn-copy-small btn-upload" title="请上传终版PDF文件仅支持PDF" @click="triggerUpload('tech', row.bianhao_code)">请上传</button>
                      <template v-else>
                        <button type="button" class="btn-copy-small btn-delete" title="删除后可重新上传" @click="deletePdf('tech', row.bianhao_code)">删除</button>
                        <button type="button" class="btn-copy-small btn-preview" @click="openFile('tech', row.bianhao_code, 0)">预览</button>
                        <button type="button" class="btn-copy-small btn-download" @click="openFile('tech', row.bianhao_code, 1)">下载</button>
                      </template>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="techTotal > 0" class="table-footer">
              共 {{ techTotal }} 条，当前页 {{ filteredTechList.length }} 条
            </div>
          </template>
          <template v-else-if="currentTab === 'jsgl'">
            <div v-if="jsglListLoading" class="empty-text">加载中...</div>
            <div v-else-if="filteredJsglList.length === 0" class="empty-text">{{ canSeeAllFiles ? '暂无文件记录' : '您只能看到本专业的文件哦' }}</div>
            <div v-else class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>编号单位</th>
                    <th>编制人</th>
                    <th>工作号</th>
                    <th>项目名称</th>
                    <th>编号类别</th>
                    <th>编号内容</th>
                    <th>编号时间</th>
                    <th>编号代码</th>
                    <th>PDF 文件</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in filteredJsglList" :key="row.id">
                    <td>{{ row.bz }}</td>
                    <td>{{ row.xm }}</td>
                    <td>{{ row.gzh }}</td>
                    <td>{{ row.cpname }}</td>
                    <td>{{ row.fenleihao || row.fenlei }}</td>
                    <td>{{ row.neirong }}</td>
                    <td>{{ row.bhtime || '—' }}</td>
                    <td>
                      <span class="bianhao-code">{{ row.bianhao_code }}</span>
                      <button type="button" class="btn-copy-small" @click="copyText(row.bianhao_code)" title="复制">复制</button>
                    </td>
                    <td class="file-actions">
                      <button v-if="!row.has_pdf" type="button" class="btn-copy-small btn-upload" title="请上传终版PDF文件仅支持PDF" @click="triggerUpload('jsgl', row.bianhao_code)">请上传</button>
                      <template v-else>
                        <button type="button" class="btn-copy-small btn-delete" title="删除后可重新上传" @click="deletePdf('jsgl', row.bianhao_code)">删除</button>
                        <button type="button" class="btn-copy-small btn-preview" @click="openFile('jsgl', row.bianhao_code, 0)">预览</button>
                        <button type="button" class="btn-copy-small btn-download" @click="openFile('jsgl', row.bianhao_code, 1)">下载</button>
                      </template>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="jsglTotal > 0" class="table-footer">
              共 {{ jsglTotal }} 条，当前页 {{ filteredJsglList.length }} 条
            </div>
          </template>
          <template v-else-if="currentTab === 'manage'">
            <div v-if="manageListLoading" class="empty-text">加载中...</div>
            <div v-else-if="filteredManageList.length === 0" class="empty-text">{{ canSeeAllFiles ? '暂无文件记录' : '您只能看到本专业的文件哦' }}</div>
            <div v-else class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>编号单位</th>
                    <th>编制人</th>
                    <th>编号类别</th>
                    <th>编号内容</th>
                    <th>编号时间</th>
                    <th>编号代码</th>
                    <th>PDF 文件</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in filteredManageList" :key="row.id">
                    <td>{{ row.bz }}</td>
                    <td>{{ row.xm }}</td>
                    <td>{{ row.fenlei }}</td>
                    <td>{{ row.neirong }}</td>
                    <td>{{ row.bhtime || '—' }}</td>
                    <td>
                      <span class="bianhao-code">{{ row.bianhao_code }}</span>
                      <button type="button" class="btn-copy-small" @click="copyText(row.bianhao_code)" title="复制">复制</button>
                    </td>
                    <td class="file-actions">
                      <button v-if="!row.has_pdf" type="button" class="btn-copy-small btn-upload" title="请上传终版PDF文件仅支持PDF" @click="triggerUpload('manage', row.bianhao_code)">请上传</button>
                      <template v-else>
                        <button type="button" class="btn-copy-small btn-delete" title="删除后可重新上传" @click="deletePdf('manage', row.bianhao_code)">删除</button>
                        <button type="button" class="btn-copy-small btn-preview" @click="openFile('manage', row.bianhao_code, 0)">预览</button>
                        <button type="button" class="btn-copy-small btn-download" @click="openFile('manage', row.bianhao_code, 1)">下载</button>
                      </template>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="manageTotal > 0" class="table-footer">
              共 {{ manageTotal }} 条，当前页 {{ filteredManageList.length }} 条
            </div>
          </template>
          <p v-else class="empty-text">{{ canSeeAllFiles ? '暂无文件记录' : '您只能看到本专业的文件哦' }}</p>
        </div>
      </div>
    </div>

    <input
      ref="pdfInputRef"
      type="file"
      accept=".pdf,application/pdf"
      class="hidden-input"
      @change="onPdfSelected"
    />

    <!-- 获取编号弹窗（技术文件：自动填充添加人/科室，分类与项目下拉） -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <h2>获取{{ currentTab === 'tech' ? '技术' : currentTab === 'jsgl' ? '技术管理' : '管理' }}文件编号</h2>
        <!-- 生成成功：显示编号 + 复制 -->
        <div v-if="generatedBianhao" class="result-block">
          <p class="result-label">编号已生成</p>
          <p class="result-bianhao">{{ generatedBianhao }}</p>
          <div class="result-actions">
            <button type="button" class="btn btn-copy" @click="copyBianhao">复制</button>
            <button type="button" class="btn-primary" @click="closeModal">关闭</button>
          </div>
        </div>
        <form v-else @submit.prevent="submitNumbering">
          <template v-if="currentTab === 'tech'">
            <div class="form-group">
              <label>添加人</label>
              <input v-model="form.xm" type="text" readonly class="readonly">
            </div>
            <div class="form-group">
              <label>所属科室</label>
              <input v-model="form.bz" type="text" readonly class="readonly">
            </div>
            <div class="form-group">
              <label>分类名称</label>
              <select v-model="form.fenlei" @change="onFenleiChange">
                <option value="">请选择分类</option>
                <option v-for="item in bianhaoFlList" :key="item.id" :value="item.flname">{{ item.flname }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>项目名称</label>
              <select v-model="form.xmname">
                <option value="">请选择项目</option>
                <option v-for="item in gzhList" :key="item.id" :value="item.gzhname">{{ item.gzhname }}</option>
              </select>
            </div>
          </template>
          <template v-else-if="currentTab === 'jsgl'">
            <div class="form-group">
              <label>添加人</label>
              <input v-model="form.xm" type="text" readonly class="readonly">
            </div>
            <div class="form-group">
              <label>所属科室</label>
              <input v-model="form.bz" type="text" readonly class="readonly">
            </div>
            <div class="form-group">
              <label>项目名称</label>
              <select v-model="form.xmname">
                <option value="">请选择项目</option>
                <option v-for="item in gzhList" :key="item.id" :value="item.gzhname">{{ item.gzhname }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>分类</label>
              <select v-model="form.fenlei">
                <option value="">请选择分类</option>
                <option v-for="item in jsglFenleiList" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </div>
          </template>
          <template v-else-if="currentTab === 'manage'">
            <div class="form-group">
              <label>添加人</label>
              <input v-model="form.xm" type="text" readonly class="readonly">
            </div>
            <div class="form-group">
              <label>所属科室</label>
              <input v-model="form.bz" type="text" readonly class="readonly">
            </div>
            <div class="form-group">
              <label>分类</label>
              <select v-model="form.fenlei">
                <option value="">请选择分类</option>
                <option v-for="item in glFenleiList" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>编制内容</label>
              <input v-model="form.neirong" type="text" placeholder="请输入编制内容">
            </div>
            <div class="form-group">
              <label>备注</label>
              <input v-model="form.content" type="text" placeholder="选填">
            </div>
          </template>
          <div v-if="currentTab !== 'manage'" class="form-group">
            <label>{{ currentTab === 'jsgl' ? '编制内容' : '文件名称' }}</label>
            <input v-model="form.neirong" type="text" :placeholder="currentTab === 'jsgl' ? '请输入编制内容' : '请输入文件名称'">
          </div>
          <div class="form-actions">
            <button type="button" @click="closeModal">取消</button>
            <button type="submit" class="btn-primary" :disabled="submitLoading">{{ submitLoading ? '生成中...' : '生成编号' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getGzhList, getBianhaoFlList, addBianhaoTech, getBianhaoTechList, getJsglFenlei, getBianhaogljsList, addBianhaogljs, getGlFenlei, getBianhaoglList, addBianhaogl, uploadNumberingPdf, deleteNumberingPdf, getNumberingFileUrl } from '@/api/fileNumbering'
import { getStatisticsPermission } from '@/api/attendance'

const router = useRouter()

const currentTab = ref('tech')
const showModal = ref(false)
const submitLoading = ref(false)
const generatedBianhao = ref('')
const techList = ref([])
const techListLoading = ref(false)
const techTotal = ref(0)
const searchKeyword = ref('')
const jsglList = ref([])
const jsglListLoading = ref(false)
const jsglTotal = ref(0)
const searchKeywordJsgl = ref('')
const jsglFenleiList = ref([])
const manageList = ref([])
const manageListLoading = ref(false)
const manageTotal = ref(0)
const searchKeywordManage = ref('')
const glFenleiList = ref([])
const pdfInputRef = ref(null)
const uploadTarget = ref({ type: '', code: '' })

const form = ref({
  xm: '',
  bz: '',
  fenlei: '',
  flbianma: '',
  xmname: '',
  neirong: '',
  content: ''
})

/** 统计权限 level：3=部长/副部长可看全部专业，1/2=仅本专业 */
const permissionLevel = ref(1)
const canSeeAllFiles = computed(() => permissionLevel.value === 3)

const bianhaoFlList = ref([])
const gzhList = ref([])

function getCurrentUser() {
  try {
    const raw = localStorage.getItem('userInfo')
    if (!raw) return null
    const u = JSON.parse(raw)
    return { name: (u.name || u.userName || '').trim() }
  } catch {
    return null
  }
}

async function loadUserDept() {
  const user = getCurrentUser()
  if (!user?.name) return
  form.value.xm = user.name
  try {
    const res = await getStatisticsPermission({ name: user.name })
    if (res && res.success !== false) {
      form.value.bz = (res.lsys || '').trim()
      permissionLevel.value = res.level ?? 1
    }
  } catch {
    // 已设置 xm，lsys 可能为空
  }
}

async function loadOptions() {
  const bz = (form.value.bz || '').trim()
  if (!bz) return
  try {
    const [flRes, gzhRes] = await Promise.all([
      getBianhaoFlList({ ssks: bz }),
      getGzhList({ ssks: bz })
    ])
    bianhaoFlList.value = (flRes.list || []).filter(Boolean)
    gzhList.value = (gzhRes.list || []).filter(Boolean)
  } catch {
    bianhaoFlList.value = []
    gzhList.value = []
  }
}

async function loadGzhOnly() {
  const bz = (form.value.bz || '').trim()
  if (!bz) return
  try {
    const res = await getGzhList({ ssks: bz })
    gzhList.value = (res.list || []).filter(Boolean)
  } catch {
    gzhList.value = []
  }
}

async function loadJsglFenlei() {
  try {
    const res = await getJsglFenlei()
    jsglFenleiList.value = (res.list || []).filter(Boolean)
  } catch {
    jsglFenleiList.value = []
  }
}

async function loadGlFenlei() {
  try {
    const res = await getGlFenlei()
    glFenleiList.value = (res.list || []).filter(Boolean)
  } catch {
    glFenleiList.value = []
  }
}

function onFenleiChange() {
  const flname = form.value.fenlei
  const item = bianhaoFlList.value.find((r) => r.flname === flname)
  form.value.flbianma = item ? (item.flbianma || '').trim() : ''
}

const filteredTechList = computed(() => {
  const kw = (searchKeyword.value || '').trim().toLowerCase()
  if (!kw) return techList.value
  return techList.value.filter(
    (r) =>
      (r.bianhao_code && r.bianhao_code.toLowerCase().includes(kw)) ||
      (r.neirong && r.neirong.toLowerCase().includes(kw)) ||
      (r.cpname && r.cpname.toLowerCase().includes(kw)) ||
      (r.bz && r.bz.toLowerCase().includes(kw)) ||
      (r.xm && r.xm.toLowerCase().includes(kw))
  )
})

const filteredJsglList = computed(() => {
  const kw = (searchKeywordJsgl.value || '').trim().toLowerCase()
  if (!kw) return jsglList.value
  return jsglList.value.filter(
    (r) =>
      (r.bianhao_code && r.bianhao_code.toLowerCase().includes(kw)) ||
      (r.neirong && r.neirong.toLowerCase().includes(kw)) ||
      (r.cpname && r.cpname.toLowerCase().includes(kw)) ||
      (r.bz && r.bz.toLowerCase().includes(kw)) ||
      (r.xm && r.xm.toLowerCase().includes(kw)) ||
      (r.fenleihao && r.fenleihao.toLowerCase().includes(kw))
  )
})

const filteredManageList = computed(() => {
  const kw = (searchKeywordManage.value || '').trim().toLowerCase()
  if (!kw) return manageList.value
  return manageList.value.filter(
    (r) =>
      (r.bianhao_code && r.bianhao_code.toLowerCase().includes(kw)) ||
      (r.neirong && r.neirong.toLowerCase().includes(kw)) ||
      (r.bz && r.bz.toLowerCase().includes(kw)) ||
      (r.xm && r.xm.toLowerCase().includes(kw)) ||
      (r.fenlei && r.fenlei.toLowerCase().includes(kw)) ||
      (r.content && r.content.toLowerCase().includes(kw))
  )
})

async function loadTechList() {
  techListLoading.value = true
  try {
    const params = { page: 1, page_size: 100 }
    if (!canSeeAllFiles.value && (form.value.bz || '').trim()) params.bz = form.value.bz.trim()
    const res = await getBianhaoTechList(params)
    techList.value = (res.list || []).filter(Boolean)
    techTotal.value = res.total ?? techList.value.length
  } catch {
    techList.value = []
    techTotal.value = 0
  } finally {
    techListLoading.value = false
  }
}

async function loadJsglList() {
  jsglListLoading.value = true
  try {
    const params = { page: 1, page_size: 100 }
    if (!canSeeAllFiles.value && (form.value.bz || '').trim()) params.bz = form.value.bz.trim()
    const res = await getBianhaogljsList(params)
    jsglList.value = (res.list || []).filter(Boolean)
    jsglTotal.value = res.total ?? jsglList.value.length
  } catch {
    jsglList.value = []
    jsglTotal.value = 0
  } finally {
    jsglListLoading.value = false
  }
}

async function loadManageList() {
  manageListLoading.value = true
  try {
    const params = { page: 1, page_size: 100 }
    if (!canSeeAllFiles.value && (form.value.bz || '').trim()) params.bz = form.value.bz.trim()
    const res = await getBianhaoglList(params)
    manageList.value = (res.list || []).filter(Boolean)
    manageTotal.value = res.total ?? manageList.value.length
  } catch {
    manageList.value = []
    manageTotal.value = 0
  } finally {
    manageListLoading.value = false
  }
}

function copyToClipboard(text) {
  if (!text) return false
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text).then(() => true).catch(() => false)
  }
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  textarea.setAttribute('readonly', '')
  document.body.appendChild(textarea)
  textarea.select()
  try {
    const ok = document.execCommand('copy')
    document.body.removeChild(textarea)
    return Promise.resolve(ok)
  } catch {
    document.body.removeChild(textarea)
    return Promise.resolve(false)
  }
}

async function copyText(text) {
  const ok = await copyToClipboard(text)
  alert(ok ? '已复制到剪贴板' : '复制失败，请手动复制')
}

function triggerUpload(type, code) {
  uploadTarget.value = { type, code }
  pdfInputRef.value?.click()
}

async function onPdfSelected(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file || uploadTarget.value.type === '') return
  const { type, code } = uploadTarget.value
  if (!code) return
  const fn = (file.name || '').toLowerCase()
  if (!fn.endsWith('.pdf')) {
    alert('请上传终版 PDF 文件，仅支持 PDF')
    return
  }
  try {
    await uploadNumberingPdf(type, code, file)
    alert('上传成功')
    if (type === 'tech') await loadTechList()
    else if (type === 'jsgl') await loadJsglList()
    else if (type === 'manage') await loadManageList()
  } catch (err) {
    alert(err.response?.data?.detail || err.message || '上传失败')
  }
}

function openFile(type, code, download) {
  const url = getNumberingFileUrl(type, code, download)
  window.open(url, '_blank', 'noopener')
}

async function deletePdf(type, code) {
  if (!confirm('确定删除该 PDF？删除后可重新上传。')) return
  try {
    await deleteNumberingPdf(type, code)
    alert('已删除')
    if (type === 'tech') await loadTechList()
    else if (type === 'jsgl') await loadJsglList()
    else if (type === 'manage') await loadManageList()
  } catch (err) {
    alert(err.response?.data?.detail || err.message || '删除失败')
  }
}

function closeModal() {
  showModal.value = false
  generatedBianhao.value = ''
}

async function copyBianhao() {
  const text = generatedBianhao.value
  const ok = await copyToClipboard(text)
  alert(ok ? '已复制到剪贴板' : '复制失败，请手动复制')
}

watch(currentTab, async (tab) => {
  if (tab === 'tech') {
    if (!(form.value.bz || '').trim()) await loadUserDept()
    await loadTechList()
  } else if (tab === 'jsgl') {
    if (!(form.value.bz || '').trim()) await loadUserDept()
    await loadJsglList()
  } else if (tab === 'manage') {
    if (!(form.value.bz || '').trim()) await loadUserDept()
    await loadManageList()
  }
})

onMounted(async () => {
  await loadJsglFenlei()
  await loadGlFenlei()
  if (currentTab.value === 'tech') {
    await loadUserDept()
    await loadTechList()
  } else if (currentTab.value === 'jsgl') {
    await loadUserDept()
    await loadJsglList()
  } else if (currentTab.value === 'manage') {
    await loadUserDept()
    await loadManageList()
  }
})

watch(showModal, async (visible) => {
  if (!visible) return
  generatedBianhao.value = ''
  form.value.xmname = ''
  form.value.neirong = ''
  form.value.content = ''
  if (currentTab.value === 'tech') {
    await loadUserDept()
    await loadOptions()
    form.value.fenlei = ''
    form.value.flbianma = ''
  } else if (currentTab.value === 'jsgl') {
    await loadUserDept()
    await loadGzhOnly()
    form.value.fenlei = ''
  } else if (currentTab.value === 'manage') {
    await loadUserDept()
    form.value.fenlei = ''
  }
})

async function submitNumbering() {
  const f = form.value
  if (currentTab.value === 'tech') {
    if (!f.neirong?.trim()) {
      alert('请输入文件名称')
      return
    }
    if (!f.fenlei || !f.xmname) {
      alert('请选择分类名称和项目名称')
      return
    }
    submitLoading.value = true
    try {
      const res = await addBianhaoTech({
        xm: f.xm,
        bz: f.bz,
        xmname: f.xmname,
        fenlei: f.fenlei,
        flbianma: f.flbianma || f.fenlei,
        neirong: f.neirong.trim(),
        content: ''
      })
      if (res.success) {
        generatedBianhao.value = res.bianhao || ''
        await loadTechList()
      } else {
        alert(res.message || '生成失败')
      }
    } catch (e) {
      alert(e.response?.data?.detail || e.message || '生成失败')
    } finally {
      submitLoading.value = false
    }
    return
  }
  if (currentTab.value === 'jsgl') {
    if (!f.neirong?.trim()) {
      alert('请输入编制内容')
      return
    }
    if (!f.fenlei || !f.xmname) {
      alert('请选择分类和项目名称')
      return
    }
    submitLoading.value = true
    try {
      const res = await addBianhaogljs({
        xm: f.xm,
        bz: f.bz,
        xmname: f.xmname,
        fenlei: f.fenlei,
        neirong: f.neirong.trim(),
        content: ''
      })
      if (res.success) {
        generatedBianhao.value = res.bianhao || ''
        await loadJsglList()
      } else {
        alert(res.message || '生成失败')
      }
    } catch (e) {
      alert(e.response?.data?.detail || e.message || '生成失败')
    } finally {
      submitLoading.value = false
    }
    return
  }
  if (currentTab.value === 'manage') {
    if (!f.neirong?.trim()) {
      alert('请输入编制内容')
      return
    }
    if (!f.fenlei) {
      alert('请选择分类')
      return
    }
    submitLoading.value = true
    try {
      const res = await addBianhaogl({
        xm: f.xm,
        bz: f.bz,
        fenlei: f.fenlei,
        neirong: f.neirong.trim(),
        content: (f.content || '').trim()
      })
      if (res.success) {
        generatedBianhao.value = res.bianhao || ''
        await loadManageList()
      } else {
        alert(res.message || '生成失败')
      }
    } catch (e) {
      alert(e.response?.data?.detail || e.message || '生成失败')
    } finally {
      submitLoading.value = false
    }
    return
  }
  alert('功能开发中')
  showModal.value = false
}
function goTechCategory() {
  router.push('/file/tech-category')
}

function goWorkNo() {
  router.push('/file/workno')
}
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

.tabs {
  display: flex;
  gap: var(--spacing-md);
  margin-top: var(--spacing-lg);
  margin-bottom: 0;
  padding: 0 var(--spacing-lg);
  background: var(--color-bg-container);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  border: 1px solid var(--color-border-lighter);
}

.page-container .tabs + .content {
  margin-top: 0;
}

.search-bar.mb-lg {
  margin-bottom: 0;
}

.tab-item {
  padding: var(--spacing-md) var(--spacing-xl);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  color: var(--color-text-secondary);
  font-weight: 500;
}

.tab-item.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

.search-bar {
  display: flex;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  border-radius: var(--radius-md);
}

.search-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
}

.card {
  background: white;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-lighter);
}

.card-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-lighter);
}

.card-body {
  padding: var(--spacing-lg);
}

.empty-text {
  text-align: center;
  color: var(--color-text-secondary);
  padding: var(--spacing-xxl) 0;
}

.table-wrap {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.data-table th,
.data-table td {
  padding: 10px 12px;
  border: 1px solid var(--color-border-lighter);
  text-align: left;
}

.data-table th {
  background: var(--color-bg-lighter, #f5f5f5);
  font-weight: 600;
}

.data-table tbody tr:hover {
  background: var(--color-bg-lighter, #fafafa);
}

.bianhao-code {
  font-family: var(--font-mono, monospace);
  letter-spacing: 0.02em;
  margin-right: 8px;
}

.btn-copy-small {
  padding: 2px 8px;
  font-size: 0.8rem;
  border-radius: 4px;
  border: 1px solid var(--color-border-base);
  background: #fff;
  cursor: pointer;
}

.btn-copy-small:hover {
  background: var(--color-bg-lighter, #f0f0f0);
}

.file-actions {
  white-space: nowrap;
}
.file-actions .btn-copy-small {
  margin-right: 4px;
}

/* 上传：主色 */
.btn-upload {
  color: var(--color-primary, #1677ff);
  border-color: var(--color-primary, #1677ff);
  background: rgba(22, 119, 255, 0.06);
}
.btn-upload:hover {
  background: rgba(22, 119, 255, 0.15);
}

/* 删除：红色 */
.btn-delete {
  color: var(--color-danger, #c00);
  border-color: var(--color-danger, #c00);
  background: rgba(204, 0, 0, 0.06);
}
.btn-delete:hover {
  background: rgba(204, 0, 0, 0.15);
}

/* 预览：蓝色/信息色 */
.btn-preview {
  color: #1890ff;
  border-color: #1890ff;
  background: rgba(24, 144, 255, 0.06);
}
.btn-preview:hover {
  background: rgba(24, 144, 255, 0.15);
}

/* 下载：绿色 */
.btn-download {
  color: #52c41a;
  border-color: #52c41a;
  background: rgba(82, 196, 26, 0.06);
}
.btn-download:hover {
  background: rgba(82, 196, 26, 0.15);
}

.hidden-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  overflow: hidden;
}

.table-footer {
  margin-top: var(--spacing-md);
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.mb-lg {
  margin-bottom: var(--spacing-lg);
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-content {
  background: white;
  padding: var(--spacing-xl);
  border-radius: var(--radius-md);
  width: 500px;
  max-width: 90%;
}

.form-group {
  margin-bottom: var(--spacing-lg);
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-xs);
  font-weight: 500;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
}

.form-group input.readonly {
  background: var(--color-bg-lighter, #f5f5f5);
  color: var(--color-text-secondary, #666);
  cursor: default;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
  margin-top: var(--spacing-xl);
}

.result-block {
  padding: var(--spacing-lg) 0;
}
.result-label {
  margin-bottom: var(--spacing-xs);
  color: var(--color-text-secondary);
  font-size: 0.9em;
}
.result-bianhao {
  font-size: 1.25rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  margin-bottom: var(--spacing-xl);
  word-break: break-all;
}
.result-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
}
.btn-copy {
  background: var(--color-bg-lighter, #f0f0f0);
  border-color: var(--color-border-base);
}
.btn-copy:hover {
  background: var(--color-border-lighter, #e8e8e8);
}

button {
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-base);
  cursor: pointer;
  background: white;
}

.btn-primary {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}
</style>
