#!/usr/bin/env python3
"""
把仿写稿（口播文案）自动转换成 Remotion 渲染用的 props.json
用 Claude 切分字幕、估算每句时间轴（30fps）。

用法:
  python build_props.py --input ../transcripts/script_rewrite_60s.txt --out props.json
  # 带配音音轨（来自第4步），并按音频实际时长对齐
  python build_props.py --input script.txt --audio ../out/voice.wav --out props.json
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCHEMA_PROMPT = """你是短视频字幕排版助手。把下面这段口播文案切分成适合竖屏短视频的字幕条，并输出严格的 JSON。

要求：
1. 每条字幕 8-16 个汉字，过长的句子拆成多条；
2. 按中文口播 4.5 字/秒估算每条的显示时长；
3. 字段说明（30fps）：
   - text: 字幕文字（去掉所有时间戳标注如（3s））
   - from: 开始帧 = 上一条结束帧 + 约9帧间隔
   - durationInFrames: 持续帧数 = round(字数 / 4.5 * 30)，最少30
   - highlight: 可选，这条里最该高亮的1个关键词（金额/数字/产品名/动作词），没有就省略
4. 顶部 pills 固定为流程五步（如果文案是讲流程的话），否则省略 pills。
5. tagLine 用 "AI落地 · 高阳纺织专属"。

只输出 JSON，不要解释，不要 markdown 代码块。结构：
{
  "tagLine": "...",
  "pills": [{"text":"① 下载","color":"#FF6B6B"}, ...] 或省略,
  "segments": [{"text":"...","from":0,"durationInFrames":75,"highlight":"..."}, ...]
}

口播文案：
\"\"\"
{script}
\"\"\"
"""

PILL_COLORS = ["#FF6B6B", "#FFA500", "#4ECDC4", "#45B7D1", "#96CEB4"]


def get_audio_duration(audio_path: Path) -> float | None:
    """用 ffprobe 拿音频时长（秒）"""
    try:
        out = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path),
        ], text=True)
        return float(out.strip())
    except Exception:
        return None


def build_with_claude(script: str) -> dict:
    try:
        import anthropic
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "anthropic", "-q"])
        import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("请设置 ANTHROPIC_API_KEY")

    client = anthropic.Anthropic(api_key=api_key)
    print("[Claude] 生成字幕时间轴...")
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": SCHEMA_PROMPT.replace("{script}", script)}],
    )
    text = msg.content[0].text.strip()
    # 容错：剥掉可能的代码块
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()
    return json.loads(text)


def fallback_parse(script: str) -> dict:
    """没有 API key 时的本地兜底：按行切分，按字数估时长"""
    print("[本地兜底] 无 API key，按行切分文案...")
    lines = []
    for ln in script.splitlines():
        ln = re.sub(r"[（(]\s*\d+\.?\d*\s*s?\s*[）)]", "", ln).strip()
        ln = re.sub(r"^[#\d、.\-—\s]+", "", ln)  # 去序号/标题符号
        if 2 <= len(ln) <= 40:
            lines.append(ln)
    segments = []
    cursor = 0
    for ln in lines:
        dur = max(30, round(len(ln) / 4.5 * 30))
        segments.append({"text": ln, "from": cursor, "durationInFrames": dur})
        cursor += dur + 9
    return {"tagLine": "AI落地 · 高阳纺织专属", "segments": segments}


def rescale_to_audio(props: dict, audio_sec: float):
    """把字幕时间轴线性缩放到配音实际时长"""
    segs = props["segments"]
    if not segs:
        return
    last_end = max(s["from"] + s["durationInFrames"] for s in segs)
    target = audio_sec * 30
    factor = target / last_end if last_end else 1.0
    for s in segs:
        s["from"] = round(s["from"] * factor)
        s["durationInFrames"] = round(s["durationInFrames"] * factor)
    print(f"[对齐配音] 缩放系数 {factor:.3f}，总时长 → {audio_sec:.1f}s")


def main():
    p = argparse.ArgumentParser(description="仿写稿 → Remotion props.json")
    p.add_argument("--input", required=True, help="仿写稿 txt")
    p.add_argument("--audio", help="可选：配音音频，用于对齐时长并加音轨")
    p.add_argument("--out", default="props.json", help="输出 props.json")
    p.add_argument("--no-llm", action="store_true", help="不调用 Claude，纯本地切分")
    args = p.parse_args()

    script = Path(args.input).read_text(encoding="utf-8")

    if args.no_llm or not os.environ.get("ANTHROPIC_API_KEY"):
        props = fallback_parse(script)
    else:
        try:
            props = build_with_claude(script)
        except Exception as e:
            print(f"[Claude 失败，转本地兜底] {e}")
            props = fallback_parse(script)

    # 修正 pills 颜色（防止 Claude 没给颜色）
    for i, pill in enumerate(props.get("pills", [])):
        pill.setdefault("color", PILL_COLORS[i % len(PILL_COLORS)])

    # 配音：对齐 + 挂音轨
    if args.audio:
        audio_path = Path(args.audio)
        dur = get_audio_duration(audio_path)
        if dur:
            rescale_to_audio(props, dur)
        # Remotion 从 public/ 读静态文件
        public_dir = Path(__file__).parent / "public"
        public_dir.mkdir(exist_ok=True)
        import shutil
        dst = public_dir / audio_path.name
        if audio_path.resolve() != dst.resolve():
            shutil.copy(audio_path, dst)
        props["audioSrc"] = audio_path.name

    out_path = Path(args.out)
    out_path.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 已生成 {out_path}（{len(props['segments'])} 条字幕）")


if __name__ == "__main__":
    main()
