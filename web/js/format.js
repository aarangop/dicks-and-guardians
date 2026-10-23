// Escaping and formatting helpers. All scraped text (claims, quotes, titles) is untrusted:
// every value that reaches innerHTML must go through esc() or safeUrl().

const ENTITIES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

export function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ENTITIES[c]);
}

/** Only http(s) links are allowed; anything else (javascript:, data:) becomes "#". */
export function safeUrl(url) {
  try {
    const u = new URL(url);
    return u.protocol === "https:" || u.protocol === "http:" ? u.href : "#";
  } catch {
    return "#";
  }
}

export function domain(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

/** 872872 -> "872,872" and null -> "------" like an empty arcade slot. */
export function points(p) {
  return p == null ? "------" : p.toLocaleString("en-US");
}

export const pct = (x) => `${Math.round(x * 100)}%`;

export function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toISOString().slice(0, 10);
}

export const ordinal = (n) => {
  const suffix = ["TH", "ST", "ND", "RD"];
  const v = n % 100;
  return `${n}${suffix[(v - 20) % 10] ?? suffix[v] ?? suffix[0]}`;
};

/**
 * Turn the model-written summary into safe HTML: **bold**, paragraphs, and citation brackets
 * like [R1-E01, https://...] into clickable evidence chips.
 */
export function renderSummary(text) {
  return String(text ?? "")
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const withCites = line.replace(/\[([^\]]*R\d-E\d+[^\]]*)\]/g, (_, inner) => {
        const ids = inner.match(/R\d-E\d+/g) ?? [];
        return ids.map((id) => `\u0000${id}\u0001`).join("");
      });
      return `<p>${esc(withCites)
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\u0000(R\d-E\d+)\u0001/g, '<a class="cite" href="#" data-ev="$1">$1</a>')}</p>`;
    })
    .join("");
}
