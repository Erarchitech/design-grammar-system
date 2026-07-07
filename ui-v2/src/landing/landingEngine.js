// Landing particle-ring engine — ported from the V2 design mockup
// (design/v2/Design Grammars V2.dc.html, data-dc-script). Owns the landing
// canvas: the particle ring with gaussian peaks toward the three region
// anchors, the leader-line callouts, and the hero title that materialises
// from / dissolves into the particle cloud. DOM elements it animates every
// frame (hero title, hero-beneath, region labels) are styled ONLY here —
// their React JSX carries classes, not style props, so re-renders never
// clobber engine-owned values.

const ANCH = [
  { key: "graph", ang: Math.PI * 1.06, amp: 0.95, sig: 0.3 },
  { key: "model", ang: -0.2, amp: 1.0, sig: 0.26 },
  { key: "projects", ang: Math.PI * 0.62, amp: 0.72, sig: 0.22 }
];

const TH = {
  ink: "#0a0a0a",
  leader: "rgba(10,10,10,0.38)",
  paper: "#f5f5f5"
};

function rng(seed) {
  let t = seed >>> 0;
  return function () {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}
function gauss(R) {
  let u = 0,
    v = 0;
  while (!u) u = R();
  while (!v) v = R();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(6.28318 * v);
}
function angDiff(a, b) {
  let d = (a - b) % 6.283185307;
  if (d > 3.141592653) d -= 6.283185307;
  if (d < -3.141592653) d += 6.283185307;
  return d;
}
const clamp01 = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);
const smooth = (a, b, x) => {
  const t = clamp01((x - a) / (b - a));
  return t * t * (3 - 2 * t);
};

export default class LandingEngine {
  /**
   * @param els {{canvas, heroTitle, heroL1, heroL2, heroBeneath, labels: Record<'graph'|'model'|'projects', HTMLElement>, hint, heroForm}}
   */
  constructor(els, { density = 2 } = {}) {
    this.els = els;
    this.density = density;
    this.authOpen = false;
    this.visible = true;
    this.heroPh = "hidden";
    this.heroT0 = 0;
    this.heroParts = null;
    this.fontsReady = false;
    this.pk = {}; // ring points per region key (used as fly() transform origins)
    this._lls = [];
    this._stop = false;
  }

  start() {
    this._stop = false;
    this.resize();
    this.initParticles();
    this.initHeroWhenReady();
    this._onResize = () => this.resize();
    window.addEventListener("resize", this._onResize);
    this._raf = requestAnimationFrame(this.tick.bind(this));
  }
  stop() {
    this._stop = true;
    cancelAnimationFrame(this._raf);
    window.removeEventListener("resize", this._onResize);
  }
  setVisible(v) {
    this.visible = v;
  }
  setAuthOpen(open) {
    this.authOpen = open;
    this.setNavLabels(!open);
    this.layoutLanding();
  }

  tick(ts) {
    if (this._stop) return;
    this._raf = requestAnimationFrame(this.tick.bind(this));
    // Self-heal: some embed contexts report 0×0 at mount and never fire a
    // resize event — re-measure every frame and rebuild layout on change.
    if (window.innerWidth !== this._vw || window.innerHeight !== this._vh) this.resize();
    if (!this.visible || !this._vw) return;
    this.drawLanding(ts / 1000);
  }

  resize() {
    this._vw = window.innerWidth;
    this._vh = window.innerHeight;
    this._dpr = Math.min(window.devicePixelRatio || 1, 2);
    const c = this.els.canvas;
    if (c) {
      c.width = this._vw * this._dpr;
      c.height = this._vh * this._dpr;
      this._ctx = c.getContext("2d");
    }
    this.layoutLanding();
    this.layoutHero();
    if (this.fontsReady) this.sampleHeroTargets();
  }

  /* ---------------- particle ring ---------------- */
  initParticles() {
    const R = rng(7);
    const N = Math.round(5200 * this.density);
    this._parts = [];
    for (let i = 0; i < N; i++) {
      const wide = R() < 0.18;
      this._parts.push({
        a: R() * 6.28318,
        j: gauss(R) * (wide ? 13 : 4.5),
        u: Math.pow(R(), 1.6),
        s: 0.5 + R() * 0.95,
        al: 0.16 + R() * 0.44,
        w: R() * 6.28,
        v: (R() - 0.5) * 0.02
      });
    }
  }
  peakEnv(a) {
    let e = 0.05;
    for (const an of ANCH) {
      const d = angDiff(a, an.ang);
      e += an.amp * Math.exp(-(d * d) / (2 * an.sig * an.sig));
    }
    return e;
  }

  /* ---------------- region callout layout ---------------- */
  layoutLanding() {
    if (!this._vw) return;
    const cx = this._vw / 2,
      cy = this._vh / 2,
      R = Math.min(this._vw, this._vh) * 0.365;
    const cfg = {
      graph: { el: this.els.labels.graph, out: 62 },
      model: { el: this.els.labels.model, out: 62 },
      projects: { el: this.els.labels.projects, out: 54 }
    };
    this._lls = [];
    this.pk = {};
    for (const an of ANCH) {
      const c = cfg[an.key];
      const dx = Math.cos(an.ang),
        dy = Math.sin(an.ang);
      const P = [cx + dx * R, cy + dy * R];
      const K = [cx + dx * (R + c.out), cy + dy * (R + c.out)];
      const right = dx >= 0;
      const tx = K[0] + (right ? 14 : -14);
      const hx = K[0] + (right ? 8 : -8);
      this._lls.push({ P, K, hx, ty: K[1] });
      this.pk[an.key] = P;
      const el = c.el;
      if (el) {
        el.style.left = "0px";
        el.style.top = "0px";
        el.style.textAlign = right ? "left" : "right";
        el.style.transform =
          "translate(" + tx + "px, " + K[1] + "px) translate(" + (right ? "0" : "-100%") + ", -50%)";
        el.style.transition = "opacity 300ms cubic-bezier(0.2,0,0,1)";
        el.style.opacity = this.authOpen ? "0" : "1";
      }
    }
  }
  setNavLabels(v) {
    const { labels, hint } = this.els;
    for (const e of [labels.graph, labels.model, labels.projects, hint]) {
      if (e) e.style.opacity = v ? "1" : "0";
    }
  }

  drawLanding(t) {
    const ctx = this._ctx;
    if (!ctx) return;
    const vw = this._vw,
      vh = this._vh;
    ctx.setTransform(this._dpr, 0, 0, this._dpr, 0, 0);
    ctx.clearRect(0, 0, vw, vh);
    const cx = vw / 2,
      cy = vh / 2,
      R = Math.min(vw, vh) * 0.365;
    ctx.fillStyle = TH.ink;
    for (const p of this._parts) {
      p.a += p.v * 0.016;
      const env = this.peakEnv(p.a);
      const sp =
        Math.pow(Math.abs(Math.sin(p.a * 41 + p.w + t * 0.1)), 3) * 0.62 +
        Math.pow(Math.abs(Math.sin(p.a * 13 - t * 0.05 + p.w * 2)), 2) * 0.38;
      const disp = env * (0.22 + 0.78 * sp);
      const rad = R + p.j + disp * p.u * R * 0.4;
      const x = cx + Math.cos(p.a) * rad,
        y = cy + Math.sin(p.a) * rad;
      ctx.globalAlpha = p.al * (0.55 + 0.45 * sp);
      ctx.fillRect(x, y, p.s, p.s);
    }
    ctx.globalAlpha = 1;
    if (!this.authOpen) {
      ctx.strokeStyle = TH.leader;
      ctx.lineWidth = 1;
      for (const L of this._lls) {
        ctx.beginPath();
        ctx.moveTo(L.P[0], L.P[1]);
        ctx.lineTo(L.K[0], L.K[1]);
        ctx.lineTo(L.hx, L.ty);
        ctx.stroke();
        for (const pt of [L.P, [L.hx, L.ty]]) {
          ctx.beginPath();
          ctx.arc(pt[0], pt[1], 3, 0, 6.29);
          ctx.fillStyle = TH.paper;
          ctx.fill();
          ctx.stroke();
        }
      }
    }
    this.drawHero(t);
  }

  /* ---------------- hero: title materialises from the cloud ---------------- */
  heroMetrics() {
    const vw = this._vw || window.innerWidth,
      vh = this._vh || window.innerHeight;
    const cx = vw / 2,
      cy = vh * 0.44;
    const { heroL1, heroL2 } = this.els;
    const s1 = heroL1 ? parseFloat(getComputedStyle(heroL1).fontSize) : Math.max(32, Math.min(76, vw * 0.052));
    const s2 = heroL2 ? parseFloat(getComputedStyle(heroL2).fontSize) : s1 * 0.42;
    const lh1 = s1 * 1.06,
      gap = s1 * 0.28,
      lh2 = s2 * 1.3;
    const H = lh1 + gap + lh2;
    const top = cy - H / 2;
    return { vw, vh, cx, cy, s1, s2, top, H, l1y: top + lh1 / 2, l2y: top + lh1 + gap + lh2 / 2 };
  }
  layoutHero() {
    const m = this.heroMetrics();
    const { heroTitle, heroBeneath, heroForm } = this.els;
    if (heroTitle) heroTitle.style.top = m.top + "px";
    if (heroBeneath) {
      heroBeneath.style.top = m.top + m.H + Math.max(30, m.s1 * 0.62) + "px";
      heroBeneath.style.transition = "opacity 220ms cubic-bezier(0.2,0,0,1)";
    }
    if (heroForm) heroForm.style.top = m.cy + "px";
  }
  sampleHeroTargets() {
    const m = this.heroMetrics();
    if (!m.vw || !m.vh) return;
    const cvs = document.createElement("canvas");
    cvs.width = m.vw;
    cvs.height = m.vh;
    const c = cvs.getContext("2d");
    c.textAlign = "center";
    c.textBaseline = "middle";
    c.fillStyle = "#000";
    c.font = "500 " + Math.round(m.s1) + 'px "Oswald", sans-serif';
    try {
      c.letterSpacing = "1px";
    } catch {
      /* older engines */
    }
    c.fillText("DESIGN GRAMMARS.", m.cx, m.l1y);
    c.font = "400 " + Math.round(m.s2) + 'px "Oswald", sans-serif';
    try {
      c.letterSpacing = "0.6px";
    } catch {
      /* older engines */
    }
    c.fillText("Encode your design intent.", m.cx, m.l2y);
    const data = c.getImageData(0, 0, m.vw, m.vh).data;
    const stride = Math.max(2, Math.round(4 / Math.max(0.6, this.density)));
    const pts = [];
    for (let y = 0; y < m.vh; y += stride) {
      for (let x = 0; x < m.vw; x += stride) {
        if (data[(y * m.vw + x) * 4 + 3] > 110)
          pts.push([x + (Math.random() - 0.5) * stride, y + (Math.random() - 0.5) * stride]);
      }
    }
    for (let i = pts.length - 1; i > 0; i--) {
      const j = (Math.random() * (i + 1)) | 0;
      const tmp = pts[i];
      pts[i] = pts[j];
      pts[j] = tmp;
    }
    const N = Math.min(pts.length, 2600);
    const R = Math.min(m.vw, m.vh) * 0.365;
    const parts = new Array(N);
    for (let i = 0; i < N; i++) {
      const ang = Math.random() * 6.28318,
        rr = R * (0.82 + Math.random() * 0.5);
      parts[i] = {
        tx: pts[i][0],
        ty: pts[i][1],
        hx: m.cx + Math.cos(ang) * rr,
        hy: m.cy + Math.sin(ang) * rr,
        d: Math.random() * 0.26,
        al: 0.5 + Math.random() * 0.5,
        s: 0.7 + Math.random() * 1.1,
        cur: 6 + Math.random() * 22,
        ca: Math.random() * 6.28318
      };
    }
    this.heroParts = parts;
    this.fontsReady = true;
  }
  initHeroWhenReady() {
    const go = () => {
      if (this._stop) return;
      this.sampleHeroTargets();
      this.layoutHero();
      if (this.visible && !this.authOpen) this.setHeroPhase("forming");
      else this.heroPh = "shown";
    };
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => setTimeout(go, 40));
    else setTimeout(go, 80);
  }
  setHeroPhase(ph) {
    this.heroPh = ph;
    this.heroT0 = performance.now();
  }
  drawHero(t) {
    const ctx = this._ctx;
    const { heroTitle: el, heroBeneath: be } = this.els;
    const ph = this.heroPh;
    if (!ph || ph === "hidden" || !this.heroParts) {
      if (el) el.style.opacity = "0";
      if (be) {
        be.style.opacity = "0";
        be.style.pointerEvents = "none";
      }
      return;
    }
    if (ph === "shown") {
      if (el) {
        el.style.opacity = "1";
        el.style.filter = "none";
        el.style.transform = "translateY(0)";
      }
      if (be) {
        const on = !this.authOpen;
        be.style.opacity = on ? "1" : "0";
        be.style.transform = "translateY(0)";
        be.style.pointerEvents = on ? "auto" : "none";
      }
      return;
    }
    const forming = ph === "forming";
    const dur = forming ? 900 : 620;
    const p = clamp01((performance.now() - (this.heroT0 || 0)) / dur);
    ctx.fillStyle = TH.ink;
    for (const q of this.heroParts) {
      const lp = clamp01((p - q.d) / (1 - 0.26));
      const fromX = forming ? q.hx : q.tx,
        fromY = forming ? q.hy : q.ty;
      const toX = forming ? q.tx : q.hx,
        toY = forming ? q.ty : q.hy;
      const e = forming ? 1 - Math.pow(1 - lp, 3) : lp * lp;
      let x = fromX + (toX - fromX) * e,
        y = fromY + (toY - fromY) * e;
      const swirl = (1 - e) * q.cur;
      x += Math.cos(q.ca + t * 0.6) * swirl * 0.4;
      y += Math.sin(q.ca + t * 0.7) * swirl * 0.4;
      let a;
      if (forming) a = lp < 0.68 ? lp / 0.68 : Math.max(0, 1 - (lp - 0.68) / 0.32);
      else a = 1 - lp;
      ctx.globalAlpha = Math.max(0, a) * 0.9 * q.al;
      ctx.fillRect(x, y, q.s, q.s);
    }
    ctx.globalAlpha = 1;
    const tv = forming ? smooth(0.5, 1, p) : 1 - smooth(0, 0.5, p);
    if (el) {
      el.style.opacity = String(tv);
      el.style.filter = "blur(" + ((1 - tv) * 7).toFixed(2) + "px)";
      el.style.transform = "translateY(" + ((1 - tv) * (forming ? 9 : -9)).toFixed(2) + "px)";
    }
    const bv = forming ? smooth(0.66, 1, p) : 1 - smooth(0, 0.38, p);
    if (be) {
      be.style.opacity = String(bv);
      be.style.transform = "translateY(" + ((1 - bv) * 10).toFixed(2) + "px)";
      be.style.pointerEvents = bv > 0.92 && !this.authOpen ? "auto" : "none";
    }
    if (p >= 1) this.heroPh = forming ? "shown" : "hidden";
  }
}
