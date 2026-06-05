#!/usr/bin/env python3
"""
第5步（对口型部分）：LatentSync —— 把配音对到真人口播视频的嘴型
仓库:  https://github.com/bytedance/LatentSync
显存:  原版约 20GB；ComfyUI Wrapper 版可压到 ~6.5GB
适用:  你有一段真人出镜视频时用。纯文字动画视频不需要这步。

⚠️ 中文口型 LatentSync 偏弱，可横向对比 MuseTalk(腾讯) / EchoMimic(蚂蚁) / Wav2Lip。

用法:
  python latentsync.py --setup
  python latentsync.py --video face.mp4 --audio ../out/voice.wav --out ../out/lipsync.mp4
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).parent / "LatentSync"


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, **kw)


def check_gpu():
    try:
        import torch
        if not torch.cuda.is_available():
            print("⚠️  LatentSync 需要 NVIDIA GPU。无 GPU 请用 AutoDL 等租实例。")
            return False
        mem = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"✅ GPU 显存: {mem:.1f}GB（原版需 ~20GB，Wrapper 版 ~6.5GB）")
        return True
    except ImportError:
        print("⚠️  未安装 torch（CUDA 版）。")
        return False


def setup():
    if not REPO_DIR.exists():
        run(["git", "clone", "https://github.com/bytedance/LatentSync.git", str(REPO_DIR)])
    # 官方提供 setup_env.sh 安装依赖并下载权重（从 HF；国内可能需镜像 HF_ENDPOINT）
    print("运行 LatentSync 官方环境脚本（首次较慢）...")
    run(["bash", "setup_env.sh"], cwd=str(REPO_DIR))
    print("✅ LatentSync 就绪")


def inference(video: Path, audio: Path, out: Path):
    if not REPO_DIR.exists():
        print("请先运行: python latentsync.py --setup")
        sys.exit(1)
    out.parent.mkdir(parents=True, exist_ok=True)
    # 调用官方推理脚本
    run([
        sys.executable, "-m", "scripts.inference",
        "--unet_config_path", "configs/unet/stage2.yaml",
        "--inference_ckpt_path", "checkpoints/latentsync_unet.pt",
        "--video_path", str(video.resolve()),
        "--audio_path", str(audio.resolve()),
        "--video_out_path", str(out.resolve()),
        "--inference_steps", "20",
        "--guidance_scale", "1.5",
    ], cwd=str(REPO_DIR))
    print(f"✅ 对口型完成: {out}")


def main():
    p = argparse.ArgumentParser(description="LatentSync 对口型")
    p.add_argument("--setup", action="store_true")
    p.add_argument("--video", help="真人口播底片视频")
    p.add_argument("--audio", help="配音音频（来自第4步）")
    p.add_argument("--out", default="../out/lipsync.mp4")
    args = p.parse_args()

    if args.setup:
        check_gpu()
        setup()
        return
    if not check_gpu():
        sys.exit(1)
    if not (args.video and args.audio):
        p.error("--video 和 --audio 都是必须的")
    inference(Path(args.video), Path(args.audio), Path(args.out))


if __name__ == "__main__":
    main()
