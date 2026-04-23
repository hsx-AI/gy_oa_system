<template>
  <div class="shift-page">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">排班管理</h1>
          <p class="header-subtitle">以班次为维度，每次展示连续两周（14 天），按科室排班；支持管理人员开放指定日期供本科室成员协同填报。</p>
        </div>
        <details class="header-rules">
          <summary class="header-rules-summary">使用规则说明（点击展开 / 收起）</summary>
          <div class="header-rules-body">
            <section class="header-rules-section">
              <h3 class="header-rules-h">一、界面与范围</h3>
              <ul>
                <li>先选择<strong>科室</strong>，表格列出该科室在职人员（按工号顺序）；姓名、统计列为左侧固定列，向右横向滚动查看日期。</li>
                <li>每次固定展示<strong>连续 14 天</strong>。可用「本周」跳到<strong>从当周周一开始</strong>的这一段；「&lt;」「&gt;」向前、向后各翻一段 14 天。</li>
                <li>日期表头会标注<strong>星期</strong>，并结合系统<strong>节假日库</strong>显示调休上班、节假日等简短标记（与行政日历一致）。</li>
              </ul>
            </section>
            <section class="header-rules-section">
              <h3 class="header-rules-h">二、班次与操作</h3>
              <ul>
                <li>每人每天一个班次，仅有三种：<strong>白班</strong>、<strong>夜班</strong>、<strong>不值班</strong>（空）。点击格子按顺序循环切换。</li>
                <li>「统计」列显示该员工在本屏日期内的白班、夜班次数；表脚「当日合计」显示每天白班、夜班人数。</li>
                <li>日期下方第一行「<strong>计划</strong>」为<strong>当日值班工作计划</strong>：点击对应日期格子弹出编辑框（字数上限 2000）；与排班格子一样，需点工具栏「<strong>保存排班</strong>」才会写入服务器。</li>
              </ul>
            </section>
            <section class="header-rules-section">
              <h3 class="header-rules-h">三、谁可以改什么</h3>
              <ul>
                <li><strong>管理人员</strong>（班组长、主任、副主任）且只能操作<strong>本人所在科室</strong>：可改本屏全部日期的排班与计划；可使用「配置」设定工作日/周末白班与夜班人数；可使用「自动排班」「复制上月」「清空」；可在每个日期下点击「<strong>锁</strong>/<strong>开</strong>」切换该日是否对成员开放，或使用「解锁全部 / 锁定全部」。</li>
                <li><strong>本科室普通成员</strong>：默认只能<strong>查看</strong>。管理人员将某日<strong>解锁</strong>后，成员仅可编辑<strong>自己姓名所在行</strong>对应日期的班次；该日<strong>值班工作计划</strong>为全科协同，凡本科室成员在解锁日均可编辑。未解锁的日期仍为只读。</li>
                <li>其他科室人员查看他科排班时，一般为只读（不能与本科室开放规则混用）。</li>
              </ul>
            </section>
            <section class="header-rules-section">
              <h3 class="header-rules-h">四、保存与自动排班</h3>
              <ul>
                <li>改完排班或计划后务必点击「<strong>保存排班</strong>」。管理人员保存<strong>整屏</strong>班次与计划；成员保存时，服务器仅接受<strong>解锁日期</strong>上<strong>本人姓名行</strong>的班次，以及<strong>解锁日期</strong>的工作计划（计划多人可改，后台按日期校验权限）。</li>
                <li>「<strong>自动排班</strong>」会按「配置」里的人数，对<strong>当前屏幕上「今天及之后」的日期</strong>重新生成（今天之前的日期不改动）；每个工作日安排配置的工作日白班/夜班人数，每个周末或节假日按周末配置人数安排，其余人为不值班，并在员工之间轮转（轮转仍按整段日期推算，使从今天起的班次连续合理）。请确认后再操作。</li>
                <li>「<strong>复制上月</strong>」把<strong>上月同一天</strong>的班次映射到本屏各日（遇上月无该日则按上月最后一天对齐）。「<strong>清空</strong>」只清除本屏日期范围内的排班数据。</li>
              </ul>
            </section>
          </div>
        </details>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar card">
      <div class="toolbar-left">
        <label class="toolbar-label">科室</label>
        <select v-model="selectedDept" class="toolbar-select" @change="loadSchedule">
          <option value="">请选择科室</option>
          <option v-for="d in departments" :key="d" :value="d">{{ d }}</option>
        </select>
        <button type="button" class="btn btn-sm" @click="prevPeriod" title="上一段（14 天）">&lt;</button>
        <span class="toolbar-month">{{ periodLabel }}</span>
        <button type="button" class="btn btn-sm" @click="nextPeriod" title="下一段（14 天）">&gt;</button>
        <button type="button" class="btn btn-sm" @click="goThisWeek" title="回到包含今天的两周（从当周周一开始）">本周</button>
        <button
          v-if="selectedDept"
          type="button"
          class="btn btn-outline btn-sm"
          @click="openMonthOverview"
          title="查看本科室整月排班（只读，可切换月份）"
        >
          月览
        </button>
      </div>
      <div class="toolbar-right">
        <template v-if="isManager">
          <button type="button" class="btn btn-outline btn-sm" @click="showConfigPanel = !showConfigPanel" title="排班规则配置">
            ⚙ 配置
          </button>
          <button type="button" class="btn btn-outline btn-sm" @click="handleCopyLastMonth" :disabled="saving">复制上月</button>
          <button type="button" class="btn btn-danger-outline btn-sm" @click="handleClear" :disabled="saving">清空</button>
          <button type="button" class="btn btn-primary btn-sm" @click="handleAutoSchedule" :disabled="saving">自动排班</button>
          <button type="button" class="btn btn-success-outline btn-sm" @click="handleBatchLock(true)" :disabled="saving" title="解锁本屏全部日期：成员仅可改本人班次，计划可协同填写">解锁全部</button>
          <button type="button" class="btn btn-outline btn-sm" @click="handleBatchLock(false)" :disabled="saving" title="锁定全部日期，仅管理人员可编辑">锁定全部</button>
        </template>
        <button
          v-if="isManager || (isSameDept && hasAnyOpenDate)"
          type="button"
          class="btn btn-primary btn-sm"
          @click="handleSave"
          :disabled="saving || !effectiveDirty"
          :title="isManager ? '保存本屏班次与值班工作计划' : '保存：本人行班次（解锁日）+ 当日工作计划（解锁日可协同）'"
        >
          {{ saving ? '保存中…' : '保存排班' }}
        </button>
        <button
          v-if="selectedDept"
          type="button"
          class="btn btn-outline btn-sm"
          @click="showExportPanel = !showExportPanel"
          title="导出排班表为 Excel（按月）"
        >导出 Excel</button>
      </div>
    </div>

    <!-- 导出面板 -->
    <div v-if="showExportPanel && selectedDept" class="export-panel card">
      <h3>导出排班表 <span class="config-dept">{{ selectedDept }}</span></h3>
      <div class="config-form">
        <div class="config-item">
          <label>年份</label>
          <input type="number" v-model.number="exportYear" min="2020" max="2099" style="width:80px">
        </div>
        <div class="config-item">
          <label>月份</label>
          <select v-model.number="exportMonth" style="width:72px">
            <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
          </select>
        </div>
        <button type="button" class="btn btn-primary btn-sm" @click="handleExportExcel" :disabled="exporting">
          {{ exporting ? '导出中…' : '下载' }}
        </button>
      </div>
      <p class="config-hint">导出该科室所选月份的排班表 Excel，含表格与日历两个 Sheet；值班计划、休息日着色均已包含。</p>
    </div>

    <!-- 配置面板 -->
    <div v-if="showConfigPanel && isManager" class="config-panel card">
      <h3>排班规则配置 <span class="config-dept">{{ selectedDept || '—' }}</span></h3>
      <div class="config-form">
        <div class="config-item">
          <label>工作日白班人数</label>
          <input type="number" v-model.number="config.workday_day" min="0" max="50">
        </div>
        <div class="config-item">
          <label>工作日夜班人数</label>
          <input type="number" v-model.number="config.workday_night" min="0" max="50">
        </div>
        <div class="config-item">
          <label>周末白班人数</label>
          <input type="number" v-model.number="config.weekend_day" min="0" max="50">
        </div>
        <div class="config-item">
          <label>周末夜班人数</label>
          <input type="number" v-model.number="config.weekend_night" min="0" max="50">
        </div>
        <button type="button" class="btn btn-primary btn-sm" @click="handleSaveConfig">保存配置</button>
      </div>
      <p class="config-hint">
        自动排班时，仅对「今天及之后」的日期写入；今天之前不覆盖。每天严格按配置人数安排白班和夜班，其余人留空（不值班），人员按日轮转。
      </p>
    </div>

    <!-- 图例 -->
    <div class="legend">
      <span class="legend-item"><span class="legend-dot legend-day"></span>白班</span>
      <span class="legend-item"><span class="legend-dot legend-night"></span>夜班</span>
      <span class="legend-item"><span class="legend-dot legend-empty"></span>不值班</span>
      <span class="legend-sep">|</span>
      <span class="legend-hint">点击单元格切换：白班 → 夜班 → 不值班</span>
      <span class="legend-sep">|</span>
      <span class="legend-item"><span class="legend-dot legend-open"></span>已解锁（成员仅可填本人班次；计划可协同）</span>
      <span class="legend-sep">|</span>
      <span class="legend-item"><span class="legend-dot legend-holiday-work"></span>调休上班</span>
      <span class="legend-item"><span class="legend-dot legend-holiday-rest"></span>节假日</span>
    </div>

    <!-- 排班网格 -->
    <div class="schedule-wrap card" v-if="employees.length">
      <div class="schedule-scroll" @mouseleave="scheduleClearHover">
        <table class="schedule-table">
          <thead>
            <tr>
              <th
                class="col-name sticky-col th-sortable"
                :class="scheduleHlClass(0, 0)"
                title="按姓名排序，点击切换升序 / 降序"
                @mouseenter="scheduleSetHover(0, 0)"
                @click.stop="toggleSortByName"
              >姓名<span
                class="th-sort-ico"
                :class="{ 'is-active': employeeSortKey === 'name' }"
                aria-hidden="true"
              >{{ employeeSortGlyph('name') }}</span></th>
              <th
                class="col-total sticky-col2 th-sortable"
                :class="scheduleHlClass(1, 0)"
                title="按本屏白班+夜班合计排序，点击切换升序 / 降序"
                @mouseenter="scheduleSetHover(1, 0)"
                @click.stop="toggleSortByStats"
              >
                <div>统计<span
                  class="th-sort-ico"
                  :class="{ 'is-active': employeeSortKey === 'stats' }"
                  aria-hidden="true"
                >{{ employeeSortGlyph('stats') }}</span></div>
                <div class="th-sub">白/夜</div>
              </th>
              <th
                v-for="(d, di) in dates"
                :key="d.date"
                class="col-day th-date-head"
                :class="[{ 'col-weekend': !d.isWorkday, 'col-today': d.date === todayStr, 'col-open': openDates[d.date] }, scheduleHlClass(2 + di, 0)]"
                :title="dateHeaderTitle(d)"
                @mouseenter="scheduleSetHover(2 + di, 0)"
              >
                <div class="th-day">{{ d.date.slice(8) }}</div>
                <div class="th-weekday">{{ d.label }}</div>
                <div
                  v-if="d.holidayMark"
                  class="th-holiday"
                  :class="holidayThClass(d)"
                >{{ d.holidayMark }}</div>
                <template v-if="d.date >= todayStr">
                  <div
                    v-if="isManager"
                    class="th-lock-btn"
                    :class="{ 'th-lock-open': openDates[d.date] }"
                    @click.stop="toggleDayLock(d.date)"
                    :title="openDates[d.date] ? '点击锁定此日' : '点击开放此日'"
                  >{{ openDates[d.date] ? '开' : '锁' }}</div>
                  <div
                    v-else-if="isSameDept && openDates[d.date]"
                    class="th-open-badge"
                  >可填</div>
                </template>
                <div v-else class="th-past-badge">已过</div>
              </th>
            </tr>
            <tr class="plan-row">
              <th
                class="col-name sticky-col plan-row-label"
                title="解锁日：本科室成员均可协同编辑当日计划；未解锁仅管理人员可改"
                :class="scheduleHlClass(0, 1)"
                @mouseenter="scheduleSetHover(0, 1)"
              >计划</th>
              <th
                class="col-total sticky-col2 plan-row-stat"
                :class="scheduleHlClass(1, 1)"
                @mouseenter="scheduleSetHover(1, 1)"
              >—</th>
              <th
                v-for="(d, di) in dates"
                :key="'plan-' + d.date"
                class="col-day plan-cell"
                :class="[{ 'col-weekend': !d.isWorkday, 'col-today': d.date === todayStr, 'plan-has': !!dayPlans[d.date], 'col-open': openDates[d.date] && isSameDept && !isManager }, scheduleHlClass(2 + di, 1)]"
                :title="planCellTitle(d)"
                @mouseenter="scheduleSetHover(2 + di, 1)"
                @click="openPlanEditor(d)"
              >
                <span v-if="dayPlans[d.date]" class="plan-preview">{{ planPreview(d.date) }}</span>
                <span v-else class="plan-empty-dot">+</span>
              </th>
            </tr>
            <tr class="summary-head-row">
              <th
                class="col-name sticky-col summary-head-label"
                :class="scheduleHlClass(0, 2)"
                @mouseenter="scheduleSetHover(0, 2)"
              ><strong>当日合计</strong></th>
              <th
                class="col-total sticky-col2 summary-head-stat"
                :class="scheduleHlClass(1, 2)"
                @mouseenter="scheduleSetHover(1, 2)"
              >—</th>
              <th
                v-for="(d, di) in dates"
                :key="'sum-' + d.date"
                class="col-day summary-head-day"
                :class="[{ 'col-weekend': !d.isWorkday, 'col-today': d.date === todayStr }, scheduleHlClass(2 + di, 2)]"
                @mouseenter="scheduleSetHover(2 + di, 2)"
              >
                <div class="summary-cell" :title="daySummaryTooltip(d)">
                  <span class="stat-day">{{ daySummary[d.date]?.day ?? 0 }}</span>
                  <span class="summary-slash">/</span>
                  <span class="stat-night">{{ daySummary[d.date]?.night ?? 0 }}</span>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(emp, ei) in sortedEmployees" :key="emp">
              <td
                class="col-name sticky-col"
                :title="emp"
                :class="scheduleHlClass(0, 3 + ei)"
                @mouseenter="scheduleSetHover(0, 3 + ei)"
              >{{ emp }}</td>
              <td
                class="col-total sticky-col2"
                :class="scheduleHlClass(1, 3 + ei)"
                @mouseenter="scheduleSetHover(1, 3 + ei)"
              >
                <span class="stat-day">{{ empStats[emp]?.day || 0 }}</span>/<span class="stat-night">{{ empStats[emp]?.night || 0 }}</span>
              </td>
              <td
                v-for="(d, di) in dates"
                :key="d.date"
                class="col-day cell"
                :class="[cellClass(emp, d), { 'cell-readonly': !canEditShiftCell(emp, d.date), 'col-open': openDates[d.date] && !isManager && d.date >= todayStr && isSelfRow(emp), 'col-past': d.date < todayStr }, scheduleHlClass(2 + di, 3 + ei)]"
                @mouseenter="scheduleSetHover(2 + di, 3 + ei)"
                @click="onCellClick(emp, d.date)"
                @mousedown="onCellDown(emp, d.date, $event)"
                @mouseup="onCellUp"
                @mouseleave="onCellUp"
                @touchstart.prevent="onCellDown(emp, d.date, $event)"
                @touchend="onCellUp"
              >
                <span class="cell-text">{{ cellLabel(emp, d.date) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-else-if="selectedDept && !loading" class="empty-state card">
      <p>该科室暂无在职员工数据</p>
    </div>
    <div v-else-if="loading" class="empty-state card"><p>加载中…</p></div>
    <div v-else class="empty-state card"><p>请先选择科室</p></div>

    <!-- 值班工作计划弹出编辑器 -->
    <div v-if="planEditing" class="plan-overlay" @click.self="closePlanEditor">
      <div class="plan-editor">
        <div class="plan-editor-header">
          <span class="plan-editor-title">{{ planEditDate }} 值班工作计划</span>
          <button type="button" class="plan-editor-close" @click="closePlanEditor">&times;</button>
        </div>
        <textarea
          ref="planTextareaRef"
          v-model="planEditText"
          class="plan-editor-textarea"
          :readonly="!canEditCurrentPlan"
          maxlength="2000"
          :placeholder="canEditCurrentPlan ? '请输入当天的值班工作安排、注意事项等…' : '该日未解锁或已过期，仅可查看；请管理人员解锁当日后本科室可协同编辑'"
          @input="plansDirty = true"
        ></textarea>
        <div class="plan-editor-footer">
          <span class="plan-editor-hint">{{ planEditText.length }} / 2000</span>
          <button v-if="canEditCurrentPlan" type="button" class="btn btn-primary btn-sm" @click="closePlanEditor">完成</button>
          <button v-else type="button" class="btn btn-sm" @click="closePlanEditor">关闭</button>
        </div>
      </div>
    </div>

    <!-- 整月排班总览（只读） -->
    <div v-if="monthOverviewVisible" class="mo-overlay" @click.self="closeMonthOverview">
      <div class="mo-panel">
        <div class="mo-header">
          <div class="mo-header-left">
            <h2 class="mo-title">整月排班总览</h2>
            <span class="mo-dept">{{ selectedDept }}</span>
            <span class="mo-badge">仅查看</span>
            <div class="mo-view-toggle">
              <button type="button" class="mo-toggle-btn" :class="{ active: moViewMode === 'table' }" @click="moViewMode = 'table'">表格</button>
              <button type="button" class="mo-toggle-btn" :class="{ active: moViewMode === 'calendar' }" @click="moViewMode = 'calendar'">日历</button>
            </div>
          </div>
          <div class="mo-header-nav">
            <button type="button" class="btn btn-sm" @click="shiftOverviewMonth(-1)" :disabled="monthOverviewLoading" title="上一月">&lt;</button>
            <span class="mo-period">{{ monthOverviewTitle }}</span>
            <button type="button" class="btn btn-sm" @click="shiftOverviewMonth(1)" :disabled="monthOverviewLoading" title="下一月">&gt;</button>
            <button type="button" class="btn btn-primary btn-sm" @click="closeMonthOverview">关闭</button>
          </div>
        </div>
        <p class="mo-hint">与下方双周编辑区无关；在此仅浏览，修改请关闭后回到主表操作。</p>
        <div v-if="monthOverviewLoading" class="mo-loading">加载中…</div>
        <div v-else-if="!monthOverviewEmployees.length" class="mo-empty">该科室当月无在职人员数据</div>

        <!-- 表格视图 -->
        <div v-else-if="moViewMode === 'table'" class="mo-scroll-wrap">
          <table class="mo-table">
            <thead>
              <tr>
                <th class="mo-col-name mo-sticky">姓名</th>
                <th class="mo-col-stat mo-sticky2">白/夜</th>
                <th
                  v-for="d in monthOverviewDates"
                  :key="d.date"
                  class="mo-col-day"
                  :class="{ 'mo-col-weekend': !d.isWorkday, 'mo-col-today': d.date === todayStr }"
                  :title="dateHeaderTitle(d)"
                >
                  <div class="mo-th-day">{{ d.date.slice(8) }}</div>
                  <div class="mo-th-wd">{{ d.label }}</div>
                  <div v-if="d.holidayMark" class="mo-th-holiday" :class="holidayThClass(d)">{{ d.holidayMark }}</div>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="emp in monthOverviewEmployees" :key="'mo-' + emp">
                <td class="mo-col-name mo-sticky" :title="emp">{{ emp }}</td>
                <td class="mo-col-stat mo-sticky2">
                  <span class="stat-day">{{ moEmpStats[emp]?.day ?? 0 }}</span>/<span class="stat-night">{{ moEmpStats[emp]?.night ?? 0 }}</span>
                </td>
                <td
                  v-for="d in monthOverviewDates"
                  :key="emp + d.date"
                  class="mo-cell"
                  :class="moCellClass(emp, d)"
                >
                  <span class="mo-cell-text">{{ moCellLabel(emp, d.date) }}</span>
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="mo-summary-row">
                <td class="mo-col-name mo-sticky"><strong>当日合计</strong></td>
                <td class="mo-col-stat mo-sticky2">—</td>
                <td v-for="d in monthOverviewDates" :key="'sum-' + d.date" class="mo-cell mo-summary-cell">
                  <span class="stat-day">{{ moDaySummary[d.date]?.day ?? 0 }}</span><span class="mo-slash">/</span><span class="stat-night">{{ moDaySummary[d.date]?.night ?? 0 }}</span>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>

        <!-- 日历视图 -->
        <div v-else class="mo-scroll-wrap cal-wrap">
          <div class="cal-legend">
            <span class="cal-legend-item"><span class="cal-dot cal-dot-day"></span>白班</span>
            <span class="cal-legend-item"><span class="cal-dot cal-dot-night"></span>夜班</span>
            <span class="cal-legend-item"><span class="cal-dot cal-dot-off"></span>不值班</span>
          </div>
          <div class="cal-grid">
            <div class="cal-weekday-header" v-for="wd in ['一','二','三','四','五','六','日']" :key="wd">{{ wd }}</div>
            <div v-for="blank in calLeadingBlanks" :key="'blank-' + blank" class="cal-day-cell cal-blank"></div>
            <div
              v-for="d in monthOverviewDates"
              :key="'cal-' + d.date"
              class="cal-day-cell"
              :class="{ 'cal-today': d.date === todayStr, 'cal-weekend': !d.isWorkday }"
            >
              <div class="cal-day-num">
                <span>{{ parseInt(d.date.slice(8)) }}</span>
                <span v-if="d.holidayMark" class="cal-holiday-tag" :class="holidayThClass(d)">{{ d.holidayMark }}</span>
                <span v-if="moDayPlans[d.date]" class="cal-plan-chip" title="鼠标悬浮查看值班计划">计划</span>
              </div>
              <div class="cal-day-people">
                <template v-if="calDayData[d.date]?.day?.length">
                  <div class="cal-shift-row cal-shift-day">
                    <span class="cal-shift-label">白</span>
                    <span class="cal-shift-names">{{ calDayData[d.date].day.join('、') }}</span>
                  </div>
                </template>
                <template v-if="calDayData[d.date]?.night?.length">
                  <div class="cal-shift-row cal-shift-night">
                    <span class="cal-shift-label">夜</span>
                    <span class="cal-shift-names">{{ calDayData[d.date].night.join('、') }}</span>
                  </div>
                </template>
                <div v-if="!calDayData[d.date]?.day?.length && !calDayData[d.date]?.night?.length" class="cal-shift-empty">无排班</div>
              </div>
              <div v-if="moDayPlans[d.date]" class="cal-plan-popover">
                <div class="cal-plan-title">值班计划</div>
                <div class="cal-plan-text">{{ moDayPlans[d.date] }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <Transition name="shift-cap-toast-fade">
      <div v-if="shiftCapToast" class="shift-cap-toast" role="status">{{ shiftCapToast }}</div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { getDepartments, getShiftConfig, saveShiftConfig, getSchedule, saveSchedule, saveDayPlans, autoSchedule, copyLastMonth, clearSchedule, setDayLocks } from '@/api/shift'
import { isDeptLeader } from '@/utils/roleMatch'

const PERIOD_DAYS = 14

function pad2(n) {
  return String(n).padStart(2, '0')
}
function toYMD(d) {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}
function parseYMD(s) {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}
/** 当周周一（周一为一周起始） */
function mondayOf(d) {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const w = x.getDay()
  const diff = w === 0 ? -6 : 1 - w
  x.setDate(x.getDate() + diff)
  return x
}

const now = new Date()
const rangeStartStr = ref(toYMD(mondayOf(now)))
const todayStr = toYMD(now)

const periodEndStr = computed(() => {
  const x = parseYMD(rangeStartStr.value)
  x.setDate(x.getDate() + PERIOD_DAYS - 1)
  return toYMD(x)
})

const periodLabel = computed(() => {
  const a = parseYMD(rangeStartStr.value)
  const b = parseYMD(periodEndStr.value)
  const fmt = (d) => `${d.getMonth() + 1}月${d.getDate()}日`
  if (a.getFullYear() === b.getFullYear()) {
    return `${a.getFullYear()}年 ${fmt(a)} - ${fmt(b)}`
  }
  return `${a.getFullYear()}年${fmt(a)} - ${b.getFullYear()}年${fmt(b)}`
})

const departments = ref([])
const selectedDept = ref('')
const employees = ref([])
const dates = ref([])
const scheduleData = reactive({})
const dayPlans = reactive({})
const loading = ref(false)
const saving = ref(false)
const dirty = ref(false)
const plansDirty = ref(false)
const effectiveDirty = computed(() => dirty.value || plansDirty.value)

const planEditing = ref(false)
const planEditDate = ref('')
const planEditText = ref('')
const planTextareaRef = ref(null)

/** 排班表 Excel 式行列十字高亮（当前悬浮列 / 行索引） */
const scheduleHoverCol = ref(null)
const scheduleHoverRow = ref(null)
function scheduleSetHover(col, row) {
  scheduleHoverCol.value = col
  scheduleHoverRow.value = row
}
function scheduleClearHover() {
  scheduleHoverCol.value = null
  scheduleHoverRow.value = null
}
function scheduleHlClass(col, row) {
  const c = scheduleHoverCol.value
  const r = scheduleHoverRow.value
  if (c === null || r === null) return {}
  return {
    'sched-hl-row': r === row,
    'sched-hl-col': c === col,
  }
}

function planPreview(dateStr) {
  const txt = (dayPlans[dateStr] || '').trim()
  if (!txt) return ''
  return txt.length > 6 ? txt.slice(0, 6) + '…' : txt
}

function openPlanEditor(d) {
  planEditDate.value = d.date
  planEditText.value = dayPlans[d.date] || ''
  planEditing.value = true
  nextTick(() => {
    if (planTextareaRef.value && canEditPlanDate(d.date)) planTextareaRef.value.focus()
  })
}

function closePlanEditor() {
  if (planEditText.value !== (dayPlans[planEditDate.value] || '')) {
    dayPlans[planEditDate.value] = planEditText.value
    plansDirty.value = true
  }
  planEditing.value = false
}
const showConfigPanel = ref(false)
const config = reactive({ workday_day: 2, workday_night: 2, weekend_day: 2, weekend_night: 2 })

const monthOverviewVisible = ref(false)
const monthOverviewLoading = ref(false)
const monthOverviewYear = ref(new Date().getFullYear())
const monthOverviewMonth = ref(new Date().getMonth() + 1)
const monthOverviewEmployees = ref([])
const monthOverviewDates = ref([])
const moSchedule = reactive({})
const moDayPlans = reactive({})
const moViewMode = ref('calendar')

const monthOverviewTitle = computed(() => `${monthOverviewYear.value}年${monthOverviewMonth.value}月`)

const calLeadingBlanks = computed(() => {
  if (!monthOverviewDates.value.length) return 0
  const first = new Date(monthOverviewDates.value[0].date)
  const dow = first.getDay()
  return dow === 0 ? 6 : dow - 1
})

const calDayData = computed(() => {
  const result = {}
  for (const d of monthOverviewDates.value) {
    const dayList = []
    const nightList = []
    for (const emp of monthOverviewEmployees.value) {
      const v = moSchedule[emp]?.[d.date] || ''
      if (v === '白班') dayList.push(emp)
      else if (v === '夜班') nightList.push(emp)
    }
    result[d.date] = { day: dayList, night: nightList }
  }
  return result
})

const moEmpStats = computed(() => {
  const stats = {}
  for (const emp of monthOverviewEmployees.value) {
    let day = 0
    let night = 0
    const dm = moSchedule[emp] || {}
    for (const v of Object.values(dm)) {
      if (v === '白班') day++
      else if (v === '夜班') night++
    }
    stats[emp] = { day, night }
  }
  return stats
})

const moDaySummary = computed(() => {
  const summary = {}
  for (const d of monthOverviewDates.value) {
    let day = 0
    let night = 0
    for (const emp of monthOverviewEmployees.value) {
      const v = moSchedule[emp]?.[d.date] || ''
      if (v === '白班') day++
      else if (v === '夜班') night++
    }
    summary[d.date] = { day, night }
  }
  return summary
})

function openMonthOverview() {
  const x = parseYMD(rangeStartStr.value)
  monthOverviewYear.value = x.getFullYear()
  monthOverviewMonth.value = x.getMonth() + 1
  moViewMode.value = 'calendar'
  monthOverviewVisible.value = true
  loadMonthOverview()
}

async function loadMonthOverview() {
  if (!selectedDept.value) return
  monthOverviewLoading.value = true
  try {
    const res = await getSchedule({
      department: selectedDept.value,
      year: monthOverviewYear.value,
      month: monthOverviewMonth.value,
    })
    monthOverviewEmployees.value = res?.employees || []
    monthOverviewDates.value = res?.dates || []
    Object.keys(moSchedule).forEach((k) => delete moSchedule[k])
    Object.keys(moDayPlans).forEach((k) => delete moDayPlans[k])
    const sch = res?.schedule || {}
    const dp = res?.dayPlans || {}
    for (const [emp, dayMap] of Object.entries(sch)) {
      moSchedule[emp] = { ...dayMap }
    }
    for (const d of monthOverviewDates.value) {
      moDayPlans[d.date] = dp[d.date] ?? ''
    }
  } catch (e) {
    console.error('月览加载失败:', e)
    alert(e?.response?.data?.detail || '加载月览失败')
  } finally {
    monthOverviewLoading.value = false
  }
}

function closeMonthOverview() {
  monthOverviewVisible.value = false
}

function shiftOverviewMonth(delta) {
  let y = monthOverviewYear.value
  let m = monthOverviewMonth.value + delta
  if (m < 1) {
    m = 12
    y -= 1
  } else if (m > 12) {
    m = 1
    y += 1
  }
  monthOverviewYear.value = y
  monthOverviewMonth.value = m
  loadMonthOverview()
}

function moCellLabel(emp, dateStr) {
  const v = moSchedule[emp]?.[dateStr] || ''
  if (v === '白班') return '白'
  if (v === '夜班') return '夜'
  return ''
}

function moCellClass(emp, d) {
  const v = moSchedule[emp]?.[d.date] || ''
  return {
    'mo-cell-day': v === '白班',
    'mo-cell-night': v === '夜班',
    'mo-cell-empty': !v || (v !== '白班' && v !== '夜班'),
    'mo-col-weekend': !d.isWorkday,
    'mo-col-today': d.date === todayStr,
  }
}

function getCurrentUser() {
  try { return (JSON.parse(localStorage.getItem('userInfo') || '{}').name || '').trim() }
  catch { return '' }
}

const isManager = computed(() => {
  try {
    const info = JSON.parse(localStorage.getItem('userInfo') || '{}')
    const jb = (info.jb || '').trim()
    const myDept = (info.dept || info.lsys || '').trim()
    const mgr = isDeptLeader(jb)
    return mgr && !!selectedDept.value && selectedDept.value === myDept
  } catch { return false }
})

const isSameDept = computed(() => {
  try {
    const info = JSON.parse(localStorage.getItem('userInfo') || '{}')
    const myDept = (info.dept || info.lsys || '').trim()
    return !!selectedDept.value && selectedDept.value === myDept
  } catch { return false }
})

const openDates = reactive({})

const hasAnyOpenDate = computed(() => Object.values(openDates).some(Boolean))

/** 解锁日 + 本科室：成员均可编辑当日工作计划（协同）；管理员始终可编辑（未过期日期） */
function canEditPlanDate(dateStr) {
  if (dateStr < todayStr) return false
  if (isManager.value) return true
  return isSameDept.value && !!openDates[dateStr]
}

/** 班次格子：成员仅可编辑本人所在行；管理员可编辑全部 */
function canEditShiftCell(emp, dateStr) {
  if (dateStr < todayStr) return false
  if (isManager.value) return true
  if (!isSameDept.value || !openDates[dateStr]) return false
  return isSelfRow(emp)
}

function isSelfRow(emp) {
  const me = getCurrentUser()
  if (!me || !emp) return false
  return String(emp).trim() === String(me).trim()
}

const canEditCurrentPlan = computed(() => canEditPlanDate(planEditDate.value))

function planCellTitle(d) {
  const hint = (dayPlans[d.date] || '').trim()
  const act = canEditPlanDate(d.date) ? '点击编辑计划' : '点击查看'
  return hint ? `${hint.slice(0, 80)}${hint.length > 80 ? '…' : ''} · ${act}` : act
}

onMounted(async () => {
  try {
    const res = await getDepartments()
    departments.value = res?.departments || []
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
    const dept = (userInfo.dept || userInfo.department || '').trim()
    if (dept && departments.value.includes(dept)) {
      selectedDept.value = dept
      await loadSchedule()
    }
  } catch (e) {
    console.error('加载科室列表失败:', e)
  }
})

async function loadSchedule() {
  if (!selectedDept.value) {
    employees.value = []
    employeeSortKey.value = null
    dates.value = []
    return
  }
  loading.value = true
  dirty.value = false
  plansDirty.value = false
  try {
    const [schRes, cfgRes] = await Promise.all([
      getSchedule({
        department: selectedDept.value,
        start_date: rangeStartStr.value,
        end_date: periodEndStr.value,
      }),
      getShiftConfig({ department: selectedDept.value }),
    ])
    employees.value = schRes?.employees || []
    employeeSortKey.value = null
    dates.value = schRes?.dates || []
    Object.keys(scheduleData).forEach(k => delete scheduleData[k])
    const sch = schRes?.schedule || {}
    for (const [emp, dayMap] of Object.entries(sch)) {
      scheduleData[emp] = { ...dayMap }
    }
    Object.keys(dayPlans).forEach(k => delete dayPlans[k])
    const dp = schRes?.dayPlans || {}
    for (const d of schRes?.dates || []) {
      dayPlans[d.date] = dp[d.date] ?? ''
    }
    Object.keys(openDates).forEach(k => delete openDates[k])
    for (const ds of schRes?.openDates || []) {
      openDates[ds] = true
    }
    const c = cfgRes?.data || {}
    config.workday_day = c.workday_day ?? 2
    config.workday_night = c.workday_night ?? 2
    config.weekend_day = c.weekend_day ?? 2
    config.weekend_night = c.weekend_night ?? 2
  } catch (e) {
    console.error('加载排班失败:', e)
  } finally {
    loading.value = false
  }
}

function shiftRangeStartByDays(delta) {
  const x = parseYMD(rangeStartStr.value)
  x.setDate(x.getDate() + delta)
  rangeStartStr.value = toYMD(x)
  loadSchedule()
}
function prevPeriod() {
  shiftRangeStartByDays(-PERIOD_DAYS)
}
function nextPeriod() {
  shiftRangeStartByDays(PERIOD_DAYS)
}
function goThisWeek() {
  rangeStartStr.value = toYMD(mondayOf(new Date()))
  loadSchedule()
}

const SHIFT_CYCLE = ['白班', '夜班', '']
let _lpTimer = null
let _lpFired = false
const shiftCapToast = ref('')
let shiftCapToastTimer = null
function showShiftCapToast(message) {
  shiftCapToast.value = message
  if (shiftCapToastTimer) clearTimeout(shiftCapToastTimer)
  shiftCapToastTimer = setTimeout(() => {
    shiftCapToast.value = ''
    shiftCapToastTimer = null
  }, 2600)
}
onUnmounted(() => {
  if (shiftCapToastTimer) clearTimeout(shiftCapToastTimer)
})

/** 与自动排班一致：工作日用 workday_*，周末/节假日用 weekend_* */
function shiftCapsForDateStr(dateStr) {
  const d = dates.value.find((x) => x.date === dateStr)
  if (!d) return { day: 999, night: 999, kindLabel: '' }
  if (d.isWorkday) {
    return {
      day: Math.max(0, Number(config.workday_day) || 0),
      night: Math.max(0, Number(config.workday_night) || 0),
      kindLabel: '工作日',
    }
  }
  return {
    day: Math.max(0, Number(config.weekend_day) || 0),
    night: Math.max(0, Number(config.weekend_night) || 0),
    kindLabel: '周末/节假日',
  }
}

function countShiftOnDate(dateStr, shift) {
  let n = 0
  for (const e of employees.value) {
    const v = scheduleData[e]?.[dateStr] || ''
    if (v === shift) n++
    else if (v === '白+夜' && (shift === '白班' || shift === '夜班')) n++
  }
  return n
}

function cycleShift(emp, dateStr) {
  if (!canEditShiftCell(emp, dateStr)) return
  if (!scheduleData[emp]) scheduleData[emp] = {}
  const cur = scheduleData[emp][dateStr] || ''
  const idxRaw = cur === '白+夜' ? 2 : SHIFT_CYCLE.indexOf(cur)
  const idx = idxRaw >= 0 ? idxRaw : 2
  const next = SHIFT_CYCLE[(idx + 1) % SHIFT_CYCLE.length]
  const caps = shiftCapsForDateStr(dateStr)
  scheduleData[emp][dateStr] = next
  dirty.value = true
  if (next === '白班') {
    const cnt = countShiftOnDate(dateStr, '白班')
    if (cnt > caps.day) {
      showShiftCapToast(
        `提示：${caps.kindLabel}白班已超过配置（配置 ${caps.day} 人，当前 ${cnt} 人），已保留您的排班`,
      )
    }
  } else if (next === '夜班') {
    const cnt = countShiftOnDate(dateStr, '夜班')
    if (cnt > caps.night) {
      showShiftCapToast(
        `提示：${caps.kindLabel}夜班已超过配置（配置 ${caps.night} 人，当前 ${cnt} 人），已保留您的排班`,
      )
    }
  }
}

function onCellDown(emp, dateStr, e) {
  _lpFired = false
  if (_lpTimer) clearTimeout(_lpTimer)
  _lpTimer = setTimeout(() => {
    _lpFired = true
    _lpTimer = null
    toggleBothShift(emp, dateStr)
  }, 500)
}

function onCellUp() {
  if (_lpTimer) { clearTimeout(_lpTimer); _lpTimer = null }
}

function onCellClick(emp, dateStr) {
  if (_lpFired) { _lpFired = false; return }
  cycleShift(emp, dateStr)
}

function toggleBothShift(emp, dateStr) {
  if (!canEditShiftCell(emp, dateStr)) return
  if (!scheduleData[emp]) scheduleData[emp] = {}
  const cur = scheduleData[emp][dateStr] || ''
  if (cur === '白+夜') {
    scheduleData[emp][dateStr] = ''
  } else {
    scheduleData[emp][dateStr] = '白+夜'
  }
  dirty.value = true
  const caps = shiftCapsForDateStr(dateStr)
  const cntDay = countShiftOnDate(dateStr, '白班')
  const cntNight = countShiftOnDate(dateStr, '夜班')
  if (scheduleData[emp][dateStr] === '白+夜') {
    if (cntDay > caps.day) {
      showShiftCapToast(`提示：${caps.kindLabel}白班已超过配置（配置 ${caps.day} 人，当前 ${cntDay} 人），已保留您的排班`)
    } else if (cntNight > caps.night) {
      showShiftCapToast(`提示：${caps.kindLabel}夜班已超过配置（配置 ${caps.night} 人，当前 ${cntNight} 人），已保留您的排班`)
    }
  }
}

function cellLabel(emp, dateStr) {
  const v = scheduleData[emp]?.[dateStr] || ''
  if (v === '白+夜') return '白夜'
  if (v === '白班') return '白'
  if (v === '夜班') return '夜'
  return ''
}

function cellClass(emp, d) {
  const v = scheduleData[emp]?.[d.date] || ''
  return {
    'cell-both': v === '白+夜',
    'cell-day': v === '白班',
    'cell-night': v === '夜班',
    'cell-empty': !v || (v !== '白班' && v !== '夜班' && v !== '白+夜'),
    'col-weekend': !d.isWorkday,
    'col-today': d.date === todayStr,
  }
}

const empStats = computed(() => {
  const stats = {}
  for (const emp of employees.value) {
    let day = 0, night = 0
    const dayMap = scheduleData[emp] || {}
    for (const v of Object.values(dayMap)) {
      if (v === '白+夜') { day++; night++ }
      else if (v === '白班') day++
      else if (v === '夜班') night++
    }
    stats[emp] = { day, night }
  }
  return stats
})

/** null：与后台返回顺序一致；name / stats：点击表头排序 */
const employeeSortKey = ref(null)
const employeeSortDir = ref('asc')

function toggleSortByName() {
  if (employeeSortKey.value !== 'name') {
    employeeSortKey.value = 'name'
    employeeSortDir.value = 'asc'
  } else {
    employeeSortDir.value = employeeSortDir.value === 'asc' ? 'desc' : 'asc'
  }
}

function toggleSortByStats() {
  if (employeeSortKey.value !== 'stats') {
    employeeSortKey.value = 'stats'
    employeeSortDir.value = 'asc'
  } else {
    employeeSortDir.value = employeeSortDir.value === 'asc' ? 'desc' : 'asc'
  }
}

/** 未选中列显示 ↕ 提示可排序；选中后显示 ↑ / ↓ */
function employeeSortGlyph(which) {
  if (employeeSortKey.value !== which) return '↕'
  return employeeSortDir.value === 'asc' ? '↑' : '↓'
}

const sortedEmployees = computed(() => {
  const list = [...employees.value]
  const key = employeeSortKey.value
  if (!key) return list
  const dir = employeeSortDir.value === 'asc' ? 1 : -1
  if (key === 'name') {
    list.sort((a, b) => dir * String(a).localeCompare(String(b), 'zh-Hans-CN', { numeric: true }))
    return list
  }
  if (key === 'stats') {
    list.sort((a, b) => {
      const sa = (empStats.value[a]?.day || 0) + (empStats.value[a]?.night || 0)
      const sb = (empStats.value[b]?.day || 0) + (empStats.value[b]?.night || 0)
      if (sa !== sb) return dir * (sa - sb)
      return String(a).localeCompare(String(b), 'zh-Hans-CN', { numeric: true })
    })
    return list
  }
  return list
})

const daySummary = computed(() => {
  const summary = {}
  for (const d of dates.value) {
    let day = 0, night = 0
    for (const emp of employees.value) {
      const v = scheduleData[emp]?.[d.date] || ''
      if (v === '白+夜') { day++; night++ }
      else if (v === '白班') day++
      else if (v === '夜班') night++
    }
    summary[d.date] = { day, night }
  }
  return summary
})

function daySummaryTooltip(d) {
  const s = daySummary.value[d.date]
  if (!s) return ''
  const kind = d.isWorkday ? '工作日' : '周末或节假日'
  return `${d.date}（${kind}）白班 ${s.day} 人，夜班 ${s.night} 人`
}

function dateHeaderTitle(d) {
  const base = `${d.date} 星期${d.label}`
  if (!d.holidayType && !d.holidayFestival) return base
  const extra = [d.holidayFestival, d.holidayType].filter(Boolean).join(' · ')
  return extra ? `${base} · ${extra}` : base
}

function holidayThClass(d) {
  const t = d.holidayType || ''
  if (t.includes('班')) return 'th-holiday-work'
  if (t.includes('假') || t.includes('休')) return 'th-holiday-rest'
  return 'th-holiday-other'
}

async function handleSave() {
  if (!selectedDept.value) return
  saving.value = true
  try {
    const rs = parseYMD(rangeStartStr.value)
    const tasks = []
    if (dirty.value) {
      tasks.push(
        saveSchedule({
          department: selectedDept.value,
          year: rs.getFullYear(),
          month: rs.getMonth() + 1,
          schedule: { ...scheduleData },
          current_user: getCurrentUser(),
        }),
      )
    }
    if (plansDirty.value) {
      const plans = {}
      for (const d of dates.value) {
        if (isManager.value || openDates[d.date]) {
          plans[d.date] = dayPlans[d.date] ?? ''
        }
      }
      tasks.push(
        saveDayPlans({
          department: selectedDept.value,
          plans,
          current_user: getCurrentUser(),
        }),
      )
    }
    if (tasks.length === 0) {
      saving.value = false
      return
    }
    await Promise.all(tasks)
    dirty.value = false
    plansDirty.value = false
    alert('已保存')
  } catch (e) {
    alert(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleAutoSchedule() {
  if (!selectedDept.value) return
  if (!confirm(`自动排班将覆盖当前屏幕内「今天及之后」的排班；今天之前的日期保留不动（${periodLabel.value}）。确认？`)) return
  saving.value = true
  try {
    const res = await autoSchedule({
      department: selectedDept.value,
      start_date: rangeStartStr.value,
      end_date: periodEndStr.value,
      current_user: getCurrentUser(),
      workday_day: config.workday_day,
      workday_night: config.workday_night,
      weekend_day: config.weekend_day,
      weekend_night: config.weekend_night,
    })
    if (res?.success) {
      await loadSchedule()
      alert(res.message || '自动排班完成')
    } else {
      alert(res?.message || '自动排班失败')
    }
  } catch (e) {
    alert(e?.response?.data?.detail || '自动排班失败')
  } finally {
    saving.value = false
  }
}

async function handleCopyLastMonth() {
  if (!selectedDept.value) return
  if (!confirm(`将上月「同一天」对到本屏各日并写入（${periodLabel.value}），确认？`)) return
  saving.value = true
  try {
    const res = await copyLastMonth({
      department: selectedDept.value,
      start_date: rangeStartStr.value,
      end_date: periodEndStr.value,
      current_user: getCurrentUser(),
    })
    if (res?.success) {
      await loadSchedule()
      alert(res.message || '已复制')
    } else {
      alert(res?.message || '复制失败')
    }
  } catch (e) {
    alert(e?.response?.data?.detail || '复制失败')
  } finally {
    saving.value = false
  }
}

async function handleClear() {
  if (!selectedDept.value) return
  if (!confirm(`确认清空 ${selectedDept.value} 在本屏日期范围内的排班？\n${periodLabel.value}`)) return
  saving.value = true
  try {
    const res = await clearSchedule({
      department: selectedDept.value,
      start_date: rangeStartStr.value,
      end_date: periodEndStr.value,
    })
    if (res?.success) {
      await loadSchedule()
      alert(res.message || '已清空')
    } else {
      alert(res?.message || '清空失败')
    }
  } catch (e) {
    alert(e?.response?.data?.detail || '清空失败')
  } finally {
    saving.value = false
  }
}

async function handleSaveConfig() {
  if (!selectedDept.value) return
  try {
    await saveShiftConfig({
      department: selectedDept.value,
      workday_day: config.workday_day,
      workday_night: config.workday_night,
      weekend_day: config.weekend_day,
      weekend_night: config.weekend_night,
      current_user: getCurrentUser(),
    })
    alert('配置已保存')
  } catch (e) {
    alert('保存配置失败')
  }
}

async function toggleDayLock(dateStr) {
  if (!isManager.value) return
  const willOpen = !openDates[dateStr]
  try {
    await setDayLocks({
      department: selectedDept.value,
      dates: [dateStr],
      is_open: willOpen,
      current_user: getCurrentUser(),
    })
    openDates[dateStr] = willOpen || undefined
    if (!willOpen) delete openDates[dateStr]
  } catch (e) {
    alert(e?.response?.data?.detail || '操作失败')
  }
}

async function handleBatchLock(open) {
  if (!isManager.value || !dates.value.length) return
  const action = open ? '解锁' : '锁定'
  if (!confirm(`确认${action}当前所有日期（${periodLabel.value}）的排班权限？\n${open ? '解锁后：成员仅可填写本人行的班次，当日计划可多人协同' : '锁定后：成员不可自行编辑班次与计划'}。`)) return
  try {
    await setDayLocks({
      department: selectedDept.value,
      dates: dates.value.map(d => d.date),
      is_open: open,
      current_user: getCurrentUser(),
    })
    for (const d of dates.value) {
      if (open) openDates[d.date] = true
      else delete openDates[d.date]
    }
    alert(`已${action}全部日期`)
  } catch (e) {
    alert(e?.response?.data?.detail || '操作失败')
  }
}

// ==================== 导出 Excel ====================
const showExportPanel = ref(false)
const exportYear = ref(new Date().getFullYear())
const exportMonth = ref(new Date().getMonth() + 1)
const exporting = ref(false)

async function handleExportExcel() {
  if (!selectedDept.value) return
  exporting.value = true
  try {
    const params = new URLSearchParams({
      department: selectedDept.value,
      year: String(exportYear.value),
      month: String(exportMonth.value),
    })
    const url = `/api/shift/export-excel?${params.toString()}`
    const resp = await fetch(url, { credentials: 'include' })
    if (!resp.ok) {
      const errText = await resp.text().catch(() => '')
      let detail = '导出失败'
      try { detail = JSON.parse(errText).detail || detail } catch {}
      alert(detail)
      return
    }
    const blob = await resp.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${selectedDept.value}_${exportYear.value}年${exportMonth.value}月_排班表.xlsx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(a.href)
    showExportPanel.value = false
  } catch (e) {
    alert(e?.message || '导出失败')
  } finally {
    exporting.value = false
  }
}
</script>

<style scoped>
.shift-page {
  width: 100%;
  max-width: none;
  padding: 0 0 var(--spacing-xl);
}
.shift-cap-toast {
  position: fixed;
  left: 50%;
  bottom: 28%;
  transform: translateX(-50%);
  z-index: 120;
  max-width: min(420px, 92vw);
  padding: 10px 16px;
  font-size: 13px;
  line-height: 1.45;
  color: #f8fafc;
  background: rgba(15, 23, 42, 0.92);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  pointer-events: none;
  text-align: center;
}
.shift-cap-toast-fade-enter-active,
.shift-cap-toast-fade-leave-active {
  transition: opacity 0.2s ease;
}
.shift-cap-toast-fade-enter-from,
.shift-cap-toast-fade-leave-to {
  opacity: 0;
}
.page-header { margin-bottom: var(--spacing-lg); text-align: left; }
/* 覆盖 global.css 中 .page-header .header-content 的 space-between，避免标题与规则块左右分列 */
.shift-page .page-header .header-content {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: flex-start;
  gap: 10px;
  width: 100%;
}
.header-info {
  width: 100%;
  text-align: left;
  align-items: flex-start;
}
.header-title { font-size: var(--font-size-xl); font-weight: var(--font-weight-bold); margin: 0; text-align: left; }
.header-subtitle { font-size: var(--font-size-sm); color: var(--color-text-tertiary); margin: 4px 0 0; line-height: 1.55; max-width: 960px; text-align: left; }

.header-rules {
  margin: 0;
  padding: 0;
  border: 1px solid var(--color-border-lighter, #e5e7eb);
  border-radius: var(--radius-md, 8px);
  background: #f8fafc;
  max-width: 960px;
  width: 100%;
  align-self: flex-start;
  text-align: left;
}
.header-rules-summary {
  cursor: pointer;
  list-style: none;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary, #475569);
  user-select: none;
  text-align: left;
}
.header-rules summary::-webkit-details-marker { display: none; }
.header-rules-summary::before {
  content: '▸ ';
  display: inline-block;
  transition: transform 0.15s;
  color: var(--color-primary, #3b82f6);
}
.header-rules[open] .header-rules-summary::before {
  transform: rotate(90deg);
}
.header-rules-body {
  padding: 0 14px 14px 14px;
  border-top: 1px solid #e2e8f0;
  max-height: min(52vh, 420px);
  overflow-y: auto;
}
.header-rules-section { margin-top: 12px; }
.header-rules-section:first-child { margin-top: 4px; }
.header-rules-h {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 700;
  color: var(--color-text-primary, #1e293b);
  letter-spacing: 0.02em;
}
.header-rules-body ul {
  margin: 0;
  padding-left: 1.15em;
  font-size: 12px;
  line-height: 1.65;
  color: var(--color-text-secondary, #64748b);
}
.header-rules-body li { margin-bottom: 6px; }
.header-rules-body li:last-child { margin-bottom: 0; }
.header-rules-body strong { color: #334155; font-weight: 600; }

.card {
  background: white;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-lighter);
  padding: var(--spacing-md) var(--spacing-lg);
  margin-bottom: var(--spacing-md);
}

/* 工具栏 */
.toolbar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.toolbar-left, .toolbar-right { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.toolbar-label { font-size: var(--font-size-sm); color: var(--color-text-secondary); }
.toolbar-select { padding: 4px 8px; border: 1px solid var(--color-border-base); border-radius: var(--radius-sm); font-size: var(--font-size-sm); }
.toolbar-month { font-weight: var(--font-weight-bold); font-size: var(--font-size-sm); min-width: 200px; max-width: 320px; text-align: center; line-height: 1.35; }
.btn { cursor: pointer; border: 1px solid var(--color-border-base); background: white; border-radius: var(--radius-sm); padding: 4px 12px; font-size: var(--font-size-sm); transition: all .15s; }
.btn:hover { background: var(--color-primary-lightest, #eff6ff); }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn-primary { background: var(--color-primary); color: white; border-color: var(--color-primary); }
.btn-primary:hover { opacity: .9; }
.btn-outline { background: white; border-color: var(--color-primary); color: var(--color-primary); }
.btn-danger-outline { background: white; border-color: #ef4444; color: #ef4444; }
.btn-danger-outline:hover { background: #fef2f2; }
.btn-sm { padding: 4px 10px; font-size: 13px; }

/* 配置面板 & 导出面板 */
.config-panel h3, .export-panel h3 { margin: 0 0 12px; font-size: var(--font-size-base); }
.config-dept { color: var(--color-primary); margin-left: 8px; }
.config-form { display: flex; align-items: flex-end; gap: 16px; flex-wrap: wrap; }
.export-panel select { padding: 4px 8px; border: 1px solid var(--color-border-base); border-radius: var(--radius-sm); }
.config-item { display: flex; flex-direction: column; gap: 4px; }
.config-item label { font-size: 12px; color: var(--color-text-secondary); }
.config-item input { width: 80px; padding: 4px 8px; border: 1px solid var(--color-border-base); border-radius: var(--radius-sm); text-align: center; }

/* 图例 */
.legend { display: flex; align-items: center; gap: 16px; margin-bottom: var(--spacing-sm); font-size: 13px; color: var(--color-text-secondary); flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 4px; }
.legend-dot { width: 14px; height: 14px; border-radius: 3px; display: inline-block; }
.legend-day { background: #dbeafe; border: 1px solid #93c5fd; }
.legend-night { background: #fef3c7; border: 1px solid #fbbf24; }
.legend-empty { background: white; border: 1px solid #d1d5db; }
.legend-sep { color: #d1d5db; }
.legend-hint { font-style: italic; color: #9ca3af; }

/* 排班网格 */
.schedule-wrap { padding: 0; overflow: hidden; }
.schedule-scroll { overflow-x: auto; overflow-y: auto; max-height: calc(100vh - 300px); }
.schedule-table {
  border-collapse: collapse;
  width: max-content;
  min-width: 100%;
  font-size: 13px;
  --shift-col-name: 72px;
  --shift-col-total: 44px;
  /* 表头三行纵向冻结：与首行/计划行/合计行实际高度对齐 */
  --schedule-head-r1: 63px;
  --schedule-head-r2: 56px;
  --sched-hl-row: rgba(191, 219, 254, 0.42);
  --sched-hl-col: rgba(191, 219, 254, 0.42);
  --sched-hl-cross: rgba(96, 165, 250, 0.38);
}
/* 鼠标悬浮：整行 + 整列淡蓝高亮，交叉格略深（类似 Excel） */
.schedule-table th.sched-hl-row,
.schedule-table td.sched-hl-row {
  background: var(--sched-hl-row) !important;
}
.schedule-table th.sched-hl-col,
.schedule-table td.sched-hl-col {
  background: var(--sched-hl-col) !important;
}
.schedule-table th.sched-hl-row.sched-hl-col,
.schedule-table td.sched-hl-row.sched-hl-col {
  background: var(--sched-hl-cross) !important;
}
.schedule-table th,
.schedule-table td { border: 1px solid #e5e7eb; text-align: center; white-space: nowrap; }
.schedule-table thead th {
  background: #f8fafc;
  position: sticky;
  top: 0;
  z-index: 3;
  padding: 4px 2px;
  font-weight: 500;
}
/* 日期表头行：顶边冻结（高度与 --schedule-head-r1 一致，避免与下方 sticky 错位） */
.schedule-table thead tr:first-child th {
  top: 0;
  z-index: 5;
  min-height: var(--schedule-head-r1);
  box-sizing: border-box;
}
/* 计划行：紧贴在首行之下冻结 */
.schedule-table thead tr.plan-row th {
  position: sticky;
  top: var(--schedule-head-r1);
  vertical-align: middle;
  padding: 6px 2px;
  background: #f0f9ff;
  border-bottom: 1px solid #bfdbfe;
  white-space: normal;
  font-weight: 500;
  min-height: 56px;
  height: 56px;
  z-index: 4;
}
.schedule-table thead tr.plan-row .sticky-col,
.schedule-table thead tr.plan-row .sticky-col2 {
  position: sticky;
  top: var(--schedule-head-r1);
  background: #eff6ff;
  z-index: 8;
}
/* 当日合计（表头第三行）：贴在计划行之下冻结 */
.schedule-table thead tr.summary-head-row th {
  position: sticky;
  top: calc(var(--schedule-head-r1) + var(--schedule-head-r2));
  z-index: 4;
  padding: 5px 2px;
  background: #f8fafc;
  font-weight: 500;
  vertical-align: middle;
  border-bottom: 1px solid #e5e7eb;
}
.schedule-table thead tr.summary-head-row .summary-head-day {
  white-space: normal;
}
.schedule-table thead tr.summary-head-row .sticky-col,
.schedule-table thead tr.summary-head-row .sticky-col2 {
  position: sticky;
  top: calc(var(--schedule-head-r1) + var(--schedule-head-r2));
  background: #f8fafc;
  z-index: 9;
}
.summary-head-label { font-size: 12px; text-align: left; }
.summary-head-stat { color: #cbd5e1; font-size: 11px; }
.plan-row-label {
  font-size: 11px;
  line-height: 1.2;
  color: #0369a1;
}
.plan-row-stat { color: #cbd5e1; font-size: 11px; }
.plan-cell {
  min-width: 36px;
  width: 36px;
  max-width: 36px;
  cursor: pointer;
  vertical-align: middle;
}
.plan-preview {
  display: block;
  font-size: 9px;
  line-height: 1.2;
  color: #1e40af;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding: 2px 1px;
  cursor: pointer;
}
.plan-empty-dot {
  display: block;
  font-size: 14px;
  color: #cbd5e1;
  cursor: pointer;
  line-height: 1;
}
.plan-has {
  background: #eff6ff !important;
}
.plan-cell:hover {
  background: #dbeafe !important;
}
/* 计划行：避免 hover / plan-has 盖住十字高亮 */
.schedule-table thead tr.plan-row th.plan-cell.sched-hl-row,
.schedule-table thead tr.plan-row th.plan-cell.sched-hl-col {
  background: var(--sched-hl-row) !important;
}
.schedule-table thead tr.plan-row th.plan-cell.sched-hl-row.sched-hl-col {
  background: var(--sched-hl-cross) !important;
}

/* 浮层编辑器 */
.plan-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
}
.plan-editor {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
  width: 420px;
  max-width: 90vw;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.plan-editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid #e5e7eb;
  background: #f8fafc;
}
.plan-editor-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}
.plan-editor-close {
  background: none;
  border: none;
  font-size: 22px;
  color: #94a3b8;
  cursor: pointer;
  line-height: 1;
  padding: 0 4px;
}
.plan-editor-close:hover { color: #ef4444; }
.plan-editor-textarea {
  margin: 14px 18px 10px;
  padding: 10px 12px;
  font-size: 14px;
  line-height: 1.6;
  min-height: 140px;
  max-height: 320px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  resize: vertical;
  box-sizing: border-box;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
}
.plan-editor-textarea:focus {
  outline: none;
  border-color: var(--color-primary, #3b82f6);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}
.plan-editor-textarea[readonly] {
  background: #f8fafc;
  color: #475569;
}
.plan-editor-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 18px 14px;
}
.plan-editor-hint {
  font-size: 12px;
  color: #94a3b8;
}
.th-day { font-size: 14px; font-weight: 600; line-height: 1.2; }
.th-weekday { font-size: 11px; color: #9ca3af; }
.th-sub { font-size: 11px; color: #9ca3af; font-weight: normal; }
.th-date-head { padding: 2px 1px 4px; vertical-align: middle; }
.th-holiday {
  font-size: 9px;
  line-height: 1.15;
  margin-top: 2px;
  max-width: 34px;
  margin-left: auto;
  margin-right: auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}
.th-holiday-work { color: #b45309; }
.th-holiday-rest { color: #64748b; }
.th-holiday-other { color: #0369a1; }
.legend-holiday-work { background: #fef3c7; border: 1px solid #d97706; }
.legend-holiday-rest { background: #f1f5f9; border: 1px solid #94a3b8; }
.legend-open { background: #dcfce7; border: 1px solid #4ade80; }

/* 日期开放 / 锁定 */
.col-open { background-color: #f0fdf4 !important; }
.th-lock-btn {
  display: inline-block;
  font-size: 9px;
  line-height: 1;
  margin-top: 2px;
  padding: 1px 4px;
  border-radius: 3px;
  cursor: pointer;
  user-select: none;
  background: #f1f5f9;
  color: #94a3b8;
  border: 1px solid #cbd5e1;
  transition: all .15s;
}
.th-lock-btn:hover { background: #e2e8f0; color: #475569; }
.th-lock-btn.th-lock-open {
  background: #dcfce7;
  color: #15803d;
  border-color: #86efac;
}
.th-lock-btn.th-lock-open:hover { background: #bbf7d0; }
.th-open-badge {
  font-size: 8px;
  line-height: 1;
  margin-top: 2px;
  padding: 1px 3px;
  border-radius: 3px;
  background: #dcfce7;
  color: #15803d;
  display: inline-block;
}
.th-past-badge {
  font-size: 8px;
  line-height: 1;
  margin-top: 2px;
  padding: 1px 3px;
  border-radius: 3px;
  background: #f1f5f9;
  color: #94a3b8;
  display: inline-block;
}
.col-past { opacity: 0.55; }

.btn-success-outline { background: white; border-color: #22c55e; color: #16a34a; }
.btn-success-outline:hover { background: #f0fdf4; }

.col-name {
  width: var(--shift-col-name);
  min-width: var(--shift-col-name);
  max-width: var(--shift-col-name);
  box-sizing: border-box;
  padding: 4px 3px;
  font-weight: 500;
  font-size: 12px;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
}
.schedule-table thead .th-sortable {
  cursor: pointer;
  user-select: none;
}
.schedule-table thead .th-sortable:hover {
  background: #eef2f7 !important;
}
.schedule-table thead .th-sort-ico {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-left: 4px;
  min-width: 22px;
  height: 20px;
  padding: 0 5px;
  border-radius: 5px;
  font-size: 13px;
  font-weight: 800;
  line-height: 1;
  color: #475569;
  background: linear-gradient(180deg, #e8eef5 0%, #dbe4f0 100%);
  border: 1px solid #cbd5e1;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
  vertical-align: middle;
  flex-shrink: 0;
}
.schedule-table thead .th-sort-ico.is-active {
  color: #fff;
  background: linear-gradient(180deg, var(--color-primary, #3b82f6) 0%, #2563eb 100%);
  border-color: #1d4ed8;
  box-shadow: 0 1px 2px rgba(37, 99, 235, 0.35);
}
.schedule-table thead .th-sortable:hover .th-sort-ico:not(.is-active) {
  border-color: #94a3b8;
  color: #334155;
}
.col-total {
  width: var(--shift-col-total);
  min-width: var(--shift-col-total);
  max-width: var(--shift-col-total);
  box-sizing: border-box;
  padding: 2px 1px;
  font-size: 11px;
  line-height: 1.15;
}
.col-day { width: 36px; min-width: 36px; max-width: 36px; padding: 0; }
.col-weekend { background: #fafaf9; }
.col-today { box-shadow: inset 0 0 0 2px var(--color-primary); }

.sticky-col {
  position: sticky;
  left: 0;
  z-index: 4;
  background: white;
}
.sticky-col2 {
  position: sticky;
  left: var(--shift-col-name);
  z-index: 4;
  background: white;
}
thead tr:first-child .sticky-col,
thead tr:first-child .sticky-col2 {
  z-index: 7;
  background: #f8fafc;
}

/* 单元格 */
.cell { cursor: pointer; height: 34px; transition: background .1s; user-select: none; }
.cell:hover { filter: brightness(.95); }
.cell-readonly { cursor: default; }
.cell-readonly:hover { filter: none; }
.cell-text { display: inline-block; width: 100%; line-height: 34px; font-weight: 600; font-size: 12px; }
.cell-day { background: #dbeafe; color: #1d4ed8; }
.cell-night { background: #fef3c7; color: #92400e; }
.cell-both { background: linear-gradient(135deg, #dbeafe 50%, #fef3c7 50%); color: #7c3aed; font-size: 11px; }
.cell-empty { background: white; color: transparent; }

.stat-day { color: #2563eb; font-weight: 600; }
.stat-night { color: #d97706; font-weight: 600; }

/* 表头内「当日合计」行（原 tfoot 上移） */
.summary-head-row .summary-cell { min-height: 28px; }
.summary-cell {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0;
  line-height: 1.2;
  font-size: 11px;
}
.summary-slash { color: #9ca3af; font-weight: 400; margin: 0 1px; user-select: none; }

.config-hint {
  margin: 12px 0 0;
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.55;
  color: var(--color-text-secondary);
  background: #f8fafc;
  border-radius: var(--radius-sm);
  border: 1px solid #e5e7eb;
}
.config-hint strong { color: var(--color-text-primary); }

.empty-state { text-align: center; padding: var(--spacing-xxl); color: var(--color-text-tertiary); }

/* 整月总览弹窗 */
.mo-overlay {
  position: fixed;
  inset: 0;
  z-index: 110;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  box-sizing: border-box;
}
.mo-panel {
  background: #fff;
  border-radius: var(--radius-md, 10px);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.2);
  border: 1px solid var(--color-border-lighter, #e5e7eb);
  width: min(1180px, 100%);
  max-height: min(92vh, 900px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.mo-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 14px 16px 10px;
  border-bottom: 1px solid #e5e7eb;
  background: #f8fafc;
}
.mo-header-left { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; min-width: 0; }
.mo-title { margin: 0; font-size: 17px; font-weight: 700; color: #1e293b; }
.mo-dept { font-size: 13px; color: var(--color-primary, #3b82f6); font-weight: 600; }
.mo-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #e0e7ff;
  color: #4338ca;
  font-weight: 600;
}
.mo-header-nav { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.mo-period { font-weight: 700; font-size: 13px; min-width: 88px; text-align: center; color: #334155; }
.mo-hint {
  margin: 0;
  padding: 8px 16px;
  font-size: 12px;
  color: #64748b;
  background: #fafafa;
  border-bottom: 1px solid #f1f5f9;
}
.mo-loading,
.mo-empty {
  padding: 32px 16px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}
.mo-scroll-wrap {
  overflow: auto;
  flex: 1;
  min-height: 120px;
  padding: 0 8px 12px;
}
.mo-table {
  border-collapse: collapse;
  font-size: 11px;
  width: max-content;
  min-width: 100%;
}
.mo-table th,
.mo-table td {
  border: 1px solid #e5e7eb;
  text-align: center;
  padding: 0;
  vertical-align: middle;
}
.mo-table thead th {
  background: #f1f5f9;
  position: sticky;
  top: 0;
  z-index: 2;
  padding: 2px 1px;
  font-weight: 600;
}
.mo-col-name {
  width: 72px;
  min-width: 72px;
  max-width: 72px;
  text-align: left;
  padding: 2px 4px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mo-col-stat {
  width: 40px;
  min-width: 40px;
  max-width: 40px;
  font-size: 10px;
  padding: 2px 1px;
}
.mo-col-day {
  width: 22px;
  min-width: 22px;
  max-width: 26px;
  padding: 2px 0;
}
.mo-th-day { font-size: 11px; font-weight: 700; line-height: 1.1; }
.mo-th-wd { font-size: 9px; color: #94a3b8; line-height: 1.1; }
.mo-th-holiday {
  font-size: 7px;
  line-height: 1.1;
  margin-top: 1px;
  max-width: 24px;
  margin-left: auto;
  margin-right: auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mo-sticky {
  position: sticky;
  left: 0;
  z-index: 3;
  background: #f8fafc;
}
.mo-sticky2 {
  position: sticky;
  left: 72px;
  z-index: 3;
  background: #f8fafc;
}
.mo-table thead .mo-sticky,
.mo-table thead .mo-sticky2 {
  z-index: 4;
  background: #f1f5f9;
}
.mo-table tbody .mo-sticky,
.mo-table tbody .mo-sticky2 {
  background: #fff;
}
.mo-summary-row .mo-sticky,
.mo-summary-row .mo-sticky2 {
  background: #f8fafc;
}
.mo-cell {
  height: 26px;
  cursor: default;
  user-select: none;
}
.mo-cell-text {
  display: inline-block;
  width: 100%;
  line-height: 26px;
  font-weight: 600;
  font-size: 10px;
}
.mo-cell-day { background: #dbeafe; color: #1d4ed8; }
.mo-cell-night { background: #fef3c7; color: #92400e; }
.mo-cell-empty { background: #fff; color: transparent; }
.mo-col-weekend { background: #fafaf9; }
.mo-col-today { box-shadow: inset 0 0 0 2px var(--color-primary, #3b82f6); }
.mo-summary-row td { background: #f8fafc; font-size: 10px; }
.mo-summary-cell { padding: 2px 0; }
.mo-slash { color: #9ca3af; margin: 0 1px; }

/* 视图切换按钮组 */
.mo-view-toggle {
  display: inline-flex;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  overflow: hidden;
  margin-left: 6px;
}
.mo-toggle-btn {
  border: none;
  background: #fff;
  color: #475569;
  font-size: 12px;
  padding: 3px 14px;
  cursor: pointer;
  font-weight: 500;
  transition: all .15s;
}
.mo-toggle-btn + .mo-toggle-btn { border-left: 1px solid #cbd5e1; }
.mo-toggle-btn.active {
  background: var(--color-primary, #3b82f6);
  color: #fff;
  font-weight: 600;
}
.mo-toggle-btn:hover:not(.active) { background: #f1f5f9; }

/* ---- 日历视图 ---- */
.cal-wrap { padding: 12px 16px 16px !important; }

.cal-legend {
  display: flex;
  gap: 16px;
  margin-bottom: 10px;
  font-size: 12px;
  color: #475569;
}
.cal-legend-item { display: flex; align-items: center; gap: 5px; }
.cal-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
}
.cal-dot-day { background: #3b82f6; }
.cal-dot-night { background: #f59e0b; }
.cal-dot-off { background: #e5e7eb; }

.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
  background: #e2e8f0;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
}

.cal-weekday-header {
  background: #f1f5f9;
  text-align: center;
  font-size: 12px;
  font-weight: 700;
  color: #475569;
  padding: 8px 0;
}

.cal-day-cell {
  background: #fff;
  min-height: 90px;
  display: flex;
  flex-direction: column;
  padding: 4px 5px;
  position: relative;
  transition: background .15s;
}
.cal-day-cell:hover:not(.cal-blank) { background: #f8fafc; }
.cal-blank { background: #fafafa; min-height: 0; }
.cal-weekend { background: #fefce8; }
.cal-weekend:hover { background: #fef9c3; }
.cal-today {
  box-shadow: inset 0 0 0 2px var(--color-primary, #3b82f6);
  z-index: 1;
}

.cal-day-num {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 3px;
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}
.cal-holiday-tag {
  font-size: 9px;
  padding: 1px 4px;
  border-radius: 3px;
  font-weight: 500;
  white-space: nowrap;
}
.cal-plan-chip {
  margin-left: auto;
  font-size: 9px;
  line-height: 1;
  padding: 2px 4px;
  border-radius: 3px;
  background: #dbeafe;
  color: #1d4ed8;
  font-weight: 600;
  border: 1px solid #93c5fd;
}

.cal-day-people { flex: 1; overflow-y: auto; }

.cal-shift-row {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  margin-bottom: 2px;
  line-height: 1.35;
}
.cal-shift-label {
  flex-shrink: 0;
  display: inline-block;
  width: 18px;
  height: 18px;
  line-height: 18px;
  text-align: center;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 700;
  color: #fff;
}
.cal-shift-day .cal-shift-label { background: #3b82f6; }
.cal-shift-night .cal-shift-label { background: #f59e0b; }
.cal-shift-names {
  font-size: 11px;
  color: #334155;
  line-height: 18px;
  word-break: break-all;
}
.cal-shift-empty {
  font-size: 10px;
  color: #cbd5e1;
  text-align: center;
  padding-top: 6px;
}

.cal-plan-popover {
  display: none;
  position: absolute;
  left: 6px;
  right: 6px;
  bottom: calc(100% - 2px);
  z-index: 20;
  background: rgba(15, 23, 42, 0.97);
  color: #f8fafc;
  border-radius: 8px;
  padding: 8px 10px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.35);
  border: 1px solid rgba(148, 163, 184, 0.35);
}
.cal-day-cell:hover .cal-plan-popover { display: block; }
.cal-plan-title {
  font-size: 11px;
  font-weight: 700;
  color: #93c5fd;
  margin-bottom: 4px;
}
.cal-plan-text {
  font-size: 11px;
  line-height: 1.45;
  max-height: 140px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 768px) {
  .toolbar { flex-direction: column; align-items: flex-start; }
  .schedule-scroll { max-height: calc(100vh - 360px); }
  .cal-day-cell { min-height: 70px; padding: 3px; }
  .cal-shift-names { font-size: 10px; }
}
</style>
