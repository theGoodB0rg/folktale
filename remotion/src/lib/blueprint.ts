import {z} from 'zod';

const renderSizeSchema = z.object({
  width: z.number().int().positive(),
  height: z.number().int().positive(),
});

const renderSchema = z.object({
  fps: z.number().positive(),
  preview: renderSizeSchema,
  final: renderSizeSchema.optional(),
  audio: z
    .object({
      mode: z.string(),
      normalize: z.boolean(),
    })
    .optional(),
});

const narrationSegmentSchema = z.object({
  id: z.string(),
  scene_id: z.string(),
  text: z.string(),
  start_sec: z.number().nonnegative(),
  target_duration_sec: z.number().nonnegative(),
  audio_path: z.string(),
});

const narrationSchema = z.object({
  voice_profile: z.string().optional(),
  segments: z.array(narrationSegmentSchema),
});

const sceneSchema = z.object({
  id: z.string(),
  type: z.string(),
  start_sec: z.number().nonnegative(),
  end_sec: z.number().nonnegative(),
  beat: z.string(),
  characters_present: z.array(z.string()).optional(),
  identity_lock: z.record(z.unknown()).optional(),
  visual_prompt: z.record(z.unknown()).optional(),
  asset_path: z.string(),
  camera_motion: z.record(z.unknown()).optional(),
  transition_out: z.string().optional(),
});

const motionShotSchema = z.object({
  id: z.string(),
  scene_id: z.string(),
  provider: z.string().optional(),
  duration_sec: z.number().nonnegative(),
  prompt: z.string().optional(),
  source_image_path: z.string().optional(),
  asset_path: z.string(),
  fallback_asset_path: z.string(),
  audio_policy: z.string().optional(),
});

export const blueprintSchema = z.object({
  schema_version: z.string().optional(),
  episode: z.object({
    id: z.string(),
    title: z.string(),
    duration_sec: z.number().positive(),
    format: z.string().optional(),
  }),
  render: renderSchema,
  narration: narrationSchema,
  scenes: z.array(sceneSchema),
  motion_shots: z.array(motionShotSchema),
});

export type RenderSize = z.infer<typeof renderSizeSchema>;
export type NarrationSegment = z.infer<typeof narrationSegmentSchema>;
export type Scene = z.infer<typeof sceneSchema>;
export type MotionShot = z.infer<typeof motionShotSchema>;
export type Blueprint = z.infer<typeof blueprintSchema>;

export const folktaleEpisodePropsSchema = z.object({
  blueprint: blueprintSchema.optional(),
  episodeRoot: z.string().optional(),
});

export type FolktaleEpisodeProps = z.infer<typeof folktaleEpisodePropsSchema>;

export const parseBlueprint = (value: unknown): Blueprint =>
  blueprintSchema.parse(value);

export const getBlueprintDurationSeconds = (
  blueprint: Blueprint | undefined,
  fallbackSeconds: number,
): number => {
  const duration = blueprint?.episode.duration_sec;
  return typeof duration === 'number' && Number.isFinite(duration) && duration > 0
    ? duration
    : fallbackSeconds;
};

export const getBlueprintFps = (
  blueprint: Blueprint | undefined,
  fallbackFps: number,
): number => {
  const fps = blueprint?.render.fps;
  return typeof fps === 'number' && Number.isFinite(fps) && fps > 0
    ? fps
    : fallbackFps;
};

export const resolveEpisodeAsset = (
  path: string,
  episodeRoot: string | undefined,
): string => {
  if (!episodeRoot) {
    return path;
  }

  const normalizedRoot = episodeRoot.replace(/\\/g, '/').replace(/\/$/, '');
  const normalizedPath = path.replace(/\\/g, '/').replace(/^\//, '');
  return `${normalizedRoot}/${normalizedPath}`;
};
