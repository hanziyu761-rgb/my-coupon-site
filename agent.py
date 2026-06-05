#!/usr/bin/env python3
"""
数字人短视频智能体 —— 一条命令跑完整条流水线

  下载 → 转写纠错 → 仿写 → 声音克隆 → 字幕动画/对口型 → 一键分发

用法:
  cp config.example.yaml config.yaml   # 改成你的配置
  python agent.py                       # 跑全流程
  python agent.py --from 3              # 从第3步（仿写）开始
  python agent.py --only 5              # 只跑第5步（渲染）
  python agent.py --url "<视频URL>"     # 临时覆盖下载源

各步对算力的要求见 README。无 GPU 时第4/5步对口型会自动跳过，
仍能产出「字幕动画 + （可选）配音」的成品视频。
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
OUT = ROOT / "out"
TRANSCRIPTS = ROOT / "transcripts"
DOWNLOADS = ROOT / "downloads"


# ── 工具 ─────────────────────────────────────────────────────
def log(step, msg):
    print(f"\n{'='*60}\n[第{step}步] {msg}\n{'='*60}")


def run(cmd, cwd=None):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, cwd=cwd)


def load_config(path):
    try:
        import yaml
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "-q"])
        import yaml
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def newest(pattern, base=TRANSCRIPTS):
    files = sorted(base.glob(pattern), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def apply_llm_env(cfg):
    """把 config 里的 llm 设置注入环境变量，供各步的 llm.py 读取"""
    llm = cfg.get("llm", {})
    provider = llm.get("provider", "deepseek")
    os.environ["LLM_PROVIDER"] = provider
    if llm.get("model"):
        os.environ["LLM_MODEL"] = llm["model"]
    # 若 config 里直接写了 key，按服务商映射到对应环境变量
    key_envs = {
        "deepseek": "DEEPSEEK_API_KEY", "qwen": "DASHSCOPE_API_KEY",
        "glm": "ZHIPU_API_KEY", "moonshot": "MOONSHOT_API_KEY",
        "doubao": "ARK_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
    }
    env_name = key_envs.get(provider)
    if llm.get("api_key") and env_name and not os.environ.get(env_name):
        os.environ[env_name] = llm["api_key"]
    if env_name and not os.environ.get(env_name):
        print(f"⚠️  未配置 {provider} 的 API key（{env_name}）。"
              f"第2/3步及字幕排版将退回本地兜底或失败。")


# ── 各步 ─────────────────────────────────────────────────────
def step1_download(cfg) -> Path:
    log(1, "下载对标视频")
    d = cfg["download"]
    DOWNLOADS.mkdir(exist_ok=True)
    if d["platform"] in ("youtube", "bilibili"):
        run([sys.executable, "01-download/download.py",
             "--platform", d["platform"], "--url", d["url"],
             "--output", str(DOWNLOADS)])
    else:
        run([sys.executable, "01-download/download.py",
             "--platform", "douyin", "--user", d["user"],
             "--limit", str(d["limit"]), "--output", str(DOWNLOADS)])
    vids = sorted(DOWNLOADS.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    if not vids:
        sys.exit("下载后未找到 mp4")
    print(f"→ {vids[-1]}")
    return vids[-1]


def step2_transcribe(cfg, video: Path) -> Path:
    log(2, "Whisper 转写 + 纠错")
    t = cfg["transcribe"]
    cmd = [sys.executable, "02-transcribe/transcribe.py",
           "--input", str(video), "--engine", t.get("engine", "auto")]
    if t.get("fix"):
        cmd.append("--fix")
    run(cmd)
    txt = newest(f"{video.stem}_fixed.txt") or newest(f"{video.stem}.txt")
    print(f"→ {txt}")
    return txt


def step3_rewrite(cfg, transcript: Path) -> Path:
    log(3, "仿写成你的风格")
    run([sys.executable, "03-rewrite/rewrite.py",
         "--input", str(transcript),
         "--duration", str(cfg["rewrite"]["duration"])])
    rw = newest("*_rewrite_*.txt")
    print(f"→ {rw}")
    return rw


def step4_voice(cfg, script: Path) -> Path | None:
    log(4, "声音克隆 IndexTTS2")
    v = cfg.get("voice", {})
    if not v.get("enabled"):
        print("voice.enabled=false，跳过配音（成品将是无声字幕动画）")
        return None
    OUT.mkdir(exist_ok=True)
    voice_out = OUT / "voice.wav"
    run([sys.executable, "04-voice-clone/tts_indextts2.py",
         "--ref", v["ref_audio"], "--text-file", str(script),
         "--out", str(voice_out)])
    print(f"→ {voice_out}")
    return voice_out


def step5_render(cfg, script: Path, audio: Path | None) -> Path:
    log(5, "字幕动画渲染（Remotion）+ 可选对口型（LatentSync）")
    OUT.mkdir(exist_ok=True)
    remotion = ROOT / "05-render-remotion"

    # 确保依赖已装
    if not (remotion / "node_modules").exists():
        run(["npm", "install"], cwd=str(remotion))

    # 仿写稿 → props.json
    props = remotion / "props.json"
    build_cmd = [sys.executable, "build_props.py",
                 "--input", str(script), "--out", str(props)]
    if audio:
        build_cmd += ["--audio", str(audio)]
    run(build_cmd, cwd=str(remotion))

    # 渲染
    video_out = OUT / "video.mp4"
    run(["bash", "render.sh", str(video_out), str(props)], cwd=str(remotion))

    # 可选：LatentSync 对口型（需真人底片 + GPU）
    ls = cfg.get("lipsync", {})
    if ls.get("enabled") and ls.get("face_video") and audio:
        lip_out = OUT / "lipsync.mp4"
        run([sys.executable, "latentsync.py",
             "--video", ls["face_video"], "--audio", str(audio),
             "--out", str(lip_out)], cwd=str(remotion))
        print(f"→ 对口型成品 {lip_out}")
        return lip_out

    print(f"→ {video_out}")
    return video_out


def step6_distribute(cfg, video: Path, script: Path):
    log(6, "一键多平台分发")
    d = cfg.get("distribute", {})
    if not d.get("enabled"):
        print("distribute.enabled=false，跳过发布。")
        print(f"成品已就绪: {video}（配好平台 cookie 后开启自动分发）")
        return
    # 标题：优先配置，否则取仿写稿最后一行（rewrite 会附标题）
    title = d.get("title") or guess_title(script)
    cmd = [sys.executable, "06-distribute/distribute.py",
           "--video", str(video), "--title", title,
           "--platforms", *d.get("platforms", ["douyin"]),
           "--tags", *d.get("tags", ["AI"])]
    run(cmd)


def guess_title(script: Path) -> str:
    lines = [l.strip() for l in script.read_text(encoding="utf-8").splitlines() if l.strip()]
    # 取最后一行非空（rewrite 提示词要求末尾输出标题）
    for l in reversed(lines):
        clean = re.sub(r"[（(]\s*\d+\.?\d*\s*s?\s*[）)]", "", l).strip()
        if 4 <= len(clean) <= 40:
            return clean
    return "AI落地 · 高阳纺织"


# ── 主流程 ───────────────────────────────────────────────────
STEPS = [None, "download", "transcribe", "rewrite", "voice", "render", "distribute"]


def main():
    p = argparse.ArgumentParser(description="数字人短视频智能体")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--from", dest="start", type=int, default=1, help="从第几步开始(1-6)")
    p.add_argument("--only", type=int, help="只跑某一步")
    p.add_argument("--url", help="覆盖 download.url")
    p.add_argument("--video", help="跳过下载，直接用本地视频")
    p.add_argument("--script", help="跳过前3步，直接用现成文案 txt")
    args = p.parse_args()

    cfg_path = ROOT / args.config
    if not cfg_path.exists():
        sys.exit(f"配置不存在：{cfg_path}\n请先: cp config.example.yaml config.yaml")
    cfg = load_config(cfg_path)
    apply_llm_env(cfg)
    if args.url:
        cfg["download"]["url"] = args.url

    start = args.only or args.start
    end = args.only or 6

    # 状态在步骤间传递
    video = Path(args.video) if args.video else None
    transcript = None
    script = Path(args.script) if args.script else None
    audio = None
    final_video = None

    if start <= 1 <= end and not video and not script:
        video = step1_download(cfg)
    if start <= 2 <= end and not script:
        transcript = step2_transcribe(cfg, video)
    if start <= 3 <= end and not script:
        script = step3_rewrite(cfg, transcript)
    if script is None:
        script = newest("*_rewrite_*.txt")
    if start <= 4 <= end:
        audio = step4_voice(cfg, script)
    if start <= 5 <= end:
        if audio is None:
            a = OUT / "voice.wav"
            audio = a if a.exists() else None
        final_video = step5_render(cfg, script, audio)
    if start <= 6 <= end:
        if final_video is None:
            final_video = OUT / "video.mp4"
        step6_distribute(cfg, final_video, script)

    print(f"\n{'='*60}\n✅ 智能体流程结束")
    if final_video:
        print(f"   成品视频: {final_video}")
    print('='*60)


if __name__ == "__main__":
    main()
