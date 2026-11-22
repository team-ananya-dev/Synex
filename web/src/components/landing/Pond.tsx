"use client";

// A pixel-art koi pond drawn in code on one canvas (original art, inspired by top-down pixel koi ponds).
// The canvas runs at 1/SCALE of the screen and is scaled up with nearest-neighbour, so everything is pixels.
//   - water: a height-field wave simulation; the pointer leaves a wake, a click or pondDrop() drops a stone
//   - koi: chain bodies that wander, leave wakes, and flee the pointer and splashes
//   - lily pads and duckweed: pushed by the pointer and by the ripples, then spring back
//   - reeds: bend away from the pointer and sway; dragonflies dart away when it comes close
import { useEffect, useRef } from "react";

const SCALE = 4;

/** Drop a stone into the pond at a screen position (power 1 = a click). */
export function pondDrop(x: number, y: number, power = 1) {
  window.dispatchEvent(new CustomEvent("pond:drop", { detail: { x, y, power } }));
}

type RGB = [number, number, number];
const hex = (h: string): RGB => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];

const WATER: RGB[] = [hex("#060b14"), hex("#050910"), hex("#04070c")];
const RIM = hex("#0a1220");
const TROUGH = hex("#020306");
const CREST = hex("#3c5f8c");
const PAD = [hex("#144a29"), hex("#1a5a32"), hex("#103d22")];
const PAD_RIM = hex("#0a2817");
const PAD_LIGHT = hex("#2f7340");
const PAD_VEIN = hex("#114226");
const PETAL = hex("#e4f5ff");
const PETAL_CORE = hex("#8fd0f0");
const YELLOW = hex("#f2cf4a");
const STEM = hex("#4a1d22");
const WEED = [hex("#3c9a4a"), hex("#2b7a3a"), hex("#58b860")];
const REED_DARK = hex("#174f2b");
const REED_LIGHT = hex("#46a457");
const FLY_BODY = hex("#3fb6a8");
const FLY_WING = hex("#bfe6ff");
const KOI_COLORS: Record<string, RGB> = {
  c: hex("#f4e6cf"), r: hex("#dc4a2c"), o: hex("#f0a640"), y: hex("#ffd27a"), k: hex("#1b1b22"), d: hex("#b8361f"),
};
const PATTERNS = [
  "crrcrccrcc", // white with red patches
  "yooooooooo", // gold
  "rrcrrrcrrr", // red with cream
  "crrrrcckcc", // white, red, a black spot
];
const PROFILE = [1.5, 2.1, 2.4, 2.5, 2.3, 2.0, 1.6, 1.2, 0.9, 0.6];

function rng(seed: number) {
  return () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

type Pad = { x: number; y: number; r: number; dx: number; dy: number; vx: number; vy: number; notch: number; tone: number; flower: 0 | 1 | 2; stem: number };
type Koi = { x: number; y: number; a: number; base: number; boost: number; wander: number; phase: number; size: number; pattern: string; seg: { x: number; y: number }[] };
type Blade = { x: number; y: number; len: number; a: number; bend: number; vb: number; flower: boolean };
type Fly = { x: number; y: number; tx: number; ty: number; a: number; speed: number; wait: number };
type Speck = { x: number; y: number; dx: number; dy: number; tone: number };

/** quiet = the calmer version used behind the app pages: fewer fish and pads, no flowers or dragonflies,
 *  slower fish, a gentler pointer wake, no splash on click, and a much darker shade. The landing page uses the full pond. */
export function Pond({ quiet = false }: { quiet?: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current!;
    const ctx = canvas.getContext("2d", { alpha: false })!;
    const calm = quiet || window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let W = 0, H = 0;
    let cur = new Float32Array(0), prev = new Float32Array(0);
    let base = new Uint8Array(0);            // water level 0..2 per pixel, 3 = rim
    let img: ImageData, px: Uint32Array;
    let pads: Pad[] = [], koi: Koi[] = [], blades: Blade[] = [], flies: Fly[] = [], specks: Speck[] = [];
    const pointer = { x: -999, y: -999, px: -999, py: -999, active: false };
    const scares: { x: number; y: number; t: number }[] = [];
    let frame = 0, raf = 0;

    const put = (x: number, y: number, c: RGB) => {
      x |= 0; y |= 0;
      if (x < 0 || y < 0 || x >= W || y >= H) return;
      px[y * W + x] = 0xff000000 | (c[2] << 16) | (c[1] << 8) | c[0];
    };
    const shade = (x: number, y: number, f: number) => {
      x |= 0; y |= 0;
      if (x < 0 || y < 0 || x >= W || y >= H) return;
      const v = px[y * W + x];
      const r = (v & 255) * f, g = ((v >> 8) & 255) * f, b = ((v >> 16) & 255) * f;
      px[y * W + x] = 0xff000000 | (b << 16) | (g << 8) | r;
    };
    const disc = (cx: number, cy: number, r: number, c: RGB) => {
      const r2 = r * r;
      for (let y = Math.floor(cy - r); y <= cy + r; y++)
        for (let x = Math.floor(cx - r); x <= cx + r; x++)
          if ((x - cx) ** 2 + (y - cy) ** 2 <= r2) put(x, y, c);
    };
    const disturb = (cx: number, cy: number, r: number, v: number) => {
      for (let y = Math.max(1, Math.floor(cy - r)); y <= Math.min(H - 2, cy + r); y++)
        for (let x = Math.max(1, Math.floor(cx - r)); x <= Math.min(W - 2, cx + r); x++)
          if ((x - cx) ** 2 + (y - cy) ** 2 <= r * r) cur[y * W + x] += v;
    };
    const grad = (x: number, y: number): [number, number] => {
      x = Math.max(1, Math.min(W - 2, x | 0)); y = Math.max(1, Math.min(H - 2, y | 0));
      const i = y * W + x;
      return [cur[i + 1] - cur[i - 1], cur[i + W] - cur[i - W]];
    };

    function build() {
      W = Math.ceil(window.innerWidth / SCALE);
      H = Math.ceil(window.innerHeight / SCALE);
      canvas.width = W;
      canvas.height = H;
      cur = new Float32Array(W * H);
      prev = new Float32Array(W * H);
      img = ctx.createImageData(W, H);
      px = new Uint32Array(img.data.buffer);
      const rand = rng(7);

      // water: darker pools with a lighter rim, like shadows on a pond floor
      const depth = new Float32Array(W * H);
      for (let k = 0; k < Math.max(8, (W * H) / 6000); k++) {
        const cx = rand() * W, cy = rand() * H, rx = 14 + rand() * 40, ry = 8 + rand() * 24, lvl = rand() < 0.4 ? 2 : 1;
        for (let y = Math.max(0, Math.floor(cy - ry)); y < Math.min(H, cy + ry); y++)
          for (let x = Math.max(0, Math.floor(cx - rx)); x < Math.min(W, cx + rx); x++)
            if (((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1) depth[y * W + x] = Math.max(depth[y * W + x], lvl);
      }
      base = new Uint8Array(W * H);
      for (let y = 0; y < H; y++)
        for (let x = 0; x < W; x++) {
          const i = y * W + x, d = depth[i];
          const edge = d > 0 && ((x > 0 && depth[i - 1] < d) || (x < W - 1 && depth[i + 1] < d) || (y > 0 && depth[i - W] < d) || (y < H - 1 && depth[i + W] < d));
          base[i] = edge ? 3 : d;
        }

      // lily pads cluster at the sides and leave open water in the middle for the words
      pads = [];
      const n = Math.round((W * H) / (quiet ? 9000 : 3600));
      for (let k = 0; k < n; k++) {
        const side = rand();
        const x = side < 0.42 ? rand() * W * 0.26 : side < 0.84 ? W * 0.74 + rand() * W * 0.26 : W * (0.3 + rand() * 0.4);
        const y = side < 0.84 ? rand() * H : H * (0.78 + rand() * 0.22);
        const r = 4 + rand() * 7;
        if (pads.some((p) => Math.hypot(p.x - x, p.y - y) < (p.r + r) * 0.8)) continue;
        pads.push({ x, y, r, dx: 0, dy: 0, vx: 0, vy: 0, notch: rand() * Math.PI * 2, tone: (rand() * 3) | 0,
          flower: quiet ? 0 : rand() < 0.16 ? 1 : rand() < 0.05 ? 2 : 0, stem: rand() * Math.PI * 2 });
      }

      // koi: a few big ones and a little school of small red fish
      koi = [];
      const big = quiet ? 2 : Math.max(3, Math.round((W * H) / 36000));
      for (let k = 0; k < big + (quiet ? 1 : 4); k++) {
        const small = k >= big;
        const x = W * (0.2 + rand() * 0.6), y = H * (0.15 + rand() * 0.7), a = rand() * Math.PI * 2;
        const size = small ? 0.55 + rand() * 0.15 : 1 + rand() * 0.45;
        koi.push({ x, y, a, base: (small ? 0.16 + rand() * 0.06 : 0.1 + rand() * 0.05) * (quiet ? 0.6 : 1), boost: 0, wander: 0, phase: rand() * 10, size,
          pattern: small ? "rrrrrrcrrr" : PATTERNS[k % PATTERNS.length],
          seg: Array.from({ length: PROFILE.length }, (_, i) => ({ x: x - Math.cos(a) * i * 1.7 * size, y: y - Math.sin(a) * i * 1.7 * size })) });
      }

      // reeds in clumps at the corners and edges
      blades = [];
      const clumps: [number, number][] = [[0.05, 0.97], [0.95, 0.5], [0.9, 0.99]];
      for (const [cx, cy] of clumps)
        for (let k = 0; k < (quiet ? 3 : 6) + rand() * (quiet ? 2 : 4); k++)
          blades.push({ x: cx * W + (rand() - 0.5) * 16, y: cy * H + (rand() - 0.5) * 6, len: 12 + rand() * 22,
            a: -Math.PI / 2 + (rand() - 0.5) * 0.9, bend: 0, vb: 0, flower: rand() < 0.1 });

      flies = Array.from({ length: quiet ? 0 : 2 }, () => {
        const x = rand() * W, y = rand() * H;
        return { x, y, tx: x, ty: y, a: 0, speed: 0.4, wait: 0 };
      });
      specks = Array.from({ length: Math.round((W * H) / (quiet ? 8000 : 3000)) }, () => {
        const nearPad = pads[(rand() * pads.length) | 0];
        const x = nearPad && rand() < 0.7 ? nearPad.x + (rand() - 0.5) * 30 : rand() * W;
        const y = nearPad && rand() < 0.7 ? nearPad.y + (rand() - 0.5) * 30 : rand() * H;
        return { x, y, dx: 0, dy: 0, tone: (rand() * 3) | 0 };
      });
    }

    function step() {
      frame++;
      const t = frame;

      // ---- water waves (every third frame, so ripples spread slowly) ----
      if (t % 3 === 0) for (let y = 1; y < H - 1; y++)
        for (let x = 1, i = y * W + 1; x < W - 1; x++, i++)
          prev[i] = ((cur[i - 1] + cur[i + 1] + cur[i - W] + cur[i + W]) * 0.5 - prev[i]) * 0.962;
      if (t % 3 === 0) [cur, prev] = [prev, cur];

      // pointer wake
      if (pointer.active && pointer.px > -900) {
        const sp = Math.hypot(pointer.x - pointer.px, pointer.y - pointer.py);
        if (sp > 0.4 && t % 2 === 0) disturb(pointer.x, pointer.y, 1.2, Math.min(sp, 4) * (quiet ? 0.9 : 2.2));
      }
      pointer.px = pointer.x;
      pointer.py = pointer.y;
      if (!calm && t % 420 === 0) disturb(Math.random() * W, Math.random() * H, 1, 7); // a fish kissing the surface

      while (scares.length && t - scares[0].t > 90) scares.shift();

      // ---- koi ----
      for (const k of koi) {
        k.wander = k.wander * 0.985 + (Math.random() - 0.5) * 0.04;
        let turn = k.wander * 0.03;
        const flee = (fx: number, fy: number, radius: number, power: number) => {
          const dx = k.x - fx, dy = k.y - fy, d = Math.hypot(dx, dy);
          if (d < radius) {
            let diff = Math.atan2(dy, dx) - k.a;
            diff = Math.atan2(Math.sin(diff), Math.cos(diff));
            turn += diff * 0.06 * power;
            k.boost = Math.max(k.boost, (1 - d / radius) * 1.4 * power);
          }
        };
        if (pointer.active) flee(pointer.x, pointer.y, 22, 1);
        for (const s of scares) flee(s.x, s.y, 45, 1);
        const m = 18; // turn back from the edges
        if (k.x < m || k.x > W - m || k.y < m || k.y > H - m) {
          let diff = Math.atan2(H / 2 - k.y, W / 2 - k.x) - k.a;
          diff = Math.atan2(Math.sin(diff), Math.cos(diff));
          turn += diff * 0.03;
        }
        k.a += Math.max(-0.05, Math.min(0.05, turn));
        const speed = k.base * (1 + k.boost);
        k.boost *= 0.97;
        k.x += Math.cos(k.a) * speed;
        k.y += Math.sin(k.a) * speed;
        k.phase += 0.05 + speed * 0.3;
        k.seg[0].x = k.x;
        k.seg[0].y = k.y;
        const gap = 1.7 * k.size;
        for (let i = 1; i < k.seg.length; i++) {
          const a = k.seg[i - 1], b = k.seg[i];
          const dx = a.x - b.x, dy = a.y - b.y, d = Math.hypot(dx, dy) || 1;
          if (d > gap) { b.x += (dx * (d - gap)) / d; b.y += (dy * (d - gap)) / d; }
        }
        if (t % 12 === 0) { const tail = k.seg[k.seg.length - 1]; disturb(tail.x, tail.y, 0.8, -1.2 * speed * k.size); }
      }

      // ---- lily pads and duckweed: pointer push, ripple push, spring back ----
      for (const p of pads) {
        const cx = p.x + p.dx, cy = p.y + p.dy;
        const [gx, gy] = grad(cx, cy);
        p.vx += -gx * 0.03 - p.dx * 0.01;
        p.vy += -gy * 0.03 - p.dy * 0.01;
        if (pointer.active) {
          const dx = cx - pointer.x, dy = cy - pointer.y, d = Math.hypot(dx, dy), R = p.r + 8;
          if (d < R && d > 0.01) { p.vx += (dx / d) * (1 - d / R) * 0.12; p.vy += (dy / d) * (1 - d / R) * 0.12; }
        }
        p.vx *= 0.86; p.vy *= 0.86;
        p.dx += p.vx; p.dy += p.vy;
        p.notch += p.vx * 0.02;
      }
      for (const s of specks) {
        const [gx, gy] = grad(s.x + s.dx, s.y + s.dy);
        s.dx += -gx * 0.05 - s.dx * 0.01;
        s.dy += -gy * 0.05 - s.dy * 0.01;
        if (pointer.active) {
          const dx = s.x + s.dx - pointer.x, dy = s.y + s.dy - pointer.y, d = Math.hypot(dx, dy);
          if (d < 8 && d > 0.01) { s.dx += (dx / d) * 0.12; s.dy += (dy / d) * 0.12; }
        }
      }

      // ---- reeds ----
      for (const b of blades) {
        const tipX = b.x + Math.cos(b.a) * b.len, tipY = b.y + Math.sin(b.a) * b.len;
        if (pointer.active) {
          const dx = tipX - pointer.x, dy = tipY - pointer.y, d = Math.hypot(dx, dy);
          if (d < 26) {
            const side = Math.sign(Math.cos(b.a) * dy - Math.sin(b.a) * dx) || 1;
            b.vb -= side * (1 - d / 26) * 0.015;
          }
        }
        b.vb += -b.bend * 0.025;
        b.vb *= 0.9;
        b.bend = Math.max(-0.6, Math.min(0.6, b.bend + b.vb));
      }

      // ---- dragonflies ----
      for (const f of flies) {
        const near = pointer.active && Math.hypot(f.x - pointer.x, f.y - pointer.y) < 18;
        if (near) {
          const away = Math.atan2(f.y - pointer.y, f.x - pointer.x);
          f.tx = Math.max(5, Math.min(W - 5, f.x + Math.cos(away) * 80));
          f.ty = Math.max(5, Math.min(H - 5, f.y + Math.sin(away) * 80));
          f.speed = 1.2;
        } else if (Math.hypot(f.tx - f.x, f.ty - f.y) < 1) {
          if (--f.wait <= 0) { f.tx = Math.random() * W; f.ty = Math.random() * H; f.speed = 0.25 + Math.random() * 0.3; f.wait = 200 + Math.random() * 400; }
        }
        const dx = f.tx - f.x, dy = f.ty - f.y, d = Math.hypot(dx, dy);
        if (d > 0.5) { f.a = Math.atan2(dy, dx); const s = Math.min(f.speed, d * 0.08 + 0.2); f.x += (dx / d) * s; f.y += (dy / d) * s; }
        f.speed = Math.max(0.25, f.speed * 0.98);
      }
    }

    function draw() {
      // the 1-pixel border is outside the wave simulation: repaint it so sprites never leave trails there
      const edge = 0xff000000 | (WATER[0][2] << 16) | (WATER[0][1] << 8) | WATER[0][0];
      for (let x = 0; x < W; x++) { px[x] = edge; px[(H - 1) * W + x] = edge; }
      for (let y = 0; y < H; y++) { px[y * W] = edge; px[y * W + W - 1] = edge; }

      // water with ripple light
      for (let y = 1; y < H - 1; y++) {
        for (let x = 1, i = y * W + 1; x < W - 1; x++, i++) {
          const lvl = base[i];
          const c = lvl === 3 ? RIM : WATER[lvl];
          const s = (cur[i - 1] - cur[i + 1]) + (cur[i - W] - cur[i + W]);
          // three flat tones only, so ripples read as pixel rings rather than a smooth gradient
          const k = s > 1.9 ? CREST : s < -1.9 ? TROUGH : c;
          px[i] = 0xff000000 | (k[2] << 16) | (k[1] << 8) | k[0];
        }
      }

      // stems under the pads
      for (const p of pads) {
        const sx = p.x + p.dx * 0.5, sy = p.y + p.dy * 0.5;
        for (let s = 0; s < 18; s++) put(sx + Math.sin(p.stem + s * 0.35 + frame * 0.004) * 3 + s * 0.4, sy + s * 0.9, STEM);
      }

      // koi: shadow pass, then bodies
      for (const k of koi) {
        for (let i = 0; i < k.seg.length; i++) {
          const s = k.seg[i], r = PROFILE[i] * k.size;
          for (let y = -r; y <= r; y++) for (let x = -r; x <= r; x++) if (x * x + y * y <= r * r) shade(s.x + x + 2.5, s.y + y + 2.5, 0.62);
        }
      }
      for (const k of koi) {
        const n = k.seg.length;
        const perp = (i: number) => {
          const a = k.seg[Math.max(0, i - 1)], b = k.seg[Math.min(n - 1, i + 1)];
          const dx = a.x - b.x, dy = a.y - b.y, d = Math.hypot(dx, dy) || 1;
          return [-dy / d, dx / d, dx / d, dy / d];
        };
        const pts = k.seg.map((s, i) => {
          const [nx, ny] = perp(i);
          const w = Math.sin(k.phase - i * 0.55) * (i / n) * 1.4 * k.size;
          return { x: s.x + nx * w, y: s.y + ny * w };
        });
        // tail fin
        const [tnx, tny, tfx, tfy] = perp(n - 1);
        const tail = pts[n - 1], flap = Math.sin(k.phase) * 1.2;
        for (let s = 1; s <= 3 * k.size + 1; s++)
          for (const side of [-1, 1])
            put(tail.x - tfx * s + tnx * (side * s * 0.7 + flap), tail.y - tfy * s + tny * (side * s * 0.7 + flap), KOI_COLORS[k.pattern[n - 1]]);
        // pectoral fins
        const [fnx, fny] = perp(2), fin = 1 + Math.abs(Math.sin(k.phase * 0.5));
        for (const side of [-1, 1])
          disc(pts[2].x + fnx * side * (PROFILE[2] * k.size + fin), pts[2].y + fny * side * (PROFILE[2] * k.size + fin), 0.9 * k.size, KOI_COLORS.c);
        for (let i = n - 1; i >= 0; i--) disc(pts[i].x, pts[i].y, PROFILE[i] * k.size, KOI_COLORS[k.pattern[i]]);
        if (k.size >= 1) {
          const [hnx, hny, hfx, hfy] = perp(0);
          for (const side of [-1, 1]) put(pts[0].x + hnx * side * 1.2 + hfx * 0.8, pts[0].y + hny * side * 1.2 + hfy * 0.8, KOI_COLORS.k);
        }
      }

      // duckweed
      for (const s of specks) put(s.x + s.dx, s.y + s.dy, WEED[s.tone]);

      // lily pads with a notch, a light edge, veins and sometimes a flower
      for (const p of pads) {
        const cx = p.x + p.dx, cy = p.y + p.dy, r = p.r, r2 = r * r;
        for (let y = Math.floor(-r); y <= r; y++)
          for (let x = Math.floor(-r); x <= r; x++) {
            const d2 = x * x + y * y;
            if (d2 > r2) continue;
            let diff = Math.atan2(y, x) - p.notch;
            diff = Math.atan2(Math.sin(diff), Math.cos(diff));
            if (Math.abs(diff) < 0.32 && d2 > r2 * 0.04) continue;
            let c = PAD[p.tone];
            if (d2 > (r - 1.2) ** 2) c = PAD_RIM;
            else if (x + y < -r * 0.75) c = PAD_LIGHT;
            else if (Math.abs(diff - 1.6) < 0.06 || Math.abs(diff + 1.6) < 0.06 || Math.abs(Math.abs(diff) - Math.PI) < 0.07) c = PAD_VEIN;
            put(cx + x, cy + y, c);
          }
        if (p.flower === 1) {
          for (const [ox, oy] of [[0, -2], [-2, 0], [2, 0], [0, 2], [-1, -1], [1, -1], [-1, 1], [1, 1]]) put(cx + ox, cy + oy - 1, PETAL);
          put(cx, cy - 1, PETAL_CORE);
        } else if (p.flower === 2) {
          for (const [ox, oy] of [[0, -2], [-2, 0], [2, 0], [-1, 1], [1, 1], [0, 0]]) put(cx + ox, cy + oy, YELLOW);
        }
      }

      // reeds
      const wind = Math.sin(frame * 0.006);
      for (const b of blades) {
        const sway = b.bend + wind * 0.06 * (b.len / 30);
        let x = b.x, y = b.y;
        for (let s = 0; s < b.len; s++) {
          const a = b.a + sway * (s / b.len) ** 1.6;
          x += Math.cos(a);
          y += Math.sin(a);
          const f = s / b.len;
          put(x, y, [REED_DARK[0] + (REED_LIGHT[0] - REED_DARK[0]) * f | 0, REED_DARK[1] + (REED_LIGHT[1] - REED_DARK[1]) * f | 0, REED_DARK[2] + (REED_LIGHT[2] - REED_DARK[2]) * f | 0]);
        }
        if (b.flower) for (const [ox, oy] of [[0, -1], [-1, 0], [1, 0], [0, 1]]) put(x + ox, y + oy, YELLOW);
      }

      // dragonflies
      for (const f of flies) {
        const cx = Math.cos(f.a), sy = Math.sin(f.a);
        for (let s = -3; s <= 2; s++) put(f.x + cx * s, f.y + sy * s, s === 2 ? KOI_COLORS.k : FLY_BODY);
        if (frame % 4 < 3) for (const side of [-1, 1]) for (let w = 1; w <= 3; w++) {
          put(f.x - sy * side * w + cx * 0.5, f.y + cx * side * w + sy * 0.5, FLY_WING);
          put(f.x - sy * side * w - cx * 1.2, f.y + cx * side * w - sy * 1.2, FLY_WING);
        }
      }

      ctx.putImageData(img, 0, 0);
    }

    const loop = () => { step(); draw(); raf = requestAnimationFrame(loop); };

    const onMove = (e: PointerEvent) => { pointer.x = e.clientX / SCALE; pointer.y = e.clientY / SCALE; pointer.active = true; };
    const onLeave = () => { pointer.active = false; pointer.px = -999; };
    const onDown = (e: PointerEvent) => {
      if (quiet) return; // clicks on app pages are for buttons, not stones
      const x = e.clientX / SCALE, y = e.clientY / SCALE;
      disturb(x, y, 1.5, 16);
      scares.push({ x, y, t: frame });
    };
    const onDrop = (e: Event) => {
      const { x, y, power } = (e as CustomEvent<{ x: number; y: number; power: number }>).detail;
      disturb(x / SCALE, y / SCALE, 2 * power, 22 * power);
      scares.push({ x: x / SCALE, y: y / SCALE, t: frame });
    };
    let resizeTimer = 0;
    const onResize = () => { clearTimeout(resizeTimer); resizeTimer = window.setTimeout(build, 150); };

    build();
    loop();
    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerdown", onDown, { passive: true });
    document.addEventListener("pointerleave", onLeave);
    window.addEventListener("blur", onLeave);
    window.addEventListener("pond:drop", onDrop);
    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(resizeTimer);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerdown", onDown);
      document.removeEventListener("pointerleave", onLeave);
      window.removeEventListener("blur", onLeave);
      window.removeEventListener("pond:drop", onDrop);
      window.removeEventListener("resize", onResize);
    };
  }, [quiet]);

  return (
    <>
      <canvas
        ref={ref}
        aria-hidden
        className="fixed inset-0 -z-10 h-screen w-screen"
        style={{ imageRendering: "pixelated" }}
      />
      {/* shade over the pond so text stays readable: darkest behind the centre column */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10"
        style={{
          background: quiet
            ? "radial-gradient(ellipse 70% 80% at 50% 45%, rgba(2,4,8,.9), rgba(2,4,8,.78) 65%, rgba(2,4,8,.68))"
            : "radial-gradient(ellipse 55% 70% at 50% 50%, rgba(2,4,8,.6), rgba(2,4,8,.25) 70%, rgba(2,4,8,.15))",
        }}
      />
    </>
  );
}
