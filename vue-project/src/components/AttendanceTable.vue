<template>
  <div class="attendance-table-wrapper">
    <div class="table-header" v-if="showHeader">
      <h3 class="table-title">{{ title }}</h3>
      <div class="table-actions">
        <slot name="actions"></slot>
      </div>
    </div>

    <div class="table-container">
      <table class="attendance-table">
        <thead>
          <tr>
            <th v-for="column in columns" :key="column.key" :class="column.className">
              {{ column.title }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td :colspan="columns.length" class="loading-cell">
              <div class="loading-container">
                <span class="loading"></span>
                <span class="loading-text">加载中...</span>
              </div>
            </td>
          </tr>
          <tr v-else-if="data.length === 0">
            <td :colspan="columns.length" class="empty-cell">
              <div class="empty-container">
                <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <span class="empty-text">暂无数据</span>
              </div>
            </td>
          </tr>
          <tr v-else v-for="(row, index) in data" :key="index" @click="handleRowClick(row)">
            <td v-for="column in columns" :key="column.key" :class="column.className">
              <slot :name="'column-' + column.key" :row="row" :value="row[column.key]">
                {{ row[column.key] }}
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="table-pagination" v-if="pagination">
      <div class="pagination-info">
        显示第 {{ (pagination.current - 1) * pagination.pageSize + 1 }}-{{ Math.min(pagination.current * pagination.pageSize, pagination.total) }} 条，
        共 {{ pagination.total }} 条
      </div>
      <div class="pagination-controls">
        <button 
          class="btn-text btn-sm" 
          :disabled="pagination.current === 1"
          @click="handlePageChange(pagination.current - 1)"
        >
          上一页
        </button>
        <div class="pagination-pages">
          <button 
            v-for="page in visiblePages" 
            :key="page"
            class="pagination-page"
            :class="{ active: page === pagination.current }"
            @click="handlePageChange(page)"
          >
            {{ page }}
          </button>
        </div>
        <button 
          class="btn-text btn-sm"
          :disabled="pagination.current === totalPages"
          @click="handlePageChange(pagination.current + 1)"
        >
          下一页
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: ''
  },
  showHeader: {
    type: Boolean,
    default: true
  },
  columns: {
    type: Array,
    required: true
    // 格式: [{ key: 'date', title: '日期', className: '' }]
  },
  data: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  pagination: {
    type: Object,
    default: null
    // 格式: { current: 1, pageSize: 10, total: 100 }
  }
})

const emit = defineEmits(['row-click', 'page-change'])

const totalPages = computed(() => {
  if (!props.pagination) return 0
  return Math.ceil(props.pagination.total / props.pagination.pageSize)
})

const visiblePages = computed(() => {
  if (!props.pagination) return []
  
  const current = props.pagination.current
  const total = totalPages.value
  const pages = []
  
  if (total <= 7) {
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
  } else {
    if (current <= 4) {
      for (let i = 1; i <= 5; i++) {
        pages.push(i)
      }
      pages.push('...')
      pages.push(total)
    } else if (current >= total - 3) {
      pages.push(1)
      pages.push('...')
      for (let i = total - 4; i <= total; i++) {
        pages.push(i)
      }
    } else {
      pages.push(1)
      pages.push('...')
      for (let i = current - 1; i <= current + 1; i++) {
        pages.push(i)
      }
      pages.push('...')
      pages.push(total)
    }
  }
  
  return pages
})

const handleRowClick = (row) => {
  emit('row-click', row)
}

const handlePageChange = (page) => {
  if (page !== '...' && page >= 1 && page <= totalPages.value) {
    emit('page-change', page)
  }
}
</script>

<style scoped>
.attendance-table-wrapper {
  background: var(--color-bg-container);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-lighter);
  overflow: hidden;
}

.table-header {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
  background: var(--color-bg-spotlight);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.table-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.table-actions {
  display: flex;
  gap: var(--spacing-sm);
}

.table-container {
  overflow-x: auto;
}

.attendance-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}

.attendance-table thead {
  background: var(--color-bg-spotlight);
}

.attendance-table th {
  padding: var(--spacing-base);
  text-align: left;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border-lighter);
  white-space: nowrap;
}

.attendance-table td {
  padding: var(--spacing-base);
  border-bottom: 1px solid var(--color-border-lighter);
  color: var(--color-text-primary);
}

.attendance-table tbody tr {
  transition: background-color var(--transition-base) var(--transition-ease);
  cursor: pointer;
}

.attendance-table tbody tr:hover {
  background: var(--color-bg-spotlight);
}

.loading-cell,
.empty-cell {
  text-align: center;
  padding: var(--spacing-xxxl) var(--spacing-xl);
}

.loading-container,
.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-base);
}

.loading-text,
.empty-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.empty-icon {
  width: 48px;
  height: 48px;
  color: var(--color-text-quaternary);
}

.table-pagination {
  padding: var(--spacing-base) var(--spacing-xl);
  border-top: 1px solid var(--color-border-lighter);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--color-bg-container);
}

.pagination-info {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.pagination-pages {
  display: flex;
  gap: var(--spacing-xs);
}

.pagination-page {
  min-width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 var(--spacing-xs);
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  background: var(--color-bg-container);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: all var(--transition-base) var(--transition-ease);
  font-size: var(--font-size-sm);
}

.pagination-page:hover:not(.active) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.pagination-page.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: white;
}

@media (max-width: 768px) {
  .table-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-base);
  }
  
  .table-pagination {
    flex-direction: column;
    gap: var(--spacing-base);
  }
}
</style>
