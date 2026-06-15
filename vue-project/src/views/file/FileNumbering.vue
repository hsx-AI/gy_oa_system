<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-content">
        <div class="header-info">
          <h1 class="header-title">文件编号管理</h1>
          <p class="header-subtitle">技术文件、技术管理文件、管理文件、工艺过程策划表、生产数字化的编号规则与记录查询</p>
        </div>
        <div class="header-actions">
          <button class="btn" @click="goTechCategory">技术分类录入</button>
          <button class="btn" @click="goWorkNo">工作号录入</button>
          <button class="btn btn-primary" @click="showModal = true">获取编号</button>
        </div>
      </div>
    </div>
    
    <div class="tabs">
      <div 
        class="tab-item" 
        :class="{ active: currentTab === 'tech' }"
        @click="currentTab = 'tech'"
      >
        技术文件编号
      </div>
      <div 
        class="tab-item" 
        :class="{ active: currentTab === 'jsgl' }"
        @click="currentTab = 'jsgl'"
      >
        技术管理文件编号
      </div>
      <div 
        class="tab-item" 
        :class="{ active: currentTab === 'manage' }"
        @click="currentTab = 'manage'"
      >
        管理文件编号
      </div>
      <div 
        class="tab-item" 
        :class="{ active: currentTab === 'gygch' }"
        @click="currentTab = 'gygch'"
      >
        工艺过程策划表
      </div>
      <div 
        class="tab-item" 
        :class="{ active: currentTab === 'scszh' }"
        @click="currentTab = 'scszh'"
      >
        生产数字化编号
      </div>
    </div>

    <div class="content mt-xl">
      <!-- 列表 -->
      <div class="card">
        <div class="card-header record-card__header">
          <div>
            <h3>{{ tabTitleMap[currentTab] || '文件列表' }}</h3>
          </div>
          <div class="record-card__filters">
            <label class="filter-label">搜索：</label>
            <input
              v-model="activeSearchKeyword"
              type="search"
              class="filter-input filter-input--search"
              placeholder="关键词"
              @keyup.enter="doCurrentSearch"
            >
            <button type="button" class="btn btn-primary btn-sm" @click="doCurrentSearch">查询</button>
            <button type="button" class="btn btn-sm" @click="doCurrentReset">重置</button>
            <button
              v-if="canExportBianhao"
              type="button"
              class="btn btn-primary btn-sm"
              :disabled="exportLoading"
              @click="exportCurrentTable"
            >
              {{ exportLoading ? '导出中…' : '导出 Excel' }}
            </button>
          </div>
        </div>
        <div class="card-body">
          <template v-if="currentTab === 'tech'">
            <div v-if="techListLoading" class="empty-text">加载中...</div>
            <div v-else-if="techTotal === 0" class="empty-text">{{ canSeeAllFiles ? '暂无文件记录' : '您只能看到本专业的文件哦' }}</div>
            <div v-else-if="filteredTechList.length === 0" class="empty-text">当前页无匹配记录，请调整搜索关键词或翻页</div>
            <div v-else class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th class="sortable-th" @click="toggleSort('tech','bz')">编号单位 <span class="sort-icon">{{ sortIcon('tech','bz') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('tech','xm')">编制人 <span class="sort-icon">{{ sortIcon('tech','xm') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('tech','gzh')">工作号 <span class="sort-icon">{{ sortIcon('tech','gzh') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('tech','cpname')">项目名称 <span class="sort-icon">{{ sortIcon('tech','cpname') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('tech','fenlei')">编号类别 <span class="sort-icon">{{ sortIcon('tech','fenlei') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('tech','neirong')">编号内容 <span class="sort-icon">{{ sortIcon('tech','neirong') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('tech','bhtime')">编号时间 <span class="sort-icon">{{ sortIcon('tech','bhtime') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('tech','bianhao_code')">编号代码 <span class="sort-icon">{{ sortIcon('tech','bianhao_code') }}</span></th>
                    <th>PDF 文件</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in filteredTechList" :key="row.id">
                    <td>{{ row.bz }}</td>
                    <td>{{ row.xm }}</td>
                    <td>{{ row.gzh }}</td>
                    <td>{{ row.cpname }}</td>
                    <td>{{ row.fenlei }}</td>
                    <td>{{ row.neirong }}</td>
                    <td>{{ row.bhtime || '—' }}</td>
                    <td>
                      <span class="bianhao-code">{{ row.bianhao_code }}</span>
                      <button type="button" class="btn-copy-small" @click="copyText(row.bianhao_code)" title="复制">复制</button>
                    </td>
                    <td class="file-actions">
                      <button v-if="!row.has_pdf" type="button" class="btn-copy-small btn-upload" title="请上传终版PDF文件仅支持PDF" @click="triggerUpload('tech', row.bianhao_code)">请上传</button>
                      <template v-else>
                        <button type="button" class="btn-copy-small btn-delete" title="删除后可重新上传" @click="deletePdf('tech', row.bianhao_code)">删除</button>
                        <button type="button" class="btn-copy-small btn-preview" @click="openFile('tech', row.bianhao_code, 0)">预览</button>
                        <button type="button" class="btn-copy-small btn-download" @click="openFile('tech', row.bianhao_code, 1)">下载</button>
                      </template>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="techTotal > 0" class="table-footer table-footer-pager">
              <span>共 {{ techTotal }} 条，第 {{ techPage }} / {{ techTotalPages }} 页，每页 {{ LIST_PAGE_SIZE }} 条</span>
              <div class="pager-btns">
                <button type="button" class="btn pager-btn" :disabled="techPage <= 1" @click="goTechPage(-1)">上一页</button>
                <button type="button" class="btn pager-btn" :disabled="techPage >= techTotalPages" @click="goTechPage(1)">下一页</button>
              </div>
            </div>
          </template>
          <template v-else-if="currentTab === 'jsgl'">
            <div v-if="jsglListLoading" class="empty-text">加载中...</div>
            <div v-else-if="jsglTotal === 0" class="empty-text">{{ canSeeAllFiles ? '暂无文件记录' : '您只能看到本专业的文件哦' }}</div>
            <div v-else-if="filteredJsglList.length === 0" class="empty-text">当前页无匹配记录，请调整搜索关键词或翻页</div>
            <div v-else class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th class="sortable-th" @click="toggleSort('jsgl','bz')">编号单位 <span class="sort-icon">{{ sortIcon('jsgl','bz') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('jsgl','xm')">编制人 <span class="sort-icon">{{ sortIcon('jsgl','xm') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('jsgl','gzh')">工作号 <span class="sort-icon">{{ sortIcon('jsgl','gzh') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('jsgl','cpname')">项目名称 <span class="sort-icon">{{ sortIcon('jsgl','cpname') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('jsgl','fenleihao')">编号类别 <span class="sort-icon">{{ sortIcon('jsgl','fenleihao') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('jsgl','neirong')">编号内容 <span class="sort-icon">{{ sortIcon('jsgl','neirong') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('jsgl','bhtime')">编号时间 <span class="sort-icon">{{ sortIcon('jsgl','bhtime') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('jsgl','bianhao_code')">编号代码 <span class="sort-icon">{{ sortIcon('jsgl','bianhao_code') }}</span></th>
                    <th>PDF 文件</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in filteredJsglList" :key="row.id">
                    <td>{{ row.bz }}</td>
                    <td>{{ row.xm }}</td>
                    <td>{{ row.gzh }}</td>
                    <td>{{ row.cpname }}</td>
                    <td>{{ row.fenleihao || row.fenlei }}</td>
                    <td>{{ row.neirong }}</td>
                    <td>{{ row.bhtime || '—' }}</td>
                    <td>
                      <span class="bianhao-code">{{ row.bianhao_code }}</span>
                      <button type="button" class="btn-copy-small" @click="copyText(row.bianhao_code)" title="复制">复制</button>
                    </td>
                    <td class="file-actions">
                      <button v-if="!row.has_pdf" type="button" class="btn-copy-small btn-upload" title="请上传终版PDF文件仅支持PDF" @click="triggerUpload('jsgl', row.bianhao_code)">请上传</button>
                      <template v-else>
                        <button type="button" class="btn-copy-small btn-delete" title="删除后可重新上传" @click="deletePdf('jsgl', row.bianhao_code)">删除</button>
                        <button type="button" class="btn-copy-small btn-preview" @click="openFile('jsgl', row.bianhao_code, 0)">预览</button>
                        <button type="button" class="btn-copy-small btn-download" @click="openFile('jsgl', row.bianhao_code, 1)">下载</button>
                      </template>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="jsglTotal > 0" class="table-footer table-footer-pager">
              <span>共 {{ jsglTotal }} 条，第 {{ jsglPage }} / {{ jsglTotalPages }} 页，每页 {{ LIST_PAGE_SIZE }} 条</span>
              <div class="pager-btns">
                <button type="button" class="btn pager-btn" :disabled="jsglPage <= 1" @click="goJsglPage(-1)">上一页</button>
                <button type="button" class="btn pager-btn" :disabled="jsglPage >= jsglTotalPages" @click="goJsglPage(1)">下一页</button>
              </div>
            </div>
          </template>
          <template v-else-if="currentTab === 'manage'">
            <div v-if="manageListLoading" class="empty-text">加载中...</div>
            <div v-else-if="manageTotal === 0" class="empty-text">{{ canSeeAllFiles ? '暂无文件记录' : '您只能看到本专业的文件哦' }}</div>
            <div v-else-if="filteredManageList.length === 0" class="empty-text">当前页无匹配记录，请调整搜索关键词或翻页</div>
            <div v-else class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th class="sortable-th" @click="toggleSort('manage','bz')">编号单位 <span class="sort-icon">{{ sortIcon('manage','bz') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('manage','xm')">编制人 <span class="sort-icon">{{ sortIcon('manage','xm') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('manage','fenlei')">编号类别 <span class="sort-icon">{{ sortIcon('manage','fenlei') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('manage','neirong')">编号内容 <span class="sort-icon">{{ sortIcon('manage','neirong') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('manage','bhtime')">编号时间 <span class="sort-icon">{{ sortIcon('manage','bhtime') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('manage','bianhao_code')">编号代码 <span class="sort-icon">{{ sortIcon('manage','bianhao_code') }}</span></th>
                    <th>PDF 文件</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in filteredManageList" :key="row.id">
                    <td>{{ row.bz }}</td>
                    <td>{{ row.xm }}</td>
                    <td>{{ row.fenlei }}</td>
                    <td>{{ row.neirong }}</td>
                    <td>{{ row.bhtime || '—' }}</td>
                    <td>
                      <span class="bianhao-code">{{ row.bianhao_code }}</span>
                      <button type="button" class="btn-copy-small" @click="copyText(row.bianhao_code)" title="复制">复制</button>
                    </td>
                    <td class="file-actions">
                      <button v-if="!row.has_pdf" type="button" class="btn-copy-small btn-upload" title="请上传终版PDF文件仅支持PDF" @click="triggerUpload('manage', row.bianhao_code)">请上传</button>
                      <template v-else>
                        <button type="button" class="btn-copy-small btn-delete" title="删除后可重新上传" @click="deletePdf('manage', row.bianhao_code)">删除</button>
                        <button type="button" class="btn-copy-small btn-preview" @click="openFile('manage', row.bianhao_code, 0)">预览</button>
                        <button type="button" class="btn-copy-small btn-download" @click="openFile('manage', row.bianhao_code, 1)">下载</button>
                      </template>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="manageTotal > 0" class="table-footer table-footer-pager">
              <span>共 {{ manageTotal }} 条，第 {{ managePage }} / {{ manageTotalPages }} 页，每页 {{ LIST_PAGE_SIZE }} 条</span>
              <div class="pager-btns">
                <button type="button" class="btn pager-btn" :disabled="managePage <= 1" @click="goManagePage(-1)">上一页</button>
                <button type="button" class="btn pager-btn" :disabled="managePage >= manageTotalPages" @click="goManagePage(1)">下一页</button>
              </div>
            </div>
          </template>
          <template v-else-if="currentTab === 'gygch'">
            <div v-if="gygchListLoading" class="empty-text">加载中...</div>
            <div v-else-if="gygchTotal === 0" class="empty-text">暂无工艺过程策划表编号记录</div>
            <div v-else-if="filteredGygchList.length === 0" class="empty-text">当前页无匹配记录，请调整搜索关键词或翻页</div>
            <div v-else class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th class="sortable-th" @click="toggleSort('gygch','bz')">编号单位 <span class="sort-icon">{{ sortIcon('gygch','bz') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('gygch','xm')">编制人 <span class="sort-icon">{{ sortIcon('gygch','xm') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('gygch','bhyear')">年代 <span class="sort-icon">{{ sortIcon('gygch','bhyear') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('gygch','room_code')">工艺部室 <span class="sort-icon">{{ sortIcon('gygch','room_code') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('gygch','neirong')">编号内容 <span class="sort-icon">{{ sortIcon('gygch','neirong') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('gygch','bhtime')">编号时间 <span class="sort-icon">{{ sortIcon('gygch','bhtime') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('gygch','bianhao_code')">编号代码 <span class="sort-icon">{{ sortIcon('gygch','bianhao_code') }}</span></th>
                    <th>PDF 文件</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in filteredGygchList" :key="row.id">
                    <td>{{ row.bz }}</td>
                    <td>{{ row.xm }}</td>
                    <td>{{ row.bhyear }}</td>
                    <td>{{ row.room_code }}</td>
                    <td>{{ row.neirong || '—' }}</td>
                    <td>{{ row.bhtime || '—' }}</td>
                    <td>
                      <span class="bianhao-code">{{ row.bianhao_code }}</span>
                      <button type="button" class="btn-copy-small" @click="copyText(row.bianhao_code)" title="复制">复制</button>
                    </td>
                    <td class="file-actions">
                      <button v-if="!row.has_pdf" type="button" class="btn-copy-small btn-upload" title="请上传终版PDF文件仅支持PDF" @click="triggerUpload('gygch', row.bianhao_code)">请上传</button>
                      <template v-else>
                        <button type="button" class="btn-copy-small btn-delete" title="删除后可重新上传" @click="deletePdf('gygch', row.bianhao_code)">删除</button>
                        <button type="button" class="btn-copy-small btn-preview" @click="openFile('gygch', row.bianhao_code, 0)">预览</button>
                        <button type="button" class="btn-copy-small btn-download" @click="openFile('gygch', row.bianhao_code, 1)">下载</button>
                      </template>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="gygchTotal > 0" class="table-footer table-footer-pager">
              <span>共 {{ gygchTotal }} 条，第 {{ gygchPage }} / {{ gygchTotalPages }} 页，每页 {{ LIST_PAGE_SIZE }} 条</span>
              <div class="pager-btns">
                <button type="button" class="btn pager-btn" :disabled="gygchPage <= 1" @click="goGygchPage(-1)">上一页</button>
                <button type="button" class="btn pager-btn" :disabled="gygchPage >= gygchTotalPages" @click="goGygchPage(1)">下一页</button>
              </div>
            </div>
          </template>
          <template v-else-if="currentTab === 'scszh'">
            <div v-if="scszhListLoading" class="empty-text">加载中...</div>
            <div v-else-if="scszhTotal === 0" class="empty-text">暂无生产数字化编号记录</div>
            <div v-else-if="filteredScszhList.length === 0" class="empty-text">当前页无匹配记录，请调整搜索关键词或翻页</div>
            <div v-else class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th class="sortable-th" @click="toggleSort('scszh','bz')">编号单位 <span class="sort-icon">{{ sortIcon('scszh','bz') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('scszh','xm')">编制人 <span class="sort-icon">{{ sortIcon('scszh','xm') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('scszh','fenlei')">项目 <span class="sort-icon">{{ sortIcon('scszh','fenlei') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('scszh','neirong')">编号内容 <span class="sort-icon">{{ sortIcon('scszh','neirong') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('scszh','content')">备注 <span class="sort-icon">{{ sortIcon('scszh','content') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('scszh','bhtime')">编号时间 <span class="sort-icon">{{ sortIcon('scszh','bhtime') }}</span></th>
                    <th class="sortable-th" @click="toggleSort('scszh','bianhao_code')">编号代码 <span class="sort-icon">{{ sortIcon('scszh','bianhao_code') }}</span></th>
                    <th>PDF 文件</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in filteredScszhList" :key="row.id">
                    <td>{{ row.bz }}</td>
                    <td>{{ row.xm }}</td>
                    <td>{{ row.fenlei }}</td>
                    <td>{{ row.neirong }}</td>
                    <td>{{ row.content || '—' }}</td>
                    <td>{{ row.bhtime || '—' }}</td>
                    <td>
                      <span class="bianhao-code">{{ row.bianhao_code }}</span>
                      <button type="button" class="btn-copy-small" @click="copyText(row.bianhao_code)" title="复制">复制</button>
                    </td>
                    <td class="file-actions">
                      <button v-if="!row.has_pdf" type="button" class="btn-copy-small btn-upload" title="请上传终版PDF文件仅支持PDF" @click="triggerUpload('scszh', row.bianhao_code)">请上传</button>
                      <template v-else>
                        <button type="button" class="btn-copy-small btn-delete" title="删除后可重新上传" @click="deletePdf('scszh', row.bianhao_code)">删除</button>
                        <button type="button" class="btn-copy-small btn-preview" @click="openFile('scszh', row.bianhao_code, 0)">预览</button>
                        <button type="button" class="btn-copy-small btn-download" @click="openFile('scszh', row.bianhao_code, 1)">下载</button>
                      </template>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="scszhTotal > 0" class="table-footer table-footer-pager">
              <span>共 {{ scszhTotal }} 条，第 {{ scszhPage }} / {{ scszhTotalPages }} 页，每页 {{ LIST_PAGE_SIZE }} 条</span>
              <div class="pager-btns">
                <button type="button" class="btn pager-btn" :disabled="scszhPage <= 1" @click="goScszhPage(-1)">上一页</button>
                <button type="button" class="btn pager-btn" :disabled="scszhPage >= scszhTotalPages" @click="goScszhPage(1)">下一页</button>
              </div>
            </div>
          </template>
          <p v-else class="empty-text">{{ canSeeAllFiles ? '暂无文件记录' : '您只能看到本专业的文件哦' }}</p>
        </div>
      </div>
    </div>

    <input
      ref="pdfInputRef"
      type="file"
      accept=".pdf,application/pdf"
      class="hidden-input"
      @change="onPdfSelected"
    />

    <!-- 获取编号弹窗（技术文件：自动填充添加人/科室，分类与项目下拉） -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <h2>获取{{ currentTab === 'tech' ? '技术' : currentTab === 'jsgl' ? '技术管理' : currentTab === 'manage' ? '管理' : currentTab === 'gygch' ? '工艺过程策划表' : '生产数字化' }}编号</h2>
        <!-- 生成成功：显示编号 + 复制 -->
        <div v-if="generatedBianhao" class="result-block">
          <p class="result-label">编号已生成</p>
          <p class="result-bianhao">{{ generatedBianhao }}</p>
          <div class="result-actions">
            <button type="button" class="btn btn-copy" @click="copyBianhao">复制</button>
            <button type="button" class="btn-primary" @click="closeModal">关闭</button>
          </div>
        </div>
        <form v-else @submit.prevent="submitNumbering">
          <template v-if="currentTab === 'tech'">
            <div class="form-group">
              <label>添加人</label>
              <input v-model="form.xm" type="text" readonly class="readonly">
            </div>
            <div class="form-group">
              <label>所属科室</label>
              <input v-model="form.bz" type="text" readonly class="readonly">
            </div>
            <div class="form-group">
              <label>分类名称</label>
              <select v-model="form.fenlei" @change="onFenleiChange">
                <option value="">请选择分类</option>
                <option v-for="item in bianhaoFlList" :key="item.id" :value="item.flname">{{ item.flname }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>项目名称</label>
              <SearchableSelect
                v-model="form.xmname"
                :options="gzhList"
                :format-label="formatProjectOptionLabel"
                value-key="gzhname"
                placeholder="输入项目名称或工作号搜索"
              />
            </div>
          </template>
          <template v-else-if="currentTab === 'jsgl'">
            <div class="form-group">
              <label>添加人</label>
              <input v-model="form.xm" type="text" readonly class="readonly">
            </div>
            <div class="form-group">
              <label>所属科室</label>
              <input v-model="form.bz" type="text" readonly class="readonly">
            </div>
            <div class="form-group">
              <label>项目名称</label>
              <SearchableSelect
                v-model="form.xmname"
                :options="gzhList"
                :format-label="formatProjectOptionLabel"
                value-key="gzhname"
                placeholder="输入项目名称或工作号搜索"
              />
            </div>
            <div class="form-group">
              <label>分类</label>
              <select v-model="form.fenlei">
                <option value="">请选择分类</option>
                <option v-for="item in jsglFenleiList" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </div>
          </template>
          <template v-else-if="currentTab === 'manage'">
            <div class="form-group">
              <label>添加人</label>
              <input v-model="form.xm" type="text" readonly class="readonly">
            </div>
            <div class="form-group">
              <label>所属科室</label>
              <input v-model="form.bz" type="text" readonly class="readonly">
            </div>
            <div class="form-group">
              <label>分类</label>
              <select v-model="form.fenlei">
                <option value="">请选择分类</option>
                <option v-for="item in glFenleiList" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>编制内容</label>
              <input v-model="form.neirong" type="text" placeholder="请输入编制内容">
            </div>
            <div class="form-group">
              <label>备注</label>
              <input v-model="form.content" type="text" placeholder="选填">
            </div>
          </template>
          <template v-else-if="currentTab === 'gygch'">
            <div class="form-group">
              <label>添加人</label>
              <input v-model="form.xm" type="text" readonly class="readonly">
            </div>
            <div class="form-group">
              <label>所属科室</label>
              <input v-model="form.bz" type="text" readonly class="readonly">
            </div>
            <div class="form-group">
              <label>年代</label>
              <input v-model.number="form.bhyear" type="number" min="2000" max="2100" placeholder="不填默认当年">
            </div>
            <div class="form-group">
              <label>编号内容/说明</label>
              <input v-model="form.neirong" type="text" placeholder="选填">
            </div>
          </template>
          <template v-else-if="currentTab === 'scszh'">
            <div class="form-group">
              <label>添加人</label>
              <input v-model="form.xm" type="text" readonly class="readonly">
            </div>
            <div class="form-group">
              <label>所属科室</label>
              <input v-model="form.bz" type="text" readonly class="readonly">
            </div>
            <div class="form-group">
              <label>项目</label>
              <select v-model="form.fenlei">
                <option value="">请选择项目</option>
                <option v-for="item in scszhFenleiList" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>编制内容</label>
              <input v-model="form.neirong" type="text" placeholder="请输入编制内容">
            </div>
            <div class="form-group">
              <label>备注</label>
              <input v-model="form.content" type="text" placeholder="选填">
            </div>
          </template>
          <div v-if="currentTab !== 'manage' && currentTab !== 'gygch' && currentTab !== 'scszh'" class="form-group">
            <label>{{ currentTab === 'jsgl' ? '编制内容' : '文件名称' }}</label>
            <input v-model="form.neirong" type="text" :placeholder="currentTab === 'jsgl' ? '请输入编制内容' : '请输入文件名称'">
          </div>
          <div class="form-actions">
            <button type="button" @click="closeModal">取消</button>
            <button type="submit" class="btn-primary" :disabled="submitLoading">{{ submitLoading ? '生成中...' : '生成编号' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SearchableSelect from '@/components/SearchableSelect.vue'
import { getGzhList, getBianhaoFlList, addBianhaoTech, getBianhaoTechList, getJsglFenlei, getBianhaogljsList, addBianhaogljs, getGlFenlei, getBianhaoglList, addBianhaogl, addBianhaoGygch, getBianhaoGygchList, getScszhFenlei, addBianhaoScszh, getBianhaoScszhList, uploadNumberingPdf, deleteNumberingPdf, getNumberingFileUrl, exportBianhaoExcel } from '@/api/fileNumbering'
import { getPolicyUploadPermission } from '@/api/departmentPolicy'
import { getStatisticsPermission } from '@/api/attendance'

const LIST_PAGE_SIZE = 20

const router = useRouter()

const currentTab = ref('tech')
const showModal = ref(false)
const submitLoading = ref(false)
const generatedBianhao = ref('')
const techList = ref([])
const techListLoading = ref(false)
const techTotal = ref(0)
const techPage = ref(1)
const searchKeyword = ref('')
const jsglList = ref([])
const jsglListLoading = ref(false)
const jsglTotal = ref(0)
const jsglPage = ref(1)
const searchKeywordJsgl = ref('')
const jsglFenleiList = ref([])
const manageList = ref([])
const manageListLoading = ref(false)
const manageTotal = ref(0)
const managePage = ref(1)
const searchKeywordManage = ref('')
const glFenleiList = ref([])
const gygchList = ref([])
const gygchListLoading = ref(false)
const gygchTotal = ref(0)
const gygchPage = ref(1)
const searchKeywordGygch = ref('')
const scszhList = ref([])
const scszhListLoading = ref(false)
const scszhTotal = ref(0)
const scszhPage = ref(1)
const searchKeywordScszh = ref('')
const scszhFenleiList = ref([])
const pdfInputRef = ref(null)
const uploadTarget = ref({ type: '', code: '' })
const canExportBianhao = ref(false)
const exportLoading = ref(false)

const techTotalPages = computed(() => Math.max(1, Math.ceil((techTotal.value || 0) / LIST_PAGE_SIZE)))
const jsglTotalPages = computed(() => Math.max(1, Math.ceil((jsglTotal.value || 0) / LIST_PAGE_SIZE)))
const manageTotalPages = computed(() => Math.max(1, Math.ceil((manageTotal.value || 0) / LIST_PAGE_SIZE)))
const gygchTotalPages = computed(() => Math.max(1, Math.ceil((gygchTotal.value || 0) / LIST_PAGE_SIZE)))
const scszhTotalPages = computed(() => Math.max(1, Math.ceil((scszhTotal.value || 0) / LIST_PAGE_SIZE)))

const EXPORT_TABLE_BY_TAB = {
  tech: 'tech',
  jsgl: 'jsgl',
  manage: 'manage',
  gygch: 'gygch',
  scszh: 'scszh'
}

const tabTitleMap = {
  tech: '技术文件列表',
  jsgl: '技术管理文件列表',
  manage: '管理文件列表',
  gygch: '工艺过程策划表列表',
  scszh: '生产数字化编号列表',
}

const _kwRefs = { tech: searchKeyword, jsgl: searchKeywordJsgl, manage: searchKeywordManage, gygch: searchKeywordGygch, scszh: searchKeywordScszh }
const activeSearchKeyword = computed({
  get: () => (_kwRefs[currentTab.value] || searchKeyword).value,
  set: v => { (_kwRefs[currentTab.value] || searchKeyword).value = v }
})

const _pageRefs = { tech: techPage, jsgl: jsglPage, manage: managePage, gygch: gygchPage, scszh: scszhPage }
const _loaders = {
  tech: () => loadTechList(),
  jsgl: () => loadJsglList(),
  manage: () => loadManageList(),
  gygch: () => loadGygchList(),
  scszh: () => loadScszhList(),
}

function doCurrentSearch() {
  const pg = _pageRefs[currentTab.value]
  if (pg) pg.value = 1
  _loaders[currentTab.value]?.()
}

function doCurrentReset() {
  activeSearchKeyword.value = ''
  doCurrentSearch()
}

const form = ref({
  xm: '',
  bz: '',
  fenlei: '',
  flbianma: '',
  xmname: '',
  neirong: '',
  content: '',
  bhyear: null
})

// 默认按编号时间从新到旧，与接口排序一致；用户可点表头改排序
const tabSort = reactive({
  tech: { key: 'bhtime', order: 'desc' },
  jsgl: { key: 'bhtime', order: 'desc' },
  manage: { key: 'bhtime', order: 'desc' },
  gygch: { key: 'bhtime', order: 'desc' },
  scszh: { key: 'bhtime', order: 'desc' },
})
function toggleSort(tab, key) {
  const s = tabSort[tab]
  if (s.key === key) {
    s.order = s.order === 'asc' ? 'desc' : 'asc'
  } else {
    s.key = key
    s.order = 'asc'
  }
}

function sortIcon(tab, key) {
  const s = tabSort[tab]
  if (s.key !== key) return ''
  return s.order === 'asc' ? '▲' : '▼'
}

function parseLooseDate(v) {
  if (!v) return null
  const s = String(v).trim()
  const m = s.match(/^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})/)
  if (!m) return null
  return new Date(+m[1], +m[2] - 1, +m[3])
}

function applySortOnly(list, tab) {
  const s = tabSort[tab]
  if (!s.key) return list
  return [...list].sort((a, b) => {
    const va = a[s.key] ?? ''
    const vb = b[s.key] ?? ''
    const da = parseLooseDate(va)
    const db = parseLooseDate(vb)
    let cmp
    if (da && db) {
      cmp = da - db
    } else if (da) {
      cmp = -1
    } else if (db) {
      cmp = 1
    } else {
      const na = parseFloat(va)
      const nb = parseFloat(vb)
      if (!isNaN(na) && !isNaN(nb)) {
        cmp = na - nb
      } else {
        cmp = String(va).localeCompare(String(vb), 'zh-Hans-CN')
      }
    }
    return s.order === 'asc' ? cmp : -cmp
  })
}

/** 统计权限 level：3=部长/副部长可看全部专业，1/2=仅本专业 */
const permissionLevel = ref(1)
const canSeeAllFiles = computed(() => permissionLevel.value === 3)

const bianhaoFlList = ref([])
const gzhList = ref([])

/** 项目下拉展示：项目名称（工作号），便于区分同名项目 */
function formatProjectOptionLabel(item) {
  const name = (item?.gzhname || '').trim()
  const gzh = (item?.gzh || '').trim()
  if (!name) return gzh || '—'
  if (!gzh) return name
  return `${name}（${gzh}）`
}

function getCurrentUser() {
  try {
    const raw = localStorage.getItem('userInfo')
    if (!raw) return null
    const u = JSON.parse(raw)
    return { name: (u.name || u.userName || '').trim() }
  } catch {
    return null
  }
}

async function loadExportPermission() {
  const u = getCurrentUser()
  if (!u?.name) {
    canExportBianhao.value = false
    return
  }
  try {
    const res = await getPolicyUploadPermission({ name: u.name })
    canExportBianhao.value = !!(res && res.canUpload)
  } catch {
    canExportBianhao.value = false
  }
}

async function exportCurrentTable() {
  const u = getCurrentUser()
  if (!u?.name) {
    alert('请先登录')
    return
  }
  const table = EXPORT_TABLE_BY_TAB[currentTab.value]
  if (!table) return
  exportLoading.value = true
  try {
    const blob = await exportBianhaoExcel({ table, name: u.name })
    const isExcel =
      blob.type &&
      (blob.type.includes('spreadsheet') ||
        blob.type.includes('ms-excel') ||
        blob.type.includes('octet-stream'))
    if (isExcel) {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `文件编号_${table}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
      return
    }
    const text = await blob.text()
    try {
      const j = JSON.parse(text)
      alert(j.detail || '导出失败')
    } catch {
      alert(text || '导出失败')
    }
  } catch (e) {
    alert(e.response?.data?.detail || e.message || '导出失败')
  } finally {
    exportLoading.value = false
  }
}

function goTechPage(delta) {
  const next = techPage.value + delta
  if (next < 1 || next > techTotalPages.value) return
  techPage.value = next
  loadTechList()
}
function goJsglPage(delta) {
  const next = jsglPage.value + delta
  if (next < 1 || next > jsglTotalPages.value) return
  jsglPage.value = next
  loadJsglList()
}
function goManagePage(delta) {
  const next = managePage.value + delta
  if (next < 1 || next > manageTotalPages.value) return
  managePage.value = next
  loadManageList()
}
function goGygchPage(delta) {
  const next = gygchPage.value + delta
  if (next < 1 || next > gygchTotalPages.value) return
  gygchPage.value = next
  loadGygchList()
}
function goScszhPage(delta) {
  const next = scszhPage.value + delta
  if (next < 1 || next > scszhTotalPages.value) return
  scszhPage.value = next
  loadScszhList()
}

async function loadUserDept() {
  const user = getCurrentUser()
  if (!user?.name) {
    await loadExportPermission()
    return
  }
  form.value.xm = user.name
  try {
    const res = await getStatisticsPermission({ name: user.name })
    if (res && res.success !== false) {
      form.value.bz = (res.lsys || '').trim()
      permissionLevel.value = res.level ?? 1
    }
  } catch {
    // 已设置 xm，lsys 可能为空
  }
  await loadExportPermission()
}

async function loadOptions() {
  const bz = (form.value.bz || '').trim()
  if (!bz) return
  try {
    const [flRes, gzhRes] = await Promise.all([
      getBianhaoFlList({ ssks: bz }),
      getGzhList({ ssks: bz })
    ])
    bianhaoFlList.value = (flRes.list || []).filter(Boolean)
    gzhList.value = (gzhRes.list || []).filter(Boolean)
  } catch {
    bianhaoFlList.value = []
    gzhList.value = []
  }
}

async function loadGzhOnly() {
  const bz = (form.value.bz || '').trim()
  if (!bz) return
  try {
    const res = await getGzhList({ ssks: bz })
    gzhList.value = (res.list || []).filter(Boolean)
  } catch {
    gzhList.value = []
  }
}

async function loadJsglFenlei() {
  const bz = (form.value.bz || '').trim()
  if (!bz) {
    jsglFenleiList.value = []
    return
  }
  try {
    const res = await getJsglFenlei({ ssks: bz })
    jsglFenleiList.value = (res.list || []).filter(Boolean)
  } catch {
    jsglFenleiList.value = []
  }
}

async function loadGlFenlei() {
  try {
    const res = await getGlFenlei()
    glFenleiList.value = (res.list || []).filter(Boolean)
  } catch {
    glFenleiList.value = []
  }
}


async function loadScszhFenlei() {
  try {
    const res = await getScszhFenlei()
    scszhFenleiList.value = (res.list || []).filter(Boolean)
  } catch {
    scszhFenleiList.value = []
  }
}

async function loadScszhList() {
  scszhListLoading.value = true
  try {
    const params = { page: scszhPage.value, page_size: LIST_PAGE_SIZE }
    if ((form.value.bz || '').trim()) params.bz = form.value.bz.trim()
    const kw = (searchKeywordScszh.value || '').trim()
    if (kw) params.keyword = kw
    const res = await getBianhaoScszhList(params)
    scszhList.value = (res.list || []).filter(Boolean)
    scszhTotal.value = res.total ?? scszhList.value.length
  } catch {
    scszhList.value = []
    scszhTotal.value = 0
  } finally {
    scszhListLoading.value = false
  }
}

async function loadGygchList() {
  gygchListLoading.value = true
  try {
    const params = { page: gygchPage.value, page_size: LIST_PAGE_SIZE }
    if ((form.value.bz || '').trim()) params.bz = form.value.bz.trim()
    const kw = (searchKeywordGygch.value || '').trim()
    if (kw) params.keyword = kw
    const res = await getBianhaoGygchList(params)
    gygchList.value = (res.list || []).filter(Boolean)
    gygchTotal.value = res.total ?? gygchList.value.length
  } catch {
    gygchList.value = []
    gygchTotal.value = 0
  } finally {
    gygchListLoading.value = false
  }
}

function onFenleiChange() {
  const flname = form.value.fenlei
  const item = bianhaoFlList.value.find((r) => r.flname === flname)
  form.value.flbianma = item ? (item.flbianma || '').trim() : ''
}

const filteredTechList = computed(() => applySortOnly(techList.value, 'tech'))

const filteredJsglList = computed(() => applySortOnly(jsglList.value, 'jsgl'))

const filteredManageList = computed(() => applySortOnly(manageList.value, 'manage'))

const filteredGygchList = computed(() => applySortOnly(gygchList.value, 'gygch'))

const filteredScszhList = computed(() => applySortOnly(scszhList.value, 'scszh'))

async function loadTechList() {
  techListLoading.value = true
  try {
    const params = { page: techPage.value, page_size: LIST_PAGE_SIZE }
    if (!canSeeAllFiles.value && (form.value.bz || '').trim()) params.bz = form.value.bz.trim()
    const kw = (searchKeyword.value || '').trim()
    if (kw) params.keyword = kw
    const res = await getBianhaoTechList(params)
    techList.value = (res.list || []).filter(Boolean)
    techTotal.value = res.total ?? techList.value.length
  } catch {
    techList.value = []
    techTotal.value = 0
  } finally {
    techListLoading.value = false
  }
}

async function loadJsglList() {
  jsglListLoading.value = true
  try {
    const params = { page: jsglPage.value, page_size: LIST_PAGE_SIZE }
    if (!canSeeAllFiles.value && (form.value.bz || '').trim()) params.bz = form.value.bz.trim()
    const kw = (searchKeywordJsgl.value || '').trim()
    if (kw) params.keyword = kw
    const res = await getBianhaogljsList(params)
    jsglList.value = (res.list || []).filter(Boolean)
    jsglTotal.value = res.total ?? jsglList.value.length
  } catch {
    jsglList.value = []
    jsglTotal.value = 0
  } finally {
    jsglListLoading.value = false
  }
}

async function loadManageList() {
  manageListLoading.value = true
  try {
    const params = { page: managePage.value, page_size: LIST_PAGE_SIZE }
    if (!canSeeAllFiles.value && (form.value.bz || '').trim()) params.bz = form.value.bz.trim()
    const kw = (searchKeywordManage.value || '').trim()
    if (kw) params.keyword = kw
    const res = await getBianhaoglList(params)
    manageList.value = (res.list || []).filter(Boolean)
    manageTotal.value = res.total ?? manageList.value.length
  } catch {
    manageList.value = []
    manageTotal.value = 0
  } finally {
    manageListLoading.value = false
  }
}

function copyToClipboard(text) {
  if (!text) return false
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text).then(() => true).catch(() => false)
  }
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  textarea.setAttribute('readonly', '')
  document.body.appendChild(textarea)
  textarea.select()
  try {
    const ok = document.execCommand('copy')
    document.body.removeChild(textarea)
    return Promise.resolve(ok)
  } catch {
    document.body.removeChild(textarea)
    return Promise.resolve(false)
  }
}

async function copyText(text) {
  const ok = await copyToClipboard(text)
  alert(ok ? '已复制到剪贴板' : '复制失败，请手动复制')
}

function triggerUpload(type, code) {
  uploadTarget.value = { type, code }
  pdfInputRef.value?.click()
}

async function onPdfSelected(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file || uploadTarget.value.type === '') return
  const { type, code } = uploadTarget.value
  if (!code) return
  const fn = (file.name || '').toLowerCase()
  if (!fn.endsWith('.pdf')) {
    alert('请上传终版 PDF 文件，仅支持 PDF')
    return
  }
  try {
    await uploadNumberingPdf(type, code, file)
    alert('上传成功')
    if (type === 'tech') await loadTechList()
    else if (type === 'jsgl') await loadJsglList()
    else if (type === 'manage') await loadManageList()
    else if (type === 'gygch') await loadGygchList()
    else if (type === 'scszh') await loadScszhList()
  } catch (err) {
    alert(err.response?.data?.detail || err.message || '上传失败')
  }
}

function openFile(type, code, download) {
  const url = getNumberingFileUrl(type, code, download)
  window.open(url, '_blank', 'noopener')
}

async function deletePdf(type, code) {
  if (!confirm('确定删除该 PDF？删除后可重新上传。')) return
  try {
    await deleteNumberingPdf(type, code)
    alert('已删除')
    if (type === 'tech') await loadTechList()
    else if (type === 'jsgl') await loadJsglList()
    else if (type === 'manage') await loadManageList()
    else if (type === 'gygch') await loadGygchList()
    else if (type === 'scszh') await loadScszhList()
  } catch (err) {
    alert(err.response?.data?.detail || err.message || '删除失败')
  }
}

function closeModal() {
  showModal.value = false
  generatedBianhao.value = ''
}

async function copyBianhao() {
  const text = generatedBianhao.value
  const ok = await copyToClipboard(text)
  alert(ok ? '已复制到剪贴板' : '复制失败，请手动复制')
}

watch(currentTab, async (tab) => {
  if (tab === 'tech') {
    techPage.value = 1
    if (!(form.value.bz || '').trim()) await loadUserDept()
    await loadTechList()
  } else if (tab === 'jsgl') {
    jsglPage.value = 1
    if (!(form.value.bz || '').trim()) await loadUserDept()
    await loadJsglFenlei()
    await loadJsglList()
  } else if (tab === 'manage') {
    managePage.value = 1
    if (!(form.value.bz || '').trim()) await loadUserDept()
    await loadManageList()
  } else if (tab === 'gygch') {
    gygchPage.value = 1
    if (!(form.value.bz || '').trim()) await loadUserDept()
    await loadGygchList()
  } else if (tab === 'scszh') {
    scszhPage.value = 1
    if (!(form.value.bz || '').trim()) await loadUserDept()
    await loadScszhList()
  }
})

onMounted(async () => {
  await loadGlFenlei()
  await loadScszhFenlei()
  if (currentTab.value === 'tech') {
    await loadUserDept()
    await loadTechList()
  } else if (currentTab.value === 'jsgl') {
    await loadUserDept()
    await loadJsglFenlei()
    await loadJsglList()
  } else if (currentTab.value === 'manage') {
    await loadUserDept()
    await loadManageList()
  } else if (currentTab.value === 'gygch') {
    await loadUserDept()
    await loadGygchList()
  } else if (currentTab.value === 'scszh') {
    await loadUserDept()
    await loadScszhList()
  }
})

watch(showModal, async (visible) => {
  if (!visible) return
  generatedBianhao.value = ''
  form.value.xmname = ''
  form.value.neirong = ''
  form.value.content = ''
  if (currentTab.value === 'tech') {
    await loadUserDept()
    await loadOptions()
    form.value.fenlei = ''
    form.value.flbianma = ''
  } else if (currentTab.value === 'jsgl') {
    await loadUserDept()
    await loadGzhOnly()
    await loadJsglFenlei()
    form.value.fenlei = ''
  } else if (currentTab.value === 'manage') {
    await loadUserDept()
    form.value.fenlei = ''
  } else if (currentTab.value === 'gygch') {
    await loadUserDept()
    form.value.bhyear = new Date().getFullYear()
    form.value.neirong = ''
  } else if (currentTab.value === 'scszh') {
    await loadUserDept()
    form.value.fenlei = ''
    form.value.neirong = ''
    form.value.content = ''
  }
})

async function submitNumbering() {
  const f = form.value
  if (currentTab.value === 'tech') {
    if (!f.neirong?.trim()) {
      alert('请输入文件名称')
      return
    }
    if (!f.fenlei || !f.xmname) {
      alert('请选择分类名称和项目名称')
      return
    }
    submitLoading.value = true
    try {
      const res = await addBianhaoTech({
        xm: f.xm,
        bz: f.bz,
        xmname: f.xmname,
        fenlei: f.fenlei,
        flbianma: f.flbianma || f.fenlei,
        neirong: f.neirong.trim(),
        content: ''
      })
      if (res.success) {
        generatedBianhao.value = res.bianhao || ''
        techPage.value = 1
        await loadTechList()
      } else {
        alert(res.message || '生成失败')
      }
    } catch (e) {
      alert(e.response?.data?.detail || e.message || '生成失败')
    } finally {
      submitLoading.value = false
    }
    return
  }
  if (currentTab.value === 'jsgl') {
    if (!f.neirong?.trim()) {
      alert('请输入编制内容')
      return
    }
    if (!f.fenlei || !f.xmname) {
      alert('请选择分类和项目名称')
      return
    }
    submitLoading.value = true
    try {
      const res = await addBianhaogljs({
        xm: f.xm,
        bz: f.bz,
        xmname: f.xmname,
        fenlei: f.fenlei,
        neirong: f.neirong.trim(),
        content: ''
      })
      if (res.success) {
        generatedBianhao.value = res.bianhao || ''
        jsglPage.value = 1
        await loadJsglList()
      } else {
        alert(res.message || '生成失败')
      }
    } catch (e) {
      alert(e.response?.data?.detail || e.message || '生成失败')
    } finally {
      submitLoading.value = false
    }
    return
  }
  if (currentTab.value === 'manage') {
    if (!f.neirong?.trim()) {
      alert('请输入编制内容')
      return
    }
    if (!f.fenlei) {
      alert('请选择分类')
      return
    }
    submitLoading.value = true
    try {
      const res = await addBianhaogl({
        xm: f.xm,
        bz: f.bz,
        fenlei: f.fenlei,
        neirong: f.neirong.trim(),
        content: (f.content || '').trim()
      })
      if (res.success) {
        generatedBianhao.value = res.bianhao || ''
        managePage.value = 1
        await loadManageList()
      } else {
        alert(res.message || '生成失败')
      }
    } catch (e) {
      alert(e.response?.data?.detail || e.message || '生成失败')
    } finally {
      submitLoading.value = false
    }
    return
  }
  if (currentTab.value === 'gygch') {
    if (!(f.bz || '').trim()) {
      alert('科室信息为空，请重新登录')
      return
    }
    submitLoading.value = true
    try {
      const res = await addBianhaoGygch({
        xm: f.xm,
        bz: f.bz,
        bhyear: f.bhyear || undefined,
        neirong: (f.neirong || '').trim()
      })
      if (res.success) {
        generatedBianhao.value = res.bianhao || ''
        gygchPage.value = 1
        await loadGygchList()
      } else {
        alert(res.message || '生成失败')
      }
    } catch (e) {
      alert(e.response?.data?.detail || e.message || '生成失败')
    } finally {
      submitLoading.value = false
    }
    return
  }
  if (currentTab.value === 'scszh') {
    if (!f.neirong?.trim()) {
      alert('请输入编制内容')
      return
    }
    if (!f.fenlei) {
      alert('请选择项目')
      return
    }
    submitLoading.value = true
    try {
      const res = await addBianhaoScszh({
        xm: f.xm,
        bz: f.bz,
        fenlei: f.fenlei,
        neirong: f.neirong.trim(),
        content: (f.content || '').trim()
      })
      if (res.success) {
        generatedBianhao.value = res.bianhao || ''
        scszhPage.value = 1
        await loadScszhList()
      } else {
        alert(res.message || '生成失败')
      }
    } catch (e) {
      alert(e.response?.data?.detail || e.message || '生成失败')
    } finally {
      submitLoading.value = false
    }
    return
  }
  alert('功能开发中')
  showModal.value = false
}
function goTechCategory() {
  router.push('/file/tech-category')
}

function goWorkNo() {
  router.push('/file/workno')
}
</script>

<style scoped>
.page-container {
  width: 100%;
  max-width: none;
  margin: 0;
  padding-top: 0;
  padding-bottom: var(--spacing-xl);
  padding-left: 0;
  padding-right: 0;
}

.tabs {
  display: flex;
  gap: var(--spacing-md);
  margin-top: var(--spacing-lg);
  margin-bottom: 0;
  padding: 0 var(--spacing-lg);
  background: var(--color-bg-container);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  border: 1px solid var(--color-border-lighter);
}

.page-container .tabs + .content {
  margin-top: 0;
}


.tab-item {
  padding: var(--spacing-md) var(--spacing-xl);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  color: var(--color-text-secondary);
  font-weight: 500;
}

.tab-item.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}


.card {
  background: white;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-lighter);
}

.card-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-lighter);
}

.record-card__header {
  padding: var(--spacing-lg) var(--spacing-xl);
  background: white;
  border-bottom: 1px solid var(--color-border-lighter);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: var(--spacing-md);
}
.record-card__header h3 {
  margin: 0;
}
.record-card__filters {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}
.record-card__filters .filter-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  white-space: nowrap;
}
.record-card__filters .filter-input {
  padding: 6px 10px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
}
.record-card__filters .filter-input--search {
  min-width: 10rem;
  max-width: 16rem;
}

.card-body {
  padding: var(--spacing-lg);
}

.empty-text {
  text-align: center;
  color: var(--color-text-secondary);
  padding: var(--spacing-xxl) 0;
}

.table-wrap {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.data-table th,
.data-table td {
  padding: 10px 12px;
  border: 1px solid var(--color-border-lighter);
  text-align: left;
}

.data-table th {
  background: var(--color-bg-lighter, #f5f5f5);
  font-weight: 600;
}

.sortable-th {
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}
.sortable-th:hover {
  background: var(--color-bg-hover, #eaeaea);
}

.sort-icon {
  font-size: 0.7em;
  color: var(--color-primary, #1677ff);
  margin-left: 2px;
}


.data-table tbody tr:hover {
  background: var(--color-bg-lighter, #fafafa);
}

.bianhao-code {
  font-family: var(--font-mono, monospace);
  letter-spacing: 0.02em;
  margin-right: 8px;
}

.btn-copy-small {
  padding: 2px 8px;
  font-size: 0.8rem;
  border-radius: 4px;
  border: 1px solid var(--color-border-base);
  background: #fff;
  cursor: pointer;
}

.btn-copy-small:hover {
  background: var(--color-bg-lighter, #f0f0f0);
}

.file-actions {
  white-space: nowrap;
}
.file-actions .btn-copy-small {
  margin-right: 4px;
}

/* 上传：主色 */
.btn-upload {
  color: var(--color-primary, #1677ff);
  border-color: var(--color-primary, #1677ff);
  background: rgba(22, 119, 255, 0.06);
}
.btn-upload:hover {
  background: rgba(22, 119, 255, 0.15);
}

/* 删除：红色 */
.btn-delete {
  color: var(--color-danger, #c00);
  border-color: var(--color-danger, #c00);
  background: rgba(204, 0, 0, 0.06);
}
.btn-delete:hover {
  background: rgba(204, 0, 0, 0.15);
}

/* 预览：蓝色/信息色 */
.btn-preview {
  color: #1890ff;
  border-color: #1890ff;
  background: rgba(24, 144, 255, 0.06);
}
.btn-preview:hover {
  background: rgba(24, 144, 255, 0.15);
}

/* 下载：绿色 */
.btn-download {
  color: #52c41a;
  border-color: #52c41a;
  background: rgba(82, 196, 26, 0.06);
}
.btn-download:hover {
  background: rgba(82, 196, 26, 0.15);
}

.hidden-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  overflow: hidden;
}

.table-footer {
  margin-top: var(--spacing-md);
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.table-footer-pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.pager-btns {
  display: flex;
  gap: var(--spacing-sm);
}

.pager-btn {
  font-size: 0.85rem;
  padding: 4px 12px;
}

.mb-lg {
  margin-bottom: var(--spacing-lg);
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-content {
  background: white;
  padding: var(--spacing-xl);
  border-radius: var(--radius-md);
  width: 500px;
  max-width: 90%;
}

.form-group {
  margin-bottom: var(--spacing-lg);
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-xs);
  font-weight: 500;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid var(--color-border-base);
  border-radius: var(--radius-sm);
}

.form-group input.readonly {
  background: var(--color-bg-lighter, #f5f5f5);
  color: var(--color-text-secondary, #666);
  cursor: default;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
  margin-top: var(--spacing-xl);
}

.result-block {
  padding: var(--spacing-lg) 0;
}
.result-label {
  margin-bottom: var(--spacing-xs);
  color: var(--color-text-secondary);
  font-size: 0.9em;
}
.result-bianhao {
  font-size: 1.25rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  margin-bottom: var(--spacing-xl);
  word-break: break-all;
}
.result-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
}
.btn-copy {
  background: var(--color-bg-lighter, #f0f0f0);
  border-color: var(--color-border-base);
}
.btn-copy:hover {
  background: var(--color-border-lighter, #e8e8e8);
}

button {
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-base);
  cursor: pointer;
  background: white;
}

.btn-primary {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}
</style>
