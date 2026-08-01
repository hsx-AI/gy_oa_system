# -*- coding: utf-8 -*-
"""系统访问情况看板：记录前端页面访问并提供管理员聚合数据。"""
from datetime import datetime, timedelta
import os
import platform
import shutil
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from database import db
from routers.health_monitor import (
    _check_database, _check_server_resources, _get_cpu_percent, _get_memory_usage,
)

router = APIRouter(prefix="/access-dashboard", tags=["系统访问看板"])

class VisitEvent(BaseModel):
    user_name: str
    department: str = ""
    path: str
    title: str = ""

def ensure_access_log_table():
    db.execute_update("""CREATE TABLE IF NOT EXISTS system_access_log (
      id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
      user_name VARCHAR(80) NOT NULL, department VARCHAR(120) NOT NULL DEFAULT '',
      page_path VARCHAR(255) NOT NULL, page_title VARCHAR(120) NOT NULL DEFAULT '',
      ip_address VARCHAR(64) NOT NULL DEFAULT '', visited_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      INDEX idx_access_time (visited_at), INDEX idx_access_user_time (user_name, visited_at),
      INDEX idx_access_path_time (page_path, visited_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")

@router.post("/track")
async def track_visit(event: VisitEvent, request: Request):
    name, path = event.user_name.strip()[:80], event.path.strip()[:255]
    if not name or not path or path == "/login": return {"success": True}
    ensure_access_log_table()
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    ip = forwarded or (request.client.host if request.client else "")
    db.execute_update("INSERT INTO system_access_log (user_name,department,page_path,page_title,ip_address) VALUES (%s,%s,%s,%s,%s)",
      (name, event.department.strip()[:120], path, event.title.strip()[:120], ip[:64]))
    return {"success": True}

def rows(sql, params=None): return db.execute_query(sql, params) or []

@router.get("/overview")
async def access_overview(current_user: str = Query(default="")):
    ensure_access_log_table()
    now = datetime.now(); start_day = (now - timedelta(days=6)).strftime("%Y-%m-%d")
    summary = (rows("""SELECT COUNT(*) visits, COUNT(DISTINCT user_name) unique_users,
      COUNT(DISTINCT CASE WHEN visited_at >= NOW()-INTERVAL 15 MINUTE THEN user_name END) active_users
      FROM system_access_log WHERE visited_at >= CURDATE()""") or [{}])[0]
    summary["total_users"] = (rows("SELECT COUNT(*) total FROM yggl WHERE COALESCE(zaizhi,0)=0") or [{}])[0].get("total",0)
    raw = rows("""SELECT DATE_FORMAT(visited_at,'%%Y-%%m-%%d') day, COUNT(*) visits, COUNT(DISTINCT user_name) users
      FROM system_access_log WHERE visited_at >= %s GROUP BY DATE(visited_at) ORDER BY day""", (start_day,))
    by_day = {str(r['day']):r for r in raw}; daily=[]
    for i in range(7):
        d=(now-timedelta(days=6-i)).strftime('%Y-%m-%d'); v=by_day.get(d,{})
        daily.append({'day':d,'visits':v.get('visits',0),'users':v.get('users',0)})
    raw=rows("SELECT HOUR(visited_at) hour, COUNT(*) visits FROM system_access_log WHERE visited_at>=CURDATE() GROUP BY HOUR(visited_at)")
    by_hour={int(r['hour']):r['visits'] for r in raw}; hourly=[{'hour':h,'visits':by_hour.get(h,0)} for h in range(24)]
    pages=rows("""SELECT page_path path, MAX(page_title) title, COUNT(*) visits, COUNT(DISTINCT user_name) users
      FROM system_access_log WHERE visited_at>=CURDATE() GROUP BY page_path ORDER BY visits DESC LIMIT 8""")
    departments=rows("""SELECT IF(department='','未归属',department) department, COUNT(DISTINCT user_name) users, COUNT(*) visits
      FROM system_access_log WHERE visited_at>=CURDATE() GROUP BY department ORDER BY visits DESC LIMIT 8""")
    recent=rows("""SELECT user_name,department,page_path path,page_title title,DATE_FORMAT(visited_at,'%%H:%%i:%%s') time
      FROM system_access_log ORDER BY visited_at DESC LIMIT 12""")
    db_health, resources = await _check_database(), await _check_server_resources()
    hardware = {"available": False, "cpu": None, "memory": None, "disk": None}
    if platform.system() == "Linux":
        cpu = await _get_cpu_percent()
        memory = _get_memory_usage()
        disk = shutil.disk_usage("/")
        hardware = {
            "available": True,
            "cpu": cpu,
            "memory": memory.get("percent") if memory else None,
            "disk": round(disk.used / disk.total * 100, 1) if disk.total else None,
            "cpu_cores": os.cpu_count() or 1,
            "memory_used_gb": round(memory["used"] / 1024**3, 1) if memory else None,
            "memory_total_gb": round(memory["total"] / 1024**3, 1) if memory else None,
            "disk_used_gb": round(disk.used / 1024**3, 1),
            "disk_total_gb": round(disk.total / 1024**3, 1),
        }
    return {'success':True,'generated_at':now.strftime('%Y-%m-%d %H:%M:%S'),'summary':summary,'daily':daily,'hourly':hourly,
      'pages':pages,'departments':departments,'recent':recent,'hardware':hardware,'services':[
        {'name':'OA 应用服务','status':'ok','message':'运行正常'}, {'name':'业务数据库',**db_health}, {'name':'服务器资源',**resources}]}
