# -*- coding: utf-8 -*-
"""
公出地图接口
"""
from fastapi import APIRouter
from datetime import datetime, date
from collections import defaultdict
import re
from database import db

router = APIRouter()

# 直辖市
MUNICIPALITIES = ["北京", "上海", "天津", "重庆"]

# 自治区
AUTONOMOUS_REGIONS = [
    "内蒙古自治区",
    "广西壮族自治区",
    "西藏自治区",
    "宁夏回族自治区",
    "新疆维吾尔自治区",
]

# 特别行政区
SPECIAL_ADMINISTRATIVE_REGIONS = [
    "香港特别行政区",
    "澳门特别行政区",
]

# 一些中国地区别名（便于测试数据写得不完全规范时也能识别）
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


def parse_china_region(gcdd: str):
    """
    只负责把“境内公出”的 gcdd 解析成中国地图需要的区域名称
    返回：
    - xx省
    - xx市（直辖市）
    - xx自治区
    - xx特别行政区
    """
    if not gcdd:
        return None

    gcdd = str(gcdd).strip()

    # 特别行政区
    for region in SPECIAL_ADMINISTRATIVE_REGIONS:
        if gcdd.startswith(region):
            return region

    # 自治区
    for region in AUTONOMOUS_REGIONS:
        if gcdd.startswith(region):
            return region

    # 直辖市
    for m in MUNICIPALITIES:
        if gcdd.startswith(m):
            return m + "市"

    # 普通省
    match = re.match(r"(.+?省)", gcdd)
    if match:
        return match.group(1)

    # 中国地区别名
    for k, v in CHINA_REGION_ALIASES.items():
        if gcdd.startswith(k):
            return v

    # 最后兜底，直接原样返回，避免数据丢失
    return gcdd


def normalize_world_country(gcdd: str):
    """
    只负责把“境外公出”的 gcdd 解析成世界地图需要的国家名称
    默认你的测试数据是：美国 / 英国 / 巴西 这种
    也兼容：美国/纽约、英国,伦敦 这种写法
    """
    if not gcdd:
        return None

    gcdd = str(gcdd).strip()

    # 按常见分隔符截取第一个字段
    separators = ["/", "／", ",", "，", "、", ";", "；", "(", "（"]
    for sep in separators:
        if sep in gcdd:
            gcdd = gcdd.split(sep)[0].strip()
            break

    return gcdd or None


def to_date(v):
    """把 datetime/date/字符串 转成 date"""
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
    a = to_date(a)
    b = to_date(b)
    return (b - a).days


def build_tree(src):
    result = []
    for k, persons in src.items():
        dept_map = defaultdict(list)
        for p in persons:
            dept_map[p["dept"]].append(p)

        dept_list = []
        for d, plist in dept_map.items():
            dept_list.append({
                "dept": d,
                "count": len(plist),
                "persons": plist
            })

        dept_list.sort(key=lambda x: x["count"], reverse=True)

        result.append({
            "name": k,
            "count": len(persons),
            "depts": dept_list
        })

    result.sort(key=lambda x: x["count"], reverse=True)
    return result


@router.get("/business-trip-map")
async def business_trip_map():
    today = date.today()

    # 这里保持你现在的测试逻辑：先不按“当前正在公出中”筛选，只排除市内公出
    sql = """
        SELECT gcr, gcdw, gcdd, yjcfsj, yjfhsj, xmmc, gclx
        FROM gcsqb
        WHERE gclx != '市内公出'
        ORDER BY yjfhsj DESC
        LIMIT 500
    """

    rows = db.execute_query(sql)

    china_map = defaultdict(list)
    world_map = defaultdict(list)

    china_lines = set()
    world_lines = set()

    for r in rows:
        gclx = (r.get("gclx") or "").strip()
        gcdd = (r.get("gcdd") or "").strip()

        if not gcdd:
            continue

        # 市内公出直接过滤
        if gclx == "市内公出":
            continue

        start = to_date(r.get("yjcfsj"))
        end = to_date(r.get("yjfhsj"))
        if not start or not end:
            continue

        passed = days_between(start, today)
        remain = days_between(today, end)

        person = {
            "name": r.get("gcr") or "",
            "dept": r.get("gcdw") or "未分组部门",
            "project": r.get("xmmc") or "",
            "location": gcdd,
            "period": f"{start} ~ {end}",
            "passed": passed,
            "remain": remain
        }

        # 1) 境内公出 -> 一律走中国逻辑
        if gclx == "境内公出":
            region = parse_china_region(gcdd)
            if not region:
                continue

            china_map[region].append(person)

            # 黑龙江省（包括省内其他城市）不画飞线，但明细照常显示
            if region != "黑龙江省":
                china_lines.add(region)

        # 2) 境外公出 -> 一律走世界逻辑
        elif gclx == "境外公出":
            country = normalize_world_country(gcdd)
            if not country:
                continue

            world_map[country].append(person)
            world_lines.add(country)

        # 3) 其他异常值忽略
        else:
            continue

    china_tree = build_tree(china_map)
    world_tree = build_tree(world_map)

    return {
        "china": {
            "points": [{"name": k, "value": len(v)} for k, v in china_map.items()],
            "lines": list(china_lines),
            "tree": china_tree,
            "total": sum(item["count"] for item in china_tree)
        },
        "world": {
            "points": [{"name": k, "value": len(v)} for k, v in world_map.items()],
            "lines": list(world_lines),
            "tree": world_tree,
            "total": sum(item["count"] for item in world_tree)
        }
    }