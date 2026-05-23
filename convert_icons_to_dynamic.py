#!/usr/bin/env python3
import argparse
import colorsys
import re
import sys
from collections import Counter
from pathlib import Path

CSS = '\n    <style type="text/css" id="current-color-scheme">\n.ColorScheme-Text{color:#232629}.ColorScheme-Highlight{color:#3daee9}\n    </style>'
HEX6 = re.compile(r"#[0-9a-fA-F]{6}\b")
GRAPHIC_TAGS = re.compile(r"^<(rect|circle|ellipse|path|polygon|polyline|stop)\b", re.I)


def hex_to_hsl(hex_str):
    h = hex_str.lstrip("#").lower()
    r, g, b = int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h, s, l


def build_global_palette_relations(files, vibrancy):
    all_colors = []
    for f in files:
        try:
            all_colors.extend(HEX6.findall(f.read_text(encoding="utf-8")))
        except Exception:
            continue

    if not all_colors:
        return {}
    counts = Counter([c.lower() for c in all_colors])
    valid_colors = {}

    for hx, cnt in counts.items():
        h = hx.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        if (
            max(r, g, b) < 30
            or min(r, g, b) > 245
            or (max(r, g, b) - min(r, g, b)) < (14 - vibrancy)
        ):
            continue
        valid_colors[hx] = cnt

    if not valid_colors:
        return {}

    avg_l = sum(hex_to_hsl(c)[2] for c in valid_colors) / len(valid_colors)
    relations_map = {}

    for hx in valid_colors:
        _, _, l = hex_to_hsl(hx)
        if avg_l > 0.5:
            relations_map[hx] = (
                "ColorScheme-Highlight" if l > avg_l - 0.05 else "ColorScheme-Text"
            )
        else:
            relations_map[hx] = (
                "ColorScheme-Highlight" if l < avg_l + 0.05 else "ColorScheme-Text"
            )

    return relations_map


def _inject_class(tag, role):
    if any(c in tag for c in ("ColorScheme-Text", "ColorScheme-Highlight")):
        return tag
    ex = re.search(r'class\s*=\s*["\']([^"\']*)["\']', tag)
    if ex:
        v = set(ex.group(1).strip().split() + [role])
        return tag[: ex.start(1)] + ' class="' + " ".join(v) + '"' + tag[ex.end(1) :]
    end = tag.index(">")
    offset = 1 if tag[end - 1] == "/" else 0
    return tag[: end - offset] + f' class="{role}"' + tag[end - offset :]


def patch_svg_with_relations(text, relations_map):
    old = text

    def _element_replacer(match):
        tag = match.group(0)
        if not GRAPHIC_TAGS.match(tag):
            return tag

        found_hexes = HEX6.findall(tag)
        if not found_hexes:
            return tag

        target_role = None
        for hx in found_hexes:
            hl = hx.lower()
            if hl in relations_map:
                target_role = relations_map[hl]
                break

        if target_role:
            tag = re.sub(
                r'(fill|stroke|stop-color)\s*=\s*["\']#[0-9a-fA-F]{6}["\']',
                r'\1="currentColor"',
                tag,
            )
            tag = re.sub(
                r"(fill|stroke|stop-color)\s*:\s*#[0-9a-fA-F]{6};?",
                r"\1:currentColor;",
                tag,
                flags=re.I,
            )
            return _inject_class(tag, target_role)
        return tag

    text = re.sub(r"<[\w:-]+[^>]*>", _element_replacer, text)
    text = re.sub(
        r'<style[^>]*id="current-color-scheme"[^>]*>.*?</style>',
        "",
        text,
        flags=re.DOTALL | re.I,
    )

    m = re.search(r"(<svg\b[^>]*?>)", text, re.I | re.DOTALL)
    if m and "current-color-scheme" not in text:
        text = text[: m.end(1)] + CSS + text[m.end(1) :]

    return text if text != old else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=str)
    parser.add_argument("--vibrancy", type=int, default=4)
    args = parser.parse_args()

    tgt = Path(args.path).expanduser()
    valid_files = [
        f for f in tgt.rglob("*.svg") if f.is_file() and "folder" in f.name.lower()
    ]
    if not valid_files:
        return

    relations_map = build_global_palette_relations(valid_files, args.vibrancy)
    if not relations_map:
        return

    total = patched = 0
    for f in sorted(valid_files):
        total += 1
        try:
            r = patch_svg_with_relations(f.read_text(encoding="utf-8"), relations_map)
            if r is not None:
                f.write_text(r, encoding="utf-8")
                patched += 1
        except Exception as e:
            print(f"ERROR {f}: {e}")

    print(f"Processed: {total} | Patched: {patched}")


if __name__ == "__main__":
    main()
