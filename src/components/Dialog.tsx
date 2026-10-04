import { useEffect, useRef, useState } from 'react'
import type { ReactNode, PointerEvent as RPointerEvent } from 'react'

interface Props {
  open: boolean
  onClose: () => void
  labelledBy: string
  className: string
  children: ReactNode
  /** returns the element (inside the dialog) that receives focus on open */
  initialFocus?: () => HTMLElement | null
}

const FOCUSABLE = 'a[href],button:not([disabled]),video,[tabindex]:not([tabindex="-1"]),input,select,textarea'
const EXIT_MS = 240

/**
 * Overlay shell shared by the article and the video: Escape, click-outside and
 * an X close it; focus is trapped inside while it is open; the page behind
 * cannot scroll.
 */
export default function Dialog({ open, onClose, labelledBy, className, children, initialFocus }: Props) {
  const [mounted, setMounted] = useState(open)
  const [shown, setShown] = useState(false)
  const panel = useRef<HTMLDivElement>(null)
  const downOnBackdrop = useRef(false)
  const lastChildren = useRef(children)
  if (open) lastChildren.current = children
  const focusTarget = useRef(initialFocus)
  focusTarget.current = initialFocus

  useEffect(() => {
    if (open) {
      setMounted(true)
      const r = requestAnimationFrame(() => requestAnimationFrame(() => setShown(true)))
      return () => cancelAnimationFrame(r)
    }
    setShown(false)
    const t = window.setTimeout(() => setMounted(false), EXIT_MS)
    return () => window.clearTimeout(t)
  }, [open])

  useEffect(() => {
    if (!open) return
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    document.documentElement.classList.add('has-overlay')
    const t = window.setTimeout(() => {
      const target = focusTarget.current?.() ?? panel.current
      target?.focus({ preventScroll: true })
    }, 30)
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
        return
      }
      if (e.key === 'Tab' && panel.current) {
        const els = Array.from(panel.current.querySelectorAll<HTMLElement>(FOCUSABLE)).filter((el) => !el.hasAttribute('hidden'))
        if (!els.length) return
        const first = els[0]
        const last = els[els.length - 1]
        if (e.shiftKey && (document.activeElement === first || document.activeElement === panel.current)) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }
    document.addEventListener('keydown', onKey)
    return () => {
      window.clearTimeout(t)
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
      document.documentElement.classList.remove('has-overlay')
    }
  }, [open, onClose])

  if (!mounted) return null

  // close only on a click that both starts and ends outside the panel
  const onDown = (e: RPointerEvent) => {
    downOnBackdrop.current = e.target === e.currentTarget || e.target === panel.current
  }
  const onUp = (e: RPointerEvent) => {
    if (downOnBackdrop.current && (e.target === e.currentTarget || e.target === panel.current)) onClose()
    downOnBackdrop.current = false
  }

  return (
    <div className={`overlay ${className} ${shown ? 'is-shown' : ''}`} onPointerDown={onDown} onPointerUp={onUp}>
      <div
        ref={panel}
        className="overlay-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        tabIndex={-1}
      >
        {open ? children : lastChildren.current}
      </div>
    </div>
  )
}

export function CloseButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button type="button" className="close-x" onClick={onClick} aria-label={label}>
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M6 6l12 12M18 6L6 18" />
      </svg>
    </button>
  )
}
