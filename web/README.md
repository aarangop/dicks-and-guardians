# Site

Static site: `index.html`, one bundled script (`app.js`) and the data embedded as `data/people.js`.
The site never calls an API. It works when deployed and when you just double-click `index.html`.
Source lives in `js/` as ES modules; `app.js` is generated from it.

## Update the data (offline, when you decide)

```sh
uv run python scripts/export_web_data.py     # data/results.json -> web/data/people.{json,js}
git add web/data && git commit -m "Update site data" && git push
```

Only runs with status `done` are exported.

## Edit the code

After changing anything in `web/js/`, rebuild the bundle and commit it:

```sh
./scripts/build_web.sh                       # js/main.js -> web/app.js (esbuild via pnpm dlx)
```

## Run locally

```sh
open web/index.html                          # works straight from disk
python3 -m http.server -d web 8080           # or serve it, then open http://localhost:8080
node --test "tests/web/*.test.mjs"           # unit tests for the filter/rank/group logic
```

`?data=data/other.json` previews another JSON file (needs the served version, same origin only).

## Deploy

**GitHub Pages (wired up):** `.github/workflows/pages.yml` publishes `web/` on every push to
`main` that touches `web/`. One-time setup: repo Settings → Pages → Source: *GitHub Actions*.
Note: Pages on a private repo needs a paid GitHub plan.

**Alternatives, zero config:** Cloudflare Pages or Netlify, connected to the repo with build
command empty and output directory `web`. Or drag the `web/` folder into Netlify Drop.
For a blob-storage setup, upload `web/` to any bucket with static hosting; to swap only the
data, upload just `data/people.json`.

## Notes

- `index.html` has `<meta name="robots" content="noindex">` because the site names real people.
  Delete it to allow search indexing.
- Fonts (Press Start 2P, VT323) load from Google Fonts; monospace fallbacks apply offline.
- All scraped text is HTML-escaped and links are limited to http(s) (`js/format.js`).
