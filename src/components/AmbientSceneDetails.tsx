import { memo } from 'react'
import type { CSSProperties } from 'react'
import type { SceneData } from '../scene'

/** Steam off the pizza, a lens vignette and a whisper of film grain. */
function AmbientSceneDetails({ data, animate }: { data: SceneData; animate: boolean }) {
  const { cx, cy, rx, ry } = data.pizza
  return (
    <div className="ambient" aria-hidden="true">
      {animate && (
        <div
          className="steam"
          style={
            {
              left: `${(cx - rx * 0.75) * 100}%`,
              width: `${rx * 150}%`,
              top: `${(cy - ry * 1.9) * 100}%`,
              height: `${ry * 230}%`,
            } as CSSProperties
          }
        >
          {[0, 1, 2, 3, 4].map((i) => (
            <i key={i} style={{ left: `${12 + i * 18}%`, animationDelay: `${-i * 2.3}s` } as CSSProperties} />
          ))}
        </div>
      )}
      <div className="vignette" />
      <div className="grain" />
    </div>
  )
}

export default memo(AmbientSceneDetails)
