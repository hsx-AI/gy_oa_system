# -*- coding: utf-8 -*-
"""3D打印委托管理：申请、串行审批、排期、批次、交付与统计。"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from config import settings
from database import db

router = APIRouter(prefix="/print3d", tags=["3D打印委托"])
ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = ROOT / settings.UPLOAD_DIR / "print3d"

STATUSES = {
    "DRAFT", "PENDING_FIRST_REVIEW", "RETURNED_BY_FIRST_REVIEW",
    "PENDING_TECH_REVIEW", "RETURNED_BY_TECH_REVIEW",
    "PENDING_LEADER_APPROVAL", "RETURNED_BY_LEADER", "REJECTED",
    "APPROVED_PENDING_SCHEDULE", "SCHEDULED", "PRINTING", "PAUSED",
    "PRINT_FAILED", "REPRINT_PENDING", "PRINT_COMPLETED",
    "PENDING_PICKUP", "COMPLETED", "CANCELLED",
}
RETURNED = {"RETURNED_BY_FIRST_REVIEW", "RETURNED_BY_TECH_REVIEW", "RETURNED_BY_LEADER"}
DEFAULT_MODEL_EXT = "stl,3mf,step,stp,obj,sldprt,sldasm,prt,asm,x_t,x_b,iges,igs,jt,catpart,catproduct,nx,ug"
DEFAULT_AUX_EXT = "zip,rar,7z,pdf,doc,docx,xls,xlsx,jpg,jpeg,png"


def _tables():
    statements = [
        """CREATE TABLE IF NOT EXISTS print3d_config (
          config_key VARCHAR(80) PRIMARY KEY, config_value TEXT, description VARCHAR(255) DEFAULT '',
          updated_by VARCHAR(80) DEFAULT '', updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS print3d_role_user (
          id INT AUTO_INCREMENT PRIMARY KEY, role_code VARCHAR(40) NOT NULL, user_name VARCHAR(80) NOT NULL,
          created_by VARCHAR(80) DEFAULT '', created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          UNIQUE KEY uk_role_user(role_code,user_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS print3d_printer (
          id INT AUTO_INCREMENT PRIMARY KEY, printer_code VARCHAR(40) NOT NULL UNIQUE, printer_name VARCHAR(100) NOT NULL,
          model VARCHAR(100) DEFAULT '拓竹 H2D', status VARCHAR(30) DEFAULT 'IDLE', enabled TINYINT DEFAULT 1,
          location VARCHAR(200) DEFAULT '', remark VARCHAR(500) DEFAULT '', updated_by VARCHAR(80) DEFAULT '',
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS print3d_request (
          id INT AUTO_INCREMENT PRIMARY KEY, request_no VARCHAR(30) UNIQUE, subject VARCHAR(200) NOT NULL,
          applicant VARCHAR(80) NOT NULL, applicant_gh VARCHAR(40) DEFAULT '', department VARCHAR(120) DEFAULT '',
          contact VARCHAR(100) DEFAULT '', expected_date DATE NULL, urgency VARCHAR(20) DEFAULT '普通', purpose VARCHAR(50) DEFAULT '',
          project_code VARCHAR(120) DEFAULT '', purpose_desc TEXT, confidentiality VARCHAR(30) DEFAULT '内部', remark TEXT,
          quantity INT DEFAULT 1, approximate_size VARCHAR(120) DEFAULT '', material VARCHAR(100) DEFAULT '', color VARCHAR(80) DEFAULT '',
          strength_requirement VARCHAR(200) DEFAULT '', surface_requirement VARCHAR(200) DEFAULT '', split_policy VARCHAR(30) DEFAULT '由智能室判断',
          need_model_help TINYINT DEFAULT 0, need_post_process TINYINT DEFAULT 0, special_requirement TEXT,
          rules_accepted TINYINT DEFAULT 0,
          status VARCHAR(40) NOT NULL DEFAULT 'DRAFT', return_to_status VARCHAR(40) DEFAULT '',
          first_reviewer VARCHAR(80) DEFAULT '', tech_reviewer VARCHAR(80) DEFAULT '', leader_approver VARCHAR(80) DEFAULT '',
          assignee VARCHAR(80) DEFAULT '', promise_date DATE NULL, progress INT DEFAULT 0,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP, submitted_at DATETIME NULL, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          closed_at DATETIME NULL, INDEX idx_p3d_applicant(applicant), INDEX idx_p3d_status(status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS print3d_attachment (
          id INT AUTO_INCREMENT PRIMARY KEY, request_id INT NOT NULL, category VARCHAR(20) NOT NULL,
          original_name VARCHAR(500) NOT NULL, stored_name VARCHAR(120) NOT NULL, relative_path VARCHAR(500) NOT NULL,
          file_size BIGINT NOT NULL, file_type VARCHAR(30) DEFAULT '', file_hash VARCHAR(64) NOT NULL,
          uploaded_by VARCHAR(80) NOT NULL, uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP, version_no INT DEFAULT 1,
          active TINYINT DEFAULT 1, INDEX idx_p3d_att_req(request_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS print3d_approval (
          id INT AUTO_INCREMENT PRIMARY KEY, request_id INT NOT NULL, stage VARCHAR(30) NOT NULL,
          action VARCHAR(30) NOT NULL, operator VARCHAR(80) NOT NULL, opinion TEXT, reason_tags TEXT,
          from_status VARCHAR(40), to_status VARCHAR(40), created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          INDEX idx_p3d_approval_req(request_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS print3d_batch (
          id INT AUTO_INCREMENT PRIMARY KEY, request_id INT NOT NULL, batch_no INT NOT NULL, printer_id INT NULL,
          operator VARCHAR(80) DEFAULT '', status VARCHAR(30) DEFAULT 'SCHEDULED', planned_start DATETIME NULL, planned_end DATETIME NULL,
          actual_start DATETIME NULL, actual_end DATETIME NULL, nozzle VARCHAR(30) DEFAULT '', layer_height VARCHAR(30) DEFAULT '',
          infill VARCHAR(30) DEFAULT '', wall VARCHAR(30) DEFAULT '', support_params VARCHAR(500) DEFAULT '', orientation VARCHAR(500) DEFAULT '',
          slicing_params TEXT, estimated_material VARCHAR(100) DEFAULT '', estimated_hours DECIMAL(10,2) NULL,
          actual_material VARCHAR(100) DEFAULT '', actual_hours DECIMAL(10,2) NULL, progress INT DEFAULT 0, note TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP, UNIQUE KEY uk_p3d_batch(request_id,batch_no)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS print3d_event (
          id INT AUTO_INCREMENT PRIMARY KEY, request_id INT NOT NULL, batch_id INT NULL, event_type VARCHAR(40) NOT NULL,
          operator VARCHAR(80) NOT NULL, detail TEXT, from_status VARCHAR(40), to_status VARCHAR(40),
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP, INDEX idx_p3d_event_req(request_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    ]
    for sql in statements:
        if db.execute_update(sql) < 0:
            raise HTTPException(500, "3D打印模块数据库初始化失败")
    has_rules = db.execute_scalar(
        "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() "
        "AND TABLE_NAME='print3d_request' AND COLUMN_NAME='rules_accepted'"
    )
    if not has_rules:
        db.execute_update("ALTER TABLE print3d_request ADD COLUMN rules_accepted TINYINT DEFAULT 0 AFTER special_requirement")
    defaults = {
        "monitor_url": "http://10.42.60.211:8080/", "model_extensions": DEFAULT_MODEL_EXT,
        "aux_extensions": DEFAULT_AUX_EXT, "max_file_mb": "500", "department": "智能制造技术室",
        "monitor_cam0": "http://10.42.60.211:8080/cam0/stream",
        "monitor_cam1": "http://10.42.60.211:8080/cam1/stream",
        "material_options": "PLA,PETG,TPU,ABS,ASA,PC,PA,PVA,PLA-CF,PETG-CF,PA-CF,由智能室判断",
        "color_options": "黑色,白色,灰色,红色,蓝色,绿色,黄色,透明,由智能室判断",
    }
    for k, v in defaults.items():
        db.execute_update("INSERT IGNORE INTO print3d_config(config_key,config_value) VALUES(%s,%s)", (k, v))
    for code, name in (("H2D-01", "拓竹 H2D 1号机"), ("H2D-02", "拓竹 H2D 2号机")):
        db.execute_update("INSERT IGNORE INTO print3d_printer(printer_code,printer_name) VALUES(%s,%s)", (code, name))


def _user(name: str) -> dict:
    name = (name or "").strip()
    rows = db.execute_query("SELECT name,gh,lsys,jb,enterprise_email FROM yggl WHERE name=%s AND COALESCE(zaizhi,0)=0 LIMIT 1", (name,))
    if not rows:
        raise HTTPException(401, "当前用户无效或已离职")
    return rows[0]


def _roles(name: str) -> set[str]:
    return {r["role_code"] for r in db.execute_query("SELECT role_code FROM print3d_role_user WHERE user_name=%s", (name,))}


def _is_admin(user: dict) -> bool:
    if "ADMIN" in _roles(user["name"]): return True
    v = db.execute_scalar("SELECT admin1 FROM webconfig WHERE id=1 LIMIT 1")
    return bool(v and str(v).strip() == user["name"])


def _request(request_id: int) -> dict:
    rows = db.execute_query("SELECT * FROM print3d_request WHERE id=%s LIMIT 1", (request_id,))
    if not rows: raise HTTPException(404, "委托单不存在")
    return rows[0]


def _can_view(row: dict, user: dict) -> bool:
    if row["applicant"] == user["name"] or _is_admin(user): return True
    roles = _roles(user["name"])
    return bool(roles & {"FIRST_REVIEWER","TECH_REVIEWER","LEADER","TASK_ADMIN"}) or user["name"] in {
        row.get("first_reviewer"), row.get("tech_reviewer"), row.get("leader_approver"), row.get("assignee")}


def _event(rid: int, operator: str, typ: str, detail="", old=None, new=None, batch_id=None):
    db.execute_insert("INSERT INTO print3d_event(request_id,batch_id,event_type,operator,detail,from_status,to_status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                      (rid,batch_id,typ,operator,detail,old,new))


def _transition(row: dict, operator: str, expected: set[str], target: str, typ: str, detail=""):
    if row["status"] not in expected: raise HTTPException(409, f"当前状态 {row['status']} 不允许此操作")
    changed = db.execute_update("UPDATE print3d_request SET status=%s WHERE id=%s AND status=%s", (target,row["id"],row["status"]))
    if changed != 1: raise HTTPException(409, "委托状态已变化，请刷新后重试")
    _event(row["id"],operator,typ,detail,row["status"],target)


class RequestSave(BaseModel):
    current_user: str
    id: Optional[int] = None
    subject: str = Field(min_length=1, max_length=200)
    contact: str = ""; expected_date: Optional[str] = None; urgency: str = "普通"; purpose: str = ""
    project_code: str = ""; purpose_desc: str = ""; confidentiality: str = "内部"; remark: str = ""
    quantity: int = Field(default=1, ge=1, le=10000); approximate_size: str = ""; material: str = ""; color: str = ""
    strength_requirement: str = ""; surface_requirement: str = ""; split_policy: str = "由智能室判断"
    need_model_help: bool = False; need_post_process: bool = False; special_requirement: str = ""
    rules_accepted: bool = False
    leader_approver: str = ""


class Action(BaseModel):
    current_user: str; action: str; opinion: str = ""; reason_tags: List[str] = []


class Schedule(BaseModel):
    current_user: str; assignee: str; printer_id: int; promise_date: str
    planned_start: Optional[str] = None; planned_end: Optional[str] = None; note: str = ""


class BatchUpdate(BaseModel):
    current_user: str; progress: Optional[int] = Field(default=None, ge=0, le=100); detail: str = ""
    nozzle: str = ""; layer_height: str = ""; infill: str = ""; wall: str = ""; support_params: str = ""
    orientation: str = ""; slicing_params: str = ""; estimated_material: str = ""; estimated_hours: Optional[float] = None


class Pickup(BaseModel): current_user: str; receiver: str = ""; note: str = ""
class ConfigSave(BaseModel): current_user: str; config: dict; roles: dict
class PrinterUpdate(BaseModel):
    current_user: str
    status: str
    location: str = ""
    remark: str = ""


@router.get("/bootstrap")
def bootstrap(current_user: str = Query(...)):
    _tables(); u = _user(current_user); rs = _roles(u["name"])
    cfg = {r["config_key"]: r["config_value"] for r in db.execute_query("SELECT config_key,config_value FROM print3d_config")}
    leaders = db.execute_query(
        "SELECT ru.user_name name,COALESCE(y.jb,'') title,COALESCE(y.lsys,'') department "
        "FROM print3d_role_user ru LEFT JOIN yggl y ON y.name=ru.user_name "
        "WHERE ru.role_code='LEADER' ORDER BY ru.user_name"
    )
    return {"success":True,"user":u,"roles":list(rs),"isAdmin":_is_admin(u),"config":cfg,
            "printers":db.execute_query("SELECT * FROM print3d_printer WHERE enabled=1 ORDER BY id"),
            "leaders": leaders}


@router.post("/requests")
def save_request(req: RequestSave):
    _tables(); u=_user(req.current_user); data=req.model_dump(); data.pop("current_user"); rid=data.pop("id")
    selected_leader = (data.get("leader_approver") or "").strip()
    if selected_leader:
        _user(selected_leader)
        if "LEADER" not in _roles(selected_leader):
            raise HTTPException(400, "所选人员不是已配置的审批领导")
    cols=list(data.keys()); vals=[int(v) if isinstance(v,bool) else v for v in data.values()]
    if rid:
        row=_request(rid)
        if row["applicant"] != u["name"] or row["status"] not in ({"DRAFT"}|RETURNED): raise HTTPException(403,"当前委托不可编辑")
        db.execute_update("UPDATE print3d_request SET "+",".join(f"{c}=%s" for c in cols)+" WHERE id=%s", tuple(vals+[rid]))
    else:
        rid=db.execute_insert("INSERT INTO print3d_request("+",".join(cols)+",applicant,applicant_gh,department) VALUES("+",".join(["%s"]*(len(cols)+3))+")",
                              tuple(vals+[u["name"],u.get("gh") or "",u.get("lsys") or ""]))
        no=f"3DP-{datetime.now():%Y%m}-{rid:04d}"; db.execute_update("UPDATE print3d_request SET request_no=%s WHERE id=%s",(no,rid)); _event(rid,u["name"],"CREATE","创建草稿")
    return {"success":True,"id":rid,"message":"草稿已保存"}


@router.post("/requests/{rid}/files")
async def upload_files(rid:int,current_user:str=Form(...),category:str=Form("MODEL"),files:List[UploadFile]=File(...)):
    _tables(); u=_user(current_user); row=_request(rid)
    if row["applicant"]!=u["name"] or row["status"] not in ({"DRAFT"}|RETURNED): raise HTTPException(403,"当前委托不可上传附件")
    cfg={r["config_key"]:r["config_value"] for r in db.execute_query("SELECT config_key,config_value FROM print3d_config")}
    allowed=set((cfg["model_extensions"] if category=="MODEL" else cfg["aux_extensions"]).lower().split(",")); limit=int(cfg["max_file_mb"])*1024*1024
    folder=UPLOAD_DIR/str(rid); folder.mkdir(parents=True,exist_ok=True); result=[]
    for f in files:
        ext=Path(f.filename or "").suffix.lower().lstrip(".")
        if ext not in allowed: raise HTTPException(400,f"不支持文件格式：{ext}")
        content=await f.read()
        if len(content)>limit: raise HTTPException(413,f"文件 {f.filename} 超过 {cfg['max_file_mb']}MB")
        stored=f"{uuid.uuid4().hex}.{ext}"; path=folder/stored; path.write_bytes(content)
        version=(db.execute_scalar("SELECT COALESCE(MAX(version_no),0)+1 FROM print3d_attachment WHERE request_id=%s AND original_name=%s",(rid,f.filename)) or 1)
        aid=db.execute_insert("INSERT INTO print3d_attachment(request_id,category,original_name,stored_name,relative_path,file_size,file_type,file_hash,uploaded_by,version_no) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (rid,category,f.filename,stored,str(path.relative_to(ROOT)),len(content),ext,hashlib.sha256(content).hexdigest(),u["name"],version)); result.append({"id":aid,"name":f.filename})
    _event(rid,u["name"],"UPLOAD",f"上传{len(result)}个文件")
    return {"success":True,"data":result}


@router.post("/requests/{rid}/submit")
def submit(rid:int, action:Action):
    u=_user(action.current_user); row=_request(rid)
    if row["applicant"]!=u["name"]: raise HTTPException(403,"仅委托人可提交")
    if not int(row.get("rules_accepted") or 0): raise HTTPException(400,"请先阅读并同意3D打印委托要求")
    if not (row.get("leader_approver") or "").strip(): raise HTTPException(400,"请选择审批领导")
    if "LEADER" not in _roles(row["leader_approver"]): raise HTTPException(400,"所选审批领导配置已失效，请重新选择")
    if not db.execute_scalar("SELECT COUNT(*) FROM print3d_attachment WHERE request_id=%s AND category='MODEL' AND active=1",(rid,)): raise HTTPException(400,"请至少上传一个模型文件")
    target={"RETURNED_BY_FIRST_REVIEW":"PENDING_FIRST_REVIEW","RETURNED_BY_TECH_REVIEW":"PENDING_TECH_REVIEW","RETURNED_BY_LEADER":"PENDING_LEADER_APPROVAL"}.get(row["status"],"PENDING_FIRST_REVIEW")
    _transition(row,u["name"],{"DRAFT"}|RETURNED,target,"SUBMIT","提交委托")
    db.execute_update("UPDATE print3d_request SET submitted_at=COALESCE(submitted_at,NOW()) WHERE id=%s",(rid,)); return {"success":True,"message":"委托已提交"}


@router.get("/requests")
def list_requests(current_user:str=Query(...),scope:str=Query("mine"),status:str=Query(""),keyword:str=Query("")):
    _tables(); u=_user(current_user); rs=_roles(u["name"]); where=[]; p=[]
    if scope=="mine": where.append("applicant=%s"); p.append(u["name"])
    elif scope=="todo":
        clauses=[]
        if "FIRST_REVIEWER" in rs: clauses.append("status='PENDING_FIRST_REVIEW'")
        if "TECH_REVIEWER" in rs: clauses.append("status='PENDING_TECH_REVIEW'")
        if "LEADER" in rs:
            clauses.append("(status='PENDING_LEADER_APPROVAL' AND leader_approver=%s)")
            p.append(u["name"])
        if "TASK_ADMIN" in rs: clauses.append("status IN ('APPROVED_PENDING_SCHEDULE','SCHEDULED','PRINTING','PAUSED','PRINT_FAILED','REPRINT_PENDING','PRINT_COMPLETED','PENDING_PICKUP')")
        where.append("("+" OR ".join(clauses or ["0"])+")")
    elif not (_is_admin(u) or rs & {"FIRST_REVIEWER","TECH_REVIEWER","LEADER","TASK_ADMIN"}): raise HTTPException(403,"无权查看全部委托")
    if status: where.append("status=%s"); p.append(status)
    if keyword: where.append("(request_no LIKE %s OR subject LIKE %s OR applicant LIKE %s)"); p += [f"%{keyword}%"]*3
    rows=db.execute_query("SELECT * FROM print3d_request WHERE "+(" AND ".join(where) if where else "1=1")+" ORDER BY created_at DESC LIMIT 500",tuple(p))
    return {"success":True,"data":rows}


@router.get("/requests/{rid}")
def detail(rid:int,current_user:str=Query(...)):
    u=_user(current_user); row=_request(rid)
    if not _can_view(row,u): raise HTTPException(403,"无权查看该委托")
    row["attachments"]=db.execute_query("SELECT id,category,original_name,file_size,file_type,file_hash,uploaded_by,uploaded_at,version_no FROM print3d_attachment WHERE request_id=%s AND active=1 ORDER BY id",(rid,))
    row["approvals"]=db.execute_query("SELECT * FROM print3d_approval WHERE request_id=%s ORDER BY id",(rid,)); row["batches"]=db.execute_query("SELECT b.*,p.printer_name FROM print3d_batch b LEFT JOIN print3d_printer p ON p.id=b.printer_id WHERE b.request_id=%s ORDER BY b.batch_no",(rid,)); row["events"]=db.execute_query("SELECT * FROM print3d_event WHERE request_id=%s ORDER BY id DESC",(rid,))
    return {"success":True,"data":row}


@router.post("/requests/{rid}/review/{stage}")
def review(rid:int,stage:str,action:Action):
    u=_user(action.current_user); row=_request(rid); roles=_roles(u["name"])
    spec={"first":("FIRST_REVIEWER","PENDING_FIRST_REVIEW","PENDING_TECH_REVIEW","RETURNED_BY_FIRST_REVIEW","first_reviewer"),"tech":("TECH_REVIEWER","PENDING_TECH_REVIEW","PENDING_LEADER_APPROVAL","RETURNED_BY_TECH_REVIEW","tech_reviewer"),"leader":("LEADER","PENDING_LEADER_APPROVAL","APPROVED_PENDING_SCHEDULE","RETURNED_BY_LEADER","leader_approver")}
    if stage not in spec: raise HTTPException(400,"无效审核环节")
    role,pending,passed,returned,col=spec[stage]
    if role not in roles: raise HTTPException(403,"无该环节审核权限")
    if stage=="leader" and (row.get("leader_approver") or "").strip()!=u["name"]:
        raise HTTPException(403,"仅委托人指定的审批领导可处理该委托")
    if stage=="tech" and row.get("first_reviewer")==u["name"]: raise HTTPException(409,"技术校核人员必须与一级审核人员不同")
    if action.action not in {"approve","return","reject"}: raise HTTPException(400,"无效审核动作")
    if action.action in {"return","reject"} and not (action.opinion.strip() or action.reason_tags): raise HTTPException(400,"退回或驳回必须填写原因")
    target=passed if action.action=="approve" else (returned if action.action=="return" else "REJECTED"); opinion="；".join(action.reason_tags+[action.opinion.strip()]).strip("；")
    _transition(row,u["name"],{pending},target,f"{stage.upper()}_{action.action.upper()}",opinion)
    db.execute_update(f"UPDATE print3d_request SET {col}=%s WHERE id=%s",(u["name"],rid)); db.execute_insert("INSERT INTO print3d_approval(request_id,stage,action,operator,opinion,reason_tags,from_status,to_status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",(rid,stage,action.action,u["name"],opinion,json.dumps(action.reason_tags,ensure_ascii=False),pending,target))
    return {"success":True,"message":"操作成功"}


@router.post("/requests/{rid}/schedule")
def schedule(rid:int,req:Schedule):
    u=_user(req.current_user); row=_request(rid)
    if "TASK_ADMIN" not in _roles(u["name"]): raise HTTPException(403,"无排期权限")
    _user(req.assignee); _transition(row,u["name"],{"APPROVED_PENDING_SCHEDULE"},"SCHEDULED","SCHEDULE",req.note)
    db.execute_update("UPDATE print3d_request SET assignee=%s,promise_date=%s WHERE id=%s",(req.assignee,req.promise_date,rid)); no=(db.execute_scalar("SELECT COALESCE(MAX(batch_no),0)+1 FROM print3d_batch WHERE request_id=%s",(rid,)) or 1)
    bid=db.execute_insert("INSERT INTO print3d_batch(request_id,batch_no,printer_id,operator,planned_start,planned_end,note) VALUES(%s,%s,%s,%s,%s,%s,%s)",(rid,no,req.printer_id,req.assignee,req.planned_start,req.planned_end,req.note)); return {"success":True,"batchId":bid}


@router.post("/requests/{rid}/print/{command}")
def print_command(rid:int,command:str,req:BatchUpdate):
    u=_user(req.current_user); row=_request(rid)
    if "TASK_ADMIN" not in _roles(u["name"]): raise HTTPException(403,"无打印任务管理权限")
    mapping={"start":({"SCHEDULED","REPRINT_PENDING"},"PRINTING"),"pause":({"PRINTING"},"PAUSED"),"resume":({"PAUSED"},"PRINTING"),"fail":({"PRINTING","PAUSED"},"PRINT_FAILED"),"complete":({"PRINTING"},"PRINT_COMPLETED"),"pickup-ready":({"PRINT_COMPLETED"},"PENDING_PICKUP")}
    if command not in mapping: raise HTTPException(400,"无效打印操作")
    expected,target=mapping[command]; _transition(row,u["name"],expected,target,"PRINT_"+command.upper(),req.detail)
    batch=db.execute_query("SELECT * FROM print3d_batch WHERE request_id=%s ORDER BY batch_no DESC LIMIT 1",(rid,)); bid=batch[0]["id"] if batch else None
    if bid:
        fields={"status":target,"progress":req.progress if req.progress is not None else (100 if command in {"complete","pickup-ready"} else batch[0].get("progress",0)),"nozzle":req.nozzle,"layer_height":req.layer_height,"infill":req.infill,"wall":req.wall,"support_params":req.support_params,"orientation":req.orientation,"slicing_params":req.slicing_params,"estimated_material":req.estimated_material,"estimated_hours":req.estimated_hours}
        extra=",actual_start=NOW()" if command=="start" else (",actual_end=NOW()" if command=="complete" else "")
        db.execute_update("UPDATE print3d_batch SET "+",".join(f"{k}=%s" for k in fields)+extra+" WHERE id=%s",tuple(fields.values())+(bid,))
    db.execute_update("UPDATE print3d_request SET progress=%s WHERE id=%s",(req.progress if req.progress is not None else (100 if command in {"complete","pickup-ready"} else row.get("progress",0)),rid)); return {"success":True,"message":"状态已更新"}


@router.post("/requests/{rid}/reprint")
def reprint(rid:int,req:BatchUpdate):
    u=_user(req.current_user); row=_request(rid)
    if "TASK_ADMIN" not in _roles(u["name"]): raise HTTPException(403,"无权限")
    _transition(row,u["name"],{"PRINT_FAILED"},"REPRINT_PENDING","REPRINT",req.detail); last=db.execute_query("SELECT * FROM print3d_batch WHERE request_id=%s ORDER BY batch_no DESC LIMIT 1",(rid,))[0]
    bid=db.execute_insert("INSERT INTO print3d_batch(request_id,batch_no,printer_id,operator,status,note) VALUES(%s,%s,%s,%s,'REPRINT_PENDING',%s)",(rid,last["batch_no"]+1,last["printer_id"],u["name"],req.detail)); return {"success":True,"batchId":bid}


@router.post("/requests/{rid}/pickup")
def pickup(rid:int,req:Pickup):
    u=_user(req.current_user); row=_request(rid); roles=_roles(u["name"])
    if row["applicant"]!=u["name"] and "TASK_ADMIN" not in roles: raise HTTPException(403,"仅委托人或任务管理员可登记领取")
    _transition(row,u["name"],{"PENDING_PICKUP"},"COMPLETED","PICKUP",req.note or f"领取人：{req.receiver or u['name']}"); db.execute_update("UPDATE print3d_request SET closed_at=NOW(),progress=100 WHERE id=%s",(rid,)); return {"success":True}


@router.post("/requests/{rid}/cancel")
def cancel(rid:int,req:Pickup):
    u=_user(req.current_user); row=_request(rid)
    if row["applicant"]!=u["name"] and not _is_admin(u): raise HTTPException(403,"无权撤回")
    _transition(row,u["name"],{"DRAFT","PENDING_FIRST_REVIEW","RETURNED_BY_FIRST_REVIEW","RETURNED_BY_TECH_REVIEW","RETURNED_BY_LEADER"},"CANCELLED","CANCEL",req.note); return {"success":True}


@router.get("/attachments/{aid}")
def download(aid:int,current_user:str=Query(...)):
    u=_user(current_user); rows=db.execute_query("SELECT a.* FROM print3d_attachment a WHERE a.id=%s AND a.active=1",(aid,))
    if not rows: raise HTTPException(404,"附件不存在")
    a=rows[0]; row=_request(a["request_id"])
    if not _can_view(row,u): raise HTTPException(403,"无权下载该附件")
    path=(ROOT/a["relative_path"]).resolve()
    if ROOT.resolve() not in path.parents or not path.is_file(): raise HTTPException(404,"文件不存在")
    return FileResponse(str(path),filename=a["original_name"],media_type="application/octet-stream")


@router.get("/todos")
def todos(current_user:str=Query(...)):
    data=list_requests(current_user,"todo")["data"]
    return {"success":True,"data":[{"id":r["id"],"requestNo":r["request_no"],"subject":r["subject"],"applicant":r["applicant"],"status":r["status"],"createdAt":r["created_at"]} for r in data]}


@router.get("/statistics")
def statistics(current_user:str=Query(...)):
    u=_user(current_user)
    if not (_is_admin(u) or _roles(u["name"]) & {"LEADER","TASK_ADMIN"}): raise HTTPException(403,"无统计权限")
    return {"success":True,"status":db.execute_query("SELECT status,COUNT(*) count FROM print3d_request GROUP BY status"),"monthly":db.execute_query("SELECT DATE_FORMAT(created_at,'%Y-%m') month,COUNT(*) count FROM print3d_request GROUP BY month ORDER BY month DESC LIMIT 12"),"printer":db.execute_query("SELECT p.printer_name,COUNT(b.id) batches,COALESCE(SUM(b.actual_hours),0) hours FROM print3d_printer p LEFT JOIN print3d_batch b ON b.printer_id=p.id GROUP BY p.id")}


@router.post("/printers/{printer_id}")
def update_printer(printer_id: int, req: PrinterUpdate):
    u = _user(req.current_user)
    if not (_is_admin(u) or "TASK_ADMIN" in _roles(u["name"])):
        raise HTTPException(403, "仅系统管理员或打印任务管理员可更新设备")
    allowed = {"IDLE", "SCHEDULED", "PRINTING", "PAUSED", "MAINTENANCE", "OFFLINE"}
    if req.status not in allowed:
        raise HTTPException(400, "无效设备状态")
    if db.execute_update("UPDATE print3d_printer SET status=%s,location=%s,remark=%s,updated_by=%s WHERE id=%s",
                         (req.status, req.location.strip(), req.remark.strip(), u["name"], printer_id)) != 1:
        raise HTTPException(404, "设备不存在")
    return {"success": True, "message": "设备状态已更新"}


@router.get("/admin/config")
def get_config(current_user:str=Query(...)):
    u=_user(current_user)
    if not _is_admin(u): raise HTTPException(403,"仅系统管理员可配置")
    return {"success":True,"config":{r["config_key"]:r["config_value"] for r in db.execute_query("SELECT config_key,config_value FROM print3d_config")},"roles":db.execute_query("SELECT role_code,user_name FROM print3d_role_user ORDER BY role_code,user_name")}


@router.post("/admin/config")
def save_config(req:ConfigSave):
    u=_user(req.current_user)
    if not _is_admin(u): raise HTTPException(403,"仅系统管理员可配置")
    for k,v in req.config.items(): db.execute_update("INSERT INTO print3d_config(config_key,config_value,updated_by) VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE config_value=VALUES(config_value),updated_by=VALUES(updated_by)",(k,str(v),u["name"]))
    db.execute_update("DELETE FROM print3d_role_user")
    for role,names in req.roles.items():
        for name in names:
            _user(name); db.execute_update("INSERT INTO print3d_role_user(role_code,user_name,created_by) VALUES(%s,%s,%s)",(role,name,u["name"]))
    return {"success":True,"message":"配置已保存"}
