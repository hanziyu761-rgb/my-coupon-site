import React from "react";
import { Composition } from "remotion";
import { VideoComposition } from "../Composition/VideoComposition";
import { VideoConfig } from "../Composition/types";
import { sampleScript } from "./sampleScript";

// 竖屏 9:16，30fps
const WIDTH = 1080;
const HEIGHT = 1920;
const FPS = 30;

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="VideoComposition"
      component={VideoComposition as React.ComponentType<VideoConfig>}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={sampleScript}
      // 时长根据字幕自动算（agent 注入新文案时自适应）
      calculateMetadata={({ props }) => {
        const segs = (props as VideoConfig).segments ?? [];
        const last = segs.length
          ? Math.max(...segs.map((s) => s.from + s.durationInFrames))
          : FPS * 2;
        return {
          durationInFrames: Math.round(last + FPS), // 末尾留1秒
          fps: FPS,
          width: WIDTH,
          height: HEIGHT,
        };
      }}
    />
  );
};
