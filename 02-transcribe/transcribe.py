#!/usr/bin/env python3
"""
第2步：视频转文字 + AI纠错
优先用 FunASR/SenseVoice（国内，模型从 ModelScope 下，中文效果更好）
无 GPU 时自动退回 OpenAI Whisper API 或 faster-whisper(CPU)

用法:
  python transcribe.py --input ../downloads/video.mp4
  python transcribe.py --input ../downloads/  # 批量处理目录
  python transcribe.py --input video.mp4 --fix  # 转写 + Claude API 纠错
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent / "transcripts"


# ─── 依赖检测 ────────────────────────────────────────────────────────────────

def install(pkg: str):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])


def has_gpu() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


# ─── 音频提取 ────────────────────────────────────────────────────────────────

def extract_audio(video_path: Path) -> Path:
    """用 ffmpeg 从视频提取 16kHz 单声道 wav"""
    wav_path = video_path.with_suffix(".wav")
    if wav_path.exists():
        return wav_path
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-ar", "16000", "-ac", "1", "-vn",
        str(wav_path),
    ]
    print(f"[ffmpeg] 提取音频: {video_path.name}")
    subprocess.run(cmd, check=True, capture_output=True)
    return wav_path


# ─── 转写引擎 ────────────────────────────────────────────────────────────────

def transcribe_funasr(wav_path: Path) -> str:
    """
    FunASR / SenseVoice（推荐，魔搭下载，中文效果最好）
    需要 GPU 或耐心等 CPU 跑
    pip install funasr modelscope
    """
    try:
        from funasr import AutoModel
    except ImportError:
        install("funasr")
        install("modelscope")
        from funasr import AutoModel

    print("[FunASR] 加载 SenseVoiceSmall 模型（首次从 ModelScope 下载）...")
    model = AutoModel(
        model="iic/SenseVoiceSmall",
        trust_remote_code=True,
        remote_code="./model.py",
    )
    result = model.generate(
        input=str(wav_path),
        cache={},
        language="zh",
        use_itn=True,
        batch_size_s=60,
    )
    text = result[0]["text"]
    # SenseVoice 输出带情绪标签，清理掉
    import re
    text = re.sub(r"<[^>]+>", "", text).strip()
    return text


def transcribe_faster_whisper(wav_path: Path) -> str:
    """
    faster-whisper CPU 版（无 GPU 备选，速度慢但不用联网）
    pip install faster-whisper
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        install("faster-whisper")
        from faster_whisper import WhisperModel

    print("[faster-whisper] 加载 large-v3 模型（CPU 模式）...")
    model = WhisperModel("large-v3", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(wav_path), language="zh", beam_size=5)
    return "".join(seg.text for seg in segments)


def transcribe_openai_api(wav_path: Path) -> str:
    """
    OpenAI Whisper API（最省本地资源，需要 API key 和网络）
    OPENAI_API_KEY 从环境变量读取
    """
    try:
        from openai import OpenAI
    except ImportError:
        install("openai")
        from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("请设置 OPENAI_API_KEY 环境变量")

    client = OpenAI(api_key=api_key)
    print("[OpenAI Whisper API] 上传音频...")
    with open(wav_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="zh",
        )
    return result.text


# ─── AI 纠错 ─────────────────────────────────────────────────────────────────

FIX_PROMPT = """你是一个专业文案校对助手。下面是一段语音转写稿，可能有以下问题：
1. 同音字、近音字错误（如"的地得"混用、"帝"写成"第"等）
2. 专业词汇识别错误（如 AI、SaaS、抖音、纺织类术语）
3. 缺少标点符号
4. 数字口语化（比如"一百二十三"应为"123"）

请在**保留原意和口语风格**的前提下，只改错字和加标点，不改句式，不扩写。
直接输出修正后的文本，不要解释。

原文：
{text}"""


def fix_with_claude(text: str) -> str:
    """用 Claude API 纠错（需要 ANTHROPIC_API_KEY）"""
    try:
        import anthropic
    except ImportError:
        install("anthropic")
        import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("请设置 ANTHROPIC_API_KEY 环境变量")

    client = anthropic.Anthropic(api_key=api_key)
    print("[Claude] 纠错中...")
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": FIX_PROMPT.format(text=text)}],
    )
    return message.content[0].text


# ─── 主流程 ──────────────────────────────────────────────────────────────────

def process_one(video_path: Path, engine: str, fix: bool) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_txt = OUTPUT_DIR / (video_path.stem + ".txt")
    out_fixed = OUTPUT_DIR / (video_path.stem + "_fixed.txt")

    # 提取音频
    wav_path = extract_audio(video_path)

    # 转写
    if engine == "funasr":
        text = transcribe_funasr(wav_path)
    elif engine == "faster-whisper":
        text = transcribe_faster_whisper(wav_path)
    elif engine == "openai":
        text = transcribe_openai_api(wav_path)
    else:
        # 自动选择
        if has_gpu():
            text = transcribe_funasr(wav_path)
        else:
            print("未检测到 GPU，使用 faster-whisper CPU 模式（较慢）")
            text = transcribe_faster_whisper(wav_path)

    out_txt.write_text(text, encoding="utf-8")
    print(f"[转写完成] {out_txt}")

    if fix:
        fixed = fix_with_claude(text)
        out_fixed.write_text(fixed, encoding="utf-8")
        print(f"[纠错完成] {out_fixed}")
        return out_fixed

    return out_txt


def main():
    parser = argparse.ArgumentParser(description="视频转文字 + 纠错")
    parser.add_argument("--input", required=True, help="视频文件或目录路径")
    parser.add_argument(
        "--engine",
        choices=["auto", "funasr", "faster-whisper", "openai"],
        default="auto",
        help="转写引擎（默认自动选择）",
    )
    parser.add_argument("--fix", action="store_true", help="转写后用 Claude API 纠错")
    args = parser.parse_args()

    input_path = Path(args.input)
    if input_path.is_dir():
        videos = list(input_path.glob("*.mp4")) + list(input_path.glob("*.mov"))
        print(f"批量处理 {len(videos)} 个视频")
        for v in videos:
            process_one(v, args.engine, args.fix)
    elif input_path.is_file():
        process_one(input_path, args.engine, args.fix)
    else:
        print(f"路径不存在: {input_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
