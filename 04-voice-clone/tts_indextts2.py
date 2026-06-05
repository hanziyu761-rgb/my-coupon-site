#!/usr/bin/env python3
"""
第4步：声音克隆 —— IndexTTS2 用你自己的声音念文案
仓库:  https://github.com/index-tts/index-tts
模型:  魔搭 IndexTeam/IndexTTS-2  （也可 HuggingFace IndexTeam/IndexTTS-2）
显存:  最低 6GB，推荐 8GB+（无 GPU 跑不动，请用 AutoDL 等租 GPU 实例）

用法:
  # 首次在 GPU 机器上准备模型（自动从魔搭下载）
  python tts_indextts2.py --setup

  # 用你的参考音频克隆，把文案念出来
  python tts_indextts2.py \
      --ref my_voice.wav \
      --text-file ../transcripts/script.txt \
      --out ../out/voice.wav
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).parent / "index-tts"
MODEL_DIR = Path(__file__).parent / "checkpoints"


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, **kw)


def check_gpu():
    try:
        import torch
        if not torch.cuda.is_available():
            print("⚠️  未检测到 CUDA GPU。IndexTTS2 需要 NVIDIA GPU（≥6GB 显存）。")
            print("    建议：AutoDL / 揽睿 / 恒源云 租一张 3090/4090，按小时计费。")
            return False
        name = torch.cuda.get_device_name(0)
        mem = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"✅ GPU: {name}  显存: {mem:.1f}GB")
        return True
    except ImportError:
        print("⚠️  未安装 torch。请先在 GPU 机器上安装 PyTorch (CUDA 版)。")
        return False


def setup():
    """克隆仓库 + 安装依赖 + 下载模型权重"""
    if not REPO_DIR.exists():
        run(["git", "clone", "https://github.com/index-tts/index-tts.git", str(REPO_DIR)])
    run([sys.executable, "-m", "pip", "install", "-e", str(REPO_DIR)])
    run([sys.executable, "-m", "pip", "install", "modelscope", "-q"])

    # 从魔搭下载模型（国内不被墙）
    MODEL_DIR.mkdir(exist_ok=True)
    print("从 ModelScope 下载 IndexTTS-2 模型权重...")
    from modelscope import snapshot_download
    snapshot_download("IndexTeam/IndexTTS-2", local_dir=str(MODEL_DIR))
    print(f"✅ 模型已就绪: {MODEL_DIR}")


def synthesize(ref_audio: Path, text: str, out_path: Path):
    """零样本声音克隆合成"""
    sys.path.insert(0, str(REPO_DIR))
    try:
        from indextts.infer_v2 import IndexTTS2
    except ImportError:
        print("未找到 IndexTTS2，请先运行: python tts_indextts2.py --setup")
        sys.exit(1)

    print(f"加载模型 ({MODEL_DIR})...")
    tts = IndexTTS2(
        cfg_path=str(MODEL_DIR / "config.yaml"),
        model_dir=str(MODEL_DIR),
        use_fp16=True,   # 省显存
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"用参考音频 {ref_audio.name} 克隆声音，合成 {len(text)} 字...")
    tts.infer(
        spk_audio_prompt=str(ref_audio),  # 你的参考录音（3-10秒清晰人声）
        text=text,
        output_path=str(out_path),
        verbose=True,
    )
    print(f"✅ 已生成配音: {out_path}")


def main():
    p = argparse.ArgumentParser(description="IndexTTS2 声音克隆")
    p.add_argument("--setup", action="store_true", help="安装环境 + 下载模型")
    p.add_argument("--ref", help="参考音频（你的声音，3-10秒 wav）")
    p.add_argument("--text", help="要合成的文字")
    p.add_argument("--text-file", help="从文件读取文字")
    p.add_argument("--out", default="../out/voice.wav", help="输出音频路径")
    args = p.parse_args()

    if args.setup:
        check_gpu()
        setup()
        return

    if not check_gpu():
        sys.exit(1)

    if not args.ref:
        p.error("--ref 参考音频是必须的")

    text = args.text
    if args.text_file:
        # 去掉仿写稿里的时间戳标注 (Ns) 和标题行
        import re
        raw = Path(args.text_file).read_text(encoding="utf-8")
        lines = [re.sub(r"[（(]\s*\d+\.?\d*\s*s?\s*[）)]", "", ln).strip()
                 for ln in raw.splitlines() if ln.strip()]
        text = " ".join(lines)
    if not text:
        p.error("需要 --text 或 --text-file")

    synthesize(Path(args.ref), text, Path(args.out))


if __name__ == "__main__":
    main()
