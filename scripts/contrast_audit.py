#!/usr/bin/env python3
"""WCAG contrast audit for a rendered Hugo page.

Renders light and dark. For each visible text run and icon, hides the
foreground, screenshots the real background pixels, and computes contrast.
AA is 4.5:1 for body text and 3:1 for large text and icons.

Exits 1 when any sample is below AA.
"""

import argparse
import io
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright


def parse_args():
    parser = argparse.ArgumentParser(description="Audit WCAG contrast on a page")
    parser.add_argument("url")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--out", default="/tmp/audit")
    parser.add_argument("--height", type=int, default=900)
    return parser.parse_args()


def channel(value):
    value = value / 255.0
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = (channel(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a, b):
    l1, l2 = luminance(a), luminance(b)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def parse_color(value):
    value = (value or "").strip()
    if not value or value == "transparent":
        return None
    if value.startswith("#"):
        hex_value = value[1:]
        if len(hex_value) == 3:
            hex_value = "".join(ch * 2 for ch in hex_value)
        if len(hex_value) >= 6:
            return tuple(int(hex_value[i : i + 2], 16) for i in (0, 2, 4))
        return None
    if value.startswith("rgb"):
        nums = value[value.find("(") + 1 : value.find(")")].split(",")
        parts = []
        for num in nums[:3]:
            num = num.strip()
            if num.endswith("%"):
                parts.append(int(round(float(num[:-1]) * 2.55)))
            else:
                parts.append(int(round(float(num))))
        if len(parts) == 3:
            return tuple(parts)
    return None


COLLECT_JS = r"""
() => {
  const out = [];
  const seen = new Set();

  function visible(el) {
    const style = getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") return false;
    if (parseFloat(style.opacity || "1") === 0) return false;
    const rect = el.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) return false;
    return true;
  }

  function box(el) {
    const rect = el.getBoundingClientRect();
    return {
      x: rect.x + window.scrollX,
      y: rect.y + window.scrollY,
      w: rect.width,
      h: rect.height,
    };
  }

  function push(el, kind, text, color) {
    if (!color) return;
    if (seen.has(el)) return;
    if (!visible(el)) return;
    const style = getComputedStyle(el);
    const size = parseFloat(style.fontSize) || 16;
    const weight = parseInt(style.fontWeight, 10) || 400;
    seen.add(el);
    out.push({
      kind,
      text: (text || "").replace(/\s+/g, " ").trim().slice(0, 80),
      color,
      size,
      weight,
      box: box(el),
    });
  }

  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();
  while (node) {
    const raw = node.nodeValue || "";
    if (raw.trim()) {
      const el = node.parentElement;
      if (el && !["SCRIPT", "STYLE", "NOSCRIPT"].includes(el.tagName)) {
        push(el, "text", raw, getComputedStyle(el).color);
      }
    }
    node = walker.nextNode();
  }

  document.querySelectorAll("a, button, span, p, li, h1, h2, h3, h4, div").forEach((el) => {
    const after = getComputedStyle(el, "::after").content;
    if (!after || after === "none" || after === "normal" || after === '""') return;
    const label = after.replace(/^["']|["']$/g, "");
    if (!label.trim()) return;
    push(el, "text", label, getComputedStyle(el).color);
  });

  document.querySelectorAll("svg").forEach((svg) => {
    if (!visible(svg)) return;
    const style = getComputedStyle(svg);
    let color = style.color;
    const painted = svg.querySelector("[stroke], [fill]");
    if (painted) {
      const paintedStyle = getComputedStyle(painted);
      if (paintedStyle.stroke && paintedStyle.stroke !== "none") color = paintedStyle.stroke;
      else if (paintedStyle.fill && paintedStyle.fill !== "none") color = paintedStyle.fill;
    }
    push(svg, "icon", "icon", color);
  });

  return out;
}
"""

HIDE_CSS = """
html.bw-hide-text, html.bw-hide-text * {
  color: transparent !important;
  -webkit-text-fill-color: transparent !important;
  text-shadow: none !important;
  caret-color: transparent !important;
}
html.bw-hide-text svg, html.bw-hide-text svg * {
  fill: transparent !important;
  stroke: transparent !important;
}
"""


def sample_background(image, box):
    width, height = image.size
    left = max(0, int(box["x"] + box["w"] * 0.3))
    right = min(width - 1, int(box["x"] + box["w"] * 0.7))
    top = max(0, int(box["y"] + box["h"] * 0.3))
    bottom = min(height - 1, int(box["y"] + box["h"] * 0.7))
    if right < left:
        left = right = min(width - 1, max(0, int(box["x"] + box["w"] / 2)))
    if bottom < top:
        top = bottom = min(height - 1, max(0, int(box["y"] + box["h"] / 2)))
    pixels = []
    xs = {left, (left + right) // 2, right}
    ys = {top, (top + bottom) // 2, bottom}
    for y in ys:
        for x in xs:
            pixels.append(image.getpixel((x, y))[:3])
    pixels.sort(key=luminance)
    return pixels[len(pixels) // 2]


def required_ratio(item):
    if item["kind"] == "icon":
        return 3.0
    size = item["size"]
    weight = item["weight"]
    if size >= 24 or (size >= 18.67 and weight >= 700):
        return 3.0
    return 4.5


def audit_mode(page, mode, out_dir, width):
    page.evaluate(
        """(mode) => {
          localStorage.removeItem('hb-theme-pack');
          localStorage.setItem('wc-color-theme', mode);
          document.documentElement.classList.toggle('dark', mode === 'dark');
          document.documentElement.setAttribute('data-theme-pack', '');
        }""",
        mode,
    )
    page.wait_for_timeout(250)
    items = page.evaluate(COLLECT_JS)
    page.screenshot(path=str(out_dir / f"{mode}_page.png"), full_page=True)

    page.evaluate(
        """(css) => {
          let style = document.getElementById('bw-hide-style');
          if (!style) {
            style = document.createElement('style');
            style.id = 'bw-hide-style';
            document.head.appendChild(style);
          }
          style.textContent = css;
          document.documentElement.classList.add('bw-hide-text');
        }""",
        HIDE_CSS,
    )
    page.wait_for_timeout(100)
    background = Image.open(io.BytesIO(page.screenshot(full_page=True))).convert("RGB")
    page.evaluate(
        """() => {
          document.documentElement.classList.remove('bw-hide-text');
        }"""
    )

    failures = []
    for item in items:
        fg = parse_color(item["color"])
        if not fg:
            continue
        bg = sample_background(background, item["box"])
        ratio = contrast_ratio(fg, bg)
        need = required_ratio(item)
        if ratio + 1e-6 < need:
            failures.append((ratio, need, item, fg, bg))
    failures.sort(key=lambda row: row[0])
    return failures


def main():
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(
            viewport={"width": args.width, "height": args.height},
            device_scale_factor=1,
        )
        page.add_init_script(
            """() => {
              localStorage.removeItem('hb-theme-pack');
              localStorage.removeItem('wc-color-theme');
            }"""
        )
        page.goto(args.url, wait_until="networkidle", timeout=60000)
        page.evaluate("() => document.fonts && document.fonts.ready")
        for mode in ("light", "dark"):
            failures = audit_mode(page, mode, out_dir, args.width)
            print(f"{mode.upper()}: {len(failures)} below WCAG AA")
            for ratio, need, item, fg, bg in failures[:80]:
                label = item["text"] or item["kind"]
                print(
                    f"  {ratio:.2f}:1 need {need:.1f}  {item['size']:.0f}px/{item['weight']}  "
                    f"fg={fg} bg={bg}  {label}"
                )
            if len(failures) > 80:
                print(f"  ... {len(failures) - 80} more")
            total += len(failures)
        browser.close()
    if total:
        print(f"RESULT failures={total}")
        return 1
    print("RESULT failures=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
