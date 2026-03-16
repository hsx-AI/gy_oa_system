# -*- coding: utf-8 -*-
"""
补齐 2025-01 至 2026-02 的加班数据脚本

原理：
  1. 从 attendance_suggestions 表读取 status=0（加班建议）的所有记录
  2. 过滤时间范围为 2025-01 至 2026-02
  3. 排除已在 jiaban 表中存在对应记录的建议（按姓名+时间段判重）
  4. 对每条未处理的加班建议，插入 jiaban 表：
     - jb = '平时加班'
     - hx = '否'（不要换休票）
     - jiabanfs = '补报'
     - jiabanzt = 0（待审批）
     - jbf = 时长（小时），hxp = 0
  5. 部门/性别从 yggl 表补全

使用方法：
  cd fastapi_backend
  python scripts/backfill_overtime.py [--dry-run] [--auto-approve]

  --dry-run       仅预览要插入的记录数，不实际写入
  --auto-approve  写入后自动将 jiabanzt 设为 4（已通过），跳过审批流程
"""

import sys
import os
import uuid
import math
import argparse
import time as _time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database import db


def _flush_print(*args, **kwargs):
    """print 后立即 flush，确保进度实时可见"""
    print(*args, **kwargs)
    sys.stdout.flush()


def round_overtime_hours_down(hours: float) -> float:
    if hours <= 0:
        return 0.0
    return math.floor(hours * 2) / 2.0


def calc_hours(start_time_str: str, end_time_str: str) -> float:
    try:
        fmt = "%Y-%m-%d %H:%M:%S"
        t1 = datetime.strptime(str(start_time_str)[:19], fmt)
        t2 = datetime.strptime(str(end_time_str)[:19], fmt)
        return (t2 - t1).total_seconds() / 3600
    except Exception:
        return 0.0


def load_employee_info():
    """从 yggl 加载姓名 -> {lsys(部门), xbie(性别)} 映射"""
    _flush_print("  正在查询 yggl 表...", end="")
    t0 = _time.time()
    rows = db.execute_query("SELECT name, lsys, xbie FROM yggl", ())
    _flush_print(f" 查询到 {len(rows)} 行 ({_time.time()-t0:.1f}s)")
    info = {}
    for r in rows:
        name = (r.get("name") or "").strip()
        if name:
            info[name] = {
                "department": (r.get("lsys") or "").strip() or "未知",
                "gender": (r.get("xbie") or "男").strip() or "男",
            }
    return info


def load_existing_overtime():
    """
    加载 jiaban 表中已有的加班记录，返回 set((xm, timedate, timefrom, timeto))，
    用于判重——同一人同一天同一时间段不重复插入。
    只关注 2025-01 至 2026-02 的数据。
    """
    _flush_print("  正在查询 jiaban 表...", end="")
    t0 = _time.time()
    sql = """
        SELECT xm, timedate, timefrom, timeto
        FROM jiaban
        WHERE timedate >= '2025-01-01' AND timedate <= '2026-02-28'
    """
    rows = db.execute_query(sql, ())
    _flush_print(f" 查询到 {len(rows)} 行 ({_time.time()-t0:.1f}s)")
    existing = set()
    for r in rows:
        xm = (r.get("xm") or "").strip()
        td = str(r.get("timedate") or "").strip()[:10]
        tf = str(r.get("timefrom") or "").strip()[:19]
        tt = str(r.get("timeto") or "").strip()[:19]
        if xm and td:
            existing.add((xm, td, tf, tt))
    return existing


def load_suggestions():
    """
    读取 attendance_suggestions 中 status=0（加班建议），
    时间范围 2025-01 至 2026-02 的记录。
    """
    _flush_print("  正在查询 attendance_suggestions 表...", end="")
    t0 = _time.time()
    sql = """
        SELECT employee_name, department, year, month, day_type,
               message, start_time, end_time
        FROM attendance_suggestions
        WHERE status = 0
          AND ((year = 2025) OR (year = 2026 AND month <= 2))
        ORDER BY employee_name, start_time
    """
    rows = db.execute_query(sql, ())
    _flush_print(f" 查询到 {len(rows)} 行 ({_time.time()-t0:.1f}s)")
    return rows


def _progress_bar(current, total, width=40, prefix=""):
    """在同一行打印进度条"""
    pct = current / total if total else 1
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    _flush_print(f"\r  {prefix}|{bar}| {current}/{total} ({pct*100:.1f}%)", end="")


def main():
    parser = argparse.ArgumentParser(description="补齐2025-01至2026-02加班数据")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不写入数据库")
    parser.add_argument("--auto-approve", action="store_true", help="自动审批通过(jiabanzt=4)")
    args = parser.parse_args()

    _flush_print("=" * 60)
    _flush_print("加班数据补齐脚本")
    _flush_print(f"时间范围: 2025-01 ~ 2026-02")
    _flush_print(f"模式: {'预览(dry-run)' if args.dry_run else '正式写入'}")
    if args.auto_approve and not args.dry_run:
        _flush_print("自动审批: 是 (jiabanzt=4)")
    _flush_print("=" * 60)

    total_t0 = _time.time()

    # 1. 加载员工信息
    _flush_print("\n[1/4] 加载员工信息...")
    emp_info = load_employee_info()
    _flush_print(f"  共 {len(emp_info)} 名员工")

    # 2. 加载已有加班记录
    _flush_print("\n[2/4] 加载已有加班记录...")
    existing = load_existing_overtime()
    _flush_print(f"  去重后 {len(existing)} 条唯一记录")

    # 3. 加载加班建议
    _flush_print("\n[3/4] 加载加班建议...")
    suggestions = load_suggestions()
    _flush_print(f"  共 {len(suggestions)} 条加班建议")

    # 4. 生成待插入记录
    _flush_print("\n[4/4] 生成待插入记录...")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    jiabanzt = 4 if args.auto_approve else 0
    to_insert = []
    skipped_existing = 0
    skipped_short = 0

    for idx, s in enumerate(suggestions):
        if (idx + 1) % 500 == 0 or idx == len(suggestions) - 1:
            _progress_bar(idx + 1, len(suggestions), prefix="分析建议 ")

        name = (s.get("employee_name") or "").strip()
        start_time = s.get("start_time")
        end_time = s.get("end_time")
        if not name or not start_time or not end_time:
            continue

        start_str = str(start_time)[:19]
        end_str = str(end_time)[:19]
        date_str = start_str[:10]

        if (name, date_str, start_str, end_str) in existing:
            skipped_existing += 1
            continue

        hours = calc_hours(start_str, end_str)
        hours = round_overtime_hours_down(hours)
        if hours < 0.5:
            skipped_short += 1
            continue

        info = emp_info.get(name, {"department": "未知", "gender": "男"})
        department = info["department"]
        gender = info["gender"]

        tian1_str = str(int(hours)) if hours == int(hours) else str(hours)
        jbf_val = float(hours)
        hxp_val = 0.0

        new_id = uuid.uuid4().hex
        to_insert.append((
            new_id,
            department,     # bz
            name,           # xm
            gender,         # xb
            "平时加班",     # jb
            "补报",         # jiabanfs
            date_str,       # timedate
            start_str,      # timefrom
            end_str,        # timeto
            "",             # content
            "",             # spr
            now,            # jiabantime
            jiabanzt,       # jiabanzt: 0待审批 or 4已通过
            "否",           # hx
            tian1_str,      # tian1
            jbf_val,        # jbf
            hxp_val,        # hxp
        ))

    _flush_print("")  # 换行
    _flush_print(f"\n统计:")
    _flush_print(f"  待插入: {len(to_insert)} 条")
    _flush_print(f"  跳过(已存在): {skipped_existing} 条")
    _flush_print(f"  跳过(时长<0.5h): {skipped_short} 条")

    if not to_insert:
        _flush_print("\n没有需要补齐的加班记录，退出。")
        return

    # 按人汇总
    by_person = {}
    for row in to_insert:
        name = row[2]
        by_person.setdefault(name, []).append(row)

    _flush_print(f"\n涉及 {len(by_person)} 名员工:")
    for name in sorted(by_person.keys()):
        records = by_person[name]
        total_hours = sum(float(r[14]) for r in records)
        _flush_print(f"  {name}: {len(records)} 条, 共 {total_hours} 小时")

    if args.dry_run:
        elapsed = _time.time() - total_t0
        _flush_print(f"\n[dry-run] 预览模式，未写入数据库。总耗时 {elapsed:.1f}s")
        return

    # 确认
    confirm = input(f"\n确认插入 {len(to_insert)} 条加班记录? (y/N): ").strip().lower()
    if confirm != "y":
        _flush_print("已取消。")
        return

    # 批量插入（带进度条）
    sql = """
        INSERT INTO jiaban (id, bz, xm, xb, jb, jiabanfs, timedate, timefrom, timeto,
                            content, spr, jiabantime, jiabanzt, hx, tian1, jbf, hxp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    total = len(to_insert)
    inserted = 0
    failed = 0
    insert_t0 = _time.time()

    for i, params in enumerate(to_insert):
        try:
            db.execute_update(sql, params)
            inserted += 1
        except Exception as e:
            failed += 1
            if failed <= 10:
                _flush_print(f"\n  [ERROR] 插入失败: {params[2]} {params[6]} - {e}")

        if (i + 1) % 50 == 0 or i == total - 1:
            elapsed = _time.time() - insert_t0
            speed = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (total - i - 1) / speed if speed > 0 else 0
            _progress_bar(i + 1, total, prefix=f"写入数据 ")
            _flush_print(f"  {speed:.0f}条/s  ETA {eta:.0f}s", end="")

    _flush_print("")  # 换行
    total_elapsed = _time.time() - total_t0
    _flush_print(f"\n{'='*60}")
    _flush_print(f"完成！成功插入 {inserted} 条加班记录。")
    if failed > 0:
        _flush_print(f"  失败: {failed} 条")
    _flush_print(f"  总耗时: {total_elapsed:.1f}s")
    _flush_print(f"{'='*60}")


if __name__ == "__main__":
    main()
