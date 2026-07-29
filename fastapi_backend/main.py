# -*- coding: utf-8 -*-
"""
考勤系统 FastAPI 后端
主应用文件
"""
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from routers.business_trip_map import router as map_router
from config import settings
from routers import holiday, suggestions, auth, attendance, report, leave_overtime, approvers, business_trip, approval, statistics, file_numbering, department_policy, admin, db_manager, health_monitor, sso, email_sender, shift_schedule, holiday_exchange, tech_problem, bid_template, inbox_email, feedback, contacts, seal_apply, confidentiality_ledger, attendance_exception, rotor_blade_balance, personnel_visualization, info_feed, ai_assistant, massage_chair, low_value_reimbursement, performance, action_items
import logging
import time

# 配置日志
log_level = logging.DEBUG if settings.DEBUG else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="考勤系统现代化API接口"
)


class RequestLogMiddleware(BaseHTTPMiddleware):
    """请求日志中间件：每个请求/响应在控制台打一行"""
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        try:
            response = await call_next(request)
            elapsed = (time.time() - start) * 1000
            log_msg = f"{request.method} {request.url.path} -> {response.status_code} ({elapsed:.0f} ms)"
            logger.info(log_msg)
            print(f"[Request] {log_msg}") # 强制输出到控制台
            return response
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            print(f"[Error] Request failed: {str(e)}")
            raise e


app.add_middleware(RequestLogMiddleware)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# 注册路由
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(attendance.router, prefix=settings.API_PREFIX)  # 新的考勤数据管理路由
app.include_router(holiday.router, prefix=settings.API_PREFIX)
app.include_router(suggestions.router, prefix=settings.API_PREFIX)
app.include_router(report.router, prefix=settings.API_PREFIX)  # 加班/请假统计路由
app.include_router(leave_overtime.router, prefix=settings.API_PREFIX)  # 请假申请/加班登记
app.include_router(approvers.router, prefix=settings.API_PREFIX)  # 审批人规则
app.include_router(business_trip.router, prefix=settings.API_PREFIX)  # 公出登记
app.include_router(approval.router, prefix=settings.API_PREFIX)  # 审批
app.include_router(statistics.router, prefix=settings.API_PREFIX)  # 统计
app.include_router(file_numbering.router, prefix=settings.API_PREFIX)
app.include_router(department_policy.router, prefix=settings.API_PREFIX)
app.include_router(admin.router, prefix=settings.API_PREFIX)  # 员工在职管理
app.include_router(db_manager.router, prefix=settings.API_PREFIX)
app.include_router(health_monitor.router, prefix=settings.API_PREFIX)  # 系统管理员页面（仅 admin1）
app.include_router(sso.router, prefix=settings.API_PREFIX)  # 系统管理员-数据库表增删改查
app.include_router(email_sender.router, prefix=settings.API_PREFIX)  # 邮件发送（仅 admin1）
app.include_router(shift_schedule.router, prefix=settings.API_PREFIX)  # 排班管理
app.include_router(holiday_exchange.router, prefix=settings.API_PREFIX)  # 公出节假日换休票
app.include_router(map_router, prefix=settings.API_PREFIX)  # 公出地图
app.include_router(tech_problem.router, prefix=settings.API_PREFIX)  # 工艺技术问题手册
app.include_router(inbox_email.router, prefix=settings.API_PREFIX)  # 共用邮箱收件箱（仅 admin1）
app.include_router(feedback.router, prefix=settings.API_PREFIX)  # 意见与建议
app.include_router(contacts.router, prefix=settings.API_PREFIX)  # 部门通讯录
app.include_router(seal_apply.router, prefix=settings.API_PREFIX)  # 部门用印申请
app.include_router(confidentiality_ledger.router, prefix=settings.API_PREFIX)  # 论文保密审批台账
app.include_router(bid_template.router, prefix=settings.API_PREFIX)  # 工艺投标模板库
app.include_router(attendance_exception.router, prefix=settings.API_PREFIX)  # 打卡异常申请
app.include_router(rotor_blade_balance.router, prefix=settings.API_PREFIX)  # 转轮叶片配重计算结果追溯
app.include_router(personnel_visualization.router, prefix=settings.API_PREFIX)  # 人员出勤可视化
app.include_router(info_feed.router, prefix=settings.API_PREFIX)  # 天气新闻中转缓存
app.include_router(ai_assistant.router, prefix=settings.API_PREFIX)  # 智能制造工艺部 AI 助手
app.include_router(massage_chair.router, prefix=settings.API_PREFIX)  # 休闲角预约
app.include_router(low_value_reimbursement.router, prefix=settings.API_PREFIX)  # 低值易耗报销
app.include_router(performance.router, prefix=settings.API_PREFIX)  # 月度绩效
app.include_router(action_items.router, prefix=settings.API_PREFIX)  # 行动项督办

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    msg = f"系统启动成功! 当前环境: {'DEBUG' if settings.DEBUG else 'PROD'}"
    logger.info(msg)
    print(f"[System] {msg}")
    print(f"[System] API文档地址: http://localhost:8000/docs")
    logger.info(f"API文档地址: http://localhost:8000/docs")
    logger.debug("调试日志已开启，将显示详细调试信息")
    # 定时从打卡服务器拉取报表并上传（时间与建议截止日见 webconfig / 系统管理员页）
    from routers.attendance_scheduler_config import init_attendance_fetch_scheduler
    init_attendance_fetch_scheduler()
    # 考勤异常提醒自动发送后台任务
    import asyncio as _asyncio
    from routers.email_sender import auto_reminder_background_loop, todo_reminder_background_loop, shift_schedule_email_background_loop, shift_holiday_email_background_loop
    _asyncio.get_event_loop().create_task(auto_reminder_background_loop())
    _asyncio.get_event_loop().create_task(todo_reminder_background_loop())
    _asyncio.get_event_loop().create_task(shift_schedule_email_background_loop())
    _asyncio.get_event_loop().create_task(shift_holiday_email_background_loop())
    # 共用邮箱自动拉取后台任务
    from routers.inbox_email import inbox_email_background_loop, inbox_email_analysis_background_loop
    _asyncio.get_event_loop().create_task(inbox_email_background_loop())
    # 共用邮箱任务抽取后台任务
    _asyncio.get_event_loop().create_task(inbox_email_analysis_background_loop())
    # 行动项临期、逾期和长期未更新提醒
    from routers.action_items import action_reminder_background_loop
    _asyncio.get_event_loop().create_task(action_reminder_background_loop())


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "考勤系统API服务",
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
        log_level="info",
        access_log=True,
    )
