# -*- coding: utf-8 -*-
"""
考勤系统 FastAPI 后端
主应用文件
"""
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from config import settings
from routers import holiday, suggestions, auth, attendance, report, leave_overtime, approvers, business_trip, approval, statistics, file_numbering, department_policy, admin, db_manager, sso
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
app.include_router(sso.router, prefix=settings.API_PREFIX)  # 系统管理员-数据库表增删改查


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    msg = f"系统启动成功! 当前环境: {'DEBUG' if settings.DEBUG else 'PROD'}"
    logger.info(msg)
    print(f"[System] {msg}")
    print(f"[System] API文档地址: http://localhost:8000/docs")
    logger.info(f"API文档地址: http://localhost:8000/docs")
    logger.debug("调试日志已开启，将显示详细调试信息")


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
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
        access_log=True,
    )

