#!/usr/bin/env python3
# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Atlante's brand on top of Plane: name, logo, colors, icons and texts.

Re-run it after every update taken from Plane: it always starts from what is in
the repository and gives the same result (running it twice changes nothing).

    python3 -I atlante/script/marchio.py             # apply the brand
    python3 -I atlante/script/marchio.py --verifica  # only check, exit 1 if "Plane" is still visible

Sources, in atlante/marchio/: marchio.json (name, description, color), segno.svg
(the mark, in the text color), icona.svg (the app icon). PNG icons are made on a
Mac with qlmanage and sips; elsewhere the ones already saved in atlante/marchio/icone/
are used.
"""

import json
import math
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRAND = ROOT / "atlante" / "marchio"
ICONS = BRAND / "icone"
PROPEL_VARIABLES = ROOT / "apps/web/node_modules/@makeplane/propel/dist/styles/variables.css"
COLORS_CSS = ROOT / "packages/tailwind-config/atlante-colori.css"
TAILWIND_INDEX = ROOT / "packages/tailwind-config/index.css"
LOCALES = [ROOT / "packages/i18n/src/locales/it", ROOT / "packages/i18n/src/locales/en"]

# Names of Plane's paid offers: they only appear in advertising that Atlante hides.
PLANE_OFFERS = r"Plane (?:Pro|AI|One|Business|Enterprise|Pages|Publish)"
# "Plane" as a word, also at the end of a sentence ("...in Plane."); not inside web addresses
# (plane.so, Plane-xyz, Plane/...): zeta3-progetti#12.
PLANE_WORD = re.compile(r"\bPlane\b(?!\.[A-Za-z0-9])(?![/-])")

# Icons: (size, files that get it).
ICON_TARGETS = {
    16: ["apps/{app}/app/assets/favicon/favicon-16x16.png"],
    32: ["apps/{app}/app/assets/favicon/favicon-32x32.png"],
    180: ["apps/{app}/app/assets/favicon/apple-touch-icon.png", "apps/web/app/assets/icons/icon-180x180.png"],
    192: ["apps/{app}/public/favicon/android-chrome-192x192.png", "apps/web/public/icons/icon-192x192.png"],
    348: ["apps/web/public/icons/icon-348x348.png"],
    512: [
        "apps/{app}/public/favicon/android-chrome-512x512.png",
        "apps/web/app/assets/icons/icon-512x512.png",
        "apps/web/public/icons/icon-512x512.png",
    ],
}
APPS = ("web", "admin", "space")
ICO_TARGETS = ["apps/{app}/app/assets/favicon/favicon.ico"]
SPINNER_TARGETS = {
    "apps/web/app/assets/images/logo-spinner-light.gif": "#1F2937",  # light theme: dark mark
    "apps/web/app/assets/images/logo-spinner-dark.gif": "#F3F4F6",  # dark theme: light mark
}
OG_IMAGE = "apps/web/app/assets/og-image.png"

TITLE_FILES = ["apps/web/app/root.tsx", "apps/admin/app/root.tsx", "apps/space/app/root.tsx"]
TITLE_PATTERN = r'const APP_TITLE = "[^"]*";(?: // ATLANTE[^\n]*)?'
METADATA = ROOT / "packages/constants/src/metadata.ts"
MANIFESTS = ["apps/web/manifest.json", "apps/web/public/manifest.json", "apps/web/public/favicon/site.webmanifest"]
EMAIL_TEMPLATES = ROOT / "apps/api/templates/emails"
EMAIL_TASKS = sorted((ROOT / "apps/api/plane/bgtasks").glob("*.py"))
# Images that Plane's emails load from other servers: each opened email would tell those servers.
EMAIL_LOGO = re.compile(r'<img[^>]*src="https://(?:media\.docs\.plane\.so/logo|ik\.imagekit\.io)/[^"]*"[^>]*>')
EMAIL_EXTERNAL_IMAGE = re.compile(r'<img[^>]*src="https?://[^"]*"[^>]*>')
LOGO = ROOT / "packages/blocks/src/icons/brand/plane-logo.tsx"
LOCKUP = ROOT / "packages/blocks/src/icons/brand/plane-lockup.tsx"
ADMIN_LOCKUP = ROOT / "apps/admin/components/common/plane-lockup.tsx"  # the admin panel keeps its own copy

PLANE_HEADER = """/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */
"""


def load_brand():
    brand = json.loads((BRAND / "marchio.json").read_text(encoding="utf-8"))
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", brand["colore"]):
        sys.exit("marchio.json: il colore va scritto come #RRGGBB")
    return brand


# Colors -------------------------------------------------------------------------------------


def _srgb_to_linear(channel):
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def hex_to_oklch(hex_color):
    """The OKLCH hue of a color: the interface keeps Plane's lightness ladder and takes this hue."""
    r, g, b = (_srgb_to_linear(int(hex_color[i : i + 2], 16) / 255) for i in (1, 3, 5))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    lightness = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return lightness, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360


BRAND_SHADE = re.compile(r"--brand-(\w+): oklch\(([\d.]+) ([\d.]+) ([\d.]+)\);")


def propel_brand_themes():
    """Plane's brand colors theme by theme: the light ones, then those inside "@variant dark".
    Read by position, never by counting: each theme also has its main color, --brand-default (#23)."""
    text = PROPEL_VARIABLES.read_text(encoding="utf-8")
    dark_start = text.find("@variant dark {")
    dark_end = text.find("@variant", dark_start + 1)
    light = BRAND_SHADE.findall(text[:dark_start]) if dark_start > 0 else []
    dark = BRAND_SHADE.findall(text[dark_start:dark_end]) if dark_end > dark_start > 0 else []
    names = [name for name, *_ in light]
    if "default" not in names or names != [name for name, *_ in dark]:
        sys.exit("Non trovo gli stessi colori nel tema chiaro e scuro di Plane: forse è cambiata la libreria propel.")
    return light, dark


def colors_css(brand):
    """Plane's brand palette (light and dark) with Atlante's hue. Custom themes stay the user's."""
    light, dark = propel_brand_themes()
    _, _, hue = hex_to_oklch(brand["colore"])
    blocks = []
    for selector, part in (
        (':root:not([data-custom-theme="true"])', light),
        (':root[data-theme*="dark"]:not([data-custom-theme="true"])', dark),
    ):
        lines = "\n".join(f"  --brand-{name}: oklch({lightness} {chroma} {hue:.2f});" for name, lightness, chroma, _ in part)
        blocks.append(f"{selector} {{\n{lines}\n}}")
    return (
        "/* Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.\n"
        " * SPDX-License-Identifier: AGPL-3.0-only\n"
        " * Generated by atlante/script/marchio.py from atlante/marchio/marchio.json: do not edit by hand.\n"
        " * Plane's brand palette with Atlante's hue, same lightness, so legibility stays the same. */\n\n"
        + "\n\n".join(blocks)
        + "\n"
    )


# Logo ---------------------------------------------------------------------------------------

JSX_ATTRIBUTES = {
    "stroke-width": "strokeWidth",
    "stroke-linecap": "strokeLinecap",
    "stroke-linejoin": "strokeLinejoin",
    "fill-rule": "fillRule",
    "clip-rule": "clipRule",
    "font-family": "fontFamily",
    "font-size": "fontSize",
    "font-weight": "fontWeight",
    "text-anchor": "textAnchor",
}


def _jsx(element, indent):
    tag = element.tag.split("}")[-1]
    attributes = []
    for key, value in element.attrib.items():
        key = JSX_ATTRIBUTES.get(key, key)
        value = "{color}" if value == "currentColor" else f'"{value}"'
        attributes.append(f"{key}={value}")
    children = [_jsx(child, indent + "  ") for child in element]
    attrs = (" " + " ".join(attributes)) if attributes else ""
    if not children:
        return f"{indent}<{tag}{attrs} />"
    return f"{indent}<{tag}{attrs}>\n" + "\n".join(children) + f"\n{indent}</{tag}>"


def mark():
    """The mark: its viewBox, the attributes of its root (stroke, fill) and its drawing as JSX."""
    root = ET.fromstring((BRAND / "segno.svg").read_text(encoding="utf-8"))
    group = ET.Element("g", {k: v for k, v in root.attrib.items() if k not in ("viewBox", "width", "height")})
    group.extend(list(root))
    return root.attrib["viewBox"], group


def mark_box():
    """The mark's viewBox as numbers: x, y, width, height."""
    view_box, _ = mark()
    return tuple(float(n) for n in view_box.split())


def placed_mark(color, x, y, width):
    """The mark drawn in one color, scaled to the given width, with its top left corner at x, y."""
    vx, vy, vw, _ = mark_box()
    scale = width / vw
    _, group = mark()
    group.set("transform", f"translate({x - vx * scale:.3f} {y - vy * scale:.3f}) scale({scale:.4f})")
    return ET.tostring(group, encoding="unicode").replace("currentColor", color).replace("ns0:", "")


def logo_tsx():
    view_box, group = mark()
    _, _, vw, vh = mark_box()
    # The default size keeps the mark's proportions (Zeta3's logo is wide); most pages set the height only.
    height = 26
    width = round(height * vw / vh)
    return (
        PLANE_HEADER
        + "\n// ATLANTE: the drawing is Atlante's mark (atlante/marchio/segno.svg), written by atlante/script/marchio.py\n\n"
        + 'import * as React from "react";\n\n'
        + "export type PlaneLogoProps = React.ComponentPropsWithoutRef<\"svg\">;\n\n"
        + f'export function PlaneLogo({{ width = "{width}", height = "{height}", className, color = "currentColor" }}: PlaneLogoProps) {{\n'
        + "  return (\n"
        + f'    <svg width={{width}} height={{height}} viewBox="{view_box}" xmlns="http://www.w3.org/2000/svg" className={{className}}>\n'
        + _jsx(group, "      ")
        + "\n    </svg>\n  );\n}\n"
    )


def lockup_tsx(brand):
    """Mark and name side by side, in Plane's lockup box (253 x 53): the mark 30 high, the name after it."""
    view_box, group = mark()
    vx, vy, vw, vh = mark_box()
    scale = min(30 / vh, 110 / vw)
    top = (53 - vh * scale) / 2
    group.set("transform", f"translate({-vx * scale:.3f} {top - vy * scale:.3f}) scale({scale:.4f})")
    name_x = round(vw * scale + 16)
    return (
        PLANE_HEADER
        + "\n// ATLANTE: Atlante's mark and name (atlante/marchio), written by atlante/script/marchio.py\n\n"
        + 'import * as React from "react";\n\n'
        + "export type PlaneLockupProps = React.ComponentPropsWithoutRef<\"svg\">;\n\n"
        + 'export function PlaneLockup({ width = "253", height = "53", className, color = "currentColor" }: PlaneLockupProps) {\n'
        + "  return (\n"
        + '    <svg width={width} height={height} viewBox="0 0 253 53" xmlns="http://www.w3.org/2000/svg" className={className}>\n'
        + _jsx(group, "      ")
        + "\n"
        + f'      <text x="{name_x}" y="38" fill={{color}} fontFamily="Inter, sans-serif" fontSize="32" fontWeight="500">\n'
        + f"        {brand['nome']}\n"
        + "      </text>\n"
        + "    </svg>\n  );\n}\n"
    )


# Icons --------------------------------------------------------------------------------------


def _render(svg_text, size, out, crop_height=None):
    """SVG to PNG of the given size, with the Mac's own tools. They handle square drawings only:
    a wide picture is drawn square and then cut to crop_height, keeping the middle."""
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "disegno.svg"
        source.write_text(svg_text, encoding="utf-8")
        thumbnail = str(max(512, size[0]))
        subprocess.run(["qlmanage", "-t", "-s", thumbnail, "-o", tmp, str(source)], check=True, capture_output=True)
        rendered = Path(tmp) / "disegno.svg.png"
        subprocess.run(["sips", "-z", str(size[1]), str(size[0]), str(rendered), "--out", str(out)], check=True, capture_output=True)
        if crop_height:
            subprocess.run(["sips", "-c", str(crop_height), str(size[0]), str(out)], check=True, capture_output=True)


def _ico(pngs, out):
    """A .ico with PNG images inside (supported by every browser)."""
    images = [(size, path.read_bytes()) for size, path in pngs]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, data = b"", b""
    for size, png in images:
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(png), offset + len(data))
        data += png
    out.write_bytes(header + entries + data)


def make_icons(brand):
    """Make the PNG icons from icona.svg (Mac only); elsewhere keep the saved ones."""
    if not shutil.which("qlmanage") or not shutil.which("sips"):
        print("Icone: qlmanage non disponibile, uso quelle già salvate in atlante/marchio/icone/")
        return
    ICONS.mkdir(exist_ok=True)
    icon = (BRAND / "icona.svg").read_text(encoding="utf-8")
    for size in (16, 32, 48, 180, 192, 348, 512):
        _render(icon, (size, size), ICONS / f"icona-{size}.png")
    _ico([(size, ICONS / f"icona-{size}.png") for size in (16, 32, 48)], ICONS / "favicon.ico")
    _, _, vw, vh = mark_box()
    for name, color in (("chiaro", "#1F2937"), ("scuro", "#F3F4F6")):
        # A square picture with the mark in the middle, whatever the mark's proportions.
        width = 440 if vw >= vh else 440 * vw / vh
        drawing = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">'
            + placed_mark(color, (512 - width) / 2, (512 - width * vh / vw) / 2, width)
            + "</svg>"
        )
        _render(drawing, (96, 96), ICONS / f"segno-{name}.png")
        subprocess.run(
            ["sips", "-s", "format", "gif", str(ICONS / f"segno-{name}.png"), "--out", str(ICONS / f"segno-{name}.gif")],
            check=True,
            capture_output=True,
        )
    # The share preview (1200 x 630): the mark above the name, white on the brand color. Drawn on a
    # 1200 square with the preview in the middle band (285-915), then cut to 630.
    width = min(420, 160 * vw / vh)
    preview = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200" viewBox="0 0 1200 1200">'
        f'<rect width="1200" height="1200" fill="{brand["colore"]}"/>'
        + placed_mark("#FFFFFF", (1200 - width) / 2, 285 + 130, width)
        + f'<text x="600" y="{285 + 470}" fill="#FFFFFF" font-family="Helvetica, Arial, sans-serif" font-size="110" '
        f'font-weight="600" text-anchor="middle">{brand["nome"]}</text></svg>'
    )
    _render(preview, (1200, 1200), ICONS / "anteprima.png", crop_height=630)


def copy_icons():
    copied = 0
    for size, targets in ICON_TARGETS.items():
        for target in targets:
            for app in APPS if "{app}" in target else (None,):
                path = ROOT / (target.format(app=app) if app else target)
                if path.exists():
                    shutil.copyfile(ICONS / f"icona-{size}.png", path)
                    copied += 1
    for target in ICO_TARGETS:
        for app in APPS:
            path = ROOT / target.format(app=app)
            if path.exists():
                shutil.copyfile(ICONS / "favicon.ico", path)
                copied += 1
    for target, color in SPINNER_TARGETS.items():
        name = "chiaro" if color == "#1F2937" else "scuro"
        shutil.copyfile(ICONS / f"segno-{name}.gif", ROOT / target)
        copied += 1
    shutil.copyfile(ICONS / "anteprima.png", ROOT / OG_IMAGE)
    return copied + 1


# Texts --------------------------------------------------------------------------------------


def _replace_in_values(node, name):
    """Plane -> Atlante in every text of a translation file, never in keys, links or Plane's offers."""
    if isinstance(node, dict):
        return {key: _replace_in_values(value, name) for key, value in node.items()}
    if isinstance(node, str):
        protected = {}

        def keep(match):
            protected[f"\x00{len(protected)}\x00"] = match.group(0)
            return f"\x00{len(protected) - 1}\x00"

        text = re.sub(PLANE_OFFERS, keep, node)
        text = PLANE_WORD.sub(name, text)
        for placeholder, original in protected.items():
            text = text.replace(placeholder, original)
        return text
    return node


def apply_texts(brand):
    changed = []
    for folder in LOCALES:
        for path in sorted(folder.glob("*.json")):
            if path.name == "atlante.json":
                continue
            original = path.read_text(encoding="utf-8")
            data = _replace_in_values(json.loads(original), brand["nome"])
            new = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
            if new != original and json.loads(new) != json.loads(original):
                path.write_text(new, encoding="utf-8")
                changed.append(path)
    return changed


def apply_titles(brand):
    title = brand["nome"]
    for relative in TITLE_FILES:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        new = re.sub(TITLE_PATTERN, f'const APP_TITLE = "{title}"; // ATLANTE: written by atlante/script/marchio.py', text)
        new = re.sub(
            r'const APP_DESCRIPTION = "[^"]*";(?: // ATLANTE[^\n]*)?',
            f'const APP_DESCRIPTION = "{brand["descrizione"]}"; // ATLANTE: written by atlante/script/marchio.py',
            new,
        )
        new = new.replace('name="application-name" content="Plane"', f'name="application-name" content="{title}"')
        new = new.replace('"Plane - Modern project management"', f'"{title}"')
        path.write_text(new, encoding="utf-8")
    text = METADATA.read_text(encoding="utf-8")
    replacements = {
        "SITE_NAME": title,
        "SITE_TITLE": title,
        "SITE_DESCRIPTION": brand["descrizione"],
        "TWITTER_USER_NAME": title,
        "SPACE_SITE_NAME": title,
        "SPACE_SITE_TITLE": title,
        "SPACE_SITE_DESCRIPTION": brand["descrizione"],
    }
    for constant, value in replacements.items():
        text = re.sub(
            rf'export const {constant} =\s*"[^"]*";(?: // ATLANTE[^\n]*)?',
            f'export const {constant} = "{value}"; // ATLANTE: written by atlante/script/marchio.py',
            text,
        )
    METADATA.write_text(text, encoding="utf-8")
    for relative in MANIFESTS:
        path = ROOT / relative
        data = json.loads(path.read_text(encoding="utf-8"))
        data["name"] = title
        data["short_name"] = title
        if "description" in data:
            data["description"] = brand["descrizione"]
        if "theme_color" in data:
            data["theme_color"] = brand["colore"]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def apply_colors(brand):
    COLORS_CSS.write_text(colors_css(brand), encoding="utf-8")
    index = TAILWIND_INDEX.read_text(encoding="utf-8")
    line = '@import "./atlante-colori.css"; /* ATLANTE: Atlante\'s colors, after Plane\'s (atlante/script/marchio.py) */'
    if line not in index:
        index = index.replace('@import "@makeplane/propel/styles";\n', '@import "@makeplane/propel/styles";\n' + line + "\n", 1)
        TAILWIND_INDEX.write_text(index, encoding="utf-8")


# Emails -------------------------------------------------------------------------------------


def apply_emails(brand):
    """No image from other servers in the emails, Atlante's name in texts and subjects."""
    changed = 0
    name = brand["nome"]
    logo_text = (
        f'<span style="font-family: Arial, sans-serif; font-size: 22px; font-weight: 600; color: {brand["colore"]};">'
        f"{name}</span>"
    )
    for path in sorted(EMAIL_TEMPLATES.rglob("*.html")):
        original = path.read_text(encoding="utf-8")
        text = EMAIL_LOGO.sub(logo_text, original)
        text = EMAIL_EXTERNAL_IMAGE.sub("", text)
        text = PLANE_WORD.sub(name, text)
        if text != original:
            path.write_text(text, encoding="utf-8")
            changed += 1
    for path in EMAIL_TASKS:
        original = path.read_text(encoding="utf-8")
        text = "\n".join(
            PLANE_WORD.sub(name, line) if re.match(r"\s*subject = ", line) else line for line in original.split("\n")
        )
        if text != original:
            path.write_text(text, encoding="utf-8")
            changed += 1
    return changed


# Check --------------------------------------------------------------------------------------


def check(brand):
    """Where "Plane" is still visible: texts in Italian and English, titles, manifests, logo."""
    problems = []
    for folder in LOCALES:
        for path in sorted(folder.glob("*.json")):
            if path.name == "atlante.json":  # ours: "based on Plane" is required by the license
                continue

            def walk(node, key=""):
                if isinstance(node, dict):
                    for k, v in node.items():
                        walk(v, f"{key}.{k}" if key else k)
                elif isinstance(node, str):
                    if PLANE_WORD.search(re.sub(PLANE_OFFERS, "", node)):
                        problems.append(f"{path.relative_to(ROOT)}: {key}")

            walk(json.loads(path.read_text(encoding="utf-8")))
    visible = re.compile(r'"[^"]*\bPlane\b[^"]*"')
    for relative in [*TITLE_FILES, *MANIFESTS, "packages/constants/src/metadata.ts"]:
        for line in (ROOT / relative).read_text(encoding="utf-8").splitlines():
            if visible.search(line):
                problems.append(f"{relative}: {line.strip()}")
    for path in (LOGO, LOCKUP, ADMIN_LOCKUP):
        if "ATLANTE" not in path.read_text(encoding="utf-8"):
            problems.append(f"{path.relative_to(ROOT)}: il disegno è ancora quello di Plane")
    for path in sorted(EMAIL_TEMPLATES.rglob("*.html")):
        for match in EMAIL_EXTERNAL_IMAGE.finditer(path.read_text(encoding="utf-8")):
            problems.append(f"{path.relative_to(ROOT)}: immagine da un altro server {match.group(0)[:80]}")
    for path in EMAIL_TASKS:
        for line in path.read_text(encoding="utf-8").splitlines():
            if re.match(r"\s*subject = ", line) and PLANE_WORD.search(line):
                problems.append(f"{path.relative_to(ROOT)}: {line.strip()}")
    if not COLORS_CSS.exists() or "atlante-colori.css" not in TAILWIND_INDEX.read_text(encoding="utf-8"):
        problems.append("packages/tailwind-config: i colori di Atlante non sono applicati")
    elif COLORS_CSS.read_text(encoding="utf-8") != colors_css(brand):
        # Every color of Plane, in both themes, must have Atlante's hue: one missing is #23 again.
        problems.append(f"{COLORS_CSS.relative_to(ROOT)}: non copre tutti i colori di Plane, rilanciare marchio.py")
    return problems


def main():
    brand = load_brand()
    if "--verifica" not in sys.argv:
        make_icons(brand)
        LOGO.write_text(logo_tsx(), encoding="utf-8")
        LOCKUP.write_text(lockup_tsx(brand), encoding="utf-8")
        ADMIN_LOCKUP.write_text(lockup_tsx(brand), encoding="utf-8")
        apply_colors(brand)
        apply_titles(brand)
        changed = apply_texts(brand)
        copied = copy_icons()
        emails = apply_emails(brand)
        print(f"Marchio applicato: logo, colori, titoli, {len(changed)} file di testi, {copied} icone, {emails} file delle email.")
        if brand.get("provvisorio"):
            print("Attenzione: logo e colore sono ancora provvisori (atlante/marchio/marchio.json).")
    problems = check(brand)
    for problem in problems:
        print(f"  Da sistemare: {problem}")
    if problems:
        sys.exit(1)
    print("Verifica: nei punti controllati non resta \"Plane\" visibile, e i colori di Atlante coprono tutti quelli di Plane.")


if __name__ == "__main__":
    main()
