<template>
  <main class="screen">
    <div class="industrial-bg" aria-hidden="true"><i></i><i></i><i></i></div>
    <div class="ambient a1"></div><div class="ambient a2"></div>
    <header class="topbar">
      <div class="brand"><span class="mark">OA</span><div><h1>系统访问情况组态看板</h1><p>INTELLIGENT MANUFACTURING · OPERATION CENTER</p></div></div>
      <div class="platform-title"><span>哈电机智能制造工艺部集成办公平台</span></div>
      <div class="headline"><i></i><span>数据实时监测中</span><b>{{ clock }}</b><small>{{ dateText }}</small></div>
    </header>

    <section v-if="error" class="error-state"><h2>数据连接暂时中断</h2><p>{{ error }}</p><button @click="load">重新连接</button></section>
    <template v-else>
      <section class="metrics">
        <article v-for="card in metricCards" :key="card.label" class="metric-card">
          <div class="metric-icon" v-html="card.icon"></div><div class="metric-copy"><span>{{ card.label }}</span><strong>{{ fmt(card.value) }}</strong><em>{{ card.note }}</em></div>
        </article>
      </section>

      <section class="grid">
        <article class="panel trend-panel">
          <PanelTitle icon="trend" title="近 7 日访问趋势" />
          <div class="legend"><span><i class="cyan"></i>访问次数</span><span><i class="blue"></i>访问人数</span></div>
          <svg class="trend" viewBox="0 0 720 240" preserveAspectRatio="none">
            <defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#20c8ff" stop-opacity=".48"/><stop offset="1" stop-color="#0878d8" stop-opacity=".04"/></linearGradient></defs>
            <g class="lines"><line v-for="n in 6" :key="n" x1="54" :y1="22+(n-1)*35" x2="705" :y2="22+(n-1)*35"/></g>
            <g class="axis-labels"><text v-for="n in 6" :key="n" x="42" :y="26+(n-1)*35">{{ fmt(Math.round(dailyMax*(6-n)/5)) }}</text></g>
            <path :d="areaPath" fill="url(#area)"/><polyline :points="visitPoints" class="line visit"/><polyline :points="userPoints" class="line user"/>
            <g v-for="(d,i) in data.daily" :key="d.day"><circle :cx="x(i, data.daily.length)" :cy="y(d.visits, dailyMax)" r="4"/><text :x="x(i,data.daily.length)" y="225">{{ d.day.slice(5) }}</text></g>
          </svg>
        </article>

        <article class="panel health-panel">
          <PanelTitle icon="shield" title="核心服务状态" />
          <div class="gauge-row">
            <div class="gauge-item"><div class="mini-gauge health" :style="gaugeStyle(healthScore)"><div><strong>{{ healthScore }}%</strong><small>健康度</small></div></div><span>OA 应用服务</span><em><i></i>正常</em></div>
            <div class="gauge-item"><div class="mini-gauge" :style="gaugeStyle(data.hardware?.cpu)"><div><strong>{{ gaugeValue(data.hardware?.cpu) }}</strong><small>CPU 使用率</small></div></div><span>业务数据库</span><em><i></i>{{ data.hardware?.cpu_cores || '--' }} 核</em></div>
            <div class="gauge-item"><div class="mini-gauge" :style="gaugeStyle(data.hardware?.memory)"><div><strong>{{ gaugeValue(data.hardware?.memory) }}</strong><small>内存使用率</small></div></div><span>服务器资源</span><em><i></i>{{ capacity(data.hardware?.memory_used_gb, data.hardware?.memory_total_gb) }}</em></div>
            <div class="gauge-item"><div class="mini-gauge" :style="gaugeStyle(data.hardware?.disk)"><div><strong>{{ gaugeValue(data.hardware?.disk) }}</strong><small>磁盘使用率</small></div></div><span>磁盘存储资源</span><em><i></i>{{ capacity(data.hardware?.disk_used_gb, data.hardware?.disk_total_gb) }}</em></div>
          </div>
          <div class="service-summary"><span class="shield-mini">◇</span>所有核心服务运行{{ healthScore === 100 ? '正常' : '状态已更新' }}</div>
        </article>

        <article class="panel hourly-panel">
          <PanelTitle icon="clock" title="今日访问时段分布" />
          <div class="chart-grid"><span v-for="n in 7" :key="n">{{ Math.round(hourMax*(7-n)/6) }}</span></div>
          <div class="bars"><div v-for="h in data.hourly" :key="h.hour" class="bar-wrap" :title="`${h.hour}:00 · ${h.visits} 次`"><div class="bar" :style="{height: Math.max(3,h.visits/hourMax*100)+'%'}"></div><span v-if="h.hour%3===0">{{ pad(h.hour) }}</span></div></div>
        </article>

        <article class="panel pages-panel">
          <PanelTitle icon="fire" title="热门功能排行" />
          <div class="ranking"><div v-for="(p,i) in data.pages.slice(0,6)" :key="p.path" :title="displayPageTitle(p)"><em>{{ pad(i+1) }}</em><span>{{ displayPageTitle(p) }}</span><div><i :style="{width:(p.visits/pageMax*100)+'%'}"></i></div><b>{{ p.visits }}</b></div><p v-if="!data.pages.length" class="empty">今日暂无访问记录</p></div>
        </article>

        <article class="panel dept-panel">
          <PanelTitle icon="building" title="科室活跃度" />
          <div class="dept-head"><span>科室名称</span><b>活跃人数</b><em>访问次数</em></div>
          <div class="dept-list"><div v-for="d in data.departments.slice(0,6)" :key="d.department"><span>{{ d.department }}</span><div><i :style="{width:(d.visits/deptMax*100)+'%'}"></i></div><b>{{ d.users }} 人</b><em>{{ d.visits }} 次</em></div><p v-if="!data.departments.length" class="empty">等待访问数据沉淀</p></div>
        </article>

        <article class="panel live-panel">
          <PanelTitle icon="live" title="实时访问动态" />
          <div class="live-list"><div v-for="(r,i) in data.recent.slice(0,7)" :key="i"><time>{{ r.time }}</time><i :class="{warning:i === 3}"></i><span><b>{{ mask(r.user_name) }}</b> 访问了 {{ displayPageTitle(r) }}</span><em>{{ r.department || '未归属' }}</em></div><p v-if="!data.recent.length" class="empty">新的访问将实时显示在这里</p></div>
        </article>
      </section>
    </template>
    <footer><span></span><b><i>◇</i> 数据每 30 秒自动刷新</b><span></span></footer>
  </main>
</template>

<script setup>
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref } from 'vue'
import { getAccessDashboard } from '@/api/accessDashboard'
const PANEL_ICONS={trend:'↗',shield:'⬡',clock:'◷',fire:'♨',building:'▥',live:'◉'}
const PanelTitle=defineComponent({props:['title','icon'],setup:p=>()=>h('div',{class:'panel-title'},[h('i',{class:`title-icon ${p.icon||''}`},PANEL_ICONS[p.icon]||'◇'),h('h2',p.title)])})
const data=ref({summary:{},daily:[],hourly:[],pages:[],departments:[],recent:[],services:[],hardware:{}}); const error=ref(''); const now=ref(new Date()); let refreshTimer,clockTimer
const userName=()=>{try{const u=JSON.parse(localStorage.getItem('userInfo')||'{}');return (u.name||u.userName||'').trim()}catch{return ''}}
async function load(){try{error.value='';data.value=await getAccessDashboard({current_user:userName()})}catch(e){error.value=e?.response?.data?.detail||e.message||'无法获取看板数据'}}
const clock=computed(()=>now.value.toLocaleTimeString('zh-CN',{hour12:false})); const dateText=computed(()=>`${now.value.toLocaleDateString('zh-CN',{year:'numeric',month:'2-digit',day:'2-digit'})}\n${now.value.toLocaleDateString('zh-CN',{weekday:'short'})}`)
const generatedTime=computed(()=>(data.value.generated_at||'--').slice(11)); const fmt=v=>Number(v||0).toLocaleString('zh-CN'); const pad=v=>String(v).padStart(2,'0')
const metricCards=computed(()=>[
  {label:'今日访问次数',value:data.value.summary.visits,note:'累计页面浏览量',icon:'<svg viewBox="0 0 48 48"><path d="M10 34l9-10 7 6 12-15M29 15h9v9"/></svg>'},
  {label:'今日访问人数',value:data.value.summary.unique_users,note:'独立登录用户',icon:'<svg viewBox="0 0 48 48"><circle cx="19" cy="18" r="7"/><circle cx="32" cy="20" r="5"/><path d="M7 37c1-8 5-12 12-12s11 4 12 12M29 28c7 0 10 3 11 9"/></svg>'},
  {label:'当前活跃用户',value:data.value.summary.active_users,note:'近 15 分钟',icon:'<svg viewBox="0 0 48 48"><path d="M7 25h9l4-12 7 24 5-16 3 4h7"/></svg>'},
  {label:'系统在册用户',value:data.value.summary.total_users,note:'当前在职人员',icon:'<svg viewBox="0 0 48 48"><circle cx="21" cy="18" r="7"/><path d="M8 38c1-9 5-13 13-13s12 4 13 13M36 15v10M31 20h10"/></svg>'}
])
const dailyMax=computed(()=>Math.max(5,...data.value.daily.map(d=>+d.visits))); const hourMax=computed(()=>Math.max(1,...data.value.hourly.map(d=>+d.visits))); const pageMax=computed(()=>Math.max(1,...data.value.pages.map(d=>+d.visits))); const deptMax=computed(()=>Math.max(1,...data.value.departments.map(d=>+d.visits)))
const x=(i,n)=>66+i*(624/Math.max(1,n-1)); const y=(v,max)=>197-(+v/max)*175
const visitPoints=computed(()=>data.value.daily.map((d,i)=>`${x(i,data.value.daily.length)},${y(d.visits,dailyMax.value)}`).join(' ')); const userPoints=computed(()=>data.value.daily.map((d,i)=>`${x(i,data.value.daily.length)},${y(d.users,dailyMax.value)}`).join(' ')); const areaPath=computed(()=>data.value.daily.length?`M ${visitPoints.value.replaceAll(' ',' L ')} L 690 197 L 66 197 Z`:'')
const healthScore=computed(()=>{const s=data.value.services;if(!s.length)return 0;return Math.round(s.filter(v=>v.status==='ok').length/s.length*100)})
const gaugeStyle=value=>{const v=Math.max(0,Math.min(100,Number(value)||0));const color=v>=90?'#fb7185':v>=75?'#fbbf24':'#22d3ee';return {'--gauge':`${v*3.6}deg`,'--gauge-color':color}}
const gaugeValue=value=>value==null?'--':`${Math.round(Number(value))}%`
const capacity=(used,total)=>used==null||total==null?'未采集':`${used}/${total} GB`
const PAGE_NAMES={
  '/':'工作台首页','/attendance':'个人考勤查询','/upload':'打卡数据上传','/statistics':'综合统计分析',
  '/reports-hub':'报表汇聚中心','/leader-dashboard':'管理驾驶舱','/leader-overtime-statistics':'领导加班统计',
  '/overtime-pay':'加班费统计','/performance':'员工绩效管理','/attendance/manual':'请假与加班填报',
  '/attendance/business-trip':'公出登记','/attendance/approvals':'考勤审批','/attendance/pending-tasks':'考勤待办任务',
  '/attendance/my-applications':'我的考勤申请','/attendance/personnel-visualization':'人员出勤可视化',
  '/attendance/shift-schedule':'排班管理','/attendance/discipline':'考勤纪律审查','/attendance/exceptions':'考勤异常管理',
  '/attendance/holiday-settings':'假期调休设置','/attendance/holiday-duty-check':'假期值班出勤核查',
  '/file/numbering':'文件编号管理','/file/tech-category':'技术文件分类管理','/file/workno':'工作号管理',
  '/file/policy-query':'部门制度查询','/file/bid-templates':'投标文件模板库','/file/tech-problem':'工艺技术问题手册',
  '/profile':'个人资料','/admin/employees':'员工在职管理','/admin/db-manager':'数据库表管理',
  '/admin/health-monitor':'系统配置与健康监控','/admin/yggl-fill':'员工主表批量填充','/admin/email':'邮件发送管理',
  '/admin/notification':'系统消息推送','/admin/inbox-emails':'公共邮箱收件管理','/admin/hxp-manage':'换休票管理',
  '/admin/mashangban':'工艺码上办月报','/admin/hxp-records':'换休票明细查询','/feedback':'意见与建议','/contacts':'部门通讯录',
  '/info-feed':'天气新闻资讯','/ai-assistant':'智能制造工艺部 AI 助手','/seal/apply':'部门用印申请',
  '/low-value-reimbursement':'低值易耗品报销','/massage-chair':'健康角预约','/confidentiality-ledger':'论文保密审批台账',
  '/action-items/dashboard':'行动项驾驶舱','/action-items/minutes':'会议纪要','/action-items/ledger':'行动项台账',
  '/action-items/my':'我的行动项','/action-items/messages':'行动项消息','/action-items/approvals':'行动项审批'
}
const pageName=p=>PAGE_NAMES[p]||(/^\/action-items\/[^/]+$/.test(p)?'行动项详情':p.split('/').filter(Boolean).pop()||'首页')
const displayPageTitle=item=>{const title=String(item?.title||'').trim();return !title||title==='智能制造工艺部集成办公平台'?pageName(item?.path||''):title}
const statusLabel=s=>s==='ok'?'正常':s==='unconfigured'?'未配置':'异常'; const mask=n=>{n=String(n||'');return n.length>1?n[0]+'*':n}
onMounted(()=>{load();refreshTimer=setInterval(load,30000);clockTimer=setInterval(()=>now.value=new Date(),1000)});onBeforeUnmount(()=>{clearInterval(refreshTimer);clearInterval(clockTimer)})
</script>

<style scoped>
*{box-sizing:border-box}.screen{--cyan:#22d3ee;--blue:#3b82f6;min-height:100vh;color:#dcecff;background:#06101f;font-family:"Microsoft YaHei",sans-serif;padding:18px 24px 10px;position:relative;overflow:hidden}.screen:before{content:"";position:absolute;inset:0;background-image:linear-gradient(rgba(42,114,180,.06) 1px,transparent 1px),linear-gradient(90deg,rgba(42,114,180,.06) 1px,transparent 1px);background-size:44px 44px;pointer-events:none}.ambient{position:absolute;border-radius:50%;filter:blur(100px);opacity:.15}.a1{width:420px;height:420px;background:#0ea5e9;left:-150px;top:15%}.a2{width:360px;height:360px;background:#2563eb;right:-100px;bottom:-120px}.topbar{height:76px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(56,189,248,.22);position:relative}.topbar:after{content:"";position:absolute;bottom:-1px;left:33%;width:34%;height:2px;background:linear-gradient(90deg,transparent,var(--cyan),transparent)}.brand{display:flex;align-items:center;gap:14px}.mark{width:52px;height:52px;display:grid;place-items:center;font:800 17px Arial;border:1px solid #38bdf8;background:linear-gradient(135deg,#0c4a6e,#082f49);clip-path:polygon(14% 0,100% 0,100% 72%,72% 100%,0 100%,0 14%)}h1{font-size:25px;letter-spacing:4px;margin:0;color:#f0f8ff}.brand p{font:10px Arial;letter-spacing:2.4px;color:#5595b8;margin:6px 0 0}.headline{display:flex;align-items:center;gap:11px;font-size:13px}.headline i,.health-score p i{width:7px;height:7px;border-radius:50%;background:#34d399;box-shadow:0 0 10px #34d399}.headline b{font:600 27px "DIN Alternate",monospace;color:#fff;margin-left:16px}.headline small{color:#7da2bd}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:16px 0}.metric-card,.panel{position:relative;background:linear-gradient(145deg,rgba(10,31,55,.92),rgba(5,20,38,.82));border:1px solid rgba(65,155,211,.24);box-shadow:inset 0 1px rgba(255,255,255,.02),0 10px 30px rgba(0,0,0,.12)}.metric-card{height:100px;padding:16px 20px;display:flex;align-items:center;gap:17px}.metric-card:after,.panel:after{content:"";position:absolute;right:-1px;top:-1px;width:22px;height:22px;border-top:2px solid var(--cyan);border-right:2px solid var(--cyan)}.metric-icon{width:48px;height:48px;display:grid;place-items:center;color:var(--cyan);font-size:25px;border:1px solid rgba(34,211,238,.28);background:rgba(14,165,233,.08)}.metric-card span{font-size:12px;color:#88a9c1}.metric-card strong{display:inline-block;font:700 29px "DIN Alternate",Arial;color:#fff;margin:0 12px 0 0}.metric-card em{display:block;font-style:normal;font-size:10px;color:#4f7895;margin-top:3px}.grid{display:grid;grid-template-columns:1.35fr 1fr .9fr;grid-template-rows:300px 255px;gap:14px}.panel{padding:14px 16px;min-width:0;overflow:hidden}.panel-title{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:1px solid rgba(75,135,174,.16);padding-bottom:9px}.panel-title h2{font-size:15px;letter-spacing:1px;margin:0;color:#e6f4ff}.panel-title small{display:block;font:8px Arial;letter-spacing:1.6px;color:#477793;margin-top:4px}.panel-title span{width:35px;height:3px;background:linear-gradient(90deg,var(--cyan),transparent)}.legend{position:absolute;right:18px;top:24px;display:flex;gap:12px;font-size:9px;color:#6f91aa}.legend i{display:inline-block;width:12px;height:2px;vertical-align:middle;margin-right:4px}.cyan{background:var(--cyan)}.blue{background:var(--blue)}.trend{width:100%;height:225px;margin-top:5px;overflow:visible}.lines line{stroke:rgba(89,143,178,.12)}.line{fill:none;stroke-width:2.2;vector-effect:non-scaling-stroke}.visit{stroke:var(--cyan)}.user{stroke:#3b82f6;stroke-dasharray:5 4}.trend circle{fill:#dffaff;stroke:var(--cyan);stroke-width:2}.trend text{fill:#668aa3;font-size:9px;text-anchor:middle}.health-score{display:flex;align-items:center;gap:19px;padding:14px 4px 8px}.ring{--score:0deg;width:105px;height:105px;border-radius:50%;display:grid;place-content:center;text-align:center;background:radial-gradient(circle at center,#071527 61%,transparent 63%),conic-gradient(var(--cyan) var(--score),rgba(40,91,122,.25) 0);box-shadow:0 0 25px rgba(34,211,238,.1)}.ring strong{font:700 28px Arial;color:#fff}.ring span{font-size:9px;color:#668ca6}.health-score p{font-size:12px;line-height:2;color:#acd0e6}.health-score p i{display:inline-block;margin-right:7px}.health-score small{color:#547992}.services{display:grid;gap:7px}.services div{height:30px;padding:0 10px;display:flex;align-items:center;background:rgba(15,52,77,.34);font-size:11px}.services i{width:6px;height:6px;border-radius:50%;margin-right:9px}.services i.ok{background:#34d399;box-shadow:0 0 7px #34d399}.services i.error{background:#fb7185}.services i.unconfigured{background:#fbbf24}.services span{flex:1}.services b{font-weight:400;color:#7aa3bc}.bars{height:205px;display:flex;align-items:flex-end;gap:3px;padding-top:18px}.bar-wrap{height:172px;flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;position:relative}.bar{width:70%;min-height:3px;background:linear-gradient(180deg,var(--cyan),#1265a0);box-shadow:0 0 5px rgba(34,211,238,.25)}.bar-wrap span{position:absolute;bottom:-18px;font-size:8px;color:#547a94}.ranking,.dept-list,.live-list{padding-top:11px}.ranking>div{display:grid;grid-template-columns:25px 110px 1fr 35px;gap:7px;align-items:center;height:29px;font-size:10px}.ranking em{font-style:normal;color:#4e7793}.ranking span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.ranking div>div,.dept-list div>div{height:4px;background:rgba(49,95,127,.28)}.ranking div>div i,.dept-list div>div i{height:100%;display:block;background:linear-gradient(90deg,#1576b8,var(--cyan))}.ranking b{text-align:right;color:#91dff3}.dept-list>div{display:grid;grid-template-columns:105px 1fr 40px 45px;gap:7px;align-items:center;height:29px;font-size:10px}.dept-list span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.dept-list b{font-weight:400;color:#a3dbe9}.dept-list em{font-style:normal;color:#547d97;text-align:right}.live-list>div{display:grid;grid-template-columns:55px 10px 1fr 75px;align-items:center;height:27px;font-size:10px;border-bottom:1px dashed rgba(73,124,157,.12)}.live-list time{font-family:monospace;color:#5f8ba6}.live-list i{width:5px;height:5px;border-radius:50%;background:#22d3ee}.live-list span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#89a9bc}.live-list span b{color:#d3edfa}.live-list em{font-style:normal;text-align:right;color:#517690;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}.empty{text-align:center;color:#456c86;font-size:11px;padding:30px 0}.error-state{height:65vh;display:grid;place-content:center;text-align:center}.error-state h2{color:#fff}.error-state p{color:#7194ac}.error-state button{justify-self:center;background:#0e7490;color:#fff;border:1px solid #22d3ee;padding:8px 22px}footer{height:30px;display:flex;align-items:end;justify-content:space-between;color:#426984;font-size:9px;position:relative}footer b{font-weight:400;color:#5c8da9}@media(max-width:1200px){.grid{grid-template-columns:1.2fr 1fr;grid-template-rows:auto}.health-panel{grid-column:2}.hourly-panel{grid-column:1/-1}.screen{overflow:auto}.metrics{grid-template-columns:repeat(2,1fr)}}
/* 1920×1080 常驻屏适配：各区域随浏览器可视高度分配，避免纵向裁切。 */
.screen{height:100vh;min-height:720px;padding:14px 24px 8px;display:flex;flex-direction:column}
.topbar{height:68px;min-height:68px}.metrics{margin:12px 0;flex:none}.metric-card{height:88px;padding-top:12px;padding-bottom:12px}
.grid{grid-template-columns:1.28fr 1.08fr .9fr;grid-template-rows:minmax(260px,1.12fr) minmax(220px,.88fr);gap:12px;flex:1;min-height:0}
.panel{padding:12px 15px;min-height:0}.trend-panel,.hourly-panel{display:flex;flex-direction:column}.trend-panel .panel-title,.hourly-panel .panel-title{flex:none}.trend{display:block;flex:1;width:100%;height:auto;min-height:0;margin:3px 0 0;overflow:hidden}
.gauge-row{height:130px;display:grid;grid-template-columns:repeat(4,1fr);gap:8px;align-items:center;padding:5px 0}
.mini-gauge{--gauge:0deg;--gauge-color:#22d3ee;width:min(86px,100%);aspect-ratio:1;border-radius:50%;display:grid;place-items:center;margin:auto;background:radial-gradient(circle,#071527 59%,transparent 61%),conic-gradient(var(--gauge-color) var(--gauge),rgba(40,91,122,.25) 0);filter:drop-shadow(0 0 8px rgba(34,211,238,.12))}
.mini-gauge>div{text-align:center;max-width:76px}.mini-gauge strong{display:block;font:700 17px Arial;color:#fff}.mini-gauge small{display:block;margin-top:3px;font-size:7px;line-height:1.25;color:#6f99b2;white-space:normal}.mini-gauge.health{--gauge-color:#34d399}
.services{grid-template-columns:repeat(3,1fr);gap:6px}.services div{height:27px;padding:0 8px}.services b{font-size:9px}
.bars{height:auto;flex:1;min-height:0;padding:8px 0 0;align-items:stretch}.bar-wrap{height:auto;min-height:0;padding-bottom:20px;justify-content:flex-end}.bar{max-height:calc(100% - 20px)}.bar-wrap span{bottom:2px;line-height:12px}
.ranking{display:grid;grid-template-rows:repeat(6,minmax(27px,1fr));height:calc(100% - 37px);padding-top:6px}
.ranking>div{grid-template-columns:25px minmax(145px,1.35fr) minmax(60px,.75fr) 35px;height:auto;min-height:27px}
.ranking span{overflow:visible;text-overflow:clip;white-space:normal;line-height:1.25;word-break:break-word}
.dept-list,.live-list{height:calc(100% - 37px);padding-top:6px;display:flex;flex-direction:column;justify-content:space-evenly}.dept-list>div,.live-list>div{min-height:25px;height:auto}
footer{height:24px;min-height:24px}
@media(max-height:850px){.brand p{display:none}.topbar{height:56px;min-height:56px}.mark{width:44px;height:44px}.metrics{margin:8px 0}.metric-card{height:76px}.metric-icon{width:42px;height:42px}.grid{grid-template-rows:minmax(235px,1.08fr) minmax(205px,.92fr)}.gauge-row{height:108px}.mini-gauge{width:min(72px,100%)}.services div{height:24px}}
@media(max-width:1200px){.screen{height:auto;min-height:100vh;overflow:auto}.grid{grid-template-columns:1.2fr 1fr;grid-template-rows:auto}.health-panel{grid-column:2}.hourly-panel{grid-column:1/-1}.metrics{grid-template-columns:repeat(2,1fr)}}

/* 访问组态看板 · 设计稿复刻层 */
.screen{
  --cyan:#2fc7ff;--blue:#2389ff;--deep:#020b16;--panel:#071d32;
  position:fixed;inset:0;z-index:1000;height:100vh;min-height:760px;padding:0 22px;color:#d9ecff;
  background:
    radial-gradient(ellipse at 50% -8%,rgba(8,92,154,.20),transparent 46%),
    radial-gradient(ellipse at 10% 88%,rgba(0,112,191,.10),transparent 35%),
    linear-gradient(180deg,#020a14 0,#041426 15%,#031323 100%);
  font-family:"Microsoft YaHei","PingFang SC",sans-serif;
}
.screen:before{opacity:.65;background-size:56px 56px;background-image:linear-gradient(rgba(32,130,190,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(32,130,190,.035) 1px,transparent 1px)}
.screen:after{content:"";position:absolute;inset:0;pointer-events:none;background:linear-gradient(90deg,rgba(0,85,154,.12),transparent 12%,transparent 88%,rgba(0,85,154,.10));box-shadow:inset 0 0 90px rgba(0,0,0,.3)}
.ambient{z-index:0;opacity:.10}.industrial-bg{position:absolute;z-index:0;left:0;right:0;top:0;height:105px;overflow:hidden;border-bottom:1px solid rgba(31,132,205,.24);pointer-events:none}
.industrial-bg:before{content:"";position:absolute;left:33%;right:15%;top:-125px;height:260px;border:1px solid rgba(20,120,190,.14);border-radius:50%;transform:skewX(-12deg);box-shadow:0 0 0 18px rgba(16,100,170,.02),0 0 0 42px rgba(16,100,170,.018)}
.industrial-bg:after{content:"";position:absolute;right:5%;top:-50px;width:430px;height:190px;opacity:.22;background:repeating-linear-gradient(156deg,transparent 0 12px,rgba(26,126,194,.18) 13px,transparent 14px)}
.industrial-bg i{position:absolute;border:1px solid rgba(35,136,204,.13);border-radius:50%}.industrial-bg i:nth-child(1){width:112px;height:112px;right:25%;top:-7px;box-shadow:0 0 0 11px rgba(16,110,180,.025),inset 0 0 0 20px rgba(8,74,125,.03)}.industrial-bg i:nth-child(2){width:220px;height:220px;left:35%;top:-160px}.industrial-bg i:nth-child(3){width:310px;height:80px;left:4%;top:65px;border-radius:50%}
.topbar,.metrics,.grid,footer,.error-state{z-index:1}.topbar{height:105px;min-height:105px;padding:0;position:relative;border-bottom:1px solid rgba(40,145,216,.20)}
.topbar:after{left:8%;width:84%;height:1px;background:linear-gradient(90deg,transparent,#1687d1 18%,transparent 50%,#1687d1 82%,transparent)}
.brand{height:100%;gap:22px}.mark{position:relative;width:96px;height:74px;clip-path:polygon(0 0,78% 0,100% 50%,78% 100%,0 100%);font:800 35px "Arial Narrow",Arial;letter-spacing:3px;border:0;background:linear-gradient(90deg,rgba(7,31,51,.88),rgba(7,63,104,.38));filter:drop-shadow(0 0 8px rgba(29,139,209,.12))}
.mark:before{content:"";position:absolute;inset:0;clip-path:inherit;background:linear-gradient(120deg,#064476,#168bd7,#064476);z-index:-2}.mark:after{content:"";position:absolute;inset:1px;clip-path:inherit;background:#071b2b;z-index:-1}.brand h1{font-size:34px;line-height:1;font-weight:700;letter-spacing:6px;text-shadow:0 0 14px rgba(171,222,255,.20)}.brand p{font:12px Arial;letter-spacing:1.5px;color:#9bb2c5;margin-top:9px}
.platform-title{position:absolute;left:50%;top:0;transform:translateX(-50%);width:460px;height:54px;display:flex;justify-content:center;align-items:center;color:#e4f0ff;font-size:17px;letter-spacing:4px;white-space:nowrap;clip-path:polygon(6% 0,94% 0,100% 0,89% 100%,11% 100%,0 0);background:linear-gradient(90deg,#0876c4,#123e72 15%,#123e72 85%,#0876c4)}
.platform-title:before{content:"";position:absolute;inset:0 1px 1px;clip-path:inherit;background:linear-gradient(180deg,#061422,#04101d)}.platform-title span{position:relative}
.headline{height:100%;padding-top:10px;gap:13px;font-size:14px;align-items:center}.headline i{width:10px;height:10px}.headline b{font:500 27px "Consolas","DIN Alternate",monospace;letter-spacing:2px;margin-left:7px;padding-left:20px;border-left:1px solid rgba(47,199,255,.28)}.headline small{width:76px;font-size:11px;line-height:1.65;color:#b7c9d7;white-space:pre-line}
.metrics{height:110px;margin:12px 0 11px;gap:13px}.metric-card{height:110px;padding:16px 19px;gap:25px;border-radius:5px;background:linear-gradient(110deg,rgba(10,38,64,.96),rgba(5,25,44,.88));border:1px solid rgba(65,153,209,.34);box-shadow:inset 0 1px rgba(172,226,255,.05),0 8px 22px rgba(0,0,0,.12)}
.metric-card:before{content:"";position:absolute;inset:0;background:linear-gradient(115deg,rgba(36,145,214,.09),transparent 45%);pointer-events:none}.metric-card:after{display:none}.metric-icon{width:72px;height:72px;min-width:72px;border-radius:50%;font-size:0;border:1px solid rgba(47,199,255,.52);background:radial-gradient(circle,rgba(20,104,159,.25),rgba(4,25,43,.76) 68%);box-shadow:inset 0 0 15px rgba(14,115,179,.16),0 0 14px rgba(20,139,213,.08)}
.metric-icon :deep(svg){width:43px;height:43px;fill:none;stroke:#2faeff;stroke-width:3;stroke-linecap:round;stroke-linejoin:round;filter:drop-shadow(0 0 4px rgba(40,177,255,.45))}.metric-copy{display:flex;flex-direction:column;justify-content:center;height:100%}.metric-card span{font-size:15px;color:#c0d6e9;order:0}.metric-card strong{font:700 43px/1 "Arial Narrow",Arial;color:#f6fbff;margin:8px 0 0;letter-spacing:1px;order:1;text-shadow:0 0 10px rgba(255,255,255,.1)}.metric-card em{display:none}
.grid{grid-template-columns:1.12fr 1fr 1.02fr;grid-template-rows:minmax(278px,1.08fr) minmax(250px,.98fr);gap:10px;flex:1;min-height:0}.panel{padding:15px 17px 12px;border-radius:5px;border:1px solid rgba(59,148,204,.38);background:linear-gradient(145deg,rgba(9,33,56,.97),rgba(4,22,39,.91));box-shadow:inset 0 1px rgba(167,220,255,.035),0 8px 24px rgba(0,0,0,.12)}.panel:before{content:"";position:absolute;inset:0;pointer-events:none;background:linear-gradient(135deg,rgba(32,123,185,.05),transparent 40%)}.panel:after{display:none}
.panel-title{height:42px;padding:0 0 10px;display:flex;align-items:center;justify-content:flex-start;gap:10px;border-bottom:1px solid rgba(72,141,185,.17)}.panel-title h2{font-size:18px;line-height:1;font-weight:700;letter-spacing:1px;color:#e7f2ff}.panel-title .title-icon{width:22px;color:#329cff;font:700 24px/1 Arial;font-style:normal;text-align:center;text-shadow:0 0 8px rgba(41,148,255,.45)}.panel-title .title-icon.trend{border-left:5px solid #31beff;width:6px;height:24px;font-size:0;box-shadow:0 0 8px rgba(49,190,255,.38)}
:deep(.panel-title .title-icon.trend){overflow:hidden;color:transparent;border-left:5px solid #31beff;width:6px;height:24px;font-size:0;box-shadow:0 0 8px rgba(49,190,255,.38)}
.legend{right:19px;top:21px;font-size:11px;color:#afc7d8;gap:18px}.legend i{width:18px}.trend{height:auto;flex:1;margin:1px 0 0}.lines line{stroke:rgba(84,145,185,.18);stroke-width:1}.axis-labels text{fill:#9aafbf;font-size:10px;text-anchor:end}.line{stroke-width:1.8}.visit{stroke:#37c7ff;filter:drop-shadow(0 0 2px rgba(55,199,255,.45))}.user{stroke:#5ccdf7;stroke-dasharray:5 4}.trend circle{fill:#dffaff;stroke:#2bbcff;stroke-width:2}.trend text{fill:#aabccc;font-size:10px}
.gauge-row{height:calc(100% - 74px);min-height:138px;padding:11px 0 2px;gap:8px;align-items:start}.gauge-item{text-align:center;min-width:0}.mini-gauge{width:min(103px,92%);background:radial-gradient(circle,#07192b 57%,transparent 59%),conic-gradient(var(--gauge-color) var(--gauge),#0b3c62 0);filter:drop-shadow(0 0 8px rgba(34,176,238,.10))}.mini-gauge:after{content:"";position:absolute;width:76%;height:76%;border-radius:50%;border:1px solid rgba(34,157,218,.13)}.mini-gauge>div{position:relative;z-index:1}.mini-gauge strong{font-size:21px}.mini-gauge small{font-size:9px;color:#a7bbca}.mini-gauge.health{--gauge-color:#ff687a}.gauge-item>span{display:block;margin-top:8px;font-size:13px;color:#ecf5ff;white-space:nowrap}.gauge-item>em{display:block;margin-top:7px;font-size:10px;font-style:normal;color:#9db4c5;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.gauge-item>em i{display:inline-block;width:7px;height:7px;margin-right:7px;border-radius:50%;background:#39d77c;box-shadow:0 0 7px #2fd372}
.service-summary{position:absolute;left:17px;right:17px;bottom:0;height:36px;border-top:1px solid rgba(54,127,174,.16);display:flex;align-items:center;justify-content:center;font-size:12px;color:#b8cedd}.shield-mini{margin-right:10px;color:#269cff;font-size:19px}
.hourly-panel{position:relative}.chart-grid{position:absolute;z-index:0;left:17px;right:17px;top:60px;bottom:27px;display:flex;flex-direction:column;justify-content:space-between}.chart-grid:after{content:"";position:absolute;left:34px;right:0;top:2px;bottom:4px;background:repeating-linear-gradient(to bottom,rgba(83,145,184,.18) 0 1px,transparent 1px calc(16.66%));border-bottom:1px solid rgba(94,153,188,.3)}.chart-grid span{font-size:9px;color:#9ab0c1;height:1px}.bars{z-index:1;position:relative;height:auto;flex:1;margin-left:30px;padding:16px 0 0;gap:4px}.bar-wrap{padding-bottom:19px}.bar{width:66%;background:linear-gradient(180deg,#31dcf5 0,#25b6ef 22%,#1475d7 70%,#0c58ba 100%);box-shadow:0 0 8px rgba(35,186,239,.25)}.bar-wrap span{color:#9bb0bf;font-size:9px}
.ranking,.dept-list,.live-list{position:relative}.ranking{padding:7px 5px 0;height:calc(100% - 42px);grid-template-rows:repeat(6,1fr)}.ranking>div{grid-template-columns:35px minmax(115px,.95fr) minmax(80px,1.55fr) 42px;gap:9px;min-height:25px;font-size:12px}.ranking em{font:700 17px "Arial Narrow",Arial;color:#319eff}.ranking span{line-height:1.2;color:#d4e4ee}.ranking div>div,.dept-list div>div{height:10px;background:#102f4d}.ranking div>div i,.dept-list div>div i{background:linear-gradient(90deg,#0a70d9,#43d7f1);box-shadow:0 0 6px rgba(36,170,236,.18)}.ranking b{font-size:13px;color:#7fd8ff}
.dept-head{height:27px;display:grid;grid-template-columns:1fr 65px 70px;align-items:end;font-size:10px;color:#718da2;padding:0 5px 4px}.dept-head b,.dept-head em{text-align:right;font-weight:400;font-style:normal}.dept-list{height:calc(100% - 69px);padding:0 5px}.dept-list>div{grid-template-columns:minmax(90px,.9fr) minmax(90px,1.5fr) 65px 70px;gap:9px;min-height:26px;font-size:11px}.dept-list span{color:#d3e5ef}.dept-list b{font-size:11px;text-align:right;color:#d7e9f4}.dept-list em{font-size:11px;color:#c5d9e5}
.live-list{height:calc(100% - 42px);padding-top:5px}.live-list>div{grid-template-columns:64px 15px minmax(130px,1fr) 98px;height:auto;min-height:26px;font-size:11px;border-bottom:1px solid rgba(61,125,168,.11)}.live-list time{font-size:11px;color:#7e9aad}.live-list i{width:9px;height:9px;background:#35d375;box-shadow:0 0 6px rgba(53,211,117,.42)}.live-list i.warning{background:#ffad13;box-shadow:0 0 6px rgba(255,173,19,.42)}.live-list span{color:#c2d6e2}.live-list span b{font-weight:400;color:#c2d6e2}.live-list em{color:#718da2}
footer{height:47px;min-height:47px;align-items:center}.screen footer>span{height:1px;flex:1;background:linear-gradient(90deg,transparent,rgba(35,125,185,.38))}.screen footer>span:last-child{transform:scaleX(-1)}footer b{margin:0 27px;font-size:12px;color:#94b2c7;letter-spacing:.5px}footer b i{font-size:19px;font-style:normal;color:#259cff;margin-right:8px}.error-state button{cursor:pointer;border-radius:2px}
@media(max-height:900px){.topbar{height:88px;min-height:88px}.industrial-bg{height:88px}.brand h1{font-size:30px}.brand p{margin-top:7px}.mark{width:82px;height:64px}.metrics{height:96px;margin:10px 0}.metric-card{height:96px}.metric-icon{width:62px;height:62px;min-width:62px}.metric-card strong{font-size:36px}.grid{grid-template-rows:minmax(255px,1.08fr) minmax(226px,.98fr)}footer{height:34px;min-height:34px}.gauge-item>span{margin-top:5px}.gauge-item>em{margin-top:4px}.mini-gauge{width:min(86px,92%)}.service-summary{height:30px}}
@media(max-width:1450px){.platform-title{width:380px;font-size:14px;letter-spacing:2px}.brand h1{font-size:27px;letter-spacing:4px}.headline span{display:none}.headline b{font-size:23px}.metric-card{gap:16px}.metric-icon{width:58px;height:58px;min-width:58px}.metric-card strong{font-size:35px}.grid{grid-template-columns:1.12fr 1.05fr 1fr}.panel-title h2{font-size:16px}}
@media(max-width:1200px){.screen{height:auto;min-height:100vh;padding-bottom:20px}.platform-title{display:none}.grid{grid-template-columns:1fr 1fr}.health-panel{grid-column:auto}.hourly-panel{grid-column:auto}.panel{min-height:280px}.metrics{height:auto}.metric-card{height:96px}footer{display:none}}
</style>
