import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowDownToLine, ArrowRight, Check, Code2, Eye, EyeOff, FileCode2,
  ImagePlus, LoaderCircle, LockKeyhole, LogOut, ScanText, ShieldCheck,
  Sparkles, WandSparkles,
} from 'lucide-react';

const STORAGE_KEY = 'smart-sketch-latest-result-v4';

function makePreview(html, css, javascript) {
  if (!html) return '';
  const withStyles = html.replace(/<link\s+rel="stylesheet"[^>]*>/i, `<style>${css || ''}</style>`);
  return withStyles.replace('</body>', `<script>${javascript || ''}</script></body>`);
}

function saveFile(name, contents, type) {
  const url = URL.createObjectURL(new Blob([contents], { type }));
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function Brand({ inverse = false }) {
  return <a className={`brand ${inverse ? 'brand-inverse' : ''}`} href="#top" aria-label="Sketchflow home">
    <span className="brand-mark"><WandSparkles size={18} /></span>
    <span className="brand-name">sketchflow<span>.</span><small>SKETCH TO CODE</small></span>
  </a>;
}

function LoginScreen({ onSignedIn, setupMessage = '' }) {
  const [isSignup, setIsSignup] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(setupMessage);

  async function submit(event) {
    event.preventDefault();
    if (isSignup && password !== confirmPassword) { setError('The passwords do not match.'); return; }
    setBusy(true);
    setError('');
    try {
      const response = await fetch(`/api/auth/${isSignup ? 'register' : 'login'}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(isSignup ? { username, email, password } : { username, password }),
      });
      const data = await response.json();
      if (!response.ok) {
        const message = Array.isArray(data.detail) ? data.detail.map((item) => item.msg).join(' ') : data.detail;
        throw new Error(message || (isSignup ? 'Registration failed.' : 'Sign in failed.'));
      }
      onSignedIn(data.username);
    } catch (cause) {
      setError(cause.message || 'Could not connect to the backend.');
    } finally {
      setBusy(false);
    }
  }

  return <main className="login-shell">
    <section className="login-story">
      <div className="story-top"><Brand inverse /><span className="secure-label"><ShieldCheck size={14} /> PRIVATE WORKSPACE</span></div>
      <div className="story-copy">
        <span className="eyebrow eyebrow-dark"><Sparkles size={14} /> YOUR IDEAS, READY TO BUILD</span>
        <h1>From a sketch<br />to <span>something real.</span></h1>
        <p>Turn a hand-drawn interface into a working preview and clean, editable front-end code.</p>
      </div>
      <div className="story-visual" aria-hidden="true">
        <div className="visual-paper"><div className="paper-topline" /><div className="paper-title" /><div className="paper-field" /><div className="paper-field short" /><div className="paper-button" /><div className="paper-note">YOUR SKETCH</div></div>
        <div className="visual-connector"><span /><ArrowRight size={19} /><span /></div>
        <div className="visual-code"><div className="code-lights"><i /><i /><i /></div><span className="code-line purple" /><span className="code-line long" /><span className="code-line medium" /><span className="code-line green" /><span className="code-line short" /><span className="code-label">HTML · CSS · JS</span></div>
      </div>
      <div className="story-foot"><span><Check size={14} /> Image to interface</span><span><Check size={14} /> Three exportable files</span><span><Check size={14} /> Live preview</span></div>
    </section>

    <section className="login-side">
      <div className="login-card">
        <div className="login-icon"><LockKeyhole size={20} /></div>
        <span className="login-kicker">{isSignup ? 'GET STARTED' : 'WELCOME BACK'}</span>
        <h2>{isSignup ? 'Create your account' : 'Sign in to Sketchflow'}</h2>
        <p className="login-description">{isSignup ? 'Create an account to start your sketch workspace.' : 'Use your email or username to open the sketch workspace.'}</p>
        {error && <div className="error-message login-error" role="alert">{error}</div>}
        <form className="login-form" onSubmit={submit}>
          {isSignup ? <>
            <label htmlFor="username">Username</label>
            <input id="username" name="username" autoComplete="username" minLength="3" maxLength="32" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="Choose a username" required />
            <label className="signup-field-label" htmlFor="email">Email</label>
            <input id="email" name="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" required />
          </> : <>
            <label htmlFor="username">Email or username</label>
            <input id="username" name="username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="Enter your email or username" required />
          </>}
          <div className="password-heading"><label htmlFor="password">Password</label></div>
          <div className="password-input-wrap"><input id="password" name="password" type={showPassword ? 'text' : 'password'} minLength={isSignup ? 8 : undefined} autoComplete={isSignup ? 'new-password' : 'current-password'} value={password} onChange={(event) => setPassword(event.target.value)} placeholder={isSignup ? 'At least 8 characters' : 'Enter your password'} required /><button type="button" className="password-toggle" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword((value) => !value)}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div>
          {isSignup && <><div className="password-heading"><label htmlFor="confirm-password">Confirm password</label></div><input id="confirm-password" name="confirm-password" type="password" autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Enter your password again" required /></>}
          <button className="login-button" type="submit" disabled={busy}>{busy ? <><LoaderCircle className="spin" size={17} /> Please wait…</> : isSignup ? <>Create account <ArrowRight size={17} /></> : <>Enter workspace <ArrowRight size={17} /></>}</button>
        </form>
        <div className="signup-switch">{isSignup ? 'Already registered?' : 'New to Sketchflow?'} <button type="button" onClick={() => { setIsSignup((value) => !value); setError(''); }}>{isSignup ? 'Sign in' : 'Create an account'}</button></div>
        <div className="login-security"><ShieldCheck size={15} /><span>Private sign-in · Your API key stays on the server</span></div>
      </div>
      <div className="login-footer">SKETCHFLOW <span>·</span> A COMPUTER VISION PROJECT</div>
    </section>
  </main>;
}

function App() {
  const inputRef = useRef(null);
  const [authState, setAuthState] = useState('checking');
  const [username, setUsername] = useState('');
  const [setupMessage, setSetupMessage] = useState('');
  const [file, setFile] = useState(null);
  const [imageUrl, setImageUrl] = useState('');
  const [result, setResult] = useState(() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null'); } catch { return null; }
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('preview');
  const [provider, setProvider] = useState('auto');
  const basename = useMemo(() => (file?.name || 'sketch').replace(/\.[^.]+$/, '').replace(/[^a-z0-9_-]+/gi, '-').replace(/^-|-$/g, '').toLowerCase() || 'sketch', [file]);

  useEffect(() => {
    let active = true;
    fetch('/api/auth/me', { credentials: 'same-origin' })
      .then(async (response) => {
        const data = await response.json();
        if (!active) return;
        if (response.ok && data.authenticated) {
          setUsername(data.username);
          setAuthState('signed-in');
        } else {
          if (response.status === 503) setSetupMessage(data.detail || 'Configure login settings in .env.');
          setAuthState('signed-out');
        }
      })
      .catch(() => { if (active) setAuthState('signed-out'); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!result) return;
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(result)); } catch { /* Keep large results available in memory. */ }
  }, [result]);
  useEffect(() => () => { if (imageUrl) URL.revokeObjectURL(imageUrl); }, [imageUrl]);

  function selectFile(nextFile) {
    if (!nextFile) return;
    if (!nextFile.type.startsWith('image/')) { setError('Choose a PNG, JPG, WEBP, or BMP image.'); return; }
    if (nextFile.size > 12 * 1024 * 1024) { setError('The image must be smaller than 12 MB.'); return; }
    if (imageUrl) URL.revokeObjectURL(imageUrl);
    setFile(nextFile);
    setImageUrl(URL.createObjectURL(nextFile));
    setError('');
  }

  async function analyze() {
    if (!file) { setError('Choose a sketch image first.'); return; }
    setBusy(true); setError('');
    try {
      const body = new FormData();
      body.append('file', file);
      body.append('provider', provider);
      const response = await fetch('/api/analyze', { method: 'POST', body, credentials: 'same-origin' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Analysis failed.');
      setResult({ ...data, filename: basename, created_at: new Date().toISOString() });
      setActiveTab('preview');
    } catch (cause) {
      setError(cause.message || 'Could not connect to the API. Start the backend and try again.');
    } finally { setBusy(false); }
  }

  async function signOut() {
    try { await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' }); } catch { /* Clear this browser even if the server is offline. */ }
    localStorage.removeItem(STORAGE_KEY);
    setResult(null);
    setFile(null);
    if (imageUrl) URL.revokeObjectURL(imageUrl);
    setImageUrl('');
    setUsername('');
    setAuthState('signed-out');
  }

  function downloadGenerated(kind) {
    if (!result) return;
    const stamp = new Date(result.created_at || Date.now()).toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z');
    const stem = `${result.filename || 'sketch'}-${stamp}`;
    if (kind === 'html') {
      const html = result.html
        .replace('href="style.css"', `href="${stem}.css"`)
        .replace('src="script.js"', `src="${stem}.js"`);
      saveFile(`${stem}.html`, html, 'text/html;charset=utf-8');
    } else if (kind === 'css') {
      saveFile(`${stem}.css`, result.css, 'text/css;charset=utf-8');
    } else {
      saveFile(`${stem}.js`, result.javascript || '', 'text/javascript;charset=utf-8');
    }
  }

  if (authState === 'checking') return <div className="auth-loading"><LoaderCircle className="spin" size={22} /><span>Opening your workspace…</span></div>;
  if (authState !== 'signed-in') return <LoginScreen setupMessage={setupMessage} onSignedIn={(name) => { setUsername(name); setSetupMessage(''); setAuthState('signed-in'); }} />;

  const words = result?.recognized_text || [];
  const elements = result?.elements || [];
  const confidence = words.length ? Math.round(words.reduce((sum, word) => sum + word.confidence, 0) / words.length * 100) : 0;

  return <div className="app-shell">
    <header className="topbar">
      <Brand />
      <div className="topbar-right"><span className="topbar-state"><span className="status-dot" /> API workspace</span><span className="topbar-divider" /><span className="user-chip">{username}</span><button className="signout-button" onClick={signOut}><LogOut size={14} /> Sign out</button><a href="/docs" target="_blank" rel="noreferrer">API docs <ArrowDownToLine size={13} /></a></div>
    </header>

    <main id="top" className="main-wrap">
      <section className="intro">
        <div className="eyebrow"><Sparkles size={14} /> FROM WHITEBOARD TO WORKING UI</div>
        <h1>Your sketch,<br /><span>ready for the web.</span></h1>
        <p>Upload a hand-drawn interface. We’ll find its shapes, read its labels, and turn it into code you can preview and edit.</p>
      </section>

      <section className="workspace">
        <div className="upload-card">
          <div className="section-heading"><span className="step-num">01</span><div><h2>Upload your sketch</h2><p>Use a clear photo or scan for the best results.</p></div></div>
          <button className={`dropzone ${file ? 'has-file' : ''}`} onClick={() => inputRef.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); selectFile(event.dataTransfer.files[0]); }}>
            {imageUrl ? <img className="uploaded-image" src={imageUrl} alt="Selected sketch" /> : <span className="upload-icon"><ImagePlus size={24} /></span>}
            <strong>{file ? file.name : 'Drop your sketch here'}</strong><span>{file ? 'Click to choose a different image' : 'or click to browse your files'}</span>
            <em>PNG · JPG · WEBP · BMP <i>UP TO 12 MB</i></em>
          </button>
          <input ref={inputRef} hidden type="file" accept="image/png,image/jpeg,image/webp,image/bmp" onChange={(event) => selectFile(event.target.files[0])} />
          {error && <div className="error-message" role="alert">{error}</div>}
          <button className="analyze-button" onClick={analyze} disabled={busy || !file}>{busy ? <><LoaderCircle className="spin" size={17} /> Reading sketch…</> : <><WandSparkles size={17} /> Generate my UI</>}</button>
          <label className="provider-control"><span>Analysis engine</span><select value={provider} onChange={(event) => setProvider(event.target.value)}><option value="auto">Auto (OpenAI if configured)</option><option value="openai">OpenAI Vision API</option><option value="local">Local EasyOCR</option></select></label>
          <div className="privacy-note"><ScanText size={14} /> OpenAI mode sends this image to OpenAI; API usage may be billed.</div>
        </div>

        <div className="result-card">
          <div className="result-heading"><div className="section-heading"><span className="step-num">02</span><div><h2>Your generated interface</h2><p>{result ? `${elements.length} elements found` : 'Your live preview appears here.'}</p></div></div>
            {result && <div className="download-actions"><button className="download-button" onClick={() => downloadGenerated('html')}><ArrowDownToLine size={14} /> HTML</button><button className="download-button" onClick={() => downloadGenerated('css')}><ArrowDownToLine size={14} /> CSS</button><button className="download-button" onClick={() => downloadGenerated('javascript')}><ArrowDownToLine size={14} /> JS</button></div>}
          </div>
          {result ? <>
            <div className="tabs"><button className={activeTab === 'preview' ? 'selected' : ''} onClick={() => setActiveTab('preview')}><Sparkles size={14} /> Live preview</button><button className={activeTab === 'html' ? 'selected' : ''} onClick={() => setActiveTab('html')}><Code2 size={14} /> HTML</button><button className={activeTab === 'css' ? 'selected' : ''} onClick={() => setActiveTab('css')}><FileCode2 size={14} /> CSS</button><button className={activeTab === 'javascript' ? 'selected' : ''} onClick={() => setActiveTab('javascript')}><Code2 size={14} /> JavaScript</button></div>
            <div className="preview-frame">{activeTab === 'preview' ? <iframe title="Generated interface preview" sandbox="allow-scripts" srcDoc={makePreview(result.html, result.css, result.javascript)} /> : <pre><code>{activeTab === 'html' ? result.html : activeTab === 'css' ? result.css : result.javascript}</code></pre>}</div>
            <div className="insights"><div className="insight-title"><ScanText size={16} /><div><strong>Text recognition · {result.analysis_provider === 'openai' ? 'OpenAI Vision' : 'Local EasyOCR'}</strong><span>{words.length} items · {confidence}% estimated confidence (review the result)</span></div><Check className="check-icon" size={17} /></div>
              {words.length ? <div className="word-list">{words.map((word, index) => <span key={`${word.text}-${index}`} title={`Confidence: ${Math.round(word.confidence * 100)}%`}>{word.text}<small>{Math.round(word.confidence * 100)}%</small></span>)}</div> : <p className="no-words">No text was detected. Try a sharper, well-lit image with clear handwriting.</p>}
            </div>
          </> : <div className="empty-result"><div className="empty-art"><div className="art-page"><span /><span /><span /><span /></div><div className="art-arrow">→</div><div className="art-code">&lt;/&gt;</div></div><strong>Make your first sketch come alive</strong><span>Your generated page will show up here, ready to preview and download.</span><div className="empty-badges"><span><Check size={13} /> Editable HTML</span><span><Check size={13} /> Separate CSS</span><span><Check size={13} /> Interactive JS</span></div></div>}
        </div>
      </section>

      <section className="how-it-works"><div><span className="mini-icon"><ScanText size={16} /></span><strong>Finds the layout</strong><span>OpenCV detects sketch shapes and positions.</span></div><div><span className="mini-icon"><Sparkles size={16} /></span><strong>Reads the labels</strong><span>OCR recognizes words and confidence scores.</span></div><div><span className="mini-icon"><Code2 size={16} /></span><strong>Builds your page</strong><span>Preview and export HTML, CSS, and JavaScript.</span></div></section>
      <footer>SKETCHFLOW <span>·</span> A COMPUTER VISION PROJECT</footer>
    </main>
  </div>;
}

export default App;
