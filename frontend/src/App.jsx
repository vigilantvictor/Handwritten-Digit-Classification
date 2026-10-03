import { useEffect, useRef, useState } from 'react'
import ThoughtLine from './components/ThoughtLine.jsx'

const steps = ['Preparing the image', 'Matching the handwriting', 'Reading the most likely digit']

export default function App() {
  const canvasRef = useRef(null)
  const fileRef = useRef(null)
  const [mode, setMode] = useState('draw')
  const [theme, setTheme] = useState(() => localStorage.getItem('digit-theme') || 'dark')
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem('digit-theme', theme) }, [theme])
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const context = canvas.getContext('2d')
    context.fillStyle = '#090a0d'
    context.fillRect(0, 0, canvas.width, canvas.height)
  }, [mode])
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])

  const clearDrawing = () => {
    const canvas = canvasRef.current
    if (!canvas) return
    const context = canvas.getContext('2d')
    context.fillStyle = '#090a0d'
    context.fillRect(0, 0, canvas.width, canvas.height)
    setResult(null); setError('')
  }

  const point = event => {
    const rect = canvasRef.current.getBoundingClientRect()
    return { x: (event.clientX - rect.left) * canvasRef.current.width / rect.width,
      y: (event.clientY - rect.top) * canvasRef.current.height / rect.height }
  }
  const startDraw = event => {
    const canvas = canvasRef.current
    canvas.setPointerCapture(event.pointerId)
    const p = point(event)
    const ctx = canvas.getContext('2d')
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 42; ctx.lineCap = 'round'; ctx.lineJoin = 'round'
    ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(p.x + .01, p.y + .01); ctx.stroke()
  }
  const draw = event => {
    if (!event.buttons) return
    const p = point(event), ctx = canvasRef.current.getContext('2d')
    ctx.lineTo(p.x, p.y); ctx.stroke()
  }

  const chooseFile = event => {
    const picked = event.target.files?.[0]
    if (!picked) return
    if (!picked.type.startsWith('image/')) { setError('Choose an image file such as PNG, JPG, or WEBP.'); return }
    setFile(picked); setPreview(URL.createObjectURL(picked)); setResult(null); setError('')
  }

  const predict = async () => {
    setError(''); setResult(null)
    let imageBlob
    if (mode === 'draw') {
      const canvas = canvasRef.current
      if (!canvas || !canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data.some((value, i) => i % 4 !== 3 && value > 20)) {
        setError('Draw a digit on the canvas first.'); return
      }
      imageBlob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'))
    } else {
      if (!file) { setError('Choose a picture first.'); return }
      imageBlob = file
    }
    const body = new FormData()
    body.append('image', imageBlob, file?.name || 'drawing.png')
    setLoading(true)
    try {
      const response = await fetch('/api/predict', { method: 'POST', body })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.error || 'The prediction could not be completed.')
      setResult(payload.digit)
    } catch (err) {
      setError(err.message === 'Failed to fetch'
        ? 'The prediction service is not running. Start the Python backend, then try again.'
        : err.message)
    } finally { setLoading(false) }
  }

  return <div className="site-shell">
    <header className="topbar">
      <a className="brand" href="#top" aria-label="Digit Studio home"><span className="brand-mark" aria-hidden="true">d</span><span>digit<span className="brand-light">studio</span></span></a>
      <nav className="nav-links"><a href="#recognizer">Try the recognizer</a><a href="#about">About</a></nav>
      <button className="theme-toggle" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} title="Toggle theme">
        <span aria-hidden="true">{theme === 'dark' ? '☼' : '◐'}</span><span className="theme-name">{theme === 'dark' ? 'Light' : 'Dark'} mode</span>
      </button>
    </header>

    <main id="top">
      <section className="hero">
        <div className="eyebrow"><span className="eyebrow-dot" /> A small experiment in machine learning</div>
        <h1>Every number has<br /><span>a little character.</span></h1>
        <p className="hero-copy">Write a digit or choose a picture. See how a model trained on thousands of handwritten examples reads it.</p>
        <a href="#recognizer" className="hero-link">Try it yourself <span aria-hidden="true">↓</span></a>
        <div className="hero-index" aria-hidden="true"><span>MNIST</span><i /> 0—9</div>
      </section>

      <section id="recognizer" className="recognizer-section">
        <div className="section-heading"><div><span className="section-kicker">THE RECOGNIZER</span><h2>Give it a number</h2></div><span className="model-tag"><span /> SVM · MNIST</span></div>
        <div className="workbench">
          <div className="input-panel">
            <div className="mode-tabs" role="tablist" aria-label="Choose an input method">
              <button role="tab" aria-selected={mode === 'draw'} className={mode === 'draw' ? 'active' : ''} onClick={() => { setMode('draw'); setResult(null); setError('') }}><span className="tab-icon">✎</span> Draw</button>
              <button role="tab" aria-selected={mode === 'upload'} className={mode === 'upload' ? 'active' : ''} onClick={() => { setMode('upload'); setResult(null); setError('') }}><span className="tab-icon">↥</span> Upload</button>
            </div>
            {mode === 'draw' ? <div className="draw-area">
              <div className="canvas-frame"><canvas ref={canvasRef} width="560" height="560" onPointerDown={startDraw} onPointerMove={draw} className="draw-canvas" aria-label="Draw your digit here" /></div>
              <div className="canvas-caption"><span>Use your mouse or touch</span><button className="text-button" onClick={clearDrawing}>Clear canvas</button></div>
            </div> : <div className="upload-area">
              <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" onChange={chooseFile} hidden />
              <button className={`dropzone ${preview ? 'has-preview' : ''}`} onClick={() => fileRef.current?.click()}>
                {preview ? <><img src={preview} alt="Selected handwritten digit" /><span className="replace-file">Choose another image</span></> : <><span className="upload-symbol">↥</span><strong>Choose an image</strong><span>PNG, JPG or WEBP</span><small>For best results, use a clear image with one dark digit on a plain background.</small></>}
              </button>
              {file && <div className="file-name"><span className="file-dot" />{file.name}</div>}
            </div>}
            <div className="panel-actions"><span className="privacy-note"><span>◉</span> Your image is processed for this prediction</span><button className="predict-button" onClick={predict} disabled={loading}>{loading ? 'Reading…' : 'Recognize digit'}<span aria-hidden="true">↗</span></button></div>
          </div>

          <aside className="answer-panel" aria-live="polite">
            <div className="answer-top"><span className="section-kicker">THE MODEL READS</span><span className="answer-spark" aria-hidden="true">✳</span></div>
            {loading ? <div className="answer-loading"><div className="loading-orbit"><span /></div><ThoughtLine working steps={steps} label="Reading your handwriting…" /></div>
              : result !== null ? <div className="prediction-result"><span className="result-label">PREDICTED DIGIT</span><div className="result-digit">{result}</div><p className="result-description">That’s the model’s best read of your handwriting.</p><button className="try-again" onClick={() => { setResult(null); if (mode === 'draw') clearDrawing() }}>Try another <span>↗</span></button></div>
              : <div className="answer-empty"><div className="empty-glyph" aria-hidden="true">?</div><p>Your result will appear here.</p><span>Draw or upload a single digit to begin.</span></div>}
            {error && <div className="error-message" role="alert">{error}</div>}
            <div className="answer-foot"><span>0—9</span><span>28 × 28 pixels</span></div>
          </aside>
        </div>
      </section>

      <section id="about" className="about-strip"><div><span className="section-kicker">A LITTLE CONTEXT</span><h2>From ink to an idea.</h2></div><p>The recognizer was trained on the MNIST collection of handwritten digits. It looks at the shape and placement of pixels, then chooses the number it thinks fits best. Different handwriting can lead to different answers—that’s part of the experiment.</p></section>
    </main>
    <footer className="footer"><a className="brand footer-brand" href="#top"><span className="brand-mark">d</span><span>digit<span className="brand-light">studio</span></span></a><span>A student machine learning project</span><a href="#top">Back to top ↑</a></footer>
  </div>
}



