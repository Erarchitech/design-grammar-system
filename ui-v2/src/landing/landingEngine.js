// Landing particle-ring engine. Owns the landing canvas: the particle ring with
// gaussian peaks toward the region anchors, the leader-line callouts, and the
// opening sequence. DOM elements it animates every frame (hero lines, hero-
// beneath, region labels, hint) are styled ONLY here — their React JSX carries
// classes, not style props, so re-renders never clobber engine-owned values.
//
// Opening sequence (owner-tuned 2026-10-08 in the landing motion tuner): a
// bright current runs once round the ring clockwise from the top, the ring
// lights up behind it, and each region's node pops in — with the Graph
// Viewer's arrival impulse — as the current passes it; its leader line draws
// out and its label fades in. The hero words then fade in by opacity alone.

const ANCH = [
  { key: "graph", ang: Math.PI * 1.06, amp: 0.95, sig: 0.3, out: 62 },
  { key: "model", ang: -0.2, amp: 1.0, sig: 0.26, out: 62 },
  { key: "projects", ang: Math.PI * 0.62, amp: 0.72, sig: 0.22, out: 54 },
  // v8.1 setup regions — secondary peaks (amp/sig below the three primaries),
  // distributed in the free arcs so all 7 callouts + hero + hint stay clear.
  { key: "aiengine", ang: -Math.PI * 0.45, amp: 0.68, sig: 0.24, out: 54 }, // top, slightly right
  { key: "connectors", ang: Math.PI * 0.3, amp: 0.66, sig: 0.22, out: 54 }, // lower-right
  { key: "reasoner", ang: -Math.PI * 0.78, amp: 0.64, sig: 0.22, out: 54 }, // top-left
  { key: "apidocs", ang: Math.PI * 0.86, amp: 0.6, sig: 0.2, out: 54 } // left, below center
];

// Owner-tuned ring and sequence values (landing motion tuner, 2026-10-08).
const RING = {
  count: 26000, // dots
  peakDensity: 0.9, // 0 = even round the ring, 1 = packed into the peaks
  peakHeight: 0.59, // outward reach of a peak, × ring radius
  peakGain: 0.75,
  peakWidth: 0.4, // × each anchor's sigma
  floor: 0.015, // ring level between peaks
  brightContrast: 0.46, // dims the gaps, brightens the peaks
  thickness: 0.3, // × radial jitter
  dotSize: 1.7,
  dotAlpha: 0.35,
  speed: 1.4, // shimmer time scale
  drift: 0.2, // dot oscillation about its home angle
  breathing: 0.35, // each peak rises and falls on its own beat
  leaderLen: 1.15
};
const SEQ = {
  start: -Math.PI / 2, // the current enters at the top
  flow0: 0.25, // s before the current starts
  loop: 1.0, // s for one turn of the ring
  reveal: 0.7, // rad of ring fading in behind the head
  labelFade: 1.0,
  textDelay: -0.1, // hero start relative to the current's end
  textFade: 1.0
};

const ENV_BINS = 2048; // per-frame peak-envelope lookup table resolution
const TAU = 6.283185307;

const TH = {
  ink: "#0a0a0a",
  rgb: "10,10,10",
  leader: "rgba(10,10,10,0.38)"
};

// Theme-aware canvas palette (dark values mirror colors.css dark tokens)
function refreshLandingTheme() {
  const dark = document.documentElement.dataset.theme === "dark";
  TH.ink = dark ? "#f0f0f0" : "#0a0a0a";
  TH.rgb = dark ? "240,240,240" : "10,10,10";
  TH.leader = dark ? "rgba(240,240,240,0.38)" : "rgba(10,10,10,0.38)";
}
refreshLandingTheme();
if (typeof window !== "undefined") window.addEventListener("dg-theme", refreshLandingTheme);

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
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(TAU * v);
}
function angDiff(a, b) {
  let d = (a - b) % TAU;
  if (d > Math.PI) d -= TAU;
  if (d < -Math.PI) d += TAU;
  return d;
}
const clamp01 = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);
const easeSine = (v) => 0.5 - 0.5 * Math.cos(Math.PI * clamp01(v));
const easeOut = (v) => 1 - Math.pow(1 - clamp01(v), 3);
const wrap = (a) => ((a % TAU) + TAU) % TAU;

// Peak envelope at angle a; tt drives the per-peak breathing.
function envAt(a, tt, anchors = ANCH) {
  let e = RING.floor;
  for (let k = 0; k < anchors.length; k++) {
    const an = anchors[k];
    const d = angDiff(a, an.ang);
    const sg = an.sig * RING.peakWidth;
    const amp = an.amp * RING.peakGain * (1 + RING.breathing * Math.sin(tt * 0.5 + k * 1.9));
    e += amp * Math.exp(-(d * d) / (2 * sg * sg));
  }
  return e;
}

export default class LandingEngine {
  /**
   * @param els {{canvas, heroTitle, heroL1, heroL2, heroBeneath, labels: Record<'graph'|'model'|'projects'|'aiengine'|'connectors'|'reasoner'|'apidocs', HTMLElement>, hint, heroForm}}
   */
  constructor(els, regions = ANCH) {
    this.els = els;
    this.anchors = regions;
    this.authOpen = false;
    this.visible = true;
    this.heroPh = "hidden";
    this.heroT0 = 0;
    this.fontsReady = false;
    this.pk = {}; // ring points per region key (used as fly() transform origins)
    this._lls = [];
    this._stop = false;
    this._intro = null; // { t0, fired: number[] } while the opening sequence runs
    this._nav = 1; // label/leader visibility, eased toward 0 while the auth card is open
    this._env = new Float32Array(ENV_BINS);
  }

  start() {
    this._stop = false;
    this.resize();
    this.initParticles();
    this.playIntro(); // the ring needs no fonts; the hero waits for them (see drawLanding)
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
    this.layoutLanding();
  }

  tick(ts) {
    if (this._stop) return;
    this._raf = requestAnimationFrame(this.tick.bind(this));
    // Self-heal: some embed contexts report 0×0 at mount and never fire a
    // resize event — re-measure every frame and rebuild layout on change.
    if (window.innerWidth !== this._vw || window.innerHeight !== this._vh) this.resize();
    const dt = Math.min(0.05, (ts - (this._lts || ts)) / 1000);
    this._lts = ts;
    if (!this.visible || !this._vw) return;
    this.drawLanding(ts / 1000, dt);
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
  }

  /* ---------------- particle ring ---------------- */
  initParticles() {
    let envMax = 0;
    for (let i = 0; i < 720; i++) envMax = Math.max(envMax, envAt((i / 720) * TAU, 0, this.anchors));
    this._envMax = envMax;
    const R = rng(7);
    this._parts = new Array(RING.count);
    for (let i = 0; i < RING.count; i++) {
      // rejection-sample the home angle so dots gather in the peaks
      let a = 0;
      for (let tries = 0; tries < 60; tries++) {
        a = R() * TAU;
        const w = 1 - RING.peakDensity + RING.peakDensity * (envAt(a, 0, this.anchors) / envMax);
        if (R() < w) break;
      }
      const wide = R() < 0.18;
      this._parts[i] = {
        a,
        j: gauss(R) * (wide ? 13 : 4.5),
        u: Math.pow(R(), 1.6),
        s: 0.5 + R() * 0.95,
        al: 0.16 + R() * 0.44,
        w: R() * TAU,
        osc: (R() - 0.5) * 0.03,
        oph: R() * TAU
      };
    }
  }

  /* ---------------- region callout layout ---------------- */
  layoutLanding() {
    if (!this._vw) return;
    const cx = this._vw / 2,
      cy = this._vh / 2,
      R = Math.min(this._vw, this._vh) * 0.365;
    this._lls = [];
    this.pk = {};
    for (const an of this.anchors) {
      const el = this.els.labels[an.key];
      const out = an.out * RING.leaderLen;
      const dx = Math.cos(an.ang),
        dy = Math.sin(an.ang);
      const P = [cx + dx * R, cy + dy * R];
      const K = [cx + dx * (R + out), cy + dy * (R + out)];
      const right = dx >= 0;
      const tx = K[0] + (right ? 14 : -14);
      const hx = K[0] + (right ? 8 : -8);
      const base = "translate(" + tx + "px, " + K[1] + "px) translate(" + (right ? "0" : "-100%") + ", -50%)";
      this._lls.push({ key: an.key, rel: wrap(an.ang - SEQ.start), P, K, hx, ty: K[1], right, base, el });
      this.pk[an.key] = P;
      if (el) {
        el.style.left = "0px";
        el.style.top = "0px";
        el.style.textAlign = right ? "left" : "right";
      }
    }
  }

  /* ---------------- opening sequence ---------------- */
  playIntro() {
    this._intro = { t0: performance.now() / 1000, fired: this.anchors.map(() => null) };
    this.setHeroPhase("hidden");
  }
  introTimes() {
    const ring0 = SEQ.flow0;
    const end = ring0 + SEQ.loop;
    return { ring0, end, text0: Math.max(ring0 + 0.2, end + SEQ.textDelay) };
  }

  drawLanding(now, dt) {
    const ctx = this._ctx;
    if (!ctx) return;
    const vw = this._vw,
      vh = this._vh;
    ctx.setTransform(this._dpr, 0, 0, this._dpr, 0, 0);
    ctx.clearRect(0, 0, vw, vh);
    const cx = vw / 2,
      cy = vh / 2,
      R = Math.min(vw, vh) * 0.365;
    const tt = now * RING.speed;

    // opening-sequence clock
    const I = this._intro;
    const it = I ? now - I.t0 : Infinity;
    const TL = this.introTimes();
    const headTravel = it < TL.ring0 ? 0 : easeSine((it - TL.ring0) / SEQ.loop) * TAU;
    const revealing = it < TL.end + 0.8;
    if (it >= TL.text0 && this.fontsReady && this.heroPh === "hidden" && !this.authOpen && !this._heroDone) {
      this._heroDone = true; // the opening fades the hero in once; later fades follow the auth card
      this.setHeroPhase("forming");
    }
    if (I && it > TL.end + SEQ.labelFade + 1) this._intro = null;

    // envelope lookup for this frame (breathing makes it time-dependent)
    const env = this._env;
    for (let b = 0; b < ENV_BINS; b++) env[b] = envAt((b / ENV_BINS) * TAU, tt, this.anchors);
    const span = Math.max(1e-6, this._envMax - RING.floor);

    ctx.fillStyle = TH.ink;
    for (const p of this._parts) {
      const a = p.a + Math.sin(tt * 0.35 + p.oph) * p.osc * RING.drift;
      let vis = 1;
      if (revealing) {
        vis = clamp01((headTravel - wrap(a - SEQ.start)) / SEQ.reveal);
        if (vis <= 0) continue;
      }
      const e = env[Math.min(ENV_BINS - 1, ((wrap(a) / TAU) * ENV_BINS) | 0)];
      const sp =
        Math.pow(Math.abs(Math.sin(a * 41 + p.w + tt * 0.1)), 3) * 0.62 +
        Math.pow(Math.abs(Math.sin(a * 13 - tt * 0.05 + p.w * 2)), 2) * 0.38;
      const disp = e * (0.22 + 0.78 * sp);
      const rad = R + p.j * RING.thickness + disp * p.u * R * RING.peakHeight;
      const en = clamp01((e - RING.floor) / span);
      const bright =
        1 - RING.brightContrast + RING.brightContrast * (0.12 + 0.88 * Math.pow(en, 0.8)) * (1 + 0.5 * en);
      const al = p.al * (0.55 + 0.45 * sp) * RING.dotAlpha * bright * vis;
      if (al <= 0.003) continue;
      ctx.globalAlpha = al > 1 ? 1 : al;
      const sz = p.s * RING.dotSize;
      ctx.fillRect(cx + Math.cos(a) * rad, cy + Math.sin(a) * rad, sz, sz);
    }
    ctx.globalAlpha = 1;

    if (I && it >= TL.ring0 && it < TL.end + 0.8) this.drawCurrent(it, TL, cx, cy, R, headTravel);

    // nodes, leader lines and labels: fired as the current passes each anchor;
    // all hidden while the auth card is open
    this._nav += ((this.authOpen ? 0 : 1) - this._nav) * Math.min(1, dt * 10);
    for (let k = 0; k < this._lls.length; k++) {
      const L = this._lls[k];
      let age = Infinity;
      if (I) {
        if (I.fired[k] == null && it >= TL.ring0 && headTravel >= L.rel) I.fired[k] = it;
        age = I.fired[k] == null ? -1 : it - I.fired[k];
      }
      this.drawNode(L, age);
    }
    const hint = this.els.hint;
    if (hint) hint.style.opacity = String(this._nav * (I ? easeSine((it - TL.text0 - 1.1) / 0.8) : 1));

    this.drawHero();
  }

  // The current: a bright head with a shimmering wake, running clockwise round
  // the ring (the Graph Viewer's core→node stream, minus its strands).
  drawCurrent(it, TL, cx, cy, R, headTravel) {
    const ctx = this._ctx;
    const fade = it > TL.end ? 1 - clamp01((it - TL.end) / 0.8) : 1;
    const steps = Math.max(2, Math.ceil((R * headTravel) / 7));
    const wake = R * 0.32;
    const headD = R * headTravel;
    ctx.fillStyle = TH.ink;
    for (let i = steps; i >= 0; i--) {
      const a = SEQ.start + (headTravel * i) / steps;
      const d = (headD * i) / steps;
      const behind = headD - d;
      if (behind > wake) break;
      ctx.globalAlpha = (1 - behind / wake) * 0.6 * fade * (0.5 + 0.5 * Math.sin(d * 0.9 + it * 5));
      ctx.fillRect(cx + Math.cos(a) * R - 0.9, cy + Math.sin(a) * R - 0.9, 1.8, 1.8);
    }
    if (it < TL.end) {
      const ha = SEQ.start + headTravel;
      const hx = cx + Math.cos(ha) * R,
        hy = cy + Math.sin(ha) * R;
      const glow = ctx.createRadialGradient(hx, hy, 0, hx, hy, 16);
      glow.addColorStop(0, "rgba(" + TH.rgb + ",0.35)");
      glow.addColorStop(1, "rgba(" + TH.rgb + ",0)");
      ctx.globalAlpha = fade;
      ctx.fillStyle = glow;
      ctx.fillRect(hx - 16, hy - 16, 32, 32);
      ctx.fillStyle = TH.ink;
      ctx.globalAlpha = 0.95 * fade;
      ctx.fillRect(hx - 1.7, hy - 1.7, 3.4, 3.4);
    }
    ctx.globalAlpha = 1;
  }

  // age: seconds since the current reached this node; -1 = not yet; Infinity = settled.
  drawNode(L, age) {
    const ctx = this._ctx;
    const el = L.el;
    const nav = this._nav;
    if (age < 0) {
      if (el) {
        el.style.opacity = "0";
        el.style.transform = L.base;
        el.style.pointerEvents = "none";
      }
      return;
    }
    // arrival impulse, as the Graph Viewer marks a node the current reaches
    if (age < 0.6) {
      const q = age / 0.6;
      ctx.strokeStyle = TH.ink;
      ctx.lineWidth = 1.2;
      ctx.globalAlpha = 0.55 * (1 - q) * nav;
      ctx.beginPath();
      ctx.arc(L.P[0], L.P[1], 2.5 + q * 24, 0, TAU);
      ctx.stroke();
    }
    if (nav > 0.01) {
      // leader line draws outward
      const lp = easeOut(age / 0.4);
      const seg1 = Math.hypot(L.K[0] - L.P[0], L.K[1] - L.P[1]);
      const seg2 = Math.abs(L.hx - L.K[0]);
      const want = (seg1 + seg2) * lp;
      ctx.globalAlpha = nav;
      ctx.strokeStyle = TH.leader;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(L.P[0], L.P[1]);
      if (want <= seg1) {
        const f = want / seg1;
        ctx.lineTo(L.P[0] + (L.K[0] - L.P[0]) * f, L.P[1] + (L.K[1] - L.P[1]) * f);
      } else {
        ctx.lineTo(L.K[0], L.K[1]);
        ctx.lineTo(L.K[0] + (L.hx - L.K[0]) * ((want - seg1) / seg2), L.ty);
      }
      ctx.stroke();
      ctx.fillStyle = TH.ink;
      const pop = easeOut(age / 0.25);
      ctx.beginPath();
      ctx.arc(L.P[0], L.P[1], 2.4 * pop, 0, TAU);
      ctx.fill();
      if (lp >= 1) {
        ctx.beginPath();
        ctx.arc(L.hx, L.ty, 2.4, 0, TAU);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    }
    if (el) {
      // label fades in with a short slide away from the ring
      const lo = age === Infinity ? 1 : easeSine((age - 0.15) / SEQ.labelFade);
      const o = lo * nav;
      el.style.opacity = String(o);
      el.style.transform = L.base + " translateX(" + ((1 - lo) * (L.right ? -8 : 8)).toFixed(2) + "px)";
      el.style.pointerEvents = o > 0.5 ? "auto" : "none";
    }
  }

  /* ---------------- hero: words fade in, opacity only ---------------- */
  layoutHero() {
    const vh = this._vh || window.innerHeight;
    const { heroTitle, heroL1, heroBeneath, heroForm } = this.els;
    const cy = vh * 0.44;
    const H = heroTitle ? heroTitle.offsetHeight : 0;
    const top = cy - H / 2;
    if (heroTitle) heroTitle.style.top = top + "px";
    if (heroBeneath) {
      const s1 = heroL1 ? parseFloat(getComputedStyle(heroL1).fontSize) : 40;
      heroBeneath.style.top = top + H + Math.max(30, s1 * 0.62) + "px";
    }
    if (heroForm) heroForm.style.top = cy + "px";
  }
  initHeroWhenReady() {
    const go = () => {
      if (this._stop) return;
      this.fontsReady = true;
      this.layoutHero();
    };
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => setTimeout(go, 40));
    else setTimeout(go, 80);
  }
  setHeroPhase(ph) {
    this.heroPh = ph;
    this.heroT0 = performance.now();
  }
  drawHero() {
    const { heroL1: l1, heroL2: l2, heroTitle: el, heroBeneath: be } = this.els;
    const ph = this.heroPh;
    let o1 = 0,
      o2 = 0,
      o3 = 0;
    if (ph === "shown") {
      o1 = o2 = o3 = 1;
    } else if (ph === "forming") {
      const s = (performance.now() - this.heroT0) / 1000;
      o1 = easeSine(s / SEQ.textFade);
      o2 = easeSine((s - 0.25) / SEQ.textFade);
      o3 = easeSine((s - 0.6) / SEQ.textFade);
      if (o3 >= 1) this.heroPh = "shown";
    } else if (ph === "dissolving") {
      const s = (performance.now() - this.heroT0) / 1000;
      o1 = o2 = o3 = 1 - easeSine(s / 0.4);
      if (s >= 0.4) this.heroPh = "hidden";
    }
    if (el) el.style.opacity = "1";
    if (l1) l1.style.opacity = String(o1);
    if (l2) l2.style.opacity = String(o2);
    if (be) {
      const on = !this.authOpen;
      be.style.opacity = String(on ? o3 : 0);
      be.style.pointerEvents = on && o3 > 0.92 ? "auto" : "none";
    }
  }
}
