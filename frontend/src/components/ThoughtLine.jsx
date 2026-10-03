import { useEffect, useState } from 'react'
import { animate, useReducedMotion } from 'motion/react'
import { HugeiconsIcon } from '@hugeicons/react'
import { SparklesIcon, Tick02Icon } from '@hugeicons/core-free-icons'
import './ThoughtLine.css'

/** A compact adaptation of the supplied React Bits ThoughtLine for digit inference. */
export default function ThoughtLine({ working, steps = [], label = 'Reading your digit…' }) {
  const reduced = useReducedMotion()
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    if (!working) return
    const start = performance.now()
    const timer = window.setInterval(() => setElapsed((performance.now() - start) / 1000), 100)
    return () => window.clearInterval(timer)
  }, [working])
  useEffect(() => {
    if (!working || reduced) return
    const glyph = document.querySelector('.thought-line__glyph')
    if (!glyph) return
    const animation = animate(glyph, { opacity: [0.54, 1, 0.54], scale: [0.96, 1.04, 0.96] }, {
      duration: 1.6, ease: [0.77, 0, 0.175, 1], repeat: Infinity,
    })
    return () => animation.stop()
  }, [working, reduced])
  if (!working) return null
  return <div className="thought-line" role="status" aria-live="polite">
    <div className="thought-line__head">
      <span className="thought-line__glyph" aria-hidden="true"><HugeiconsIcon icon={SparklesIcon} size="100%" /></span>
      <span className="thought-line__breath">{label}</span>
      <span className="thought-line__timer">{elapsed.toFixed(1)}s</span>
    </div>
    <div className="thought-line__trace">
      {steps.map((step, index) => <div className="thought-line__step" key={step}>
        <span className="thought-line__mark">{index < steps.length - 1
          ? <HugeiconsIcon icon={Tick02Icon} size="100%" />
          : <i className="thought-line__pulse" />}</span>
        <span>{step}</span>
      </div>)}
    </div>
  </div>
}
