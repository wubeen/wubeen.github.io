#!/usr/bin/env python3
"""
Contrast audit for a rendered web page (light + dark mode).

How it works: renders the page twice per color mode. Pass 1 hides all text and
takes a screenshot, so it captures the real background behind every text
element: gradients, blurred "mesh" orbs, translucent cards. Pass 2 reads each
text element's computed color, size and weight. The script then computes the
WCAG contrast of the text color against the actual background pixels behind it.

Usage:
  pip install playwright && playwright install chromium
  python3 contrast_audit.py http://localhost:1313/ [--out report_dir] [--width 1280]

Exit code 1 if any text fails WCAG AA (4.5:1 normal, 3:1 large text).
"""
import argparse, json, os, sys
from playwright.sync_api import sync_playwright
from PIL import Image

COLLECT_JS = r"""
() => {
  const cv = document.createElement('canvas'); cv.width = cv.height = 1;
  const cx = cv.getContext('2d', { willReadFrequently: true });
  const toRGBA = (c) => {
    cx.clearRect(0, 0, 1, 1); cx.fillStyle = '#000'; cx.fillStyle = c;
    cx.fillRect(0, 0, 1, 1); const d = cx.getImageData(0, 0, 1, 1).data;
    return [d[0], d[1], d[2], d[3] / 255];
  };
  const out = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  let el;
  while ((el = walker.nextNode())) {
    // text nodes with at least one letter or digit (skips emoji-only nodes such as a status icon)
    const own = [...el.childNodes].filter(n => n.nodeType === 3 && /[\p{L}\p{N}]/u.test(n.textContent));
    const isIcon = el.tagName.toLowerCase() === 'svg';
    if (!own.length && !isIcon) continue;
    if (el.closest('[aria-hidden="true"]') && !isIcon) continue;
    if (el.closest('svg') && !isIcon) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    let r;
    if (isIcon) { r = el.getBoundingClientRect(); }
    else { const range = document.createRange(); range.selectNodeContents(own[0]); r = range.getBoundingClientRect(); }
    if (r.width < 2 || r.height < 2) continue;
    let op = 1, p = el;
    while (p && p.nodeType === 1) { op *= parseFloat(getComputedStyle(p).opacity || '1'); p = p.parentElement; }
    if (op < 0.05) continue;
    const color = isIcon ? (cs.color) : cs.color;
    const fg = toRGBA(color); fg[3] *= op;
    const text = isIcon ? `[icon] ${(el.closest('a,button')?.getAttribute('aria-label') || el.closest('a,button')?.getAttribute('title') || '')}`
                        : own.map(n => n.textContent.trim()).join(' ').slice(0, 70);
    const sel = (() => { const parts = []; let e = el; for (let i = 0; e && e.nodeType === 1 && i < 4; i++, e = e.parentElement) {
      let s = e.tagName.toLowerCase(); if (e.id) { s += '#' + e.id; parts.unshift(s); break; }
      const c = [...e.classList].filter(x => !x.includes(':') && !x.includes('[') && !x.includes('/')).slice(0, 3); if (c.length) s += '.' + c.join('.');
      parts.unshift(s); } return parts.join(' > '); })();
    out.push({ text, sel, isIcon, fg, colorCss: color,
      fontSize: parseFloat(cs.fontSize), fontWeight: parseInt(cs.fontWeight, 10) || 400,
      x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height });
  }
  return out;
}
"""

HIDE_TEXT_CSS = """
*, *::before, *::after { color: transparent !important; -webkit-text-fill-color: transparent !important;
  text-shadow: none !important; caret-color: transparent !important; text-decoration-color: transparent !important; }
svg, img, picture, video, canvas { visibility: hidden !important; }
*, *::before, *::after { animation: none !important; transition: none !important; }
"""
FREEZE_CSS = "*, *::before, *::after { animation: none !important; transition: none !important; }"

def lum(c):
    def f(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])

def ratio(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

def blend(fg, bg):
    a = fg[3]
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3))

def audit(page, url, mode, outdir, width):
    page.goto(url, wait_until="networkidle")
    page.evaluate(f"""() => {{ try {{ localStorage.setItem('wc-color-theme', '{mode}'); localStorage.removeItem('hb-theme-pack'); }} catch(e) {{}} }}""")
    page.reload(wait_until="networkidle")
    page.add_style_tag(content=FREEZE_CSS)
    page.wait_for_timeout(400)
    is_dark = page.evaluate("() => document.documentElement.classList.contains('dark')")
    items = page.evaluate(COLLECT_JS)
    shot_text = os.path.join(outdir, f"{mode}_page.png")
    page.screenshot(path=shot_text, full_page=True)
    page.add_style_tag(content=HIDE_TEXT_CSS)
    page.wait_for_timeout(200)
    shot_bg = os.path.join(outdir, f"{mode}_bg.png")
    page.screenshot(path=shot_bg, full_page=True)
    img = Image.open(shot_bg).convert("RGB")
    W, H = img.size
    rows = []
    for it in items:
        x0, y0 = max(0, int(it["x"])), max(0, int(it["y"]))
        x1, y1 = min(W, int(it["x"] + it["w"])), min(H, int(it["y"] + it["h"]))
        if x1 <= x0 or y1 <= y0:
            continue
        step = max(1, int(((x1 - x0) * (y1 - y0) / 400) ** 0.5))
        samples = [img.getpixel((x, y)) for x in range(x0, x1, step) for y in range(y0, y1, step)]
        rs = sorted(ratio(blend(it["fg"], s), s) for s in samples)
        worst = rs[max(0, int(len(rs) * 0.1) - 1)]  # 10th percentile
        large = it["fontSize"] >= 24 or (it["fontSize"] >= 18.66 and it["fontWeight"] >= 700)
        need = 3.0 if (large or it["isIcon"]) else 4.5
        bgmed = sorted(samples, key=lum)[len(samples) // 2]
        rows.append({**it, "ratio": round(worst, 2), "need": need, "pass": worst >= need,
                     "fgHex": "#%02x%02x%02x" % tuple(int(v) for v in it["fg"][:3]),
                     "bgHex": "#%02x%02x%02x" % tuple(bgmed)})
    return is_dark, rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", default="contrast_report")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--modes", default="light,dark")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    failed_any = False
    report = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        for mode in a.modes.split(","):
            ctx = b.new_context(viewport={"width": a.width, "height": 900}, color_scheme=mode, device_scale_factor=1)
            page = ctx.new_page()
            is_dark, rows = audit(page, a.url, mode, a.out, a.width)
            fails = [r for r in rows if not r["pass"]]
            report[mode] = rows
            print(f"\n=== {mode.upper()} (html.dark={is_dark}) — {len(rows)} text items, {len(fails)} below WCAG AA")
            seen = set()
            for r in sorted(fails, key=lambda r: r["ratio"]):
                key = (r["sel"], r["fgHex"])
                if key in seen:
                    continue
                seen.add(key)
                print(f"  {r['ratio']:5.2f} < {r['need']:.1f}  {r['fgHex']} on {r['bgHex']}  {r['fontSize']:.0f}px/{r['fontWeight']}  "
                      f"\"{r['text'][:50]}\"  [{r['sel']}]")
            failed_any |= bool(fails)
            ctx.close()
        b.close()
    with open(os.path.join(a.out, "report.json"), "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print(f"\nScreenshots and report.json written to {a.out}/")
    sys.exit(1 if failed_any else 0)

if __name__ == "__main__":
    main()
