#!/usr/bin/env python3
"""
第3步：仿写 —— 把对标文案改写成高阳纺织老板的风格
用法:
  python rewrite.py --input ../transcripts/video_fixed.txt
  python rewrite.py --input ../transcripts/video_fixed.txt --duration 60
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from llm import chat

REWRITE_PROMPT = """你是我的短视频仿写助手。我的身份背景：
- 我是河北高阳（全国家纺纺织重镇）的创业者，专门给本地纺织厂、布商、电商分销商做"AI落地"的工具和服务（不是自己开家纺店，是卖工具/服务给商家）。
- 我已落地的产品：纺织爆款内容助手、纱知道（纱线助手）等 SaaS。
- 我的受众：不太懂技术、但想用 AI 多赚钱/省人力的中小纺织商家和老板。
- 我的语气：接地气、说人话、不端着，像同行老板在饭桌上掏心窝子讲干货；少用专业黑话，多用"能省多少人、能多卖多少"的具体好处。

【仿写任务】
下面是一条对标视频的文案。请你：
1. 保留"钩子 → 拆解 → 价值升华 → 落点"的结构骨架；
2. 把题材/案例全部换成"高阳纺织商家用 AI"的真实场景（比如：一个人管十个抖音号发布新品、AI 写直播话术、AI 客服自动回复询单等）；
3. 用我上面的语气重写，口语化、每句话短、适合口播；
4. 开头 3 秒必须有一个让纺织老板"咦？"的钩子；
5. 结尾给一个明确动作（关注/私信"AI"领工具/进群）；
6. 控制在 {duration} 秒口播量（约 {chars} 字），并在每句后用括号标注大致累计秒数，如（3s）；
7. 最后另起一行，输出一个适合发布的短视频标题（20字以内，含1-2个热词话题）。

对标文案如下：
\"\"\"
{text}
\"\"\"
"""


def rewrite(text: str, duration: int) -> str:
    # 中文口播约 4.5 字/秒
    chars = int(duration * 4.5)
    prompt = REWRITE_PROMPT.format(text=text, duration=duration, chars=chars)
    print(f"[仿写中] 目标 {duration}s / {chars}字 ...")
    return chat(prompt, max_tokens=4096, temperature=0.8)


def main():
    parser = argparse.ArgumentParser(description="仿写 —— 把文案改成高阳纺织老板风格")
    parser.add_argument("--input", required=True, help="转写稿 txt 路径")
    parser.add_argument("--duration", type=int, default=60, help="目标视频秒数（默认60s）")
    args = parser.parse_args()

    text = Path(args.input).read_text(encoding="utf-8")
    result = rewrite(text, args.duration)

    out_path = Path(args.input).parent / (Path(args.input).stem + f"_rewrite_{args.duration}s.txt")
    out_path.write_text(result, encoding="utf-8")
    print(f"\n[仿写完成] {out_path}")
    print("─" * 60)
    print(result)


if __name__ == "__main__":
    main()
