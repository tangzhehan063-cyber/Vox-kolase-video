import React from "react";
import { Composition } from "remotion";
import { CaptionOverlay, SEQUENCE_DURATION } from "./scenes/CaptionOverlay";

// Every <Composition> keeps its defaultProps as an INLINE object literal.
// Remotion Studio cannot write prop edits back to disk otherwise.
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="CaptionOverlay"
        component={CaptionOverlay}
        durationInFrames={SEQUENCE_DURATION}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{}}
      />
    </>
  );
};
