#!/usr/bin/env python3
"""
离线兜底语音合成 —— 无 GPU、无网络也能出声。

优先级（自动探测，能用哪个用哪个）：
  1. edge-tts   微软在线语音，最自然（需联网，部分环境被墙）
  2. espeak-ng  纯离线，机器音，永远可用兜底

⚠️ 注意：这两个都不是「你本人的声音」。要克隆你自己的声音，
   用 tts_indextts2.py（需 GPU）或剪映/硅基智能的声音克隆。
   本脚本只用于无 GPU/无 API 时让流水线端到端跑通并产出音轨。

用法：
  python tts_offline.py --text-file script.txt --out voice.wav
  python tts_offline.py --text "测试一句" --out voice.wav --voice zh-CN-XiaoxiaoNeural
"""
from __future__ import annotations
import argparse
import re
import subprocess
import sys
from pathlib import Path


def strip_script(text: str) -> str:
    """去掉时间戳/标题行，拼成可朗读的纯文本"""
    out = []
    for l in text.splitlines():
        l = l.strip()
        if not l or l.startswith("标题") or "带货口播脚本" in l:
            continue
        l = re.sub(r"[（(].*?[）)]", "", l).strip()   # 去时间戳
        l = re.sub(r"[#＃].*$", "", l).strip()          # 去话题标签
        if l:
            out.append(l)
    return "。".join(out)


def tts_edge(text: str, out: Path, voice: str = "zh-CN-XiaoxiaoNeural") -> bool:
    """微软在线 TTS，最自然。失败返回 False。"""
    try:
        import ssl, asyncio
        import edge_tts.communicate as cm
        # 部分企业代理用自签证书，放宽校验（仅本地合成，无敏感数据）
        cm._SSL_CTX = ssl._create_unverified_context()
        import edge_tts

        mp3 = out.with_suffix(".mp3")

        async def go():
            c = edge_tts.Communicate(text, voice)
            await c.save(str(mp3))

        asyncio.run(go())
        if mp3.exists() and mp3.stat().st_size > 0:
            # 转 wav
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(mp3), str(out)],
                check=True, capture_output=True,
            )
            mp3.unlink(missing_ok=True)
            print(f"[edge-tts] ✅ {voice} → {out}")
            return True
    except Exception as e:
        print(f"[edge-tts] 不可用（{type(e).__name__}），改用离线引擎…")
    return False


def tts_espeak(text: str, out: Path, speed: int = 150) -> bool:
    """espeak-ng 纯离线，机器音兜底。"""
    txt_file = out.with_suffix(".txt")
    txt_file.write_text(text, encoding="utf-8")
    try:
        subprocess.run(
            ["espeak-ng", "-v", "cmn", "-s", str(speed),
             "-f", str(txt_file), "-w", str(out)],
            check=True, capture_output=True,
        )
        print(f"[espeak-ng] ✅ 离线机器音 → {out}")
        return True
    except FileNotFoundError:
        print("[espeak-ng] 未安装。请: sudo apt-get install -y espeak-ng")
        return False
    finally:
        txt_file.unlink(missing_ok=True)


def synth(text: str, out: Path, voice: str = "zh-CN-XiaoxiaoNeural",
          prefer_offline: bool = False) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    text = strip_script(text)
    if not prefer_offline and tts_edge(text, out, voice):
        return out
    if tts_espeak(text, out):
        return out
    sys.exit("❌ 所有语音引擎都不可用")


def main():
    p = argparse.ArgumentParser(description="离线兜底语音合成")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--text")
    g.add_argument("--text-file")
    p.add_argument("--out", required=True)
    p.add_argument("--voice", default="zh-CN-XiaoxiaoNeural",
                   help="edge-tts 音色，如 zh-CN-YunxiNeural(男)")
    p.add_argument("--offline", action="store_true",
                   help="强制用离线 espeak（不尝试联网）")
    args = p.parse_args()

    text = args.text or Path(args.text_file).read_text(encoding="utf-8")
    synth(text, Path(args.out), args.voice, prefer_offline=args.offline)


if __name__ == "__main__":
    main()
