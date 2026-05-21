import {AbsoluteFill, Sequence} from 'remotion';
import {CaptionLayer} from '../components/CaptionLayer';
import {MotionClip} from '../components/MotionClip';
import {NarrationAudioLayer} from '../components/NarrationAudioLayer';
import {SceneStill} from '../components/SceneStill';
import type {FolktaleEpisodeProps} from '../lib/blueprint';
import {getBlueprintFps} from '../lib/blueprint';
import {secondsToFrames} from '../lib/timeline';

const PLACEHOLDER_SCENE = {
  id: 'placeholder_scene',
  type: 'still',
  start_sec: 0,
  end_sec: 6,
  beat: 'Remotion renderer shell',
  asset_path: '',
};

export const FolktaleEpisode = ({
  blueprint,
  episodeRoot,
}: FolktaleEpisodeProps) => {
  const fps = getBlueprintFps(blueprint, 30);

  if (!blueprint) {
    return (
      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'center',
          backgroundColor: '#16120f',
          color: 'white',
          fontFamily: 'Arial, Helvetica, sans-serif',
          fontSize: 42,
        }}
      >
        {PLACEHOLDER_SCENE.beat}
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{backgroundColor: '#16120f'}}>
      {blueprint.scenes.map((scene) => {
        const startFrame = secondsToFrames(scene.start_sec, fps);
        const durationInFrames = Math.max(
          1,
          secondsToFrames(scene.end_sec - scene.start_sec, fps),
        );
        const motionShot = blueprint.motion_shots.find(
          (shot) => shot.scene_id === scene.id,
        );

        return (
          <Sequence
            key={scene.id}
            from={startFrame}
            durationInFrames={durationInFrames}
          >
            {motionShot ? (
              <MotionClip shot={motionShot} episodeRoot={episodeRoot} />
            ) : (
              <SceneStill scene={scene} episodeRoot={episodeRoot} />
            )}
          </Sequence>
        );
      })}
      <NarrationAudioLayer
        segments={blueprint.narration.segments}
        episodeRoot={episodeRoot}
        fps={fps}
      />
      <CaptionLayer segments={blueprint.narration.segments} fps={fps} />
    </AbsoluteFill>
  );
};
