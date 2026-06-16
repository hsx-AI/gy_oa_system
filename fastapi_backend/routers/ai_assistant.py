# -*- coding: utf-8 -*-
"""
智能制造工艺部 AI 助手
------------------------------------------------------------
基于系统现有的本地大模型（Ollama / OpenAI 兼容接口，配置见 webconfig.llm_base_url / llm_model），
整合系统数据库资源，提供带 skills（工具调用）的流式问答：
  - 制度/工艺智能检索（向量库 bge-small-zh）
  - 加班 / 请假 / 公出记录查询统计
  - 月度考勤汇总
  - 报表查询与下载（生成 Excel 下载链接，复用报表汇聚口径）

对话以 SSE (text/event-stream) 形式流式返回，事件类型：
  - {"type": "meta",  "model": "...", "base_url": "..."}
  - {"type": "tool",  "name": "...", "label": "...", "status": "running|done", "summary": "..."}
  - {"type": "attachment", "label": "...", "url": "...", "filename": "..."}
  - {"type": "chunk", "text": "增量 token"}
  - {"type": "done"}
  - {"type": "error", "message": "..."}
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from io import BytesIO
from urllib.parse import urlencode
import json
import logging

from database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-assistant", tags=["AI助手"])

# ==================== 本地大模型配置 ====================

DEFAULT_LLM_BASE_URL = "http://10.42.60.250:11434/v1"
DEFAULT_LLM_MODEL = "qwen3:8b"

# 工具调用最多迭代轮数，防止无限循环
MAX_TOOL_ROUNDS = 4


def _normalize_llm_base_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return u
    u = u.rstrip("/")
    if u.endswith("/chat/completions"):
        u = u[: -len("/chat/completions")].rstrip("/")
    return u


def _get_llm_config() -> dict:
    """从 webconfig 读取本地大模型配置（与假期/邮件解析共用同一套配置）。"""
    base_url = DEFAULT_LLM_BASE_URL
    model = DEFAULT_LLM_MODEL
    try:
        rows = db.execute_query(
            "SELECT llm_base_url, llm_model FROM webconfig WHERE id = %s LIMIT 1",
            ("1",),
        )
        if rows:
            r = rows[0]
            if (r.get("llm_base_url") or "").strip():
                base_url = (r["llm_base_url"] or "").strip()
            if (r.get("llm_model") or "").strip():
                model = (r["llm_model"] or "").strip()
    except Exception as e:
        logger.debug(f"读取 webconfig 大模型配置失败: {e}")
    return {"base_url": _normalize_llm_base_url(base_url), "model": model}


# ==================== 请求模型 ====================


class ChatMessage(BaseModel):
    role: str
    content: str = ""


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = []
    current_user: str = ""


# ==================== Skills（工具）实现 ====================


def _fmt_dt(d) -> str:
    if d is None:
        return ""
    if hasattr(d, "strftime"):
        try:
            return d.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return str(d)
    return str(d)[:16]


def _to_float(v) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def skill_search_policy(args: Dict[str, Any], current_user: str) -> Dict[str, Any]:
    """部门制度 / 工艺制度智能检索（向量库）。"""
    query = (args.get("query") or "").strip()
    top_k = int(args.get("top_k") or 5)
    top_k = max(1, min(10, top_k))
    if not query:
        return {"ok": False, "message": "缺少检索关键词 query"}
    try:
        from services.policy_vector import search
        hits = search(query, top_k=top_k)
    except Exception as e:
        logger.warning(f"制度向量检索失败: {e}")
        return {"ok": False, "message": f"制度检索服务不可用：{e}"}

    if not hits:
        return {"ok": True, "count": 0, "results": [], "message": "未检索到相关制度"}

    ids = [h[0] for h in hits]
    placeholders = ",".join(["%s"] * len(ids))
    meta = {}
    try:
        rows = db.execute_query(
            f"SELECT id, title, issue_time, remark FROM dept_policy WHERE id IN ({placeholders})",
            tuple(ids),
        )
        for r in rows:
            meta[str(r["id"])] = r
    except Exception as e:
        logger.debug(f"读取制度标题失败: {e}")

    results = []
    for pid, score, snippet in hits:
        m = meta.get(str(pid), {})
        results.append({
            "title": (m.get("title") or "（未命名制度）"),
            "issue_time": str(m.get("issue_time") or ""),
            "score": round(float(score) * 100, 1),
            "snippet": (snippet or "")[:300],
        })
    return {"ok": True, "count": len(results), "results": results}


def skill_query_overtime(args: Dict[str, Any], current_user: str) -> Dict[str, Any]:
    """查询某员工加班记录（已通过 jiabanzt=4）。"""
    name = (args.get("name") or current_user or "").strip()
    if not name:
        return {"ok": False, "message": "缺少员工姓名"}
    year = int(args.get("year") or datetime.now().year)
    month = args.get("month")
    month = int(month) if month not in (None, "", 0) else None

    if month:
        month_str = f"{year}-{month:02d}"
        rows = db.execute_query(
            """SELECT timedate, jiabanfs, jbf, tian1, content
               FROM jiaban WHERE xm=%s AND jiabanzt=4
               AND (timedate LIKE %s OR substr(timedate,1,7)=%s)
               ORDER BY timedate DESC""",
            (name, f"{year}-{month:02d}%", month_str),
        )
    else:
        rows = db.execute_query(
            """SELECT timedate, jiabanfs, jbf, tian1, content
               FROM jiaban WHERE xm=%s AND jiabanzt=4
               AND (timedate LIKE %s OR substr(timedate,1,4)=%s)
               ORDER BY timedate DESC""",
            (name, f"{year}%", str(year)),
        )
    total_hours = 0.0
    records = []
    for r in rows:
        h = _to_float(r.get("jbf")) or _to_float(r.get("tian1"))
        total_hours += h
        records.append({
            "date": str(r.get("timedate") or ""),
            "type": r.get("jiabanfs") or "",
            "hours": h,
            "content": (r.get("content") or "")[:80],
        })
    return {
        "ok": True, "name": name, "year": year, "month": month,
        "total_count": len(records), "total_hours": round(total_hours, 2),
        "records": records[:30],
    }


def skill_query_leave(args: Dict[str, Any], current_user: str) -> Dict[str, Any]:
    """查询某员工请假记录（已通过 qjzt=4）。"""
    name = (args.get("name") or current_user or "").strip()
    if not name:
        return {"ok": False, "message": "缺少员工姓名"}
    year = int(args.get("year") or datetime.now().year)
    month = args.get("month")
    month = int(month) if month not in (None, "", 0) else None

    if month:
        month_str = f"{year}-{month:02d}"
        rows = db.execute_query(
            """SELECT qjfs, timefrom, timeto, tian, xiaoshi, content
               FROM qj WHERE xm=%s AND qjzt=4
               AND (timefrom LIKE %s OR substr(timefrom,1,7)=%s
                    OR timefromdate LIKE %s OR substr(timefromdate,1,7)=%s)
               ORDER BY timefrom DESC""",
            (name, f"{year}-{month:02d}%", month_str, f"{year}-{month:02d}%", month_str),
        )
    else:
        rows = db.execute_query(
            """SELECT qjfs, timefrom, timeto, tian, xiaoshi, content
               FROM qj WHERE xm=%s AND qjzt=4
               AND (timefrom LIKE %s OR substr(timefrom,1,4)=%s
                    OR timefromdate LIKE %s OR substr(timefromdate,1,4)=%s)
               ORDER BY timefrom DESC""",
            (name, f"{year}%", str(year), f"{year}%", str(year)),
        )
    total_days = 0.0
    total_hours = 0.0
    records = []
    by_type: Dict[str, float] = {}
    for r in rows:
        d = _to_float(r.get("tian"))
        h = _to_float(r.get("xiaoshi"))
        total_days += d
        total_hours += h
        t = r.get("qjfs") or "其他"
        by_type[t] = round(by_type.get(t, 0.0) + (d if d else h / 8.0), 2)
        records.append({
            "type": t,
            "from": _fmt_dt(r.get("timefrom")),
            "to": _fmt_dt(r.get("timeto")),
            "days": d,
            "hours": h,
            "content": (r.get("content") or "")[:80],
        })
    return {
        "ok": True, "name": name, "year": year, "month": month,
        "total_count": len(records), "total_days": round(total_days, 2),
        "total_hours": round(total_hours, 2), "by_type": by_type,
        "records": records[:30],
    }


def skill_query_business_trip(args: Dict[str, Any], current_user: str) -> Dict[str, Any]:
    """查询某员工公出记录。"""
    name = (args.get("name") or current_user or "").strip()
    if not name:
        return {"ok": False, "message": "缺少员工姓名"}
    year = int(args.get("year") or datetime.now().year)
    month = args.get("month")
    month = int(month) if month not in (None, "", 0) else None

    if month:
        month_str = f"{year}-{month:02d}"
        rows = db.execute_query(
            """SELECT wpdw, gcdd, gcsj, yjfhsj, sjfhtime, gcrw
               FROM gcsqb WHERE gcr=%s AND (gcsj LIKE %s OR DATE_FORMAT(gcsj,'%%Y-%%m')=%s)
               ORDER BY gcsj DESC""",
            (name, f"{month_str}%", month_str),
        )
    else:
        rows = db.execute_query(
            """SELECT wpdw, gcdd, gcsj, yjfhsj, sjfhtime, gcrw
               FROM gcsqb WHERE gcr=%s AND (gcsj LIKE %s OR YEAR(gcsj)=%s)
               ORDER BY gcsj DESC""",
            (name, f"{year}%", year),
        )
    total_days = 0.0
    records = []
    for r in rows:
        gcsj = r.get("gcsj")
        end_dt = r.get("sjfhtime") or r.get("yjfhsj") or gcsj
        days = 1.0
        if gcsj and end_dt:
            try:
                d1 = gcsj if hasattr(gcsj, "day") else datetime.strptime(str(gcsj)[:10], "%Y-%m-%d")
                d2 = end_dt if hasattr(end_dt, "day") else datetime.strptime(str(end_dt)[:10], "%Y-%m-%d")
                days = max(1, (d2 - d1).days + 1)
            except Exception:
                pass
        total_days += days
        records.append({
            "unit": r.get("wpdw") or "",
            "place": r.get("gcdd") or "",
            "start": _fmt_dt(gcsj),
            "expected_return": _fmt_dt(r.get("yjfhsj")),
            "actual_return": _fmt_dt(r.get("sjfhtime")),
            "task": (r.get("gcrw") or "")[:80],
            "days": round(days, 2),
        })
    return {
        "ok": True, "name": name, "year": year, "month": month,
        "total_count": len(records), "total_days": round(total_days, 2),
        "records": records[:30],
    }


def skill_generate_report(args: Dict[str, Any], current_user: str) -> Dict[str, Any]:
    """生成报表下载链接（Excel）。report_type: overtime|leave|business_trip。"""
    report_type = (args.get("report_type") or "").strip()
    type_label = {
        "overtime": "加班", "leave": "请假", "business_trip": "公出",
    }
    if report_type not in type_label:
        return {"ok": False, "message": "report_type 仅支持 overtime / leave / business_trip"}
    name = (args.get("name") or current_user or "").strip()
    if not name:
        return {"ok": False, "message": "缺少员工姓名"}
    year = int(args.get("year") or datetime.now().year)
    month = args.get("month")
    month = int(month) if month not in (None, "", 0) else None

    params = {"report_type": report_type, "name": name, "year": year}
    if month:
        params["month"] = month
    url = "/api/ai-assistant/export?" + urlencode(params)
    period = f"{year}年" + (f"{month}月" if month else "全年")
    filename = f"{name}-{type_label[report_type]}报表-{period}.xlsx"
    return {
        "ok": True,
        "download_url": url,
        "filename": filename,
        "label": f"{name} {period}{type_label[report_type]}报表",
        "message": f"已生成《{filename}》下载链接，请提示用户点击下载。",
    }


SKILL_FUNCS = {
    "search_policy": skill_search_policy,
    "query_overtime": skill_query_overtime,
    "query_leave": skill_query_leave,
    "query_business_trip": skill_query_business_trip,
    "generate_report": skill_generate_report,
}

SKILL_LABELS = {
    "search_policy": "制度智能检索",
    "query_overtime": "加班记录查询",
    "query_leave": "请假记录查询",
    "query_business_trip": "公出记录查询",
    "generate_report": "生成报表下载",
}

# OpenAI 函数调用工具定义
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_policy",
            "description": "对部门制度、工艺规范、管理规定等文档进行语义智能检索，返回最相关的制度片段。当用户询问规章制度、流程规定、工艺要求等知识性问题时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词或自然语言问题"},
                    "top_k": {"type": "integer", "description": "返回条数，默认5", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_overtime",
            "description": "查询某员工已审批通过的加班记录与累计工时。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "员工姓名，不填则查询当前登录用户"},
                    "year": {"type": "integer", "description": "年份，默认当前年"},
                    "month": {"type": "integer", "description": "月份1-12，不填为全年"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_leave",
            "description": "查询某员工已审批通过的请假记录、累计请假天数/小时及按类型分布。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "员工姓名，不填则查询当前登录用户"},
                    "year": {"type": "integer", "description": "年份，默认当前年"},
                    "month": {"type": "integer", "description": "月份1-12，不填为全年"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_business_trip",
            "description": "查询某员工公出（出差）记录与累计公出天数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "员工姓名，不填则查询当前登录用户"},
                    "year": {"type": "integer", "description": "年份，默认当前年"},
                    "month": {"type": "integer", "description": "月份1-12，不填为全年"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_report",
            "description": "为用户生成可下载的 Excel 报表链接。当用户要求导出/下载加班、请假或公出报表时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "report_type": {
                        "type": "string",
                        "enum": ["overtime", "leave", "business_trip"],
                        "description": "报表类型：overtime=加班，leave=请假，business_trip=公出",
                    },
                    "name": {"type": "string", "description": "员工姓名，不填则为当前登录用户"},
                    "year": {"type": "integer", "description": "年份，默认当前年"},
                    "month": {"type": "integer", "description": "月份1-12，不填为全年"},
                },
                "required": ["report_type"],
            },
        },
    },
]


def _execute_skill(name: str, args: Dict[str, Any], current_user: str) -> Dict[str, Any]:
    func = SKILL_FUNCS.get(name)
    if not func:
        return {"ok": False, "message": f"未知技能：{name}"}
    try:
        return func(args, current_user)
    except Exception as e:
        logger.exception(f"技能 {name} 执行失败")
        return {"ok": False, "message": f"技能执行失败：{e}"}


# ==================== System Prompt ====================


def _build_system_prompt(current_user: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return (
        "你是「智能制造工艺部 AI 助手」，服务于哈电智能制造工艺部门的集成办公平台。"
        "你可以整合系统数据库资源，帮助员工查询考勤、加班、请假、公出数据，检索部门制度与工艺规范，并生成可下载的报表。\n\n"
        f"当前登录用户：{current_user or '未知'}；今天日期：{today}。\n\n"
        "工作要求：\n"
        "1. 始终使用简体中文回答，语气专业、简洁、友好。\n"
        "2. 当用户的问题需要查询系统数据（加班/请假/公出记录、统计）或检索制度规范时，必须调用相应的工具获取真实数据，不要凭空编造。\n"
        "3. 当用户未指明姓名时，默认查询当前登录用户的数据。\n"
        "4. 当用户要求导出或下载报表时，调用 generate_report 生成下载链接，并明确告诉用户报表已生成、可点击下方按钮下载。\n"
        "5. 引用制度检索结果时，注明制度标题，并基于检索到的片段作答，避免脱离原文。\n"
        "6. 回答可使用 Markdown（标题、列表、表格、加粗）让结构清晰美观。\n"
        "7. 若工具返回无数据，如实说明未查询到相关记录。"
    )


# ==================== 流式对话接口 ====================


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/chat-stream")
async def chat_stream(req: ChatRequest):
    """带工具调用的流式对话（SSE）。"""
    try:
        from openai import OpenAI
    except ImportError:
        raise HTTPException(status_code=500, detail="服务端未安装 openai SDK，无法调用大模型")

    config = _get_llm_config()
    if not config.get("base_url") or not config.get("model"):
        raise HTTPException(status_code=500, detail="未配置本地大模型，请在 webconfig 中设置 llm_base_url 与 llm_model")

    current_user = (req.current_user or "").strip()
    model = config["model"]
    base_url = config["base_url"]

    # 组装对话消息（仅保留 user / assistant 文本）
    history: List[Dict[str, Any]] = [{"role": "system", "content": _build_system_prompt(current_user)}]
    for m in (req.messages or []):
        role = (m.role or "").strip()
        if role not in ("user", "assistant"):
            continue
        content = (m.content or "").strip()
        if not content:
            continue
        history.append({"role": role, "content": content})

    if len(history) <= 1:
        raise HTTPException(status_code=400, detail="对话内容为空")

    no_think = {"chat_template_kwargs": {"enable_thinking": False}}

    def gen():
        yield _sse({"type": "meta", "model": model, "base_url": base_url})
        messages = list(history)
        try:
            client = OpenAI(base_url=base_url, api_key="ollama", timeout=120.0)
        except Exception as e:
            yield _sse({"type": "error", "message": f"初始化大模型客户端失败：{e}"})
            return

        # ---------- 工具调用循环 ----------
        rounds = 0
        try:
            while rounds < MAX_TOOL_ROUNDS:
                rounds += 1
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.2,
                    stream=False,
                    extra_body=no_think,
                )
                msg = resp.choices[0].message
                tool_calls = getattr(msg, "tool_calls", None) or []
                if not tool_calls:
                    break

                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                })

                for tc in tool_calls:
                    fname = tc.function.name
                    label = SKILL_LABELS.get(fname, fname)
                    try:
                        fargs = json.loads(tc.function.arguments or "{}")
                    except Exception:
                        fargs = {}
                    yield _sse({"type": "tool", "name": fname, "label": label, "status": "running"})

                    result = _execute_skill(fname, fargs, current_user)

                    # 报表下载：额外推送附件事件，前端渲染下载按钮
                    if fname == "generate_report" and result.get("ok") and result.get("download_url"):
                        yield _sse({
                            "type": "attachment",
                            "label": result.get("label") or "报表下载",
                            "url": result.get("download_url"),
                            "filename": result.get("filename") or "report.xlsx",
                        })

                    summary = ""
                    if isinstance(result, dict):
                        if not result.get("ok", True):
                            summary = result.get("message", "执行失败")
                        elif "total_count" in result:
                            summary = f"共 {result.get('total_count', 0)} 条"
                        elif "count" in result:
                            summary = f"命中 {result.get('count', 0)} 条"
                    yield _sse({"type": "tool", "name": fname, "label": label, "status": "done", "summary": summary})

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })
        except Exception as e:
            logger.error(f"AI 助手工具调用失败: {e}")
            yield _sse({"type": "error", "message": f"模型调用失败：{e}"})
            return

        # ---------- 最终答案：流式输出（不再带工具，基于已有上下文/工具结果作答） ----------
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.4,
                stream=True,
                extra_body=no_think,
            )
            got = False
            for event in stream:
                try:
                    piece = getattr(event.choices[0].delta, "content", None) or ""
                except Exception:
                    piece = ""
                if not piece:
                    continue
                got = True
                yield _sse({"type": "chunk", "text": piece})
            if not got:
                yield _sse({"type": "chunk", "text": "（未生成回复，请重试或换一种问法）"})
            yield _sse({"type": "done"})
        except Exception as e:
            logger.error(f"AI 助手流式输出失败: {e}")
            yield _sse({"type": "error", "message": f"流式输出失败：{e}"})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ==================== 报表导出（Excel 下载） ====================


@router.get("/export")
async def export_report(
    report_type: str = Query(..., description="overtime|leave|business_trip"),
    name: str = Query(..., description="员工姓名"),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
):
    """生成并下载某员工的加班 / 请假 / 公出 Excel 报表。"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
    except ImportError:
        raise HTTPException(status_code=500, detail="服务端未安装 openpyxl，无法导出 Excel")

    year = year or datetime.now().year
    args = {"name": name, "year": year, "month": month}

    headers_map = {
        "overtime": (["日期", "加班方式", "时长(小时)", "内容"], "加班报表", skill_query_overtime,
                     lambda r: [r["date"], r["type"], r["hours"], r["content"]]),
        "leave": (["请假类型", "开始时间", "结束时间", "天数", "小时", "事由"], "请假报表", skill_query_leave,
                  lambda r: [r["type"], r["from"], r["to"], r["days"], r["hours"], r["content"]]),
        "business_trip": (["外派单位", "公出地点", "公出时间", "预计返回", "实际返回", "公出任务", "天数"], "公出报表",
                          skill_query_business_trip,
                          lambda r: [r["unit"], r["place"], r["start"], r["expected_return"], r["actual_return"], r["task"], r["days"]]),
    }
    if report_type not in headers_map:
        raise HTTPException(status_code=400, detail="report_type 仅支持 overtime / leave / business_trip")

    cols, sheet_title, skill_func, row_mapper = headers_map[report_type]
    data = skill_func(args, name)
    records = data.get("records", []) if isinstance(data, dict) else []

    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title

    period = f"{year}年" + (f"{month}月" if month else "全年")
    title_text = f"{name} - {sheet_title}（{period}）"
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(cols))
    tcell = ws.cell(row=1, column=1, value=title_text)
    tcell.font = Font(size=14, bold=True)
    tcell.alignment = Alignment(horizontal="center", vertical="center")

    header_fill = PatternFill(start_color="1890FF", end_color="1890FF", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    for ci, h in enumerate(cols, start=1):
        c = ws.cell(row=2, column=ci, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center")

    r_idx = 3
    for rec in records:
        for ci, val in enumerate(row_mapper(rec), start=1):
            ws.cell(row=r_idx, column=ci, value=val)
        r_idx += 1

    # 汇总行
    if report_type == "overtime":
        ws.cell(row=r_idx, column=1, value=f"合计：{data.get('total_count',0)} 条，{data.get('total_hours',0)} 小时").font = Font(bold=True)
    elif report_type == "leave":
        ws.cell(row=r_idx, column=1, value=f"合计：{data.get('total_count',0)} 条，{data.get('total_days',0)} 天 / {data.get('total_hours',0)} 小时").font = Font(bold=True)
    else:
        ws.cell(row=r_idx, column=1, value=f"合计：{data.get('total_count',0)} 条，{data.get('total_days',0)} 天").font = Font(bold=True)

    for ci, h in enumerate(cols, start=1):
        ws.column_dimensions[ws.cell(row=2, column=ci).column_letter].width = max(12, len(str(h)) + 8)

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    from urllib.parse import quote
    filename = f"{name}-{sheet_title}-{period}.xlsx"
    disposition = f"attachment; filename*=UTF-8''{quote(filename)}"
    return StreamingResponse(
        bio,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": disposition},
    )
