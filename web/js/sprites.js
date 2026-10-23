// Tiny pixel-art sprites drawn as inline SVG rects. "." is transparent, other letters index
// into the palette passed to sprite().

const GRIDS = {
  crown: ["X...X...X", "XX.XXX.XX", "XXXXXXXXX", "XXJXXXJXX", "XXXXXXXXX"],
  skull: [
    ".XXXXXXX.",
    "XXXXXXXXX",
    "XX..X..XX",
    "XX..X..XX",
    "XXXXXXXXX",
    "..XXXXX..",
    "..X.X.X..",
    "..XXXXX..",
  ],
  star: ["...X...", "...X...", ".XXXXX.", "XXXXXXX", ".XXXXX.", ".XX.XX.", ".X...X."],
  heart: [".XX.XX.", "XXXXXXX", "XXXXXXX", ".XXXXX.", "..XXX..", "...X..."],
};

function svg(rows, palette, px, cls = "") {
  const h = rows.length;
  const w = rows[0].length;
  let rects = "";
  rows.forEach((row, y) => {
    [...row].forEach((ch, x) => {
      if (ch !== "." && palette[ch]) {
        rects += `<rect x="${x}" y="${y}" width="1" height="1" fill="${palette[ch]}"/>`;
      }
    });
  });
  return `<svg class="sprite ${cls}" viewBox="0 0 ${w} ${h}" width="${w * px}" height="${h * px}" shape-rendering="crispEdges" aria-hidden="true">${rects}</svg>`;
}

export function sprite(name, color, px = 4, cls = "") {
  return svg(GRIDS[name], { X: color, J: "#ff4f9a" }, px, cls);
}

const HAIR = ["#ff4f9a", "#3be8ff", "#7dff5a", "#b48cff", "#ff9a2e", "#fff7e0"];
const MOUTH = {
  smile: ["SMSSSMS", "SSMMMSS"],
  flat: ["SSSSSSS", "SSMMMSS"],
  frown: ["SSMMMSS", "SMSSSMS"],
};

function hash(text) {
  let h = 2166136261;
  for (const c of text) h = Math.imul(h ^ c.charCodeAt(0), 16777619);
  return h >>> 0;
}

/**
 * A generic pixel face. Everyone gets the same neutral skin tone and only the hair color varies
 * (by a hash of the id), so it never pretends to be a likeness. The mouth follows the tier.
 */
export function face(id, tier, px = 6) {
  const mood = tier === "not_a_dick" ? "smile" : tier === "minor" || tier === "unrated" ? "flat" : "frown";
  const [m1, m2] = MOUTH[mood];
  const rows = [
    "..HHHHH..",
    ".HHHHHHH.",
    "HHSSSSSHH",
    "HSSSSSSSH",
    "HSESSSESH",
    `.${"SSSSSSS"}.`,
    `.${m1}.`,
    `.${m2}.`,
    "..SSSSS..",
  ];
  const palette = { H: HAIR[hash(id) % HAIR.length], S: "#ffd98a", E: "#14103f", M: "#14103f" };
  return svg(rows, palette, px, "face");
}
