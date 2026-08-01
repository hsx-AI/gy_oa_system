# -*- coding: utf-8 -*-
"""按各科室排班邮件配置，临时补发指定假期的节假日值班表邮件。

示例：
  # 列出某年假期
  python scripts/send_shift_holiday_email.py --year 2026 --holiday x --list-holidays

  # 确认后真正发送（不加 --apply 只打印参数不发信）
  python scripts/send_shift_holiday_email.py --year 2026 --holiday 高温防暑休假 --force --apply

  # 指定科室 + 强制重发
  python scripts/send_shift_holiday_email.py --year 2026 --holiday 春节 --department 智能制造技术室 --force --apply

假期名称须与 /shift/holiday-options 返回的 name 一致（如：元旦、春节、高温防暑休假）。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description="临时补发节假日值班表邮件")
    parser.add_argument("--year", type=int, required=True, help="假期年份，如 2026")
    parser.add_argument("--holiday", type=str, required=True, help="假期名称，如 高温防暑休假")
    parser.add_argument("--department", type=str, default="", help="只发指定科室；留空=全部已启用排班邮件的科室")
    parser.add_argument("--force", action="store_true", help="忽略已发送记录强制重发")
    parser.add_argument("--apply", action="store_true", help="确认执行发送（不加此参数仅打印参数并退出）")
    parser.add_argument("--list-holidays", action="store_true", help="列出该年可用假期后退出")
    args = parser.parse_args()

    from routers.shift_schedule import _holiday_options_for_year

    options = _holiday_options_for_year(args.year)
    if args.list_holidays or not options:
        print(f"{args.year} 年可用假期：")
        for opt in options:
            print(f"  - {opt['name']}（{opt.get('startDate')} 至 {opt.get('endDate')}）")
        if args.list_holidays:
            return 0
        if not options:
            print("未找到假期数据，请先维护节假日库。")
            return 1

    names = {o["name"] for o in options}
    if args.holiday not in names:
        print(f"未找到假期「{args.holiday}」。可用：")
        for opt in options:
            print(f"  - {opt['name']}")
        return 1

    only = [args.department.strip()] if args.department.strip() else None
    print(
        f"将补发：{args.year}年「{args.holiday}」"
        f" | 科室={'、'.join(only) if only else '全部启用科室'}"
        f" | force={bool(args.force)}"
    )
    if not args.apply:
        print("未加 --apply，已退出（未发信）。确认后请加上 --apply 再执行。")
        return 0

    from routers.email_sender import run_shift_holiday_email_once

    result = asyncio.run(
        run_shift_holiday_email_once(
            trigger_label="脚本临时补发",
            only_departments=only,
            force=bool(args.force),
            target_year=args.year,
            target_holiday=args.holiday,
        )
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
