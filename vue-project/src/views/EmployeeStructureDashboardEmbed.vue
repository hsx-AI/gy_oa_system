<template>
  <div class="personnel-archive-embed">
    <div class="personnel-archive-embed__toolbar">
      <button type="button" class="personnel-archive-embed__back" @click="goBack">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <polyline points="15 18 9 12 15 6" />
        </svg>
        <span>{{ MSG.back }}</span>
      </button>
    </div>
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
import { useRouter } from 'vue-router'
import { getPersonnelPageUrl } from '@/api/sso'

const router = useRouter()

const MSG = {
  back: '\u8fd4\u56de\u7ba1\u7406\u9a7e\u9a76\u8231',
  loading: '\u6b63\u5728\u52a0\u8f7d\u5458\u5de5\u4fe1\u606f\u9a7e\u9a76\u8231\u2026',
  retry: '\u91cd\u8bd5',
  title: '\u5458\u5de5\u4fe1\u606f\u9a7e\u9a76\u8231',
  linkFailed: '\u83b7\u53d6\u5458\u5de5\u4fe1\u606f\u9a7e\u9a76\u8231\u94fe\u63a5\u5931\u8d25\uff0c\u8bf7\u8054\u7cfb\u7ba1\u7406\u5458',
  loadFailed: '\u52a0\u8f7d\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5',
}

const loading = ref(true)
const error = ref('')
const embedUrl = ref('')

function goBack() {
  router.push('/leader-dashboard')
}

async function loadEmbed() {
  loading.value = true
  error.value = ''
  embedUrl.value = ''

  try {
    const res = await getPersonnelPageUrl('/public-dashboard')
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

.personnel-archive-embed__toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding: 10px 16px 10px 0;
  border-bottom: 1px solid var(--color-border-lighter, #e5e7eb);
  background: var(--color-bg-container);
}

.personnel-archive-embed__back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--color-border-base, #d1d5db);
  border-radius: var(--radius-sm, 6px);
  background: var(--color-bg-container, #fff);
  color: var(--color-text-primary, #1f2937);
  font-size: 14px;
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s;
}

.personnel-archive-embed__back svg {
  width: 16px;
  height: 16px;
}

.personnel-archive-embed__back:hover {
  border-color: var(--color-primary, #2563eb);
  color: var(--color-primary, #2563eb);
}

.personnel-archive-embed__frame {
  flex: 1;
  width: 100%;
  min-height: calc(100vh - var(--header-height, 64px) - 49px);
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
  min-height: calc(100vh - var(--header-height, 64px) - 49px);
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
