<template>
  <div class="stat-card card">
    <div class="stat-icon-wrapper" :style="{ background: iconBg }">
      <svg class="stat-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path :d="iconPath" />
      </svg>
    </div>
    <div class="stat-content">
      <div class="stat-label">{{ label }}</div>
      <div class="stat-value">{{ value }}</div>
      <div v-if="trend" class="stat-trend" :class="`trend-${trend.type}`">
        <span class="trend-icon">{{ trend.type === 'up' ? '↑' : '↓' }}</span>
        <span class="trend-value">{{ trend.value }}</span>
        <span class="trend-label">{{ trend.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  label: {
    type: String,
    required: true
  },
  value: {
    type: [String, Number],
    required: true
  },
  iconPath: {
    type: String,
    default: 'M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6'
  },
  iconBg: {
    type: String,
    default: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
  },
  trend: {
    type: Object,
    default: null
    // 格式: { type: 'up' | 'down', value: string, label: string }
  }
})
</script>

<style scoped>
.stat-card {
  padding: var(--spacing-xl);
  display: flex;
  gap: var(--spacing-base);
  border: 1px solid var(--color-border-lighter);
  transition: all var(--transition-base) var(--transition-ease);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-card-hover);
}

.stat-icon-wrapper {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon-svg {
  width: 32px;
  height: 32px;
  color: white;
}

.stat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.stat-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-xs);
}

.stat-value {
  font-size: var(--font-size-xxxl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  line-height: 1.2;
  margin-bottom: var(--spacing-sm);
}

.stat-trend {
  font-size: var(--font-size-sm);
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.trend-icon {
  font-weight: var(--font-weight-bold);
}

.trend-up {
  color: var(--color-success);
}

.trend-down {
  color: var(--color-error);
}

.trend-label {
  color: var(--color-text-tertiary);
}

@media (max-width: 768px) {
  .stat-card {
    padding: var(--spacing-base);
  }
  
  .stat-icon-wrapper {
    width: 48px;
    height: 48px;
  }
  
  .stat-icon-svg {
    width: 24px;
    height: 24px;
  }
  
  .stat-value {
    font-size: var(--font-size-xxl);
  }
}
</style>
