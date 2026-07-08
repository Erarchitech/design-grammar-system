// Graph datascape engine — ported from the V2 design mockup's canvas logic
// and generalised from 5 hard-coded layers to N data-driven ring layers.
// Renders orbit guides, ink-arc edges, achromatic dot nodes with idle drift,
// the divergence field, the red selection halo + inclined divergence callout,
// and the minimap. Input: drag rotates the grabbed orbit (with inertia),
// click selects, double-click opens the detail panel, wheel zooms about the
// cursor, right-click opens the search popover (via callback).

const TAU = 6.283185307;

const TH = {
  ink: "#0a0a0a",
  dim: "#d4d4d4",
  guide: "rgba(10,10,10,0.06)",
  guideOn: "rgba(10,10,10,0.16)",
  edge: "rgba(10,10,10,0.20)",
  signal: "#e7000b",
  signalDim: "rgba(231,0,11,0.5)",
  leader: "rgba(10,10,10,0.38)",
  paper: "#f5f5f5"
};

// Theme-aware canvas palette: light values above stay pixel-identical;
// dark values mirror the [data-theme="dark"] tokens in colors.css.
function refreshEngineTheme() {
  const dark = document.documentElement.dataset.theme === "dark";
  const a = dark ? (x) => `rgba(240,240,240,${x})` : (x) => `rgba(10,10,10,${x})`;
  TH.ink = dark ? "#f0f0f0" : "#0a0a0a";
  TH.dim = dark ? "#3d3d3d" : "#d4d4d4";
  TH.guide = a(0.06);
  TH.guideOn = a(0.16);
  TH.edge = a(0.2);
  TH.signal = dark ? "#ff3b44" : "#e7000b";
  TH.signalDim = dark ? "rgba(255,59,68,0.5)" : "rgba(231,0,11,0.5)";
  TH.leader = a(0.38);
  TH.paper = dark ? "#111111" : "#f5f5f5";
}
refreshEngineTheme();
if (typeof window !== "undefined") window.addEventListener("dg-theme", refreshEngineTheme);

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

export default class GraphEngine {
  /**
   * @param els {{canvas, map, zoomLabel, hoverPanel, selPanel}}
   * @param cb  {{onHover, onSelect, onClearSel, onContextSearch, onSearchEnter, onPromptEnter}}
   */
  constructor(els, cb = {}) {
    this.els = els;
    this.cb = cb;
    this.rings = [];
    this.cross = [];
    this.xmap = {};
    this.xPerRing = [];
    this.type = 0;
    this.sel = null;
    this.selBig = false;
    this.hover = null;
    this.searchOpen = false;
    this.filterSet = null; // Set of active-ring indices to keep (others fade)
    this.liveSet = null; // Set of indices to halo (live search matches)
    this.visible = false;
    this.idleDrift = true;
    this.fieldOn = true;
    this.fieldAmplitude = 0.2;
    this._cam = { x: 0, y: 0, s: 1 };
    this._camT = { x: 0, y: 0, s: 1 };
    this._orbReach = [0.03, 0.052, 0.175];
    this._stop = false;
  }

  /* ---------------- data ---------------- */
  setData({ rings, cross, xmap, xPerRing }) {
    this.rings = rings;
    this.cross = cross;
    this.xmap = xmap;
    this.xPerRing = xPerRing;
    const N = rings.length || 1;
    // per-orbit world radii — tight intra-layer gaps, wide inter-layer gaps
    this._orbR = [];
    let acc = 0.16;
    for (let g = 0; g < N; g++) {
      const t = [];
      for (let o = 0; o < 3; o++) {
        t.push(acc);
        acc += 0.058;
      }
      acc += 0.12;
      this._orbR.push(t);
    }
    this._fit = 0.4 / this._orbR[N - 1][2];
    const seeds = [
      [0.3, 0.95, 1.6],
      [1.7, 2.35, 0.45],
      [0.9, 2.05, 3.05],
      [2.4, 1.15, 0.2],
      [1.2, 2.8, 1.95]
    ];
    this._rot = Array.from({ length: N }, (_, g) => (seeds[g % 5] || seeds[0]).slice());
    this._rotT = this._rot.map((a) => a.slice());
    this._spin = this._rot.map((a) => a.map(() => 0));
    if (this.type >= N) this.type = 0;
    this.initFieldParticles();
  }
  xOf(r, i) {
    return (this.xmap && this.xmap[r + ":" + i]) || [];
  }
  xCount(r) {
    return this.xPerRing[r] || 0;
  }

  /* ---------------- lifecycle ---------------- */
  start() {
    this._stop = false;
    this.resize();
    this._onResize = () => this.resize();
    window.addEventListener("resize", this._onResize);
    this.bind();
    this._raf = requestAnimationFrame(this.tick.bind(this));
  }
  stop() {
    this._stop = true;
    cancelAnimationFrame(this._raf);
    window.removeEventListener("resize", this._onResize);
    this.unbind();
  }
  setVisible(v) {
    this.visible = v;
  }
  getCamera() {
    return { x: this._cam.x, y: this._cam.y, s: this._cam.s };
  }
  setCamera(cam) {
    if (cam) {
      this._cam.x = cam.x || 0;
      this._cam.y = cam.y || 0;
      this._cam.s = cam.s || 1;
      this._camT.x = this._cam.x;
      this._camT.y = this._cam.y;
      this._camT.s = this._cam.s;
    }
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
    const mc = this.els.map;
    if (mc) {
      mc.width = 150 * this._dpr;
      mc.height = 150 * this._dpr;
      this._ctxM = mc.getContext("2d");
    }
  }

  tick(ts) {
    if (this._stop) return;
    this._raf = requestAnimationFrame(this.tick.bind(this));
    if (window.innerWidth !== this._vw || window.innerHeight !== this._vh) this.resize();
    const t = ts / 1000,
      dt = Math.min(0.05, t - (this._lt || t));
    this._lt = t;
    if (!this.visible || !this.rings.length || !this._vw) return;
    const act = this.type;
    for (let r = 0; r < this.rings.length; r++) {
      for (let o = 0; o < 3; o++) {
        const dr = this._rotT[r][o] - this._rot[r][o];
        if (Math.abs(dr) > 0.0004) this._rot[r][o] += dr * Math.min(1, dt * 5);
        else {
          this._rot[r][o] = this._rotT[r][o];
          if (this._spin[r][o]) {
            this._rot[r][o] += this._spin[r][o] * dt;
            this._rotT[r][o] = this._rot[r][o];
            this._spin[r][o] *= Math.exp(-dt * 2.0);
            if (Math.abs(this._spin[r][o]) < 0.02) this._spin[r][o] = 0;
          } else if (!this.sel && this.idleDrift) {
            const sp = (r === act ? 0.012 : 0.005) * (o % 2 ? -1 : 1) * (0.6 + o * 0.4);
            this._rot[r][o] += sp * dt;
            this._rotT[r][o] = this._rot[r][o];
          }
        }
      }
    }
    const cs = this._cam,
      ct = this._camT,
      k = Math.min(1, dt * 6);
    cs.x += (ct.x - cs.x) * k;
    cs.y += (ct.y - cs.y) * k;
    cs.s += (ct.s - cs.s) * k;
    this.drawGraph();
    this.placeGraphDOM();
    this.drawMinimap();
  }

  /* ---------------- camera ---------------- */
  camScreen() {
    const s = this._cam.s,
      m = Math.min(this._vw, this._vh);
    return { gcx: this._vw / 2 - this._cam.x * s, gcy: this._vh / 2 - this._cam.y * s, base: m * this._fit * s, s };
  }
  worldOf(g, i, rot) {
    const m = Math.min(this._vw, this._vh),
      nd = this.rings[g].nodes[i];
    const a = nd.ang + (rot || this._rot)[g][nd.orbit],
      Rw = this._orbR[g][nd.orbit] * m * this._fit;
    return [Math.cos(a) * Rw, Math.sin(a) * Rw];
  }
  fitToSelection(r, i, big) {
    const rot = this._rotT,
      rg = this.rings[r],
      pts = [this.worldOf(r, i, rot)];
    for (const e of rg.edges) {
      if (e[0] === i) pts.push(this.worldOf(r, e[1], rot));
      else if (e[1] === i) pts.push(this.worldOf(r, e[0], rot));
    }
    if (big) for (const p of this.xOf(r, i)) pts.push(this.worldOf(p.r, p.i, rot));
    let minx = 1e9,
      miny = 1e9,
      maxx = -1e9,
      maxy = -1e9;
    for (const [x, y] of pts) {
      if (x < minx) minx = x;
      if (x > maxx) maxx = x;
      if (y < miny) miny = y;
      if (y > maxy) maxy = y;
    }
    const cxw = (minx + maxx) / 2,
      cyw = (miny + maxy) / 2;
    const w = Math.max(maxx - minx, 60),
      h = Math.max(maxy - miny, 60);
    const fill = big ? 0.62 : 0.78;
    let s = Math.min((this._vw * fill) / w, (this._vh * fill) / h);
    s = Math.max(big ? 1.15 : 0.95, Math.min(2.6, s));
    const offX = big ? (this._vw * 0.14) / s : 0;
    this._camT = { x: cxw - offX, y: cyw, s };
  }
  resetCam() {
    this._camT = { x: 0, y: 0, s: 1 };
  }
  nodePos(g, i) {
    const { gcx, gcy, base } = this.camScreen();
    const nd = this.rings[g].nodes[i],
      a = nd.ang + this._rot[g][nd.orbit],
      R = this._orbR[g][nd.orbit] * base;
    return [gcx + Math.cos(a) * R, gcy + Math.sin(a) * R];
  }
  hitNode(x, y) {
    if (!this.rings.length) return null;
    const { gcx, gcy, base } = this.camScreen();
    const act = this.type;
    let best = null,
      bestRaw = 1e9,
      bestScore = 1e9;
    for (let g = 0; g < this.rings.length; g++) {
      const rg = this.rings[g];
      for (let i = 0; i < rg.nodes.length; i++) {
        const nd = rg.nodes[i];
        const a = nd.ang + this._rot[g][nd.orbit],
          R = this._orbR[g][nd.orbit] * base;
        const dx = x - (gcx + Math.cos(a) * R),
          dy = y - (gcy + Math.sin(a) * R);
        const raw = dx * dx + dy * dy,
          score = g === act ? raw * 0.45 : raw;
        if (score < bestScore) {
          bestScore = score;
          bestRaw = raw;
          best = { r: g, i };
        }
      }
    }
    return best && bestRaw < 220 ? best : null;
  }

  /* ---------------- search ---------------- */
  computeMatches(q, ring, prop = "*") {
    const s = new Set();
    if (!q || !this.rings[ring]) return s;
    const lq = q.toLowerCase();
    this.rings[ring].nodes.forEach((n, i) => {
      let hay;
      if (prop === "*") hay = n.label + " " + n.props.map((p) => p[1]).join(" ");
      else if (prop === "__label") hay = n.label;
      else {
        const kv = n.props.find((p) => p[0] === prop);
        hay = kv ? String(kv[1]) : "";
      }
      if (hay.toLowerCase().indexOf(lq) >= 0) s.add(i);
    });
    return s;
  }

  /* ---------------- selection ---------------- */
  align(r0, i0) {
    const done = new Set();
    const setO = (r, o, ang, tgt) => {
      const key = r + ":" + o;
      if (done.has(key)) return true;
      done.add(key);
      const cur = this._rot[r][o];
      this._rotT[r][o] = cur + angDiff(tgt - ang, cur);
      return false;
    };
    const rg0 = this.rings[r0],
      nd0 = rg0.nodes[i0];
    setO(r0, nd0.orbit, nd0.ang, 0);
    const fan = [];
    const consider = (r, i) => {
      const n = this.rings[r].nodes[i];
      const key = r + ":" + n.orbit;
      if (done.has(key) || fan.some((f) => f.key === key)) return;
      fan.push({ key, r, o: n.orbit, ang: n.ang });
    };
    for (const e of rg0.edges) {
      const j = e[0] === i0 ? e[1] : e[1] === i0 ? e[0] : -1;
      if (j >= 0) consider(r0, j);
    }
    for (const p of this.xOf(r0, i0)) consider(p.r, p.i);
    const cnt = fan.length,
      spread = 0.62;
    fan.forEach((f, k) => {
      const slot = cnt > 1 ? (k / (cnt - 1) - 0.5) * 2 : 0;
      setO(f.r, f.o, f.ang, slot * spread);
    });
    this._spin = this._spin.map((a) => a.map(() => 0));
  }
  selectNode(r, i, big) {
    this._selT = this._lt || 0;
    this.sel = { r, i };
    this.selBig = !!big;
    this.hover = null;
    if (r !== this.type) this.type = r;
    this.align(r, i);
    this.fitToSelection(r, i, !!big);
    if (this.cb.onSelect) this.cb.onSelect({ r, i }, !!big);
  }
  clearSel() {
    this.resetCam();
    this.sel = null;
    this.selBig = false;
    if (this.cb.onClearSel) this.cb.onClearSel();
  }
  setType(i) {
    if (i === this.type) return;
    this.type = i;
    this.sel = null;
    this.selBig = false;
    this.filterSet = null;
    this.liveSet = null;
    this.resetCam();
    if (this.cb.onTypeChange) this.cb.onTypeChange(i);
  }

  /* ---------------- input ---------------- */
  bind() {
    const g = this.els.canvas;
    this._gEl = g;
    const L = (this._L = {});
    L.down = (e) => {
      if (e.button !== 0) return;
      const cx = this._vw / 2,
        cy = this._vh / 2;
      const act = this.type,
        base = this.camScreen().base;
      const dist = Math.hypot(e.clientX - cx, e.clientY - cy);
      let orbit = 0,
        bd = 1e9;
      if (!this._orbR) return;
      for (let o = 0; o < 3; o++) {
        const dd = Math.abs(dist - this._orbR[act][o] * base);
        if (dd < bd) {
          bd = dd;
          orbit = o;
        }
      }
      this._pd = {
        x: e.clientX,
        y: e.clientY,
        t: performance.now(),
        moved: 0,
        orbit,
        a: Math.atan2(e.clientY - cy, e.clientX - cx),
        la: 0,
        lt: performance.now()
      };
    };
    L.move = (e) => {
      if (!this.rings.length) return;
      if (this._pd && e.buttons & 1) {
        this._pd.moved += Math.abs(e.movementX || 0) + Math.abs(e.movementY || 0);
        if (this._pd.moved > 4) {
          const cx = this._vw / 2,
            cy = this._vh / 2;
          const a = Math.atan2(e.clientY - cy, e.clientX - cx);
          const d = angDiff(a, this._pd.a);
          const act = this.type,
            o = this._pd.orbit;
          this._rot[act][o] += d;
          this._rotT[act][o] = this._rot[act][o];
          const now = performance.now();
          this._pd.la = d / Math.max(0.008, (now - this._pd.lt) / 1000);
          this._pd.lt = now;
          this._pd.a = a;
          if (this.sel) this.clearSel();
          g.style.cursor = "grabbing";
        }
      } else {
        const hit = this.hitNode(e.clientX, e.clientY);
        const cur = this.hover;
        if ((hit && (!cur || cur.r !== hit.r || cur.i !== hit.i)) || (!hit && cur)) {
          this.hover = hit;
          if (this.cb.onHover) this.cb.onHover(hit);
        }
        g.style.cursor = hit ? "pointer" : "default";
      }
    };
    L.up = (e) => {
      g.style.cursor = "default";
      if (this._pd) {
        if (this._pd.moved < 5 && performance.now() - this._pd.t < 400) this.clickAt(e.clientX, e.clientY);
        else if (Math.abs(this._pd.la) > 0.4 && !this.sel)
          this._spin[this.type][this._pd.orbit] = Math.max(-3, Math.min(3, this._pd.la));
      }
      this._pd = null;
    };
    L.dbl = (e) => {
      const hit = this.hitNode(e.clientX, e.clientY);
      if (hit) this.selectNode(hit.r, hit.i, true);
    };
    L.ctx = (e) => {
      e.preventDefault();
      const hit = this.hitNode(e.clientX, e.clientY);
      if (hit) return;
      if (this.cb.onContextSearch) this.cb.onContextSearch(e.clientX, e.clientY);
    };
    L.wheel = (e) => {
      e.preventDefault();
      const rect = g.getBoundingClientRect();
      const mx = e.clientX - rect.left,
        my = e.clientY - rect.top;
      const s0 = this._camT.s;
      const ns = Math.max(0.55, Math.min(4.5, s0 * Math.exp(-e.deltaY * 0.0012)));
      const wx = this._camT.x + (mx - this._vw / 2) / s0;
      const wy = this._camT.y + (my - this._vh / 2) / s0;
      this._camT = { s: ns, x: wx - (mx - this._vw / 2) / ns, y: wy - (my - this._vh / 2) / ns };
    };
    g.addEventListener("pointerdown", L.down);
    g.addEventListener("pointermove", L.move);
    window.addEventListener("pointerup", L.up);
    g.addEventListener("dblclick", L.dbl);
    g.addEventListener("contextmenu", L.ctx);
    g.addEventListener("wheel", L.wheel, { passive: false });
    const mp = this.els.map;
    if (mp) {
      L.mapMove = (e) => {
        if (!this._mapDrag || !this._mapMM) return;
        const r = mp.getBoundingClientRect();
        this._camT = {
          x: (e.clientX - r.left - 75) / this._mapMM,
          y: (e.clientY - r.top - 75) / this._mapMM,
          s: this._camT.s
        };
      };
      L.mapDown = (e) => {
        e.stopPropagation();
        this._mapDrag = true;
        L.mapMove(e);
      };
      L.mapUp = () => {
        this._mapDrag = false;
      };
      mp.addEventListener("pointerdown", L.mapDown);
      window.addEventListener("pointermove", L.mapMove);
      window.addEventListener("pointerup", L.mapUp);
    }
  }
  unbind() {
    const g = this._gEl,
      L = this._L;
    if (g && L) {
      g.removeEventListener("pointerdown", L.down);
      g.removeEventListener("pointermove", L.move);
      g.removeEventListener("dblclick", L.dbl);
      g.removeEventListener("contextmenu", L.ctx);
      g.removeEventListener("wheel", L.wheel);
    }
    if (L) {
      window.removeEventListener("pointerup", L.up);
      if (L.mapMove) window.removeEventListener("pointermove", L.mapMove);
      if (L.mapUp) window.removeEventListener("pointerup", L.mapUp);
      if (this.els.map && L.mapDown) this.els.map.removeEventListener("pointerdown", L.mapDown);
    }
  }
  clickAt(x, y) {
    const hit = this.hitNode(x, y);
    if (!hit) {
      if (this.searchOpen && this.cb.onCloseSearch) this.cb.onCloseSearch();
      else if (this.sel) this.clearSel();
      return;
    }
    this.selectNode(hit.r, hit.i, false);
  }

  /* ---------------- divergence field ---------------- */
  initFieldParticles() {
    const R = rng(19);
    const N = Math.round(6000 * 1.8);
    const parts = [];
    for (let i = 0; i < N; i++) {
      const rr = R();
      const o = rr < 0.2 ? 0 : rr < 0.48 ? 1 : 2;
      parts.push({
        o,
        a: R() * TAU,
        j: gauss(R) * 2.6,
        u: Math.pow(R(), 1.4),
        s: 0.5 + R() * 1.0,
        al: 0.16 + R() * 0.5,
        w: R() * TAU,
        v: (R() - 0.5) * 0.016
      });
    }
    this._gparts = parts;
  }
  buildEnvLUT(g) {
    const BINS = 360,
      rg = this.rings[g];
    const luts = [new Float32Array(BINS), new Float32Array(BINS), new Float32Array(BINS)];
    for (let o = 0; o < 3; o++) luts[o].fill(0.07);
    const sig = 0.14,
      inv = 1 / (2 * sig * sig),
      span = Math.ceil(((sig * 4) / TAU) * BINS) + 2;
    for (let i = 0; i < rg.nodes.length; i++) {
      const nd = rg.nodes[i],
        o = nd.orbit || 0;
      const a = (((nd.ang + this._rot[g][o]) % TAU) + TAU) % TAU;
      const amp = 0.3 + 1.05 * (Math.min(nd.deg, 8) / 8);
      const cBin = (a / TAU) * BINS;
      for (let db = -span; db <= span; db++) {
        let b = Math.round(cBin) + db;
        b = ((b % BINS) + BINS) % BINS;
        const da = (db / BINS) * TAU;
        luts[o][b] += amp * Math.exp(-da * da * inv);
      }
    }
    this._envLUT = luts;
    this._envBins = BINS;
  }
  sampleEnv(o, a) {
    const BINS = this._envBins;
    const b = Math.round((((a % TAU) + TAU) % TAU) / TAU * BINS) % BINS;
    return this._envLUT[o][b];
  }
  drawField(g, base, cx, cy, t) {
    const ctx = this._ctx;
    if (!ctx || !this._gparts) return;
    this.buildEnvLUT(g);
    const amp = this.fieldAmplitude,
      reach = this._orbReach;
    ctx.fillStyle = TH.ink;
    for (const p of this._gparts) {
      const o = p.o,
        Ro = this._orbR[g][o] * base;
      p.a += p.v * 0.016;
      const env = this.sampleEnv(o, p.a);
      const shim =
        Math.pow(Math.abs(Math.sin(p.a * 37 + p.w + t * 0.1)), 3) * 0.6 +
        Math.pow(Math.abs(Math.sin(p.a * 11 - t * 0.05 + p.w * 2)), 2) * 0.4;
      const disp = env * reach[o] * base * p.u * amp * (0.35 + 0.65 * shim);
      const rad = Ro + p.j + disp;
      const x = cx + Math.cos(p.a) * rad,
        y = cy + Math.sin(p.a) * rad;
      ctx.globalAlpha = p.al * (0.4 + 0.6 * shim) * Math.min(1, env * 0.8);
      ctx.fillRect(x, y, p.s, p.s);
    }
    ctx.globalAlpha = 1;
  }

  /* ---------------- draw ---------------- */
  drawGraph() {
    const ctx = this._ctx;
    if (!ctx || !this.rings.length) return;
    const vw = this._vw,
      vh = this._vh;
    ctx.setTransform(this._dpr, 0, 0, this._dpr, 0, 0);
    ctx.clearRect(0, 0, vw, vh);
    const cam = this.camScreen(),
      cx = cam.gcx,
      cy = cam.gcy,
      base = cam.base,
      z = cam.s;
    const act = this.type,
      sel = this.sel;
    const RR = (g, nd) => this._orbR[g][nd.orbit] * base;
    const posOf = (g, nd) => {
      const a = nd.ang + this._rot[g][nd.orbit],
        R = RR(g, nd);
      return [cx + Math.cos(a) * R, cy + Math.sin(a) * R];
    };
    const live = this.liveSet;
    const filt = this.filterSet;

    // orbit guide circles
    for (let g = 0; g < this.rings.length; g++) {
      for (let o = 0; o < 3; o++) {
        ctx.beginPath();
        ctx.arc(cx, cy, this._orbR[g][o] * base, 0, 6.29);
        ctx.strokeStyle = g === act ? TH.guideOn : TH.guide;
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }

    // dimmed nodes on inactive layers
    for (let g = 0; g < this.rings.length; g++) {
      if (g === act) continue;
      const rg = this.rings[g];
      ctx.fillStyle = TH.dim;
      for (let i = 0; i < rg.nodes.length; i++) {
        const nd = rg.nodes[i],
          a = nd.ang + this._rot[g][nd.orbit],
          R = RR(g, nd);
        const rr = (1.5 + 0.3 * Math.min(nd.deg, 6)) * Math.sqrt(z);
        ctx.beginPath();
        ctx.arc(cx + Math.cos(a) * R, cy + Math.sin(a) * R, rr, 0, 6.29);
        ctx.fill();
      }
    }

    // divergence field on the active layer
    if (this.fieldOn) this.drawField(act, base, cx, cy, this._lt || 0);

    // active layer edges — translucent ink arcs bowed toward the centre
    const rg = this.rings[act];
    ctx.strokeStyle = TH.edge;
    ctx.lineWidth = 1;
    for (const e of rg.edges) {
      if (filt && !(filt.has(e[0]) && filt.has(e[1]))) continue;
      const n1 = rg.nodes[e[0]],
        n2 = rg.nodes[e[1]];
      const [x1, y1] = posOf(act, n1),
        [x2, y2] = posOf(act, n2);
      const mx = (x1 + x2) / 2,
        my = (y1 + y2) / 2;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.quadraticCurveTo(cx + (mx - cx) * 0.72, cy + (my - cy) * 0.72, x2, y2);
      ctx.stroke();
    }

    // selection edges (same-ring + cross-layer), highlighted and labelled
    if (sel) {
      const [sx, sy] = this.nodePos(sel.r, sel.i);
      const selNd = this.rings[sel.r].nodes[sel.i];
      const tags = [];
      ctx.lineWidth = 1.25;
      const srg = this.rings[sel.r];
      for (const e of srg.edges) {
        const j = e[0] === sel.i ? e[1] : e[1] === sel.i ? e[0] : -1;
        if (j < 0) continue;
        const [px, py] = this.nodePos(sel.r, j);
        ctx.strokeStyle = TH.signalDim;
        ctx.beginPath();
        ctx.moveTo(sx, sy);
        ctx.lineTo(px, py);
        ctx.stroke();
        ctx.strokeStyle = TH.signal;
        ctx.beginPath();
        ctx.arc(px, py, 5.5, 0, 6.29);
        ctx.stroke();
        tags.push({ x1: sx, y1: sy, x2: px, y2: py, label: e[2] || "relatedTo" });
      }
      for (const p of this.xOf(sel.r, sel.i)) {
        const [px, py] = this.nodePos(p.r, p.i);
        ctx.strokeStyle = TH.signalDim;
        ctx.beginPath();
        ctx.moveTo(sx, sy);
        ctx.lineTo(px, py);
        ctx.stroke();
        ctx.strokeStyle = TH.signal;
        ctx.beginPath();
        ctx.arc(px, py, 5.5, 0, 6.29);
        ctx.stroke();
        tags.push({ x1: sx, y1: sy, x2: px, y2: py, label: p.label || "relatedTo" });
      }
      this._selTags = tags;
      void selNd;
    } else this._selTags = null;

    // active layer nodes
    for (let i = 0; i < rg.nodes.length; i++) {
      const nd = rg.nodes[i],
        [x, y] = posOf(act, nd);
      const isSel = sel && sel.r === act && sel.i === i;
      let rr = (2.0 + 0.34 * Math.min(nd.deg, 6)) * Math.sqrt(z);
      if (isSel) rr *= this.selBig ? 2.1 : 1.8;
      const faded = filt && !filt.has(i);
      ctx.globalAlpha = faded ? 0.14 : 1;
      ctx.fillStyle = isSel ? TH.signal : TH.ink;
      ctx.beginPath();
      ctx.arc(x, y, rr, 0, 6.29);
      ctx.fill();
      if (!faded && live && live.has(i) && !isSel) {
        ctx.strokeStyle = TH.signal;
        ctx.lineWidth = 1.25;
        ctx.beginPath();
        ctx.arc(x, y, rr + 2.5, 0, 6.29);
        ctx.stroke();
      }
      if (isSel) {
        ctx.strokeStyle = TH.signal;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(x, y, rr + 4, 0, 6.29);
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;

    // hover ring
    const h = this.hover;
    if (h) {
      const [hx, hy] = this.nodePos(h.r, h.i);
      ctx.strokeStyle = TH.guideOn;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(hx, hy, 8, 0, 6.29);
      ctx.stroke();
    }

    // edge property-label tags above the nodes
    if (this._selTags) for (const t of this._selTags) this.edgeTag(t.x1, t.y1, t.x2, t.y2, t.label);

    // divergence spire callout on selection
    if (sel && sel.r === act) this.drawSpire(act, sel.i, base, cx, cy, this._lt || 0);
  }

  edgeTag(x1, y1, x2, y2, text) {
    if (!text) return;
    const ctx = this._ctx;
    const dx = x2 - x1,
      dy = y2 - y1,
      len = Math.hypot(dx, dy) || 1;
    if (len < 34) return;
    const mx = x1 + dx * 0.56,
      my = y1 + dy * 0.56;
    const ox = (-dy / len) * 9,
      oy = (dx / len) * 9;
    const tx = mx + ox,
      ty = my + oy;
    ctx.save();
    ctx.font = '500 9px "Oswald", "Geist", sans-serif';
    try {
      ctx.letterSpacing = "1px";
    } catch {
      /* older engines */
    }
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const w = ctx.measureText(text.toUpperCase()).width;
    ctx.globalAlpha = 1;
    ctx.fillStyle = TH.paper;
    ctx.fillRect(tx - w / 2 - 3, ty - 6.5, w + 6, 13);
    ctx.fillStyle = TH.signal;
    ctx.fillText(text.toUpperCase(), tx, ty + 0.5);
    ctx.restore();
    try {
      ctx.letterSpacing = "0px";
    } catch {
      /* older engines */
    }
  }

  drawSpire(g, i, base, cx, cy, t) {
    const ctx = this._ctx;
    const rg = this.rings[g],
      nd = rg.nodes[i];
    const a = nd.ang + this._rot[g][nd.orbit],
      R = this._orbR[g][nd.orbit] * base;
    const nx = cx + Math.cos(a) * R,
      ny = cy + Math.sin(a) * R;
    const gi = Math.min(1, (t - (this._selT || 0)) * 3.2);
    const ease = 1 - Math.pow(1 - Math.max(0, gi), 3);
    if (ease < 0.35) return;
    if (this.selBig) return;

    const vw = this._vw,
      vh = this._vh;
    const kind = (rg.orbits[nd.orbit] || "") + " · " + rg.name;
    const label = String(nd.label || "");
    try {
      ctx.letterSpacing = "0.5px";
    } catch {
      /* older engines */
    }
    ctx.font = '600 17px "Oswald", "Geist", sans-serif';
    const lw = ctx.measureText(label.toUpperCase()).width;
    try {
      ctx.letterSpacing = "1.4px";
    } catch {
      /* older engines */
    }
    ctx.font = '500 10px "Oswald", "Geist", sans-serif';
    const kw = ctx.measureText(kind.toUpperCase()).width;
    try {
      ctx.letterSpacing = "0px";
    } catch {
      /* older engines */
    }
    const capW = Math.max(lw, kw, 84) + 18;

    const horiz = base * 0.17,
      lift = base * 0.2;
    let dir = 1,
      vdir = -1;
    if (nx + horiz + capW + 28 > vw - 12) dir = -1;
    if (ny - lift < 64) vdir = 1;
    const ex = nx + dir * horiz;
    const ey = Math.max(64, Math.min(vh - 84, ny + vdir * lift));
    ctx.strokeStyle = TH.leader;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(nx, ny);
    ctx.lineTo(ex, ey);
    ctx.stroke();
    ctx.fillStyle = TH.signal;
    ctx.beginPath();
    ctx.arc(nx, ny, 2.2, 0, 6.29);
    ctx.fill();
    ctx.fillStyle = TH.paper;
    ctx.beginPath();
    ctx.arc(ex, ey, 2.4, 0, 6.29);
    ctx.fill();
    ctx.strokeStyle = TH.leader;
    ctx.stroke();

    const align = dir > 0 ? "left" : "right";
    const tX = ex + dir * 8;
    ctx.textAlign = align;
    ctx.textBaseline = "alphabetic";
    const bx = ex + dir * 3,
      bTop = ey - 15,
      bBot = ey + 9;
    ctx.strokeStyle = TH.leader;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(bx + dir * 4, bTop);
    ctx.lineTo(bx, bTop);
    ctx.lineTo(bx, bBot);
    ctx.lineTo(bx + dir * 4, bBot);
    ctx.stroke();
    try {
      ctx.letterSpacing = "0.5px";
    } catch {
      /* older engines */
    }
    ctx.font = '600 17px "Oswald", "Geist", sans-serif';
    ctx.fillStyle = TH.ink;
    ctx.fillText(label.toUpperCase(), tX, ey - 2);
    try {
      ctx.letterSpacing = "1.4px";
    } catch {
      /* older engines */
    }
    ctx.font = '500 10px "Oswald", "Geist", sans-serif';
    ctx.fillStyle = TH.signal;
    ctx.fillText(kind.toUpperCase(), tX, ey + 12);
    ctx.strokeStyle = TH.leader;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(tX, ey + 16);
    ctx.lineTo(tX + dir * (capW - 4), ey + 16);
    ctx.stroke();
    try {
      ctx.letterSpacing = "0px";
    } catch {
      /* older engines */
    }
    ctx.textAlign = "left";
  }

  drawMinimap() {
    const ctx = this._ctxM;
    if (!ctx || !this.rings.length) return;
    const S = 150,
      mc = S / 2,
      m = Math.min(this._vw, this._vh);
    ctx.setTransform(this._dpr, 0, 0, this._dpr, 0, 0);
    ctx.clearRect(0, 0, S, S);
    const N = this.rings.length;
    const worldR = this._orbR[N - 1][2] * m * this._fit;
    const mm = (S * 0.46) / worldR;
    this._mapMM = mm;
    const act = this.type;
    for (let g = 0; g < N; g++) {
      ctx.beginPath();
      ctx.arc(mc, mc, this._orbR[g][2] * m * this._fit * mm, 0, 6.29);
      ctx.strokeStyle = g === act ? TH.guideOn : TH.guide;
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    const rg = this.rings[act];
    ctx.fillStyle = TH.dim;
    for (const nd of rg.nodes) {
      const a = nd.ang + this._rot[act][nd.orbit],
        R = this._orbR[act][nd.orbit] * m * this._fit * mm;
      ctx.fillRect(mc + Math.cos(a) * R - 0.6, mc + Math.sin(a) * R - 0.6, 1.4, 1.4);
    }
    const sel = this.sel;
    if (sel && sel.r === act) {
      const nd = rg.nodes[sel.i],
        a = nd.ang + this._rot[act][nd.orbit],
        R = this._orbR[act][nd.orbit] * m * this._fit * mm;
      ctx.fillStyle = TH.signal;
      ctx.beginPath();
      ctx.arc(mc + Math.cos(a) * R, mc + Math.sin(a) * R, 2.4, 0, 6.29);
      ctx.fill();
    }
    const cam = this._cam,
      halfW = this._vw / 2 / cam.s,
      halfH = this._vh / 2 / cam.s;
    const rx = mc + (cam.x - halfW) * mm,
      ry = mc + (cam.y - halfH) * mm,
      rw = halfW * 2 * mm,
      rh = halfH * 2 * mm;
    const x0 = Math.max(1, rx),
      y0 = Math.max(1, ry),
      x1 = Math.min(S - 1, rx + rw),
      y1 = Math.min(S - 1, ry + rh);
    ctx.fillStyle = TH.signal;
    ctx.globalAlpha = 0.09;
    ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
    ctx.globalAlpha = 1;
    ctx.strokeStyle = TH.signal;
    ctx.lineWidth = 1;
    ctx.strokeRect(x0, y0, x1 - x0, y1 - y0);
    const zl = this.els.zoomLabel;
    if (zl) zl.textContent = cam.s.toFixed(1) + "×";
  }

  placeGraphDOM() {
    const vw = this._vw,
      vh = this._vh;
    const hp = this.els.hoverPanel;
    if (hp) {
      const h = this.hover;
      if (h && !this.searchOpen) {
        const [x, y] = this.nodePos(h.r, h.i);
        const px = x + 18 > vw - 300 ? x - 300 : x + 18;
        const py = Math.max(12, Math.min(vh - 260, y + 12));
        hp.style.transform = "translate(" + px + "px, " + py + "px)";
        hp.style.opacity = "1";
      } else hp.style.opacity = "0";
    }
    const sp = this.els.selPanel;
    if (sp) {
      const s = this.sel;
      if (s && this.selBig) {
        const [x, y] = this.nodePos(s.r, s.i);
        const w = 360,
          hh = vh * 0.7;
        let px = x - w - 30;
        if (px < 12) px = Math.min(vw - w - 12, x + 26);
        const py = Math.max(12, Math.min(vh - hh - 12, y - hh / 2));
        sp.style.transform = "translate(" + px + "px, " + py + "px)";
        sp.style.opacity = "1";
        sp.style.pointerEvents = "auto";
      } else {
        sp.style.opacity = "0";
        sp.style.pointerEvents = "none";
      }
    }
  }
}
