<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">工艺技术问题手册</h1>
          <p class="header-subtitle">记录并管理工艺技术问题、原因分析与解决措施</p>
        </div>
        <div class="header-actions">
          <button class="btn btn-primary" @click="goCreate">+ 新建记录</button>
        </div>
      </div>
    </div>

    <div class="content mt-xl">
      <!-- 搜索栏 -->
      <div class="search-bar card mb-lg">
        <select v-model="filterCategory" class="search-select">
          <option value="">全部分类</option>
          <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
        </select>
        <input
          v-model="searchKeyword"
          type="text"
          placeholder="搜索主题、问题描述、原因分析、措施..."
          class="search-input"
          @keyup.enter="doSearch"
        >
        <button type="button" class="btn btn-primary" @click="doSearch">查询</button>
        <button type="button" class="btn btn-default" @click="resetSearch">重置</button>
      </div>

      <!-- 列表 -->
      <div class="card">
        <div class="card-header">
          <h3>问题列表</h3>
          <span v-if="total > 0" class="card-header-extra">共 {{ total }} 条</span>
        </div>
        <div class="card-body">
          <div v-if="loading" class="empty-text">加载中...</div>
          <div v-else-if="list.length === 0" class="empty-text">暂无记录</div>
          <div v-else class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th style="width:60px">序号</th>
                  <th style="width:100px">分类</th>
                  <th style="width:110px">所属专业</th>
                  <th>主题</th>
                  <th style="width:90px">记录人</th>
                  <th style="width:100px">记录时间</th>
                  <th style="width:80px">有措施</th>
                  <th style="width:100px">创建时间</th>
                  <th style="width:150px">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in list" :key="row.id">
                  <td>{{ (page - 1) * pageSize + idx + 1 }}</td>
                  <td><span class="tag tag-info">{{ row.category || '—' }}</span></td>
                  <td>{{ row.department || '—' }}</td>
                  <td class="td-title" :title="row.title">{{ row.title || '—' }}</td>
                  <td>{{ row.recorder || '—' }}</td>
                  <td>{{ row.record_time || '—' }}</td>
                  <td>
                    <span :class="row.measures ? 'tag tag-success' : 'tag tag-warning'">
                      {{ row.measures ? '已填' : '待补' }}
                    </span>
                  </td>
                  <td>{{ (row.created_at || '').slice(0, 10) }}</td>
                  <td class="file-actions">
                    <button type="button" class="btn-copy-small btn-preview" @click="goDetail(row.id)">查看</button>
                    <button type="button" class="btn-copy-small btn-edit" @click="goEdit(row.id)">编辑</button>
                    <button type="button" class="btn-copy-small btn-delete" @click="doDelete(row)">删除</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="total > 0" class="table-footer">
            共 {{ total }} 条，当前页 {{ list.length }} 条
          </div>
          <!-- 分页 -->
          <div v-if="totalPages > 1" class="pagination-bar">
            <button class="btn btn-sm" :disabled="page <= 1" @click="changePage(page - 1)">上一页</button>
            <span class="page-info">{{ page }} / {{ totalPages }}</span>
            <button class="btn btn-sm" :disabled="page >= totalPages" @click="changePage(page + 1)">下一页</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="showDetail" class="modal-overlay preview-overlay" @click.self="showDetail = false">
      <div class="detail-modal">
        <div class="detail-header">
          <span class="detail-header-title">问题详情</span>
          <button type="button" class="btn-close" @click="showDetail = false">×</button>
        </div>
        <div class="detail-body" v-if="detailData">
          <div class="detail-meta">
            <span class="tag tag-info">{{ detailData.category }}</span>
            <span v-if="detailData.department" class="detail-meta-item">所属专业：{{ detailData.department }}</span>
            <span class="detail-meta-item">记录人：{{ detailData.recorder }}</span>
            <span class="detail-meta-item">记录时间：{{ detailData.record_time }}</span>
          </div>
          <h3 class="detail-title">{{ detailData.title }}</h3>

          <div class="detail-section">
            <h4>问题描述</h4>
            <p class="detail-text">{{ detailData.problem_desc || '—' }}</p>
            <div v-if="detailData.problem_images && detailData.problem_images.length" class="detail-images">
              <img
                v-for="(img, i) in detailData.problem_images"
                :key="'p' + i"
                :src="getImageUrl(img)"
                class="detail-img"
                @click="previewImage(getImageUrl(img))"
              >
            </div>
          </div>

          <div class="detail-section">
            <h4>原因分析</h4>
            <p class="detail-text">{{ detailData.cause_analysis || '—' }}</p>
            <div v-if="detailData.cause_images && detailData.cause_images.length" class="detail-images">
              <img
                v-for="(img, i) in detailData.cause_images"
                :key="'c' + i"
                :src="getImageUrl(img)"
                class="detail-img"
                @click="previewImage(getImageUrl(img))"
              >
            </div>
          </div>

          <div class="detail-section">
            <h4>采取措施及效果</h4>
            <p class="detail-text" v-if="detailData.measures">{{ detailData.measures }}</p>
            <p class="detail-text text-tertiary" v-else>暂未填写</p>
            <div v-if="detailData.measures_images && detailData.measures_images.length" class="detail-images">
              <img
                v-for="(img, i) in detailData.measures_images"
                :key="'m' + i"
                :src="getImageUrl(img)"
                class="detail-img"
                @click="previewImage(getImageUrl(img))"
              >
            </div>
          </div>

          <div class="detail-footer-actions">
            <button class="btn btn-primary" @click="showDetail = false; goEdit(detailData.id)">编辑</button>
            <button class="btn btn-default" @click="showDetail = false">关闭</button>
          </div>
        </div>
        <div v-else class="empty-text">加载中...</div>
      </div>
    </div>

    <!-- 图片预览大图 -->
    <div v-if="previewImgSrc" class="modal-overlay img-preview-overlay" @click.self="previewImgSrc = ''">
      <div class="img-preview-wrap">
        <button class="btn-close img-preview-close" @click="previewImgSrc = ''">×</button>
        <img :src="previewImgSrc" class="img-preview-full">
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getTechProblemList, getTechProblemDetail, deleteTechProblem, getTechProblemCategories, getTechProblemImageUrl } from '@/api/techProblem'

const router = useRouter()

const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const searchKeyword = ref('')
const filterCategory = ref('')
const categories = ref([])

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

const showDetail = ref(false)
const detailData = ref(null)
const previewImgSrc = ref('')

function getImageUrl(filename) {
  return getTechProblemImageUrl(filename)
}

function previewImage(src) {
  previewImgSrc.value = src
}

async function loadList() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (searchKeyword.value.trim()) params.keyword = searchKeyword.value.trim()
    if (filterCategory.value) params.category = filterCategory.value
    const res = await getTechProblemList(params)
    list.value = res.list || []
    total.value = res.total ?? 0
  } catch {
    list.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function loadCategories() {
  try {
    const res = await getTechProblemCategories()
    categories.value = res.categories || []
  } catch { /* ignore */ }
}

function doSearch() {
  page.value = 1
  loadList()
}

function resetSearch() {
  searchKeyword.value = ''
  filterCategory.value = ''
  page.value = 1
  loadList()
}

function changePage(p) {
  page.value = p
  loadList()
}

function goCreate() {
  router.push('/file/tech-problem/create')
}

function goEdit(id) {
  router.push(`/file/tech-problem/edit/${id}`)
}

async function goDetail(id) {
  showDetail.value = true
  detailData.value = null
  try {
    const res = await getTechProblemDetail(id)
    detailData.value = res
  } catch (e) {
    alert('加载详情失败: ' + (e.message || e))
    showDetail.value = false
  }
}

async function doDelete(row) {
  if (!confirm(`确定删除「${row.title}」？删除后不可恢复。`)) return
  try {
    await deleteTechProblem(row.id)
    loadList()
  } catch (e) {
    alert('删除失败: ' + (e.message || e))
  }
}

onMounted(() => {
  loadList()
  loadCategories()
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

.search-bar {
  display: flex;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  border-radius: var(--radius-md);
  flex-wrap: wrap;
  align-items: center;
}

.search-input {
  flex: 1;
  min-width: 200px;
  padding: 8px 12px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-base);
  outline: none;
  transition: border-color var(--transition-base) var(--transition-ease);
}
.search-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-lightest);
}

.search-select {
  padding: 8px 12px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-base);
  outline: none;
  background: var(--color-bg-container);
  max-width: 160px;
  transition: border-color var(--transition-base) var(--transition-ease);
}
.search-select:focus {
  border-color: var(--color-primary);
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
.card-header-extra {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
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
  font-size: var(--font-size-sm);
}
.data-table th,
.data-table td {
  padding: 10px 12px;
  border: 1px solid var(--color-border-lighter);
  text-align: left;
}
.data-table th {
  background: var(--color-bg-spotlight);
  font-weight: var(--font-weight-semibold);
}

.td-title {
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-actions {
  white-space: nowrap;
}
.file-actions .btn-copy-small {
  margin-right: 4px;
}

.btn-copy-small {
  padding: 2px 8px;
  font-size: var(--font-size-xs);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-base);
  background: var(--color-bg-container);
  cursor: pointer;
  transition: all var(--transition-base) var(--transition-ease);
}

.btn-preview {
  color: var(--color-primary);
  border-color: var(--color-primary);
  background: var(--color-primary-lightest);
}
.btn-preview:hover {
  background: var(--color-primary-lighter);
  color: #fff;
}
.btn-edit {
  color: var(--color-info);
  border-color: var(--color-info);
  background: var(--color-info-bg);
}
.btn-edit:hover {
  background: var(--color-info-light);
  color: #fff;
}
.btn-delete {
  color: var(--color-error);
  border-color: var(--color-error);
  background: var(--color-error-bg);
}
.btn-delete:hover {
  background: var(--color-error-light);
  color: #fff;
}

.table-footer {
  margin-top: var(--spacing-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  padding: var(--spacing-base) 0 var(--spacing-xs);
}
.page-info {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
}

/* 详情弹窗 */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: var(--color-bg-mask);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-index-modal);
}
.preview-overlay {
  z-index: var(--z-index-modal);
}

.detail-modal {
  background: var(--color-bg-container);
  border-radius: var(--radius-md);
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: var(--shadow-elevated);
}
.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
}
.detail-header-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
}
.btn-close {
  width: 32px;
  height: 32px;
  padding: 0;
  font-size: 24px;
  line-height: 1;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
}
.btn-close:hover {
  color: var(--color-text-primary);
}

.detail-body {
  padding: var(--spacing-lg) var(--spacing-xl) var(--spacing-xl);
}
.detail-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-base);
  margin-bottom: var(--spacing-md);
  flex-wrap: wrap;
}
.detail-meta-item {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
.detail-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  margin: 0 0 var(--spacing-lg);
  color: var(--color-text-primary);
}
.detail-section {
  margin-bottom: var(--spacing-xl);
}
.detail-section h4 {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-sm);
  padding-left: 10px;
  border-left: 3px solid var(--color-primary);
}
.detail-text {
  font-size: var(--font-size-base);
  line-height: var(--line-height-lg);
  color: var(--color-text-secondary);
  white-space: pre-wrap;
  margin: 0;
}
.detail-images {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
}
.detail-img {
  width: 120px;
  height: 90px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  cursor: pointer;
  border: 1px solid var(--color-border-lighter);
  transition: transform var(--transition-base), box-shadow var(--transition-base);
}
.detail-img:hover {
  transform: scale(1.05);
  box-shadow: var(--shadow-card-hover);
}
.detail-footer-actions {
  display: flex;
  gap: var(--spacing-md);
  justify-content: flex-end;
  padding-top: var(--spacing-base);
  border-top: 1px solid var(--color-border-lighter);
}

/* 图片大图预览 */
.img-preview-overlay {
  z-index: calc(var(--z-index-modal) + 10);
}
.img-preview-wrap {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
}
.img-preview-close {
  position: absolute;
  top: -12px;
  right: -12px;
  z-index: 1;
  background: var(--color-bg-container);
  border-radius: var(--radius-circle);
  width: 32px;
  height: 32px;
  font-size: 18px;
  box-shadow: var(--shadow-popup);
}
.img-preview-full {
  max-width: 90vw;
  max-height: 85vh;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-elevated);
}
</style>
