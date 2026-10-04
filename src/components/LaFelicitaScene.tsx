import { useEffect, useMemo, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { asset, layoutStage, pickView, scenes } from '../scene'
import { useFinePointer, useReducedMotion, useViewport } from '../hooks'
import type { SliceId } from '../content/articles'
import type { VideoKey } from '../config/videos'
import RestaurantBackground from './RestaurantBackground'
import CommunalTable from './CommunalTable'
import FoodTray from './FoodTray'
import AmbientSceneDetails from './AmbientSceneDetails'

interface Props {
  onOpenArticle: (id: SliceId) => void
  onOpenVideo: (key: VideoKey) => void
  dimmed: boolean
}

/**
 * The whole site: you are sitting at a communal table in La Felicità,
 * Station F. The tray in front of you is the navigation.
 */
export default function LaFelicitaScene({ onOpenArticle, onOpenVideo, dimmed }: Props) {
  const vp = useViewport()
  const view = pickView(vp.w, vp.h)
  const data = scenes[view]
  const box = useMemo(() => layoutStage(data, vp.w, vp.h, vp.dpr), [data, vp.w, vp.h, vp.dpr])
  const reduced = useReducedMotion()
  const fine = useFinePointer()

  // every layer reports in; the camera settles once the plate is on the table
  const total = 2 + Object.keys(data.layers).length
  const [loaded, setLoaded] = useState<Record<string, number>>({})
  const [ready, setReady] = useState(false)
  const onLoad = (key: string) => setLoaded((l) => (l[key] ? l : { ...l, [key]: 1 }))
  useEffect(() => {
    setReady(false)
    setLoaded({})
    const t = window.setTimeout(() => setReady(true), 7000)
    return () => window.clearTimeout(t)
  }, [view])
  useEffect(() => {
    if (Object.keys(loaded).length >= total) setReady(true)
  }, [loaded, total])

  // gentle parallax: the hall drifts more than the table
  const stageRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (reduced || !fine) return
    const el = stageRef.current
    if (!el) return
    let tx = 0, ty = 0, x = 0, y = 0, raf = 0
    const move = (e: PointerEvent) => {
      tx = (e.clientX / window.innerWidth - 0.5) * 2
      ty = (e.clientY / window.innerHeight - 0.5) * 2
      if (!raf) raf = requestAnimationFrame(tick)
    }
    const tick = () => {
      x += (tx - x) * 0.06
      y += (ty - y) * 0.06
      el.style.setProperty('--px', x.toFixed(4))
      el.style.setProperty('--py', y.toFixed(4))
      raf = Math.abs(tx - x) + Math.abs(ty - y) > 0.001 ? requestAnimationFrame(tick) : 0
    }
    window.addEventListener('pointermove', move, { passive: true })
    return () => {
      window.removeEventListener('pointermove', move)
      cancelAnimationFrame(raf)
    }
  }, [reduced, fine])

  const stageStyle = {
    width: `${box.width}px`,
    height: `${box.height}px`,
    left: `${box.left}px`,
    top: `${box.top}px`,
    '--u': `${box.height / 100}px`,
    '--lqip': `url("${data.lqip}")`,
  } as CSSProperties

  return (
    <main className={`scene ${dimmed ? 'is-dimmed' : ''}`} aria-label="A tray at a communal table in La Felicità, Station F">
      <h1 className="sr-only">A tray at La Felicità, Station F</h1>
      <p className="sr-only">
        A pizza cut into six slices sits on a tray. Each slice opens one article. The Coke Zero plays the class
        introduction video and the tiramisu plays the Station F film.
      </p>
      <div className="backdrop" style={{ backgroundImage: `url("${data.lqip}")` }} aria-hidden="true" />
      <div
        ref={stageRef}
        className={`stage view-${view} ${ready ? 'is-ready' : ''} ${reduced ? 'is-reduced' : ''}`}
        style={stageStyle}
        key={view}
      >
        <div className="settle">
          <div className="lqip" aria-hidden="true" />
          <RestaurantBackground data={data} density={box.density} onLoad={() => onLoad('bg')} animate={!reduced} />
          <CommunalTable src={asset(view, data.base[box.density])} onLoad={() => onLoad('base')} />
          <FoodTray
            data={data}
            density={box.density}
            onLayerLoad={onLoad}
            onOpenArticle={onOpenArticle}
            onOpenVideo={onOpenVideo}
            animate={!reduced}
            ready={ready}
            fine={fine}
          />
          <AmbientSceneDetails data={data} animate={!reduced} />
        </div>
      </div>
    </main>
  )
}
