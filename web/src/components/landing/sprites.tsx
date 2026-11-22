// Pixel sprites drawn for Synex (original art). Each row is a string; each character is one pixel.
// "." is empty; other characters map to colours in the palette passed to <Sprite>.

export const KRILL = [
  "......a.....",
  ".....a......",
  "....a..pppp.",
  "...a.ppppHpp",
  "..pppppppppp",
  ".pppppppppp.",
  "pppppppppp..",
  ".l.l.l.l.l..",
  "l.l.l.l.l...",
];

export const FISH = [
  "....bbbb....",
  "b..bbbbbbb..",
  "bbbbbbbbebb.",
  "bbbbbbbbbbbb",
  "b..bbbbbbb..",
  "....bbbb....",
];

export const SMALL_FISH = [
  "..bbb..",
  "bbbbeb.",
  "bbbbbbb",
  "..bbb..",
];

export const BOTTLE = [
  "..cc..",
  "..cc..",
  ".gggg.",
  "gggggg",
  "gwwwwg",
  "gwwwwg",
  "gggggg",
];

export const PEARL = [
  ".wwww.",
  "wwHHww",
  "wHwwww",
  "wwwwww",
  ".wwww.",
];

export const LANTERN = [
  "......y.",
  ".....y..",
  "..bbbyy.",
  ".bbbbbbb",
  "bbbbebbb",
  ".bbbbbbb",
  "..bbbbb.",
];

export const CHEST = [
  ".gggggg.",
  "gyyyyyyg",
  "gggggggg",
  "gyyggyyg",
  "gyyyyyyg",
  "gggggggg",
];

export function Sprite({
  rows, palette, scale = 4, className = "", style,
}: {
  rows: string[];
  palette: Record<string, string>;
  scale?: number;
  className?: string;
  style?: React.CSSProperties;
}) {
  const w = rows[0].length;
  const h = rows.length;
  return (
    <svg
      width={w * scale}
      height={h * scale}
      viewBox={`0 0 ${w} ${h}`}
      shapeRendering="crispEdges"
      className={className}
      style={style}
      aria-hidden
    >
      {rows.flatMap((row, y) =>
        [...row].map((ch, x) => (palette[ch] ? <rect key={`${x}-${y}`} x={x} y={y} width={1} height={1} fill={palette[ch]} /> : null)),
      )}
    </svg>
  );
}

/** A pixel kelp silhouette: a stem with leaves alternating sides, generated so each one differs. */
export function Kelp({ height = 40, seed = 1, color = "#0b1a2e", scale = 8, flip = false }: {
  height?: number; seed?: number; color?: string; scale?: number; flip?: boolean;
}) {
  const w = 14;
  const cells: [number, number][] = [];
  let x = 6;
  for (let y = 0; y < height; y++) {
    if ((y * 7 + seed * 3) % 9 === 0) x += ((y + seed) % 2 ? 1 : -1);
    x = Math.max(4, Math.min(9, x));
    cells.push([x, y], [x + 1, y]);
    if (y > 3 && (y + seed) % 5 === 0) {
      const dir = (y + seed) % 10 === 0 ? 1 : -1;
      for (let k = 1; k <= 3 + ((y + seed) % 3); k++) cells.push([x + (dir > 0 ? 1 + k : -k), y - Math.floor(k / 2)]);
    }
  }
  return (
    <svg
      width={w * scale}
      height={height * scale}
      viewBox={`0 0 ${w} ${height}`}
      shapeRendering="crispEdges"
      style={{ transform: flip ? "scaleX(-1)" : undefined }}
      aria-hidden
    >
      {cells.map(([cx, cy], i) => <rect key={i} x={cx} y={height - 1 - cy} width={1} height={1} fill={color} />)}
    </svg>
  );
}
