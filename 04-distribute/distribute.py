#!/usr/bin/env python3
"""
第6步：一键分发视频到多平台
基于 social-auto-upload（Playwright 浏览器自动化）
支持：抖音、微信视频号、小红书、快手、B站

用法:
  python distribute.py --video ../out/video.mp4 --title "标题" --tags AI纺织 高阳 --platforms douyin weixin
  python distribute.py --video ../out/video.mp4 --config publish.json
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

PLATFORMS = {
    "douyin": "抖音",
    "weixin": "微信视频号",
    "xiaohongshu": "小红书",
    "kuaishou": "快手",
    "bilibili": "B站",
}


def ensure_deps():
    try:
        import social_auto_upload  # noqa
    except ImportError:
        print("安装 social-auto-upload...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "git+https://github.com/dreammis/social-auto-upload.git",
            "-q",
        ])


def publish_douyin(video: Path, title: str, tags: list[str]):
    """抖音发布（需提前用 `playwright install chromium` 安装浏览器）"""
    from uploader.douyin_uploader.main import DouYinVideo, douyin_setup

    cookie_file = Path(__file__).parent / "cookies" / "douyin.json"
    if not cookie_file.exists():
        print(f"[抖音] cookie 文件不存在：{cookie_file}")
        print("请先运行以下命令登录并保存 cookie：")
        print("  python -c \"from uploader.douyin_uploader.main import douyin_setup; douyin_setup('cookies/douyin.json', handle=True)\"")
        return

    app = DouYinVideo(
        title=title,
        file_path=str(video),
        tags=tags,
        publish_date=0,  # 0 = 立即发布
        account_file=str(cookie_file),
    )
    app.main()
    print(f"[抖音] 发布成功: {title}")


def publish_weixin(video: Path, title: str, tags: list[str]):
    """微信视频号发布"""
    from uploader.weixin_uploader.main import WeixinVideo

    cookie_file = Path(__file__).parent / "cookies" / "weixin.json"
    if not cookie_file.exists():
        print(f"[视频号] cookie 文件不存在：{cookie_file}")
        return

    app = WeixinVideo(
        title=title,
        file_path=str(video),
        tags=tags,
        publish_date=0,
        account_file=str(cookie_file),
    )
    app.main()
    print(f"[视频号] 发布成功: {title}")


def publish_bilibili(video: Path, title: str, tags: list[str]):
    """B站发布"""
    from uploader.bilibili_uploader.main import BilibiliVideo

    cookie_file = Path(__file__).parent / "cookies" / "bilibili.json"
    if not cookie_file.exists():
        print(f"[B站] cookie 文件不存在：{cookie_file}")
        return

    app = BilibiliVideo(
        title=title,
        file_path=str(video),
        tags=tags,
        tid=21,  # 日常
        account_file=str(cookie_file),
    )
    app.main()
    print(f"[B站] 发布成功: {title}")


PUBLISHERS = {
    "douyin": publish_douyin,
    "weixin": publish_weixin,
    "bilibili": publish_bilibili,
}


def main():
    parser = argparse.ArgumentParser(description="一键多平台分发")
    parser.add_argument("--video", required=True, help="视频文件路径")
    parser.add_argument("--title", help="视频标题")
    parser.add_argument("--tags", nargs="+", default=["AI", "高阳纺织", "AI落地"], help="话题标签")
    parser.add_argument(
        "--platforms",
        nargs="+",
        choices=list(PLATFORMS.keys()),
        default=["douyin"],
        help="目标平台（默认仅抖音）",
    )
    parser.add_argument("--config", help="从 JSON 配置文件读取参数")
    args = parser.parse_args()

    if args.config:
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
        video = Path(cfg["video"])
        title = cfg.get("title", "")
        tags = cfg.get("tags", args.tags)
        platforms = cfg.get("platforms", args.platforms)
    else:
        video = Path(args.video)
        title = args.title or video.stem
        tags = args.tags
        platforms = args.platforms

    if not video.exists():
        print(f"视频文件不存在：{video}")
        sys.exit(1)

    ensure_deps()
    Path(__file__).parent.joinpath("cookies").mkdir(exist_ok=True)

    for platform in platforms:
        name = PLATFORMS.get(platform, platform)
        print(f"\n{'='*40}")
        print(f"发布到 {name}...")
        fn = PUBLISHERS.get(platform)
        if fn:
            fn(video, title, tags)
        else:
            print(f"[{name}] 暂未支持，跳过")

    print("\n全部完成！")


if __name__ == "__main__":
    main()
