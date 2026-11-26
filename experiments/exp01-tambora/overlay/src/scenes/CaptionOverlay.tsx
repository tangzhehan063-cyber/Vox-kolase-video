import React, { useEffect, useState } from "react";
import { AbsoluteFill, continueRender, delayRender, staticFile } from "remotion";
import { Captions } from "../shared/system";
import { CAPTIONS as captions } from "../shared/captions";
import { TOTAL_FRAMES } from "../shared/meta";

export const SEQUENCE_DURATION = TOTAL_FRAMES;

// Transparent layer: only the burned captions, composited over the film by ffmpeg.
export const CaptionOverlay: React.FC = () => {
  const [handle] = useState(() => delayRender("font"));
  useEffect(() => {
    new FontFace("Anton", `url(${staticFile("Anton.ttf")})`)
      .load()
      .then((f) => {
        document.fonts.add(f);
        continueRender(handle);
      })
      .catch(() => continueRender(handle));
  }, [handle]);
  return (
    <AbsoluteFill style={{ background: "transparent" }}>
      {/* bottom 440 -> the plate's lower edge sits at y=1480, just above the 420px platform dead zone */}
      <Captions captions={captions} bottom={440} fontSize={74} />
    </AbsoluteFill>
  );
};
