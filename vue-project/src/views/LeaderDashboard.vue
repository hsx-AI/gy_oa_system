<template>
  <div class="leader-dashboard-page">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">管理驾驶舱</h1>
          <p class="header-subtitle">本科室请假、加班、公出汇总，按人查看</p>
        </div>
        <div class="header-actions">
          <router-link v-if="canAccessLeaderOvertimeEntry" to="/leader-overtime-statistics" class="btn btn-leader-ot">
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6v6l4 2"/>
            </svg>
            领导加班统计
          </router-link>
          <router-link to="/attendance/discipline" class="btn btn-discipline">
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
            考勤纪律审查
          </router-link>
          <button type="button" class="btn btn-public-dashboard" @click="openPublicDashboard">
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="7" height="7" rx="1"/>
              <rect x="14" y="3" width="7" height="7" rx="1"/>
              <rect x="3" y="14" width="7" height="7" rx="1"/>
              <rect x="14" y="14" width="7" height="7" rx="1"/>
            </svg>
            员工信息驾驶舱
          </button>
        </div>
      </div>
    </div>

    <div class="container">
      <!-- 无科室权限提示 -->
      <div v-if="!canViewDept" class="no-permission card">
        <div class="no-permission-content">
          <svg class="no-permission-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <h3>暂无科室数据权限</h3>
          <p>您当前仅可查看个人统计。科室维度汇总需组长/主任/部长等权限。</p>
          <router-link to="/statistics" class="btn btn-primary">前往统计汇总</router-link>
        </div>
      </div>

      <template v-else>
        <!-- 筛选 -->
        <div class="filter-section card">
          <div class="filter-form">
            <div class="form-item">
              <label class="form-label">隶属科室</label>
              <!-- 部长/副部长：下拉选择全员或任意科室 -->
              <select
                v-if="permLevel === 3"
                v-model="selectedLsys"
                class="form-select"
                :disabled="!lsysList.length"
              >
                <option value="">全员</option>
                <option v-for="d in lsysList" :key="d" :value="d">{{ d }}</option>
              </select>
              <!-- 组长/主任等：仅显示本科室 -->
              <input
                v-else
                :value="lsys"
                type="text"
                class="form-input"
                readonly
              />
            </div>
            <div class="form-item">
              <label class="form-label">年份</label>
              <select v-model="filterYear" class="form-select">
                <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option>
              </select>
            </div>
            <div class="form-item">
              <label class="form-label">月份</label>
              <select v-model="filterMonth" class="form-select">
                <option value="">全年</option>
                <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
              </select>
            </div>
            <div class="form-item form-actions">
              <button class="btn btn-primary" @click="fetchData" :disabled="loading">
                <svg v-if="loading" class="loading-icon" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="31.4" stroke-linecap="round">
                    <animateTransform attributeName="transform" type="rotate" dur="1s" from="0 12 12" to="360 12 12" repeatCount="indefinite"/>
                  </circle>
                </svg>
                <span>{{ loading ? '加载中...' : '查询' }}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- ====== 考勤总览 ====== -->
        <div class="section card overview-section">
          <h2 class="section-title">考勤总览</h2>
          <div class="dashboard-cards">
            <div class="dashboard-card leave-card">
              <div class="dashboard-card-header">
                <svg class="dashboard-card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                  <line x1="16" y1="2" x2="16" y2="6"/>
                  <line x1="8" y1="2" x2="8" y2="6"/>
                  <line x1="3" y1="10" x2="21" y2="10"/>
                </svg>
                <h3>{{ showHxLeaveOnly ? '换休请假汇总' : '请假汇总' }}</h3>
                <button
                  class="ot-toggle-btn"
                  :class="{ active: showHxLeaveOnly }"
                  type="button"
                  @click="toggleHxLeaveOnly"
                  title="点击在全部请假与仅换休、员工换休票之间切换"
                >
                  切换换休请假
                </button>
              </div>
              <div class="dashboard-card-body">
                <div class="dashboard-total clickable trend-anchor" @click="goLeave()" title="点击查看全部请假记录">
                  <span class="total-value">{{ leaveStats.totalDays ?? '-' }}</span>
                  <span class="total-unit">天</span>
                  <div v-if="isFullYear && trendLeave" class="trend-popover trend-popover-leave">
                    <div class="trend-pop-title">{{ filterYear }}年月度{{ showHxLeaveOnly ? '换休请假' : '请假' }}趋势（天）</div>
                    <svg class="trend-svg" :viewBox="`0 0 ${TREND_W} ${TREND_H}`" preserveAspectRatio="xMidYMid meet">
                      <line v-for="(t, i) in trendLeave.yTicks" :key="'yl-' + i" :x1="TREND_PAD.l" :x2="TREND_W - TREND_PAD.r" :y1="t.y" :y2="t.y" class="trend-grid"/>
                      <text v-for="(t, i) in trendLeave.yTicks" :key="'yt-' + i" :x="TREND_PAD.l - 4" :y="t.y + 3" class="trend-y-label">{{ t.label }}</text>
                      <path :d="trendLeave.areaD" class="trend-area trend-area-leave"/>
                      <path :d="trendLeave.pathD" class="trend-line trend-line-leave"/>
                      <template v-for="p in trendLeave.points" :key="'lp-' + p.month">
                        <circle :cx="p.x" :cy="p.y" r="3.5" class="trend-dot trend-dot-leave"/>
                        <text :x="p.x" :y="p.y - 8" text-anchor="middle" class="trend-dot-val">{{ p.v }}</text>
                      </template>
                      <text v-for="p in trendLeave.points" :key="'lm-' + p.month" :x="p.x" :y="TREND_H - 4" text-anchor="middle" class="trend-x-label">{{ p.month }}月</text>
                    </svg>
                  </div>
                </div>
                <div class="dashboard-meta">共 {{ leaveStats.personCount ?? 0 }} 人</div>
                <div v-if="showHxLeaveOnly" class="ot-net-hint">仅统计类型为「换休」「员工换休票」的已通过请假（按天）</div>
                <div v-if="leaveStats.list?.length" class="dashboard-list">
                  <div class="list-title">按人明细</div>
                  <ul class="person-list">
                    <li v-for="(item, idx) in leaveStats.list" :key="item.name" class="person-item clickable" @click="goLeave(item.name)" :title="`点击查看 ${item.name} 的请假记录`">
                      <span class="person-name"><span class="person-rank">{{ idx + 1 }}</span>{{ item.name }}</span>
                      <span class="person-value">{{ item.days }} 天</span>
                    </li>
                  </ul>
                </div>
                <router-link :to="leaveAllRecordsLink" class="card-detail-link">查看全部记录 →</router-link>
              </div>
            </div>

            <div class="dashboard-card overtime-card">
              <div class="dashboard-card-header">
                <svg class="dashboard-card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
                <h3>{{ showNetOvertime ? '净加班' : '加班汇总' }}</h3>
                <button class="ot-toggle-btn" :class="{ active: showNetOvertime }" @click="toggleNetOvertime" title="净加班 = 加班时长 − 换休请假时长，点击在总加班与净加班之间切换">
                  切换净加班
                </button>
              </div>
              <div class="dashboard-card-body">
                <div class="dashboard-total clickable trend-anchor" @click="goOvertime()" title="点击查看全部加班记录">
                  <span class="total-value">{{ overtimeStats.totalHours ?? '-' }}</span>
                  <span class="total-unit">小时</span>
                  <span
                    v-if="overtimeStats.autoCalculatedHours != null"
                    class="auto-ot-badge"
                    :class="{ 'auto-ot-badge--zero': !overtimeStats.autoCalculatedHours }"
                    :title="`按打卡数据自动识别的加班时长（与工作强度/部办加班统计同算法）；${overtimeStats.autoCalculatedPersonCount ?? 0} 人有识别记录`"
                  >自动计算数 {{ overtimeStats.autoCalculatedHours }}h</span>
                  <div v-if="isFullYear && trendOvertime" class="trend-popover trend-popover-overtime">
                    <div class="trend-pop-title">{{ filterYear }}年月度{{ showNetOvertime ? '净加班' : '加班' }}趋势（小时）</div>
                    <svg class="trend-svg" :viewBox="`0 0 ${TREND_W} ${TREND_H}`" preserveAspectRatio="xMidYMid meet">
                      <line v-for="(t, i) in trendOvertime.yTicks" :key="'yl-' + i" :x1="TREND_PAD.l" :x2="TREND_W - TREND_PAD.r" :y1="t.y" :y2="t.y" class="trend-grid"/>
                      <text v-for="(t, i) in trendOvertime.yTicks" :key="'yt-' + i" :x="TREND_PAD.l - 4" :y="t.y + 3" class="trend-y-label">{{ t.label }}</text>
                      <path :d="trendOvertime.areaD" class="trend-area trend-area-overtime"/>
                      <path :d="trendOvertime.pathD" class="trend-line trend-line-overtime"/>
                      <template v-for="p in trendOvertime.points" :key="'op-' + p.month">
                        <circle :cx="p.x" :cy="p.y" r="3.5" class="trend-dot trend-dot-overtime"/>
                        <text :x="p.x" :y="p.y - 8" text-anchor="middle" class="trend-dot-val">{{ p.v }}</text>
                      </template>
                      <text v-for="p in trendOvertime.points" :key="'om-' + p.month" :x="p.x" :y="TREND_H - 4" text-anchor="middle" class="trend-x-label">{{ p.month }}月</text>
                    </svg>
                  </div>
                </div>
                <div class="dashboard-meta">共 {{ overtimeStats.personCount ?? 0 }} 人 <span class="meta-sub">· {{ overtimeStats.totalTimes ?? 0 }} 次</span></div>
                <div v-if="showNetOvertime" class="ot-net-hint">加班时长 − 换休请假时长</div>
                <div v-if="overtimeStats.list?.length" class="dashboard-list">
                  <div class="list-title">按人明细</div>
                  <ul class="person-list">
                    <li v-for="(item, idx) in overtimeStats.list" :key="item.name" class="person-item clickable" @click="goOvertime(item.name)" :title="`点击查看 ${item.name} 的加班记录`">
                      <span class="person-name"><span class="person-rank">{{ idx + 1 }}</span>{{ item.name }}</span>
                      <span class="person-value">
                        {{ item.hours }} 小时
                        <span
                          v-if="item.autoHours != null"
                          class="person-auto-ot"
                          :class="{ 'person-auto-ot--zero': !item.autoHours }"
                          :title="`按智能建议加班规则识别 ${item.autoHours} 小时`"
                        >· 自动计算 {{ item.autoHours }}h</span>
                      </span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>

            <div class="dashboard-card trip-card">
              <div class="dashboard-card-header">
                <svg class="dashboard-card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/>
                  <circle cx="12" cy="10" r="3"/>
                </svg>
                <h3>公出汇总</h3>
              </div>
              <div class="dashboard-card-body">
                <div class="dashboard-total clickable trend-anchor" @click="goTrip()" title="点击查看全部公出记录">
                  <span class="total-value">{{ tripStats.totalDays ?? '-' }}</span>
                  <span class="total-unit">天</span>
                  <div v-if="isFullYear && trendTrip" class="trend-popover trend-popover-trip">
                    <div class="trend-pop-title">{{ filterYear }}年月度公出趋势（天）</div>
                    <svg class="trend-svg" :viewBox="`0 0 ${TREND_W} ${TREND_H}`" preserveAspectRatio="xMidYMid meet">
                      <line v-for="(t, i) in trendTrip.yTicks" :key="'yl-' + i" :x1="TREND_PAD.l" :x2="TREND_W - TREND_PAD.r" :y1="t.y" :y2="t.y" class="trend-grid"/>
                      <text v-for="(t, i) in trendTrip.yTicks" :key="'yt-' + i" :x="TREND_PAD.l - 4" :y="t.y + 3" class="trend-y-label">{{ t.label }}</text>
                      <path :d="trendTrip.areaD" class="trend-area trend-area-trip"/>
                      <path :d="trendTrip.pathD" class="trend-line trend-line-trip"/>
                      <template v-for="p in trendTrip.points" :key="'tp-' + p.month">
                        <circle :cx="p.x" :cy="p.y" r="3.5" class="trend-dot trend-dot-trip"/>
                        <text :x="p.x" :y="p.y - 8" text-anchor="middle" class="trend-dot-val">{{ p.v }}</text>
                      </template>
                      <text v-for="p in trendTrip.points" :key="'tm-' + p.month" :x="p.x" :y="TREND_H - 4" text-anchor="middle" class="trend-x-label">{{ p.month }}月</text>
                    </svg>
                  </div>
                </div>
                <div class="dashboard-meta">共 {{ tripStats.personCount ?? 0 }} 人</div>
                <div v-if="tripStats.list?.length" class="dashboard-list">
                  <div class="list-title">按人明细</div>
                  <ul class="person-list">
                    <li v-for="(item, idx) in tripStats.list" :key="item.name" class="person-item clickable" @click="goTrip(item.name)" :title="`点击查看 ${item.name} 的公出记录`">
                      <span class="person-name"><span class="person-rank">{{ idx + 1 }}</span>{{ item.name }}</span>
                      <span class="person-value">{{ item.days }} 天</span>
                    </li>
                  </ul>
                </div>
                <router-link :to="tripAllRecordsLink" class="card-detail-link">查看全部记录 →</router-link>
              </div>
            </div>
          </div>

          <!-- 科室横向对比（内嵌在考勤总览中） -->
          <div v-if="hasFetched && deptComparison.list?.length" class="overview-comparison">
            <div class="fa-divider"></div>
            <h3 class="fa-chart-title">科室横向对比</h3>
            <p class="section-desc">各科室加班、请假、公出（可选月份为当月，未选为全年）</p>
            <div class="chart-filter-row">
              <label class="chart-filter-label">展示</label>
              <div class="chart-type-tabs">
                <button
                  v-for="t in compareChartTypes"
                  :key="t.type"
                  :class="['tab-btn', 'tab-btn-sm', { active: compareChartType === t.type }]"
                  @click="compareChartType = t.type"
                >
                  {{ t.label }}{{ t.unit }}
                </button>
              </div>
            </div>
            <div class="bar-chart-wrap">
              <div class="bar-chart-total bar-chart-single">
                <div v-for="row in deptComparisonSorted" :key="row.lsys" class="bar-group">
                  <div class="bar-col">
                    <div
                      class="bar bar-has-value"
                      :class="[compareChartBarClass, { 'bar-negative': compareChartTotalValue(row) < 0 }]"
                      :style="{ height: getCompareBarHeight(compareChartTotalValue(row), compareChartMaxTotal) }"
                      :title="compareChartTotalTitle(row)"
                    >
                      <span class="bar-value">{{ compareChartTotalValue(row) }}</span>
                    </div>
                  </div>
                  <div class="bar-label">{{ row.lsys }}</div>
                </div>
              </div>
            </div>
            <div class="chart-subtitle-row">
              <h3 class="chart-subtitle">{{ compareChartPcSubtitle }}</h3>
              <button
                v-if="compareChartType === 'overtime' || compareChartType === 'netOvertime'"
                class="ot-toggle-btn pc-dim-btn"
                :class="{ active: pcNetMode }"
                @click="pcNetMode = !pcNetMode"
                title="净人均 = 总加班 / (工作日×人数 − 公出天数)"
              >{{ pcNetMode ? '切换人均' : '切换净人均' }}</button>
            </div>
            <div v-if="pcNetMode && (compareChartType === 'overtime' || compareChartType === 'netOvertime')" class="ot-net-hint" style="margin-bottom:8px">
              公式：总加班 ÷（工作日 × 科室人数 − 科室公出天数），剔除公出人天后的实际在岗人均
            </div>
            <div class="bar-chart-wrap">
              <div class="bar-chart-total bar-chart-single">
                <div v-for="row in deptComparisonSortedPc" :key="'pc-' + row.lsys" class="bar-group">
                  <div class="bar-col">
                    <div
                      class="bar bar-has-value"
                      :class="[compareChartBarClass, { 'bar-negative': compareChartPerCapitaValue(row) < 0 }]"
                      :style="{ height: getCompareBarHeight(compareChartPerCapitaValue(row), compareChartMaxPc) }"
                      :title="compareChartPerCapitaTitle(row)"
                    >
                      <span class="bar-value">{{ compareChartPerCapitaValue(row) }}</span>
                    </div>
                  </div>
                  <div class="bar-label">{{ row.lsys }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ====== 满勤统计 ====== -->
        <div v-if="hasFetched" class="section card full-attendance-section">
          <h2 class="section-title">
            <span>满勤统计</span>
            <span class="section-sub">{{ filterYear }}年{{ filterMonth ? filterMonth + '月' : '全年' }}</span>
          </h2>
          <p class="section-desc">根据打卡数据识别，考勤异常全部由公出覆盖或无异常即视为满勤。</p>

          <div v-if="fullAttendance.totalPeople != null" class="full-attendance-content">
            <div class="full-attendance-summary">
              <div v-if="fullAttendance.workdays != null" class="fa-item">
                <span class="fa-label">应出勤工作日</span>
                <span class="fa-value">{{ fullAttendance.workdays }} 天</span>
              </div>
              <div class="fa-item">
                <span class="fa-label">全员满勤率</span>
                <span class="fa-value">{{ ((fullAttendance.rate ?? 0) * 100).toFixed(1) }}%</span>
                <span class="fa-meta">满勤 {{ fullAttendance.fullCount ?? 0 }} / {{ fullAttendance.totalPeople ?? 0 }} 人</span>
              </div>
            </div>
            <div v-if="byDeptSortedByRate.length" class="full-attendance-depts">
              <div class="fa-dept-title">各科室满勤率（悬停或聚焦卡片查看满勤名单，按满勤率从高到低排列）</div>
              <div class="fa-dept-grid">
                <div
                  v-for="d in byDeptSortedByRate"
                  :key="d.lsys"
                  class="fa-dept-card-wrap"
                  tabindex="0"
                >
                  <div class="fa-dept-card">
                    <span class="fa-dept-name">{{ d.lsys }}</span>
                    <span class="fa-dept-rate">{{ (d.rate * 100).toFixed(1) }}%</span>
                    <span class="fa-dept-meta">{{ d.fullCount }}/{{ d.totalPeople }} 人</span>
                  </div>
                  <div class="fa-dept-tooltip" role="tooltip">
                    <div class="fa-tooltip-title">{{ d.lsys }} · 满勤 {{ d.fullCount }} 人</div>
                    <ul v-if="deptFullNames(d).length" class="fa-tooltip-names">
                      <li v-for="nm in deptFullNames(d)" :key="nm">{{ nm }}</li>
                    </ul>
                    <p v-else-if="d.fullCount > 0" class="fa-tooltip-empty">满勤名单未加载，请点击「查询」刷新</p>
                    <p v-else class="fa-tooltip-empty">本科室暂无满勤人员</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="fa-divider"></div>

          <h3 class="fa-chart-title">满勤人数柱状图</h3>
          <div class="chart-filter-row">
            <label class="chart-filter-label">科室</label>
            <select v-model="chartLsys" class="form-select chart-filter-select" @change="fetchFullAttendanceChart">
              <option value="">全部</option>
              <option v-for="d in chartDeptOptions" :key="d" :value="d">{{ d }}</option>
            </select>
            <span class="chart-filter-hint">{{ filterYear }}年 · 横轴月，纵轴满勤人数</span>
          </div>
          <div class="bar-chart-wrap full-count-chart">
            <div class="bar-chart-months">
              <div v-for="item in fullAttendanceByMonthFiltered" :key="item.month" class="bar-month-group">
                <div class="bar-month-area">
                  <div
                    class="bar-month-bar"
                    :style="{ height: getFullCountBarHeightPx(item.fullCount, maxFullCountChart) }"
                    :title="`${item.monthLabel} 满勤 ${item.fullCount} 人`"
                  >
                    <span v-if="item.fullCount > 0" class="bar-month-value">{{ item.fullCount }}</span>
                  </div>
                </div>
                <div class="bar-month-label">{{ item.monthLabel }}</div>
              </div>
            </div>
          </div>
        </div>


        <!-- ====== 工作强度统计 ====== -->
        <div v-if="hasFetched && workIntensity.totalPeople" class="section card wi-section">
          <h2 class="section-title">
            <span>工作强度统计</span>
            <span class="section-sub">{{ wiSectionSubtitle }}</span>
          </h2>
          <p class="section-desc">{{ wiFormulaDesc }}</p>
          <div class="wi-formula-bar">
            <span class="wi-formula-label">口径</span>
            <button
              type="button"
              class="wi-formula-btn"
              :class="{ active: wiIntensityFormula === 'a' }"
              @click="setWiIntensityFormula('a')"
            >A</button>
            <button
              type="button"
              class="wi-formula-btn"
              :class="{ active: wiIntensityFormula === 'b' }"
              @click="setWiIntensityFormula('b')"
            >B</button>
          </div>

          <div class="wi-range-toolbar">
            <label class="wi-range-check">
              <input v-model="wiUseDateRange" type="checkbox" @change="onWiRangeToggle" />
              自定义日期区间
            </label>
            <template v-if="wiUseDateRange">
              <div class="wi-range-inputs">
                <input v-model="wiDateFrom" type="date" class="form-input wi-date-input" />
                <span class="wi-range-sep">至</span>
                <input v-model="wiDateTo" type="date" class="form-input wi-date-input" />
              </div>
              <button type="button" class="btn btn-primary wi-range-apply" :disabled="loading || !wiDateFrom || !wiDateTo" @click="fetchWorkIntensityOnly">
                按区间重算
              </button>
            </template>
            <button
              type="button"
              class="btn btn-outline wi-export-btn"
              :disabled="!canExportWorkIntensity"
              @click="exportWorkIntensityTable"
            >
              导出表格
            </button>
            <p v-if="wiUseDateRange && wiRangeError" class="wi-range-error">{{ wiRangeError }}</p>
          </div>

          <div class="wi-summary">
            <div class="wi-summary-item">
              <span class="wi-label">应出勤工作日</span>
              <span class="wi-value">{{ workIntensity.workdays }} 天</span>
            </div>
            <div class="wi-summary-item">
              <span class="wi-label">统计人数</span>
              <span class="wi-value">{{ workIntensity.totalPeople }} 人</span>
            </div>
            <div class="wi-summary-item wi-summary-highlight">
              <span class="wi-label">全员工作强度</span>
              <span class="wi-value">{{ (workIntensity.overallIntensity * 100).toFixed(1) }}%</span>
            </div>
            <div v-if="!filterMonth && !wiUseDateRange && wiMonthly.length >= 2" class="wi-sparkline-wrap">
              <span class="wi-label">月度趋势</span>
              <svg class="wi-sparkline" viewBox="0 0 280 68" preserveAspectRatio="none">
                <path :d="wiSparklinePoints" fill="none" stroke="#c2410c" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
                <template v-for="(dot, di) in wiSparklineDots" :key="di">
                  <circle :cx="dot.x" :cy="dot.y" r="3" fill="#c2410c" stroke="white" stroke-width="1.5"/>
                  <text :x="dot.x" :y="dot.y - 6" :text-anchor="dot.anchor" class="sparkline-val">{{ dot.pct }}</text>
                </template>
              </svg>
              <div class="wi-sparkline-labels">
                <span v-for="d in wiMonthly" :key="d.month" class="wi-sparkline-m">{{ d.month }}月</span>
              </div>
            </div>
          </div>

          <div class="wi-tabs">
            <button
              type="button"
              class="wi-tab"
              :class="{ active: wiViewMode === 'dept' }"
              @click="wiViewMode = 'dept'"
            >按科室</button>
            <button
              type="button"
              class="wi-tab"
              :class="{ active: wiViewMode === 'person' }"
              @click="wiViewMode = 'person'"
            >按个人</button>
          </div>

          <div v-if="wiViewMode === 'person' && wiByPersonRawScoped.length" class="wi-person-filters">
            <label class="wi-person-filter-item">
              <span>职务</span>
              <select v-model="wiJobFilter" class="form-input wi-job-filter-select">
                <option value="">全部职务</option>
                <option :value="WI_JOB_FILTER_ALL_MANAGERS">全体管理人员</option>
                <option :value="WI_JOB_FILTER_ZHUREN_ZRZE">主任/主任责</option>
                <option :value="WI_JOB_FILTER_FUZHUREN">副主任</option>
                <option v-for="jb in wiJobOptions" :key="jb" :value="jb">{{ jb }}</option>
              </select>
            </label>
          </div>

          <div v-if="wiViewMode === 'dept' && wiByDeptScoped.length" class="wi-dept-grid">
            <div v-for="d in wiByDeptScoped" :key="d.lsys" class="wi-dept-card">
              <div class="wi-dept-name">{{ d.lsys }}</div>
              <div class="wi-dept-intensity">{{ (d.intensity * 100).toFixed(1) }}%</div>
              <div class="wi-dept-meta">
                {{ d.personCount }}人 · 加班{{ d.overtimeHours }}h<span v-if="wiIsFormulaB"> · 请假{{ d.leaveHours ?? 0 }}h</span> · 境内境外公出{{ d.tripDays }}天
              </div>
            </div>
          </div>

          <div v-if="wiViewMode === 'person' && wiByPersonRawScoped.length" class="wi-person-table-wrap">
            <table class="wi-person-table">
              <thead>
                <tr>
                  <th class="th-rank">序号</th>
                  <th class="wi-th-sort" @click="toggleWiSort('name')">
                    姓名 <span class="wi-sort-ind">{{ wiSortIndicator('name') }}</span>
                  </th>
                  <th>科室</th>
                  <th class="wi-th-sort" @click="toggleWiSort('jb')">
                    职务 <span class="wi-sort-ind">{{ wiSortIndicator('jb') }}</span>
                  </th>
                  <th class="wi-th-sort" @click="toggleWiSort('overtimeHours')">
                    加班(h) <span class="wi-sort-ind">{{ wiSortIndicator('overtimeHours') }}</span>
                  </th>
                  <th v-if="wiIsFormulaB" class="wi-th-sort" @click="toggleWiSort('leaveHours')">
                    请假(h) <span class="wi-sort-ind">{{ wiSortIndicator('leaveHours') }}</span>
                  </th>
                  <th class="wi-th-sort" @click="toggleWiSort('actualHours')">
                    实际在岗(h) <span class="wi-sort-ind">{{ wiSortIndicator('actualHours') }}</span>
                  </th>
                  <th class="wi-th-sort" @click="toggleWiSort('intensity')">
                    工作强度 <span class="wi-sort-ind">{{ wiSortIndicator('intensity') }}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(p, idx) in wiByPersonFilteredSorted" :key="p.name">
                  <td class="td-rank">{{ idx + 1 }}</td>
                  <td>{{ p.name }}</td>
                  <td>{{ p.lsys }}</td>
                  <td>{{ p.jb || '-' }}</td>
                  <td class="td-num">{{ p.overtimeHours }}</td>
                  <td v-if="wiIsFormulaB" class="td-num">{{ p.leaveHours ?? 0 }}</td>
                  <td class="td-num">{{ p.actualHours }}</td>
                  <td class="td-num td-intensity">{{ (p.intensity * 100).toFixed(1) }}%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 未查询时的提示 -->
        <div v-if="!hasFetched && !loading" class="init-hint card">
          <p>选择年份（可选月份）后点击「查询」查看本科室汇总、满勤率、科室对比与全员排序。</p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as XLSX from 'xlsx'
import {
  getStatisticsPermission,
  getDeptLsysList,
  getDeptLeaveStats,
  getDeptOvertimeStats,
  getDeptBusinessTripStats,
  getLeaderFullAttendance,
  getLeaderFullAttendanceYear,
  getLeaderFullAttendanceByMonth,
  getLeaderDeptComparison,
  getLeaderWorkIntensity,
  getUploadConfig,
} from '@/api/attendance'
import { isMinisterLevel } from '@/utils/roleMatch'

const router = useRouter()
const PUBLIC_DASHBOARD_URL = 'http://10.42.60.230:8088/public-dashboard'

function openPublicDashboard() {
  window.open(PUBLIC_DASHBOARD_URL, '_blank', 'noopener,noreferrer')
}

const leaderOtAdmin1 = ref('')
const leaderOtAdmin2 = ref('')
const canAccessLeaderOvertimeEntry = computed(() => {
  try {
    const info = JSON.parse(localStorage.getItem('userInfo') || '{}')
    const name = (info.name || info.userName || '').trim()
    const jb = (info.jb || '').trim()
    const a1 = (leaderOtAdmin1.value || '').trim()
    const a2 = (leaderOtAdmin2.value || '').trim()
    if ((a1 && name === a1) || (a2 && name === a2)) return true
    return isMinisterLevel(jb)
  } catch {
    return false
  }
})
const lsys = ref('')
const permLevel = ref(1)
/** 部长/副部长可选任意科室；组长/主任仅本科室，与 lsys 一致 */
const selectedLsys = ref('')
const lsysList = ref([])
const canViewDept = computed(() => (permLevel.value === 2 && !!lsys.value) || permLevel.value === 3)

const filterYear = ref(new Date().getFullYear())
/** 默认当前月，便于进入看板即看当月数据 */
const filterMonth = ref(new Date().getMonth() + 1)
const loading = ref(false)
const hasFetched = ref(false)

const leaveStats = ref({})
const overtimeStats = ref({})
const showHxLeaveOnly = ref(false)
const showNetOvertime = ref(false)
const tripStats = ref({})

const fullAttendance = ref({})
const fullAttendanceByMonth = ref([])
const chartLsys = ref('')
const deptComparison = ref({ list: [] })
const compareChartType = ref('overtime')
const pcNetMode = ref(false)
const compareChartTypes = [
  { type: 'overtime', label: '加班', unit: '(小时)' },
  { type: 'netOvertime', label: '净加班', unit: '(小时)' },
  { type: 'leave', label: '请假', unit: '(天)' },
  { type: 'trip', label: '公出', unit: '(天)' }
]

const monthlyLeave = ref([])
const monthlyOvertime = ref([])
const monthlyTrip = ref([])

const isFullYear = computed(() => !filterMonth.value)

const TREND_W = 340
const TREND_H = 120
const TREND_PAD = { l: 40, r: 16, t: 18, b: 22 }

function _buildTrendChart(data, unit) {
  if (!data.length) return null
  const vals = data.map(d => d.value)
  const max = Math.max(...vals, 0.01)
  const min = Math.min(...vals, 0)
  const range = max - min || 1
  const usableW = TREND_W - TREND_PAD.l - TREND_PAD.r
  const usableH = TREND_H - TREND_PAD.t - TREND_PAD.b

  const points = vals.map((v, i) => {
    const x = TREND_PAD.l + (data.length > 1 ? (i / (data.length - 1)) * usableW : usableW / 2)
    const y = TREND_PAD.t + (1 - (v - min) / range) * usableH
    return { x, y, v, month: data[i].month }
  })

  const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  const areaD = pathD + ` L${points[points.length - 1].x.toFixed(1)},${TREND_H - TREND_PAD.b} L${points[0].x.toFixed(1)},${TREND_H - TREND_PAD.b} Z`

  const yTicks = []
  const steps = 4
  for (let i = 0; i <= steps; i++) {
    const val = min + (range * i) / steps
    const y = TREND_PAD.t + (1 - i / steps) * usableH
    yTicks.push({ y, label: val >= 1000 ? (val / 1000).toFixed(1) + 'k' : Number.isInteger(val) ? String(val) : val.toFixed(1) })
  }

  return { points, pathD, areaD, yTicks, unit }
}

const trendLeave = computed(() => _buildTrendChart(monthlyLeave.value, '天'))
const trendOvertime = computed(() => _buildTrendChart(monthlyOvertime.value, '小时'))
const trendTrip = computed(() => _buildTrendChart(monthlyTrip.value, '天'))

const workIntensity = ref({})
/** 工作强度请求序号：快速切换科室/口径时丢弃过期响应，避免列表与当前筛选不一致 */
let workIntensityFetchSeq = 0
const wiUseDateRange = ref(false)
const wiDateFrom = ref('')
const wiDateTo = ref('')
const wiRangeError = ref('')
const wiViewMode = ref('dept')
const wiMonthly = ref([])
const wiSortKey = ref('intensity')
const wiSortOrder = ref('desc')
const wiJobFilter = ref('')
const wiIntensityFormula = ref('a')

/** 工作强度口径 B：与后端 /leader/work-intensity intensity_formula=b 一致 */
const wiIsFormulaB = computed(() => wiIntensityFormula.value === 'b')

/** 与 yggl.jb 一致：部长、副部长、经理、副经理等部级/公司经理层可看详细公式；各室主任/副主任等仅看摘要（与 getStatisticsPermission 能进驾驶舱的人员不完全等同） */
const canSeeWiFormulaDetail = computed(() => {
  try {
    const info = JSON.parse(localStorage.getItem('userInfo') || '{}')
    const jb = (info.jb || '').trim()
    if (!jb) return false
    return isMinisterLevel(jb)
  } catch {
    return false
  }
})

const WI_FORMULA_CONFIDENTIAL_NOTE = '（本公示仅正副职部长、经理层可见；科室主任/副主任不展示本条具体算式）'

const wiFormulaDesc = computed(() => {
  const full = canSeeWiFormulaDetail.value
  if (wiIntensityFormula.value === 'b') {
    if (full) {
      return '口径 B：工作强度 =（加班时长 − 请假时间）÷ 实际在岗时长；加班时长由打卡数据自动识别（与部办加班统计一致）。请假时间为统计期内已通过请假按天重叠分摊后×8（小时），与请假汇总一致。实际在岗 = 应出勤时长 − 公出时长 + 公出期间节假日时长；公出时长仅计境内/境外公出（不含市内公出）。' + WI_FORMULA_CONFIDENTIAL_NOTE
    }
    return '口径 B：在统计期内，按「加班相对在岗」并兼顾已通过请假影响折算的强度指标；具体核算方式内部掌握。'
  }
  if (full) {
    return '口径 A：工作强度 = 加班时长 ÷ 实际在岗时长；加班时长由打卡数据自动识别（与部办加班统计一致）。实际在岗 = 应出勤时长 − 公出时长 + 公出期间节假日时长；公出时长仅计境内/境外公出（不含市内公出）。' + WI_FORMULA_CONFIDENTIAL_NOTE
  }
  return '口径 A：在统计期内，按加班时长相对实际在岗时长的强度指标；具体核算方式内部掌握。'
})

const WI_JOB_CATEGORY_ORDER = ['部领导', '总师', '责任工艺师', '主任及副主任', '班组长', '无']
/** 筛选专用：主任/副主任/班组长等合并类下的全体管理人员 */
const WI_JOB_FILTER_ALL_MANAGERS = '全体管理人员'
/** 筛选专用：仅主任或主任责（不含副主任，因「副主任」含「主任」子串） */
const WI_JOB_FILTER_ZHUREN_ZRZE = '主任/主任责'
/** 筛选专用：仅副主任 */
const WI_JOB_FILTER_FUZHUREN = '副主任'

function wiJobMatchesZhurenOrZrze(jbRaw) {
  const jb = (jbRaw || '').trim()
  if (!jb || jb.includes('副主任')) return false
  return jb.includes('主任')
}

function wiJobMatchesFuzhurenOnly(jbRaw) {
  return (jbRaw || '').trim().includes('副主任')
}

function wiJobIsBuLingdao(jb) {
  const s = jb || ''
  return (
    s.includes('副部长')
    || s.includes('部长')
    || s.includes('副经理')
    || s.includes('经理')
  )
}

function wiJobDisplayCategory(jbRaw, lsysRaw) {
  const jb = (jbRaw || '').trim()
  const dept = (lsysRaw || '').trim()
  const isBanban = dept === '部办'

  if (isBanban) {
    if (wiJobIsBuLingdao(jb)) return '部领导'
    return '总师'
  }

  if (jb.includes('返聘')) return '无'

  if (jb.includes('责任工艺师') || jb.includes('责任师') || jb.includes('责工师')) return '责任工艺师'

  if (jb.includes('副主任') || jb.includes('主任责') || jb.includes('主任')) return '主任及副主任'

  if (jb.includes('班组长') || jb.includes('组长')) return '班组长'

  if (!jb || jb === '无' || jb.includes('员工')) return '无'

  return '无'
}

const WI_SPARK_W = 280
const WI_SPARK_H = 68
const WI_SPARK_LEFT = 16
const WI_SPARK_RIGHT = 16
const WI_SPARK_TOP = 14
const WI_SPARK_BOT = 4

function _wiSparkCalc() {
  const data = wiMonthly.value
  if (!data || data.length < 2) return null
  const vals = data.map(d => d.intensity * 100)
  const max = Math.max(...vals, 1)
  const min = Math.min(...vals, 0)
  const range = max - min || 1
  return { vals, max, min, range }
}

const wiSparklinePoints = computed(() => {
  const c = _wiSparkCalc()
  if (!c) return ''
  return c.vals.map((v, i) => {
    const x = WI_SPARK_LEFT + (i / (c.vals.length - 1)) * (WI_SPARK_W - WI_SPARK_LEFT - WI_SPARK_RIGHT)
    const y = WI_SPARK_TOP + (1 - (v - c.min) / c.range) * (WI_SPARK_H - WI_SPARK_TOP - WI_SPARK_BOT)
    return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
})

const wiSparklineDots = computed(() => {
  const c = _wiSparkCalc()
  if (!c) return []
  const data = wiMonthly.value
  return c.vals.map((v, i) => {
    const x = WI_SPARK_LEFT + (i / (c.vals.length - 1)) * (WI_SPARK_W - WI_SPARK_LEFT - WI_SPARK_RIGHT)
    const y = WI_SPARK_TOP + (1 - (v - c.min) / c.range) * (WI_SPARK_H - WI_SPARK_TOP - WI_SPARK_BOT)
    const anchor = i === 0 ? 'start' : (i === c.vals.length - 1 ? 'end' : 'middle')
    return { x, y, anchor, pct: v.toFixed(1) + '%', label: `${data[i].month}月: ${v.toFixed(1)}%` }
  })
})

const wiSectionSubtitle = computed(() => {
  const wi = workIntensity.value
  if (wi?.rangeMode && wi.dateFrom && wi.dateTo) {
    const line = `${wi.dateFrom} ~ ${wi.dateTo}`
    if (wi.effectiveDateTo && wi.effectiveDateTo !== wi.dateTo) {
      return `${line}（统计截止 ${wi.effectiveDateTo}）`
    }
    return line
  }
  return `${filterYear.value}年${filterMonth.value ? filterMonth.value + '月' : '全年'}`
})

/** 部长在筛选里选中具体科室时，仅展示该科室行，防止请求竞态导致混入其他科室人员 */
function wiSelectedDeptTrim() {
  if (permLevel.value === 3) return (selectedLsys.value || '').trim()
  return (lsys.value || '').trim()
}

function filterWiRowsBySelectedDept(rows) {
  const scope = wiSelectedDeptTrim()
  if (!scope || !Array.isArray(rows)) return rows || []
  return rows.filter((r) => (r?.lsys || '').trim() === scope)
}

const wiByPersonRawScoped = computed(() => filterWiRowsBySelectedDept(workIntensity.value?.byPerson || []))
const wiByDeptScoped = computed(() => filterWiRowsBySelectedDept(workIntensity.value?.byDept || []))

const canExportWorkIntensity = computed(() => {
  const wi = workIntensity.value || {}
  const byD = filterWiRowsBySelectedDept(wi.byDept || [])
  const byP = filterWiRowsBySelectedDept(wi.byPerson || [])
  return !!(wi.totalPeople && (byD.length || byP.length))
})

function roundForExport(value, digits = 2) {
  const n = Number(value || 0)
  return Number(n.toFixed(digits))
}

function percentForExport(value) {
  return `${roundForExport(Number(value || 0) * 100, 1)}%`
}

function workIntensityDeptActualHours(row) {
  if (row?.actualHours != null && row.actualHours !== '') {
    return roundForExport(row.actualHours)
  }
  const expected = Number(workIntensity.value?.expectedHoursPerPerson || 0)
  const count = Number(row?.personCount || 0)
  const tripDays = Number(row?.tripDays || 0)
  const holidayTripDays = Number(row?.tripHolidayDays || 0)
  return roundForExport(expected * count - tripDays * 8 + holidayTripDays * 8)
}

/** 工作强度导出/汇总用全员明细（不受职务筛选影响） */
function wiAllPersonsForTotals() {
  return filterWiRowsBySelectedDept(workIntensity.value?.byPerson || [])
}

function appendAoASheet(wb, name, rows, widths = []) {
  const sheet = XLSX.utils.aoa_to_sheet(rows)
  if (widths.length) {
    sheet['!cols'] = widths.map(wch => ({ wch }))
  }
  XLSX.utils.book_append_sheet(wb, sheet, name)
}

function formatWiExportFileName() {
  const scope = ((permLevel.value === 3 ? selectedLsys.value : lsys.value) || '全员').replace(/[\\/:*?"<>|]+/g, '_')
  const range = wiSectionSubtitle.value.replace(/[\\/:*?"<>|()\s]+/g, '_').replace(/^_+|_+$/g, '')
  const suf = wiIntensityFormula.value === 'b' ? '口径B' : '口径A'
  return `工作强度统计_${scope}_${range || filterYear.value}_${suf}.xlsx`
}

async function loadLeaderWorkIntensity(lsysToUse) {
  const seq = ++workIntensityFetchSeq
  wiRangeError.value = ''
  const wiParams = {
    year: filterYear.value,
    intensity_formula: wiIntensityFormula.value,
  }
  if (lsysToUse) wiParams.lsys = lsysToUse
  const useWiRange = wiUseDateRange.value && wiDateFrom.value && wiDateTo.value
  if (useWiRange) {
    wiParams.date_from = wiDateFrom.value
    wiParams.date_to = wiDateTo.value
  } else if (filterMonth.value) {
    wiParams.month = parseInt(filterMonth.value, 10)
  }
  const wiRes = await getLeaderWorkIntensity(wiParams)
  if (seq !== workIntensityFetchSeq) return
  if (wiRes?.success) {
    workIntensity.value = wiRes
  } else {
    throw new Error('工作强度接口未返回成功')
  }

  const month = filterMonth.value ? parseInt(filterMonth.value, 10) : undefined
  if (!month && !useWiRange) {
    const today = new Date()
    const year = filterYear.value
    const maxM = year < today.getFullYear() ? 12 : today.getMonth() + 1
    const monthPromises = []
    for (let m = 1; m <= maxM; m++) {
      const mp = { year, month: m, intensity_formula: wiIntensityFormula.value }
      if (lsysToUse) mp.lsys = lsysToUse
      monthPromises.push(
        getLeaderWorkIntensity(mp).then(r => ({ month: m, intensity: r?.overallIntensity ?? 0 })).catch(() => ({ month: m, intensity: 0 })),
      )
    }
    const monthly = await Promise.all(monthPromises)
    if (seq !== workIntensityFetchSeq) return
    wiMonthly.value = monthly
  } else {
    if (seq !== workIntensityFetchSeq) return
    wiMonthly.value = []
  }
}

async function setWiIntensityFormula(v) {
  const x = v === 'b' ? 'b' : 'a'
  if (wiIntensityFormula.value === x) return
  wiIntensityFormula.value = x
  if (!hasFetched.value) return
  const lsysToUse = permLevel.value === 3 ? selectedLsys.value : lsys.value
  if (permLevel.value !== 3 && !lsysToUse) return
  loading.value = true
  try {
    await loadLeaderWorkIntensity(lsysToUse)
  } catch (e) {
    console.error('工作强度加载失败:', e)
    if (wiUseDateRange.value) wiRangeError.value = '加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function exportWorkIntensityTable() {
  if (!canExportWorkIntensity.value) {
    alert('暂无可导出的工作强度数据')
    return
  }

  const wi = workIntensity.value || {}
  const b = wiIntensityFormula.value === 'b'
  const deptRows = filterWiRowsBySelectedDept(wi.byDept || []).map((row, idx) => {
    const cells = [
      idx + 1,
      row.lsys || '',
      row.personCount ?? 0,
      roundForExport(row.overtimeHours),
    ]
    if (b) cells.push(roundForExport(row.leaveHours ?? 0))
    cells.push(
      roundForExport(row.tripDays),
      roundForExport(row.tripHolidayDays),
      workIntensityDeptActualHours(row),
      percentForExport(row.intensity),
    )
    return cells
  })
  const allPersons = wiAllPersonsForTotals()
  const totalOvertimeHours = wi.totalOvertimeHours != null
    ? Number(wi.totalOvertimeHours)
    : allPersons.reduce((sum, p) => sum + Number(p.overtimeHours || 0), 0)
  const totalActualHours = wi.totalActualHours != null
    ? Number(wi.totalActualHours)
    : allPersons.reduce((sum, p) => sum + Number(p.actualHours || 0), 0)
  const totalLeaveH = b
    ? (wi.totalLeaveHours != null
        ? Number(wi.totalLeaveHours)
        : allPersons.reduce((sum, p) => sum + Number(p.leaveHours || 0), 0))
    : 0
  const overallPct = totalActualHours > 0
    ? (b ? (totalOvertimeHours - totalLeaveH) / totalActualHours : totalOvertimeHours / totalActualHours)
    : 0

  const personRows = wiByPersonFilteredSorted.value.map((row, idx) => {
    const cells = [
      idx + 1,
      row.name || '',
      row.lsys || '',
      row.jb || '',
      roundForExport(row.overtimeHours),
    ]
    if (b) cells.push(roundForExport(row.leaveHours ?? 0))
    cells.push(
      roundForExport(row.tripDays),
      roundForExport(row.tripHolidayDays),
      roundForExport(row.actualHours),
      percentForExport(row.intensity),
    )
    return cells
  })

  const sumDeptCount = deptRows.reduce((s, row) => s + Number(row[2] || 0), 0)
  const sumDeptOt = deptRows.reduce((s, row) => s + Number(row[3] || 0), 0)
  const deptActualCol = b ? 7 : 6
  const sumDeptActual = deptRows.reduce((s, row) => s + Number(row[deptActualCol] || 0), 0)
  const sumDeptLeave = b ? deptRows.reduce((s, row) => s + Number(row[4] || 0), 0) : 0

  const overviewRows = [
    ['统计项', '数值'],
    ['统计范围', wiSectionSubtitle.value],
    ['导出范围', (permLevel.value === 3 ? selectedLsys.value : lsys.value) || '全员'],
    ['应出勤工作日（天）', wi.workdays ?? 0],
    ['应出勤时长/人（h）', wi.expectedHoursPerPerson ?? 0],
    ['统计人数（人）', wi.totalPeople ?? 0],
    ['全员加班（h）', roundForExport(totalOvertimeHours)],
  ]
  if (b) {
    overviewRows.push(['全员请假（h）', roundForExport(totalLeaveH)])
    overviewRows.push(['全员（加班−请假）（h）', roundForExport(totalOvertimeHours - totalLeaveH)])
  }
  overviewRows.push(
    ['全员实际在岗（h）', roundForExport(totalActualHours)],
    ['全员工作强度', percentForExport(overallPct)],
    ['各科室加班合计（h）', roundForExport(sumDeptOt)],
    ['各科室在岗合计（h）', roundForExport(sumDeptActual)],
  )
  if (wiJobFilter.value) {
    overviewRows.push(['说明', '「按个人」sheet 受职务筛选；概览与各科室为全员口径'])
  }

  const wb = XLSX.utils.book_new()
  appendAoASheet(wb, '统计概览', overviewRows, [24, 48])
  const deptHead = ['序号', '科室', '人数', '加班（h）']
  if (b) deptHead.push('请假（h）')
  deptHead.push('公出（天，不含市内）', '公出期间节假日（天，不含市内）', '实际在岗（h）', '工作强度')
  const deptColW = [8, 24, 10, 12, ...(b ? [12] : []), 12, 20, 14, 12]
  const deptFoot = ['', '各科室合计', sumDeptCount, roundForExport(sumDeptOt)]
  if (b) deptFoot.push(roundForExport(sumDeptLeave))
  deptFoot.push('', '', roundForExport(sumDeptActual), '')
  appendAoASheet(wb, '按科室', [deptHead, ...deptRows, deptFoot], deptColW)
  const personHead = ['序号', '姓名', '科室', '职务', '加班（h）']
  if (b) personHead.push('请假（h）')
  personHead.push('公出（天，不含市内）', '公出期间节假日（天，不含市内）', '实际在岗（h）', '工作强度')
  const personColW = [8, 14, 24, 16, 12, ...(b ? [12] : []), 12, 20, 14, 12]
  appendAoASheet(wb, '按个人', [personHead, ...personRows], personColW)
  XLSX.writeFile(wb, formatWiExportFileName())
}

function pad2(n) {
  return String(n).padStart(2, '0')
}

function syncWiRangeDefaultsFromFilter() {
  const y = filterYear.value
  const m = filterMonth.value ? parseInt(filterMonth.value, 10) : null
  const today = new Date()
  const ty = today.getFullYear()
  const tm = today.getMonth() + 1
  const td = today.getDate()
  if (m) {
    wiDateFrom.value = `${y}-${pad2(m)}-01`
    const lastDay = new Date(y, m, 0).getDate()
    wiDateTo.value = `${y}-${pad2(m)}-${pad2(lastDay)}`
  } else {
    wiDateFrom.value = `${y}-01-01`
    if (y < ty) wiDateTo.value = `${y}-12-31`
    else if (y === ty) wiDateTo.value = `${y}-${pad2(tm)}-${pad2(td)}`
    else wiDateTo.value = `${y}-12-31`
  }
}

function onWiRangeToggle() {
  wiRangeError.value = ''
  if (wiUseDateRange.value) syncWiRangeDefaultsFromFilter()
}

async function fetchWorkIntensityOnly() {
  wiRangeError.value = ''
  if (!wiDateFrom.value || !wiDateTo.value) {
    wiRangeError.value = '请选择开始日期与结束日期'
    return
  }
  const lsysToUse = permLevel.value === 3 ? selectedLsys.value : lsys.value
  if (permLevel.value !== 3 && !lsysToUse) return
  loading.value = true
  try {
    await loadLeaderWorkIntensity(lsysToUse)
  } catch (e) {
    console.error('工作强度加载失败:', e)
    wiRangeError.value = '加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

const wiByPersonSorted = computed(() => {
  const list = [...wiByPersonRawScoped.value]
  const key = wiSortKey.value
  const desc = wiSortOrder.value === 'desc'

  /** 主键相同（尤其工作强度同为 0）时：实际在岗更高的靠前，实际在岗为 0 的沉底 */
  function tieBreakActualHours(a, b) {
    const aah = Number(a?.actualHours ?? 0)
    const bah = Number(b?.actualHours ?? 0)
    if (aah !== bah) return bah - aah
    return String(a?.name || '').localeCompare(String(b?.name || ''), 'zh-CN')
  }

  list.sort((a, b) => {
    if (key === 'jb') {
      const ca = String(a?.jb || '').trim()
      const cb = String(b?.jb || '').trim()
      const c = desc
        ? cb.localeCompare(ca, 'zh-CN')
        : ca.localeCompare(cb, 'zh-CN')
      if (c !== 0) return c
      return tieBreakActualHours(a, b)
    }
    const av = a?.[key]
    const bv = b?.[key]
    if (key === 'name') {
      const c = desc
        ? String(bv || '').localeCompare(String(av || ''), 'zh-CN')
        : String(av || '').localeCompare(String(bv || ''), 'zh-CN')
      if (c !== 0) return c
      return tieBreakActualHours(a, b)
    }
    const na = Number(av || 0)
    const nb = Number(bv || 0)
    const primary = desc ? nb - na : na - nb
    if (primary !== 0) return primary
    return tieBreakActualHours(a, b)
  })
  return list
})

const wiJobOptions = computed(() => {
  const set = new Set()
  wiByPersonRawScoped.value.forEach((row) => {
    set.add(wiJobDisplayCategory(row?.jb, row?.lsys))
  })
  return WI_JOB_CATEGORY_ORDER.filter(label => set.has(label))
})

const wiByPersonFilteredSorted = computed(() => {
  const selected = (wiJobFilter.value || '').trim()
  if (!selected) return wiByPersonSorted.value
  if (selected === WI_JOB_FILTER_ALL_MANAGERS) {
    return wiByPersonSorted.value.filter((row) => {
      const c = wiJobDisplayCategory(row?.jb, row?.lsys)
      return c === '主任及副主任' || c === '班组长'
    })
  }
  if (selected === WI_JOB_FILTER_ZHUREN_ZRZE) {
    return wiByPersonSorted.value.filter(row => wiJobMatchesZhurenOrZrze(row?.jb))
  }
  if (selected === WI_JOB_FILTER_FUZHUREN) {
    return wiByPersonSorted.value.filter(row => wiJobMatchesFuzhurenOnly(row?.jb))
  }
  return wiByPersonSorted.value.filter(
    row => wiJobDisplayCategory(row?.jb, row?.lsys) === selected,
  )
})

function toggleWiSort(key) {
  if (wiSortKey.value === key) {
    wiSortOrder.value = wiSortOrder.value === 'desc' ? 'asc' : 'desc'
    return
  }
  wiSortKey.value = key
  wiSortOrder.value = (key === 'name' || key === 'jb') ? 'asc' : 'desc'
}

function wiSortIndicator(key) {
  if (wiSortKey.value !== key) return '↕'
  return wiSortOrder.value === 'desc' ? '↓' : '↑'
}

const EXCLUDED_LSYS_SET = new Set(['其他部门员工', '其他部门成员'])

function isAllowedLsys(v) {
  return !EXCLUDED_LSYS_SET.has((v || '').trim())
}

const maxCompareOvertime = computed(() => {
  const list = deptComparison.value?.list || []
  if (!list.length) return 1
  return Math.max(...list.map(r => r.overtimeTotal), 1)
})
const maxCompareNetOvertime = computed(() => {
  const list = deptComparison.value?.list || []
  if (!list.length) return 1
  return Math.max(...list.map(r => Math.abs(r.netOvertimeTotal || 0)), 1)
})
const maxCompareLeave = computed(() => {
  const list = deptComparison.value?.list || []
  if (!list.length) return 1
  return Math.max(...list.map(r => r.leaveTotal), 1)
})
const maxCompareTrip = computed(() => {
  const list = deptComparison.value?.list || []
  if (!list.length) return 1
  return Math.max(...list.map(r => r.tripTotal), 1)
})
const maxCompareOvertimePc = computed(() => {
  const list = deptComparison.value?.list || []
  if (!list.length) return 1
  return Math.max(...list.map(r => r.overtimePerCapita), 0.01)
})
const maxCompareNetOvertimePc = computed(() => {
  const list = deptComparison.value?.list || []
  if (!list.length) return 1
  return Math.max(...list.map(r => Math.abs(r.netOvertimePerCapita || 0)), 0.01)
})
const maxCompareLeavePc = computed(() => {
  const list = deptComparison.value?.list || []
  if (!list.length) return 1
  return Math.max(...list.map(r => r.leavePerCapita), 0.01)
})
const maxCompareTripPc = computed(() => {
  const list = deptComparison.value?.list || []
  if (!list.length) return 1
  return Math.max(...list.map(r => r.tripPerCapita), 0.01)
})

function getCompareBarHeight(value, max) {
  if (value == null || !max) return '0%'
  const pct = (Math.abs(value) / max) * 100
  return `${Math.max(pct, 4)}%`
}

const compareChartBarClass = computed(() => {
  if (compareChartType.value === 'overtime') return 'bar-ot'
  if (compareChartType.value === 'netOvertime') return 'bar-not'
  if (compareChartType.value === 'leave') return 'bar-lv'
  return 'bar-tr'
})
/** 科室横向对比：按当前展示类型（加班/请假/公出）数值从高到低排序，柱状图从左到右由高到低 */
const deptComparisonSorted = computed(() => {
  const list = (deptComparison.value?.list || []).filter(r => isAllowedLsys(r?.lsys))
  if (!list.length) return []
  return [...list].sort((a, b) => (compareChartTotalValue(b) - compareChartTotalValue(a)))
})
const deptComparisonSortedPc = computed(() => {
  const list = (deptComparison.value?.list || []).filter(r => isAllowedLsys(r?.lsys))
  if (!list.length) return []
  return [...list].sort((a, b) => (compareChartPerCapitaValue(b) - compareChartPerCapitaValue(a)))
})
const compareChartMaxTotal = computed(() => {
  if (compareChartType.value === 'overtime') return maxCompareOvertime.value
  if (compareChartType.value === 'netOvertime') return maxCompareNetOvertime.value
  if (compareChartType.value === 'leave') return maxCompareLeave.value
  return maxCompareTrip.value
})
const maxCompareOvertimeWd = computed(() => {
  const list = deptComparison.value?.list || []
  if (!list.length) return 0.01
  return Math.max(...list.map(r => Math.abs(r.overtimePerWorkday || 0)), 0.01)
})
const maxCompareNetOvertimeWd = computed(() => {
  const list = deptComparison.value?.list || []
  if (!list.length) return 0.01
  return Math.max(...list.map(r => Math.abs(r.netOvertimePerWorkday || 0)), 0.01)
})
const compareChartMaxPc = computed(() => {
  const useWd = pcNetMode.value && (compareChartType.value === 'overtime' || compareChartType.value === 'netOvertime')
  if (compareChartType.value === 'overtime') return useWd ? maxCompareOvertimeWd.value : maxCompareOvertimePc.value
  if (compareChartType.value === 'netOvertime') return useWd ? maxCompareNetOvertimeWd.value : maxCompareNetOvertimePc.value
  if (compareChartType.value === 'leave') return maxCompareLeavePc.value
  return maxCompareTripPc.value
})
function compareChartTotalValue(row) {
  if (compareChartType.value === 'overtime') return row.overtimeTotal
  if (compareChartType.value === 'netOvertime') return row.netOvertimeTotal || 0
  if (compareChartType.value === 'leave') return row.leaveTotal
  return row.tripTotal
}
function compareChartPerCapitaValue(row) {
  const useWorkday = pcNetMode.value && (compareChartType.value === 'overtime' || compareChartType.value === 'netOvertime')
  if (compareChartType.value === 'overtime') return useWorkday ? (row.overtimePerWorkday || 0) : row.overtimePerCapita
  if (compareChartType.value === 'netOvertime') return useWorkday ? (row.netOvertimePerWorkday || 0) : (row.netOvertimePerCapita || 0)
  if (compareChartType.value === 'leave') return row.leavePerCapita
  return row.tripPerCapita
}
function compareChartTotalTitle(row) {
  const v = compareChartTotalValue(row)
  const t = compareChartType.value
  if (t === 'overtime') return `加班 ${v} 小时`
  if (t === 'netOvertime') return `净加班 ${v} 小时`
  return `${compareChartTypes.find(c => c.type === t)?.label || ''} ${v} 天`
}
function compareChartPerCapitaTitle(row) {
  const v = compareChartPerCapitaValue(row)
  const t = compareChartType.value
  const wd = pcNetMode.value && (t === 'overtime' || t === 'netOvertime')
  if (t === 'overtime') return wd ? `净人均加班 ${v} 小时/人天` : `人均加班 ${v} 小时`
  if (t === 'netOvertime') return wd ? `净人均净加班 ${v} 小时/人天` : `人均净加班 ${v} 小时`
  return `人均${compareChartTypes.find(c => c.type === t)?.label || ''} ${v} 天`
}

const compareChartPcSubtitle = computed(() => {
  const t = compareChartType.value
  const wd = pcNetMode.value && (t === 'overtime' || t === 'netOvertime')
  if (t === 'overtime') return wd ? '净人均每天加班（去公出人天）' : '人均每天加班'
  if (t === 'netOvertime') return wd ? '净人均每天净加班（去公出人天）' : '人均每天净加班'
  if (t === 'leave') return '人均每天请假'
  return '人均每天公出'
})

const yearOptions = computed(() => {
  const currentYear = new Date().getFullYear()
  const years = []
  for (let y = currentYear; y >= currentYear - 5; y--) years.push(y)
  return years
})

const chartDeptOptions = computed(() => {
  if (permLevel.value === 3) return lsysList.value
  return lsys.value ? [lsys.value] : []
})

const leaveAllRecordsLink = computed(() => {
  const q = { tab: 'leave', from: 'leader', view: 'ledger' }
  if (filterYear.value) q.year = filterYear.value
  if (filterMonth.value) q.month = filterMonth.value
  return { path: '/attendance/manual', query: q }
})
const tripAllRecordsLink = computed(() => {
  const q = { from: 'leader', view: 'ledger' }
  if (filterYear.value) q.year = filterYear.value
  if (filterMonth.value) q.month = filterMonth.value
  return { path: '/attendance/business-trip', query: q }
})

function goLeave(personName) {
  const q = { tab: 'leave', from: 'leader', view: 'ledger' }
  if (filterYear.value) q.year = filterYear.value
  if (filterMonth.value && !personName) q.month = filterMonth.value
  if (personName) q.focusName = personName
  router.push({ path: '/attendance/manual', query: q })
}
function goOvertime(personName) {
  const q = { tab: 'overtime', from: 'leader' }
  if (filterYear.value) q.year = filterYear.value
  if (filterMonth.value && !personName) q.month = filterMonth.value
  if (personName) q.focusName = personName
  router.push({ path: '/attendance/manual', query: q })
}
function goTrip(personName) {
  const q = { from: 'leader', view: 'ledger' }
  if (filterYear.value) q.year = filterYear.value
  if (filterMonth.value && !personName) q.month = filterMonth.value
  if (personName) q.focusName = personName
  router.push({ path: '/attendance/business-trip', query: q })
}

/** 满勤柱状图只显示已过去的月份（当年只显示到当前月，未来年不显示） */
const fullAttendanceByMonthFiltered = computed(() => {
  const list = fullAttendanceByMonth.value
  if (!list.length) return []
  const now = new Date()
  const currentYear = now.getFullYear()
  const currentMonth = now.getMonth() + 1
  const y = filterYear.value
  if (y > currentYear) return []
  if (y < currentYear) return list
  return list.filter((item) => item.month <= currentMonth)
})

const maxFullCountChart = computed(() => {
  const list = fullAttendanceByMonthFiltered.value
  if (!list.length) return 1
  return Math.max(...list.map(i => i.fullCount), 1)
})

/** 满勤柱状图柱区固定高度(px)，所有柱子在此高度内按比例绘制，底部对齐 */
const FULL_COUNT_BAR_AREA_PX = 180

function getFullCountBarHeightPx(value, max) {
  if (value == null || !max) return '8px'
  const pct = value / max
  const px = Math.max(8, Math.round(pct * FULL_COUNT_BAR_AREA_PX))
  return `${px}px`
}

/** 科室满勤卡片：后端 byDept 项含 fullNames（与导出逻辑一致） */
function deptFullNames(d) {
  return Array.isArray(d?.fullNames) ? d.fullNames : []
}

const byDeptSortedByRate = computed(() => {
  const list = (fullAttendance.value?.byDept || []).filter(d => isAllowedLsys(d?.lsys))
  if (!list?.length) return []
  return [...list].sort((a, b) => (b.rate || 0) - (a.rate || 0))
})

const fetchFullAttendanceChart = async () => {
  try {
    const res = await getLeaderFullAttendanceByMonth({
      year: filterYear.value,
      lsys: chartLsys.value || undefined
    })
    if (res.success && res.list) fullAttendanceByMonth.value = res.list
    else fullAttendanceByMonth.value = []
  } catch (e) {
    fullAttendanceByMonth.value = []
  }
}

const loadPermission = async () => {
  const savedUser = localStorage.getItem('userInfo')
  if (!savedUser) return
  try {
    const user = JSON.parse(savedUser)
    const name = user.name || user.userName
    if (!name) return
    const res = await getStatisticsPermission({ name })
    if (res.success) {
      permLevel.value = res.level ?? 1
      lsys.value = (res.lsys || '').trim()
      if (permLevel.value === 2) {
        selectedLsys.value = lsys.value
      } else if (permLevel.value === 3) {
        const listRes = await getDeptLsysList()
        if (listRes.success && listRes.list?.length) {
          lsysList.value = listRes.list.filter(isAllowedLsys)
          selectedLsys.value = '' // 默认全员
        }
      }
    }
  } catch (e) {
    permLevel.value = 1
    lsys.value = ''
    selectedLsys.value = ''
    lsysList.value = []
  }
}

const fetchData = async () => {
  const lsysToUse = permLevel.value === 3 ? selectedLsys.value : lsys.value
  // 部长可选全员(空)；组长/主任必须有科室
  if (permLevel.value !== 3 && !lsysToUse) return
  loading.value = true
  hasFetched.value = true
  const params = { year: filterYear.value }
  if (lsysToUse) params.lsys = lsysToUse
  if (filterMonth.value) params.month = parseInt(filterMonth.value)
  const year = filterYear.value
  const month = filterMonth.value ? parseInt(filterMonth.value) : undefined
  try {
    const [
      leaveRes,
      overtimeRes,
      tripRes,
      fullAttRes,
      deptCompRes,
    ] = await Promise.all([
      getDeptLeaveStats(showHxLeaveOnly.value ? { ...params, hx_only: true } : params),
      getDeptOvertimeStats(showNetOvertime.value ? { ...params, net: true } : params),
      getDeptBusinessTripStats(params),
      filterMonth.value ? getLeaderFullAttendance({ year, month, lsys: lsysToUse || undefined }) : getLeaderFullAttendanceYear({ year, lsys: lsysToUse || undefined }),
      getLeaderDeptComparison(month ? { year, month } : { year }),
    ])
    if (leaveRes.success) leaveStats.value = leaveRes
    if (overtimeRes.success) overtimeStats.value = overtimeRes
    if (tripRes.success) tripStats.value = tripRes
    if (fullAttRes?.success) fullAttendance.value = fullAttRes
    if (deptCompRes?.success) deptComparison.value = deptCompRes
    await fetchFullAttendanceChart()

    if (!month) {
      const today = new Date()
      const maxM = year < today.getFullYear() ? 12 : today.getMonth() + 1
      const leaveP = [], otP = [], tripP = []
      for (let m = 1; m <= maxM; m++) {
        const mp = { year, month: m }
        if (lsysToUse) mp.lsys = lsysToUse
        leaveP.push(getDeptLeaveStats(showHxLeaveOnly.value ? { ...mp, hx_only: true } : mp).then(r => ({ month: m, value: r?.totalDays ?? 0 })).catch(() => ({ month: m, value: 0 })))
        otP.push(getDeptOvertimeStats(showNetOvertime.value ? { ...mp, net: true } : mp).then(r => ({ month: m, value: r?.totalHours ?? 0 })).catch(() => ({ month: m, value: 0 })))
        tripP.push(getDeptBusinessTripStats(mp).then(r => ({ month: m, value: r?.totalDays ?? 0 })).catch(() => ({ month: m, value: 0 })))
      }
      const [lv, ot, tr] = await Promise.all([Promise.all(leaveP), Promise.all(otP), Promise.all(tripP)])
      monthlyLeave.value = lv
      monthlyOvertime.value = ot
      monthlyTrip.value = tr
    } else {
      monthlyLeave.value = []
      monthlyOvertime.value = []
      monthlyTrip.value = []
    }

    try {
      wiRangeError.value = ''
      await loadLeaderWorkIntensity(lsysToUse)
    } catch (e) {
      console.error('工作强度加载失败:', e)
    }
  } catch (error) {
    console.error('管理驾驶舱数据加载失败:', error)
  } finally {
    loading.value = false
  }
}

async function toggleHxLeaveOnly() {
  showHxLeaveOnly.value = !showHxLeaveOnly.value
  const lsysToUse = permLevel.value === 3 ? selectedLsys.value : lsys.value
  if (permLevel.value !== 3 && !lsysToUse) return
  const params = { year: filterYear.value }
  if (lsysToUse) params.lsys = lsysToUse
  if (filterMonth.value) params.month = parseInt(filterMonth.value)
  if (showHxLeaveOnly.value) params.hx_only = true
  try {
    const res = await getDeptLeaveStats(params)
    if (res.success) leaveStats.value = res
  } catch (e) {
    console.error('切换换休请假统计失败:', e)
  }
}

async function toggleNetOvertime() {
  showNetOvertime.value = !showNetOvertime.value
  const lsysToUse = permLevel.value === 3 ? selectedLsys.value : lsys.value
  const params = { year: filterYear.value }
  if (lsysToUse) params.lsys = lsysToUse
  if (filterMonth.value) params.month = parseInt(filterMonth.value)
  if (showNetOvertime.value) params.net = true
  try {
    const res = await getDeptOvertimeStats(params)
    if (res.success) overtimeStats.value = res
  } catch (e) {
    console.error('切换净加班失败:', e)
  }
}

onMounted(async () => {
  try {
    const cfg = await getUploadConfig()
    leaderOtAdmin1.value = cfg?.admin1 || ''
    leaderOtAdmin2.value = cfg?.admin2 || ''
  } catch {
    leaderOtAdmin1.value = ''
    leaderOtAdmin2.value = ''
  }
  await loadPermission()
  await nextTick()
  if (canViewDept.value && (permLevel.value === 3 ? true : !!lsys.value)) {
    fetchData()
  }
})
</script>

<style scoped>
.leader-dashboard-page {
  min-height: 100vh;
  background: var(--color-bg-layout);
}

.leader-dashboard-page .page-header {
  padding: var(--spacing-md) var(--spacing-xl);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--spacing-lg);
}

.header-info { flex: 1; min-width: 200px; }

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.btn-discipline,
.btn-leader-ot,
.btn-public-dashboard {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
  border: none;
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  text-decoration: none;
  cursor: pointer;
  transition: filter 0.15s, box-shadow 0.15s;
  white-space: nowrap;
}
.btn-leader-ot {
  background: linear-gradient(135deg, #2563eb 0%, #0f766e 100%);
}
.btn-public-dashboard {
  background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%);
}
.btn-leader-ot:hover { filter: brightness(1.08); box-shadow: 0 2px 8px rgba(37, 99, 235, 0.28); }
.btn-discipline:hover { filter: brightness(1.08); box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3); }
.btn-public-dashboard:hover { filter: brightness(1.08); box-shadow: 0 2px 8px rgba(124, 58, 237, 0.3); }
.btn-discipline .btn-icon,
.btn-leader-ot .btn-icon,
.btn-public-dashboard .btn-icon { width: 18px; height: 18px; }

.leader-dashboard-page .container {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0 0 var(--spacing-xxl);
}

.card {
  background: var(--color-bg-container);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
}

/* 无权限 */
.no-permission {
  padding: var(--spacing-xxxl);
  text-align: center;
}

.no-permission-content { max-width: 420px; margin: 0 auto; }

.no-permission-icon {
  width: 56px;
  height: 56px;
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-lg);
}

.no-permission-content h3 {
  font-size: var(--font-size-xl);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-md);
}

.no-permission-content p {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-xl);
}

/* 筛选：滚动时固定在顶端 */
.filter-section {
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
  position: sticky;
  top: 0;
  z-index: 10;
}

.filter-form {
  display: flex;
  gap: var(--spacing-xl);
  align-items: flex-end;
  flex-wrap: wrap;
}

.form-item { display: flex; flex-direction: column; gap: var(--spacing-sm); }

.form-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.form-input,
.form-select {
  height: 40px;
  padding: 0 var(--spacing-md);
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  background: var(--color-bg-container);
  min-width: 160px;
}

.form-input[readonly] { background: var(--color-bg-spotlight); cursor: default; }

.form-actions { margin-left: auto; }

.btn {
  height: 40px;
  padding: 0 var(--spacing-xl);
  border-radius: var(--radius-base);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  border: none;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.btn-primary { background: var(--color-primary); color: white; }

.btn-primary:hover:not(:disabled) { filter: brightness(1.05); }

.btn-primary:disabled,
.btn:disabled { opacity: 0.7; cursor: not-allowed; }

.btn-outline {
  background: var(--color-bg-container);
  color: var(--color-primary);
  border: 1px solid var(--color-primary);
}

.btn-outline:hover:not(:disabled) { background: var(--color-primary-lightest); }

.loading-icon { width: 18px; height: 18px; }

/* 考勤总览 */
.overview-section { padding: var(--spacing-xl); margin-bottom: var(--spacing-xl); }
.overview-section .section-title { margin-bottom: var(--spacing-lg); }

.dashboard-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-lg);
}

.dashboard-card {
  overflow: visible;
  border-radius: var(--radius-base);
  border: 1px solid var(--color-border-lighter);
}

.dashboard-card-header {
  padding: var(--spacing-lg) var(--spacing-xl);
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.dashboard-card-icon { width: 24px; height: 24px; flex-shrink: 0; }

.dashboard-card h3 {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.leave-card .dashboard-card-header { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; }
.leave-card .dashboard-card-header .dashboard-card-icon { color: white; }
.leave-card .dashboard-card-header h3 { color: white; }

.overtime-card .dashboard-card-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
.overtime-card .dashboard-card-header .dashboard-card-icon { color: white; }
.overtime-card .dashboard-card-header h3 { color: white; }

.ot-toggle-btn {
  margin-left: auto;
  padding: 2px 10px;
  font-size: 12px;
  line-height: 1.6;
  border: 1px solid rgba(255,255,255,.6);
  border-radius: 12px;
  background: transparent;
  color: rgba(255,255,255,.85);
  cursor: pointer;
  transition: all .2s;
  white-space: nowrap;
}
.ot-toggle-btn:hover { background: rgba(255,255,255,.15); }
.ot-toggle-btn.active { background: rgba(255,255,255,.25); border-color: #fff; color: #fff; }

.ot-net-hint {
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin-top: 4px;
}

.trip-card .dashboard-card-header { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; }
.trip-card .dashboard-card-header .dashboard-card-icon { color: white; }
.trip-card .dashboard-card-header h3 { color: white; }

.dashboard-card-body { padding: var(--spacing-xl); }
.dashboard-card-header {
  border-top-left-radius: var(--radius-base);
  border-top-right-radius: var(--radius-base);
}
.dashboard-card-body {
  border-bottom-left-radius: var(--radius-base);
  border-bottom-right-radius: var(--radius-base);
}

.dashboard-total {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-sm);
}

.total-value { font-size: var(--font-size-huge); font-weight: var(--font-weight-bold); color: var(--color-text-primary); }

.total-unit { font-size: var(--font-size-md); color: var(--color-text-secondary); }
.auto-ot-badge {
  margin-left: 10px;
  padding: 2px 8px;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  color: #1d4ed8;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  vertical-align: middle;
  white-space: nowrap;
}
.auto-ot-badge--zero {
  color: var(--color-text-tertiary);
  background: var(--color-bg-spotlight);
  border-color: var(--color-border-lighter);
}

.dashboard-meta { font-size: var(--font-size-sm); color: var(--color-text-secondary); margin-bottom: var(--spacing-lg); }
.meta-sub { font-size: var(--font-size-xs); color: var(--color-text-tertiary); }

.dashboard-list { margin-top: var(--spacing-md); padding-top: var(--spacing-md); border-top: 1px solid var(--color-border-lighter); }

.list-title { font-size: var(--font-size-sm); font-weight: var(--font-weight-medium); color: var(--color-text-secondary); margin-bottom: var(--spacing-sm); }

.person-list { list-style: none; padding: 0; margin: 0; max-height: 200px; overflow-y: auto; }

.person-item {
  display: flex;
  justify-content: space-between;
  padding: var(--spacing-xs) 0;
  font-size: var(--font-size-sm);
  border-bottom: 1px solid var(--color-border-lighter);
}

.person-item:last-child { border-bottom: none; }

.card-detail-link {
  display: block;
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-border-lighter);
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  text-decoration: none;
  text-align: center;
}
.card-detail-link:hover { text-decoration: underline; }

.person-name { color: var(--color-text-primary); }

.person-rank { display: inline-block; min-width: 1.6em; text-align: right; margin-right: 0.4em; color: var(--color-text-tertiary); font-variant-numeric: tabular-nums; }
.person-value { color: var(--color-primary); font-weight: var(--font-weight-medium); }
.person-auto-ot {
  margin-left: 6px;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-normal);
  color: #1d4ed8;
}
.person-auto-ot--zero {
  color: var(--color-text-tertiary);
}

.clickable { cursor: pointer; transition: background 0.15s, box-shadow 0.15s; border-radius: var(--radius-sm, 4px); }
.clickable:hover { background: var(--color-bg-hover, rgba(0,0,0,.04)); }
.dashboard-total.clickable:hover { box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.person-item.clickable { padding-left: var(--spacing-xs); padding-right: var(--spacing-xs); margin: 0 calc(var(--spacing-xs, 4px) * -1); }

.init-hint {
  padding: var(--spacing-xl);
  text-align: center;
  color: var(--color-text-secondary);
}

/* 区块标题 */
.section { padding: var(--spacing-xl); margin-bottom: var(--spacing-xl); }
.section-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-md);
  display: flex;
  align-items: baseline;
  gap: var(--spacing-md);
}
.section-sub { font-size: var(--font-size-sm); color: var(--color-text-secondary); font-weight: normal; }
.section-icon { width: 24px; height: 24px; color: var(--color-primary); flex-shrink: 0; }
.section-desc, .section-desc + .chart-legend { margin-bottom: var(--spacing-md); font-size: var(--font-size-sm); color: var(--color-text-secondary); }

/* 满勤统计 */
.fa-divider { border-top: 1px solid var(--color-border-lighter); margin: var(--spacing-xl) 0; }
.fa-chart-title { font-size: var(--font-size-md); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin-bottom: var(--spacing-md); }

.full-attendance-content { margin-top: var(--spacing-md); }
.full-attendance-summary {
  display: flex;
  gap: var(--spacing-xl);
  flex-wrap: wrap;
  margin-bottom: var(--spacing-lg);
}
.fa-item { display: flex; flex-direction: column; gap: var(--spacing-xs); }
.fa-label { font-size: var(--font-size-sm); color: var(--color-text-secondary); }
.fa-value { font-size: var(--font-size-xl); font-weight: var(--font-weight-bold); color: var(--color-primary); }
.fa-meta { font-size: var(--font-size-sm); color: var(--color-text-tertiary); }
.full-attendance-section {
  overflow: visible;
}
.full-attendance-depts {
  overflow: visible;
}
.fa-dept-title { font-size: var(--font-size-sm); font-weight: var(--font-weight-medium); color: var(--color-text-secondary); margin-bottom: var(--spacing-sm); }
.fa-dept-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: var(--spacing-md);
  overflow: visible;
}
.fa-dept-card-wrap {
  position: relative;
  z-index: 1;
  outline: none;
}
.fa-dept-card-wrap:hover,
.fa-dept-card-wrap:focus-within {
  z-index: 30;
}
.fa-dept-card {
  padding: var(--spacing-md);
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--radius-base);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  cursor: default;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.fa-dept-card-wrap:hover .fa-dept-card,
.fa-dept-card-wrap:focus-within .fa-dept-card {
  border-color: var(--color-primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.fa-dept-name { font-weight: var(--font-weight-medium); color: var(--color-text-primary); }
.fa-dept-rate { font-size: var(--font-size-lg); color: var(--color-primary); }
.fa-dept-meta { font-size: var(--font-size-xs); color: var(--color-text-tertiary); }

.fa-dept-tooltip {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  bottom: calc(100% + 10px);
  min-width: min(280px, 90vw);
  max-width: min(320px, 92vw);
  max-height: 260px;
  overflow-y: auto;
  padding: var(--spacing-md);
  background: var(--color-bg-container);
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  box-shadow: var(--shadow-card);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: opacity 0.15s ease, visibility 0.15s ease;
}
.fa-dept-card-wrap:hover .fa-dept-tooltip,
.fa-dept-card-wrap:focus-within .fa-dept-tooltip {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
}
.fa-tooltip-title {
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--spacing-sm);
  padding-bottom: var(--spacing-xs);
  border-bottom: 1px solid var(--color-border-lighter);
}
.fa-tooltip-names {
  margin: 0;
  padding-left: 1.1em;
  list-style: disc;
}
.fa-tooltip-names li {
  margin-bottom: 2px;
}
.fa-tooltip-empty {
  margin: 0;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-xs);
}

/* 科室对比柱状图 */
.chart-filter-row { display: flex; align-items: center; gap: var(--spacing-md); margin-bottom: var(--spacing-lg); flex-wrap: wrap; }
.chart-filter-label { font-size: var(--font-size-sm); color: var(--color-text-secondary); }
.chart-type-tabs { display: flex; gap: var(--spacing-sm); }
.tab-btn-sm { padding: var(--spacing-xs) var(--spacing-md); font-size: var(--font-size-sm); }
.bar-chart-wrap { margin-bottom: var(--spacing-xl); }
.bar-chart-wrap:last-child { margin-bottom: 0; }
.chart-subtitle { font-size: var(--font-size-md); color: var(--color-text-secondary); margin: var(--spacing-lg) 0 var(--spacing-sm); }
.chart-subtitle-row { display: flex; align-items: center; gap: 12px; }
.chart-subtitle-row .chart-subtitle { margin-bottom: 0; }
.pc-dim-btn { font-size: 12px; padding: 2px 10px; border-radius: 12px; border: 1px solid var(--color-border); background: transparent; color: var(--color-text-secondary); cursor: pointer; transition: all .2s; white-space: nowrap; }
.pc-dim-btn:hover { background: var(--color-bg-hover); }
.pc-dim-btn.active { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }
.bar-chart-total {
  display: flex;
  gap: var(--spacing-sm);
  height: 200px;
  align-items: stretch;
  padding-top: 28px;
  padding-bottom: var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
  overflow-x: auto;
  overflow-y: visible;
  box-sizing: content-box;
}
.bar-chart-single .bar-group .bar-col { min-width: 28px; }
.bar-group { flex: 1; min-width: 60px; display: flex; flex-direction: column; align-items: center; height: 100%; min-height: 0; }
.bar-group .bars { flex: 1; display: flex; gap: 4px; align-items: flex-end; width: 100%; justify-content: center; min-height: 0; }
.bar-group .bar-col { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; flex: 1; min-width: 20px; min-height: 0; }
.bar-group .bar { width: 20px; min-height: 4px; border-radius: 4px 4px 0 0; transition: height 0.2s; }
.bar-group .bar-has-value { position: relative; }
/* 柱顶数值相对柱子顶部定位，始终在柱子上方，不与高柱重叠 */
.bar-group .bar-has-value .bar-value { position: absolute; top: 0; left: 50%; transform: translate(-50%, calc(-100% - 4px)); font-size: var(--font-size-xs); color: var(--color-text-secondary); white-space: nowrap; pointer-events: none; }
.bar-chart-single .bar-group .bar { width: 28px; }
.bar-group .bar-ot { background: linear-gradient(180deg, #667eea 0%, #764ba2 100%); }
.bar-group .bar-not { background: linear-gradient(180deg, #36d1dc 0%, #5b86e5 100%); }
.bar-group .bar-negative { opacity: .55; }
.bar-group .bar-lv { background: linear-gradient(180deg, #f093fb 0%, #f5576c 100%); }
.bar-group .bar-tr { background: linear-gradient(180deg, #4facfe 0%, #00f2fe 100%); }
.bar-group .bar-label { font-size: var(--font-size-xs); color: var(--color-text-tertiary); margin-top: var(--spacing-sm); text-align: center; }

.tab-btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  background: var(--color-bg-container);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all var(--transition-base);
}
.tab-btn:hover { border-color: var(--color-primary); color: var(--color-primary); }
.tab-btn.active { background: var(--color-primary); color: white; border-color: var(--color-primary); }
.empty-rankings { text-align: center; padding: var(--spacing-xxl); color: var(--color-text-tertiary); }

/* 满勤人数柱状图 */
.chart-filter-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
  flex-wrap: wrap;
}
.chart-filter-label { font-size: var(--font-size-sm); color: var(--color-text-secondary); font-weight: var(--font-weight-medium); }
.chart-filter-select { width: 160px; }
.chart-filter-hint { font-size: var(--font-size-sm); color: var(--color-text-tertiary); }
.full-count-chart .bar-chart-months {
  display: flex;
  gap: var(--spacing-sm);
  height: 240px;
  align-items: flex-end;
  padding-bottom: var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-lighter);
}
.full-count-chart .bar-month-group {
  flex: 1;
  min-width: 36px;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}
/* 固定高度柱区：所有柱子在此高度内绘制，底部贴 X 轴，顶部随数值起伏 */
.full-count-chart .bar-month-area {
  width: 100%;
  max-width: 32px;
  height: 180px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
  flex-shrink: 0;
}
.full-count-chart .bar-month-bar {
  width: 100%;
  max-width: 32px;
  min-height: 8px;
  border-radius: 6px 6px 0 0;
  background: linear-gradient(180deg, #0d9488 0%, #0f766e 100%);
  transition: height 0.2s;
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 4px;
  flex-shrink: 0;
}
.full-count-chart .bar-month-value {
  font-size: var(--font-size-xs);
  color: white;
  font-weight: var(--font-weight-medium);
  text-shadow: 0 0 1px rgba(0,0,0,0.5);
}
.full-count-chart .bar-month-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-top: var(--spacing-sm);
  flex-shrink: 0;
}
/* ====== 工作强度统计 ====== */
.wi-section { overflow: visible; }

.wi-formula-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin: 0 0 var(--spacing-md);
}
.wi-formula-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
.wi-formula-btn {
  padding: 4px 14px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  background: var(--color-bg-container);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  color: var(--color-text-secondary);
}
.wi-formula-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.wi-formula-btn.active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.wi-range-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-spotlight);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-lighter);
}
.wi-range-check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  cursor: pointer;
  user-select: none;
}
.wi-range-inputs {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}
.wi-date-input {
  width: auto;
  min-width: 140px;
  font-size: var(--font-size-sm);
}
.wi-range-sep {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
.wi-range-apply {
  padding: 6px 16px;
  font-size: var(--font-size-sm);
}
.wi-export-btn {
  height: 34px;
  padding: 0 16px;
  font-size: var(--font-size-sm);
  margin-left: auto;
}
.wi-range-error {
  flex-basis: 100%;
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-error, #dc2626);
}

.wi-summary {
  display: flex;
  gap: var(--spacing-xl);
  flex-wrap: wrap;
  margin-bottom: var(--spacing-lg);
}
.wi-summary-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.wi-label { font-size: var(--font-size-sm); color: var(--color-text-secondary); }
.wi-value { font-size: var(--font-size-xl); font-weight: var(--font-weight-bold); color: var(--color-primary); }
.wi-summary-highlight .wi-value { color: #c2410c; }

.wi-tabs {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
}
.wi-tab {
  padding: 6px 18px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-base);
  background: var(--color-bg-container);
  font-size: var(--font-size-sm);
  cursor: pointer;
}
.wi-tab.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.wi-person-filters {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin: calc(var(--spacing-lg) * -1 + 2px) 0 var(--spacing-md);
}
.wi-person-filter-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
.wi-job-filter-select {
  min-width: 132px;
  height: 32px;
  padding: 0 10px;
}

.wi-dept-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--spacing-md);
}
.wi-dept-card {
  padding: var(--spacing-md) var(--spacing-lg);
  border: 1px solid var(--color-border-lighter);
  border-radius: var(--radius-md);
  background: var(--color-bg-spotlight);
}
.wi-dept-name { font-weight: var(--font-weight-semibold); margin-bottom: 4px; }
.wi-dept-intensity { font-size: var(--font-size-xl); font-weight: var(--font-weight-bold); color: #c2410c; }
.wi-dept-meta { font-size: var(--font-size-xs); color: var(--color-text-tertiary); margin-top: 4px; }

.wi-person-table-wrap { overflow-x: auto; }
.wi-person-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}
.wi-person-table th,
.wi-person-table td {
  padding: 8px 14px;
  text-align: left;
  border-bottom: 1px solid var(--color-border-lighter);
}
.wi-person-table th {
  background: var(--color-bg-spotlight);
  font-weight: 600;
  color: var(--color-text-secondary);
}
.wi-person-table .th-rank,
.wi-person-table .td-rank {
  width: 56px;
  text-align: center;
}
.wi-th-sort {
  cursor: pointer;
  user-select: none;
  transition: color .15s, background .15s;
}
.wi-th-sort:hover {
  color: var(--color-primary);
  background: #eef4ff;
}
.wi-sort-ind {
  margin-left: 4px;
  font-size: 11px;
  color: #94a3b8;
}
.wi-person-table .td-num { text-align: center; }
.wi-person-table .td-intensity { color: #c2410c; font-weight: 600; }

.wi-sparkline-wrap {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 300px;
  flex: 1;
  max-width: 460px;
}
.wi-sparkline {
  width: 100%;
  height: 68px;
}
.wi-sparkline .sparkline-val {
  font-size: 8px;
  fill: #c2410c;
  font-weight: 600;
}
.wi-sparkline-labels {
  display: flex;
  justify-content: space-between;
}
.wi-sparkline-m {
  font-size: 10px;
  color: var(--color-text-tertiary);
}
.wi-sparkline circle { cursor: default; }

/* ---- 月度趋势折线图悬浮弹窗 ---- */
.trend-anchor { position: relative; }
.trend-popover {
  display: none;
  position: absolute;
  left: 0;
  top: calc(100% + 8px);
  z-index: 50;
  width: 380px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 12px 36px rgba(15, 23, 42, 0.18);
  border: 1px solid #e2e8f0;
  padding: 12px 14px 8px;
  pointer-events: none;
}
.trend-anchor:hover .trend-popover { display: block; }

.trend-pop-title {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 6px;
}
.trend-svg {
  width: 100%;
  height: auto;
}
.trend-grid { stroke: #e2e8f0; stroke-width: 0.5; stroke-dasharray: 3 2; }
.trend-y-label { font-size: 8px; fill: #94a3b8; text-anchor: end; }
.trend-x-label { font-size: 8px; fill: #94a3b8; }
.trend-dot-val { font-size: 8px; fill: #334155; font-weight: 600; }

.trend-line { fill: none; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
.trend-area { opacity: 0.12; }
.trend-dot { stroke: #fff; stroke-width: 1.5; }

.trend-line-leave { stroke: #ec4899; }
.trend-area-leave { fill: #ec4899; }
.trend-dot-leave { fill: #ec4899; }

.trend-line-overtime { stroke: #7c3aed; }
.trend-area-overtime { fill: #7c3aed; }
.trend-dot-overtime { fill: #7c3aed; }

.trend-line-trip { stroke: #0ea5e9; }
.trend-area-trip { fill: #0ea5e9; }
.trend-dot-trip { fill: #0ea5e9; }

@media (max-width: 960px) {
  .dashboard-cards { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .filter-form { flex-direction: column; align-items: stretch; }
  .form-actions { margin-left: 0; }
  .bar-chart-total { min-width: 400px; }
  .fa-dept-grid { grid-template-columns: repeat(2, 1fr); }
  .wi-dept-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
