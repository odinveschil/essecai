import { useEffect, useRef, useState } from 'react'
import Dialog, { CloseButton } from './Dialog'
import { videoSources, videos } from '../config/videos'
import type { VideoKey } from '../config/videos'

interface Props {
  videoKey: VideoKey | null
  onClose: () => void
}

type Source = { src: string; type?: string }
type Status = 'checking' | 'ready' | 'missing' | 'unplayable'

// remember lookups so reopening is instant
const found = new Map<VideoKey, Source[]>()

/** Which of 1.mp4 / 1.webm / 1.mov / 1.m4v actually exist on the server. */
async function locate(key: VideoKey): Promise<Source[]> {
  const cached = found.get(key)
  if (cached) return cached
  const candidates = videoSources(key)
  const checks = await Promise.all(
    candidates.map(async (s) => {
      try {
        const r = await fetch(s.src, { method: 'HEAD', cache: 'no-cache' })
        const type = r.headers.get('content-type') ?? ''
        // dev servers answer unknown paths with index.html — that is not a video
        return r.ok && !type.startsWith('text/html') ? s : null
      } catch {
        return null
      }
    }),
  )
  const list = checks.filter((s): s is Source => s !== null)
  if (list.length) found.set(key, list)
  return list
}

/**
 * Plays one of the two uploaded films above the table — never autoplays.
 * 1 → Coke Zero → introduction, 2 → tiramisu → Station F (see config/videos.ts).
 */
export default function VideoModal({ videoKey, onClose }: Props) {
  const [status, setStatus] = useState<Status>('checking')
  const [sources, setSources] = useState<Source[]>([])
  const videoRef = useRef<HTMLVideoElement>(null)
  const figureRef = useRef<HTMLElement>(null)
  const meta = videoKey ? videos[videoKey] : null

  useEffect(() => {
    if (!videoKey) return
    let alive = true
    setStatus('checking')
    locate(videoKey).then((list) => {
      if (!alive) return
      setSources(list)
      setStatus(list.length ? 'ready' : 'missing')
    })
    return () => {
      alive = false
    }
  }, [videoKey])

  useEffect(() => {
    const v = videoRef.current
    if (!v || status !== 'ready') return
    v.focus({ preventScroll: true })
    const fail = () => {
      if (v.networkState === HTMLMediaElement.NETWORK_NO_SOURCE || v.error) setStatus('unplayable')
    }
    v.addEventListener('error', fail)
    const last = v.querySelector('source:last-of-type')
    last?.addEventListener('error', fail)
    return () => {
      v.removeEventListener('error', fail)
      last?.removeEventListener('error', fail)
    }
  }, [status, sources])

  return (
    <Dialog
      open={!!videoKey}
      onClose={onClose}
      labelledBy="video-title"
      className="overlay-video"
      initialFocus={() => figureRef.current?.querySelector<HTMLElement>('.close-x') ?? null}
    >
      {videoKey && meta && (
        <figure className={`screen screen-${videoKey}`} ref={figureRef}>
          <div className="screen-frame">
            {status === 'ready' && (
              <video
                key={videoKey}
                ref={videoRef}
                controls
                playsInline
                preload="metadata"
                controlsList="nodownload"
                aria-label={meta.title}
              >
                {sources.map((s, i) => (
                  <source key={s.src} src={i === 0 ? `${s.src}#t=0.05` : s.src} type={s.type} />
                ))}
              </video>
            )}
            {status === 'missing' && (
              <div className="soon" role="status">
                <p>Video coming soon.</p>
              </div>
            )}
            {status === 'unplayable' && (
              <div className="soon" role="status">
                <p>
                  This browser can’t play the film here —{' '}
                  <a href={sources[0]?.src} target="_blank" rel="noreferrer">
                    open it directly
                  </a>
                  .
                </p>
              </div>
            )}
          </div>
          <figcaption>
            <span id="video-title" className="screen-title">
              {meta.title}
            </span>
            <span className="screen-caption">{meta.caption}</span>
          </figcaption>
          <span className="close-wrap">
            <CloseButton onClick={onClose} label="Close video" />
          </span>
        </figure>
      )}
    </Dialog>
  )
}
