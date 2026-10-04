import { useMemo, useRef } from 'react'
import Dialog, { CloseButton } from './Dialog'
import { articleById, articles } from '../content/articles'
import type { SliceId } from '../content/articles'

interface Props {
  id: SliceId | null
  onClose: () => void
  onNavigate: (id: SliceId) => void
}

const ORDINALS = ['prima', 'seconda', 'terza', 'quarta', 'quinta', 'sesta']

/** Split "Main (read: aside)" so the aside can be set smaller — the text itself is untouched. */
function splitTitle(t: string): [string, string | null] {
  const i = t.indexOf(' (read:')
  return i === -1 ? [t, null] : [t.slice(0, i), t.slice(i)]
}

/** The article, printed like an oversized Italian menu laid over the tray. */
export default function ArticleModal({ id, onClose, onNavigate }: Props) {
  const scroller = useRef<HTMLDivElement>(null)
  const heading = useRef<HTMLHeadingElement>(null)
  const article = id ? articleById[id] : null
  const idx = id ? articles.findIndex((a) => a.id === id) : -1
  const prev = idx > 0 ? articles[idx - 1] : null
  const next = idx >= 0 && idx < articles.length - 1 ? articles[idx + 1] : null
  const [main, aside] = useMemo(() => (article ? splitTitle(article.title) : ['', null]), [article])

  const go = (to: SliceId) => {
    onNavigate(to)
    scroller.current?.scrollTo({ top: 0 })
    requestAnimationFrame(() => heading.current?.focus({ preventScroll: true }))
  }

  return (
    <Dialog open={!!article} onClose={onClose} labelledBy="article-title" className="overlay-article" initialFocus={() => heading.current}>
      {article && (
        <article className="menu-sheet" key={article.id}>
          <CloseButton onClick={onClose} label="Close article" />
          <div className="menu-scroll" ref={scroller}>
            <header className="menu-head">
              <p className="kicker">
                <span>La Felicità</span>
                <span className="dot" aria-hidden="true">·</span>
                <span>la {ORDINALS[idx]} fetta</span>
                <span className="dot" aria-hidden="true">·</span>
                <span className="kicker-crust">{article.crust}</span>
              </p>
              <h2 id="article-title" ref={heading} tabIndex={-1}>
                {main}
                {aside && <span className="title-aside">{aside}</span>}
              </h2>
              {article.subtitle && <p className="deck">{article.subtitle}</p>}
              <div className="flourish" aria-hidden="true">
                <span />
                <svg viewBox="0 0 40 12">
                  <path d="M2 6h10M28 6h10M20 1.5l4.5 4.5L20 10.5 15.5 6z" />
                </svg>
                <span />
              </div>
            </header>
            <div className="menu-body">
              {article.blocks.map((b, i) => {
                if (b.type === 'h') return <h3 key={i}>{b.text}</h3>
                if (b.type === 'ul')
                  return (
                    <ul key={i}>
                      {b.items.map((it, j) => (
                        <li key={j}>{it}</li>
                      ))}
                    </ul>
                  )
                return <p key={i}>{b.text}</p>
              })}
            </div>
            <footer className="menu-foot">
              {prev ? (
                <button type="button" className="turn prev" onClick={() => go(prev.id)}>
                  <span aria-hidden="true">←</span> <span className="sr-only">Previous slice: </span>
                  {prev.crust}
                </button>
              ) : (
                <span />
              )}
              <span className="foot-mark" aria-hidden="true">
                {idx + 1} / {articles.length}
              </span>
              {next ? (
                <button type="button" className="turn next" onClick={() => go(next.id)}>
                  <span className="sr-only">Next slice: </span>
                  {next.crust} <span aria-hidden="true">→</span>
                </button>
              ) : (
                <span />
              )}
            </footer>
          </div>
        </article>
      )}
    </Dialog>
  )
}
