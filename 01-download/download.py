#!/usr/bin/env python3
"""
第1步：下载对标账号视频
支持抖音/TikTok (f2) 和 YouTube/其他平台 (yt-dlp)
用法:
  python download.py --platform douyin --user <主页URL或用户ID> --limit 10
  python download.py --platform youtube --url <视频URL>
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "downloads"


def ensure_deps():
    pkgs = []
    try:
        import yt_dlp  # noqa
    except ImportError:
        pkgs.append("yt-dlp")
    try:
        import f2  # noqa
    except ImportError:
        pkgs.append("f2")
    if pkgs:
        print(f"安装依赖: {' '.join(pkgs)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + pkgs)


def download_youtube(url: str, output_dir: Path):
    """用 yt-dlp 下载单条或播放列表"""
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", str(output_dir / "%(uploader)s_%(id)s.%(ext)s"),
        "--write-info-json",
        "--no-playlist",  # 单条，去掉此参数则下整个播放列表
        url,
    ]
    print(f"[yt-dlp] 下载: {url}")
    subprocess.run(cmd, check=True)


def download_douyin(user_url: str, limit: int, output_dir: Path):
    """
    用 f2 批量下载抖音账号视频
    f2 文档: https://github.com/Johnserf-Seed/f2
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "f2", "douyin",
        "-u", user_url,
        "--max-count", str(limit),
        "--path", str(output_dir),
        "--naming", "{create}_{desc}",
    ]
    print(f"[f2] 下载抖音账号: {user_url}，最多 {limit} 条")
    print("注意: 首次运行需要先执行 `f2 douyin -h` 查看配置说明，并准备好 cookie")
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(description="对标视频下载器")
    parser.add_argument("--platform", choices=["youtube", "douyin", "bilibili"], required=True)
    parser.add_argument("--url", help="单条视频 URL（youtube/bilibili）")
    parser.add_argument("--user", help="账号主页 URL（douyin）")
    parser.add_argument("--limit", type=int, default=20, help="最多下载条数（douyin）")
    parser.add_argument("--output", default=str(OUTPUT_DIR), help="输出目录")
    args = parser.parse_args()

    ensure_deps()
    out = Path(args.output)

    if args.platform in ("youtube", "bilibili"):
        if not args.url:
            parser.error("--url 是必须的")
        download_youtube(args.url, out)
    elif args.platform == "douyin":
        if not args.user:
            parser.error("--user 是必须的")
        download_douyin(args.user, args.limit, out)


if __name__ == "__main__":
    main()
