# -*- coding: utf-8 -*-
"""Multi-process email lock test (simulates multiple uvicorn workers).

Examples:
  python scripts/test_email_worker_lock.py --processes 4 --delay 5 --lock-only
  python scripts/test_email_worker_lock.py --to your@email.com --processes 4 --delay 5 --apply
  python scripts/test_email_worker_lock.py --lock-kind shift --departments deptA,deptB --processes 4 --delay 5 --lock-only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _build_lock_name(lock_kind: str, departments: list[str]) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    if lock_kind == "todo":
        return "oa_todo_email_reminder_run"
    if lock_kind == "shift":
        lock_scope = ",".join(sorted(departments)) or "all"
        digest = hashlib.sha256(lock_scope.encode("utf-8")).hexdigest()[:16]
        return f"oa_shift_schedule_email_{today}_{digest}"
    if lock_kind == "holiday":
        lock_scope = ",".join(sorted(departments)) or "all"
        lock_key = f"|{today}"
        digest = hashlib.sha256((lock_scope + lock_key).encode("utf-8")).hexdigest()[:16]
        return f"oa_shift_holiday_email_{digest}"
    return "oa_email_worker_lock_test"


def _worker(
    worker_id: int,
    lock_name: str,
    delay: float,
    to_email: str,
    apply_send: bool,
    lock_only: bool,
) -> dict:
    from routers.email_sender import (
        _build_email_message,
        _get_email_config,
        _release_mysql_lock,
        _smtp_send,
        _try_acquire_mysql_lock,
    )

    pid = os.getpid()
    started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[worker-{worker_id} pid={pid}] started, try lock in {delay:.0f}s: {lock_name}")
    time.sleep(delay)

    label = f"LockTest-W{worker_id}"
    conn = _try_acquire_mysql_lock(lock_name, label)
    if not conn:
        result = {
            "worker": worker_id,
            "pid": pid,
            "started": started,
            "lock_name": lock_name,
            "acquired": False,
            "sent": False,
            "message": "lock not acquired (held by another process)",
        }
        print(f"[worker-{worker_id} pid={pid}] SKIP lock not acquired")
        return result

    print(f"[worker-{worker_id} pid={pid}] OK lock acquired")
    sent = False
    message = "lock acquired"
    try:
        if lock_only:
            message = "lock acquired (lock-only, no email sent)"
            time.sleep(2)
        elif apply_send and to_email:
            cfg = _get_email_config()
            sender = cfg["address"]
            password = cfg["auth_code"]
            if not sender or not password:
                message = "email not configured in webconfig"
            else:
                subject = (
                    f"[OA lock test] worker={worker_id} pid={pid} "
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                body = (
                    "OA multi-worker GET_LOCK test email.\n\n"
                    f"worker_id={worker_id}\n"
                    f"pid={pid}\n"
                    f"lock_name={lock_name}\n"
                    "If you received only 1 email, GET_LOCK works.\n"
                )
                msg = _build_email_message(sender, [to_email], [], subject, body, "plain", None)
                _smtp_send(sender, password, [to_email], msg)
                sent = True
                message = f"sent to {to_email}"
                print(f"[worker-{worker_id} pid={pid}] SENT -> {to_email}")
        else:
            message = "lock acquired but --apply not set, no email sent"
    finally:
        _release_mysql_lock(conn, lock_name, label)

    return {
        "worker": worker_id,
        "pid": pid,
        "started": started,
        "lock_name": lock_name,
        "acquired": True,
        "sent": sent,
        "message": message,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-process email lock test")
    parser.add_argument("--to", type=str, default="", help="recipient email for --apply")
    parser.add_argument("--processes", type=int, default=4, help="parallel processes (simulate workers)")
    parser.add_argument("--delay", type=float, default=5.0, help="seconds before all try lock together")
    parser.add_argument(
        "--lock-kind",
        choices=("test", "todo", "shift", "holiday"),
        default="test",
        help="lock type: test/todo/shift/holiday",
    )
    parser.add_argument(
        "--departments",
        type=str,
        default="",
        help="departments for shift/holiday lock test, comma-separated",
    )
    parser.add_argument("--apply", action="store_true", help="winner sends test email")
    parser.add_argument("--lock-only", action="store_true", help="test lock only, no email")
    args = parser.parse_args()

    if args.lock_only and args.apply:
        print("Use either --lock-only or --apply, not both")
        return 1
    if args.apply and not args.to.strip():
        print("--apply requires --to <email>")
        return 1

    departments = [d.strip() for d in args.departments.split(",") if d.strip()]
    lock_name = _build_lock_name(args.lock_kind, departments)
    n = max(1, int(args.processes))

    print("=" * 60)
    print(f"lock: {lock_name}")
    print(f"processes: {n} | delay: {args.delay}s | lock-only={args.lock_only} | apply={args.apply}")
    if args.apply:
        print(f"to: {args.to.strip()}")
    print("=" * 60)

    ctx = mp.get_context("spawn")
    with ctx.Pool(processes=n) as pool:
        results = pool.starmap(
            _worker,
            [
                (i + 1, lock_name, args.delay, args.to.strip(), args.apply, args.lock_only)
                for i in range(n)
            ],
        )

    acquired = [r for r in results if r.get("acquired")]
    sent = [r for r in results if r.get("sent")]
    print("\n" + "=" * 60)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"acquired: {len(acquired)} | sent: {len(sent)}")
    if len(acquired) == 1 and (args.lock_only or len(sent) == 1):
        print("RESULT: PASS")
        return 0
    if args.lock_only and len(acquired) == 1:
        print("RESULT: PASS (lock-only)")
        return 0
    print("RESULT: FAIL - expected exactly 1 acquirer/sender")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
