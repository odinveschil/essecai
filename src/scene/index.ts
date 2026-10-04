import desktop from './desktop.json'

export type View = 'desktop'
export type Density = '1x' | '2x'
export type Files = Record<Density, string>
export type Pt = [number, number]

export interface Layer {
  files: Files
  /** normalised [x, y, w, h] of the cut-out inside the render */
  rect: [number, number, number, number]
  /** normalised hit polygon following the object's silhouette */
  polygon: Pt[]
  center: Pt
}

export interface Light {
  x: number
  y: number
  r: number
  c: string
}

export interface SceneData {
  view: View
  size: [number, number]
  bg: Files
  base: Files
  lqip: string
  layers: Record<string, Layer>
  liquid: Pt[]
  lights: Light[]
  horizon: number
  pizza: { cx: number; cy: number; rx: number; ry: number }
}

export const scene = desktop as unknown as SceneData

export function asset(view: View, file: string) {
  return `${import.meta.env.BASE_URL}scene/${view}/${file}`
}

export interface StageBox {
  scale: number
  width: number
  height: number
  left: number
  top: number
  density: Density
}

/**
 * Cover the viewport with the render, unless that would crop the tray —
 * then fit the tray (plus a slice of the hall) and let the blurred
 * backdrop fill the remainder.
 */
export function layoutStage(data: SceneData, vw: number, vh: number, dpr: number): StageBox {
  const [W, H] = data.size
  let x0 = 1, y0 = 1, x1 = 0, y1 = 0
  for (const l of Object.values(data.layers)) {
    const [x, y, w, h] = l.rect
    x0 = Math.min(x0, x); y0 = Math.min(y0, y)
    x1 = Math.max(x1, x + w); y1 = Math.max(y1, y + h)
  }
  y0 = Math.min(y0, data.horizon - 0.06)
  const pad = 0.012
  x0 = Math.max(0, x0 - pad); y0 = Math.max(0, y0 - pad)
  x1 = Math.min(1, x1 + pad); y1 = Math.min(1, y1 + pad)

  const cover = Math.max(vw / W, vh / H)
  const fit = Math.min(vw / ((x1 - x0) * W), vh / ((y1 - y0) * H))
  const scale = Math.min(cover, fit)
  const width = W * scale
  const height = H * scale
  // when something has to be cropped, give up the near edge of the table before the hall
  const yAnchor = Math.max(0, Math.min(y0, data.horizon - 0.2))
  let left = vw / 2 - ((x0 + x1) / 2) * width
  let top = vh / 2 - ((yAnchor + y1) / 2) * height
  left = width >= vw ? Math.min(0, Math.max(vw - width, left)) : (vw - width) / 2
  top = height >= vh ? Math.min(0, Math.max(vh - height, top)) : (vh - height) / 2
  const density: Density = width * dpr > W * 0.62 ? '2x' : '1x'
  return { scale, width, height, left, top, density }
}
