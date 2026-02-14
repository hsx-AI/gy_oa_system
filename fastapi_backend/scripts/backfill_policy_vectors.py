# -*- coding: utf-8 -*-
"""
部门制度向量库回填脚本 - 为已有制度记录生成向量并入库
运行: cd fastapi_backend && python scripts/backfill_policy_vectors.py
"""
import sys
import os

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db
from services.policy_vector import add_to_index

def main():
    rows = db.execute_query("SELECT id, title, issue_time, remark, file_path, file_type FROM dept_policy")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base, "data")
    ok, fail = 0, 0
    for r in rows or []:
        pid = (r.get("id") or "").strip()
        if not pid:
            continue
        title = (r.get("title") or "").strip()
        issue_time = (r.get("issue_time") or "").strip()
        remark = (r.get("remark") or "").strip()
        file_path = (r.get("file_path") or "").strip()
        file_type = (r.get("file_type") or "").strip().lower()
        if add_to_index(pid, title, issue_time, remark, file_path, file_type):
            ok += 1
            print(f"  OK: {pid} {title[:30]}...")
        else:
            fail += 1
            print(f"  FAIL: {pid} {title[:30]}...")
    print(f"\n完成: 成功 {ok} 条, 失败 {fail} 条")

if __name__ == "__main__":
    main()
