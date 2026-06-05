#!/usr/bin/env python3
"""
多租户管理 —— 每个纺织厂客户一套独立配置。

租户目录结构：
  commercial/tenants/{tenant_id}/
    config.yaml          - 客户配置（产品/身份/声音/形象）
    voice_ref.wav        - 声音参考录音（可选）
    avatar.mp4           - 数字人底片（可选，HeyGem 用）
    jobs/                - 任务历史（SQLite）

用法：
  python -m commercial.tenant list
  python -m commercial.tenant add --id factory_a --name "高阳A棉纺"
  python -m commercial.tenant show factory_a
"""

from __future__ import annotations
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent
TENANTS_DIR = ROOT / "tenants"

DEFAULT_TEMPLATE = {
    "name": "高阳纺织客户",
    "product": "纯棉毛巾",
    "location": "河北高阳",
    "tagline": "AI落地 · 高阳纺织专属",
    "identity": {
        "who": "河北高阳家纺纺织厂老板",
        "tone": "接地气、说人话、不端着",
    },
    "llm": {
        "provider": "deepseek",
        "api_key": "",
    },
    "digital_human": {
        "backend": "mock",        # mock | heygem | guiji
        "avatar_id": "",          # 平台形象ID（guiji用）
        "heygem_url": "http://localhost:8080",
    },
    "voice": {
        "enabled": False,         # True=用 IndexTTS2 克隆 ref_audio（需GPU）
        "ref_audio": "",          # 指向 voice_ref.wav 的路径
        # 无克隆时的兜底语音：auto(先试edge再espeak) | edge | offline(纯espeak) | ""(无声)
        "tts": "auto",
        "voice": "zh-CN-XiaoxiaoNeural",  # edge-tts音色，男声可用 zh-CN-YunxiNeural
    },
    "distribute": {
        "enabled": False,
        "platforms": ["douyin"],
        "douyin_cookie": "",      # 相对于租户目录的 cookie 文件
    },
    "rewrite": {
        "duration": 45,
        "style": "带货口播",
    },
}


class Tenant:
    def __init__(self, tenant_id: str):
        self.id = tenant_id
        self.dir = TENANTS_DIR / tenant_id
        self.config_path = self.dir / "config.yaml"

    @property
    def config(self) -> dict:
        if not self.config_path.exists():
            raise FileNotFoundError(f"租户不存在: {self.id}（{self.config_path}）")
        import yaml
        return yaml.safe_load(self.config_path.read_text(encoding="utf-8"))

    def voice_ref(self) -> Path | None:
        p = self.dir / "voice_ref.wav"
        return p if p.exists() else None

    def avatar_video(self) -> Path | None:
        p = self.dir / "avatar.mp4"
        return p if p.exists() else None

    def jobs_dir(self) -> Path:
        d = self.dir / "jobs"
        d.mkdir(exist_ok=True)
        return d

    def out_dir(self) -> Path:
        d = self.dir / "out"
        d.mkdir(exist_ok=True)
        return d


def list_tenants() -> list[str]:
    if not TENANTS_DIR.exists():
        return []
    return [d.name for d in sorted(TENANTS_DIR.iterdir()) if d.is_dir()]


def create_tenant(tenant_id: str, name: str = "") -> Tenant:
    import yaml
    t = Tenant(tenant_id)
    t.dir.mkdir(parents=True, exist_ok=True)
    (t.dir / "jobs").mkdir(exist_ok=True)
    (t.dir / "out").mkdir(exist_ok=True)

    cfg = dict(DEFAULT_TEMPLATE)
    if name:
        cfg["name"] = name
    t.config_path.write_text(
        yaml.dump(cfg, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
    print(f"✅ 租户 [{tenant_id}] 已创建: {t.dir}")
    print(f"   请编辑: {t.config_path}")
    print(f"   可选：把声音参考录音放到 {t.dir}/voice_ref.wav")
    return t


def build_agent_config(tenant: Tenant, extra: dict | None = None) -> dict:
    """
    把租户配置合并成 agent.py 能读懂的 config dict，
    agent.py 无需改动，通过这里注入多租户设置。
    """
    tc = tenant.config
    cfg = {
        "llm": tc.get("llm", {}),
        "identity": tc.get("identity", {}),
        "download": {"platform": "douyin", "url": "", "user": "", "limit": 5},
        "transcribe": {"engine": "auto", "fix": True},
        "rewrite": tc.get("rewrite", {"duration": 45}),
        "voice": {
            "enabled": tc.get("voice", {}).get("enabled", False),
            "ref_audio": str(tenant.voice_ref() or ""),
        },
        "digital_human": tc.get("digital_human", {"backend": "mock"}),
        "lipsync": {"enabled": False},
        "distribute": tc.get("distribute", {"enabled": False}),
        "_tenant_id": tenant.id,
        "_tenant_dir": str(tenant.dir),
        "_tenant_out": str(tenant.out_dir()),
    }
    if extra:
        cfg.update(extra)
    return cfg


# ── CLI ──────────────────────────────────────────────────────

def main():
    import argparse
    p = argparse.ArgumentParser(description="多租户管理")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("list", help="列出所有租户")

    add_p = sub.add_parser("add", help="新建租户")
    add_p.add_argument("--id", required=True, dest="tid")
    add_p.add_argument("--name", default="")

    show_p = sub.add_parser("show", help="查看租户配置")
    show_p.add_argument("tenant_id")

    args = p.parse_args()

    if args.cmd == "list":
        ids = list_tenants()
        if not ids:
            print("（暂无租户，用 add 命令创建）")
        for tid in ids:
            t = Tenant(tid)
            try:
                name = t.config.get("name", "")
                print(f"  {tid:20s}  {name}")
            except Exception:
                print(f"  {tid:20s}  （配置文件损坏）")

    elif args.cmd == "add":
        create_tenant(args.tid, args.name)

    elif args.cmd == "show":
        import yaml
        t = Tenant(args.tenant_id)
        print(yaml.dump(t.config, allow_unicode=True))

    else:
        p.print_help()


if __name__ == "__main__":
    main()
