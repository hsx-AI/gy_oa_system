# -*- coding: utf-8 -*-
"""
公出地图接口 — 按城市级别解析公出地点
"""
from fastapi import APIRouter
from datetime import datetime, date
from collections import defaultdict
import json, os, re
from database import db

router = APIRouter()

# ── 加载省市映射数据 ──────────────────────────────
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

_city_province_map: dict = _load_json(os.path.join(_DATA_DIR, "city_province_map.json"))

_PROVINCE_NAMES = list(set(_city_province_map.values()))

_CITY_NAMES_SORTED = sorted(_city_province_map.keys(), key=lambda n: len(n), reverse=True)

_CITY_SHORT_MAP: dict = {}
for full_name in _city_province_map:
    short = re.sub(r"(市|地区|盟)$", "", full_name)
    if short and short != full_name:
        _CITY_SHORT_MAP[short] = full_name

_CITY_SHORT_SORTED = sorted(_CITY_SHORT_MAP.keys(), key=lambda n: len(n), reverse=True)

MUNICIPALITIES = {"北京": "北京市", "上海": "上海市", "天津": "天津市", "重庆": "重庆市"}

CHINA_REGION_ALIASES = {
    "香港": "香港特别行政区",
    "澳门": "澳门特别行政区",
    "内蒙古": "内蒙古自治区",
    "广西": "广西壮族自治区",
    "西藏": "西藏自治区",
    "宁夏": "宁夏回族自治区",
    "新疆": "新疆维吾尔自治区",
    "台湾": "台湾省",
}

# ── 解析函数 ───────────────────────────────────────

def parse_china_location(gcdd: str):
    """
    解析境内公出地点，返回 (province, city):
      - province: 省/直辖市/自治区名称（用于地图高亮）
      - city: 市级名称（用于散点标记）；如果只能解析到省，city=None
    支持新版 LocationPicker 生成的 "黑龙江省哈尔滨市南岗区xxx" 和
    旧版手写的 "杭州、桐庐" "哈电江苏镇江公司" 等各种写法。
    """
    if not gcdd:
        return None, None

    gcdd = str(gcdd).strip()

    for m_short, m_full in MUNICIPALITIES.items():
        if gcdd.startswith(m_short):
            return m_full, m_full

    for full_city in _CITY_NAMES_SORTED:
        if full_city in gcdd:
            province = _city_province_map[full_city]
            return province, full_city

    for short, full_city in _CITY_SHORT_MAP.items():
        if short in gcdd:
            province = _city_province_map[full_city]
            return province, full_city

    for alias, prov_name in CHINA_REGION_ALIASES.items():
        if gcdd.startswith(alias):
            return prov_name, None

    m = re.match(r"(.+?省)", gcdd)
    if m:
        return m.group(1), None

    m = re.match(r"(.+?自治区)", gcdd)
    if m:
        return m.group(1), None

    return gcdd, None


def normalize_world_country(gcdd: str):
    if not gcdd:
        return None
    gcdd = str(gcdd).strip()
    separators = ["/", "／", ",", "，", "、", ";", "；", "(", "（"]
    for sep in separators:
        if sep in gcdd:
            gcdd = gcdd.split(sep)[0].strip()
            break
    return gcdd or None


# ── 工具函数 ──────────────────────────────────────

def to_date(v):
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        return datetime.fromisoformat(v.replace(" ", "T")).date()
    return v


def days_between(a, b):
    return (to_date(b) - to_date(a)).days


def build_tree(src):
    """按 region -> dept -> person 构建树"""
    result = []
    for k, persons in src.items():
        dept_map = defaultdict(list)
        for p in persons:
            dept_map[p["dept"]].append(p)
        dept_list = sorted(
            [{"dept": d, "count": len(pl), "persons": pl} for d, pl in dept_map.items()],
            key=lambda x: x["count"], reverse=True
        )
        result.append({"name": k, "count": len(persons), "depts": dept_list})
    result.sort(key=lambda x: x["count"], reverse=True)
    return result


# ── API ────────────────────────────────────────────

@router.get("/business-trip-map")
async def business_trip_map():
    today = date.today()

    sql = """
        SELECT gcr, gcdw, gcdd, yjcfsj, yjfhsj, xmmc, gclx
        FROM gcsqb
        WHERE gclx != '市内公出'
        ORDER BY yjfhsj DESC
        LIMIT 500
    """
    rows = db.execute_query(sql)

    china_map = defaultdict(list)      # province_or_city -> [person]
    china_city_map = defaultdict(list)  # city -> [person]  (仅有city信息的)
    world_map = defaultdict(list)

    china_lines = set()
    china_city_points = []  # [{name, coord, count}]
    world_lines = set()

    for r in rows:
        gclx = (r.get("gclx") or "").strip()
        gcdd = (r.get("gcdd") or "").strip()
        if not gcdd or gclx == "市内公出":
            continue

        start = to_date(r.get("yjcfsj"))
        end = to_date(r.get("yjfhsj"))
        if not start or not end:
            continue

        person = {
            "name": r.get("gcr") or "",
            "dept": r.get("gcdw") or "未分组部门",
            "project": r.get("xmmc") or "",
            "location": gcdd,
            "period": f"{start} ~ {end}",
            "passed": days_between(start, today),
            "remain": days_between(today, end)
        }

        if gclx == "境内公出":
            province, city = parse_china_location(gcdd)
            if not province:
                continue
            china_map[province].append(person)
            if city:
                china_city_map[city].append(person)
            if province != "黑龙江省":
                china_lines.add(province)

        elif gclx == "境外公出":
            country = normalize_world_country(gcdd)
            if not country:
                continue
            world_map[country].append(person)
            world_lines.add(country)

    city_count_map = {city: len(persons) for city, persons in china_city_map.items()}

    china_tree = build_tree(china_map)
    world_tree = build_tree(world_map)

    return {
        "china": {
            "points": [{"name": k, "value": len(v)} for k, v in china_map.items()],
            "lines": list(china_lines),
            "tree": china_tree,
            "total": sum(item["count"] for item in china_tree),
            "cityPoints": city_count_map,
        },
        "world": {
            "points": [{"name": k, "value": len(v)} for k, v in world_map.items()],
            "lines": list(world_lines),
            "tree": world_tree,
            "total": sum(item["count"] for item in world_tree)
        }
    }
