#!/usr/bin/env python3
"""
数字人渲染抽象层 —— 支持多种后端，统一接口。

支持的后端：
  mock    - 直接返回字幕动画视频（无真人脸），用于测试/无 GPU 环境
  heygem  - HeyGem 开源自托管（需 GPU + Docker，一次性部署）
  guiji   - 硅基智能云端 API（RMB 充值，按分钟计费，无需 GPU）
  tencentyy - 腾讯智影 API

用法：
  python digital_human.py \
      --backend heygem \
      --audio out/voice.wav \
      --avatar avatars/default.mp4 \
      --out out/digital_human.mp4
"""

from __future__ import annotations
import argparse
import os
import sys
import time
from pathlib import Path


# ─── 后端接口 ─────────────────────────────────────────────────

class DigitalHumanBackend:
    """所有后端实现这个接口"""

    def render(
        self,
        audio_path: Path,
        avatar_video: Path | None,
        out_path: Path,
        **kwargs,
    ) -> Path:
        raise NotImplementedError


# ─── Mock 后端（直接用字幕动画视频） ───────────────────────────

class MockBackend(DigitalHumanBackend):
    """
    无数字人脸的 fallback：把已有的字幕动画视频直接复制过来。
    用于本地测试或无 GPU 时的完整流程验证。
    """

    def render(self, audio_path, avatar_video, out_path, subtitle_video=None, **kwargs):
        import shutil
        src = subtitle_video or avatar_video
        if src and Path(src).exists():
            shutil.copy2(src, out_path)
            print(f"[mock] 直接复制字幕视频 → {out_path}")
        else:
            # 创建一个静态黑色视频（ffmpeg）
            _ffmpeg_silent_video(out_path, audio_path)
            print(f"[mock] 生成占位视频 → {out_path}")
        return out_path


def _ffmpeg_silent_video(out_path: Path, audio_path: Path | None):
    import subprocess
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=30",
    ]
    if audio_path and Path(audio_path).exists():
        dur = _get_duration(audio_path)
        cmd += ["-i", str(audio_path), "-t", str(dur), "-c:a", "aac", "-shortest"]
    else:
        cmd += ["-t", "10"]
    cmd += ["-c:v", "libx264", str(out_path)]
    subprocess.run(cmd, check=True, capture_output=True)


def _get_duration(path: Path) -> float:
    import subprocess, json
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", str(path)],
        capture_output=True, text=True
    )
    for s in json.loads(r.stdout).get("streams", []):
        if s.get("duration"):
            return float(s["duration"])
    return 30.0


# ─── HeyGem 后端（开源自托管） ─────────────────────────────────

class HeyGemBackend(DigitalHumanBackend):
    """
    HeyGem 开源数字人（https://github.com/GuijiAI/HeyGen）
    Docker 部署在本地或 GPU 服务器上，REST API 调用。

    环境变量：
      HEYGEM_URL  - HeyGem 服务地址（默认 http://localhost:8080）
    """

    def __init__(self):
        self.base = os.environ.get("HEYGEM_URL", "http://localhost:8080").rstrip("/")

    def render(self, audio_path: Path, avatar_video: Path, out_path: Path, **kwargs) -> Path:
        import requests, json, shutil, tempfile

        print(f"[heygem] 提交任务：avatar={avatar_video} audio={audio_path}")

        # 1. 上传素材
        with open(avatar_video, "rb") as vf, open(audio_path, "rb") as af:
            upload_r = requests.post(
                f"{self.base}/api/v1/task",
                files={"video": vf, "audio": af},
                timeout=60,
            )
        upload_r.raise_for_status()
        task_id = upload_r.json()["task_id"]
        print(f"[heygem] task_id={task_id}，等待渲染…")

        # 2. 轮询状态（最多等 10 分钟）
        for _ in range(120):
            time.sleep(5)
            status_r = requests.get(f"{self.base}/api/v1/task/{task_id}", timeout=10)
            status_r.raise_for_status()
            data = status_r.json()
            state = data.get("status", "")
            print(f"[heygem] 状态: {state}")
            if state == "done":
                video_url = data["video_url"]
                break
            elif state == "failed":
                raise RuntimeError(f"HeyGem 渲染失败: {data}")
        else:
            raise TimeoutError("HeyGem 渲染超时（10分钟）")

        # 3. 下载结果
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(video_url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
        print(f"[heygem] 下载完成 → {out_path}")
        return out_path


# ─── 硅基智能后端（云端 API，RMB 充值） ─────────────────────────

class GuijiBackend(DigitalHumanBackend):
    """
    硅基智能数字人 API（https://www.guiji.ai）
    支持支付宝/微信充值，按分钟计费（约 0.3 元/分钟）。

    环境变量：
      GUIJI_API_KEY  - 硅基智能 API Key
      GUIJI_AVATAR_ID - 数字人形象 ID（在控制台选好记下来）
    """

    API_BASE = "https://openapi.guiji.ai"

    def __init__(self):
        self.api_key = os.environ.get("GUIJI_API_KEY", "")
        self.avatar_id = os.environ.get("GUIJI_AVATAR_ID", "")
        if not self.api_key:
            raise ValueError("请设置环境变量 GUIJI_API_KEY（硅基智能 API Key）")

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"}

    def render(self, audio_path: Path, avatar_video: Path | None, out_path: Path,
               text: str = "", **kwargs) -> Path:
        import requests

        print(f"[guiji] 提交数字人任务…")

        # 1. 上传音频获取 audio_url
        with open(audio_path, "rb") as f:
            up_r = requests.post(
                f"{self.API_BASE}/v1/upload",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": f},
                timeout=60,
            )
        up_r.raise_for_status()
        audio_url = up_r.json()["url"]

        # 2. 创建数字人视频任务
        payload = {
            "avatar_id": self.avatar_id,
            "audio_url": audio_url,
            "resolution": "1080x1920",  # 竖屏 9:16
        }
        create_r = requests.post(
            f"{self.API_BASE}/v1/video/create",
            json=payload, headers=self._headers(), timeout=30,
        )
        create_r.raise_for_status()
        task_id = create_r.json()["task_id"]
        print(f"[guiji] task_id={task_id}，等待渲染…")

        # 3. 轮询
        for _ in range(180):
            time.sleep(5)
            qr = requests.get(
                f"{self.API_BASE}/v1/video/{task_id}",
                headers=self._headers(), timeout=15,
            )
            qr.raise_for_status()
            d = qr.json()
            state = d.get("status", "")
            print(f"[guiji] 状态: {state}")
            if state == "completed":
                video_url = d["video_url"]
                break
            elif state in ("failed", "error"):
                raise RuntimeError(f"硅基智能渲染失败: {d}")
        else:
            raise TimeoutError("硅基智能渲染超时（15分钟）")

        # 4. 下载
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(video_url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
        print(f"[guiji] 下载完成 → {out_path}")
        return out_path


# ─── 后端工厂 ─────────────────────────────────────────────────

BACKENDS: dict[str, type[DigitalHumanBackend]] = {
    "mock":    MockBackend,
    "heygem":  HeyGemBackend,
    "guiji":   GuijiBackend,
}


def get_backend(name: str) -> DigitalHumanBackend:
    cls = BACKENDS.get(name)
    if cls is None:
        raise ValueError(f"未知后端: {name}，可选: {list(BACKENDS)}")
    return cls()


# ─── 合并数字人 + 字幕轨道 ─────────────────────────────────────

def merge_with_subtitles(dh_video: Path, subtitle_video: Path, out_path: Path) -> Path:
    """
    把数字人（pip 小窗，右下角）叠加到字幕背景视频上。
    数字人占画面高度 40%，右下角圆角遮罩。
    """
    import subprocess
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # 数字人缩放到 400x711，定位在右下角（留 30px 边距）
    filter_complex = (
        "[0:v]scale=1080:1920[bg];"
        "[1:v]scale=400:-1,format=yuva420p[dh];"
        "[bg][dh]overlay=x=650:y=1140:shortest=1[out]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", str(subtitle_video),
        "-i", str(dh_video),
        "-filter_complex", filter_complex,
        "-map", "[out]", "-map", "1:a?",
        "-c:v", "libx264", "-crf", "20",
        "-c:a", "aac", "-shortest",
        str(out_path)
    ]
    subprocess.run(cmd, check=True)
    print(f"[merge] 合并完成 → {out_path}")
    return out_path


# ─── CLI ─────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="数字人渲染（支持 mock/heygem/guiji）")
    p.add_argument("--backend", default="mock",
                   choices=list(BACKENDS), help="渲染后端")
    p.add_argument("--audio", required=True, help="配音 wav/mp3 文件")
    p.add_argument("--avatar", default=None, help="数字人底片视频（heygem用）")
    p.add_argument("--subtitle-video", default=None,
                   help="字幕动画视频（用于 mock 或合并叠加）")
    p.add_argument("--out", required=True, help="输出 mp4 路径")
    p.add_argument("--merge", action="store_true",
                   help="将数字人叠加到字幕视频（pip 小窗模式）")
    args = p.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    backend = get_backend(args.backend)
    dh_video = backend.render(
        audio_path=Path(args.audio),
        avatar_video=Path(args.avatar) if args.avatar else None,
        out_path=out if not args.merge else out.with_suffix(".dh_raw.mp4"),
        subtitle_video=args.subtitle_video,
    )

    if args.merge and args.subtitle_video:
        merge_with_subtitles(dh_video, Path(args.subtitle_video), out)

    print(f"\n✅ 数字人视频已生成: {out}")


if __name__ == "__main__":
    main()
