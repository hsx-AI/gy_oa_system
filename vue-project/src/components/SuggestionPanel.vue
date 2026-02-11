<template>
  <div class="suggestion-panel">
    <div class="panel-header">
      <div class="header-left">
        <svg class="header-icon" :class="`icon-${type}`" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path v-if="type === 'warning'" d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3z" />
          <circle v-else-if="type === 'info'" cx="12" cy="12" r="10" />
          <circle v-else cx="12" cy="12" r="10" />
          <line v-if="type === 'warning'" x1="12" y1="9" x2="12" y2="13" />
          <line v-if="type === 'warning'" x1="12" y1="17" x2="12.01" y2="17" />
          <path v-if="type === 'info'" d="M12 16v-4" />
          <path v-if="type === 'info'" d="M12 8h.01" />
        </svg>
        <h3 class="panel-title">{{ title }}</h3>
        <span v-if="badge" class="panel-badge" :class="`badge-${type}`">
          {{ badge }}
        </span>
      </div>
      <slot name="actions">
        <button v-if="dismissable" class="btn-text btn-sm" @click="handleDismiss">
          <svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </slot>
    </div>
    <div class="panel-content">
      <slot></slot>
    </div>
    <div v-if="$slots.footer" class="panel-footer">
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<script setup>
import { defineEmits } from 'vue'

defineProps({
  title: {
    type: String,
    required: true
  },
  type: {
    type: String,
    default: 'info',
    validator: (value) => ['info', 'warning', 'error', 'success'].includes(value)
  },
  badge: {
    type: [String, Number],
    default: null
  },
  dismissable: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['dismiss'])

const handleDismiss = () => {
  emit('dismiss')
}
</script>

<style scoped>
.suggestion-panel {
  background: var(--color-bg-container);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-lighter);
  overflow: hidden;
  transition: all var(--transition-base) var(--transition-ease);
}

.suggestion-panel:hover {
  box-shadow: var(--shadow-card);
}

.panel-header {
  padding: var(--spacing-base) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-lighter);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--color-bg-spotlight);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.header-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.icon-warning {
  color: var(--color-warning);
}

.icon-info {
  color: var(--color-info);
}

.icon-error {
  color: var(--color-error);
}

.icon-success {
  color: var(--color-success);
}

.panel-title {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.panel-badge {
  font-size: var(--font-size-xs);
  padding: 2px var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-weight: var(--font-weight-medium);
  line-height: 1;
}

.badge-warning {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.badge-info {
  background: var(--color-info-bg);
  color: var(--color-info);
}

.badge-error {
  background: var(--color-error-bg);
  color: var(--color-error);
}

.badge-success {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.panel-content {
  padding: var(--spacing-lg);
}

.panel-footer {
  padding: var(--spacing-base) var(--spacing-lg);
  border-top: 1px solid var(--color-border-lighter);
  background: var(--color-bg-spotlight);
}

.icon-sm {
  width: 16px;
  height: 16px;
}

@media (max-width: 768px) {
  .panel-header {
    padding: var(--spacing-sm) var(--spacing-base);
  }
  
  .panel-content {
    padding: var(--spacing-base);
  }
  
  .panel-footer {
    padding: var(--spacing-sm) var(--spacing-base);
  }
}
</style>
