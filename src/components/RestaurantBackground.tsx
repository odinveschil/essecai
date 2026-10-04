import { memo, useMemo } from 'react'
import type { CSSProperties } from 'react'
import { asset } from '../scene'
import type { Density, SceneData } from '../scene'

interface Props {
  data: SceneData
  density: Density
  onLoad: () => void
  animate: boolean
}

// deterministic pseudo-random so the room doesn't reshuffle on every render
function rand(seed: number) {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453
  return x - Math.floor(x)
}

const CROWD_COLOURS = ['#2a201b', '#6b2a20', '#3b4a5e', '#d6cbb8', '#1d1d22', '#7a6a3a', '#4a3a52', '#a0533a']

/** The hall: out-of-focus Station F, hanging bulbs breathing, people drifting past. */
function RestaurantBackground({ data, density, onLoad, animate }: Props) {
  const lights = useMemo(() => data.lights.slice(0, 40), [data.lights])
  const crowd = useMemo(
    () =>
      Array.from({ length: 7 }, (_, i) => {
        const far = rand(i + 3)
        return {
          h: 9 + far * 9, // % of stage height
          bottom: data.horizon * 100 + 2 + far * 5,
          dur: 38 + rand(i + 11) * 40,
          delay: -rand(i + 21) * 70,
          dir: i % 2 ? 1 : -1,
          colour: CROWD_COLOURS[i % CROWD_COLOURS.length],
          opacity: 0.32 + (1 - far) * 0.25,
        }
      }),
    [data.horizon],
  )
  return (
    <div className="hall" aria-hidden="true">
      <div className="hall-plate">
        <img
          src={asset(data.view, data.bg[density])}
          alt=""
          draggable={false}
          decoding="async"
          fetchPriority="high"
          onLoad={onLoad}
        />
      </div>
      {animate && (
        <div className="hall-life">
          {lights.map((l, i) => (
            <span
              key={i}
              className={`glow ${i % 5 === 0 ? 'flicker' : 'breathe'}`}
              style={
                {
                  left: `${l.x * 100}%`,
                  top: `${l.y * 100}%`,
                  width: `calc(var(--u) * ${Math.max(l.r * 100 * (data.size[0] / data.size[1]) * 3.2, 1.2)})`,
                  '--c': l.c,
                  animationDelay: `${-rand(i) * 9}s`,
                  animationDuration: `${(i % 5 === 0 ? 5 : 7) + rand(i + 50) * 6}s`,
                } as CSSProperties
              }
            />
          ))}
          {crowd.map((p, i) => (
            <span
              key={`p${i}`}
              className={`passerby ${p.dir > 0 ? 'ltr' : 'rtl'}`}
              style={
                {
                  '--h': p.h,
                  bottom: `${100 - p.bottom}%`,
                  '--c': p.colour,
                  opacity: p.opacity,
                  animationDuration: `${p.dur}s`,
                  animationDelay: `${p.delay}s`,
                } as CSSProperties
              }
            >
              <i className="head" />
              <i className="body" />
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default memo(RestaurantBackground)
