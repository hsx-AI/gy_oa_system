<template>
  <div class="lvr-page">
    <header class="lvr-header">
      <div class="lvr-header__title">
        <p class="lvr-eyebrow">数字化办公</p>
        <h1>低值易耗报销</h1>
      </div>
      <nav class="lvr-tabs">
        <button
          v-for="tab in visibleTabs"
          :key="tab.key"
          type="button"
          class="lvr-tab"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
          <span v-if="tab.key === 'pending' && pendingCount" class="tab-badge">{{ pendingCount }}</span>
        </button>
      </nav>
    </header>

    <section v-if="activeTab === 'apply'" class="lvr-apply-grid">
      <aside class="notice-panel">
        <h2 class="panel-title">报销须知</h2>
        <ul class="notice-list">
          <li class="notice-item--emphasis"><strong><span class="notice-highlight">购买前</span>请自行与主管领导确认可行性。</strong></li>
          <li>提交申请时需填写台账必填项，并上传已购买实物照片和发票。</li>
          <li>申请依次经主管领导（副经理）、主要领导（经理）审批，通过后由综合技术室主任/副主任完成报销闭环。</li>
        </ul>
      </aside>

      <form class="form-card" @submit.prevent="handleSubmit">
        <h2 class="panel-title">填写报销申请</h2>
        <div class="form-grid">
          <label class="form-row required">
            <span>物资名称</span>
            <input v-model="form.material_name" class="form-input" />
          </label>
          <label class="form-row">
            <span>规格</span>
            <input v-model="form.specification" class="form-input" />
          </label>
          <label class="form-row required">
            <span>单价</span>
            <input v-model.number="form.unit_price" type="number" step="0.01" min="0" class="form-input" />
          </label>
          <label class="form-row required">
            <span>数量</span>
            <input v-model.number="form.quantity" type="number" step="0.01" min="0" class="form-input" />
          </label>
          <label class="form-row">
            <span>总价</span>
            <input :value="totalPrice" class="form-input" disabled />
          </label>
          <label class="form-row required">
            <span>供应商名称</span>
            <input v-model="form.supplier" class="form-input" />
          </label>
          <label class="form-row">
            <span>工作号/科研号</span>
            <input v-model="form.work_no" class="form-input" />
          </label>
          <label class="form-row">
            <span>部套号</span>
            <input v-model="form.part_no" class="form-input" />
          </label>
          <label class="form-row">
            <span>申请人</span>
            <input :value="userName" class="form-input" disabled />
          </label>
          <label class="form-row required">
            <span>二级审批人</span>
            <select v-model="form.approver2" class="form-input">
              <option value="">请选择副经理</option>
              <option v-for="item in approvers.second" :key="item.name" :value="item.name">{{ item.label }}</option>
            </select>
          </label>
          <label class="form-row required">
            <span>三级审批人</span>
            <select v-model="form.approver3" class="form-input">
              <option value="">请选择经理</option>
              <option v-for="item in approvers.third" :key="item.name" :value="item.name">{{ item.label }}</option>
            </select>
          </label>
          <label class="form-row">
            <span>备注</span>
            <input v-model="form.remark" class="form-input" />
          </label>
        </div>

        <label class="form-row required form-row--full">
          <span>用途（详细说明）</span>
          <textarea v-model="form.usage_detail" class="form-textarea" rows="4" />
        </label>

        <div class="upload-grid">
          <FileBox title="已购买的实物照片" hint="支持拖拽、点击或 Ctrl+V 粘贴图片" accept=".jpg,.jpeg,.png,.gif,.bmp,.webp" :file="photoFile" @change="setPhotoFile" @invalid="showToast($event, 'error')" />
          <FileBox
            title="发票"
            hint="上传PDF自动识别；也可从文件夹复制后 Ctrl+V 粘贴 PDF/图片"
            :status="invoiceParseStatus"
            accept=".jpg,.jpeg,.png,.gif,.bmp,.webp,.pdf,.ofd"
            :file="invoiceFile"
            @change="setInvoiceFile"
            @invalid="showToast($event, 'error')"
          />
        </div>
        <div v-if="invoiceParseMessage || invoiceParsedSummary" class="invoice-parse-panel" :class="invoiceParseStatus">
          <strong>{{ invoiceParseMessage || '发票识别结果' }}</strong>
          <span v-if="invoiceParsedSummary">{{ invoiceParsedSummary }}</span>
        </div>

        <div class="form-actions">
          <button class="btn-primary" type="submit" :disabled="submitting">{{ submitting ? '提交中...' : '提交申请' }}</button>
        </div>
      </form>
    </section>

    <section v-if="activeTab === 'pending'" class="table-card">
      <div class="table-card__header">
        <h2 class="panel-title">待我处理（{{ pendingList.length }}）</h2>
        <div class="header-actions">
          <button class="btn-primary btn-outline" :disabled="!userName || invoiceCheckLoading" @click="runInvoiceCheck">
            {{ invoiceCheckLoading ? '校验中...' : '智能校验' }}
          </button>
          <button v-if="invoiceCheckResult" class="btn-approve" :disabled="!selectablePassedIds.length" @click="selectCheckedPassed">
            全选校验通过（{{ selectablePassedIds.length }}）
          </button>
          <button class="btn-plain" @click="loadPending">刷新</button>
        </div>
      </div>
      <div v-if="pendingList.length" class="batch-bar">
        <label class="batch-check">
          <input type="checkbox" class="row-check" :checked="allPendingSelected" @change="toggleSelectAll($event.target.checked)" />
          <span>全选</span>
        </label>
        <span class="batch-count">已选 <strong>{{ selectedIds.length }}</strong> / {{ pendingList.length }} 项</span>
        <div class="batch-actions">
          <button class="btn-approve" :disabled="!selectedIds.length || batchLoading" @click="batchApprove">批量通过</button>
          <button class="btn-reject" :disabled="!selectedIds.length || batchLoading" @click="openBatchReject">批量驳回</button>
        </div>
      </div>
      <RecordTable
        :rows="pendingList"
        mode="pending"
        :operator="userName"
        :selected-ids="selectedIds"
        :all-selected="allPendingSelected"
        @approve="handleAction($event, 'approve')"
        @reject="openReject"
        @complete="handleAction($event, 'complete')"
        @preview="openPreview"
        @toggle="toggleSelect"
        @toggle-all="toggleSelectAll"
        @detail="openDetail"
      />
    </section>

    <section v-if="activeTab === 'mine'" class="table-card">
      <div class="table-card__header">
        <h2 class="panel-title">我的申请</h2>
        <button class="btn-plain" @click="loadMine">刷新</button>
      </div>
      <RecordTable :rows="myList" mode="mine" @preview="openPreview" @delete="handleDelete" @detail="openDetail" />
    </section>

    <section v-if="activeTab === 'records'" class="records-panel">
      <div class="budget-stats">
        <div class="budget-stats__head">
          <div>
            <h2 class="panel-title">{{ budgetYear }} 年部门低值易耗额度</h2>
            <p class="budget-stats__hint">
              已完成按报销完成时间统计；审核中按申请年份统计；结余 = 年度总额 − 已完成。
              <template v-if="!budgetSummary.configured">（本年度总额尚未配置）</template>
            </p>
          </div>
          <div class="budget-stats__tools">
            <select v-model.number="budgetYear" class="filter-select" @change="loadBudgetSummary">
              <option v-for="y in budgetYearOptions" :key="y" :value="y">{{ y }} 年</option>
            </select>
            <button type="button" class="btn-primary" @click="openBudgetModal">配置年度额度</button>
          </div>
        </div>
        <div class="budget-stats__cards">
          <div class="budget-card">
            <span class="budget-card__label">年度总额</span>
            <strong class="budget-card__value">¥ {{ formatMoney(budgetSummary.total_amount) }}</strong>
          </div>
          <div class="budget-card budget-card--done">
            <span class="budget-card__label">本年度已完成</span>
            <strong class="budget-card__value">¥ {{ formatMoney(budgetSummary.completed_amount) }}</strong>
          </div>
          <div class="budget-card budget-card--pending">
            <span class="budget-card__label">正在审核中</span>
            <strong class="budget-card__value">¥ {{ formatMoney(budgetSummary.pending_amount) }}</strong>
          </div>
          <div class="budget-card budget-card--remain" :class="{ 'is-negative': Number(budgetSummary.remaining_amount) < 0 }">
            <span class="budget-card__label">当前结余</span>
            <strong class="budget-card__value">¥ {{ formatMoney(budgetSummary.remaining_amount) }}</strong>
            <small>扣除在审后预计结余 ¥ {{ formatMoney(budgetSummary.projected_remaining) }}</small>
          </div>
        </div>
      </div>

      <div class="table-card">
        <div class="table-card__header">
          <h2 class="panel-title">报销台账</h2>
          <div class="filter-bar">
            <input v-model="filter.keyword" class="filter-input" placeholder="物资/供应商/申请人/用途" @keyup.enter="loadRecords(1)" />
            <select v-model="filter.status" class="filter-select" @change="loadRecords(1)">
              <option value="">全部状态</option>
              <option value="pending2">待二级审批</option>
              <option value="pending3">待三级审批</option>
              <option value="pending-complete">待报销完成</option>
              <option value="completed">已完成</option>
              <option value="rejected">已驳回</option>
            </select>
            <input v-model="filter.date_from" class="filter-date" type="date" @change="loadRecords(1)" />
            <input v-model="filter.date_to" class="filter-date" type="date" @change="loadRecords(1)" />
            <button class="btn-plain" @click="loadRecords(1)">查询</button>
            <a class="btn-primary btn-link" :href="exportHref" target="_blank">导出Excel</a>
            <a class="btn-primary btn-link btn-outline" :href="invoiceZipHref" target="_blank">发票ZIP</a>
          </div>
        </div>
        <RecordTable :rows="recordsList" mode="records" :page="recordsPage" :page-size="pageSize" @preview="openPreview" @delete="handleDelete" @detail="openDetail" />
        <div class="pagination" v-if="recordsTotal > pageSize">
          <button :disabled="recordsPage <= 1" @click="loadRecords(recordsPage - 1)">上一页</button>
          <span>第 {{ recordsPage }} / {{ Math.ceil(recordsTotal / pageSize) }} 页，共 {{ recordsTotal }} 条</span>
          <button :disabled="recordsPage >= Math.ceil(recordsTotal / pageSize)" @click="loadRecords(recordsPage + 1)">下一页</button>
        </div>
      </div>
    </section>

    <div v-if="budgetModalVisible" class="modal-overlay" @click.self="budgetModalVisible = false">
      <div class="budget-modal">
        <div class="budget-modal__header">
          <h3 class="panel-title" style="margin:0">配置年度低值易耗总额</h3>
          <button type="button" class="preview-close" aria-label="关闭" @click="budgetModalVisible = false">×</button>
        </div>
        <div class="budget-modal__body">
          <p class="budget-modal__tip">可按年份配置部门低值易耗报销总额。台账结余会按「总额 − 当年已完成报销」自动计算。</p>
          <div class="budget-form">
            <label class="form-row required">
              <span>年度</span>
              <input v-model.number="budgetForm.budget_year" type="number" min="2000" max="2100" class="form-input" />
            </label>
            <label class="form-row required">
              <span>年度总额（元）</span>
              <input v-model.number="budgetForm.total_amount" type="number" step="0.01" min="0" class="form-input" placeholder="例如 20000" />
            </label>
            <label class="form-row form-row--full">
              <span>备注</span>
              <input v-model="budgetForm.remark" class="form-input" placeholder="可选" />
            </label>
          </div>
          <div class="budget-list" v-if="budgetList.length">
            <h4>已配置年度</h4>
            <ul>
              <li v-for="item in budgetList" :key="item.year">
                <button type="button" class="budget-list__item" @click="editBudgetYear(item)">
                  <strong>{{ item.year }} 年</strong>
                  <span>¥ {{ formatMoney(item.total_amount) }}</span>
                </button>
              </li>
            </ul>
          </div>
        </div>
        <div class="budget-modal__footer">
          <button type="button" class="btn-plain" @click="budgetModalVisible = false">取消</button>
          <button type="button" class="btn-primary" :disabled="budgetSaving" @click="saveBudget">{{ budgetSaving ? '保存中...' : '保存' }}</button>
        </div>
      </div>
    </div>

    <div v-if="rejectVisible" class="modal-overlay" @click.self="rejectVisible = false">
      <div class="reject-modal">
        <h3 class="panel-title">{{ rejectMode === 'batch' ? '批量驳回' : '驳回申请' }}</h3>
        <p class="reject-target">
          <template v-if="rejectMode === 'batch'">将驳回选中的 {{ selectedIds.length }} 条申请</template>
          <template v-else>{{ rejectTarget?.applicant }}：{{ rejectTarget?.material_name }}</template>
        </p>
        <textarea v-model="rejectReason" class="form-textarea" rows="3" placeholder="请输入驳回原因" />
        <div class="modal-actions">
          <button class="btn-plain" @click="rejectVisible = false">取消</button>
          <button class="btn-danger" @click="confirmReject">确认驳回</button>
        </div>
      </div>
    </div>

    <div v-if="previewVisible" class="preview-overlay" @click.self="closePreview">
      <div class="preview-modal">
        <div class="preview-modal__header">
          <div class="preview-modal__title">
            <span class="preview-kind">{{ previewItem?.kind === 'photo' ? '实物照片' : '发票' }}</span>
            <span class="preview-name" :title="previewItem?.original">{{ previewItem?.original || '附件预览' }}</span>
          </div>
          <div class="preview-modal__tools">
            <template v-if="previewCanApprove">
              <button type="button" class="btn-reject btn-sm" @click="previewReject">驳回</button>
              <button type="button" class="btn-approve btn-sm" @click="previewApprove">{{ Number(previewActionRow?.status) === 2 ? '完成报销' : '通过' }}</button>
            </template>
            <a class="btn-plain btn-sm" :href="previewInlineUrl" target="_blank" rel="noopener">新窗口打开</a>
            <a class="btn-plain btn-sm" :href="previewDownloadUrl">下载</a>
            <button type="button" class="preview-close" aria-label="关闭" @click="closePreview">×</button>
          </div>
        </div>
        <div class="preview-modal__body">
          <img v-if="previewType === 'image'" :src="previewInlineUrl" :alt="previewItem?.original || ''" class="preview-image" />
          <iframe v-else-if="previewType === 'pdf'" :src="previewInlineUrl" class="preview-frame" title="发票预览"></iframe>
          <div v-else class="preview-fallback">
            <p>该附件类型暂不支持在线预览。</p>
            <a class="btn-primary" :href="previewDownloadUrl">下载查看</a>
          </div>
        </div>
      </div>
    </div>

    <div v-if="detailVisible" class="modal-overlay" @click.self="closeDetail">
      <div class="detail-modal">
        <div class="detail-modal__header">
          <div class="detail-modal__title">
            <span class="panel-title" style="margin:0">报销申请详情</span>
            <span v-if="detailItem" class="status-tag" :class="statusClass(detailItem.status)">{{ detailItem.status_text || '-' }}</span>
          </div>
          <button type="button" class="preview-close" aria-label="关闭" @click="closeDetail">×</button>
        </div>
        <div class="detail-modal__body" v-if="detailItem">
          <section class="detail-section">
            <h4 class="detail-section__title">基本信息</h4>
            <div class="detail-grid">
              <div class="detail-field"><label>物资名称</label><span>{{ detailItem.material_name || '-' }}</span></div>
              <div class="detail-field"><label>规格</label><span>{{ detailItem.specification || '-' }}</span></div>
              <div class="detail-field"><label>单价</label><span>{{ formatMoney(detailItem.unit_price) }}</span></div>
              <div class="detail-field"><label>数量</label><span>{{ formatNumber(detailItem.quantity) }}</span></div>
              <div class="detail-field"><label>总价</label><span class="detail-strong">{{ formatMoney(detailItem.total_price) }}</span></div>
              <div class="detail-field"><label>供应商</label><span>{{ detailItem.supplier || '-' }}</span></div>
              <div class="detail-field"><label>工作号/科研号</label><span>{{ detailItem.work_no || '-' }}</span></div>
              <div class="detail-field"><label>部套号</label><span>{{ detailItem.part_no || '-' }}</span></div>
              <div class="detail-field detail-field--full"><label>用途（详细说明）</label><span class="detail-multiline">{{ detailItem.usage_detail || '-' }}</span></div>
              <div class="detail-field detail-field--full" v-if="detailItem.remark"><label>备注</label><span class="detail-multiline">{{ detailItem.remark }}</span></div>
            </div>
          </section>

          <section class="detail-section">
            <h4 class="detail-section__title">附件</h4>
            <div class="detail-attach-grid">
              <div class="detail-attach">
                <label>实物照片</label>
                <button v-if="detailItem.photo_attachment" type="button" class="attach-cell" @click="openPreview({ kind: 'photo', stored: detailItem.photo_attachment, original: detailItem.photo_original, row: detailItem, mode: detailMode })">
                  <img v-if="isLowValueImage(detailItem.photo_attachment)" class="attach-thumb" :src="lowValueAttachmentUrl('photo', detailItem.photo_attachment, 'inline')" :alt="detailItem.photo_original || ''" loading="lazy" />
                  <span v-else class="attach-thumb attach-thumb--file">文件</span>
                  <span class="attach-name">{{ detailItem.photo_original || '查看' }}</span>
                </button>
                <span v-else class="cell-dash">-</span>
              </div>
              <div class="detail-attach">
                <label>发票</label>
                <button v-if="detailItem.invoice_attachment" type="button" class="attach-cell" @click="openPreview({ kind: 'invoice', stored: detailItem.invoice_attachment, original: detailItem.invoice_original, row: detailItem, mode: detailMode })">
                  <img v-if="isLowValueImage(detailItem.invoice_attachment)" class="attach-thumb" :src="lowValueAttachmentUrl('invoice', detailItem.invoice_attachment, 'inline')" :alt="detailItem.invoice_original || ''" loading="lazy" />
                  <span v-else class="attach-thumb attach-thumb--file" :class="{ 'is-pdf': isLowValuePdf(detailItem.invoice_attachment) }">{{ isLowValuePdf(detailItem.invoice_attachment) ? 'PDF' : '文件' }}</span>
                  <span class="attach-name">{{ detailItem.invoice_original || '查看' }}</span>
                </button>
                <span v-else class="cell-dash">-</span>
              </div>
            </div>
          </section>

          <section class="detail-section">
            <h4 class="detail-section__title">审批流程</h4>
            <div class="detail-grid">
              <div class="detail-field"><label>申请人</label><span>{{ detailItem.applicant || '-' }}</span></div>
              <div class="detail-field"><label>申请科室</label><span>{{ detailItem.department || '-' }}</span></div>
              <div class="detail-field"><label>申请日期</label><span>{{ detailItem.apply_time || '-' }}</span></div>
              <div class="detail-field"><label>二级审批人</label><span>{{ detailItem.approver2 || '-' }}</span></div>
              <div class="detail-field"><label>二级审批时间</label><span>{{ detailItem.approve2_time || '-' }}</span></div>
              <div class="detail-field"><label>三级审批人</label><span>{{ detailItem.approver3 || '-' }}</span></div>
              <div class="detail-field"><label>三级审批时间</label><span>{{ detailItem.approve3_time || '-' }}</span></div>
              <div class="detail-field"><label>报销完成人</label><span>{{ detailItem.completer || '-' }}</span></div>
              <div class="detail-field"><label>报销完成时间</label><span>{{ detailItem.complete_time || '-' }}</span></div>
              <div class="detail-field detail-field--full" v-if="Number(detailItem.status) === 22 && detailItem.reject_reason">
                <label>驳回原因</label><span class="detail-multiline detail-reject">{{ detailItem.reject_reason }}</span>
              </div>
            </div>
          </section>
        </div>
        <div class="detail-modal__footer">
          <button type="button" class="btn-plain" @click="closeDetail">关闭</button>
          <template v-if="detailCanApprove">
            <button type="button" class="btn-reject" @click="detailReject">驳回</button>
            <button type="button" class="btn-approve" @click="detailApprove">{{ Number(detailItem?.status) === 2 ? '完成报销' : '通过' }}</button>
          </template>
        </div>
      </div>
    </div>

    <div v-if="invoiceCheckVisible" class="modal-overlay" @click.self="invoiceCheckVisible = false">
      <div class="check-modal">
        <div class="check-modal__header">
          <h3 class="panel-title" style="margin:0">发票智能校验</h3>
          <button type="button" class="preview-close" aria-label="关闭" @click="invoiceCheckVisible = false">×</button>
        </div>
        <div class="check-summary" v-if="invoiceCheckResult?.summary">
          <span>{{ invoiceCheckResult.summary.scope || '近一年未驳回申请' }}</span>
          <span>已校验 {{ invoiceCheckResult.summary.checked_count }} 项</span>
          <span>校验通过 {{ invoiceCheckResult.summary.passed_count || 0 }} 项</span>
          <span>重复发票 {{ invoiceCheckResult.summary.duplicate_count }} 组</span>
          <span>拆分风险 {{ invoiceCheckResult.summary.split_risk_count }} 组</span>
          <span v-if="invoiceCheckResult.summary.skipped_count">跳过 {{ invoiceCheckResult.summary.skipped_count }} 项</span>
        </div>
        <div class="check-modal__body">
          <section class="check-section">
            <h4>重复提交发票</h4>
            <p v-if="!invoiceCheckResult?.duplicate_invoices?.length" class="check-empty">未发现重复发票号码。</p>
            <div v-for="group in invoiceCheckResult?.duplicate_invoices || []" :key="group.invoice_number" class="risk-group">
              <strong>发票号码：{{ group.invoice_number }}</strong>
              <ul>
                <li v-for="item in group.items" :key="item.id">
                  <span>#{{ item.id }} {{ item.applicant }} - {{ item.material_name || '-' }}，{{ item.supplier || '-' }}，{{ item.status_text || '-' }}，金额 {{ formatMoney(item.total_price) }}</span>
                  <button type="button" class="risk-preview-btn" @click="previewCheckedInvoice(item)">预览发票</button>
                </li>
              </ul>
            </div>
          </section>
          <section class="check-section">
            <h4>拆分报销风险</h4>
            <p v-if="!invoiceCheckResult?.split_risks?.length" class="check-empty">未发现同供应商同开票日期的多张发票。</p>
            <div v-for="group in invoiceCheckResult?.split_risks || []" :key="`${group.supplier}-${group.invoice_date}`" class="risk-group">
              <strong>{{ group.supplier }}，开票日期：{{ group.invoice_date }}</strong>
              <ul>
                <li v-for="item in group.items" :key="item.id">
                  <span>#{{ item.id }} {{ item.applicant }} - {{ item.material_name || '-' }}，发票号 {{ item.invoice_number || '未识别' }}，{{ item.status_text || '-' }}，金额 {{ formatMoney(item.total_price) }}</span>
                  <button type="button" class="risk-preview-btn" @click="previewCheckedInvoice(item)">预览发票</button>
                </li>
              </ul>
            </div>
          </section>
          <section v-if="invoiceCheckResult?.skipped?.length" class="check-section">
            <h4>未校验项目</h4>
            <ul class="skip-list">
              <li v-for="item in invoiceCheckResult.skipped" :key="item.id">#{{ item.id }}：{{ item.reason }}</li>
            </ul>
          </section>
        </div>
      </div>
    </div>

    <div v-if="toastMsg" class="toast" :class="toastType">{{ toastMsg }}</div>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  actionLowValueReimbursement,
  batchActionLowValueReimbursement,
  checkLowValueInvoices,
  deleteLowValueReimbursement,
  getLowValueApprovers,
  getLowValueBudgetList,
  getLowValueBudgetSummary,
  getLowValueRecords,
  getMyLowValueApplications,
  getPendingLowValueReimbursements,
  isLowValueImage,
  isLowValuePdf,
  lowValueInvoiceZipUrl,
  lowValueAttachmentUrl,
  lowValueExportUrl,
  parseLowValueInvoice,
  saveLowValueBudget,
  submitLowValueReimbursement,
} from '@/api/lowValueReimbursement'

const FileBox = defineComponent({
  props: { title: String, hint: String, status: String, accept: String, file: Object },
  emits: ['change', 'invalid'],
  setup(props, { emit }) {
    const inputRef = ref(null)
    const dragging = ref(false)
    const pasteTarget = ref(false)
    const pick = () => inputRef.value?.click()
    const onChange = (e) => emit('change', e.target.files?.[0] || null)
    const IMAGE_EXTS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    const MIME_EXT = {
      'application/pdf': '.pdf',
      'application/ofd': '.ofd',
      'image/jpeg': '.jpg',
      'image/jpg': '.jpg',
      'image/png': '.png',
      'image/gif': '.gif',
      'image/bmp': '.bmp',
      'image/webp': '.webp',
    }
    const normalizePastedFile = (file) => {
      if (!file) return null
      const name = String(file.name || '').trim()
      if (name) return file
      const type = String(file.type || '').toLowerCase()
      let ext = MIME_EXT[type] || ''
      if (!ext && type.startsWith('image/')) {
        const sub = type.split('/')[1] || 'png'
        ext = `.${sub === 'jpeg' ? 'jpg' : sub}`
      }
      if (!ext) return file
      return new File([file], `粘贴文件${ext}`, { type: file.type || undefined, lastModified: file.lastModified || Date.now() })
    }
    const getClipboardFiles = (clipboardData) => {
      const fromFiles = Array.from(clipboardData?.files || []).filter(Boolean)
      if (fromFiles.length) return fromFiles.map(normalizePastedFile).filter(Boolean)
      const fromItems = []
      for (const item of Array.from(clipboardData?.items || [])) {
        if (item?.kind !== 'file') continue
        const file = normalizePastedFile(item.getAsFile())
        if (file) fromItems.push(file)
      }
      return fromItems
    }
    const acceptsFile = (file) => {
      const acceptList = String(props.accept || '')
        .toLowerCase()
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
      if (!acceptList.length) return true
      const fileName = String(file?.name || '').toLowerCase()
      const fileType = String(file?.type || '').toLowerCase()
      if (fileType.startsWith('image/') && acceptList.some((accept) => IMAGE_EXTS.includes(accept))) {
        return true
      }
      if (fileType === 'application/pdf' && acceptList.includes('.pdf')) return true
      if ((fileType === 'application/ofd' || fileType.includes('ofd')) && acceptList.includes('.ofd')) return true
      return acceptList.some((accept) => {
        if (accept.startsWith('.')) return fileName.endsWith(accept)
        if (accept.endsWith('/*')) return fileType.startsWith(accept.slice(0, -1))
        return fileType === accept
      })
    }
    const useFile = (file) => {
      if (!file) return
      if (!acceptsFile(file)) {
        emit('invalid', `${props.title || '附件'}不支持该文件格式`)
        return
      }
      emit('change', file)
    }
    const onDrop = (e) => {
      dragging.value = false
      useFile(normalizePastedFile(e.dataTransfer?.files?.[0]))
    }
    const onPaste = (e) => {
      if (e.defaultPrevented) return
      const files = getClipboardFiles(e.clipboardData)
      const file = files.find(acceptsFile)
      if (!file) {
        if (files.length) emit('invalid', `${props.title || '附件'}不支持剪贴板中的文件格式`)
        else if (pasteTarget.value) emit('invalid', '未检测到可粘贴文件，请先在文件夹中复制 PDF/图片后再粘贴')
        return
      }
      e.preventDefault()
      useFile(file)
    }
    const onWindowPaste = (e) => {
      if (pasteTarget.value) onPaste(e)
    }
    onMounted(() => window.addEventListener('paste', onWindowPaste))
    onBeforeUnmount(() => window.removeEventListener('paste', onWindowPaste))
    return () => h('div', {
      class: ['file-box', props.file ? 'has-file' : '', dragging.value ? 'is-dragging' : '', props.status ? `status-${props.status}` : ''],
      tabindex: 0,
      title: '点击选择文件，或将鼠标移到此处后按 Ctrl+V 粘贴',
      onPointerenter: () => { pasteTarget.value = true },
      onPointerleave: () => { pasteTarget.value = false },
      onDragenter: (e) => { e.preventDefault(); dragging.value = true },
      onDragover: (e) => { e.preventDefault(); dragging.value = true },
      onDragleave: () => { dragging.value = false },
      onDrop: (e) => { e.preventDefault(); onDrop(e) },
      onPaste,
    }, [
      h('input', { ref: inputRef, class: 'file-hidden', type: 'file', accept: props.accept, onChange }),
      props.file
        ? h('div', { class: 'file-selected' }, [
            h('strong', props.title),
            h('span', props.file.name),
            props.hint ? h('small', props.hint) : null,
            h('button', { type: 'button', onClick: () => emit('change', null) }, '移除'),
          ])
        : h('button', { type: 'button', class: 'file-empty', onClick: pick }, [
            h('strong', props.title),
            h('span', props.hint || '点击或拖拽上传'),
          ]),
    ])
  },
})

function attachmentCell(kind, stored, original, emit, row = null, mode = '') {
  if (!stored) return h('td', [h('span', { class: 'cell-dash' }, '-')])
  const isImg = isLowValueImage(stored)
  const isPdf = isLowValuePdf(stored)
  const thumb = isImg
    ? h('img', {
        class: 'attach-thumb',
        src: lowValueAttachmentUrl(kind, stored, 'inline'),
        alt: original || '',
        loading: 'lazy',
      })
    : h('span', { class: ['attach-thumb', 'attach-thumb--file', isPdf ? 'is-pdf' : ''] }, isPdf ? 'PDF' : '文件')
  return h('td', [
    h('button', {
      type: 'button',
      class: 'attach-cell',
      title: original ? `${original}（点击预览）` : '点击预览',
      onClick: () => emit('preview', { kind, stored, original, row, mode }),
    }, [thumb, h('span', { class: 'attach-name' }, original || '查看')]),
  ])
}

const RecordTable = defineComponent({
  props: {
    rows: Array,
    mode: String,
    page: { type: Number, default: 1 },
    pageSize: { type: Number, default: 20 },
    selectedIds: { type: Array, default: () => [] },
    allSelected: { type: Boolean, default: false },
  },
  emits: ['approve', 'reject', 'complete', 'preview', 'toggle', 'toggle-all', 'delete', 'detail'],
  setup(props, { emit }) {
    const cell = (text, cls = '') => h('td', { class: cls, title: text || '' }, text || '-')
    return () => {
      const rows = props.rows || []
      const selectable = props.mode === 'pending'
      if (!rows.length) return h('div', { class: 'empty-state' }, '暂无记录')
      const headers = [
        '序号', '物资名称', '申请人', '规格', '单价', '数量', '总价',
        '实物照片', '用途', '发票',
        '供应商', '工作号/科研号', '部套号',
        '二级审批人', '三级审批人', '状态', '申请日期', '操作',
      ]
      const headRow = []
      if (selectable) {
        headRow.push(h('th', { class: 'select-cell' }, [
          h('input', {
            type: 'checkbox',
            class: 'row-check',
            checked: props.allSelected,
            onChange: (e) => emit('toggle-all', e.target.checked),
          }),
        ]))
      }
      headers.forEach((x) => headRow.push(h('th', x)))
      return h('div', { class: 'table-wrap' }, [
        h('table', { class: 'data-table' }, [
          h('thead', [h('tr', headRow)]),
          h('tbody', rows.map((r, index) => {
            const tds = []
            if (selectable) {
              tds.push(h('td', { class: 'select-cell' }, [
                h('input', {
                  type: 'checkbox',
                  class: 'row-check',
                  checked: props.selectedIds.includes(r.id),
                  onChange: () => emit('toggle', r.id),
                }),
              ]))
            }
            tds.push(
              cell(String((Number(props.page) - 1) * Number(props.pageSize) + index + 1), 'index-cell'),
              cell(r.material_name, 'name-cell'),
              cell(r.applicant),
              cell(r.specification),
              cell(formatMoney(r.unit_price)),
              cell(formatNumber(r.quantity)),
              cell(formatMoney(r.total_price)),
              attachmentCell('photo', r.photo_attachment, r.photo_original, emit, r, props.mode),
              cell(r.usage_detail, 'wide-cell'),
              attachmentCell('invoice', r.invoice_attachment, r.invoice_original, emit, r, props.mode),
              cell(r.supplier, 'supplier-cell'),
              cell(r.work_no),
              cell(r.part_no),
              cell(r.approver2),
              cell(r.approver3),
              h('td', [h('span', { class: ['status-tag', statusClass(r.status)] }, r.status_text || '-')]),
              cell((r.apply_time || '').slice(0, 10)),
              h('td', { class: 'action-cell' }, actionButtons(r, props.mode, emit)),
            )
            return h('tr', { key: r.id, class: props.selectedIds.includes(r.id) ? 'row-selected' : '' }, tds)
          })),
        ]),
      ])
    }
  },
})

function actionButtons(row, mode, emit) {
  const detailBtn = h('button', { class: 'btn-detail', type: 'button', onClick: () => emit('detail', row) }, '详情')
  const buttons = [detailBtn]
  if (mode === 'pending') {
    if (Number(row.status) === 2) {
      buttons.push(h('button', { class: 'btn-approve', type: 'button', onClick: () => emit('complete', row) }, '完成报销'))
    } else {
      buttons.push(
        h('button', { class: 'btn-approve', type: 'button', onClick: () => emit('approve', row) }, '通过'),
        h('button', { class: 'btn-reject', type: 'button', onClick: () => emit('reject', row) }, '驳回'),
      )
    }
  } else if ((mode === 'mine' || mode === 'records') && Number(row.status) === 22) {
    buttons.push(h('button', { class: 'btn-delete', type: 'button', onClick: () => emit('delete', row) }, '删除'))
  }
  return buttons
}

const route = useRoute()
const tabs = [
  { key: 'apply', label: '发起申请' },
  { key: 'pending', label: '待我处理' },
  { key: 'mine', label: '我的申请' },
  { key: 'records', label: '报销台账' },
]
const activeTab = ref('apply')

function getUserInfo() {
  try {
    return JSON.parse(localStorage.getItem('userInfo') || '{}')
  } catch {
    return {}
  }
}

const userInfo = getUserInfo()
const userName = ref((userInfo.name || userInfo.userName || '').trim())
const userDept = ref((userInfo.dept || userInfo.lsys || '').trim())
const userJb = ref((userInfo.jb || '').trim())
const form = ref(defaultForm())
const photoFile = ref(null)
const invoiceFile = ref(null)
const invoiceParseStatus = ref('')
const invoiceParseMessage = ref('')
const invoiceParsed = ref(null)
const approvers = ref({ second: [], third: [], completers: [] })
const submitting = ref(false)
const pendingList = ref([])
const myList = ref([])
const recordsList = ref([])
const recordsTotal = ref(0)
const recordsPage = ref(1)
const pageSize = 20
const filter = ref({ keyword: '', status: '', date_from: '', date_to: '' })
const currentYear = new Date().getFullYear()
const budgetYear = ref(currentYear)
const budgetYearOptions = Array.from({ length: 8 }, (_, i) => currentYear - 2 + i)
const budgetSummary = ref({
  year: currentYear,
  total_amount: 0,
  completed_amount: 0,
  pending_amount: 0,
  remaining_amount: 0,
  projected_remaining: 0,
  configured: false,
})
const budgetList = ref([])
const budgetModalVisible = ref(false)
const budgetSaving = ref(false)
const budgetForm = ref({ budget_year: currentYear, total_amount: '', remark: '' })
const rejectVisible = ref(false)
const rejectTarget = ref(null)
const rejectReason = ref('')
const rejectMode = ref('single')
const selectedIds = ref([])
const batchLoading = ref(false)
const invoiceCheckLoading = ref(false)
const invoiceCheckVisible = ref(false)
const invoiceCheckResult = ref(null)
const toastMsg = ref('')
const toastType = ref('success')
let toastTimer = null

const previewVisible = ref(false)
const previewItem = ref(null)
const detailVisible = ref(false)
const detailItem = ref(null)
const detailMode = ref('')
const detailCanApprove = computed(() => {
  if (detailMode.value !== 'pending' || !detailItem.value) return false
  return [0, 1, 2].includes(Number(detailItem.value.status))
})
const previewType = computed(() => {
  const stored = previewItem.value?.stored
  if (!stored) return 'other'
  if (isLowValueImage(stored)) return 'image'
  if (isLowValuePdf(stored)) return 'pdf'
  return 'other'
})
const previewInlineUrl = computed(() => {
  const item = previewItem.value
  if (!item?.stored) return ''
  return lowValueAttachmentUrl(item.kind, item.stored, 'inline')
})
const previewDownloadUrl = computed(() => {
  const item = previewItem.value
  if (!item?.stored) return ''
  return lowValueAttachmentUrl(item.kind, item.stored)
})
const previewActionRow = computed(() => previewItem.value?.row || null)
const previewCanApprove = computed(() => {
  const row = previewActionRow.value
  return previewItem.value?.mode === 'pending' && row && [0, 1, 2].includes(Number(row.status))
})

const pendingCount = computed(() => pendingList.value.length)
const allPendingSelected = computed(() => pendingList.value.length > 0 && selectedIds.value.length === pendingList.value.length)
const selectablePassedIds = computed(() => {
  const pendingIds = new Set(pendingList.value.map((row) => Number(row.id)))
  return (invoiceCheckResult.value?.checked || [])
    .filter((item) => item.check_passed && pendingIds.has(Number(item.id)))
    .map((item) => item.id)
})
const totalPrice = computed(() => formatMoney((Number(form.value.unit_price) || 0) * (Number(form.value.quantity) || 0)))
const invoiceParsedSummary = computed(() => {
  const data = invoiceParsed.value
  if (!data) return ''
  const parts = []
  if (data.supplier) parts.push(`供应商：${data.supplier}`)
  if (data.quantity) {
    const quantityText = data.quantity_defaulted
      ? `数量：${formatNumber(data.quantity)}（未识别到数量，默认填入）`
      : `数量：${formatNumber(data.quantity)}`
    parts.push(quantityText)
  }
  if (data.unit_price) parts.push(`单价：${formatMoney(data.unit_price)}`)
  if (data.invoice_date) parts.push(`开票日期：${data.invoice_date}`)
  return parts.join('；')
})
const canViewLedger = computed(() => {
  const jb = userJb.value || ''
  const dept = userDept.value || ''
  const isLeader = jb === '经理' || jb.startsWith('经理') || jb === '副经理' || jb.startsWith('副经理')
  const isZhDirector = dept === '综合技术室' && jb.includes('主任')
  return isLeader || isZhDirector
})
const visibleTabs = computed(() => tabs.filter((tab) => tab.key !== 'records' || canViewLedger.value))
const ledgerParams = computed(() => ({ ...filter.value, current_user: userName.value }))
const exportHref = computed(() => lowValueExportUrl(ledgerParams.value))
const invoiceZipHref = computed(() => lowValueInvoiceZipUrl(ledgerParams.value))

function defaultForm() {
  return {
    material_name: '',
    specification: '',
    unit_price: '',
    quantity: '',
    supplier: '',
    work_no: '',
    part_no: '',
    usage_detail: '',
    approver2: '',
    approver3: '',
    remark: '',
  }
}

function showToast(msg, type = 'success') {
  toastMsg.value = msg
  toastType.value = type
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastMsg.value = '' }, 3500)
}

function formatMoney(value) {
  const n = Number(value) || 0
  return n.toFixed(2)
}

function formatNumber(value) {
  const n = Number(value) || 0
  return Number.isInteger(n) ? String(n) : String(n.toFixed(2)).replace(/0+$/, '').replace(/\.$/, '')
}

function statusClass(status) {
  const st = Number(status)
  if (st === 3) return 'status-approved'
  if (st === 22) return 'status-rejected'
  if (st === 2) return 'status-complete'
  return 'status-pending'
}

function openPreview(item) {
  if (!item?.stored) return
  previewItem.value = item
  previewVisible.value = true
}

function previewCheckedInvoice(item) {
  if (!item?.invoice_attachment) {
    showToast('该发票文件不存在，暂时无法预览', 'error')
    return
  }
  openPreview({
    kind: 'invoice',
    stored: item.invoice_attachment,
    original: item.invoice_original,
    row: item,
    mode: 'check',
  })
}

function closePreview() {
  previewVisible.value = false
  previewItem.value = null
}

async function previewApprove() {
  const row = previewActionRow.value
  if (!row) return
  const action = Number(row.status) === 2 ? 'complete' : 'approve'
  await handleAction(row, action)
  closePreview()
  if (detailVisible.value) closeDetail()
}

function previewReject() {
  const row = previewActionRow.value
  if (!row) return
  closePreview()
  if (detailVisible.value) closeDetail()
  openReject(row)
}

function openDetail(row) {
  if (!row) return
  detailItem.value = row
  detailMode.value = activeTab.value
  detailVisible.value = true
}

function closeDetail() {
  detailVisible.value = false
  detailItem.value = null
  detailMode.value = ''
}

async function detailApprove() {
  const row = detailItem.value
  if (!row) return
  const action = Number(row.status) === 2 ? 'complete' : 'approve'
  await handleAction(row, action)
  closeDetail()
}

function detailReject() {
  const row = detailItem.value
  if (!row) return
  closeDetail()
  openReject(row)
}

async function loadApprovers() {
  try {
    const res = await getLowValueApprovers()
    approvers.value = res?.data || { second: [], third: [], completers: [] }
    if (!form.value.approver3 && approvers.value.third?.length === 1) form.value.approver3 = approvers.value.third[0].name
  } catch {
    approvers.value = { second: [], third: [], completers: [] }
  }
}

function setPhotoFile(file) {
  photoFile.value = file
}

async function setInvoiceFile(file) {
  invoiceFile.value = file
  invoiceParsed.value = null
  invoiceParseStatus.value = ''
  invoiceParseMessage.value = ''
  if (!file) return
  if (!String(file.name || '').toLowerCase().endsWith('.pdf')) {
    invoiceParseStatus.value = 'idle'
    invoiceParseMessage.value = '当前仅PDF发票支持自动识别，图片发票请手工填写'
    return
  }
  invoiceParseStatus.value = 'loading'
  invoiceParseMessage.value = '正在识别发票信息...'
  try {
    const res = await parseLowValueInvoice(file)
    const data = res?.data || {}
    if (data.supplier) form.value.supplier = data.supplier
    if (data.quantity) form.value.quantity = data.quantity
    if (data.unit_price) form.value.unit_price = data.unit_price
    if (data.material_name) form.value.material_name = data.material_name
    invoiceParsed.value = data
    invoiceParseStatus.value = 'success'
    invoiceParseMessage.value = data.quantity_defaulted
      ? '已自动识别并覆盖表单字段，数量未识别到，已按1填入'
      : '已自动识别并覆盖表单字段，请核对后提交'
    showToast('发票已自动识别并回填')
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '发票解析失败，请手工填写'
    invoiceParseStatus.value = 'error'
    invoiceParseMessage.value = typeof msg === 'string' ? msg : '发票解析失败，请手工填写'
    showToast(invoiceParseMessage.value, 'error')
  }
}

function validateForm() {
  if (!form.value.material_name.trim()) return '请填写物资名称'
  if (!(Number(form.value.unit_price) > 0)) return '请填写有效单价'
  if (!(Number(form.value.quantity) > 0)) return '请填写有效数量'
  if (!form.value.supplier.trim()) return '请填写供应商名称'
  if (!form.value.usage_detail.trim()) return '请填写用途（详细说明）'
  if (!form.value.approver2) return '请选择二级审批人'
  if (!form.value.approver3) return '请选择三级审批人'
  if (!photoFile.value) return '请上传已购买的实物照片'
  if (!invoiceFile.value) return '请上传发票'
  return ''
}

async function handleSubmit() {
  const err = validateForm()
  if (err) {
    showToast(err, 'error')
    return
  }
  submitting.value = true
  try {
    await submitLowValueReimbursement({
      ...form.value,
      applicant: userName.value,
      department: userDept.value,
      photo: photoFile.value,
      invoice: invoiceFile.value,
    })
    showToast('报销申请已提交')
    form.value = defaultForm()
    photoFile.value = null
    invoiceFile.value = null
    invoiceParsed.value = null
    invoiceParseStatus.value = ''
    invoiceParseMessage.value = ''
    await loadMine()
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '提交失败'
    showToast(typeof msg === 'string' ? msg : '提交失败', 'error')
  } finally {
    submitting.value = false
  }
}

async function loadPending() {
  if (!userName.value) return
  try {
    const res = await getPendingLowValueReimbursements({ approver: userName.value })
    pendingList.value = res?.data || []
  } catch {
    pendingList.value = []
  } finally {
    pruneSelection()
  }
}

function pruneSelection() {
  const ids = new Set(pendingList.value.map((r) => r.id))
  selectedIds.value = selectedIds.value.filter((id) => ids.has(id))
}

function toggleSelect(id) {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(id)
}

function toggleSelectAll(checked) {
  selectedIds.value = checked ? pendingList.value.map((r) => r.id) : []
}

function selectCheckedPassed() {
  selectedIds.value = [...selectablePassedIds.value]
  showToast(`已选中 ${selectedIds.value.length} 条校验通过且有权审批的申请`)
}

async function runInvoiceCheck() {
  invoiceCheckLoading.value = true
  try {
    const res = await checkLowValueInvoices({ operator: userName.value })
    invoiceCheckResult.value = res?.data || null
    invoiceCheckVisible.value = true
    const summary = invoiceCheckResult.value?.summary || {}
    const riskCount = Number(summary.duplicate_count || 0) + Number(summary.split_risk_count || 0)
    showToast(riskCount ? `发现 ${riskCount} 组发票风险` : '未发现发票风险', riskCount ? 'error' : 'success')
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '发票校验失败'
    showToast(typeof msg === 'string' ? msg : '发票校验失败', 'error')
  } finally {
    invoiceCheckLoading.value = false
  }
}

function batchSummary(res) {
  const processed = res?.processed || 0
  const failed = res?.failed || []
  if (failed.length) {
    return { text: `已处理 ${processed} 条，${failed.length} 条未处理：${failed[0]?.reason || ''}`, type: 'error' }
  }
  return { text: `已处理 ${processed} 条`, type: 'success' }
}

async function batchApprove() {
  if (!selectedIds.value.length) return
  batchLoading.value = true
  try {
    const res = await batchActionLowValueReimbursement({ ids: selectedIds.value, operator: userName.value, action: 'approve' })
    const summary = batchSummary(res)
    showToast(summary.text, summary.type)
    selectedIds.value = []
    await loadPending()
    if (activeTab.value === 'records') await loadRecords(recordsPage.value)
    else if (canViewLedger.value) await loadBudgetSummary()
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '批量操作失败'
    showToast(typeof msg === 'string' ? msg : '批量操作失败', 'error')
  } finally {
    batchLoading.value = false
  }
}

function openBatchReject() {
  if (!selectedIds.value.length) return
  rejectMode.value = 'batch'
  rejectTarget.value = null
  rejectReason.value = ''
  rejectVisible.value = true
}

async function loadMine() {
  if (!userName.value) return
  try {
    const res = await getMyLowValueApplications({ name: userName.value })
    myList.value = res?.data || []
  } catch {
    myList.value = []
  }
}

async function loadRecords(page = 1) {
  if (!canViewLedger.value) {
    recordsList.value = []
    recordsTotal.value = 0
    return
  }
  recordsPage.value = page
  try {
    const res = await getLowValueRecords({ page, page_size: pageSize, ...ledgerParams.value })
    recordsList.value = res?.data || []
    recordsTotal.value = res?.total || 0
  } catch {
    recordsList.value = []
    recordsTotal.value = 0
  }
  await loadBudgetSummary()
}

async function loadBudgetSummary() {
  if (!canViewLedger.value || !userName.value) return
  try {
    const res = await getLowValueBudgetSummary({ year: budgetYear.value, current_user: userName.value })
    budgetSummary.value = {
      year: budgetYear.value,
      total_amount: 0,
      completed_amount: 0,
      pending_amount: 0,
      remaining_amount: 0,
      projected_remaining: 0,
      configured: false,
      ...(res?.data || {}),
    }
  } catch {
    budgetSummary.value = {
      year: budgetYear.value,
      total_amount: 0,
      completed_amount: 0,
      pending_amount: 0,
      remaining_amount: 0,
      projected_remaining: 0,
      configured: false,
    }
  }
}

async function loadBudgetList() {
  if (!canViewLedger.value || !userName.value) return
  try {
    const res = await getLowValueBudgetList({ current_user: userName.value })
    budgetList.value = res?.data || []
  } catch {
    budgetList.value = []
  }
}

function openBudgetModal() {
  budgetForm.value = {
    budget_year: budgetYear.value,
    total_amount: budgetSummary.value.configured ? budgetSummary.value.total_amount : '',
    remark: budgetSummary.value.remark || '',
  }
  budgetModalVisible.value = true
  loadBudgetList()
}

function editBudgetYear(item) {
  budgetForm.value = {
    budget_year: item.year,
    total_amount: item.total_amount,
    remark: item.remark || '',
  }
}

async function saveBudget() {
  const year = Number(budgetForm.value.budget_year)
  const amount = Number(budgetForm.value.total_amount)
  if (!Number.isInteger(year) || year < 2000 || year > 2100) {
    showToast('请输入有效年度', 'error')
    return
  }
  if (!(amount >= 0) || Number.isNaN(amount)) {
    showToast('请输入有效的年度总额', 'error')
    return
  }
  budgetSaving.value = true
  try {
    const res = await saveLowValueBudget({
      budget_year: year,
      total_amount: amount,
      remark: budgetForm.value.remark || '',
      operator: userName.value,
    })
    showToast(res?.message || '年度额度已保存')
    budgetYear.value = year
    budgetModalVisible.value = false
    await loadBudgetSummary()
    await loadBudgetList()
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '保存失败'
    showToast(typeof msg === 'string' ? msg : '保存失败', 'error')
  } finally {
    budgetSaving.value = false
  }
}

async function handleAction(row, action) {
  try {
    await actionLowValueReimbursement({ id: row.id, operator: userName.value, action })
    showToast(action === 'complete' ? '已完成报销闭环' : '已审批通过')
    await loadPending()
    if (activeTab.value === 'records') {
      await loadRecords(recordsPage.value)
    } else if (canViewLedger.value) {
      await loadBudgetSummary()
    }
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '操作失败'
    showToast(typeof msg === 'string' ? msg : '操作失败', 'error')
  }
}

async function handleDelete(row) {
  if (!row?.id) return
  const label = `${row.applicant || ''}：${row.material_name || ''}`.replace(/^：/, '')
  if (!window.confirm(`确认删除已驳回申请「${label || row.id}」？删除后不可恢复。`)) return
  try {
    await deleteLowValueReimbursement({ id: row.id, operator: userName.value })
    showToast('已删除')
    if (activeTab.value === 'mine') await loadMine()
    if (activeTab.value === 'records') await loadRecords(recordsPage.value)
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '删除失败'
    showToast(typeof msg === 'string' ? msg : '删除失败', 'error')
  }
}

function openReject(row) {
  rejectMode.value = 'single'
  rejectTarget.value = row
  rejectReason.value = ''
  rejectVisible.value = true
}

async function confirmReject() {
  if (rejectMode.value === 'batch') {
    if (!selectedIds.value.length) return
    batchLoading.value = true
    try {
      const res = await batchActionLowValueReimbursement({
        ids: selectedIds.value,
        operator: userName.value,
        action: 'reject',
        reject_reason: rejectReason.value,
      })
      const summary = batchSummary(res)
      showToast(summary.text, summary.type)
      rejectVisible.value = false
      selectedIds.value = []
      await loadPending()
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || '批量操作失败'
      showToast(typeof msg === 'string' ? msg : '批量操作失败', 'error')
    } finally {
      batchLoading.value = false
    }
    return
  }
  if (!rejectTarget.value) return
  try {
    await actionLowValueReimbursement({
      id: rejectTarget.value.id,
      operator: userName.value,
      action: 'reject',
      reject_reason: rejectReason.value,
    })
    showToast('已驳回')
    rejectVisible.value = false
    await loadPending()
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '操作失败'
    showToast(typeof msg === 'string' ? msg : '操作失败', 'error')
  }
}

watch(activeTab, (tab) => {
  if (tab === 'records' && !canViewLedger.value) {
    activeTab.value = 'apply'
    return
  }
  if (tab === 'pending') loadPending()
  if (tab === 'mine') loadMine()
  if (tab === 'records') {
    loadRecords(1)
    loadBudgetSummary()
  }
})

onMounted(() => {
  const tab = route.query.tab
  if (tab && visibleTabs.value.some((item) => item.key === tab)) activeTab.value = tab
  loadApprovers()
  loadPending()
  loadMine()
})

watch(rejectVisible, (visible) => {
  if (!visible) {
    rejectTarget.value = null
    rejectMode.value = 'single'
  }
})
</script>

<style scoped>
.lvr-page {
  min-height: 100vh;
  padding: 0 18px 28px 0;
  color: var(--color-text-primary);
}

/* 顶部标题 + 选项卡 */
.lvr-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-base);
  margin-bottom: var(--spacing-base);
  padding: var(--spacing-lg) var(--spacing-xl);
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--radius-md);
  background: var(--color-bg-container);
  box-shadow: var(--shadow-card);
  flex-wrap: wrap;
}
.lvr-header__title h1 {
  margin: 0;
  font-size: var(--font-size-xxl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}
.lvr-eyebrow {
  margin: 0 0 4px;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  letter-spacing: .5px;
  color: var(--color-primary);
}
.lvr-tabs {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  border-radius: var(--radius-md);
  background: var(--color-bg-spotlight);
  border: 1px solid var(--color-border-lighter);
  flex-wrap: wrap;
}
.lvr-tab {
  position: relative;
  padding: 8px 18px;
  border: none;
  border-radius: var(--radius-base);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--transition-base) var(--transition-ease);
}
.lvr-tab:hover {
  color: var(--color-primary);
}
.lvr-tab.active {
  color: #fff;
  background: var(--color-primary);
  box-shadow: 0 2px 6px rgba(0, 0, 0, .12);
}
.tab-badge {
  margin-left: 6px;
  padding: 1px 7px;
  border-radius: var(--radius-circle);
  background: var(--color-error);
  color: #fff;
  font-size: var(--font-size-xs);
}
.lvr-tab.active .tab-badge {
  background: #fff;
  color: var(--color-primary);
}

/* 卡片通用 */
.lvr-apply-grid {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: var(--spacing-base);
  align-items: start;
}
.notice-panel,
.form-card,
.table-card {
  background: var(--color-bg-container);
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
}
.panel-title {
  margin: 0 0 var(--spacing-base);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}
.notice-panel {
  padding: var(--spacing-lg);
}
.notice-list {
  margin: 0;
  padding-left: 18px;
  color: var(--color-text-secondary);
  line-height: 1.75;
  font-size: var(--font-size-sm);
}
.notice-list li {
  margin-bottom: 8px;
}
.notice-list li:last-child {
  margin-bottom: 0;
}
.notice-list li.notice-item--emphasis {
  font-weight: var(--font-weight-semibold);
}
.notice-highlight {
  color: var(--color-error);
  font-weight: var(--font-weight-bold);
}
.notice-list li::marker {
  color: var(--color-primary);
}
.form-card {
  padding: var(--spacing-xl);
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--spacing-base);
}
.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}
.form-row.required > span::after {
  content: '*';
  color: var(--color-error);
  margin-left: 3px;
}
.form-row--full {
  margin-top: var(--spacing-base);
}
.form-input,
.form-textarea,
.filter-input,
.filter-date,
.filter-select {
  min-height: 38px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  padding: 9px 11px;
  background: var(--color-bg-container);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  outline: none;
  transition: border-color var(--transition-base) var(--transition-ease), box-shadow var(--transition-base) var(--transition-ease);
}
.form-input:focus,
.form-textarea:focus,
.filter-input:focus,
.filter-date:focus,
.filter-select:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-lightest);
}
.form-input:disabled {
  background: var(--color-bg-spotlight);
  color: var(--color-text-tertiary);
}
.form-textarea {
  resize: vertical;
  min-height: 90px;
}
.upload-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--spacing-base);
  margin-top: var(--spacing-base);
}
:deep(.file-box) {
  border: 2px dashed var(--color-border-base);
  border-radius: var(--radius-md);
  min-height: 96px;
  overflow: hidden;
  transition: all var(--transition-base) var(--transition-ease);
}
:deep(.file-box.has-file) {
  border-style: solid;
  border-color: var(--color-primary-light);
  background: var(--color-primary-lightest);
}
:deep(.file-box.is-dragging) {
  border-color: var(--color-primary);
  background: var(--color-primary-lightest);
}
:deep(.file-box:focus),
:deep(.file-box:focus-within) {
  border-color: var(--color-primary);
  outline: 3px solid var(--color-primary-lightest);
}
:deep(.file-box.status-loading) {
  border-color: var(--color-primary-light);
  background: var(--color-primary-lightest);
}
:deep(.file-box.status-success) {
  border-color: var(--color-success-light);
  background: var(--color-success-bg);
}
:deep(.file-box.status-error) {
  border-color: var(--color-error-light);
  background: var(--color-error-bg);
}
:deep(.file-hidden) {
  display: none;
}
:deep(.file-empty),
:deep(.file-selected) {
  width: 100%;
  min-height: 96px;
  border: 0;
  background: transparent;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--color-text-secondary);
  cursor: pointer;
}
:deep(.file-empty strong),
:deep(.file-selected strong) {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}
:deep(.file-selected span) {
  max-width: 90%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-size-sm);
  color: var(--color-primary-dark);
}
:deep(.file-selected small) {
  max-width: 90%;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-xs);
  line-height: 1.35;
  text-align: center;
}
:deep(.file-selected button) {
  border: 1px solid var(--color-error);
  border-radius: var(--radius-base);
  background: var(--color-bg-container);
  color: var(--color-error);
  padding: 4px 12px;
  cursor: pointer;
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--spacing-lg);
}
.invoice-parse-panel {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: var(--spacing-md);
  padding: 10px 12px;
  border: 1px solid var(--color-info-light);
  border-radius: var(--radius-base);
  background: var(--color-info-bg);
  color: var(--color-primary-dark);
  font-size: var(--font-size-sm);
  line-height: 1.45;
}
.invoice-parse-panel.success {
  border-color: var(--color-success-light);
  background: var(--color-success-bg);
  color: #166534;
}
.invoice-parse-panel.error {
  border-color: var(--color-error-light);
  background: var(--color-error-bg);
  color: #991b1b;
}
.invoice-parse-panel.idle {
  border-color: var(--color-border-light);
  background: var(--color-bg-spotlight);
  color: var(--color-text-secondary);
}

/* 按钮 */
.btn-primary,
.btn-plain,
.btn-danger,
.btn-approve,
.btn-reject {
  border-radius: var(--radius-base);
  padding: 7px 16px;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition-base) var(--transition-ease);
}
.btn-primary {
  border: 1px solid var(--color-primary);
  color: #fff;
  background: var(--color-primary);
}
.btn-primary:hover {
  background: var(--color-primary-dark);
  border-color: var(--color-primary-dark);
}
.btn-outline {
  background: var(--color-bg-container);
  color: var(--color-primary);
}
.btn-outline:hover {
  background: var(--color-primary-lightest);
  color: var(--color-primary-dark);
}
.btn-link {
  display: inline-flex;
  align-items: center;
  text-decoration: none;
}
.btn-plain {
  border: 1px solid var(--color-border-base);
  color: var(--color-text-secondary);
  background: var(--color-bg-container);
}
.btn-plain:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.btn-sm {
  padding: 4px 10px;
  font-size: var(--font-size-xs);
}
.btn-danger,
.btn-reject {
  border: 1px solid var(--color-error);
  color: var(--color-error);
  background: var(--color-error-bg);
}
.btn-danger:hover,
.btn-reject:hover {
  background: var(--color-error);
  color: #fff;
}
.btn-approve {
  border: 1px solid var(--color-success);
  color: #047857;
  background: var(--color-success-bg);
}
.btn-approve:hover {
  background: var(--color-success);
  color: #fff;
}
.btn-primary:disabled {
  opacity: .6;
  cursor: not-allowed;
}

/* 年度额度统计 */
.records-panel {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-base);
}
.budget-stats {
  background: var(--color-bg-container);
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  padding: var(--spacing-lg);
}
.budget-stats__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-base);
  flex-wrap: wrap;
  margin-bottom: var(--spacing-base);
}
.budget-stats__head .panel-title {
  margin: 0 0 4px;
}
.budget-stats__hint {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  line-height: 1.5;
}
.budget-stats__tools {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.budget-stats__cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--spacing-md);
}
.budget-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 16px;
  border-radius: var(--radius-md);
  background: var(--color-bg-spotlight);
  border: 1px solid var(--color-border-lighter);
}
.budget-card--done {
  background: #f0fdf4;
  border-color: #bbf7d0;
}
.budget-card--pending {
  background: #fffbeb;
  border-color: #fde68a;
}
.budget-card--remain {
  background: var(--color-primary-lightest);
  border-color: var(--color-primary-light);
}
.budget-card--remain.is-negative {
  background: var(--color-error-bg);
  border-color: var(--color-error-light);
}
.budget-card__label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}
.budget-card__value {
  font-size: 22px;
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
}
.budget-card--remain .budget-card__value {
  color: var(--color-primary-dark);
}
.budget-card--remain.is-negative .budget-card__value {
  color: var(--color-error);
}
.budget-card small {
  font-size: 11px;
  color: var(--color-text-tertiary);
  line-height: 1.4;
}
.budget-modal {
  width: min(520px, 94vw);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-lg);
  background: var(--color-bg-container);
  box-shadow: var(--shadow-elevated);
  overflow: hidden;
}
.budget-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-lighter);
  background: var(--color-bg-spotlight);
}
.budget-modal__body {
  padding: var(--spacing-lg);
  overflow-y: auto;
}
.budget-modal__tip {
  margin: 0 0 var(--spacing-base);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.55;
}
.budget-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-base);
}
.budget-list {
  margin-top: var(--spacing-lg);
}
.budget-list h4 {
  margin: 0 0 8px;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
.budget-list ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.budget-list__item {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--radius-base);
  background: var(--color-bg-spotlight);
  cursor: pointer;
  color: var(--color-text-primary);
}
.budget-list__item:hover {
  border-color: var(--color-primary-light);
  background: var(--color-primary-lightest);
}
.budget-modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: var(--spacing-md) var(--spacing-lg);
  border-top: 1px solid var(--color-border-lighter);
}
@media (max-width: 900px) {
  .budget-stats__cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .budget-form {
    grid-template-columns: 1fr;
  }
}

/* 表格 */
.table-card {
  overflow: hidden;
}
.table-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  padding: var(--spacing-base) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-lighter);
  flex-wrap: wrap;
}
.table-card__header .panel-title {
  margin: 0;
}
.filter-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.batch-bar {
  display: flex;
  align-items: center;
  gap: var(--spacing-base);
  padding: 10px var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-lighter);
  background: var(--color-bg-spotlight);
  flex-wrap: wrap;
}
.batch-check {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
}
.batch-check .row-check {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--color-primary);
}
.batch-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}
.batch-count strong {
  color: var(--color-primary);
}
.batch-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}
.batch-actions .btn-approve,
.batch-actions .btn-reject {
  border-radius: var(--radius-base);
  padding: 6px 16px;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--transition-base) var(--transition-ease);
}
.batch-actions .btn-approve {
  border: 1px solid var(--color-success);
  color: #047857;
  background: var(--color-success-bg);
}
.batch-actions .btn-approve:hover:not(:disabled) {
  background: var(--color-success);
  color: #fff;
}
.batch-actions .btn-reject {
  border: 1px solid var(--color-error);
  color: var(--color-error);
  background: var(--color-error-bg);
}
.batch-actions .btn-reject:hover:not(:disabled) {
  background: var(--color-error);
  color: #fff;
}
.batch-actions button:disabled {
  opacity: .5;
  cursor: not-allowed;
}
.filter-input {
  width: 230px;
}
.table-wrap {
  overflow-x: auto;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
  table-layout: auto;
}
.data-table th,
.data-table td {
  padding: 11px 12px;
  border-bottom: 1px solid var(--color-border-lighter);
  text-align: left;
  white-space: nowrap;
  vertical-align: middle;
}
.data-table th {
  background: var(--color-bg-spotlight);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-semibold);
}
.data-table tbody tr:hover {
  background: var(--color-primary-lightest);
}
.index-cell {
  width: 56px;
  color: var(--color-text-tertiary);
  text-align: center;
  font-variant-numeric: tabular-nums;
}
.wide-cell {
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cell-dash {
  color: var(--color-text-tertiary);
}

/* 附件缩略图/预览按钮 */
.attach-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 190px;
  padding: 3px 6px;
  border: 1px solid transparent;
  border-radius: var(--radius-base);
  background: transparent;
  cursor: pointer;
  transition: all var(--transition-base) var(--transition-ease);
}
.attach-cell:hover {
  border-color: var(--color-primary-light);
  background: var(--color-primary-lightest);
}
.attach-thumb {
  width: 42px;
  height: 42px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  object-fit: cover;
  border: 1px solid var(--color-border-light);
  background: var(--color-bg-spotlight);
}
.attach-thumb--file {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-tertiary);
}
.attach-thumb.is-pdf {
  color: #b91c1c;
  background: var(--color-error-bg);
  border-color: var(--color-error-light);
}
.attach-name {
  max-width: 130px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-primary);
  font-size: var(--font-size-xs);
}

.status-tag {
  display: inline-block;
  padding: 2px 9px;
  border-radius: var(--radius-circle);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
}
.status-pending { color: #b45309; background: #fef3c7; }
.status-complete { color: var(--color-primary-dark); background: var(--color-primary-lightest); }
.status-approved { color: #15803d; background: #dcfce7; }
.status-rejected { color: var(--color-error); background: var(--color-error-bg); }
.action-cell {
  display: flex;
  gap: 6px;
  min-width: 112px;
}
.empty-state {
  padding: 44px;
  text-align: center;
  color: var(--color-text-tertiary);
}
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  padding: var(--spacing-base);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}
.pagination button {
  padding: 6px 14px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  background: var(--color-bg-container);
  color: var(--color-text-secondary);
  cursor: pointer;
}
.pagination button:disabled {
  opacity: .5;
  cursor: not-allowed;
}

/* 弹窗通用 */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-index-modal);
  background: var(--color-bg-mask);
  display: flex;
  align-items: center;
  justify-content: center;
}
.reject-modal {
  width: 440px;
  max-width: 92vw;
  padding: var(--spacing-lg);
  border-radius: var(--radius-md);
  background: var(--color-bg-container);
  box-shadow: var(--shadow-elevated);
}
.reject-target {
  margin: 0 0 var(--spacing-md);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: var(--spacing-md);
}

.check-modal {
  width: min(760px, 94vw);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-lg);
  background: var(--color-bg-container);
  box-shadow: var(--shadow-elevated);
  overflow: hidden;
}
.check-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-lighter);
  background: var(--color-bg-spotlight);
}
.check-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: var(--spacing-base) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-lighter);
}
.check-summary span {
  padding: 3px 9px;
  border-radius: var(--radius-circle);
  background: var(--color-primary-lightest);
  color: var(--color-primary-dark);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
}
.check-modal__body {
  overflow-y: auto;
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}
.check-section h4 {
  margin: 0 0 8px;
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
}
.check-empty {
  margin: 0;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}
.risk-group {
  padding: 10px 12px;
  border: 1px solid var(--color-error-light);
  border-radius: var(--radius-base);
  background: var(--color-error-bg);
  color: var(--color-text-primary);
}
.risk-group + .risk-group {
  margin-top: 8px;
}
.risk-group ul,
.skip-list {
  margin: 8px 0 0;
  padding-left: 18px;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  line-height: 1.65;
}
.risk-group li {
  margin: 6px 0;
}
.risk-preview-btn {
  margin-left: 10px;
  padding: 3px 9px;
  border: 1px solid #93c5fd;
  border-radius: 6px;
  color: #1d4ed8;
  background: #eff6ff;
  cursor: pointer;
  white-space: nowrap;
}
.risk-preview-btn:hover {
  border-color: #3b82f6;
  background: #dbeafe;
}

/* 详情弹窗 */
.detail-modal {
  width: min(720px, 94vw);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-lg);
  background: var(--color-bg-container);
  box-shadow: var(--shadow-elevated);
  overflow: hidden;
}
.detail-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-lighter);
  background: var(--color-bg-spotlight);
}
.detail-modal__title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.detail-modal__body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}
.detail-section__title {
  margin: 0 0 var(--spacing-md);
  padding-left: 8px;
  border-left: 3px solid var(--color-primary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}
.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px var(--spacing-lg);
}
.detail-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.detail-field--full {
  grid-column: 1 / -1;
}
.detail-field label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}
.detail-field span {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  word-break: break-word;
}
.detail-strong {
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-dark);
}
.detail-multiline {
  line-height: 1.6;
  white-space: pre-wrap;
}
.detail-reject {
  color: var(--color-error);
}
.detail-attach-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--spacing-lg);
}
.detail-attach {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.detail-attach label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}
.detail-modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: var(--spacing-md) var(--spacing-lg);
  border-top: 1px solid var(--color-border-lighter);
}
@media (max-width: 640px) {
  .detail-grid,
  .detail-attach-grid {
    grid-template-columns: 1fr;
  }
}

/* 附件预览弹窗 */
.preview-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-index-popover);
  background: rgba(0, 0, 0, .72);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-lg);
}
.preview-modal {
  width: min(960px, 94vw);
  max-height: 92vh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-container);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-elevated);
  overflow: hidden;
}
.preview-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  flex-wrap: wrap;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-lighter);
  background: var(--color-bg-spotlight);
}
.preview-modal__title {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.preview-kind {
  flex-shrink: 0;
  padding: 2px 10px;
  border-radius: var(--radius-circle);
  background: var(--color-primary-lightest);
  color: var(--color-primary-dark);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
}
.preview-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
.preview-modal__tools {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  flex-shrink: 0;
}
.preview-close {
  width: 30px;
  height: 30px;
  border: none;
  background: transparent;
  color: var(--color-text-tertiary);
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  border-radius: var(--radius-base);
}
.preview-close:hover {
  background: var(--color-border-lighter);
  color: var(--color-text-primary);
}
.preview-modal__body {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-base);
  background: var(--color-bg-layout);
  overflow: auto;
}
.preview-image {
  max-width: 100%;
  max-height: calc(92vh - 120px);
  object-fit: contain;
  border-radius: var(--radius-base);
  box-shadow: 0 8px 24px rgba(0, 0, 0, .18);
}
.preview-frame {
  width: 100%;
  height: calc(92vh - 120px);
  border: none;
  background: #fff;
  border-radius: var(--radius-base);
}
.preview-fallback {
  text-align: center;
  color: var(--color-text-secondary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
}

/* Toast */
.toast {
  position: fixed;
  top: 76px;
  left: 50%;
  z-index: var(--z-index-tooltip);
  transform: translateX(-50%);
  padding: 10px 24px;
  border-radius: var(--radius-md);
  background: #047857;
  color: #fff;
  box-shadow: var(--shadow-popup);
}
.toast.error {
  background: var(--color-error);
}

@media (max-width: 900px) {
  .lvr-apply-grid,
  .form-grid,
  .upload-grid {
    grid-template-columns: 1fr;
  }
}
</style>

<!--
  以下为「非 scoped」样式：RecordTable 使用渲染函数(h)生成，其内部元素不会带上
  scoped 的 data-v 属性，因此 scoped 样式无法命中。这里统一以 .lvr-page 前缀限定，
  既能命中渲染函数生成的表格元素，又不会污染其他页面（.lvr-page 为本页面独有根类名）。
-->
<style>
.lvr-page .table-wrap {
  overflow-x: auto;
}
.lvr-page .data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
  table-layout: auto;
}
.lvr-page .data-table th,
.lvr-page .data-table td {
  padding: 11px 12px;
  border-bottom: 1px solid var(--color-border-lighter);
  text-align: left;
  white-space: nowrap;
  vertical-align: middle;
}
.lvr-page .data-table th {
  background: var(--color-bg-spotlight);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-semibold);
}
.lvr-page .data-table tbody tr:hover {
  background: var(--color-primary-lightest);
}
.lvr-page .index-cell {
  width: 56px;
  color: var(--color-text-tertiary);
  text-align: center;
  font-variant-numeric: tabular-nums;
}
.lvr-page .wide-cell {
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* 物资名称、供应商文字较长，允许自动换行以节省横向空间
   （选择器需带 .data-table td 前缀，优先级要高于通用的 nowrap 规则） */
.lvr-page .data-table td.name-cell,
.lvr-page .data-table td.supplier-cell {
  white-space: normal;
  word-break: break-word;
  line-height: 1.5;
}
.lvr-page .data-table td.name-cell {
  min-width: 180px;
  max-width: 260px;
}
.lvr-page .data-table td.supplier-cell {
  min-width: 130px;
  max-width: 180px;
}
.lvr-page .cell-dash {
  color: var(--color-text-tertiary);
}

/* 附件缩略图 / 预览触发按钮 */
.lvr-page .attach-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 190px;
  padding: 3px 6px;
  border: 1px solid transparent;
  border-radius: var(--radius-base);
  background: transparent;
  cursor: pointer;
  transition: all var(--transition-base) var(--transition-ease);
}
.lvr-page .attach-cell:hover {
  border-color: var(--color-primary-light);
  background: var(--color-primary-lightest);
}
.lvr-page .attach-thumb {
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  object-fit: cover;
  border: 1px solid var(--color-border-light);
  background: var(--color-bg-spotlight);
  display: block;
}
.lvr-page .attach-thumb--file {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-tertiary);
}
.lvr-page .attach-thumb.is-pdf {
  color: #b91c1c;
  background: var(--color-error-bg);
  border-color: var(--color-error-light);
}
.lvr-page .attach-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-primary);
  font-size: var(--font-size-xs);
}

/* 状态标签 */
.lvr-page .status-tag {
  display: inline-block;
  padding: 2px 9px;
  border-radius: var(--radius-circle);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
}
.lvr-page .status-pending { color: #b45309; background: #fef3c7; }
.lvr-page .status-complete { color: var(--color-primary-dark); background: var(--color-primary-lightest); }
.lvr-page .status-approved { color: #15803d; background: #dcfce7; }
.lvr-page .status-rejected { color: var(--color-error); background: var(--color-error-bg); }

.lvr-page .action-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 112px;
}
.lvr-page .empty-state {
  padding: 44px;
  text-align: center;
  color: var(--color-text-tertiary);
}

/* 表格内审批 / 驳回按钮（渲染函数生成） */
.lvr-page .btn-approve,
.lvr-page .btn-reject {
  border-radius: var(--radius-base);
  padding: 6px 14px;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition-base) var(--transition-ease);
}
.lvr-page .btn-approve {
  border: 1px solid var(--color-success);
  color: #047857;
  background: var(--color-success-bg);
}
.lvr-page .btn-approve:hover {
  background: var(--color-success);
  color: #fff;
}
.lvr-page .btn-reject {
  border: 1px solid var(--color-error);
  color: var(--color-error);
  background: var(--color-error-bg);
}
.lvr-page .btn-reject:hover {
  background: var(--color-error);
  color: #fff;
}
.lvr-page .btn-delete {
  border-radius: var(--radius-base);
  padding: 6px 14px;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  white-space: nowrap;
  border: 1px solid var(--color-error);
  color: var(--color-error);
  background: var(--color-error-bg);
  transition: all var(--transition-base) var(--transition-ease);
}
.lvr-page .btn-delete:hover {
  background: var(--color-error);
  color: #fff;
}
.lvr-page .btn-detail {
  border-radius: var(--radius-base);
  padding: 6px 14px;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  white-space: nowrap;
  border: 1px solid var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-lightest);
  transition: all var(--transition-base) var(--transition-ease);
}
.lvr-page .btn-detail:hover {
  background: var(--color-primary);
  color: #fff;
}

/* 多选框列 */
.lvr-page .select-cell {
  width: 44px;
  text-align: center;
}
.lvr-page .row-check {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--color-primary);
}
.lvr-page .data-table tbody tr.row-selected td {
  background: var(--color-primary-lightest);
}

/* 操作列固定在表格右侧，审批按钮无需横向滚动即可看到 */
.lvr-page .data-table th:last-child,
.lvr-page .data-table td:last-child {
  position: sticky;
  right: 0;
  background: var(--color-bg-container);
  box-shadow: -8px 0 8px -8px rgba(0, 0, 0, .18);
}
.lvr-page .data-table thead th:last-child {
  background: var(--color-bg-spotlight);
  z-index: 3;
}
.lvr-page .data-table tbody td:last-child {
  z-index: 1;
}
.lvr-page .data-table tbody tr:hover td:last-child,
.lvr-page .data-table tbody tr.row-selected td:last-child {
  background: var(--color-primary-lightest);
}
</style>
