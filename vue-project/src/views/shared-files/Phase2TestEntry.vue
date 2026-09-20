<template>
  <div class="oo-redirect">
    <p v-if="errorMessage" class="oo-error">{{ errorMessage }}</p>
    <p v-else>正在打开 Phase2 测试文档…</p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getPhase2TestInfo } from '@/api/sharedFiles'

const router = useRouter()
const errorMessage = ref('')

onMounted(async () => {
  try {
    const res = await getPhase2TestInfo()
    const id = res && res.data && res.data.id
    if (!id) throw new Error('未找到 test.xlsx')
    router.replace(`/shared-files/edit/${id}`)
  } catch (e) {
    errorMessage.value = (e && e.message) || '打开失败'
  }
})
</script>

<style scoped>
.oo-redirect {
  padding: 24px;
  color: #374151;
}
.oo-error {
  color: #b91c1c;
}
</style>
