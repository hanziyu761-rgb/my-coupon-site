#!/usr/bin/env python3
"""
批量数字人视频生成器 —— 商业化核心入口

支持三种输入模式：
  1. CSV 批量  → 每行一个脚本，输出对应数量的视频
  2. 租户模式  → 指定租户，自动读取其配置批量生产
  3. 单条快跑  → --script 直接跑一条

用法示例：
  # 快速出一条（测试）
  python batch.py --tenant factory_a --script examples/towel_口播_可粘贴.txt

  # CSV 批量（每行一条脚本文字，用逗号分隔 product,script_text）
  python batch.py --tenant factory_a --csv batch_input.csv

  # 所有租户各跑一条（自动取其下 scripts/ 目录最新脚本）
  python batch.py --all-tenants

  # 查看队列状态
  python batch.py --status

选项：
  --workers N    并发工作线程数（默认 2，GPU 任务建议 1）
  --dry-run      只打印计划，不真正执行
  --from-step N  从第N步开始（跳过已有产物）
"""

from __future__ import annotations
import argparse
import csv
import io
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from commercial.tenant import Tenant, list_tenants, build_agent_config
from commercial.job_queue import enqueue, claim_next, mark_done, mark_failed, list_jobs


# ─── 任务执行器 ──────────────────────────────────────────────

def run_single_job(job: dict, dry_run: bool = False, from_step: int = 1) -> str:
    """
    执行一个任务，返回成品视频路径。
    流水线：脚本 → 声音克隆 → 字幕渲染 → 数字人合成 → 分发
    """
    tenant_id = job["tenant_id"]
    tenant = Tenant(tenant_id)
    cfg = build_agent_config(tenant)
    out_dir = tenant.out_dir()
    ts = int(time.time())

    # 脚本来源
    script_file = job.get("script_file") or ""
    script_text = job.get("script_text") or ""
    if not script_file and script_text:
        tmp = out_dir / f"script_{ts}.txt"
        tmp.write_text(script_text, encoding="utf-8")
        script_file = str(tmp)

    if not script_file or not Path(script_file).exists():
        raise FileNotFoundError(f"任务 {job['id']} 没有可用脚本")

    script_path = Path(script_file)
    voice_out = out_dir / f"voice_{ts}.wav"
    subtitle_video = out_dir / f"subtitle_{ts}.mp4"
    dh_video = out_dir / f"dh_{ts}.mp4"
    final_out = out_dir / f"final_{ts}.mp4"

    print(f"\n{'─'*60}")
    print(f"[{tenant_id}] 任务 #{job['id']} 开始")
    print(f"  脚本: {script_path}")
    if dry_run:
        print("  [dry-run] 跳过实际执行")
        return str(final_out)

    # ── 步骤 4: 声音克隆 ──────────────────────────────────────
    voice_cfg = cfg.get("voice", {})
    audio_for_render = None
    if from_step <= 4 and voice_cfg.get("enabled") and voice_cfg.get("ref_audio"):
        _apply_llm_env(cfg)
        _run_step(
            "声音克隆",
            [sys.executable, "04-voice-clone/tts_indextts2.py",
             "--ref", voice_cfg["ref_audio"],
             "--text-file", str(script_path),
             "--out", str(voice_out)],
        )
        if voice_out.exists():
            audio_for_render = voice_out
    else:
        # 找已有 voice.wav
        existing = out_dir / "voice.wav"
        if existing.exists():
            audio_for_render = existing

    # ── 步骤 5: 字幕动画渲染（Remotion）─────────────────────
    if from_step <= 5:
        remotion_dir = ROOT / "05-render-remotion"
        if not (remotion_dir / "node_modules").exists():
            subprocess.run(["npm", "install"], cwd=str(remotion_dir), check=True)

        props_file = remotion_dir / f"props_{ts}.json"
        build_cmd = [
            sys.executable, "build_props.py",
            "--input", str(script_path),
            "--out", str(props_file),
        ]
        if audio_for_render:
            build_cmd += ["--audio", str(audio_for_render)]
        _run_step("字幕动画 props 生成", build_cmd, cwd=str(remotion_dir))

        _run_step(
            "Remotion 渲染",
            ["bash", "render.sh", str(subtitle_video), str(props_file)],
            cwd=str(remotion_dir),
        )
        props_file.unlink(missing_ok=True)

    # ── 步骤 4.5: 数字人渲染 ─────────────────────────────────
    dh_cfg = cfg.get("digital_human", {})
    backend = dh_cfg.get("backend", "mock")

    if from_step <= 5 and backend != "disabled":
        _apply_dh_env(dh_cfg, tenant)
        dh_args = [
            sys.executable, "04-digital-human/digital_human.py",
            "--backend", backend,
            "--out", str(dh_video),
        ]
        if audio_for_render:
            dh_args += ["--audio", str(audio_for_render)]
        if subtitle_video.exists():
            dh_args += ["--subtitle-video", str(subtitle_video)]
        if tenant.avatar_video():
            dh_args += ["--avatar", str(tenant.avatar_video())]

        # 数字人 + 字幕叠加
        if subtitle_video.exists() and backend != "mock":
            dh_args.append("--merge")

        _run_step("数字人渲染", dh_args)

        if dh_video.exists():
            import shutil
            shutil.copy2(dh_video, final_out)
        elif subtitle_video.exists():
            import shutil
            shutil.copy2(subtitle_video, final_out)
    elif subtitle_video.exists():
        import shutil
        shutil.copy2(subtitle_video, final_out)

    # ── 步骤 6: 分发 ─────────────────────────────────────────
    dist_cfg = cfg.get("distribute", {})
    if from_step <= 6 and dist_cfg.get("enabled") and final_out.exists():
        title = (job.get("meta") or {}).get("title") or tenant.config.get("tagline", "")
        _run_step(
            "多平台分发",
            [sys.executable, "06-distribute/distribute.py",
             "--video", str(final_out),
             "--title", title,
             "--platforms", *dist_cfg.get("platforms", ["douyin"])],
        )

    print(f"[{tenant_id}] 任务 #{job['id']} 完成 → {final_out}")
    return str(final_out)


def _run_step(name: str, cmd: list, cwd: str | None = None):
    print(f"\n  ▶ {name}")
    print("   ", " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], check=True, cwd=cwd)


def _apply_llm_env(cfg: dict):
    llm = cfg.get("llm", {})
    provider = llm.get("provider", "deepseek")
    os.environ["LLM_PROVIDER"] = provider
    key_map = {
        "deepseek": "DEEPSEEK_API_KEY", "qwen": "DASHSCOPE_API_KEY",
        "glm": "ZHIPU_API_KEY", "moonshot": "MOONSHOT_API_KEY",
        "doubao": "ARK_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
    }
    env = key_map.get(provider)
    if llm.get("api_key") and env and not os.environ.get(env):
        os.environ[env] = llm["api_key"]


def _apply_dh_env(dh_cfg: dict, tenant: Tenant):
    if dh_cfg.get("avatar_id"):
        os.environ.setdefault("GUIJI_AVATAR_ID", dh_cfg["avatar_id"])
    if dh_cfg.get("heygem_url"):
        os.environ.setdefault("HEYGEM_URL", dh_cfg["heygem_url"])
    tc = tenant.config
    if tc.get("llm", {}).get("api_key"):
        # 硅基智能key通常单独配置
        os.environ.setdefault("GUIJI_API_KEY",
                              tc.get("digital_human", {}).get("api_key", ""))


# ─── Worker 线程 ─────────────────────────────────────────────

def worker(tenant_id: str | None, dry_run: bool, from_step: int, stop_event: threading.Event):
    while not stop_event.is_set():
        job = claim_next(tenant_id)
        if job is None:
            break
        try:
            out = run_single_job(job, dry_run=dry_run, from_step=from_step)
            mark_done(job["id"], out)
        except Exception as e:
            import traceback
            err = traceback.format_exc()
            print(f"\n❌ 任务 #{job['id']} 失败:\n{err}")
            mark_failed(job["id"], err)


# ─── 主入口 ──────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="批量数字人视频生成")
    p.add_argument("--tenant", default=None, help="租户 ID（见 commercial/tenants/）")
    p.add_argument("--script", default=None, help="单条脚本文件路径")
    p.add_argument("--csv", default=None,
                   help="CSV 批量文件（格式: product,script_text 或 product,script_file）")
    p.add_argument("--all-tenants", action="store_true",
                   help="对所有租户各提交一条任务")
    p.add_argument("--workers", type=int, default=2, help="并发 worker 数")
    p.add_argument("--from-step", type=int, default=1,
                   help="从第几步开始（跳过已有产物）")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--status", action="store_true", help="查看队列状态并退出")
    args = p.parse_args()

    if args.status:
        jobs = list_jobs(args.tenant)
        if not jobs:
            print("队列为空")
        else:
            print(f"{'ID':>4}  {'租户':15}  {'状态':8}  {'成品/错误'}")
            for j in jobs:
                info = j["out_video"] or (j["error"] or "")[:60] or ""
                print(f"{j['id']:>4}  {j['tenant_id']:15}  {j['status']:8}  {info}")
        return

    if not args.tenant and not args.all_tenants:
        p.error("请指定 --tenant <id> 或 --all-tenants")

    # ── 入队 ──────────────────────────────────────────────────
    enqueued = 0

    if args.all_tenants:
        for tid in list_tenants():
            t = Tenant(tid)
            scripts_dir = t.dir / "scripts"
            if scripts_dir.exists():
                txts = sorted(scripts_dir.glob("*.txt"), key=lambda p: p.stat().st_mtime)
                if txts:
                    enqueue(tid, script_file=str(txts[-1]))
                    enqueued += 1
                    print(f"入队: {tid} → {txts[-1].name}")
            else:
                print(f"⚠️  {tid} 无 scripts/ 目录，跳过")
    elif args.csv:
        with open(args.csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                tid = row.get("tenant_id") or args.tenant
                enqueue(
                    tid,
                    script_text=row.get("script_text", ""),
                    script_file=row.get("script_file", ""),
                    product=row.get("product", ""),
                )
                enqueued += 1
        print(f"CSV 入队 {enqueued} 条任务")
    elif args.script:
        if not args.tenant:
            p.error("--script 需要指定 --tenant")
        enqueue(args.tenant, script_file=args.script)
        enqueued = 1
        print(f"入队 1 条任务: {args.tenant} → {args.script}")
    else:
        p.error("请指定 --script / --csv / --all-tenants 其中之一")

    if enqueued == 0:
        print("没有可用任务，退出。")
        return

    # ── 启动 workers ──────────────────────────────────────────
    stop = threading.Event()
    threads = []
    n = min(args.workers, enqueued)
    print(f"\n启动 {n} 个 worker …\n")
    for _ in range(n):
        t = threading.Thread(
            target=worker,
            args=(args.tenant if not args.all_tenants else None,
                  args.dry_run, args.from_step, stop),
            daemon=True,
        )
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    # ── 汇总 ──────────────────────────────────────────────────
    done = list_jobs(args.tenant if not args.all_tenants else None, status="done")
    failed = list_jobs(args.tenant if not args.all_tenants else None, status="failed")
    print(f"\n{'='*60}")
    print(f"✅ 完成: {len(done)} 条  ❌ 失败: {len(failed)} 条")
    for j in done:
        print(f"  #{j['id']} → {j['out_video']}")
    for j in failed:
        print(f"  #{j['id']} FAILED: {(j['error'] or '')[:100]}")
    print('='*60)


if __name__ == "__main__":
    main()
