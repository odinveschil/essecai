import { useCallback, useRef, useState } from 'react'
import LaFelicitaScene from './components/LaFelicitaScene'
import ArticleModal from './components/ArticleModal'
import VideoModal from './components/VideoModal'
import type { SliceId } from './content/articles'
import type { VideoKey } from './config/videos'

export default function App() {
  const [article, setArticle] = useState<SliceId | null>(null)
  const [video, setVideo] = useState<VideoKey | null>(null)
  const opener = useRef<HTMLElement | SVGElement | null>(null)

  const rememberOpener = () => {
    opener.current = document.activeElement as HTMLElement | SVGElement | null
  }

  const openArticle = useCallback((id: SliceId) => {
    rememberOpener()
    setVideo(null)
    setArticle(id)
  }, [])

  const openVideo = useCallback((key: VideoKey) => {
    rememberOpener()
    setArticle(null)
    setVideo(key)
  }, [])

  const close = useCallback(() => {
    setArticle(null)
    setVideo(null)
    // hand focus back to the slice / glass / dessert that opened the overlay
    requestAnimationFrame(() => {
      const el = opener.current
      if (el && 'focus' in el && document.contains(el as Node)) (el as HTMLElement).focus({ preventScroll: true })
    })
  }, [])

  const open = article !== null || video !== null

  return (
    <>
      <LaFelicitaScene onOpenArticle={openArticle} onOpenVideo={openVideo} dimmed={open} />
      <ArticleModal id={article} onClose={close} onNavigate={setArticle} />
      <VideoModal videoKey={video} onClose={close} />
    </>
  )
}
