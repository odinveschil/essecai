/**
 * VIDEO FILES — drop them into `public/videos/`, named by number.
 *
 *   1.mp4 | 1.webm | 1.mov | 1.m4v   →  COKE ZERO  →  class introduction
 *   2.mp4 | 2.webm | 2.mov | 2.m4v   →  TIRAMISU   →  Station F film
 *
 * The base filename is what matters; any of the extensions above is picked up
 * automatically (first one that exists and plays wins). Nothing else needs to
 * change. If a file is missing, the player shows "Video coming soon." instead.
 *
 * Never swap these: 1 = Coke Zero = introduction, 2 = tiramisu = Station F.
 */

export const VIDEO_EXTENSIONS = ['mp4', 'webm', 'mov', 'm4v'] as const

export interface VideoConfig {
  /** Base filename inside public/videos (without extension). */
  file: string
  /** Optional explicit URL — overrides `file` if your host renames uploads. */
  src?: string
  title: string
  caption: string
}

export const videos = {
  introduction: {
    file: '1',
    title: 'Introduction',
    caption: 'Meet Aryaman — Advanced Steps in Entrepreneurship',
  },
  stationF: {
    file: '2',
    title: 'Station F — Film',
    caption: 'Prochain arrêt, Station F',
  },
} satisfies Record<string, VideoConfig>

export type VideoKey = keyof typeof videos

const MIME: Record<string, string | undefined> = {
  mp4: 'video/mp4',
  m4v: 'video/mp4',
  webm: 'video/webm',
  // .mov is usually H.264 inside QuickTime; leave the type off so browsers try it.
  mov: undefined,
}

export function videoSources(key: VideoKey): { src: string; type?: string }[] {
  const v: VideoConfig = videos[key]
  if (v.src) return [{ src: v.src }]
  const base = import.meta.env.BASE_URL
  return VIDEO_EXTENSIONS.map((ext) => ({ src: `${base}videos/${v.file}.${ext}`, type: MIME[ext] }))
}
