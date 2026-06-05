import React from "react";
import { Composition } from "remotion";
import { VideoComposition } from "../Composition/VideoComposition";
import { VideoConfig } from "../Composition/types";
import { sampleScript } from "./sampleScript";

// 竖屏 9:16，30fps，60秒
const WIDTH = 1080;
const HEIGHT = 1920;
const FPS = 30;

// 从字幕数据推算总帧数
const totalFrames = Math.max(
  ...sampleScript.segments.map((s) => s.from + s.durationInFrames)
);

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="VideoComposition"
      component={VideoComposition as React.ComponentType<VideoConfig>}
      durationInFrames={totalFrames + FPS * 1} // 末尾留1秒
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={sampleScript}
    />
  );
};
