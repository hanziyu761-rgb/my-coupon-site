export interface Segment {
  /** 字幕文字 */
  text: string;
  /** 开始帧（30fps） */
  from: number;
  /** 持续帧数 */
  durationInFrames: number;
  /** 可选：高亮关键词 */
  highlight?: string;
}

export interface PillLabel {
  text: string;
  color: string;
}

export interface VideoConfig {
  /** 标题（顶部，不口播时显示） */
  title?: string;
  /** 账号定位标签，显示在顶部 */
  tagLine?: string;
  /** 五步流程药丸（可选） */
  pills?: PillLabel[];
  /** 字幕片段 */
  segments: Segment[];
  /** 背景颜色，默认深色网格 */
  bgColor?: string;
}
