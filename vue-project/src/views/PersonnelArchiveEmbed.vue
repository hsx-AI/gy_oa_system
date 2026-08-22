<template>
  <div class="personnel-archive-embed">
    <div v-if="loading" class="personnel-archive-embed__status">
      <p>{{ MSG.loading }}</p>
    </div>
    <div v-else-if="error" class="personnel-archive-embed__status personnel-archive-embed__status--error">
      <p>{{ error }}</p>
      <button type="button" class="personnel-archive-embed__retry" @click="loadEmbed">{{ MSG.retry }}</button>
    </div>
    <iframe
      v-show="!loading && !error && embedUrl"
      class="personnel-archive-embed__frame"
      :src="embedUrl"
      :title="MSG.title"
    />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getSSOLink } from '@/api/sso'

const MSG = {
  loading: '\u6b63\u5728\u52a0\u8f7d\u4eba\u4e8b\u6863\u6848\u2026',
  retry: '\u91cd\u8bd5',
  title: '\u4eba\u4e8b\u6863\u6848',
  loginRequired: '\u8bf7\u5148\u767b\u5f55\u96c6\u6210\u529e\u516c\u5e73\u53f0',
  linkFailed: '\u83b7\u53d6\u4eba\u4e8b\u6863\u6848\u94fe\u63a5\u5931\u8d25\uff0c\u8bf7\u8054\u7cfb\u7ba1\u7406\u5458',
  loadFailed: '\u52a0\u8f7d\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5',
}

const loading = ref(true)
const error = ref('')
const embedUrl = ref('')

function readUserName() {
  try {
    const raw = localStorage.getItem('userInfo')
    if (!raw) return ''
    const info = JSON.parse(raw)
    return (info?.name || info?.userName || '').trim()
  } catch {
    return ''
  }
}

async function loadEmbed() {
  const name = readUserName()
  if (!name) {
    loading.value = false
    error.value = MSG.loginRequired
    embedUrl.value = ''
    return
  }

  loading.value = true
  error.value = ''
  embedUrl.value = ''

  try {
    const res = await getSSOLink('B', name)
    if (res?.success && res?.url) {
      embedUrl.value = res.url
    } else {
      error.value = res?.detail || MSG.linkFailed
    }
  } catch (e) {
    const detail = e?.response?.data?.detail
    error.value = typeof detail === 'string'
      ? detail
      : (Array.isArray(detail) ? detail.join(' ') : (e?.message || MSG.loadFailed))
  } finally {
    loading.value = false
  }
}

onMounted(loadEmbed)
</script>

<style scoped>
.personnel-archive-embed {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: calc(100vh - var(--header-height, 64px));
  background: var(--color-bg-container);
}

.personnel-archive-embed__frame {
  flex: 1;
  width: 100%;
  min-height: calc(100vh - var(--header-height, 64px));
  border: 0;
  display: block;
  background: #fff;
}

.personnel-archive-embed__status {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--color-text-secondary);
  min-height: calc(100vh - var(--header-height, 64px));
}

.personnel-archive-embed__status--error {
  color: var(--color-danger, #dc2626);
}

.personnel-archive-embed__retry {
  padding: 8px 16px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm, 6px);
  background: var(--color-bg-container);
  color: var(--color-text-primary);
  cursor: pointer;
}

.personnel-archive-embed__retry:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
</style>
