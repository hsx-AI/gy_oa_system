<template>
  <div class="inbox-config-body">
    <div class="config-hint">
      <p v-if="compact" class="config-hint-compact">
        若邮件无法同步或授权码已过期，请重新填写 IMAP 授权码（非登录密码）并保存。
        <span class="config-hint-status" :class="configured ? 'ok' : 'warn'">
          {{ configured ? '当前已配置' : '当前未配置' }}
        </span>
      </p>
      <template v-else>
        <p>IMAP 服务器：<code>{{ imapServer }}:{{ imapPort }}</code>（SSL）</p>
        <p>
          同步范围：智能整理公用邮箱收件箱中的最新
          <code>50</code>
          封邮件；自动拉取间隔：约
          <code>{{ pollIntervalSeconds }}</code>
          秒。
        </p>
      </template>
    </div>
    <div v-if="!compact" class="config-guide">
      <h4 class="config-guide-title">使用步骤</h4>
      <ol class="config-guide-steps">
        <li>填写经理层公用邮箱地址和 IMAP 授权码，点击“保存配置”</li>
        <li>系统自动同步收件箱中的全部新邮件，无需人工标记红旗</li>
        <li>AI 会筛选并提取其中的待办任务，展示在经理层“AI 待办看板”中</li>
      </ol>
    </div>
    <div class="config-form">
      <div class="form-row">
        <label>企业邮箱地址</label>
        <input
          :value="emailAddress"
          type="text"
          placeholder="如 yourname@hec-china.com"
          @input="$emit('update:emailAddress', $event.target.value)"
        />
      </div>
      <div class="form-row">
        <label>IMAP 授权码</label>
        <input
          :value="emailAuthCode"
          type="password"
          :placeholder="configured ? '填写新的 IMAP 授权码以更新' : '企业邮箱 IMAP 授权码（非登录密码）'"
          @input="$emit('update:emailAuthCode', $event.target.value)"
        />
      </div>
      <div class="form-row form-row-actions">
        <button
          type="button"
          class="btn btn-primary btn-sm"
          :disabled="saving"
          @click="$emit('save')"
        >
          {{ saving ? '保存中…' : '保存配置' }}
        </button>
        <span v-if="message" class="config-msg" :class="messageType">{{ message }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  compact: { type: Boolean, default: false },
  configured: { type: Boolean, default: false },
  imapServer: { type: String, default: '' },
  imapPort: { type: [String, Number], default: '' },
  pollIntervalSeconds: { type: [String, Number], default: '' },
  emailAddress: { type: String, default: '' },
  emailAuthCode: { type: String, default: '' },
  saving: { type: Boolean, default: false },
  message: { type: String, default: '' },
  messageType: { type: String, default: '' },
})

defineEmits(['update:emailAddress', 'update:emailAuthCode', 'save'])
</script>

<style scoped>
.config-hint {
  background: #f8fafc;
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 6px;
  padding: var(--spacing-sm, 8px) var(--spacing-md, 12px);
  margin-bottom: var(--spacing-md, 12px);
  font-size: 0.85rem;
  color: var(--color-text-secondary, #6b7280);
}
.config-hint p { margin: 4px 0; }
.config-hint-compact {
  margin: 0;
  line-height: 1.6;
}
.config-hint-status {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
}
.config-hint-status.ok {
  background: #dcfce7;
  color: #166534;
}
.config-hint-status.warn {
  background: #fef3c7;
  color: #92400e;
}
.config-hint code {
  background: #e2e8f0;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 0.82rem;
}
.config-guide {
  background: linear-gradient(135deg, #fff7ed 0%, #fffbeb 100%);
  border: 1px dashed #f59e0b;
  border-radius: 8px;
  padding: var(--spacing-sm, 8px) var(--spacing-md, 12px);
  margin-bottom: var(--spacing-md, 12px);
}
.config-guide-title {
  margin: 0 0 6px 0;
  font-size: 0.88rem;
  font-weight: 600;
  color: #92400e;
}
.config-guide-steps {
  margin: 0;
  padding-left: 1.4em;
  font-size: 0.85rem;
  color: #78350f;
  line-height: 1.8;
  list-style: decimal;
}
.config-guide-steps strong {
  color: #dc2626;
}
.config-form .form-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-md, 12px);
  margin-bottom: var(--spacing-md, 12px);
}
.config-form .form-row-actions {
  flex-wrap: wrap;
}
.config-form label {
  width: 100px;
  flex-shrink: 0;
  color: var(--color-text-secondary, #6b7280);
  font-size: 0.88rem;
}
.config-form input[type="text"],
.config-form input[type="password"] {
  flex: 1;
  max-width: 480px;
  padding: 6px 10px;
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 4px;
  font-size: 0.9rem;
}
.config-msg {
  font-size: 0.85rem;
}
.config-msg.success { color: #16a34a; }
.config-msg.error { color: #dc2626; }
</style>
