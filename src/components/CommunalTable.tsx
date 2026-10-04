import { memo } from 'react'

/** The shared wooden table and the worn tray, with the food lifted off (it lives in its own layers). */
function CommunalTable({ src, onLoad }: { src: string; onLoad: () => void }) {
  return (
    <div className="table-plate" aria-hidden="true">
      <img src={src} alt="" draggable={false} decoding="async" fetchPriority="high" onLoad={onLoad} />
    </div>
  )
}

export default memo(CommunalTable)
