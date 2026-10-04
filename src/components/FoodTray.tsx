import { memo, useEffect, useMemo, useRef, useState } from 'react'
import type { CSSProperties, KeyboardEvent, PointerEvent as RPointerEvent } from 'react'
import { asset } from '../scene'
import type { Density, Layer, SceneData } from '../scene'
import { articles } from '../content/articles'
import type { SliceId } from '../content/articles'
import type { VideoKey } from '../config/videos'

type ObjectId = SliceId | 'tiramisu' | 'glass'

interface Props {
  data: SceneData
  density: Density
  onLayerLoad: (id: string) => void
  onOpenArticle: (id: SliceId) => void
  onOpenVideo: (key: VideoKey) => void
  animate: boolean
  ready: boolean
  fine: boolean
}

const SLICE_ORDER: SliceId[] = articles.map((a) => a.id) // clockwise from the far side

const LABELS: Record<ObjectId, string> = {
  seamone: 'Open Seamone Paris article',
  angels: 'Open Business Angels article',
  serena: 'Open Serena VC article',
  tomcat: 'Open TOMCAT article',
  freeda: 'Open Freeda article',
  stationf: 'Open Station F article',
  glass: 'Play class introduction video',
  tiramisu: 'Play Station F video',
}

const isSlice = (id: ObjectId): id is SliceId => id !== 'glass' && id !== 'tiramisu'

/** The tray: six slices of pizza, a tiramisu, a Coke Zero — and the hit areas that make them the navigation. */
function FoodTray({ data, density, onLayerLoad, onOpenArticle, onOpenVideo, animate, ready, fine }: Props) {
  const [hover, setHover] = useState<ObjectId | null>(null)
  const [pressed, setPressed] = useState<ObjectId | null>(null)
  const [wave, setWave] = useState<ObjectId | null>(null)
  const [W, H] = data.size
  const openTimer = useRef(0)

  // draw order: farthest first (the lower an object's front edge sits in frame, the nearer it is)
  const order = useMemo(() => {
    const ids = [...SLICE_ORDER, 'glass', 'tiramisu'] as ObjectId[]
    return ids
      .filter((id) => data.layers[id])
      .sort((a, b) => {
        const ra = data.layers[a].rect
        const rb = data.layers[b].rect
        return ra[1] + ra[3] - (rb[1] + rb[3])
      })
  }, [data])

  // once the camera has settled, the slices rise one after another, once,
  // clockwise — a wordless hint that the pizza is the menu
  useEffect(() => {
    if (!ready || !animate) return
    const timers: number[] = []
    const seq: ObjectId[] = [...SLICE_ORDER]
    seq.forEach((id, i) => {
      timers.push(window.setTimeout(() => setWave(id), 1500 + i * 190))
    })
    timers.push(window.setTimeout(() => setWave(null), 1500 + seq.length * 190 + 160))
    return () => timers.forEach((t) => window.clearTimeout(t))
  }, [ready, animate, data.view])

  useEffect(() => () => window.clearTimeout(openTimer.current), [])

  const open = (id: ObjectId) => {
    if (isSlice(id)) onOpenArticle(id)
    else onOpenVideo(id === 'glass' ? 'introduction' : 'stationF')
  }

  const activate = (id: ObjectId, viaTouch: boolean) => {
    window.clearTimeout(openTimer.current)
    if (viaTouch && animate) {
      // let the slice visibly lift under the finger before the menu opens
      setPressed(id)
      openTimer.current = window.setTimeout(() => {
        setPressed(null)
        open(id)
      }, 190)
    } else {
      open(id)
    }
  }

  const onKey = (id: ObjectId) => (e: KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      open(id)
    }
  }

  const lastPointer = useRef<string>('mouse')
  const onPointerDown = (e: RPointerEvent) => {
    lastPointer.current = e.pointerType
  }

  return (
    <>
      <div className="food" aria-hidden="true">
        {order.map((id) => (
          <FoodLayer
            key={id}
            id={id}
            layer={data.layers[id]}
            src={asset(data.view, data.layers[id].files[density])}
            lifted={hover === id || pressed === id || wave === id}
            kind={isSlice(id) ? 'slice' : id}
            onLoad={() => onLayerLoad(id)}
            data={data}
            animate={animate}
          />
        ))}
      </div>
      <svg
        className={`hits ${fine ? 'is-fine' : ''}`}
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        role="group"
        aria-label="The tray"
        onPointerLeave={() => setHover(null)}
      >
        {[...SLICE_ORDER, 'glass', 'tiramisu'].map((id) => {
          const oid = id as ObjectId
          const layer = data.layers[oid]
          if (!layer) return null
          const pts = layer.polygon.map(([x, y]) => `${(x * W).toFixed(1)},${(y * H).toFixed(1)}`).join(' ')
          return (
            <polygon
              key={oid}
              points={pts}
              className={`hit hit-${isSlice(oid) ? 'slice' : oid}`}
              role="button"
              tabIndex={0}
              aria-label={LABELS[oid]}
              onPointerDown={onPointerDown}
              onPointerEnter={(e) => e.pointerType === 'mouse' && setHover(oid)}
              onPointerLeave={(e) => e.pointerType === 'mouse' && setHover((h) => (h === oid ? null : h))}
              onFocus={() => setHover(oid)}
              onBlur={() => setHover((h) => (h === oid ? null : h))}
              onClick={() => activate(oid, lastPointer.current !== 'mouse')}
              onKeyDown={onKey(oid)}
            />
          )
        })}
      </svg>
    </>
  )
}

interface LayerProps {
  id: ObjectId
  layer: Layer
  src: string
  lifted: boolean
  kind: 'slice' | 'glass' | 'tiramisu'
  onLoad: () => void
  data: SceneData
  animate: boolean
}

const FoodLayer = memo(function FoodLayer({ id, layer, src, lifted, kind, onLoad, data, animate }: LayerProps) {
  const [x, y, w, h] = layer.rect
  const style = {
    left: `${x * 100}%`,
    top: `${y * 100}%`,
    width: `${w * 100}%`,
    height: `${h * 100}%`,
    '--mask': `url("${src}")`,
  } as CSSProperties
  return (
    <div className={`food-layer food-${kind} ${lifted ? 'is-lifted' : ''}`} style={style} data-id={id}>
      <img src={src} alt="" draggable={false} decoding="async" fetchPriority="high" onLoad={onLoad} />
      <span className="sheen" />
      {kind === 'glass' && animate && <Bubbles layer={layer} liquid={data.liquid} />}
    </div>
  )
})

/** Carbonation rising inside the cola, clipped to the liquid as seen through the glass. */
function Bubbles({ layer, liquid }: { layer: Layer; liquid: [number, number][] }) {
  const [x, y, w, h] = layer.rect
  const clip = useMemo(() => {
    if (!liquid.length) return undefined
    return `polygon(${liquid.map(([px, py]) => `${(((px - x) / w) * 100).toFixed(2)}% ${(((py - y) / h) * 100).toFixed(2)}%`).join(',')})`
  }, [liquid, x, y, w, h])
  const bubbles = useMemo(() => {
    if (!liquid.length) return []
    const xs = liquid.map((p) => (p[0] - x) / w)
    const ys = liquid.map((p) => (p[1] - y) / h)
    const minX = Math.min(...xs), maxX = Math.max(...xs)
    const maxY = Math.max(...ys)
    const minY = Math.min(...ys)
    return Array.from({ length: 22 }, (_, i) => {
      const r = (Math.sin(i * 91.7) * 43758.5453) % 1
      const rr = Math.abs(r)
      const r2 = Math.abs((Math.sin(i * 12.9 + 4) * 9871.123) % 1)
      return {
        left: (minX + (maxX - minX) * (0.1 + 0.8 * rr)) * 100,
        bottom: (1 - maxY) * 100 + r2 * 6,
        rise: (maxY - minY) * h * 100 * (0.7 + 0.3 * r2), // in --u (1% of stage height)
        size: 0.18 + r2 * 0.32,
        dur: 2.2 + rr * 3.4,
        delay: -r2 * 6,
      }
    })
  }, [liquid, x, y, w, h])
  if (!clip) return null
  return (
    <span className="bubbles" style={{ clipPath: clip, WebkitClipPath: clip } as CSSProperties}>
      {bubbles.map((b, i) => (
        <i
          key={i}
          style={
            {
              left: `${b.left}%`,
              bottom: `${b.bottom}%`,
              width: `calc(var(--u) * ${b.size})`,
              height: `calc(var(--u) * ${b.size})`,
              '--rise': `calc(var(--u) * ${b.rise.toFixed(2)} * -1)`,
              animationDuration: `${b.dur}s`,
              animationDelay: `${b.delay}s`,
            } as CSSProperties
          }
        />
      ))}
    </span>
  )
}

export default memo(FoodTray)
