/**
 * 示例文案 —— 照着对标视频结构改写的高阳纺织版本
 * 修改这个文件里的 segments 就能换文案，无需改组件
 *
 * 换算：30fps → 1秒=30帧
 * 中文口播约 4.5字/秒，每句话建议留 0.3s 间隔（9帧）
 */

import { VideoConfig } from "../Composition/types";

// 工具函数：把秒数转成帧
const s = (sec: number) => Math.round(sec * 30);

export const sampleScript: VideoConfig = {
  tagLine: "AI落地 · 高阳纺织专属",
  pills: [
    { text: "① 下载", color: "#FF6B6B" },
    { text: "② 转写", color: "#FFA500" },
    { text: "③ 仿写", color: "#4ECDC4" },
    { text: "④ 克隆声音", color: "#45B7D1" },
    { text: "⑤ 发布", color: "#96CEB4" },
  ],
  segments: [
    // ── 钩子（0–5s）──────────────────────────────────────
    {
      text: "一个人管了十个抖音号，",
      from: s(0),
      durationInFrames: s(2.5),
      highlight: "十个抖音号",
    },
    {
      text: "每天自动发五条新品视频，",
      from: s(2.8),
      durationInFrames: s(2.5),
      highlight: "自动发",
    },
    {
      text: "一分钱外包没花。",
      from: s(5.5),
      durationInFrames: s(2),
      highlight: "一分钱",
    },

    // ── 降门槛（7–13s）──────────────────────────────────
    {
      text: "不需要懂编程，",
      from: s(8),
      durationInFrames: s(2),
    },
    {
      text: "五个开源工具串起来，",
      from: s(10.3),
      durationInFrames: s(2.5),
    },
    {
      text: "AI替你做内容、配音、发布。",
      from: s(13),
      durationInFrames: s(3),
      highlight: "AI替你",
    },

    // ── 五步拆解（16–40s）────────────────────────────────
    {
      text: "第一步，自动下载同行爆款视频，",
      from: s(17),
      durationInFrames: s(3),
    },
    {
      text: "研究他们怎么拍、怎么说话。",
      from: s(20.2),
      durationInFrames: s(2.8),
    },
    {
      text: "第二步，Whisper一键转成文字，",
      from: s(23.5),
      durationInFrames: s(3),
      highlight: "Whisper",
    },
    {
      text: "顺手把错字也改了。",
      from: s(26.8),
      durationInFrames: s(2),
    },
    {
      text: "第三步，把文案喂给 AI，",
      from: s(29.3),
      durationInFrames: s(2.5),
    },
    {
      text: "改成你自己的风格和产品。",
      from: s(32),
      durationInFrames: s(2.5),
    },
    {
      text: "第四步，克隆你的声音，",
      from: s(35),
      durationInFrames: s(2.3),
      highlight: "克隆你的声音",
    },
    {
      text: "三秒录音，自动配音。",
      from: s(37.5),
      durationInFrames: s(2.2),
    },
    {
      text: "第五步，自动加字幕、对口型，",
      from: s(40.2),
      durationInFrames: s(3),
    },
    {
      text: "一键分发到抖音、视频号、快手。",
      from: s(43.5),
      durationInFrames: s(3),
      highlight: "一键分发",
    },

    // ── 价值升华（47–54s）────────────────────────────────
    {
      text: "以前请一个运营要五六千一个月，",
      from: s(47),
      durationInFrames: s(3.2),
      highlight: "五六千",
    },
    {
      text: "现在这套流水线，",
      from: s(50.5),
      durationInFrames: s(2),
    },
    {
      text: "就是你永不睡觉的AI员工。",
      from: s(52.8),
      durationInFrames: s(3),
      highlight: "永不睡觉",
    },

    // ── 落点（56–60s）────────────────────────────────────
    {
      text: "关注我，私信「AI」",
      from: s(56.5),
      durationInFrames: s(2.5),
      highlight: "AI",
    },
    {
      text: "领取这套工具包，免费的。",
      from: s(59.2),
      durationInFrames: s(3),
      highlight: "免费",
    },
  ],
};
