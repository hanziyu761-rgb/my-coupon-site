#!/usr/bin/env python3
"""
批量任务队列 —— SQLite 持久化，支持多租户并发。

任务状态：pending → running → done | failed

用法（通常由 batch.py 调用，也可直接查询）：
  python -m commercial.job_queue status --tenant factory_a
  python -m commercial.job_queue retry --job-id 5
"""

from __future__ import annotations
import sqlite3
import json
import time
from contextlib import contextmanager
from pathlib import Path


DB_PATH = Path(__file__).parent / "jobs.db"


@contextmanager
def _conn():
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id   TEXT NOT NULL,
                script_text TEXT,
                script_file TEXT,
                product     TEXT,
                status      TEXT DEFAULT 'pending',
                out_video   TEXT,
                error       TEXT,
                created_at  REAL,
                started_at  REAL,
                done_at     REAL,
                meta        TEXT DEFAULT '{}'
            )
        """)


def enqueue(tenant_id: str, script_text: str = "", script_file: str = "",
            product: str = "", meta: dict | None = None) -> int:
    init_db()
    with _conn() as con:
        cur = con.execute(
            """INSERT INTO jobs
               (tenant_id, script_text, script_file, product, created_at, meta)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (tenant_id, script_text, script_file, product,
             time.time(), json.dumps(meta or {}))
        )
        return cur.lastrowid


def claim_next(tenant_id: str | None = None) -> dict | None:
    """取一个 pending 任务并标记为 running（原子操作）"""
    init_db()
    with _conn() as con:
        where = "WHERE status='pending'"
        params: list = []
        if tenant_id:
            where += " AND tenant_id=?"
            params.append(tenant_id)
        row = con.execute(
            f"SELECT * FROM jobs {where} ORDER BY id LIMIT 1", params
        ).fetchone()
        if row is None:
            return None
        con.execute(
            "UPDATE jobs SET status='running', started_at=? WHERE id=?",
            (time.time(), row["id"])
        )
        return dict(row)


def mark_done(job_id: int, out_video: str):
    with _conn() as con:
        con.execute(
            "UPDATE jobs SET status='done', out_video=?, done_at=? WHERE id=?",
            (out_video, time.time(), job_id)
        )


def mark_failed(job_id: int, error: str):
    with _conn() as con:
        con.execute(
            "UPDATE jobs SET status='failed', error=?, done_at=? WHERE id=?",
            (str(error)[:2000], time.time(), job_id)
        )


def list_jobs(tenant_id: str | None = None, status: str | None = None,
              limit: int = 50) -> list[dict]:
    init_db()
    with _conn() as con:
        wheres, params = [], []
        if tenant_id:
            wheres.append("tenant_id=?"); params.append(tenant_id)
        if status:
            wheres.append("status=?"); params.append(status)
        where = ("WHERE " + " AND ".join(wheres)) if wheres else ""
        rows = con.execute(
            f"SELECT * FROM jobs {where} ORDER BY id DESC LIMIT ?",
            params + [limit]
        ).fetchall()
        return [dict(r) for r in rows]


def retry_job(job_id: int):
    with _conn() as con:
        con.execute(
            "UPDATE jobs SET status='pending', error=NULL WHERE id=? AND status='failed'",
            (job_id,)
        )


# ── CLI ──────────────────────────────────────────────────────

def main():
    import argparse
    p = argparse.ArgumentParser(description="任务队列管理")
    sub = p.add_subparsers(dest="cmd")

    st_p = sub.add_parser("status", help="查看任务状态")
    st_p.add_argument("--tenant", default=None)
    st_p.add_argument("--status", default=None)

    rt_p = sub.add_parser("retry", help="重试失败任务")
    rt_p.add_argument("--job-id", type=int, required=True)

    args = p.parse_args()

    if args.cmd == "status":
        jobs = list_jobs(args.tenant, args.status)
        if not jobs:
            print("（暂无任务）")
            return
        print(f"{'ID':>4}  {'租户':15}  {'状态':8}  {'产品':12}  {'成品'}")
        for j in jobs:
            print(f"{j['id']:>4}  {j['tenant_id']:15}  {j['status']:8}  "
                  f"{(j['product'] or '')[:12]:12}  {j['out_video'] or j['error'] or ''}")

    elif args.cmd == "retry":
        retry_job(args.job_id)
        print(f"任务 {args.job_id} 已重置为 pending")
    else:
        p.print_help()


if __name__ == "__main__":
    main()
