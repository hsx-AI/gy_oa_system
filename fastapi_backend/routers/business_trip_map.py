# -*- coding: utf-8 -*-
"""
公出地图接口 — 侧边栏始终按省份分组，不出现县/区级分组
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
_city_coordinates: dict = _load_json(os.path.join(_DATA_DIR, "city_coordinates.json"))

_PROVINCE_NAMES = sorted(set(_city_province_map.values()), key=lambda n: len(n), reverse=True)

_CITY_NAMES_SORTED = sorted(_city_province_map.keys(), key=lambda n: len(n), reverse=True)

_CITY_SHORT_MAP: dict = {}
for full_name in _city_province_map:
    short = re.sub(r"(市|地区|盟)$", "", full_name)
    if short and short != full_name:
        _CITY_SHORT_MAP[short] = full_name

_CITY_SHORT_SORTED = sorted(_CITY_SHORT_MAP.keys(), key=lambda n: len(n), reverse=True)

MUNICIPALITIES = {"北京": "北京市", "上海": "上海市", "天津": "天津市", "重庆": "重庆市"}

_PROVINCE_CENTROIDS = {
    "北京市": [116.4074, 39.9042], "天津市": [117.1901, 39.1256],
    "河北省": [114.5149, 38.0428], "山西省": [112.5489, 37.8706],
    "内蒙古自治区": [111.7490, 40.8427], "辽宁省": [123.4315, 41.8057],
    "吉林省": [125.3245, 43.8868], "黑龙江省": [126.6424, 45.7570],
    "上海市": [121.4737, 31.2304], "江苏省": [118.7969, 32.0603],
    "浙江省": [120.1551, 30.2741], "安徽省": [117.2272, 31.8206],
    "福建省": [119.2965, 26.0745], "江西省": [115.8581, 28.6820],
    "山东省": [117.1205, 36.6519], "河南省": [113.6254, 34.7466],
    "湖北省": [114.3054, 30.5931], "湖南省": [112.9388, 28.2282],
    "广东省": [113.2644, 23.1291], "广西壮族自治区": [108.3200, 22.8244],
    "海南省": [110.3494, 20.0174], "重庆市": [106.5516, 29.5630],
    "四川省": [104.0657, 30.5723], "贵州省": [106.6302, 26.6477],
    "云南省": [102.8329, 24.8801], "西藏自治区": [91.1322, 29.6600],
    "陕西省": [108.9402, 34.3416], "甘肃省": [103.8343, 36.0611],
    "青海省": [101.7782, 36.6171], "宁夏回族自治区": [106.2782, 38.4664],
    "新疆维吾尔自治区": [87.6177, 43.7928],
    "香港特别行政区": [114.1694, 22.3193],
    "澳门特别行政区": [113.5439, 22.1987],
    "台湾省": [121.5654, 25.0330],
}

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

# 省份简称（两字）到全称的映射，用于"浙江""山东"等简写
_PROVINCE_SHORT_ALIASES = {}
for pn in _PROVINCE_NAMES:
    if pn.endswith("省") and len(pn) >= 3:
        _PROVINCE_SHORT_ALIASES[pn[:-1]] = pn
    elif pn.endswith("市") and len(pn) >= 3:
        _PROVINCE_SHORT_ALIASES[pn[:-1]] = pn

# ── 解析函数 ───────────────────────────────────────

def _try_fuzzy_city_match(text):
    """对短文本尝试加常见行政后缀(市/县/区)匹配城市，返回 (province, city) 或 None"""
    for suffix in ("市", "县", "区"):
        guess = text + suffix
        if guess in _city_province_map:
            return _city_province_map[guess], guess
    for suffix in ("市", "县", "区"):
        guess = text + suffix
        for full_city in _city_province_map:
            if full_city.startswith(guess):
                return _city_province_map[full_city], full_city
    return None


def parse_china_location(gcdd: str):
    """
    解析境内公出地点，返回 (province, city):
      - province: 省/直辖市/自治区全称（用于地图高亮 + 侧边栏省份分组）
      - city: 市级名称（用于散点标记）；解析不到则 None
    始终返回省级作为第一个元素，县/区级地名自动归并到所属省份。
    """
    if not gcdd:
        return None, None

    gcdd = str(gcdd).strip()

    # 1) 直辖市优先
    for m_short, m_full in MUNICIPALITIES.items():
        if gcdd.startswith(m_short) or m_full in gcdd:
            return m_full, m_full

    # 2) 省级关键字优先
    for prov_name in _PROVINCE_NAMES:
        if prov_name in gcdd:
            return prov_name, None

    # 3) 省级别名（"浙江杭州""香港xx"等）
    for alias, prov_name in CHINA_REGION_ALIASES.items():
        if gcdd.startswith(alias) or alias in gcdd:
            return prov_name, None

    # 3.5) 省份简称（"浙江""山东"等两字简写）
    for short, full in _PROVINCE_SHORT_ALIASES.items():
        if short in gcdd:
            return full, None

    # 4) 通过城市全称反推省份
    for full_city in _CITY_NAMES_SORTED:
        if full_city in gcdd:
            province = _city_province_map[full_city]
            return province, full_city

    # 5) 通过城市简称反推省份
    for short, full_city in _CITY_SHORT_MAP.items():
        if short in gcdd:
            province = _city_province_map[full_city]
            return province, full_city

    # 6) 模糊匹配：对短地名自动加"市/县/区"后缀尝试（覆盖余姚、象山、桐庐等县级地名）
    clean = re.sub(r"[省市县区镇乡村路号].*", "", gcdd).strip()
    if clean and 2 <= len(clean) <= 4:
        result = _try_fuzzy_city_match(clean)
        if result:
            return result[0], result[1]

    # 7) 兜底：从文本里提取省级尾缀
    m = re.search(r"(.+?省)", gcdd)
    if m:
        return m.group(1), None
    m = re.search(r"(.+?自治区)", gcdd)
    if m:
        return m.group(1), None
    m = re.search(r"(.+?特别行政区)", gcdd)
    if m:
        return m.group(1), None

    return "未识别省份", None


def normalize_world_country(gcdd: str):
    """解析单段境外地点文本，提取国家名"""
    if not gcdd:
        return None
    gcdd = str(gcdd).strip()
    inner_seps = ["/", "\uff0f", ",", "\uff0c", ";", "\uff1b", "(", "\uff08"]
    for sep in inner_seps:
        if sep in gcdd:
            gcdd = gcdd.split(sep)[0].strip()
            break
    return gcdd or None


def split_multi_locations(gcdd: str) -> list:
    """将 '、' 分隔的多地点字符串拆分为独立地点列表"""
    if not gcdd:
        return []
    parts = [p.strip() for p in str(gcdd).split("\u3001") if p.strip()]
    return parts if parts else [gcdd.strip()]


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
def business_trip_map():
    today = date.today()

    sql = """
        SELECT gcr, gcdw, gcdd, yjcfsj, yjfhsj, xmmc, gclx
        FROM gcsqb
        WHERE gclx != '市内公出'
          AND bldzt = 2 AND szrzt = 2
          AND yjfhsj >= %s
        ORDER BY yjfhsj DESC
        LIMIT 500
    """
    rows = db.execute_query(sql, (today.strftime("%Y-%m-%d"),))

    china_map = defaultdict(list)
    china_city_map = defaultdict(list)
    world_map = defaultdict(list)

    china_lines = set()
    world_lines = set()

    for r in rows:
        gclx = (r.get("gclx") or "").strip()
        gcdd_raw = (r.get("gcdd") or "").strip()
        if not gcdd_raw or gclx == "\u5e02\u5185\u516c\u51fa":
            continue

        start = to_date(r.get("yjcfsj"))
        end = to_date(r.get("yjfhsj"))
        if not start or not end:
            continue

        base_person = {
            "name": r.get("gcr") or "",
            "dept": r.get("gcdw") or "\u672a\u5206\u7ec4\u90e8\u95e8",
            "project": r.get("xmmc") or "",
            "location": gcdd_raw,
            "period": f"{start} ~ {end}",
            "passed": max(0, days_between(start, today)),
            "remain": max(0, days_between(today, end))
        }

        loc_parts = split_multi_locations(gcdd_raw)

        if gclx == "\u5883\u5185\u516c\u51fa":
            seen_provinces = set()
            for part in loc_parts:
                province, city = parse_china_location(part)
                if not province or province in seen_provinces:
                    continue
                seen_provinces.add(province)
                china_map[province].append(base_person)
                if city:
                    china_city_map[city].append(base_person)
                if province != "\u9ed1\u9f99\u6c5f\u7701":
                    china_lines.add(province)

        elif gclx == "\u5883\u5916\u516c\u51fa":
            seen_countries = set()
            for part in loc_parts:
                country = normalize_world_country(part)
                if not country or country in seen_countries:
                    continue
                seen_countries.add(country)
                world_map[country].append(base_person)
                world_lines.add(country)

    city_count_map = {city: len(persons) for city, persons in china_city_map.items()}

    def _slim_persons(plist):
        return [{"name": p["name"], "dept": p["dept"], "project": p["project"],
                 "location": p["location"], "period": p["period"],
                 "passed": p["passed"], "remain": p["remain"]} for p in plist]

    city_points_list = []
    for city, persons in china_city_map.items():
        coord = _city_coordinates.get(city)
        if coord:
            city_points_list.append({
                "name": city,
                "count": len(persons),
                "coord": coord,
                "persons": _slim_persons(persons)
            })

    covered_keys = set()
    for city, persons in china_city_map.items():
        if _city_coordinates.get(city):
            for p in persons:
                covered_keys.add(p["name"] + "|" + p["location"])

    for province, persons in china_map.items():
        uncovered = [p for p in persons
                     if (p["name"] + "|" + p["location"]) not in covered_keys]
        if uncovered:
            coord = _PROVINCE_CENTROIDS.get(province)
            if coord:
                city_points_list.append({
                    "name": province,
                    "count": len(uncovered),
                    "coord": coord,
                    "persons": _slim_persons(uncovered)
                })

    china_tree = build_tree(china_map)
    world_tree = build_tree(world_map)

    return {
        "china": {
            "points": [{"name": k, "value": len(v)} for k, v in china_map.items()],
            "lines": list(china_lines),
            "tree": china_tree,
            "total": sum(item["count"] for item in china_tree),
            "cityPoints": city_count_map,
            "cityList": city_points_list,
        },
        "world": {
            "points": [{"name": k, "value": len(v)} for k, v in world_map.items()],
            "lines": list(world_lines),
            "tree": world_tree,
            "total": sum(item["count"] for item in world_tree)
        }
    }
