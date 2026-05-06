<template>
  <div class="feedback-page">
    <!-- ===== 页面顶部 ===== -->
    <div class="fb-header">
      <div class="fb-header-row">
        <div class="fb-title-block">
          <h1 class="fb-title">💬 意见与建议</h1>
          <p class="fb-subtitle">倾听每一份声音，让工作环境更美好</p>
        </div>
        <div class="fb-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            :class="['fb-tab', { active: currentTab === tab.key }]"
            @click="currentTab = tab.key"
          >{{ tab.label }}</button>
        </div>
      </div>
      <div v-if="currentTab === 'wall'" class="fb-stats">
        <div class="stat-card sc-blue">
          <div class="sc-icon">📊</div>
          <div class="sc-body">
            <span class="sc-value">{{ wallStats.total }}</span>
            <span class="sc-label">总吐槽数</span>
          </div>
        </div>
        <div class="stat-card sc-orange">
          <div class="sc-icon">🔄</div>
          <div class="sc-body">
            <span class="sc-value">{{ wallStats.processing }}</span>
            <span class="sc-label">处理中</span>
            <span class="sc-extra">占比 {{ wallStats.total ? Math.round(wallStats.processing / wallStats.total * 100) : 0 }}%</span>
          </div>
        </div>
        <div class="stat-card sc-green">
          <div class="sc-icon">✅</div>
          <div class="sc-body">
            <span class="sc-value">{{ wallStats.resolved }}</span>
            <span class="sc-label">已解决</span>
            <span class="sc-extra">占比 {{ wallStats.total ? Math.round(wallStats.resolved / wallStats.total * 100) : 0 }}%</span>
          </div>
        </div>
        <div class="stat-card sc-purple">
          <div class="sc-icon">📈</div>
          <div class="sc-body">
            <span class="sc-value">{{ wallStats.thisWeek }}</span>
            <span class="sc-label">本周新增</span>
          </div>
        </div>
      </div>
    </div>

    <div class="tab-content">
      <!-- ========== Tab 1: 吐槽墙 ========== -->
      <div v-if="currentTab === 'wall'" class="wall-section">
        <!-- 筛选工具栏 -->
        <div class="wall-toolbar">
          <div class="tb-left">
            <button
              v-for="opt in wallResolveFilterOptions"
              :key="opt.value"
              :class="['tb-chip', { active: wallFilterResolved === opt.value }]"
              @click="wallFilterResolved = opt.value"
            ><span :class="['chip-dot', `cd-${opt.value}`]"></span>{{ opt.label }}</button>
          </div>
          <div class="tb-right">
            <button :class="['tb-sort', { active: wallSortOrder === 'likes' }]" @click="wallSortOrder = wallSortOrder === 'likes' ? 'desc' : 'likes'">🔥 热度排序</button>
            <button :class="['tb-sort', { active: wallSortOrder === 'desc' }]" @click="wallSortOrder = 'desc'">🕐 最新优先</button>
            <div class="tb-search">
              <input v-model="wallSearchQuery" type="text" placeholder="搜索吐槽内容、关键词" />
              <span class="tb-search-icon">🔍</span>
            </div>
            <button class="tb-icon-btn" @click="loadWall" title="刷新">↻</button>
          </div>
        </div>

        <!-- 吐槽墙主面板 -->
        <div class="wall-stage" ref="stageRef">
          <div class="ws-head">
            <div class="ws-head-text">
              <h2>🗣 吐槽墙</h2>
              <p>匿名吐槽，放心表达</p>
            </div>
          </div>
          <div class="ws-cards">
            <div
              v-for="(card, ci) in displayCards"
              :key="card.id"
              class="wcard"
              :style="{ background: card._bg, '--rot': card._rotate + 'deg' }"
              @click="openDetail(card.id)"
            >
              <span :class="['wcard-badge', `wb-${card.resolved || 0}`]">
                {{ wallResolveLabel(card.resolved) }}
              </span>
              <p class="wcard-body">{{ card.content }}</p>
              <div v-if="card.replies?.length" class="wcard-reply-hint">
                {{ card.replies[card.replies.length - 1].replyBy }} 回复：{{ card.replies[card.replies.length - 1].replyContent.length > 15 ? card.replies[card.replies.length - 1].replyContent.slice(0,15) + '…' : card.replies[card.replies.length - 1].replyContent }}
              </div>
              <img v-if="card.imageUrl" :src="getWallImgSrc(card.imageUrl)" class="wcard-img" />
              <div class="wcard-foot">
                <span class="wcard-avatar">匿</span>
                <span class="wcard-dept">匿名</span>
                <span class="wcard-like" @click.stop="doLike(card.id)">👍 {{ card.likeCount || 0 }}</span>
              </div>
            </div>
          </div>
          <div v-if="!displayCards.length && !wallLoading" class="ws-empty">暂无可展示吐槽</div>
          <div class="ws-deco ws-deco-1"></div>
          <div class="ws-deco ws-deco-2"></div>
        </div>

        <!-- 底部操作按钮 -->
        <div class="wall-bottom">
          <button class="wb-btn wb-primary" @click="showWallInput = true">✏️ 发一条吐槽</button>
          <button class="wb-btn wb-secondary" @click="openAllWallRecords">📋 查看全部记录</button>
          <button v-if="isAdmin1" class="wb-btn wb-outline" @click="openWallReview">
            ⚙️ 审核管理 <span v-if="wallPendingCount" class="badge">{{ wallPendingCount }}</span>
          </button>
        </div>

        <!-- 发布吐槽弹窗 -->
        <div v-if="showWallInput" class="modal-overlay" @click.self="showWallInput = false">
          <div class="modal-content modal-sm">
            <h3>发一条匿名吐槽</h3>
            <textarea v-model="wallDraft" maxlength="200" rows="4" placeholder="说点什么吧…（匿名，最多200字）" class="textarea"></textarea>
            <p class="char-count">{{ wallDraft.length }}/200</p>
            <div class="wall-image-upload">
              <label class="upload-label">
                <input type="file" accept="image/*" @change="onWallImagePick" ref="wallFileRef" hidden />
                <span class="upload-btn">📷 添加图片</span>
              </label>
              <div v-if="wallImagePreview" class="upload-preview">
                <img :src="wallImagePreview" />
                <button class="remove-img" @click="removeWallImage">✕</button>
              </div>
            </div>
            <div class="form-actions">
              <button type="button" @click="showWallInput = false">取消</button>
              <button class="btn-primary" @click="doSubmitWall" :disabled="wallSubmitting">{{ wallSubmitting ? '提交中…' : '提交' }}</button>
            </div>
          </div>
        </div>

        <!-- 审核弹窗 -->
        <div v-if="showWallReview" class="modal-overlay" @click.self="showWallReview = false">
          <div class="modal-content">
            <h3>待审核吐槽</h3>
            <div v-if="!wallPendingList.length" class="empty-hint">暂无待审核内容</div>
            <div v-for="p in wallPendingList" :key="p.id" class="review-card">
              <p class="review-content">{{ p.content }}</p>
              <img v-if="p.imageUrl" :src="getWallImgSrc(p.imageUrl)" class="review-img" />
              <span class="review-time">{{ p.createdAt }}</span>
              <div class="review-actions">
                <button class="btn-sm btn-approve" @click="doReview(p.id, 'approve')">通过</button>
                <button class="btn-sm btn-reject" @click="doReview(p.id, 'reject')">拒绝</button>
              </div>
            </div>
            <div class="form-actions"><button @click="showWallReview = false">关闭</button></div>
          </div>
        </div>

        <!-- 查看全部弹窗 -->
        <div v-if="showAllWall" class="modal-overlay" @click.self="showAllWall = false">
          <div class="modal-content modal-lg">
            <h3>全部吐槽记录 <span class="all-wall-count">{{ filteredWallList.length }} 条</span></h3>
            <div class="all-wall-toolbar">
              <div class="toolbar-filters">
                <button
                  v-for="opt in visibleRecordFilterOptions"
                  :key="String(opt.value)"
                  type="button"
                  :class="['filter-btn', { active: wallRecordFilterActive(opt.value) }]"
                  @click="wallRecordFilter = opt.value"
                >{{ opt.label }}</button>
              </div>
              <div class="toolbar-sort">
                <button :class="['sort-btn', { active: wallSortOrder === 'desc' }]" @click="wallSortOrder = 'desc'">最新</button>
                <button :class="['sort-btn', { active: wallSortOrder === 'asc' }]" @click="wallSortOrder = 'asc'">最早</button>
                <button :class="['sort-btn', { active: wallSortOrder === 'likes' }]" @click="wallSortOrder = 'likes'">最多赞</button>
              </div>
            </div>
            <div v-if="!pagedWallList.length" class="empty-hint">暂无内容</div>
            <div v-for="w in pagedWallList" :key="w.id" class="all-wall-card" @click="openDetail(w.id)">
              <div class="all-wall-main">
                <img v-if="w.imageUrl" :src="getWallImgSrc(w.imageUrl)" class="all-wall-img" />
                <div class="all-wall-text">
                  <p>{{ w.content }}</p>
                  <div v-if="w.replies && w.replies.length" class="all-wall-replies-preview">
                    <span v-for="(rp, ri) in w.replies.slice(0, 2)" :key="ri" class="reply-preview-tag">
                      {{ rp.replyBy }} 回复：{{ rp.replyContent.length > 20 ? rp.replyContent.slice(0, 20) + '…' : rp.replyContent }}
                    </span>
                    <span v-if="w.replies.length > 2" class="reply-preview-more">+{{ w.replies.length - 2 }} 条</span>
                  </div>
                </div>
              </div>
              <div class="all-wall-meta">
                <span class="like-info">👍 {{ w.likeCount || 0 }}</span>
                <span :class="['audit-tag', `audit-${wallStatusNorm(w)}`]">
                  {{ wallStatusLabel(w) }}
                </span>
                <span v-if="wallStatusNorm(w) === 1" :class="['resolve-tag', `resolve-${wallResolvedNorm(w)}`]">
                  {{ wallResolveLabel(w.resolved) }}
                </span>
                <span v-if="wallStatusNorm(w) !== 0 && w.reviewedAt" class="review-info">{{ w.reviewedAt }}</span>
                <span class="time-info">{{ w.createdAt }}</span>
              </div>
            </div>
            <div v-if="wallTotalPages > 1" class="pagination">
              <button :disabled="wallPage <= 1" @click="wallPage--">上一页</button>
              <span class="page-info">{{ wallPage }} / {{ wallTotalPages }}</span>
              <button :disabled="wallPage >= wallTotalPages" @click="wallPage++">下一页</button>
            </div>
            <div class="form-actions"><button @click="showAllWall = false">关闭</button></div>
          </div>
        </div>

        <!-- 详情弹窗（点击弹幕查看） -->
        <div v-if="showDetail" class="modal-overlay" @click.self="showDetail = false">
          <div class="modal-content">
            <h3>吐槽详情</h3>
            <div v-if="detailData" class="detail-body">
              <p class="detail-content">{{ detailData.content }}</p>
              <img v-if="detailData.imageUrl" :src="getWallImgSrc(detailData.imageUrl)" class="detail-img" />
              <div class="detail-meta">
                <span class="like-info" :class="{ liked: detailData.liked }" @click="doLikeDetail">
                  👍 {{ detailData.likeCount || 0 }}
                </span>
                <span v-if="wallStatusNorm(detailData) === 1" :class="['resolve-tag', `resolve-${wallResolvedNorm(detailData)}`]">
                  {{ wallResolveLabel(detailData.resolved) }}
                </span>
                <span :class="['audit-tag', `audit-${wallStatusNorm(detailData)}`]">
                  {{ wallStatusLabel(detailData) }}
                </span>
                <span class="time-info">{{ detailData.createdAt }}</span>
              </div>
              <div v-if="wallStatusNorm(detailData) !== 1" class="review-state-info">
                {{ wallStatusLabel(detailData) }}<span v-if="detailData.reviewedAt">：{{ detailData.reviewedAt }}</span>
              </div>
              <div v-if="detailData.assignee" class="assignee-info">
                负责人：{{ detailData.assignee }}
                <span v-if="detailData.assignedBy">（{{ detailData.assignedBy }} 指派）</span>
              </div>
              <div class="detail-replies">
                <h4>领导回复（{{ detailData.replies?.length || 0 }}）</h4>
                <div v-if="!detailData.replies?.length" class="empty-hint-sm">暂无回复</div>
                <div v-for="rp in detailData.replies" :key="rp.id" class="reply-item">
                  <span class="reply-author">{{ rp.replyBy }}</span>
                  <span class="reply-text">{{ rp.replyContent }}</span>
                  <span class="reply-time">{{ rp.createdAt }}</span>
                </div>
              </div>
              <div v-if="canHandleWallDetail" class="detail-leader-actions">
                <div v-if="isLeader" class="assignee-picker">
                  <label>指定负责人</label>
                  <select v-model="detailAssignee">
                    <option value="">不指定负责人</option>
                    <option v-for="p in assigneeOptions" :key="p.name" :value="p.name">
                      {{ p.name }}{{ p.department ? `（${p.department}）` : '' }}
                    </option>
                  </select>
                </div>
                <div v-if="isLeader" class="detail-reply-form">
                  <textarea
                    ref="detailReplyTextareaRef"
                    v-model="detailReplyDraft"
                    rows="2"
                    placeholder="回复该吐槽…"
                    class="textarea textarea-sm textarea-auto-grow"
                    @input="(e) => fitTextareaHeight(e.target)"
                  ></textarea>
                  <button class="btn-sm btn-primary" @click="doReplyWall" :disabled="detailReplying">回复</button>
                </div>
                <div class="detail-resolve-actions" v-if="detailData.resolved !== 3">
                  <button v-if="detailData.resolved !== 1" class="btn-sm btn-processing" @click="doResolve(1)">标记为处理中</button>
                  <button class="btn-sm btn-resolved" @click="doResolve(3)">标记为已解决</button>
                </div>
                <div v-else class="resolved-badge">✅ 已由 {{ detailData.resolvedBy }} 标记为已解决</div>
              </div>
            </div>
            <div class="form-actions"><button @click="showDetail = false">关闭</button></div>
          </div>
        </div>
      </div>

      <!-- ========== Tab 2: 领导匿名信箱 ========== -->
      <div v-if="currentTab === 'leader'" class="leader-section">
        <!-- 提交区 -->
        <div class="card submit-card">
          <h3>匿名投递意见</h3>
          <div class="form-row">
            <div class="form-group">
              <label>选择领导</label>
              <select v-model="leaderForm.target">
                <option value="">请选择</option>
                <option v-for="l in leaderTargets" :key="l.name" :value="l.name">{{ l.name }}（{{ l.jb }}）</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>意见内容</label>
            <textarea v-model="leaderForm.content" rows="4" placeholder="匿名投递，领导不会看到您的身份" class="textarea"></textarea>
          </div>
          <div class="wall-image-upload">
            <label class="upload-label">
              <input type="file" accept="image/*" @change="onLeaderImagePick" ref="leaderFileRef" hidden />
              <span class="upload-btn">📷 添加图片</span>
            </label>
            <div v-if="leaderImagePreview" class="upload-preview">
              <img :src="leaderImagePreview" />
              <button class="remove-img" @click="removeLeaderImage">✕</button>
            </div>
          </div>
          <div class="form-actions">
            <button class="btn btn-primary" @click="doSubmitLeader" :disabled="leaderSubmitting">{{ leaderSubmitting ? '提交中…' : '匿名提交' }}</button>
          </div>
        </div>

        <!-- 领导信箱（仅领导可见） -->
        <div v-if="isLeader" class="card inbox-card">
          <h3>我的信箱 <span class="badge" v-if="leaderInboxUnread">{{ leaderInboxUnread }}</span></h3>
          <div v-if="!leaderInbox.length" class="empty-hint">暂无匿名意见</div>
          <div v-for="msg in leaderInbox" :key="msg.id" class="inbox-item">
            <div class="inbox-content">{{ msg.content }}</div>
            <img v-if="msg.imageUrl" :src="getLeaderImgSrc(msg.imageUrl)" class="inbox-img" />
            <div class="inbox-time">{{ msg.createdAt }}</div>
            <div v-if="msg.reply" class="inbox-reply">
              <strong>我的回复：</strong>{{ msg.reply }}
            </div>
            <div v-else class="inbox-reply-form">
              <textarea
                v-model="msg._draft"
                rows="2"
                placeholder="回复该意见…"
                class="textarea textarea-sm textarea-auto-grow"
                @input="(e) => fitTextareaHeight(e.target)"
              ></textarea>
              <button class="btn-sm btn-primary" @click="doReplyLeader(msg)" :disabled="msg._replying">回复</button>
            </div>
          </div>
        </div>

        <!-- 公示墙 -->
        <div class="card public-card">
          <h3>已回复公示</h3>
          <div v-if="!leaderPublic.length" class="empty-hint">暂无已回复内容</div>
          <div v-for="item in leaderPublic" :key="item.id" class="public-item">
            <div class="public-leader">{{ item.targetLeader }}</div>
            <div class="public-question">匿名意见：{{ item.content }}</div>
            <img v-if="item.imageUrl" :src="getLeaderImgSrc(item.imageUrl)" class="public-img" />
            <div class="public-answer">领导回复：{{ item.reply }}</div>
            <div class="public-time">{{ item.replyAt }}</div>
          </div>
        </div>
      </div>

      <!-- ========== Tab 3: 系统功能建议 ========== -->
      <div v-if="currentTab === 'system'" class="system-section">
        <div class="card submit-card">
          <h3>提交建议（实名）</h3>
          <div class="form-row">
            <div class="form-group half">
              <label>姓名</label>
              <input type="text" :value="userName" readonly class="readonly-input" />
            </div>
            <div class="form-group half">
              <label>科室</label>
              <input type="text" :value="userDept" readonly class="readonly-input" />
            </div>
          </div>
          <div class="form-group">
            <label>建议内容</label>
            <textarea v-model="systemForm.content" rows="4" placeholder="请描述您功能上的建议或点子，业务上的需求请直接给黄圣轩7480发邮件并抄送智能室主任" class="textarea"></textarea>
          </div>
          <div class="wall-image-upload">
            <label class="upload-label">
              <input type="file" accept="image/*" @change="onSystemImagePick" ref="systemFileRef" hidden />
              <span class="upload-btn">📷 添加图片</span>
            </label>
            <div v-if="systemImagePreview" class="upload-preview">
              <img :src="systemImagePreview" />
              <button class="remove-img" @click="removeSystemImage">✕</button>
            </div>
          </div>
          <div class="form-actions">
            <button class="btn btn-primary" @click="doSubmitSystem" :disabled="systemSubmitting">{{ systemSubmitting ? '提交中…' : '提交建议' }}</button>
          </div>
        </div>

        <div class="card list-card">
          <h3>建议列表</h3>
          <div v-if="!systemList.length" class="empty-hint">暂无建议</div>
          <div v-for="item in systemList" :key="item.id" class="suggestion-item">
            <div class="suggestion-header">
              <span class="suggestion-author">{{ item.submitter }}</span>
              <span class="suggestion-dept" v-if="item.department">{{ item.department }}</span>
              <span class="suggestion-time">{{ item.createdAt }}</span>
              <span :class="['status-tag', item.status === 1 ? 'status-replied' : 'status-pending']">
                {{ item.status === 1 ? '已回复' : '待回复' }}
              </span>
            </div>
            <div class="suggestion-body">{{ item.content }}</div>
            <img v-if="item.imageUrl" :src="getSystemImgSrc(item.imageUrl)" class="suggestion-img" />
            <div v-if="item.reply" class="suggestion-reply">
              <strong>管理员回复：</strong>{{ item.reply }}
              <span class="reply-meta">— {{ item.replyBy }} · {{ item.replyAt }}</span>
            </div>
            <div v-else-if="isAdmin1" class="inbox-reply-form">
              <textarea
                v-model="item._draft"
                rows="2"
                placeholder="回复该建议…"
                class="textarea textarea-sm textarea-auto-grow"
                @input="(e) => fitTextareaHeight(e.target)"
              ></textarea>
              <button class="btn-sm btn-primary" @click="doReplySystem(item)" :disabled="item._replying">回复</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import {
  submitWall, getWallList, getWallRecords, getWallPending, reviewWall,
  likeWall, getWallDetail, replyWall, resolveWall, wallImageUrl, leaderImageUrl,
  getLeaderTargets, submitLeaderMsg, getLeaderInbox, replyLeaderMsg, getLeaderPublic,
  submitSystemFeedback, getSystemList, replySystemFeedback, systemImageUrl
} from '@/api/feedback'
import { getContacts } from '@/api/contacts'
import { refreshWorkplaceTodos } from '@/composables/useWorkplaceTodos'

const route = useRoute()
const tabs = [
  { key: 'wall', label: '部门吐槽墙' },
  { key: 'leader', label: '领导匿名信箱' },
  { key: 'system', label: '系统功能建议' }
]
const validTabs = tabs.map(t => t.key)
const initTab = validTabs.includes(route.query.tab) ? route.query.tab : 'wall'
const currentTab = ref(initTab)

function getUserInfo() {
  try { return JSON.parse(localStorage.getItem('userInfo') || '{}') } catch { return {} }
}
const userInfo = getUserInfo()
const userName = userInfo.name || userInfo.userName || ''
const userDept = userInfo.dept || userInfo.lsys || ''
const userJb = (userInfo.jb || '').trim()

/** 回复框随内容增高，超出约 14 行后出现纵向滚动条 */
function fitTextareaHeight(el, minLines = 2) {
  if (!el || el.tagName !== 'TEXTAREA') return
  const cs = window.getComputedStyle(el)
  const lh = parseFloat(cs.lineHeight)
  const lineHeight = Number.isFinite(lh) && lh > 0 ? lh : parseFloat(cs.fontSize || '14') * 1.45
  const padY = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom)
  const borderY = parseFloat(cs.borderTopWidth) + parseFloat(cs.borderBottomWidth)
  const minH = lineHeight * minLines + padY + borderY
  const maxH = lineHeight * 14 + padY + borderY
  el.style.height = 'auto'
  const next = Math.min(Math.max(el.scrollHeight, minH), maxH)
  el.style.height = `${next}px`
  el.style.overflowY = el.scrollHeight > maxH ? 'auto' : 'hidden'
}

const isAdmin1 = ref(false)
const isLeader = computed(() => {
  const j = userJb
  return /经理助理|副经理|经理|副部长|部长/.test(j) || isAdmin1.value
})
const canViewPrivateWallRecords = computed(() => isLeader.value || isAdmin1.value)

function wallResolveLabel(v) {
  return Number(v) === 3 ? '已解决' : Number(v) === 2 ? '已回复' : Number(v) === 1 ? '处理中' : '未处理'
}

function wallStatusNorm(w) {
  if (typeof w !== 'object' || w === null) {
    const n = Number(w)
    return Number.isFinite(n) ? n : 1
  }
  const raw = w.status
  if (raw !== null && raw !== undefined && raw !== '') {
    const n = Number(raw)
    if (Number.isFinite(n)) return n
  }
  const label = String(w.statusLabel || '').trim()
  if (label.includes('审核')) return 0
  if (label.includes('驳回') || label.includes('拒绝')) return 2
  return 1
}

function wallStatusLabel(w) {
  const n = wallStatusNorm(w)
  return n === 0 ? '正在审核' : n === 2 ? '已驳回' : '已上墙'
}

onMounted(async () => {
  try {
    const { getUploadConfig } = await import('@/api/attendance')
    const res = await getUploadConfig()
    const a1 = (res?.admin1 || '').trim()
    isAdmin1.value = !!(a1 && userName === a1)
  } catch { /* ignore */ }
  await loadWall()
  openRouteWallDetail()
  loadAssigneeOptions()
  loadLeaderTargets()
  loadLeaderPublic()
  loadSystemList()
  if (isLeader.value) loadLeaderInbox()
})

watch(
  () => route.query,
  (q) => {
    if (validTabs.includes(q.tab)) currentTab.value = q.tab
    openRouteWallDetail()
  }
)

// ==================== 吐槽墙 ====================
const stageRef = ref(null)
const wallList = ref([])
const allWallList = ref([])
const wallLoading = ref(false)
const activeBarrages = ref([])
let barrageTimer = null
let barrageUid = 0
const TRACK_COUNT = 7
const COLORS = [
  'rgba(255,107,107,.85)', 'rgba(78,205,196,.85)', 'rgba(255,195,113,.85)',
  'rgba(162,155,254,.85)', 'rgba(95,189,244,.85)', 'rgba(255,154,158,.85)',
  'rgba(128,203,196,.85)', 'rgba(255,183,77,.85)'
]

function getWallImgSrc(filename) {
  return filename ? wallImageUrl(filename) : ''
}

function buildDisplayText(item) {
  let text = item.content
  if (item.replies && item.replies.length) {
    const latest = item.replies[item.replies.length - 1]
    text += ` | ${latest.replyBy} 回复：${latest.replyContent}`
  }
  return text
}

async function loadWall() {
  wallLoading.value = true
  try {
    const res = await getWallList()
    if (res.success) wallList.value = res.data || []
    await loadWallRecords()
  } catch { /* ignore */ }
  wallLoading.value = false
  startBarrageLoop()
}

async function loadWallRecords() {
  try {
    const res = await getWallRecords({ current_user: userName })
    if (res.success) {
      const rows = Array.isArray(res.data) ? res.data : []
      allWallList.value = rows
      wallPendingCount.value = rows.filter(w => wallStatusNorm(w) === 0).length
      return
    }
  } catch (e) {
    console.warn('加载全部吐槽记录失败（将降级为当前上墙列表，不含已解决等）:', e)
  }
  if (!allWallList.value.length && wallList.value.length) {
    allWallList.value = wallList.value.map(w => ({ ...w }))
  }
}

const barragePool = computed(() => wallList.value)

function startBarrageLoop() {
  stopBarrageLoop()
  if (!barragePool.value.length) return
  let idx = 0
  const stageWidth = stageRef.value?.clientWidth || 900
  const launch = () => {
    if (!barragePool.value.length) return
    const item = barragePool.value[idx % barragePool.value.length]
    idx++
    const track = Math.floor(Math.random() * TRACK_COUNT)
    const duration = 12 + Math.random() * 8
    const color = COLORS[Math.floor(Math.random() * COLORS.length)]
    const uid = ++barrageUid
    activeBarrages.value.push({
      _uid: uid,
      _wallId: item.id,
      displayText: buildDisplayText(item),
      imageUrl: item.imageUrl || '',
      likeCount: item.likeCount || 0,
      resolved: item.resolved || 0,
      style: {
        '--sw': `${stageWidth}px`,
        top: `${track * (100 / TRACK_COUNT)}%`,
        animationDuration: `${duration}s`,
        background: color,
        animationDelay: `${Math.random() * 0.5}s`
      }
    })
  }
  launch()
  barrageTimer = setInterval(launch, 2200)
}

function stopBarrageLoop() {
  if (barrageTimer) { clearInterval(barrageTimer); barrageTimer = null }
}

function onBarrageEnd(uid) {
  activeBarrages.value = activeBarrages.value.filter(b => b._uid !== uid)
}

onBeforeUnmount(stopBarrageLoop)

watch(currentTab, (t) => {
  if (t === 'wall') { nextTick(() => startBarrageLoop()) }
  else { stopBarrageLoop() }
})

// -- 发布吐槽 --
const showWallInput = ref(false)
const wallDraft = ref('')
const wallSubmitting = ref(false)
const wallFileRef = ref(null)
const wallImageFile = ref(null)
const wallImagePreview = ref('')

function onWallImagePick(e) {
  const f = e.target.files?.[0]
  if (!f) return
  wallImageFile.value = f
  wallImagePreview.value = URL.createObjectURL(f)
}
function removeWallImage() {
  wallImageFile.value = null
  wallImagePreview.value = ''
  if (wallFileRef.value) wallFileRef.value.value = ''
}

async function doSubmitWall() {
  if (!wallDraft.value.trim()) { alert('请输入内容'); return }
  wallSubmitting.value = true
  try {
    const payload = { content: wallDraft.value.trim() }
    if (wallImageFile.value) payload.image = wallImageFile.value
    const res = await submitWall(payload)
    if (res.success) {
      alert('已提交，待管理员审核')
      wallDraft.value = ''
      removeWallImage()
      showWallInput.value = false
      loadWallRecords()
    } else {
      alert(res.message || '提交失败')
    }
  } catch (e) {
    alert(e.response?.data?.detail || '提交失败')
  }
  wallSubmitting.value = false
}

// -- 审核 --
const showWallReview = ref(false)
const wallPendingList = ref([])
const wallPendingCount = ref(0)

async function openWallReview() {
  try {
    const res = await getWallPending({ current_user: userName })
    if (res.success) wallPendingList.value = res.data || []
    wallPendingCount.value = wallPendingList.value.length
  } catch { /* ignore */ }
  showWallReview.value = true
}

async function doReview(id, action) {
  try {
    const res = await reviewWall(id, { action, current_user: userName })
    if (res.success) {
      wallPendingList.value = wallPendingList.value.filter(p => p.id !== id)
      wallPendingCount.value = wallPendingList.value.length
      await loadWall()
    } else {
      alert(res.message || '操作失败')
    }
  } catch (e) {
    alert(e.response?.data?.detail || '操作失败')
  }
}

// -- 点赞 --
async function doLike(wallId, barrageItem) {
  if (!userName) { alert('请先登录'); return }
  try {
    const res = await likeWall(wallId, { current_user: userName })
    if (res.success) {
      const delta = res.liked ? 1 : -1
      const item = wallList.value.find(w => w.id === wallId)
      if (item) item.likeCount = Math.max((item.likeCount || 0) + delta, 0)
      const record = allWallList.value.find(w => w.id === wallId)
      if (record) record.likeCount = Math.max((record.likeCount || 0) + delta, 0)
      activeBarrages.value.forEach(b => {
        if (b._wallId === wallId) {
          b.likeCount = Math.max((b.likeCount || 0) + delta, 0)
          b._animating = true
          setTimeout(() => { b._animating = false }, 500)
        }
      })
    }
  } catch { /* ignore */ }
}

// -- 查看全部 --
const showAllWall = ref(false)
const wallFilterResolved = ref('all')
const wallRecordFilter = ref('all')
const wallSortOrder = ref('desc')
const wallPage = ref(1)
const WALL_PAGE_SIZE = 8
const wallResolveFilterOptions = [
  { value: 'all', label: '全部' },
  { value: 0, label: '未处理' },
  { value: 1, label: '处理中' },
  { value: 2, label: '已回复' },
]
const recordFilterOptions = [
  { value: 'all', label: '全部记录' },
  { value: 0, label: '未处理' },
  { value: 1, label: '处理中' },
  { value: 2, label: '已回复' },
  { value: 3, label: '已解决' },
]
const visibleRecordFilterOptions = computed(() => {
  const privateFilters = canViewPrivateWallRecords.value
    ? [{ value: 'pending', label: '正在审核' }, { value: 'rejected', label: '已驳回' }]
    : []
  return [recordFilterOptions[0], ...privateFilters, ...recordFilterOptions.slice(1)]
})

/** 与后端 tinyint 一致，避免字符串/undefined 导致筛选恒不匹配 */
function wallResolvedNorm(w) {
  const v = w?.resolved
  if (v === null || v === undefined || v === '') return 0
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

function wallRecordFilterActive(optVal) {
  const rf = wallRecordFilter.value
  if (typeof optVal === 'number') return Number(rf) === optVal
  return rf === optVal
}

const filteredWallList = computed(() => {
  let list = [...allWallList.value]
  const rf = wallRecordFilter.value

  if (!canViewPrivateWallRecords.value) {
    list = list.filter(w => wallStatusNorm(w) === 1)
  }

  if (rf === 'pending') {
    list = list.filter(w => wallStatusNorm(w) === 0)
  } else if (rf === 'rejected') {
    list = list.filter(w => wallStatusNorm(w) === 2)
  } else if (rf !== 'all') {
    const target = Number(rf)
    if (!Number.isNaN(target)) {
      list = list.filter(w => wallStatusNorm(w) === 1 && wallResolvedNorm(w) === target)
    }
  }

  if (wallSortOrder.value === 'asc') {
    list.sort((a, b) => (a.createdAt || '').localeCompare(b.createdAt || ''))
  } else if (wallSortOrder.value === 'likes') {
    list.sort((a, b) => (b.likeCount || 0) - (a.likeCount || 0))
  } else {
    list.sort((a, b) => (b.createdAt || '').localeCompare(a.createdAt || ''))
  }
  return list
})

const wallTotalPages = computed(() => Math.max(1, Math.ceil(filteredWallList.value.length / WALL_PAGE_SIZE)))
const pagedWallList = computed(() => {
  const start = (wallPage.value - 1) * WALL_PAGE_SIZE
  return filteredWallList.value.slice(start, start + WALL_PAGE_SIZE)
})

watch([wallRecordFilter, wallSortOrder], () => { wallPage.value = 1 })

async function openAllWallRecords() {
  await loadWallRecords()
  if (!canViewPrivateWallRecords.value && ['pending', 'rejected'].includes(wallRecordFilter.value)) {
    wallRecordFilter.value = 'all'
  }
  wallPage.value = 1
  showAllWall.value = true
}

// -- 统计数据 --
const wallStats = computed(() => {
  const list = allWallList.value.length ? allWallList.value : wallList.value
  const total = list.length
  const processing = list.filter(w => wallStatusNorm(w) === 1 && wallResolvedNorm(w) === 1).length
  const resolved = list.filter(w => wallStatusNorm(w) === 1 && wallResolvedNorm(w) === 3).length
  const now = new Date()
  const weekAgo = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 7)
  const thisWeek = list.filter(w => w.createdAt && new Date(w.createdAt) >= weekAgo).length
  return { total, processing, resolved, thisWeek }
})

// -- 主面板搜索 & 展示卡片 --
const wallSearchQuery = ref('')
const CARD_BG = [
  'linear-gradient(135deg,#e74c5e,#c62d42)', 'linear-gradient(135deg,#3a7bd5,#2b5ea7)',
  'linear-gradient(135deg,#43a047,#2e7d32)', 'linear-gradient(135deg,#f4a62a,#e88d1a)',
  'linear-gradient(135deg,#8e44ad,#6c3483)', 'linear-gradient(135deg,#00acc1,#00838f)',
  'linear-gradient(135deg,#e8573a,#c0392b)', 'linear-gradient(135deg,#7c4dff,#651fff)',
]
const CARD_ROT = [-2, 1.5, -1, 2, -1.5, 1, -0.5, 1.8]

const displayCards = computed(() => {
  // 公开列表由接口控制：已解决仅保留 resolved_at 起算若干天内
  let list = wallList.value.filter(w => wallStatusNorm(w) === 1)
  if (wallFilterResolved.value !== 'all') {
    list = list.filter(w => wallResolvedNorm(w) === wallFilterResolved.value)
  }
  if (wallSearchQuery.value.trim()) {
    const q = wallSearchQuery.value.trim().toLowerCase()
    list = list.filter(w => (w.content || '').toLowerCase().includes(q))
  }
  if (wallSortOrder.value === 'likes') {
    list.sort((a, b) => (b.likeCount || 0) - (a.likeCount || 0))
  } else if (wallSortOrder.value === 'asc') {
    list.sort((a, b) => (a.createdAt || '').localeCompare(b.createdAt || ''))
  }
  return list.slice(0, 8).map((w, i) => ({
    ...w,
    _bg: CARD_BG[i % CARD_BG.length],
    _rotate: CARD_ROT[i % CARD_ROT.length],
  }))
})

// -- 详情弹窗 --
const showDetail = ref(false)
const detailData = ref(null)
const detailReplyDraft = ref('')
const detailReplyTextareaRef = ref(null)
const detailReplying = ref(false)
const detailAssignee = ref('')
const assigneeOptions = ref([])
const canHandleWallDetail = computed(() => wallStatusNorm(detailData.value) === 1 && (isLeader.value || detailData.value?.assignee === userName))
let openedRouteWallId = ''

async function loadAssigneeOptions() {
  try {
    const res = await getContacts()
    const members = (res?.departments || []).flatMap(d =>
      (d.members || []).map(m => ({ ...m, department: m.department || d.name || '' }))
    )
    const seen = new Set()
    assigneeOptions.value = members.filter((m) => {
      const name = (m.name || '').trim()
      if (!name || seen.has(name)) return false
      seen.add(name)
      return true
    })
  } catch {
    assigneeOptions.value = []
  }
}

function openRouteWallDetail() {
  const wallId = String(route.query.wallId || '').trim()
  if (!wallId || openedRouteWallId === wallId) return
  openedRouteWallId = wallId
  currentTab.value = 'wall'
  nextTick(() => openDetail(wallId))
}

async function openDetail(wallId) {
  try {
    const res = await getWallDetail(wallId, { current_user: userName })
    if (res.success) {
      detailData.value = res.data
      detailAssignee.value = res.data?.assignee || ''
      showDetail.value = true
      await nextTick()
      if (detailReplyTextareaRef.value) fitTextareaHeight(detailReplyTextareaRef.value)
    }
  } catch { /* ignore */ }
}

async function doLikeDetail() {
  if (!detailData.value || !userName || wallStatusNorm(detailData.value) !== 1) return
  try {
    const res = await likeWall(detailData.value.id, { current_user: userName })
    if (res.success) {
      detailData.value.liked = res.liked
      detailData.value.likeCount = (detailData.value.likeCount || 0) + (res.liked ? 1 : -1)
      const item = wallList.value.find(w => w.id === detailData.value.id)
      if (item) item.likeCount = detailData.value.likeCount
      const record = allWallList.value.find(w => w.id === detailData.value.id)
      if (record) record.likeCount = detailData.value.likeCount
    }
  } catch { /* ignore */ }
}

async function doReplyWall() {
  if (!detailData.value || !detailReplyDraft.value.trim()) { alert('请输入回复内容'); return }
  detailReplying.value = true
  try {
    const res = await replyWall(detailData.value.id, {
      reply_content: detailReplyDraft.value.trim(),
      current_user: userName,
      assignee: detailAssignee.value || ''
    })
    if (res.success) {
      detailReplyDraft.value = ''
      await nextTick()
      if (detailReplyTextareaRef.value) fitTextareaHeight(detailReplyTextareaRef.value)
      const fresh = await getWallDetail(detailData.value.id, { current_user: userName })
      if (fresh.success) {
        detailData.value = fresh.data
        detailAssignee.value = fresh.data?.assignee || ''
      }
      loadWall()
      loadWallRecords()
      refreshWorkplaceTodos()
    } else {
      alert(res.message || '回复失败')
    }
  } catch (e) {
    alert(e.response?.data?.detail || '回复失败')
  }
  detailReplying.value = false
}

async function doResolve(level) {
  if (!detailData.value) return
  try {
    const res = await resolveWall(detailData.value.id, { resolved: level, current_user: userName })
    if (res.success) {
      detailData.value.resolved = level
      detailData.value.resolvedBy = userName
      const item = wallList.value.find(w => w.id === detailData.value.id)
      if (item) {
        item.resolved = level
        item.resolvedBy = userName
      }
      const record = allWallList.value.find(w => w.id === detailData.value.id)
      if (record) {
        record.resolved = level
        record.resolvedBy = userName
      }
      if (level === 3) loadWall()
      refreshWorkplaceTodos()
    }
  } catch (e) {
    alert(e.response?.data?.detail || '操作失败')
  }
}

// ==================== 领导匿名信箱 ====================
const leaderTargets = ref([])
const leaderForm = reactive({ target: '', content: '' })
const leaderSubmitting = ref(false)
const leaderInbox = ref([])
const leaderPublic = ref([])
const leaderInboxUnread = computed(() => leaderInbox.value.filter(m => m.status === 0).length)

const leaderFileRef = ref(null)
const leaderImageFile = ref(null)
const leaderImagePreview = ref('')

function getLeaderImgSrc(filename) {
  return filename ? leaderImageUrl(filename) : ''
}
function onLeaderImagePick(e) {
  const f = e.target.files?.[0]
  if (!f) return
  leaderImageFile.value = f
  leaderImagePreview.value = URL.createObjectURL(f)
}
function removeLeaderImage() {
  leaderImageFile.value = null
  leaderImagePreview.value = ''
  if (leaderFileRef.value) leaderFileRef.value.value = ''
}

async function loadLeaderTargets() {
  try {
    const res = await getLeaderTargets()
    if (res.success) leaderTargets.value = res.data || []
  } catch { /* ignore */ }
}

async function doSubmitLeader() {
  if (!leaderForm.target) { alert('请选择目标领导'); return }
  if (!leaderForm.content.trim()) { alert('请输入内容'); return }
  leaderSubmitting.value = true
  try {
    const payload = { target_leader: leaderForm.target, content: leaderForm.content.trim() }
    if (leaderImageFile.value) payload.image = leaderImageFile.value
    const res = await submitLeaderMsg(payload)
    if (res.success) {
      alert('已匿名提交')
      leaderForm.target = ''
      leaderForm.content = ''
      removeLeaderImage()
    } else {
      alert(res.message || '提交失败')
    }
  } catch (e) {
    alert(e.response?.data?.detail || '提交失败')
  }
  leaderSubmitting.value = false
}

async function loadLeaderInbox() {
  try {
    const res = await getLeaderInbox({ current_user: userName })
    if (res.success) {
      leaderInbox.value = (res.data || []).map(m => ({ ...m, _draft: '', _replying: false }))
    }
  } catch { /* ignore */ }
}

async function doReplyLeader(msg) {
  if (!(msg._draft || '').trim()) { alert('请输入回复内容'); return }
  msg._replying = true
  try {
    const res = await replyLeaderMsg(msg.id, { reply: msg._draft.trim(), current_user: userName })
    if (res.success) {
      msg.reply = msg._draft.trim()
      msg.status = 1
      msg._draft = ''
      loadLeaderPublic()
    } else {
      alert(res.message || '回复失败')
    }
  } catch (e) {
    alert(e.response?.data?.detail || '回复失败')
  }
  msg._replying = false
}

async function loadLeaderPublic() {
  try {
    const res = await getLeaderPublic()
    if (res.success) leaderPublic.value = res.data || []
  } catch { /* ignore */ }
}

// ==================== 系统功能建议 ====================
const systemForm = reactive({ content: '' })
const systemSubmitting = ref(false)
const systemList = ref([])

const systemFileRef = ref(null)
const systemImageFile = ref(null)
const systemImagePreview = ref('')

function getSystemImgSrc(filename) {
  return filename ? systemImageUrl(filename) : ''
}
function onSystemImagePick(e) {
  const f = e.target.files?.[0]
  if (!f) return
  systemImageFile.value = f
  systemImagePreview.value = URL.createObjectURL(f)
}
function removeSystemImage() {
  systemImageFile.value = null
  systemImagePreview.value = ''
  if (systemFileRef.value) systemFileRef.value.value = ''
}

async function loadSystemList() {
  try {
    const res = await getSystemList()
    if (res.success) {
      systemList.value = (res.data || []).map(s => ({ ...s, _draft: '', _replying: false }))
    }
  } catch { /* ignore */ }
}

async function doSubmitSystem() {
  if (!systemForm.content.trim()) { alert('请输入内容'); return }
  systemSubmitting.value = true
  try {
    const payload = { submitter: userName, department: userDept, content: systemForm.content.trim() }
    if (systemImageFile.value) payload.image = systemImageFile.value
    const res = await submitSystemFeedback(payload)
    if (res.success) {
      alert('建议已提交')
      systemForm.content = ''
      removeSystemImage()
      loadSystemList()
    } else {
      alert(res.message || '提交失败')
    }
  } catch (e) {
    alert(e.response?.data?.detail || '提交失败')
  }
  systemSubmitting.value = false
}

async function doReplySystem(item) {
  if (!(item._draft || '').trim()) { alert('请输入回复内容'); return }
  item._replying = true
  try {
    const res = await replySystemFeedback(item.id, { reply: item._draft.trim(), current_user: userName })
    if (res.success) {
      item.reply = item._draft.trim()
      item.replyBy = userName
      item.status = 1
      item._draft = ''
    } else {
      alert(res.message || '回复失败')
    }
  } catch (e) {
    alert(e.response?.data?.detail || '回复失败')
  }
  item._replying = false
}
</script>

<style scoped>
/* ==========================================
   OA 意见与建议 — 现代企业风格
   ========================================== */

/* --- 页面布局 --- */
.feedback-page {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  background: #f0f2f5;
  padding: 24px 28px;
  gap: 20px;
}
.tab-content { flex: 1; }

/* --- 页面头部 --- */
.fb-header {
  background: #fff;
  border-radius: 16px;
  padding: 24px 28px 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.fb-header-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
}
.fb-title {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0;
}
.fb-subtitle {
  font-size: 13px;
  color: #9ca3af;
  margin: 4px 0 0;
}

/* --- 标签页 --- */
.fb-tabs { display: flex; gap: 6px; }
.fb-tab {
  padding: 8px 20px;
  border: none;
  border-radius: 20px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 14px;
  cursor: pointer;
  transition: all .2s;
  font-weight: 500;
}
.fb-tab:hover { background: #e5e7eb; }
.fb-tab.active {
  background: linear-gradient(135deg, #3a5cc1, #5c6bc0);
  color: #fff;
  box-shadow: 0 2px 8px rgba(58,92,193,.3);
}

/* --- 统计卡片 --- */
.fb-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-top: 18px;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #e5e7eb;
  transition: transform .2s, box-shadow .2s;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,.08);
}
.sc-icon {
  width: 42px; height: 42px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
}
.sc-blue .sc-icon  { background: #e8eef8; }
.sc-orange .sc-icon { background: #fef3e2; }
.sc-green .sc-icon  { background: #e6f4e8; }
.sc-purple .sc-icon { background: #ede7f6; }
.sc-body { display: flex; flex-direction: column; }
.sc-value { font-size: 24px; font-weight: 700; line-height: 1.1; }
.sc-blue .sc-value   { color: #3a7bd5; }
.sc-orange .sc-value  { color: #f4a62a; }
.sc-green .sc-value   { color: #43a047; }
.sc-purple .sc-value  { color: #7c4dff; }
.sc-label { font-size: 12px; color: #9ca3af; margin-top: 2px; }
.sc-extra { font-size: 11px; color: #b0b8c4; }

/* --- 吐槽墙区域 --- */
.wall-section { display: flex; flex-direction: column; gap: 16px; }

/* --- 筛选工具栏 --- */
.wall-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  background: #fff;
  padding: 12px 18px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,.05);
}
.tb-left { display: flex; gap: 6px; flex-wrap: wrap; }
.tb-right { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.tb-chip {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 6px 14px;
  border: 1px solid #e5e7eb; border-radius: 16px;
  background: #fff; font-size: 13px; color: #6b7280;
  cursor: pointer; transition: all .2s;
}
.tb-chip:hover { border-color: #c7ccd5; background: #f9fafb; }
.tb-chip.active {
  background: #eef2ff; border-color: #3a5cc1;
  color: #3a5cc1; font-weight: 600;
}
.chip-dot {
  width: 7px; height: 7px; border-radius: 50%;
  display: inline-block;
}
.cd-all { background: #9ca3af; }
.cd-0   { background: #ef5350; }
.cd-1   { background: #ffa726; }
.cd-2   { background: #4096ff; }
.cd-3   { background: #66bb6a; }
.tb-chip.active .cd-all { background: #3a5cc1; }
.tb-sort {
  padding: 6px 14px;
  border: 1px solid #e5e7eb; border-radius: 16px;
  background: #fff; font-size: 13px; color: #6b7280;
  cursor: pointer; transition: all .2s;
}
.tb-sort:hover { border-color: #c7ccd5; }
.tb-sort.active {
  background: #eef2ff; border-color: #3a5cc1;
  color: #3a5cc1; font-weight: 600;
}
.tb-search { position: relative; display: flex; align-items: center; }
.tb-search input {
  width: 200px; padding: 7px 32px 7px 12px;
  border: 1px solid #e5e7eb; border-radius: 16px;
  font-size: 13px; outline: none; transition: border-color .2s;
}
.tb-search input:focus { border-color: #3a5cc1; }
.tb-search-icon {
  position: absolute; right: 10px;
  font-size: 13px; pointer-events: none; opacity: .5;
}
.tb-icon-btn {
  width: 34px; height: 34px;
  border: 1px solid #e5e7eb; border-radius: 50%;
  background: #fff; font-size: 16px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: all .2s;
}
.tb-icon-btn:hover { background: #f3f4f6; transform: rotate(90deg); }

/* --- 吐槽墙主面板（深色面板） --- */
.wall-stage {
  position: relative;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border-radius: 16px;
  padding: 28px 24px 32px;
  min-height: 440px;
  overflow: hidden;
}
.ws-head { margin-bottom: 20px; position: relative; z-index: 2; }
.ws-head-text h2 { font-size: 20px; font-weight: 700; color: #fff; margin: 0; }
.ws-head-text p  { font-size: 13px; color: rgba(255,255,255,.5); margin: 4px 0 0; }

/* 漂浮卡片网格 */
.ws-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 18px;
  position: relative;
  z-index: 2;
}
.wcard {
  border-radius: 14px;
  padding: 16px;
  color: #fff;
  cursor: pointer;
  transform: rotate(var(--rot, 0deg));
  transition: transform .25s, box-shadow .25s;
  box-shadow: 0 4px 16px rgba(0,0,0,.25);
  display: flex; flex-direction: column; gap: 8px;
  backdrop-filter: blur(4px);
  position: relative;
  overflow: hidden;
}
.wcard::before {
  content: '';
  position: absolute; inset: 0;
  background: rgba(255,255,255,.06);
  border-radius: 14px;
  pointer-events: none;
}
.wcard:hover {
  transform: rotate(0deg) translateY(-4px) scale(1.03);
  box-shadow: 0 8px 28px rgba(0,0,0,.35);
  z-index: 3;
}
.wcard-badge {
  display: inline-block;
  padding: 2px 8px; border-radius: 8px;
  font-size: 11px; font-weight: 600; width: fit-content;
}
.wb-0 { background: #fff1f0; color: #cf1322; }
.wb-1 { background: #fff7e6; color: #d46b08; }
.wb-2 { background: #e6f4ff; color: #1677ff; }
.wb-3 { background: #e6f7e9; color: #389e0d; }
.wcard-body {
  font-size: 14px; line-height: 1.5; margin: 0; opacity: .95;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.wcard-reply-hint {
  font-size: 11px; opacity: .7;
  padding: 4px 8px;
  background: rgba(255,255,255,.1); border-radius: 6px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.wcard-img {
  width: 48px; height: 48px;
  object-fit: cover; border-radius: 8px;
  border: 2px solid rgba(255,255,255,.2);
}
.wcard-foot {
  display: flex; align-items: center; gap: 8px;
  margin-top: auto; padding-top: 6px;
}
.wcard-avatar {
  width: 26px; height: 26px; border-radius: 50%;
  background: rgba(255,255,255,.2);
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600;
}
.wcard-dept { font-size: 12px; opacity: .7; flex: 1; }
.wcard-like {
  font-size: 12px; opacity: .8;
  cursor: pointer; padding: 2px 6px; border-radius: 8px;
  transition: all .2s;
}
.wcard-like:hover { background: rgba(255,255,255,.15); opacity: 1; }

.ws-empty {
  text-align: center;
  color: rgba(255,255,255,.4);
  font-size: 15px; padding: 60px 0;
  position: relative; z-index: 2;
}
.ws-deco {
  position: absolute; border-radius: 50%;
  pointer-events: none; z-index: 1;
}
.ws-deco-1 {
  width: 200px; height: 200px;
  background: radial-gradient(circle, rgba(58,92,193,.15), transparent 70%);
  top: -60px; right: -40px;
}
.ws-deco-2 {
  width: 150px; height: 150px;
  background: radial-gradient(circle, rgba(124,77,255,.1), transparent 70%);
  bottom: -30px; left: 20px;
}

/* --- 底部操作按钮 --- */
.wall-bottom {
  display: flex; justify-content: center; gap: 12px; padding: 4px 0;
}
.wb-btn {
  padding: 10px 24px; border-radius: 20px;
  font-size: 14px; font-weight: 500;
  cursor: pointer; transition: all .2s;
  border: none;
  display: inline-flex; align-items: center; gap: 4px;
}
.wb-primary {
  background: linear-gradient(135deg, #3a5cc1, #5c6bc0);
  color: #fff;
  box-shadow: 0 3px 10px rgba(58,92,193,.3);
}
.wb-primary:hover { box-shadow: 0 5px 16px rgba(58,92,193,.4); transform: translateY(-1px); }
.wb-secondary {
  background: #fff; color: #3a5cc1;
  border: 1px solid #d0d7e3;
}
.wb-secondary:hover { background: #f7f8fc; border-color: #3a5cc1; }
.wb-outline {
  background: transparent; color: #6b7280;
  border: 1px solid #d0d7e3;
}
.wb-outline:hover { background: #f3f4f6; }
.badge {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 18px; height: 18px; border-radius: 9px;
  background: #ef5350; color: #fff;
  font-size: 11px; font-weight: 600;
  padding: 0 4px; margin-left: 4px;
}

/* --- 弹窗系统 --- */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.45);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}
.modal-content {
  background: #fff; border-radius: 16px;
  padding: 24px 28px;
  width: 520px; max-width: 90vw; max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 8px 30px rgba(0,0,0,.15);
  animation: modalIn .2s ease;
}
.modal-sm { width: 420px; }
.modal-lg { width: 680px; max-height: 88vh; }
@keyframes modalIn {
  from { transform: translateY(12px); opacity: 0; }
  to   { transform: translateY(0); opacity: 1; }
}
.modal-content h3 {
  font-size: 17px; font-weight: 600;
  color: #1a1a2e; margin: 0 0 16px;
}

/* --- 表单元素 --- */
.form-group { margin-bottom: 14px; }
.form-group label {
  display: block; font-size: 13px; font-weight: 500;
  color: #374151; margin-bottom: 5px;
}
.form-group select,
.form-group input[type="text"] {
  width: 100%; padding: 8px 12px;
  border: 1px solid #d1d5db; border-radius: 8px;
  font-size: 14px; outline: none; transition: border-color .2s;
  box-sizing: border-box;
}
.form-group select:focus,
.form-group input[type="text"]:focus { border-color: #3a5cc1; }
.form-row { display: flex; gap: 16px; }
.form-group.half { flex: 1; }
.form-actions {
  display: flex; justify-content: flex-end;
  gap: 10px; margin-top: 14px;
}
.form-actions button {
  padding: 8px 20px; border-radius: 8px;
  font-size: 14px; cursor: pointer;
  border: 1px solid #d1d5db;
  background: #fff; color: #374151;
  transition: all .2s;
}
.form-actions button:hover { background: #f9fafb; }
.form-actions .btn-primary {
  background: linear-gradient(135deg, #3a5cc1, #5c6bc0);
  color: #fff; border: none;
}
.form-actions .btn-primary:hover { opacity: .9; }
.form-actions .btn-primary:disabled { opacity: .5; cursor: not-allowed; }

.textarea {
  width: 100%; padding: 10px 14px;
  border: 1px solid #d1d5db; border-radius: 10px;
  font-size: 14px; resize: vertical; outline: none;
  transition: border-color .2s;
  box-sizing: border-box; font-family: inherit;
}
.textarea:focus { border-color: #3a5cc1; }
.textarea-sm { font-size: 13px; padding: 8px 10px; }
.textarea.textarea-auto-grow {
  resize: none;
  min-height: 3.25em;
  max-height: none;
}
.char-count {
  text-align: right; font-size: 12px;
  color: #9ca3af; margin: 4px 0 8px;
}
.readonly-input {
  width: 100%; padding: 8px 12px;
  border: 1px solid #e5e7eb; border-radius: 8px;
  font-size: 14px; background: #f9fafb; color: #6b7280;
  box-sizing: border-box;
}
.empty-hint {
  text-align: center; color: #9ca3af;
  padding: 24px 0; font-size: 14px;
}
.empty-hint-sm { color: #9ca3af; font-size: 13px; padding: 8px 0; }

/* --- 按钮 --- */
.btn {
  padding: 8px 20px; border-radius: 8px;
  font-size: 14px; cursor: pointer;
  border: 1px solid #d1d5db;
  background: #fff; color: #374151; transition: all .2s;
}
.btn:hover { background: #f3f4f6; }
.btn-primary, .btn.btn-primary {
  background: linear-gradient(135deg, #3a5cc1, #5c6bc0);
  color: #fff; border: none;
}
.btn-primary:hover { opacity: .9; }
.btn-primary:disabled { opacity: .5; cursor: not-allowed; }
.btn-outline, .btn.btn-outline {
  background: #fff; color: #3a5cc1;
  border: 1px solid #c7ccd5;
}
.btn-outline:hover { border-color: #3a5cc1; }
.btn-sm {
  padding: 5px 14px; border-radius: 6px;
  font-size: 13px; cursor: pointer;
  border: 1px solid #d1d5db;
  background: #fff; color: #374151; transition: all .2s;
}
.btn-sm.btn-primary {
  background: linear-gradient(135deg, #3a5cc1, #5c6bc0);
  color: #fff; border: none;
}
.btn-sm.btn-primary:disabled { opacity: .5; cursor: not-allowed; }
.btn-approve { background: #e6f4e8; color: #2e7d32; border-color: #a5d6a7; }
.btn-approve:hover { background: #c8e6c9; }
.btn-reject { background: #fce4e4; color: #c62828; border-color: #ef9a9a; }
.btn-reject:hover { background: #ffcdd2; }

/* --- 图片上传 --- */
.wall-image-upload { margin-top: 10px; }
.upload-label { display: inline-block; cursor: pointer; }
.upload-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 6px 14px; border-radius: 8px;
  background: #f3f4f6; font-size: 13px; color: #6b7280;
  transition: all .2s; border: 1px dashed #d1d5db;
}
.upload-btn:hover { background: #e5e7eb; border-color: #9ca3af; }
.upload-preview {
  display: inline-flex; align-items: flex-start;
  gap: 8px; margin-top: 8px; position: relative;
}
.upload-preview img {
  width: 80px; height: 80px;
  object-fit: cover; border-radius: 8px;
  border: 1px solid #e5e7eb;
}
.remove-img {
  position: absolute; top: -6px; right: -6px;
  width: 22px; height: 22px; border-radius: 50%;
  background: #ef5350; color: #fff; border: none;
  font-size: 12px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: opacity .2s;
}
.remove-img:hover { opacity: .8; }

/* --- 审核卡片 --- */
.review-card {
  padding: 14px;
  border: 1px solid #e5e7eb; border-radius: 10px;
  margin-bottom: 10px; transition: box-shadow .2s;
}
.review-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,.06); }
.review-content { font-size: 14px; color: #1a1a2e; margin-bottom: 6px; }
.review-img {
  display: block; max-width: 120px;
  border-radius: 6px; margin: 6px 0;
}
.review-time { font-size: 12px; color: #9ca3af; }
.review-actions { display: flex; gap: 8px; margin-top: 8px; }

/* --- 查看全部弹窗 --- */
.all-wall-count {
  font-size: 13px; font-weight: 400;
  color: #9ca3af; margin-left: 8px;
}
.all-wall-toolbar {
  display: flex; justify-content: space-between;
  align-items: center; flex-wrap: wrap; gap: 8px;
  margin-bottom: 14px; padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}
.toolbar-filters { display: flex; gap: 6px; }
.filter-btn {
  padding: 4px 12px; border-radius: 12px;
  border: 1px solid #e5e7eb; background: #fff;
  font-size: 12px; color: #6b7280;
  cursor: pointer; transition: all .2s;
}
.filter-btn.active {
  background: #eef2ff; color: #3a5cc1;
  border-color: #3a5cc1; font-weight: 600;
}
.toolbar-sort { display: flex; gap: 4px; }
.sort-btn {
  padding: 4px 10px; border-radius: 10px;
  border: 1px solid #e5e7eb; background: #fff;
  font-size: 12px; color: #6b7280;
  cursor: pointer; transition: all .2s;
}
.sort-btn.active {
  background: #eef2ff; color: #3a5cc1;
  border-color: #3a5cc1;
}
.all-wall-card {
  display: flex; flex-direction: column;
  padding: 14px;
  border: 1px solid #e5e7eb; border-radius: 10px;
  margin-bottom: 10px; cursor: pointer;
  transition: all .2s;
}
.all-wall-card:hover {
  border-color: #c7ccd5;
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
}
.all-wall-main { display: flex; gap: 12px; }
.all-wall-img {
  width: 60px; height: 60px;
  object-fit: cover; border-radius: 8px;
  flex-shrink: 0;
}
.all-wall-text { flex: 1; min-width: 0; }
.all-wall-text p {
  font-size: 14px; color: #1a1a2e;
  margin: 0 0 6px; line-height: 1.5;
  word-break: break-all;
}
.all-wall-replies-preview {
  display: flex; flex-wrap: wrap; gap: 6px;
}
.reply-preview-tag {
  display: inline-block;
  padding: 2px 8px; background: #f0f5ff;
  border-radius: 6px; font-size: 11px; color: #3a5cc1;
  max-width: 280px; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap;
}
.reply-preview-more { font-size: 11px; color: #9ca3af; }
.all-wall-meta {
  display: flex; align-items: center; gap: 12px;
  margin-top: 10px; padding-top: 8px;
  border-top: 1px solid #f5f5f5;
}
.review-info {
  font-size: 12px;
  color: #9ca3af;
}
.like-info {
  font-size: 13px; cursor: pointer;
  color: #6b7280; transition: color .2s;
}
.like-info.liked, .like-info:hover { color: #3a5cc1; }
.time-info { font-size: 12px; color: #9ca3af; margin-left: auto; }
.resolve-tag {
  padding: 2px 8px; border-radius: 6px;
  font-size: 11px; font-weight: 500;
}
.resolve-tag.resolve-0 { background: #fff1f0; color: #cf1322; }
.resolve-tag.resolve-1 { background: #fff7e6; color: #d46b08; }
.resolve-tag.resolve-2 { background: #e6f4ff; color: #1677ff; }
.resolve-tag.resolve-3 { background: #e6f7e9; color: #389e0d; }
.audit-tag {
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
}
.audit-tag.audit-0 { background: #fff7e6; color: #d46b08; }
.audit-tag.audit-1 { background: #eef2ff; color: #3a5cc1; }
.audit-tag.audit-2 { background: #fff1f0; color: #cf1322; }
.pagination {
  display: flex; align-items: center; justify-content: center;
  gap: 12px; padding: 12px 0 4px;
}
.pagination button {
  padding: 5px 14px;
  border: 1px solid #d1d5db; border-radius: 6px;
  background: #fff; font-size: 13px;
  cursor: pointer; transition: all .2s;
}
.pagination button:disabled { opacity: .4; cursor: not-allowed; }
.pagination button:not(:disabled):hover { background: #f3f4f6; }
.page-info { font-size: 13px; color: #6b7280; }

/* --- 详情弹窗 --- */
.detail-body { display: flex; flex-direction: column; gap: 12px; }
.detail-content {
  font-size: 15px; color: #1a1a2e;
  line-height: 1.6; word-break: break-all;
}
.detail-img { max-width: 240px; border-radius: 8px; }
.detail-meta {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}
.assignee-info {
  padding: 8px 10px;
  border-radius: 8px;
  background: #f0f5ff;
  color: #3a5cc1;
  font-size: 13px;
}
.review-state-info {
  padding: 8px 10px;
  border-radius: 8px;
  background: #f9fafb;
  color: #6b7280;
  font-size: 13px;
}
.detail-replies { padding-top: 8px; }
.detail-replies h4 {
  font-size: 14px; font-weight: 600;
  color: #374151; margin: 0 0 8px;
}
.reply-item {
  padding: 8px 12px;
  background: #f9fafb; border-radius: 8px;
  margin-bottom: 6px; font-size: 13px;
}
.reply-author {
  font-weight: 600; color: #3a5cc1; margin-right: 6px;
}
.reply-author::after { content: '：'; }
.reply-text { color: #374151; }
.reply-time {
  display: block; font-size: 11px;
  color: #9ca3af; margin-top: 3px;
}
.detail-leader-actions {
  padding-top: 10px;
  border-top: 1px solid #f0f0f0;
  display: flex; flex-direction: column; gap: 10px;
}
.detail-reply-form {
  display: flex; gap: 8px; align-items: flex-start;
}
.detail-reply-form .textarea { flex: 1; }
.assignee-picker {
  display: flex;
  align-items: center;
  gap: 8px;
}
.assignee-picker label {
  font-size: 13px;
  color: #374151;
  flex-shrink: 0;
}
.assignee-picker select {
  flex: 1;
  min-width: 0;
  padding: 7px 10px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 13px;
  outline: none;
}
.assignee-picker select:focus { border-color: #3a5cc1; }
.detail-resolve-actions { display: flex; gap: 8px; }
.btn-processing, .btn-sm.btn-processing {
  background: #fff7e6; color: #d46b08; border-color: #ffd591;
}
.btn-processing:hover { background: #ffe7ba; }
.btn-resolved, .btn-sm.btn-resolved {
  background: #e6f7e9; color: #389e0d; border-color: #b7eb8f;
}
.btn-resolved:hover { background: #d1f2d8; }
.resolved-badge { font-size: 13px; color: #389e0d; padding: 8px 0; }

/* --- 通用卡片（领导 & 系统） --- */
.card {
  background: #fff; border-radius: 14px;
  padding: 22px 24px; margin-bottom: 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.card h3 {
  font-size: 16px; font-weight: 600;
  color: #1a1a2e; margin: 0 0 14px;
}

/* --- 领导信箱 --- */
.leader-section { display: flex; flex-direction: column; gap: 0; }
.inbox-item {
  padding: 14px 0;
  border-bottom: 1px solid #f0f0f0;
}
.inbox-item:last-child { border-bottom: none; }
.inbox-content {
  font-size: 14px; color: #1a1a2e;
  margin-bottom: 6px; line-height: 1.5;
}
.inbox-img {
  display: block; max-width: 120px;
  border-radius: 6px; margin-bottom: 6px;
}
.inbox-time { font-size: 12px; color: #9ca3af; }
.inbox-reply {
  margin-top: 8px; padding: 10px 12px;
  background: #f0f5ff; border-radius: 8px;
  font-size: 13px; color: #374151;
}
.inbox-reply-form {
  display: flex; gap: 8px;
  align-items: flex-start; margin-top: 8px;
}
.inbox-reply-form .textarea { flex: 1; }
.public-item {
  padding: 14px 0;
  border-bottom: 1px solid #f0f0f0;
}
.public-item:last-child { border-bottom: none; }
.public-leader {
  font-weight: 600; color: #3a5cc1;
  font-size: 14px; margin-bottom: 4px;
}
.public-question { font-size: 14px; color: #6b7280; margin-bottom: 4px; }
.public-img {
  display: block; max-width: 120px;
  border-radius: 6px; margin-bottom: 4px;
}
.public-answer { font-size: 14px; color: #1a1a2e; margin-bottom: 4px; }
.public-time { font-size: 12px; color: #9ca3af; }

/* --- 系统建议 --- */
.system-section { display: flex; flex-direction: column; gap: 0; }
.suggestion-item {
  padding: 14px 0;
  border-bottom: 1px solid #f0f0f0;
}
.suggestion-item:last-child { border-bottom: none; }
.suggestion-header {
  display: flex; align-items: center;
  gap: 10px; flex-wrap: wrap; margin-bottom: 6px;
}
.suggestion-author { font-weight: 600; color: #1a1a2e; font-size: 14px; }
.suggestion-dept {
  font-size: 12px; padding: 2px 8px;
  background: #f0f5ff; border-radius: 6px; color: #3a5cc1;
}
.suggestion-time { font-size: 12px; color: #9ca3af; }
.suggestion-body {
  font-size: 14px; color: #374151;
  line-height: 1.5; margin-bottom: 6px;
}
.suggestion-img {
  display: block; max-width: 120px;
  border-radius: 6px; margin-bottom: 6px;
}
.suggestion-reply {
  margin-top: 8px; padding: 10px 12px;
  background: #f0f5ff; border-radius: 8px;
  font-size: 13px; color: #374151;
}
.reply-meta {
  display: block; font-size: 11px;
  color: #9ca3af; margin-top: 4px;
}
.status-tag {
  padding: 2px 8px; border-radius: 6px;
  font-size: 11px; font-weight: 500;
}
.status-pending { background: #fff7e6; color: #d46b08; }
.status-replied { background: #e6f7e9; color: #389e0d; }

/* --- 响应式 --- */
@media (max-width: 900px) {
  .feedback-page { padding: 16px; }
  .fb-stats { grid-template-columns: repeat(2, 1fr); }
  .fb-header-row { flex-direction: column; align-items: flex-start; }
  .ws-cards { grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
  .wall-toolbar { flex-direction: column; align-items: stretch; }
  .tb-right { flex-wrap: wrap; }
}
@media (max-width: 600px) {
  .fb-stats { grid-template-columns: 1fr 1fr; gap: 8px; }
  .ws-cards { grid-template-columns: 1fr; }
  .wall-bottom { flex-direction: column; align-items: stretch; }
  .wb-btn { justify-content: center; }
}
</style>
