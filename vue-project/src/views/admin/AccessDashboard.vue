<template>
  <main class="screen">
    <div class="ambient a1"></div><div class="ambient a2"></div>
    <header class="topbar">
      <div class="brand"><span class="mark">OA</span><div><h1>系统访问情况组态看板</h1><p>INTELLIGENT MANUFACTURING · OPERATION CENTER</p></div></div>
      <div class="headline"><i></i><span>数据实时监测中</span><b>{{ clock }}</b><small>{{ dateText }}</small></div>
    </header>

    <section v-if="error" class="error-state"><h2>数据连接暂时中断</h2><p>{{ error }}</p><button @click="load">重新连接</button></section>
    <template v-else>
      <section class="metrics">
        <article v-for="card in metricCards" :key="card.label" class="metric-card">
          <div class="metric-icon" v-html="card.icon"></div><div><span>{{ card.label }}</span><strong>{{ fmt(card.value) }}</strong><em>{{ card.note }}</em></div>
        </article>
      </section>

      <section class="grid">
        <article class="panel trend-panel">
          <PanelTitle title="近 7 日访问趋势" sub="DAILY ACCESS TREND" />
          <div class="legend"><span><i class="cyan"></i>访问次数</span><span><i class="blue"></i>访问人数</span></div>
          <svg class="trend" viewBox="0 0 720 220" preserveAspectRatio="none">
            <defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#22d3ee" stop-opacity=".42"/><stop offset="1" stop-color="#22d3ee" stop-opacity="0"/></linearGradient></defs>
            <g class="lines"><line v-for="n in 5" :key="n" x1="28" :y1="n*36" x2="705" :y2="n*36"/></g>
            <path :d="areaPath" fill="url(#area)"/><polyline :points="visitPoints" class="line visit"/><polyline :points="userPoints" class="line user"/>
            <g v-for="(d,i) in data.daily" :key="d.day"><circle :cx="x(i, data.daily.length)" :cy="y(d.visits, dailyMax)" r="3.5"/><text :x="x(i,data.daily.length)" y="214">{{ d.day.slice(5) }}</text></g>
          </svg>
        </article>

        <article class="panel health-panel">
          <PanelTitle title="核心服务状态" sub="SERVICE HEALTH" />
          <div class="gauge-row">
            <div class="mini-gauge health" :style="gaugeStyle(healthScore)"><div><strong>{{ healthScore }}</strong><small>健康指数</small></div></div>
            <div class="mini-gauge" :style="gaugeStyle(data.hardware?.cpu)"><div><strong>{{ gaugeValue(data.hardware?.cpu) }}</strong><small>CPU · {{ data.hardware?.cpu_cores || '--' }} 核</small></div></div>
            <div class="mini-gauge" :style="gaugeStyle(data.hardware?.memory)"><div><strong>{{ gaugeValue(data.hardware?.memory) }}</strong><small>内存 · {{ capacity(data.hardware?.memory_used_gb, data.hardware?.memory_total_gb) }}</small></div></div>
            <div class="mini-gauge" :style="gaugeStyle(data.hardware?.disk)"><div><strong>{{ gaugeValue(data.hardware?.disk) }}</strong><small>磁盘 · {{ capacity(data.hardware?.disk_used_gb, data.hardware?.disk_total_gb) }}</small></div></div>
          </div>
          <div class="services"><div v-for="s in data.services" :key="s.name"><i :class="s.status"></i><span>{{ s.name }}</span><b>{{ statusLabel(s.status) }}</b></div></div>
        </article>

        <article class="panel hourly-panel">
          <PanelTitle title="今日访问时段分布" sub="HOURLY DISTRIBUTION" />
          <div class="bars"><div v-for="h in data.hourly" :key="h.hour" class="bar-wrap" :title="`${h.hour}:00 · ${h.visits} 次`"><div class="bar" :style="{height: Math.max(3,h.visits/hourMax*100)+'%'}"></div><span v-if="h.hour%3===0">{{ pad(h.hour) }}</span></div></div>
        </article>

        <article class="panel pages-panel">
          <PanelTitle title="热门功能排行" sub="TOP MODULES" />
          <div class="ranking"><div v-for="(p,i) in data.pages.slice(0,6)" :key="p.path" :title="displayPageTitle(p)"><em>{{ pad(i+1) }}</em><span>{{ displayPageTitle(p) }}</span><div><i :style="{width:(p.visits/pageMax*100)+'%'}"></i></div><b>{{ p.visits }}</b></div><p v-if="!data.pages.length" class="empty">今日暂无访问记录</p></div>
        </article>

        <article class="panel dept-panel">
          <PanelTitle title="科室活跃度" sub="DEPARTMENT ACTIVITY" />
          <div class="dept-list"><div v-for="d in data.departments.slice(0,6)" :key="d.department"><span>{{ d.department }}</span><div><i :style="{width:(d.visits/deptMax*100)+'%'}"></i></div><b>{{ d.users }} 人</b><em>{{ d.visits }} 次</em></div><p v-if="!data.departments.length" class="empty">等待访问数据沉淀</p></div>
        </article>

        <article class="panel live-panel">
          <PanelTitle title="实时访问动态" sub="LIVE ACCESS FEED" />
          <div class="live-list"><div v-for="(r,i) in data.recent.slice(0,7)" :key="i"><time>{{ r.time }}</time><i></i><span><b>{{ mask(r.user_name) }}</b> 访问了 {{ displayPageTitle(r) }}</span><em>{{ r.department || '未归属' }}</em></div><p v-if="!data.recent.length" class="empty">新的访问将实时显示在这里</p></div>
        </article>
      </section>
    </template>
    <footer><span>数据范围：系统页面访问事件 · 在线口径：近 15 分钟</span><b>每 30 秒自动刷新</b><span>按 F11 进入浏览器全屏展示</span></footer>
  </main>
</template>

<script setup>
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref } from 'vue'
import { getAccessDashboard } from '@/api/accessDashboard'
const PanelTitle=defineComponent({props:['title','sub'],setup:p=>()=>h('div',{class:'panel-title'},[h('div',[h('h2',p.title),h('small',p.sub)]),h('span')])})
const data=ref({summary:{},daily:[],hourly:[],pages:[],departments:[],recent:[],services:[],hardware:{}}); const error=ref(''); const now=ref(new Date()); let refreshTimer,clockTimer
const userName=()=>{try{const u=JSON.parse(localStorage.getItem('userInfo')||'{}');return (u.name||u.userName||'').trim()}catch{return ''}}
async function load(){try{error.value='';data.value=await getAccessDashboard({current_user:userName()})}catch(e){error.value=e?.response?.data?.detail||e.message||'无法获取看板数据'}}
const clock=computed(()=>now.value.toLocaleTimeString('zh-CN',{hour12:false})); const dateText=computed(()=>now.value.toLocaleDateString('zh-CN',{year:'numeric',month:'2-digit',day:'2-digit',weekday:'short'}))
const generatedTime=computed(()=>(data.value.generated_at||'--').slice(11)); const fmt=v=>Number(v||0).toLocaleString('zh-CN'); const pad=v=>String(v).padStart(2,'0')
const metricCards=computed(()=>[{label:'今日访问次数',value:data.value.summary.visits,note:'累计页面浏览量',icon:'↗'},{label:'今日访问人数',value:data.value.summary.unique_users,note:'独立登录用户',icon:'◉'},{label:'当前活跃用户',value:data.value.summary.active_users,note:'近 15 分钟',icon:'⌁'},{label:'系统在册用户',value:data.value.summary.total_users,note:'当前在职人员',icon:'◇'}])
const dailyMax=computed(()=>Math.max(5,...data.value.daily.map(d=>+d.visits))); const hourMax=computed(()=>Math.max(1,...data.value.hourly.map(d=>+d.visits))); const pageMax=computed(()=>Math.max(1,...data.value.pages.map(d=>+d.visits))); const deptMax=computed(()=>Math.max(1,...data.value.departments.map(d=>+d.visits)))
const x=(i,n)=>28+i*(677/Math.max(1,n-1)); const y=(v,max)=>190-(+v/max)*155
const visitPoints=computed(()=>data.value.daily.map((d,i)=>`${x(i,data.value.daily.length)},${y(d.visits,dailyMax.value)}`).join(' ')); const userPoints=computed(()=>data.value.daily.map((d,i)=>`${x(i,data.value.daily.length)},${y(d.users,dailyMax.value)}`).join(' ')); const areaPath=computed(()=>data.value.daily.length?`M ${visitPoints.value.replaceAll(' ',' L ')} L 705 190 L 28 190 Z`:'')
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
  '/admin/hxp-records':'换休票明细查询','/feedback':'意见与建议','/contacts':'部门通讯录',
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
.panel{padding:12px 15px;min-height:0}.trend{height:calc(100% - 42px)}
.gauge-row{height:130px;display:grid;grid-template-columns:repeat(4,1fr);gap:8px;align-items:center;padding:5px 0}
.mini-gauge{--gauge:0deg;--gauge-color:#22d3ee;width:min(86px,100%);aspect-ratio:1;border-radius:50%;display:grid;place-items:center;margin:auto;background:radial-gradient(circle,#071527 59%,transparent 61%),conic-gradient(var(--gauge-color) var(--gauge),rgba(40,91,122,.25) 0);filter:drop-shadow(0 0 8px rgba(34,211,238,.12))}
.mini-gauge>div{text-align:center;max-width:76px}.mini-gauge strong{display:block;font:700 17px Arial;color:#fff}.mini-gauge small{display:block;margin-top:3px;font-size:7px;line-height:1.25;color:#6f99b2;white-space:normal}.mini-gauge.health{--gauge-color:#34d399}
.services{grid-template-columns:repeat(3,1fr);gap:6px}.services div{height:27px;padding:0 8px}.services b{font-size:9px}
.bars{height:calc(100% - 38px);padding-bottom:18px}.bar-wrap{height:100%}
.ranking{display:grid;grid-template-rows:repeat(6,minmax(27px,1fr));height:calc(100% - 37px);padding-top:6px}
.ranking>div{grid-template-columns:25px minmax(145px,1.35fr) minmax(60px,.75fr) 35px;height:auto;min-height:27px}
.ranking span{overflow:visible;text-overflow:clip;white-space:normal;line-height:1.25;word-break:break-word}
.dept-list,.live-list{height:calc(100% - 37px);padding-top:6px;display:flex;flex-direction:column;justify-content:space-evenly}.dept-list>div,.live-list>div{min-height:25px;height:auto}
footer{height:24px;min-height:24px}
@media(max-height:850px){.brand p{display:none}.topbar{height:56px;min-height:56px}.mark{width:44px;height:44px}.metrics{margin:8px 0}.metric-card{height:76px}.metric-icon{width:42px;height:42px}.grid{grid-template-rows:minmax(235px,1.08fr) minmax(205px,.92fr)}.gauge-row{height:108px}.mini-gauge{width:min(72px,100%)}.services div{height:24px}}
@media(max-width:1200px){.screen{height:auto;min-height:100vh;overflow:auto}.grid{grid-template-columns:1.2fr 1fr;grid-template-rows:auto}.health-panel{grid-column:2}.hourly-panel{grid-column:1/-1}.metrics{grid-template-columns:repeat(2,1fr)}}
</style>
